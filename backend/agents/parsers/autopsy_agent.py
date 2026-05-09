"""
EVIDRA — Autopsy Agent (Tier 2).

Implements the advanced NLP pipeline from Complete ML Specification:
- Text Segmentation
- Structured LLM Extraction
- Rule-Enhanced Logistic Manner Classifier
"""
import json
import re
from uuid import UUID
from typing import Tuple
from agents.base import BaseAgent
from core.llm_gateway import llm

SECTION_PATTERNS = {
    "CAUSE_OF_DEATH":    r"cause\s+of\s+death|cause\s*:",
    "MANNER_OF_DEATH":   r"manner\s+of\s+death|manner\s*:",
    "EXTERNAL_EXAMINATION": r"external\s+exam|external\s+findings",
    "POSTMORTEM_SIGNS":  r"postmortem\s+changes|rigor|lividity|decomp",
    "TOXICOLOGY":        r"toxicol|drug\s+screen|blood\s+alcohol",
    "OPINION":           r"opinion|summary|conclusion"
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

class MannerClassifier:
    """Rule-enhanced logistic fallback for manner of death classification."""
    HIGH_CONFIDENCE_RULES = {
        "HOMICIDE": ["defensive wound", "multiple blunt force", "ligature mark", "stab wound posterior", "body moved post mortem"],
        "SUICIDE": ["hesitation wound", "self-inflicted", "gunshot wound contact range intraoral"],
        "NATURAL": ["coronary artery disease", "myocardial infarction", "natural disease process"]
    }

    def classify(self, text: str, llm_manner: str, llm_confidence: float) -> Tuple[str, float]:
        text_lower = text.lower()
        rule_scores = {m: 0 for m in ["HOMICIDE", "SUICIDE", "ACCIDENT", "NATURAL", "UNDETERMINED"]}

        for manner, keywords in self.HIGH_CONFIDENCE_RULES.items():
            for kw in keywords:
                if kw in text_lower:
                    rule_scores[manner] += 0.15

        best_rule_manner = max(rule_scores, key=rule_scores.get)
        best_rule_score = rule_scores[best_rule_manner]

        if best_rule_score >= 0.30 and best_rule_manner == llm_manner:
            return llm_manner, min(0.97, llm_confidence + best_rule_score)
        elif best_rule_score >= 0.30 and best_rule_manner != llm_manner:
            return best_rule_manner, 0.65 # Conflict fallback
        return llm_manner, llm_confidence

class AutopsyAgent(BaseAgent):
    agent_id = "autopsy_agent"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        prior = await self.get_prior_result("evidence_parser")
        if not prior or "files" not in prior:
            raise ValueError("Missing upstream data")
            
        autopsy_text = ""
        for file_id, data in prior["files"].items():
            if data["doc_type"] == "AUTOPSY_REPORT":
                autopsy_text += data["content"] + "\n\n"
                
        if not autopsy_text:
            return {"status": "SKIPPED", "reason": "No autopsy report"}

        # 1. Segment Text
        sections = segment_autopsy_text(autopsy_text)
        combined = "\n\n".join([f"### {k}\n{v}" for k, v in sections.items() if v.strip()])

        # 2. LLM Extraction
        prompt = f"""
        Extract the structured pathology data from this segmented autopsy text.
        Return ONLY JSON matching:
        {{
            "demographics": {{"age": 0, "sex": "", "weight_kg": 0.0}},
            "tod_indicators": {{"rectal_temp_c": 0.0, "ambient_temp_c": 0.0, "temp_time": "ISO8601", "rigor_mortis": "NONE|EARLY|FULL|RESOLVING", "livor_mortis": "NONE|EARLY|FIXED", "decomposition": "NONE|EARLY|MODERATE|ADVANCED"}},
            "manner_of_death": "HOMICIDE|SUICIDE|ACCIDENT|NATURAL|UNDETERMINED",
            "manner_confidence": 0.8,
            "cause_of_death": ""
        }}
        TEXT:\n{combined[:8000]}
        """
        resp = await llm.complete(task="autopsy_extract", prompt=prompt)
        pathology_data = json.loads(resp.text.replace("```json", "").replace("```", "").strip())

        # 3. Manner Classifier (Rule-Enhanced)
        classifier = MannerClassifier()
        final_manner, final_conf = classifier.classify(
            autopsy_text, 
            pathology_data.get("manner_of_death", "UNDETERMINED"),
            pathology_data.get("manner_confidence", 0.5)
        )
        pathology_data["manner_of_death"] = final_manner
        pathology_data["manner_confidence"] = final_conf

        await self.log_step(
            "HYBRID_ML", 
            "Extracted and Classified Pathology",
            f"Segmented text. Classified manner as {final_manner} with {final_conf:.2f} confidence.",
            confidence=final_conf
        )

        return {"pathology": pathology_data, "_confidence": final_conf}
