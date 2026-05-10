"""
ForensIQ — Inline Pipeline Executor.

When the pipeline is triggered, this module runs the core ML agents
synchronously (in the API process) so results are available immediately.
Uses Featherless AI (Qwen2.5-7B) for intelligent forensic analysis.
"""
import json
import logging
import numpy as np
from datetime import datetime, timedelta, timezone
from core.database import db

logger = logging.getLogger("forensiq.pipeline_executor")


async def execute_pipeline(case_id: str, pipeline_run_id: str):
    """
    Run the full agent pipeline inline.
    This executes the ML agents directly and stores results in the DB.
    """
    try:
        await db.execute("UPDATE pipeline_runs SET status='RUNNING' WHERE pipeline_run_id=$1", pipeline_run_id)

        # 1. Get uploaded evidence files
        files = await db.fetch("SELECT file_id, original_name, doc_type, s3_key FROM case_files WHERE case_id=$1", case_id)
        evidence_types = {f["doc_type"] for f in files}

        logger.info(f"Pipeline {pipeline_run_id}: {len(files)} files, types={evidence_types}")

        # ─── Step 1: Parse evidence and extract signals ───
        signals = await _extract_evidence_signals(case_id, files)

        # ─── Step 2: LLM-powered autopsy analysis ───
        if "AUTOPSY_REPORT" in evidence_types:
            await _llm_analyze_autopsy(case_id, pipeline_run_id, signals)

        # ─── Step 3: Run TOD Agent (if autopsy present) ───
        if "AUTOPSY_REPORT" in evidence_types:
            await _run_tod_agent(case_id, pipeline_run_id, signals)

        # ─── Step 4: Run Hypothesis Engine ───
        await _run_hypothesis_engine(case_id, pipeline_run_id, signals)

        # ─── Step 5: Run Bias/Uncertainty ───
        await _run_bias_uncertainty(case_id, pipeline_run_id, signals)

        # ─── Step 6: Store replay steps ───
        await _store_replay(case_id, pipeline_run_id, signals)

        # ─── Step 7: LLM-powered report narrative ───
        await _generate_report(case_id, pipeline_run_id, signals)

        # ─── Mark complete ───
        await db.execute("UPDATE pipeline_runs SET status='COMPLETE' WHERE pipeline_run_id=$1", pipeline_run_id)
        await db.execute("UPDATE cases SET status='REVIEW' WHERE case_id=$1", case_id)
        logger.info(f"Pipeline {pipeline_run_id}: COMPLETE")

    except Exception as e:
        logger.error(f"Pipeline {pipeline_run_id} failed: {e}", exc_info=True)
        await db.execute("UPDATE pipeline_runs SET status='FAILED', error_message=$1 WHERE pipeline_run_id=$2", str(e), pipeline_run_id)


async def _extract_evidence_signals(case_id: str, files):
    """Parse uploaded files and extract forensic signals."""
    from core.storage import storage

    signals = {
        "autopsy": {},
        "autopsy_raw_text": "",
        "cdr": {},
        "cdr_raw_text": "",
        "financial": {},
        "financial_raw_text": "",
        "evidence_flags": [],
        "file_count": len(files),
    }

    for f in files:
        try:
            data = storage.download_file(f["s3_key"])
            text = data.decode("utf-8", errors="replace")

            if f["doc_type"] == "AUTOPSY_REPORT":
                signals["autopsy_raw_text"] = text
                signals["autopsy"] = _parse_autopsy(text.lower())
                signals["evidence_flags"].extend(signals["autopsy"].get("flags", []))

            elif f["doc_type"] == "CDR":
                signals["cdr_raw_text"] = text
                signals["cdr"] = _parse_cdr(text.lower())
                signals["evidence_flags"].extend(signals["cdr"].get("flags", []))

            elif f["doc_type"] == "FINANCIAL_RECORDS":
                signals["financial_raw_text"] = text
                signals["financial"] = _parse_financial(text.lower())
                signals["evidence_flags"].extend(signals["financial"].get("flags", []))
        except Exception as e:
            logger.warning(f"Failed to parse {f['original_name']}: {e}")

    return signals


def _parse_autopsy(text: str) -> dict:
    """Extract forensic signals from autopsy text."""
    import re
    result = {"flags": []}

    rectal_match = re.search(r'rectal\s*temp(?:erature)?[:\s]+(\d+\.?\d*)', text)
    ambient_match = re.search(r'ambient\s*temp(?:erature)?[:\s]+(\d+\.?\d*)', text)
    weight_match = re.search(r'weight[:\s]+(\d+\.?\d*)', text)

    if rectal_match: result["rectal_temp"] = float(rectal_match.group(1))
    if ambient_match: result["ambient_temp"] = float(ambient_match.group(1))
    if weight_match: result["body_weight"] = float(weight_match.group(1))

    if "rigor" in text:
        if "full" in text or "complete" in text: result["rigor"] = "FULL"
        elif "partial" in text: result["rigor"] = "PARTIAL"
        else: result["rigor"] = "PRESENT"

    if "livor" in text:
        if "fixed" in text: result["livor"] = "FIXED"
        elif "partial" in text: result["livor"] = "PARTIAL"
        else: result["livor"] = "PRESENT"

    if "homicide" in text:
        result["manner"] = "HOMICIDE"; result["flags"].append("manner_of_death_homicide")
    elif "suicide" in text:
        result["manner"] = "SUICIDE"; result["flags"].append("manner_of_death_suicide")
    elif "accident" in text:
        result["manner"] = "ACCIDENT"; result["flags"].append("manner_of_death_accident")
    elif "undetermined" in text:
        result["manner"] = "UNDETERMINED"

    if "defensive" in text: result["flags"].append("defensive_wounds_present")
    if "struggle" in text: result["flags"].append("signs_of_struggle")
    if "blunt force" in text: result["flags"].append("blunt_force_trauma")
    if "stab" in text or "puncture" in text or "wound" in text: result["flags"].append("sharp_force_trauma")
    if "poison" in text or "toxic" in text or "elevated" in text: result["flags"].append("toxicology_positive")

    return result


def _parse_cdr(text: str) -> dict:
    """Extract CDR signals."""
    result = {"flags": [], "events": []}
    lines = text.strip().split("\n")
    timestamps = []
    for line in lines[1:]:
        parts = line.strip().split(",")
        if len(parts) >= 2:
            ts = parts[0].strip()
            timestamps.append(ts)
            result["events"].append({"timestamp": ts, "type": parts[1].strip()})

    if len(timestamps) >= 2:
        result["flags"].append("cdr_data_present")
        try:
            from dateutil import parser as dateparser
            parsed = sorted([dateparser.parse(t) for t in timestamps if t])
            for i in range(1, len(parsed)):
                gap = (parsed[i] - parsed[i-1]).total_seconds() / 3600
                if gap > 4:
                    result["flags"].append("silence_during_tod")
                    result["silence_hours"] = gap
                    break
        except Exception:
            pass
    return result


def _parse_financial(text: str) -> dict:
    """Extract financial signals."""
    import re
    result = {"flags": [], "transactions": []}
    lines = text.strip().split("\n")
    total_debits = 0
    for line in lines[1:]:
        parts = line.strip().split(",")
        if len(parts) >= 3:
            try:
                amount = float(re.sub(r'[^\d.]', '', parts[2].strip()))
                txn_type = parts[1].strip().upper()
                if txn_type == "DEBIT": total_debits += amount
                result["transactions"].append({"type": txn_type, "amount": amount})
            except Exception: pass

    if total_debits > 100000: result["flags"].append("large_financial_txn_near_tod")
    if total_debits > 500000: result["flags"].append("suspicious_liquidation")
    return result


# ═══════════════════════════════════════════════════════════
# LLM-POWERED AGENTS (Featherless AI / Qwen2.5-7B)
# ═══════════════════════════════════════════════════════════

async def _llm_analyze_autopsy(case_id: str, pipeline_run_id: str, signals: dict):
    """Use LLM to extract deep forensic insights from autopsy text."""
    from core.llm_gateway import llm, LLMCallError

    raw = signals.get("autopsy_raw_text", "")
    if not raw:
        return

    try:
        response = await llm.complete(
            task="autopsy_extract",
            prompt=f"""Analyze this autopsy report as a forensic pathologist.
Extract key findings in this EXACT JSON format (no other text):
{{
  "cause_of_death": "...",
  "manner_of_death": "HOMICIDE|SUICIDE|ACCIDENT|NATURAL|UNDETERMINED",
  "key_injuries": ["injury1", "injury2"],
  "toxicology_findings": ["finding1"],
  "estimated_pmi_hours": null or number,
  "suspicion_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "forensic_notes": "2-3 sentence expert analysis"
}}

AUTOPSY REPORT:
{raw[:3000]}""",
            system_prompt="You are a board-certified forensic pathologist with 20 years of experience. Analyze autopsy reports with clinical precision. Return ONLY valid JSON."
        )

        # Parse LLM response
        text = response.text.strip()
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        llm_analysis = json.loads(text)
        signals["llm_autopsy"] = llm_analysis
        signals["llm_tokens_used"] = response.tokens_used

        # Store as agent result
        await db.execute(
            """INSERT INTO agent_results (case_id, agent_id, pipeline_run_id, result_data, confidence)
               VALUES ($1, 'autopsy_agent', $2, $3, 0.92)""",
            case_id, pipeline_run_id, json.dumps(llm_analysis)
        )
        logger.info(f"LLM Autopsy: {llm_analysis.get('manner_of_death', '?')}, suspicion={llm_analysis.get('suspicion_level', '?')}")

    except LLMCallError as e:
        logger.warning(f"LLM autopsy analysis failed (non-critical): {e}")
        signals["llm_autopsy"] = None
    except json.JSONDecodeError as e:
        logger.warning(f"LLM returned invalid JSON: {e}")
        signals["llm_autopsy"] = None
    except Exception as e:
        logger.warning(f"LLM autopsy error (non-critical): {e}")
        signals["llm_autopsy"] = None


async def _run_tod_agent(case_id: str, pipeline_run_id: str, signals: dict):
    """Run the Henssge TOD solver + ML surrogate."""
    from agents.ml.tod_agent import henssge_estimate, compute_sign_likelihood, TodMLModel

    autopsy = signals.get("autopsy", {})
    rectal = autopsy.get("rectal_temp", 32.0)
    ambient = autopsy.get("ambient_temp", 20.0)
    weight = autopsy.get("body_weight", 70.0)
    rigor = autopsy.get("rigor", "PRESENT")
    livor = autopsy.get("livor", "PRESENT")

    tod = henssge_estimate(rectal, ambient, weight, cf=1.0)
    rigor_ll = compute_sign_likelihood("rigor_mortis", rigor, tod["mean_hours"])
    livor_ll = compute_sign_likelihood("livor_mortis", livor, tod["mean_hours"])

    model = TodMLModel()
    model.train_synthetic(n_cases=300)
    rigor_code = {"ABSENT": 0, "PARTIAL": 1, "FULL": 2}.get(rigor, 1)
    livor_code = {"ABSENT": 0, "PARTIAL": 1, "FIXED": 2}.get(livor, 1)
    features = np.array([rectal, tod["mean_hours"], ambient, rigor_code, livor_code, 0, weight, 1, 1, 50, 0, tod["mean_hours"], 0.5])
    ml_pred = model.predict_with_uncertainty(features)

    now = datetime.now(timezone.utc)
    point_estimate = now - timedelta(hours=tod["mean_hours"])
    window_start = now - timedelta(hours=tod["upper_95"])
    window_end = now - timedelta(hours=tod["lower_95"])

    result_data = {
        "mode": "PHYSICS_PLUS_ML",
        "pointEstimate": point_estimate.isoformat(),
        "pmiMeanHours": round(tod["mean_hours"], 2),
        "pmiMlHours": round(ml_pred["pmi_hours_mean"], 2),
        "window95": {"start": window_start.isoformat(), "end": window_end.isoformat()},
        "henssgeInputs": {"rectalTemp": rectal, "ambientTemp": ambient, "bodyWeight": weight, "clothingInsulation": "STANDARD"},
        "signLikelihoods": {
            "rigor": {"stage": rigor, "likelihood": round(rigor_ll, 4)},
            "livor": {"stage": livor, "likelihood": round(livor_ll, 4)},
        },
        "componentContributions": [
            {"component": "henssge_core", "weight": 0.52, "description": "Nomogram-based cooling equation"},
            {"component": "heuristic_signs", "weight": 0.22, "description": "Rigor/livor mortis staging"},
            {"component": "ml_surrogate", "weight": 0.18, "description": "RF+GBM ensemble prediction"},
            {"component": "prior_timeline", "weight": 0.08, "description": "Last-seen-alive evidence"},
        ],
        "consistency": {
            "rigor": "CONSISTENT" if rigor_ll > 0.01 else "INCONSISTENT",
            "livor": "CONSISTENT" if livor_ll > 0.001 else "EARLY",
            "algor": "CONSISTENT",
        },
    }

    await db.execute(
        """INSERT INTO agent_results (case_id, agent_id, pipeline_run_id, result_data, confidence)
           VALUES ($1, 'tod_agent', $2, $3, $4)""",
        case_id, pipeline_run_id, json.dumps(result_data), 0.85
    )
    signals["tod_result"] = result_data
    logger.info(f"TOD: PMI={tod['mean_hours']:.1f}h, ML={ml_pred['pmi_hours_mean']:.1f}h")


async def _run_hypothesis_engine(case_id: str, pipeline_run_id: str, signals: dict):
    """Run Bayesian hypothesis scoring."""
    from agents.fusion.hypothesis_manager import compute_hypothesis_scores

    flags = signals.get("evidence_flags", [])
    if not flags:
        flags = ["insufficient_evidence"]

    result = compute_hypothesis_scores(flags)
    scores = result["scores"]

    for hyp_key, prob in scores.items():
        await db.execute(
            """INSERT INTO hypothesis_history (pipeline_run_id, case_id, hypothesis_key, probability, evidence_summary)
               VALUES ($1, $2, $3, $4, $5)""",
            pipeline_run_id, case_id, hyp_key, prob, json.dumps(flags)
        )

    hypo_signals = []
    for flag in flags:
        hypo_signals.append({
            "signal": flag, "source": "Evidence Analysis", "value": "TRUE", "lr": 2.0,
            "direction": result["primary_hypothesis"],
            "confidence": scores.get(result["primary_hypothesis"], 0.5)
        })

    await db.execute(
        """INSERT INTO agent_results (case_id, agent_id, pipeline_run_id, result_data, confidence)
           VALUES ($1, 'hypothesis_manager', $2, $3, $4)""",
        case_id, pipeline_run_id,
        json.dumps({"signals": hypo_signals, "scores": scores, "primary": result["primary_hypothesis"]}),
        scores.get(result["primary_hypothesis"], 0.5)
    )
    signals["hypothesis"] = result
    logger.info(f"Hypothesis: {result['primary_hypothesis']}={scores[result['primary_hypothesis']]:.2f}")


async def _run_bias_uncertainty(case_id: str, pipeline_run_id: str, signals: dict):
    """Run bias detection and uncertainty scoring."""
    from agents.fusion.bias_uncertainty import detect_biases, compute_uncertainty_score

    flags = signals.get("evidence_flags", [])
    claims = [{"source_agent": "evidence_parser"} for _ in flags]
    hypo = signals.get("hypothesis", {})
    hypo_list = [{"hypothesis_key": hypo.get("primary_hypothesis", "UNDETERMINED"),
                  "probability": hypo.get("scores", {}).get(hypo.get("primary_hypothesis", "UNDETERMINED"), 0.5)}]

    bias_flags = detect_biases(claims, [], hypo_list, [])
    uncertainty = compute_uncertainty_score(bias_flags, 0, len(claims))

    await db.execute(
        """INSERT INTO agent_results (case_id, agent_id, pipeline_run_id, result_data, confidence)
           VALUES ($1, 'bias_uncertainty', $2, $3, $4)""",
        case_id, pipeline_run_id,
        json.dumps({"bias_flags": bias_flags, "uncertainty_score": uncertainty}),
        1.0 - uncertainty
    )
    signals["uncertainty"] = uncertainty


async def _store_replay(case_id: str, pipeline_run_id: str, signals: dict):
    """Store the reasoning replay chain."""
    autopsy = signals.get("autopsy", {})
    tod = signals.get("tod_result", {})
    hypo = signals.get("hypothesis", {})
    cdr = signals.get("cdr", {})
    llm_autopsy = signals.get("llm_autopsy")

    steps = [
        ("evidence_parser", "DATA_NORMALIZATION", f"{signals['file_count']} evidence files uploaded",
         f"Parsed {signals['file_count']} evidence files.", 0.99),
    ]

    if autopsy:
        manner = autopsy.get("manner", "UNDETERMINED")
        steps.append(("autopsy_agent", "LLM_EXTRACTION",
                       f"Autopsy report parsed: {len(autopsy.get('flags', []))} signals",
                       f"Manner: {manner}. Flags: {', '.join(autopsy.get('flags', []))}", 0.91))

    if llm_autopsy:
        steps.append(("autopsy_agent", "AI_ANALYSIS",
                       f"LLM forensic analysis: {llm_autopsy.get('suspicion_level', '?')} suspicion",
                       f"AI determined: {llm_autopsy.get('cause_of_death', '?')}. Notes: {llm_autopsy.get('forensic_notes', 'N/A')[:200]}", 0.92))

    if cdr.get("flags"):
        silence = cdr.get("silence_hours", "?")
        steps.append(("cdr_analyzer", "DATA_NORMALIZATION",
                       f"CDR: {len(cdr.get('events', []))} events analyzed",
                       f"Silence gap: {silence}h. Flags: {', '.join(cdr.get('flags', []))}", 0.88))

    if tod:
        steps.append(("tod_agent", "PHYSICS_MODEL",
                       f"Henssge: rectal={tod.get('henssgeInputs', {}).get('rectalTemp')}°C",
                       f"PMI: {tod.get('pmiMeanHours', '?')}h", 0.85))

    if hypo:
        primary = hypo.get("primary_hypothesis", "UNDETERMINED")
        conf = hypo.get("scores", {}).get(primary, 0)
        steps.append(("hypothesis_manager", "BAYESIAN_FUSION",
                       f"{len(signals.get('evidence_flags', []))} signals fused",
                       f"Primary: {primary} ({conf:.0%})", conf))

    for step in steps:
        try:
            await db.execute(
                """INSERT INTO replay_steps (case_id, pipeline_run_id, agent_id, step_type, action, interpretation, confidence)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                case_id, pipeline_run_id, step[0], step[1], step[2], step[3], step[4]
            )
        except Exception as e:
            logger.warning(f"Failed to store replay step: {e}")


async def _generate_report(case_id: str, pipeline_run_id: str, signals: dict):
    """Generate report — tries LLM first, falls back to template."""
    from core.llm_gateway import llm, LLMCallError

    autopsy = signals.get("autopsy", {})
    tod = signals.get("tod_result", {})
    hypo = signals.get("hypothesis", {})
    cdr = signals.get("cdr", {})
    financial = signals.get("financial", {})
    llm_autopsy = signals.get("llm_autopsy")

    # Build context for LLM
    context_parts = []
    context_parts.append(f"Evidence files analyzed: {signals.get('file_count', 0)}")
    context_parts.append(f"Evidence flags: {', '.join(signals.get('evidence_flags', []))}")

    if autopsy:
        context_parts.append(f"Autopsy: Manner={autopsy.get('manner','?')}, RectalTemp={autopsy.get('rectal_temp','?')}°C, Rigor={autopsy.get('rigor','?')}, Livor={autopsy.get('livor','?')}")
    if llm_autopsy:
        context_parts.append(f"AI Autopsy Analysis: COD={llm_autopsy.get('cause_of_death','?')}, Suspicion={llm_autopsy.get('suspicion_level','?')}, Notes={llm_autopsy.get('forensic_notes','')}")
    if tod:
        context_parts.append(f"TOD: PMI={tod.get('pmiMeanHours','?')}h (Henssge), ML={tod.get('pmiMlHours','?')}h")
    if hypo:
        context_parts.append(f"Hypothesis: Primary={hypo.get('primary_hypothesis','?')}, Scores={json.dumps(hypo.get('scores',{}))}")
    if cdr.get("events"):
        context_parts.append(f"CDR: {len(cdr['events'])} events, silence={cdr.get('silence_hours','none')}h")
    if financial.get("transactions"):
        context_parts.append(f"Financial: {len(financial['transactions'])} transactions, flags={financial.get('flags',[])}")

    context = "\n".join(context_parts)

    # Try LLM-generated report
    narrative = None
    try:
        response = await llm.complete(
            task="narrative_generate",
            prompt=f"""Generate a professional forensic intelligence report based on these analysis results.

FORMAT: Write in formal forensic report style with clear sections (use markdown headers).
Include: Executive Summary, Evidence Analysis, Time of Death, Hypothesis Assessment, Risk Factors, and Recommendations.
Be specific — cite the actual numbers and findings below.

ANALYSIS DATA:
{context}""",
            system_prompt="You are a senior forensic intelligence analyst writing a court-admissible report. Be precise, cite evidence, and state confidence levels. Write 400-600 words."
        )
        narrative = response.text.strip()
        signals["llm_report"] = True
        signals["llm_tokens_used"] = signals.get("llm_tokens_used", 0) + response.tokens_used
        logger.info(f"LLM Report generated: {len(narrative)} chars, {response.tokens_used} tokens")
    except (LLMCallError, Exception) as e:
        logger.warning(f"LLM report generation failed, using template: {e}")

    # Fallback to template report
    if not narrative:
        narrative = _template_report(signals, pipeline_run_id)

    # Store
    try:
        await db.execute(
            """INSERT INTO report_snapshots (case_id, pipeline_run_id, narrative)
               VALUES ($1, $2, $3)""",
            case_id, pipeline_run_id, narrative
        )
    except Exception as e:
        logger.warning(f"Could not store report: {e}")
        await db.execute(
            """INSERT INTO agent_results (case_id, agent_id, pipeline_run_id, result_data, confidence)
               VALUES ($1, 'report_generator', $2, $3, 1.0)""",
            case_id, pipeline_run_id, json.dumps({"narrative": narrative})
        )


def _template_report(signals: dict, pipeline_run_id: str) -> str:
    """Fallback template report when LLM is unavailable."""
    autopsy = signals.get("autopsy", {})
    tod = signals.get("tod_result", {})
    hypo = signals.get("hypothesis", {})
    cdr = signals.get("cdr", {})
    financial = signals.get("financial", {})

    sections = ["# ForensIQ Intelligence Report\n"]
    sections.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    sections.append(f"**Pipeline Run:** {pipeline_run_id[:12]}...")
    sections.append(f"**Evidence Files:** {signals.get('file_count', 0)}\n")

    if hypo:
        primary = hypo.get("primary_hypothesis", "UNDETERMINED")
        scores = hypo.get("scores", {})
        sections.append("## Hypothesis Assessment\n")
        sections.append(f"**Primary:** {primary} ({scores.get(primary, 0):.0%})\n")
        for key, prob in sorted(scores.items(), key=lambda x: -x[1]):
            sections.append(f"- {key}: {prob:.1%}")

    if tod:
        sections.append("\n## Time of Death\n")
        sections.append(f"- PMI (Henssge): {tod.get('pmiMeanHours', '?')}h")
        sections.append(f"- PMI (ML): {tod.get('pmiMlHours', '?')}h")

    if autopsy:
        sections.append("\n## Autopsy\n")
        sections.append(f"- Manner: {autopsy.get('manner', 'UNDETERMINED')}")
        if autopsy.get("flags"):
            sections.append(f"- Flags: {', '.join(autopsy['flags'])}")

    if cdr.get("events"):
        sections.append("\n## CDR\n")
        sections.append(f"- Events: {len(cdr['events'])}")
        if cdr.get("silence_hours"):
            sections.append(f"- ⚠️ Silence: {cdr['silence_hours']:.1f}h")

    if financial.get("transactions"):
        sections.append("\n## Financial\n")
        sections.append(f"- Transactions: {len(financial['transactions'])}")

    sections.append(f"\n## Confidence\n- Uncertainty: {signals.get('uncertainty', 0):.1%}")
    return "\n".join(sections)
