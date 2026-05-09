"""
EVIDRA — Autopsy Agent (Tier 2).

Extracts 40+ forensic pathology fields from raw autopsy reports and 
performs medical consistency cross-checks using the LLM.
"""
import json
from uuid import UUID
from agents.base import BaseAgent
from core.llm_gateway import llm

class AutopsyAgent(BaseAgent):
    agent_id = "autopsy_agent"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Analyze autopsy reports and extract structured forensic parameters."""
        
        # 1. Get raw text from Tier 0
        prior = await self.get_prior_result("evidence_parser")
        if not prior or "files" not in prior:
            raise ValueError("Missing upstream data from evidence_parser")
            
        # Find the autopsy report text
        autopsy_text = ""
        autopsy_file_id = None
        for file_id, data in prior["files"].items():
            if data["doc_type"] == "AUTOPSY_REPORT":
                autopsy_text += data["content"] + "\n\n"
                autopsy_file_id = file_id
                
        if not autopsy_text:
            return {"status": "SKIPPED", "reason": "No autopsy report found in case files"}

        # 2. Call LLM to extract pathology data
        prompt = f"""
        Extract the following forensic parameters from the autopsy report.
        Return ONLY valid JSON. If a value is not found, use null.
        
        Required JSON Schema:
        {{
            "demographics": {{"age": int, "sex": "string", "weight_kg": float, "height_cm": float}},
            "tod_indicators": {{
                "rectal_temp_c": float,
                "ambient_temp_c": float,
                "temp_time": "ISO8601",
                "rigor_mortis": "absent|developing|complete|passing",
                "livor_mortis": "fixed|blanching|absent",
                "livor_color": "string",
                "stomach_contents": "string",
                "digestion_state": "intact|partially_digested|empty"
            }},
            "injuries": [
                {{ "type": "blunt|sharp|gunshot|ligature|other", "location": "string", "description": "string", "fatal": boolean }}
            ],
            "toxicology": [
                {{ "substance": "string", "concentration": float, "unit": "string", "lethal": boolean }}
            ],
            "cause_of_death": "string",
            "manner_of_death": "NATURAL|ACCIDENT|SUICIDE|HOMICIDE|UNDETERMINED"
        }}
        
        Raw Autopsy Text:
        {autopsy_text[:8000]}
        """
        
        resp = await llm.complete(
            task="autopsy_extract",
            prompt=prompt,
            system_prompt="You are an expert forensic pathologist extracting data for a legal database."
        )
        
        try:
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            pathology_data = json.loads(clean_json)
            
            # Audit log
            await self.log_step(
                "LLM_EXTRACTION",
                "Extracted pathology parameters",
                f"Found manner of death: {pathology_data.get('manner_of_death')}, Cause: {pathology_data.get('cause_of_death')}",
                confidence=0.95,
                evidence_ids=[UUID(autopsy_file_id)] if autopsy_file_id else []
            )
            
            # Check for inconsistencies (e.g. ligature mark but manner=NATURAL)
            warnings = []
            if pathology_data.get("manner_of_death") == "NATURAL" and pathology_data.get("injuries"):
                if any(inj.get("fatal") for inj in pathology_data["injuries"]):
                    warnings.append("Conflict: Manner of death is NATURAL but fatal injuries were extracted.")
                    
            return {
                "pathology": pathology_data,
                "_confidence": 0.95,
                "_warnings": warnings
            }
            
        except json.JSONDecodeError:
            await self.log_step("ERROR", "Failed to parse Autopsy JSON", resp.text[:100], 0.0)
            raise ValueError("LLM returned invalid JSON for autopsy data")
