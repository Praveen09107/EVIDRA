"""
EVIDRA — Evidence Parser (Tier 0 / M-01).

Implements Core Agent Specs §M-01 and PLAN_06:
- Loads raw evidence from MinIO
- Detects text vs scanned PDFs using PyMuPDF
- Extracts raw text/bytes for downstream agents
- Computes SHA-256 file hashes for integrity
"""
import hashlib
import logging
from uuid import UUID
from agents.base import BaseAgent
from core.storage import storage
from core.database import db

logger = logging.getLogger("evidra.parser")


class EvidenceParser(BaseAgent):
    agent_id = "evidence_parser"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Fetch all case files from MinIO and extract base data."""

        files = await self.get_case_files()

        if not files:
            return {"files": {}, "_warnings": ["No files found for case"], "_confidence": 1.0}

        parsed_data = {}

        for f in files:
            file_id = str(f["file_id"])
            doc_type = f["doc_type"]
            s3_key = f["s3_key"]
            original_name = f.get("original_name", "unknown")

            # Download from MinIO
            try:
                raw_bytes = storage.download_file(s3_key)
            except Exception as e:
                logger.error(f"Failed to download {s3_key}: {e}")
                await self.log_step("ERROR", f"Download failed: {original_name}", str(e), 0.0)
                continue

            # Compute hash for integrity
            file_hash = hashlib.sha256(raw_bytes).hexdigest()

            text_content = ""
            is_scanned = False

            # PDF handling with PyMuPDF
            if original_name.lower().endswith(".pdf"):
                try:
                    import fitz
                    doc = fitz.open(stream=raw_bytes, filetype="pdf")
                    for page in doc:
                        text_content += page.get_text() + "\n"
                    doc.close()

                    # If very little text extracted, it's probably scanned
                    if len(text_content.strip()) < 50:
                        is_scanned = True
                        text_content = ""  # Let OCR agent handle it
                        logger.info(f"PDF {original_name} appears scanned (<50 chars extracted)")
                except ImportError:
                    logger.warning("PyMuPDF not installed — falling back to UTF-8 decode")
                    try:
                        text_content = raw_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        is_scanned = True
                except Exception as e:
                    logger.warning(f"PyMuPDF failed for {original_name}: {e}")
                    is_scanned = True

            # Image files → mark for OCR
            elif any(original_name.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]):
                is_scanned = True
                text_content = f"<IMAGE: {len(raw_bytes)} bytes>"

            # Text/CSV/JSON files
            else:
                try:
                    text_content = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    is_scanned = True
                    text_content = f"<BINARY DATA: {len(raw_bytes)} bytes>"

            # Cap text size for safety
            text_content = text_content[:100000]

            parsed_data[file_id] = {
                "doc_type": doc_type,
                "original_name": original_name,
                "content": text_content,
                "is_scanned": is_scanned,
                "size_bytes": len(raw_bytes),
                "sha256": file_hash,
            }

            await self.log_step(
                "DATA_NORMALIZATION",
                f"Parsed {original_name} ({doc_type})",
                f"Extracted {len(text_content)} chars. Scanned: {is_scanned}. Hash: {file_hash[:16]}...",
                confidence=0.95 if not is_scanned else 0.70,
                evidence_ids=[f["file_id"]],
            )

        return {"files": parsed_data, "_confidence": 1.0}
