"""
EVIDRA — OCR Agent (Tier 0 / M-02).

Implements Core Agent Specs §M-02:
- Tesseract OCR with per-document-type configurations
- Image preprocessing (grayscale, denoise, deskew, adaptive threshold)
- Confidence scoring with thresholds
- LLM correction pass for low-confidence OCR
"""
import io
import logging
import numpy as np
from uuid import UUID
from typing import Optional
from agents.base import BaseAgent
from core.database import db
from core.storage import storage
from core.llm_gateway import llm

logger = logging.getLogger("evidra.ocr")

# ═══════════════════════════════════════════════════════════
# Tesseract Config Map (spec §M-02)
# ═══════════════════════════════════════════════════════════

TESSERACT_CONFIGS = {
    "AUTOPSY_REPORT": {"lang": "eng", "oem": 3, "psm": 6, "config": "--dpi 300 -c preserve_interword_spaces=1"},
    "CDR": {"lang": "eng", "oem": 3, "psm": 6, "config": "--dpi 300"},
    "FINANCIAL_RECORDS": {"lang": "eng", "oem": 3, "psm": 6, "config": "--dpi 300"},
    "DEFAULT": {"lang": "eng", "oem": 3, "psm": 3, "config": "--dpi 300"},
}

CONFIDENCE_THRESHOLDS = {
    "ACCEPTABLE": 0.85,
    "MARGINAL": 0.75,
    "POOR": 0.60,
    "UNUSABLE": 0.40,
}

CORRECTION_PROMPTS = {
    "AUTOPSY_REPORT": """You are a forensic medical document OCR corrector.
Fix OCR errors in this autopsy report text. Rules:
1. Fix obvious misreads (e.g. "rigor rnortis" → "rigor mortis")
2. Fix medical terminology errors
3. Fix number/letter confusion (e.g. "l00" → "100")
4. Preserve all original meaning — do NOT add or remove facts
5. Return ONLY corrected text, no commentary

===DOCUMENT_START===
{ocr_text}
===DOCUMENT_END===""",

    "CDR": """You are a telecom data OCR corrector.
Fix OCR errors in this Call Detail Record. Rules:
1. Phone numbers: 10 digits — fix letter/number confusion
2. Dates: fix format errors preserving the original date
3. Preserve table structure
4. Return ONLY corrected text

===DOCUMENT_START===
{ocr_text}
===DOCUMENT_END===""",

    "FINANCIAL_RECORDS": """You are a financial document OCR corrector.
Fix OCR errors in this bank statement. Rules:
1. Amounts: decimal numbers, fix misreads (e.g. "l,500.00" → "1,500.00")
2. Preserve column/row structure
3. Return ONLY corrected text

===DOCUMENT_START===
{ocr_text}
===DOCUMENT_END===""",
}


def preprocess_image(image_bytes: bytes) -> bytes:
    """OpenCV preprocessing: grayscale, denoise, deskew, adaptive threshold."""
    try:
        import cv2
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

        # Deskew
        coords = np.column_stack(np.where(denoised < 128))
        if len(coords) > 100:
            angle = cv2.minAreaRect(coords)[-1]
            angle = -(90 + angle) if angle < -45 else -angle
            if abs(angle) > 0.5:
                h, w = denoised.shape[:2]
                M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
                denoised = cv2.warpAffine(denoised, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        # Adaptive threshold
        binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        _, buffer = cv2.imencode(".png", binary)
        return buffer.tobytes()
    except ImportError:
        logger.warning("OpenCV not installed — skipping image preprocessing")
        return image_bytes
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        return image_bytes


def run_tesseract(image_bytes: bytes, doc_type: str) -> tuple[str, float]:
    """Run Tesseract OCR and return (text, confidence)."""
    try:
        import pytesseract
        from PIL import Image

        config = TESSERACT_CONFIGS.get(doc_type, TESSERACT_CONFIGS["DEFAULT"])
        img = Image.open(io.BytesIO(image_bytes))

        # Get text
        text = pytesseract.image_to_string(img, lang=config["lang"], config=config["config"])

        # Get confidence via word-level data
        data = pytesseract.image_to_data(img, lang=config["lang"], config=config["config"], output_type=pytesseract.Output.DICT)
        confidences = [int(c) for c in data["conf"] if c != "-1" and str(c).isdigit()]
        avg_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.5

        return text, avg_confidence
    except ImportError:
        logger.warning("pytesseract not installed — returning empty OCR")
        return "", 0.0
    except Exception as e:
        logger.warning(f"Tesseract OCR failed: {e}")
        return "", 0.0


class OcrAgent(BaseAgent):
    agent_id = "ocr"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Process all image/scanned files for a case through OCR pipeline."""

        files = await db.fetch(
            "SELECT * FROM case_files WHERE case_id=$1",
            case_id,
        )

        if not files:
            return {"status": "SKIPPED", "reason": "No files found"}

        ocr_results = {}
        total_warnings = []

        for f in files:
            mime = str(f.get("mime_type", ""))
            fname = str(f.get("original_name", ""))

            # Only OCR images and scanned PDFs
            is_image = "image" in mime
            is_pdf = fname.lower().endswith(".pdf")
            if not (is_image or is_pdf):
                continue

            doc_type = f["doc_type"]
            file_data = storage.download_file(f["s3_key"])

            pages_text = []
            pages_confidence = []

            if is_image:
                # Single image
                preprocessed = preprocess_image(file_data)
                text, conf = run_tesseract(preprocessed, doc_type)
                pages_text.append(text)
                pages_confidence.append(conf)

            elif is_pdf:
                # Extract pages from PDF as images
                try:
                    import fitz
                    doc = fitz.open(stream=file_data, filetype="pdf")

                    # Check if PDF has text first
                    raw_text = ""
                    for page in doc:
                        raw_text += page.get_text()

                    if len(raw_text.strip()) > 50:
                        # Text-based PDF — no OCR needed
                        pages_text.append(raw_text)
                        pages_confidence.append(0.95)
                    else:
                        # Scanned PDF — render pages as images and OCR
                        for page_num in range(min(len(doc), 20)):  # Cap at 20 pages
                            pix = doc[page_num].get_pixmap(dpi=300)
                            img_bytes = pix.tobytes("png")
                            preprocessed = preprocess_image(img_bytes)
                            text, conf = run_tesseract(preprocessed, doc_type)
                            pages_text.append(text)
                            pages_confidence.append(conf)
                    doc.close()
                except ImportError:
                    logger.warning("PyMuPDF not installed — skipping PDF OCR")
                    pages_text.append("")
                    pages_confidence.append(0.0)

            # Aggregate
            full_text = "\n\n".join(pages_text)
            avg_conf = sum(pages_confidence) / len(pages_confidence) if pages_confidence else 0.0
            word_count = len(full_text.split())

            # Warnings
            warnings = []
            if avg_conf < CONFIDENCE_THRESHOLDS["UNUSABLE"]:
                warnings.append("LOW_OCR_CONFIDENCE")
            if word_count == 0:
                warnings.append("BLANK_PAGE_DETECTED")

            # LLM Correction pass if needed (spec §M-02)
            corrected_text = full_text
            llm_correction_applied = False

            if avg_conf < CONFIDENCE_THRESHOLDS["MARGINAL"] and full_text.strip():
                correction_prompt = CORRECTION_PROMPTS.get(doc_type, CORRECTION_PROMPTS.get("AUTOPSY_REPORT", ""))
                if correction_prompt:
                    try:
                        resp = await llm.complete(
                            task="general",
                            prompt=correction_prompt.format(ocr_text=full_text[:8000]),
                            system_prompt="You are a document OCR error corrector.",
                        )
                        corrected_text = resp.text
                        llm_correction_applied = True
                        warnings.append("LLM_OCR_CORRECTION_APPLIED")
                    except Exception as e:
                        logger.warning(f"LLM OCR correction failed: {e}")

            ocr_results[str(f["file_id"])] = {
                "full_text_raw": full_text,
                "full_text_corrected": corrected_text,
                "page_count": len(pages_text),
                "avg_confidence": round(avg_conf, 3),
                "word_count": word_count,
                "llm_correction_applied": llm_correction_applied,
                "warnings": warnings,
            }
            total_warnings.extend(warnings)

            await self.log_step(
                "DATA_NORMALIZATION",
                f"OCR: {fname}",
                f"Confidence: {avg_conf:.2f}, Words: {word_count}, LLM corrected: {llm_correction_applied}",
                confidence=avg_conf,
                evidence_ids=[f["file_id"]],
                warnings=warnings,
            )

        return {
            "ocr_results": ocr_results,
            "files_processed": len(ocr_results),
            "_warnings": total_warnings,
            "_confidence": 0.85,
        }
