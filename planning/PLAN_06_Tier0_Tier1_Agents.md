# PLAN 06 — Tier 0 & Tier 1 Agents (Ingestion & Normalization)
**Owner:** Dev A | **Hour:** 4:00–5:00 | **Priority:** CRITICAL

---

## 1. Objective
Implement the foundational ingestion layer.
- **Evidence Parser (T0):** Identifies uploaded files, determines if they are text or scanned PDFs.
- **OCR Agent (T0):** Converts scanned PDFs to raw text using PyTesseract.
- **Format Normalizer (T1):** Takes raw text from parser/OCR, masks PII (phones, names, emails) using RegEx, and structures the text for downstream agents.

---

## 2. Evidence Parser (M-01)

**File: `services/agents/evidence_parser/agent.py`**

```python
import fitz  # PyMuPDF
from services.base_agent import BaseAgent, AgentTask, AgentResult
from services.database import db
from services.minio_client import storage

class EvidenceParserAgent(BaseAgent):
    agent_id = "evidence_parser"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        self.log_step(task, "DATA_NORMALIZATION", "Starting evidence parsing", "Fetching file list", confidence=1.0)
        
        # Get all files for this case
        files = await db.fetch("SELECT * FROM case_files WHERE case_id=$1", task.case_id)
        if not files:
            return AgentResult(data={"parsed_files": []}, warnings=["No files found for case"])
            
        parsed_files = []
        for file in files:
            file_data = storage.download_file(file["s3_key"])
            
            is_scanned = False
            raw_text = ""
            
            # Simple PDF heuristic: if PyMuPDF finds < 50 chars of text, assume it's scanned
            if file["original_name"].lower().endswith('.pdf'):
                try:
                    doc = fitz.open(stream=file_data, filetype="pdf")
                    for page in doc:
                        raw_text += page.get_text()
                    if len(raw_text.strip()) < 50:
                        is_scanned = True
                        raw_text = ""  # Let OCR handle it
                except Exception as e:
                    self.log_step(task, "ERROR", f"Failed to parse PDF {file['file_id']}", str(e), confidence=0.0)
            else:
                # E.g. CSVs, plain text
                try:
                    raw_text = file_data.decode("utf-8")
                except UnicodeDecodeError:
                    is_scanned = True # Could be an image
            
            parsed_files.append({
                "file_id": str(file["file_id"]),
                "doc_type": file["doc_type"],
                "is_scanned": is_scanned,
                "raw_text": raw_text[:50000] # Limit size for safety
            })
            
            self.log_step(task, "DATA_NORMALIZATION", 
                          f"Parsed file {file['original_name']}", 
                          f"Type: {file['doc_type']}, Scanned: {is_scanned}", 
                          confidence=0.9, evidence_ids=[file["file_id"]])
            
        return AgentResult(data={"parsed_files": parsed_files})
```

---

## 3. OCR Agent (M-02)

**File: `services/agents/ocr/agent.py`**

```python
import fitz
import pytesseract
from PIL import Image
import io
from services.base_agent import BaseAgent, AgentTask, AgentResult
from services.database import db
from services.minio_client import storage

class OCRAgent(BaseAgent):
    agent_id = "ocr"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        # T0 runs parallel to Parser, so we just OCR all files that look like images/scanned PDFs
        files = await db.fetch("SELECT * FROM case_files WHERE case_id=$1", task.case_id)
        
        ocr_results = {}
        for file in files:
            # For MVP, we run OCR if mime_type is image or if it's a PDF.
            # In a real system we'd wait for Parser to flag `is_scanned`. But since they are parallel,
            # we just process images directly.
            if "image" in file["mime_type"]:
                file_data = storage.download_file(file["s3_key"])
                img = Image.open(io.BytesIO(file_data))
                text = pytesseract.image_to_string(img)
                ocr_results[str(file["file_id"])] = text
                
                self.log_step(task, "DATA_NORMALIZATION", 
                              f"OCR performed on {file['original_name']}", 
                              f"Extracted {len(text)} chars", 
                              confidence=0.8, evidence_ids=[file["file_id"]])
                              
        return AgentResult(data={"ocr_results": ocr_results})
```

---

## 4. Format Normalizer Agent (M-03)

**File: `services/agents/format_normalizer/agent.py`**

```python
import re
from services.base_agent import BaseAgent, AgentTask, AgentResult

class FormatNormalizerAgent(BaseAgent):
    agent_id = "format_normalizer"
    
    async def execute(self, task: AgentTask) -> AgentResult:
        # Tier 1: Depends on Parser and OCR
        parser_data = await self.get_prior_result(task, "evidence_parser")
        ocr_data = await self.get_prior_result(task, "ocr") or {"ocr_results": {}}
        
        if not parser_data:
            return AgentResult(data={}, warnings=["No parser data found"])
            
        normalized_files = []
        for pf in parser_data.get("parsed_files", []):
            file_id = pf["file_id"]
            
            # Merge OCR text if applicable
            text = pf["raw_text"]
            if pf["is_scanned"] and file_id in ocr_data.get("ocr_results", {}):
                text = ocr_data["ocr_results"][file_id]
                
            # Basic PII Masking (MVP)
            # Mask phone numbers: \b\d{10}\b
            masked_text = re.sub(r'\b\d{10}\b', '[PHONE_MASKED]', text)
            # Mask basic emails
            masked_text = re.sub(r'\S+@\S+\.\S+', '[EMAIL_MASKED]', masked_text)
            
            pf["normalized_text"] = masked_text
            normalized_files.append(pf)
            
            self.log_step(task, "DATA_NORMALIZATION", 
                          f"Normalized {file_id}", 
                          "Merged OCR and applied PII masking", 
                          confidence=0.95, evidence_ids=[file_id])
                          
        return AgentResult(data={"normalized_files": normalized_files})
```

## Acceptance Criteria
- [ ] PyMuPDF reads text from standard PDFs.
- [ ] PyTesseract reads text from images.
- [ ] Normalizer correctly combines outputs and replaces 10-digit numbers with `[PHONE_MASKED]`.
