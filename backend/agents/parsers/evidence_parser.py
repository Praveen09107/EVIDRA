"""
EVIDRA — Evidence Parser (Tier 0).

Loads raw evidence from MinIO based on the case_id.
Extracts raw text/bytes and stores them in agent_results so downstream agents can access them.
"""
from uuid import UUID
from agents.base import BaseAgent
from core.storage import storage

class EvidenceParser(BaseAgent):
    agent_id = "evidence_parser"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Fetch all case files from MinIO and extract base data."""
        
        # 1. Get all pending files for this case
        files = await self.get_case_files()
        
        parsed_data = {}
        for f in files:
            file_id = str(f["file_id"])
            doc_type = f["doc_type"]
            s3_key = f["s3_key"]
            
            # 2. Download from MinIO
            raw_bytes = storage.download_file(s3_key)
            
            # 3. Simple parse (for hackathon, we assume UTF-8 text/CSV/JSON)
            # In production, use pdfplumber, tesseract, etc.
            try:
                text_content = raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                text_content = f"<BINARY DATA: {len(raw_bytes)} bytes>"
                
            parsed_data[file_id] = {
                "doc_type": doc_type,
                "original_name": f["original_name"],
                "content": text_content
            }
            
            await self.log_step(
                "DATA_NORMALIZATION",
                f"Parsed {f['original_name']} ({doc_type})",
                f"Extracted {len(text_content)} characters",
                confidence=1.0,
                evidence_ids=[f["file_id"]]
            )

        return {"files": parsed_data, "_confidence": 1.0}
