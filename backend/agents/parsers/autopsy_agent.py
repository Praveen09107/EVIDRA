"""
EVIDRA — Autopsy Agent (Tier 2 / M-04).

Implements Core Agent Specs §M-04 and ML Spec §2:
- Full 40+ field LLM extraction schema
- Text segmentation by report section
- 7 pathology cross-check rules
- Field-weighted confidence scoring
- Rule-enhanced manner classification
- LLM narrative generation
"""
import json
import re
import logging
from uuid import UUID
from typing import Tuple, Optional
from agents.base import BaseAgent
from core.llm_gateway import llm

logger = logging.getLogger("evidra.autopsy")

# ═══════════════════════════════════════════════════════════
# TEXT SEGMENTATION (spec §2.1)
# ═══════════════════════════════════════════════════════════

SECTION_PATTERNS = {
    "CAUSE_OF_DEATH":       r"cause\s+of\s+death|cause\s*:",
    "MANNER_OF_DEATH":      r"manner\s+of\s+death|manner\s*:",
    "EXTERNAL_EXAMINATION": r"external\s+exam|external\s+findings",
    "INTERNAL_EXAMINATION": r"internal\s+exam|internal\s+findings|organ",
    "POSTMORTEM_SIGNS":     r"postmortem\s+changes|rigor|lividity|decomp",
    "TOXICOLOGY":           r"toxicol|drug\s+screen|blood\s+alcohol",
    "INJURIES":             r"injur|wound|trauma|abrasion|laceration",
    "OPINION":              r"opinion|summary|conclusion",
}


def segment_autopsy_text(raw_text: str) -> dict:
    lines = raw_text.split("\n")
    sections = {}
    current = "PREAMBLE"
    buffer = []

    for line in lines:
        matched = False
        for section, pattern in SECTION_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                sections[current] = "\n".join(buffer)
                current = section
                buffer = [line]
                matched = True
                break
        if not matched:
            buffer.append(line)
    sections[current] = "\n".join(buffer)
    return sections


# ═══════════════════════════════════════════════════════════
# LLM EXTRACTION PROMPT (spec §M-04: 40+ fields)
# ═══════════════════════════════════════════════════════════

EXTRACTION_PROMPT = """You are a forensic pathology expert AI.
Extract structured information from an autopsy report.
Extract ALL fields. If a field is not mentioned, return null.
Do NOT infer facts not explicitly stated.
Return valid JSON only — no prose, no markdown.

{
  "pathologist_name": "string|null",
  "autopsy_date": "YYYY-MM-DD|null",
  "report_reference_no": "string|null",

  "cause_of_death_1a": "string|null",
  "cause_of_death_1b": "string|null",
  "cause_of_death_1c": "string|null",
  "cause_of_death_2": "string|null",
  "manner_of_death": "HOMICIDE|SUICIDE|ACCIDENT|NATURAL|UNDETERMINED|null",

  "rigor_mortis": "NONE|EARLY|FULL|RESOLVING|null",
  "livor_mortis": "NONE|EARLY|FIXED|null",
  "livor_distribution": "string|null",
  "decomposition": "NONE|EARLY|MODERATE|ADVANCED|null",

  "rectal_temp_c": "number|null",
  "rectal_temp_time": "HH:MM|null",
  "ambient_temp_c": "number|null",
  "body_weight_kg": "number|null",
  "body_height_cm": "number|null",
  "estimated_age_years": "number|null",
  "sex": "MALE|FEMALE|UNKNOWN|null",

  "injuries_present": "boolean",
  "injury_list": ["string"],
  "defensive_wounds": "boolean|null",
  "defensive_wounds_detail": "string|null",
  "sharp_force_injuries": "boolean|null",
  "blunt_force_injuries": "boolean|null",
  "firearm_injuries": "boolean|null",
  "strangulation_signs": "boolean|null",
  "hesitation_wounds": "boolean|null",

  "toxicology_performed": "boolean|null",
  "alcohol_present": "boolean|null",
  "alcohol_bac": "number|null",
  "drugs_detected": ["string"],
  "drug_details": [{"substance":"string","level":"string","significance":"LETHAL|TOXIC|THERAPEUTIC|TRACE|UNKNOWN"}],
  "poisons_detected": ["string"],

  "scene_type": "INDOOR|OUTDOOR|VEHICLE|PUBLIC|null",
  "body_surface": "BED|GROUND|FLOOR|WATER|OTHER|null",
  "clothing_insulation": "LIGHT|MEDIUM|HEAVY|null",

  "last_seen_alive": "ISO_DATETIME|null",
  "found_dead_time": "ISO_DATETIME|null",
  "pathologist_opinion": "string|null",
  "manner_confidence_stated": "HIGH|MEDIUM|LOW|null"
}

===AUTOPSY_REPORT_START===
{report_text}
===AUTOPSY_REPORT_END==="""


# ═══════════════════════════════════════════════════════════
# FIELD-WEIGHTED CONFIDENCE (spec §M-04)
# ═══════════════════════════════════════════════════════════

FIELD_WEIGHTS = {
    "manner_of_death":    0.20,
    "cause_of_death_1a":  0.15,
    "rigor_mortis":       0.10,
    "rectal_temp_c":      0.10,
    "livor_mortis":       0.08,
    "injuries_present":   0.07,
    "defensive_wounds":   0.07,
    "body_weight_kg":     0.05,
    "toxicology_performed": 0.05,
    "ambient_temp_c":     0.05,
    "decomposition":      0.05,
    "found_dead_time":    0.03,
}


def compute_extraction_confidence(data: dict) -> float:
    score = 0.0
    for field, weight in FIELD_WEIGHTS.items():
        val = data.get(field)
        if val is not None and val != "" and val != []:
            score += weight
    return round(score, 3)


# ═══════════════════════════════════════════════════════════
# 7 PATHOLOGY CROSS-CHECK RULES (spec §M-04)
# ═══════════════════════════════════════════════════════════

def run_pathology_checks(data: dict) -> list[dict]:
    warnings = []

    cod = str(data.get("cause_of_death_1a", "")).lower()
    manner = data.get("manner_of_death")
    injuries = data.get("injuries_present", False)
    defensive = data.get("defensive_wounds", False)
    rigor = data.get("rigor_mortis")
    livor = data.get("livor_mortis")
    decomp = data.get("decomposition")
    rectal = data.get("rectal_temp_c")
    weight = data.get("body_weight_kg")
    drugs = data.get("drug_details", [])

    # RULE 1: COD mentions trauma but injuries_present=False
    trauma_keywords = ["trauma", "wound", "fracture", "laceration", "stab", "gunshot"]
    if any(kw in cod for kw in trauma_keywords) and not injuries:
        warnings.append({"code": "COD_INJURY_MISMATCH", "severity": "HIGH",
                         "message": "Cause of death mentions trauma but injuries_present is False"})

    # RULE 2: manner=SUICIDE but defensive_wounds=True
    if manner == "SUICIDE" and defensive:
        warnings.append({"code": "MANNER_DEFENSIVE_WOUND_CONFLICT", "severity": "HIGH",
                         "message": "Manner is SUICIDE but defensive wounds are present"})

    # RULE 3: rigor=FULL + livor=NONE (inconsistent)
    if rigor == "FULL" and livor == "NONE":
        warnings.append({"code": "RIGOR_LIVOR_INCONSISTENT", "severity": "MEDIUM",
                         "message": "Full rigor mortis with no livor mortis is physiologically unusual"})

    # RULE 4: decomp=ADVANCED + rigor=FULL (impossible)
    if decomp == "ADVANCED" and rigor == "FULL":
        warnings.append({"code": "DECOMP_RIGOR_INCONSISTENT", "severity": "HIGH",
                         "message": "Advanced decomposition with full rigor is physiologically impossible"})

    # RULE 5: rectal_temp present but weight=null
    if rectal is not None and weight is None:
        warnings.append({"code": "MISSING_BODY_WEIGHT_FOR_TOD", "severity": "MEDIUM",
                         "message": "Rectal temperature recorded but body weight missing — TOD calculation will use default"})

    # RULE 6: Impossible temp
    if rectal is not None and rectal > 37.5:
        warnings.append({"code": "UNUSUALLY_HIGH_RECTAL_TEMP", "severity": "MEDIUM",
                         "message": f"Rectal temp {rectal}°C exceeds living norm — verify measurement"})

    # RULE 7: Lethal drug + manner=HOMICIDE
    lethal_drugs = [d for d in (drugs or []) if isinstance(d, dict) and d.get("significance") == "LETHAL"]
    if lethal_drugs and manner == "HOMICIDE":
        warnings.append({"code": "LETHAL_TOXICOLOGY_WITH_HOMICIDE", "severity": "INFO",
                         "message": "Lethal drug levels detected with homicide manner — consider poisoning vs incidental"})

    return warnings


# ═══════════════════════════════════════════════════════════
# MANNER CLASSIFIER (Rule-Enhanced) (spec §2.3)
# ═══════════════════════════════════════════════════════════

class MannerClassifier:
    HIGH_CONFIDENCE_RULES = {
        "HOMICIDE": ["defensive wound", "multiple blunt force", "ligature mark", "stab wound posterior",
                     "body moved post mortem", "gunshot wound", "strangulation"],
        "SUICIDE": ["hesitation wound", "self-inflicted", "gunshot wound contact range intraoral",
                    "wrist laceration", "hanging"],
        "NATURAL": ["coronary artery disease", "myocardial infarction", "natural disease process",
                    "pulmonary embolism", "cerebrovascular accident"],
    }

    def classify(self, text: str, llm_manner: str, llm_confidence: float) -> Tuple[str, float]:
        text_lower = text.lower()
        rule_scores = {m: 0.0 for m in ["HOMICIDE", "SUICIDE", "ACCIDENT", "NATURAL", "UNDETERMINED"]}

        for manner, keywords in self.HIGH_CONFIDENCE_RULES.items():
            for kw in keywords:
                if kw in text_lower:
                    rule_scores[manner] += 0.15

        best_rule = max(rule_scores, key=rule_scores.get)
        best_score = rule_scores[best_rule]

        if best_score >= 0.30 and best_rule == llm_manner:
            return llm_manner, min(0.97, llm_confidence + best_score)
        elif best_score >= 0.30 and best_rule != llm_manner:
            return best_rule, 0.65  # Conflict: rule wins with lower confidence
        return llm_manner, llm_confidence


# ═══════════════════════════════════════════════════════════
# NARRATIVE GENERATION (spec §M-04)
# ═══════════════════════════════════════════════════════════

NARRATIVE_PROMPT = """You are a forensic intelligence analyst.
Write a 3-sentence neutral, factual summary covering:
1. Cause and manner of death
2. Key physical findings relevant to investigation
3. Toxicology summary (if available)
Rules: passive voice, factual only, no speculation, no names/locations.

AUTOPSY FINDINGS (JSON):
{autopsy_json}"""


class AutopsyAgent(BaseAgent):
    agent_id = "autopsy_agent"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        prior = await self.get_prior_result("evidence_parser")
        ocr_result = await self.get_prior_result("ocr")

        autopsy_text = ""

        # Get text from evidence parser
        if prior and "files" in prior:
            for file_id, data in prior["files"].items():
                if data["doc_type"] == "AUTOPSY_REPORT":
                    autopsy_text += data["content"] + "\n\n"

        # Merge OCR text if available
        if ocr_result and "ocr_results" in ocr_result:
            for file_id, ocr_data in ocr_result["ocr_results"].items():
                corrected = ocr_data.get("full_text_corrected", "")
                if corrected and not autopsy_text:
                    autopsy_text += corrected + "\n\n"

        if not autopsy_text.strip():
            return {"status": "SKIPPED", "reason": "No autopsy report text available"}

        # 1. Segment Text (spec §2.1)
        sections = segment_autopsy_text(autopsy_text)
        combined = "\n\n".join([f"### {k}\n{v}" for k, v in sections.items() if v.strip()])

        await self.log_step(
            "DATA_NORMALIZATION",
            "Autopsy Text Segmentation",
            f"Segmented into {len(sections)} sections: {list(sections.keys())}",
            confidence=0.95,
        )

        # 2. LLM Extraction (40+ fields)
        resp = await llm.complete(
            task="autopsy_extract",
            prompt=EXTRACTION_PROMPT.format(report_text=combined[:12000]),
            system_prompt="You are a forensic pathology expert AI.",
        )

        try:
            clean = resp.text.replace("```json", "").replace("```", "").strip()
            pathology = json.loads(clean)
        except json.JSONDecodeError:
            await self.log_step("ERROR", "LLM JSON Parse Failed", resp.text[:200], 0.0)
            return {"status": "FAILED", "reason": "LLM returned invalid JSON"}

        await self.log_step(
            "LLM_EXTRACTION",
            "Extracted 40+ Autopsy Fields",
            f"Manner: {pathology.get('manner_of_death')}, COD: {pathology.get('cause_of_death_1a')}",
            confidence=0.88,
        )

        # 3. Manner Classifier (Rule-Enhanced)
        classifier = MannerClassifier()
        llm_manner = pathology.get("manner_of_death", "UNDETERMINED")
        manner_conf_map = {"HIGH": 0.92, "MEDIUM": 0.75, "LOW": 0.55, None: 0.80}
        llm_conf = manner_conf_map.get(pathology.get("manner_confidence_stated"), 0.80)

        final_manner, final_conf = classifier.classify(autopsy_text, llm_manner, llm_conf)
        pathology["manner_of_death"] = final_manner
        pathology["manner_confidence"] = final_conf

        # 4. Pathology Cross-Check Rules (7 rules)
        pathology_warnings = run_pathology_checks(pathology)

        # Adjust confidence based on warnings
        high_warning_count = sum(1 for w in pathology_warnings if w["severity"] == "HIGH")
        final_conf = max(0.3, final_conf - (high_warning_count * 0.08))
        pathology["manner_confidence"] = round(final_conf, 3)

        if pathology_warnings:
            await self.log_step(
                "CONSISTENCY_CHECK",
                "Pathology Cross-Check",
                f"Found {len(pathology_warnings)} warnings: {[w['code'] for w in pathology_warnings]}",
                confidence=0.85,
                warnings=[w["message"] for w in pathology_warnings],
            )

        # 5. Extraction Confidence (field-weighted)
        extraction_confidence = compute_extraction_confidence(pathology)

        # 6. Narrative
        try:
            narr_resp = await llm.complete(
                task="narrative_generate",
                prompt=NARRATIVE_PROMPT.format(autopsy_json=json.dumps(pathology, default=str)[:4000]),
            )
            narrative = narr_resp.text
        except Exception:
            narrative = f"Manner of death: {final_manner}. Cause: {pathology.get('cause_of_death_1a', 'Unknown')}."

        # Build structured output
        result = {
            "pathology": pathology,
            "extraction_confidence": extraction_confidence,
            "pathology_warnings": pathology_warnings,
            "narrative": narrative,
            "sections_found": list(sections.keys()),
            "_confidence": final_conf,
        }

        # Also attach top-level convenience keys for downstream agents
        result["pathology"]["demographics"] = {
            "age": pathology.get("estimated_age_years"),
            "sex": pathology.get("sex"),
            "weight_kg": pathology.get("body_weight_kg"),
        }
        result["pathology"]["tod_indicators"] = {
            "rectal_temp_c": pathology.get("rectal_temp_c"),
            "ambient_temp_c": pathology.get("ambient_temp_c"),
            "temp_time": pathology.get("rectal_temp_time"),
            "rigor_mortis": pathology.get("rigor_mortis"),
            "livor_mortis": pathology.get("livor_mortis"),
            "decomposition": pathology.get("decomposition"),
            "clothing": pathology.get("clothing_insulation", "MEDIUM"),
            "scene_type": pathology.get("scene_type"),
        }

        await self.log_step(
            "HYBRID_ML",
            "Autopsy Analysis Complete",
            f"Manner: {final_manner} ({final_conf:.2f}). "
            f"Extraction conf: {extraction_confidence:.2f}. Warnings: {len(pathology_warnings)}",
            confidence=final_conf,
        )

        return result
