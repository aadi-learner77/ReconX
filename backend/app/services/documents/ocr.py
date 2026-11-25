import csv
import io
from dataclasses import dataclass
from typing import Any

import openpyxl
import pymupdf

_rapidocr_engine: Any = None


def _get_rapidocr() -> Any:
    global _rapidocr_engine
    if _rapidocr_engine is None:
        from rapidocr import RapidOCR

        _rapidocr_engine = RapidOCR()
    return _rapidocr_engine


@dataclass(frozen=True)
class OCRTextBlock:
    page: int
    text: str
    bbox: dict[str, float] | None
    method: str  # pymupdf_text | rapidocr | openpyxl | csv_parser
    confidence: float


def extract_document_blocks(content: bytes, mime_type: str) -> list[OCRTextBlock]:
    """Extract text with page & bbox provenance: PyMuPDF first, RapidOCR fallback for scans."""
    if mime_type == "application/pdf":
        blocks: list[OCRTextBlock] = []
        doc = pymupdf.open(stream=content, filetype="pdf")
        try:
            for page_idx in range(doc.page_count):
                page = doc[page_idx]
                page_num = page_idx + 1
                text = page.get_text("text").strip()
                if text:
                    for ln in page.get_text("blocks"):
                        x0, y0, x1, y1, block_text, *_ = ln
                        cleaned = str(block_text).strip()
                        if cleaned:
                            blocks.append(
                                OCRTextBlock(
                                    page=page_num,
                                    text=cleaned,
                                bbox={
                                    "x0": float(x0),
                                    "y0": float(y0),
                                    "x1": float(x1),
                                    "y1": float(y1),
                                },
                                    method="pymupdf_text",
                                    confidence=0.97,
                                )
                            )
                else:
                    # Rasterize scanned PDF page and run RapidOCR
                    pix = page.get_pixmap(dpi=180)
                    img_bytes = pix.tobytes("png")
                    blocks.extend(_run_rapidocr_on_image(img_bytes, page=page_num))
        finally:
            doc.close()
        return blocks

    if mime_type in {"image/png", "image/jpeg"}:
        return _run_rapidocr_on_image(content, page=1)

    if mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
        blocks = []
        try:
            for s_idx, sheet in enumerate(wb.worksheets, start=1):
                lines: list[str] = []
                for row in sheet.iter_rows(values_only=True):
                    vals = [str(c).strip() if c is not None else "" for c in row]
                    if any(vals):
                        lines.append(" | ".join(vals))
                if lines:
                    blocks.append(
                        OCRTextBlock(
                            page=s_idx,
                            text="\n".join(lines),
                            bbox=None,
                            method="openpyxl",
                            confidence=0.98,
                        )
                    )
        finally:
            wb.close()
        return blocks

    if mime_type == "text/csv":
        decoded = content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(decoded))
        lines = [" | ".join(cell.strip() for cell in row) for row in reader if any(row)]
        return [
            OCRTextBlock(
                page=1,
                text="\n".join(lines),
                bbox=None,
                method="csv_parser",
                confidence=0.98,
            )
        ]

    return []


def _run_rapidocr_on_image(img_bytes: bytes, page: int) -> list[OCRTextBlock]:
    ocr = _get_rapidocr()
    result = ocr(img_bytes)
    blocks: list[OCRTextBlock] = []
    # RapidOCR >=3.0 returns RapidOCROutput (.boxes, .txts, .scores); older returns list of tuples
    boxes = getattr(result, "boxes", None)
    txts = getattr(result, "txts", None)
    scores = getattr(result, "scores", None)
    if txts is not None:
        for idx, txt in enumerate(txts):
            score = float(scores[idx]) if scores is not None and idx < len(scores) else 0.75
            bbox = None
            if boxes is not None and idx < len(boxes) and len(boxes[idx]) >= 4:
                pts = boxes[idx]
                xs = [float(p[0]) for p in pts]
                ys = [float(p[1]) for p in pts]
                bbox = {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)}
            if str(txt).strip():
                blocks.append(
                    OCRTextBlock(
                        page=page,
                        text=str(txt).strip(),
                        bbox=bbox,
                        method="rapidocr",
                        confidence=max(0.0, min(1.0, score)),
                    )
                )
    elif isinstance(result, (list, tuple)):
        for item in result:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                pts, txt, score = item[0], item[1], item[2]
                xs = [float(p[0]) for p in pts]
                ys = [float(p[1]) for p in pts]
                blocks.append(
                    OCRTextBlock(
                        page=page,
                        text=str(txt).strip(),
                        bbox={"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)},
                        method="rapidocr",
                        confidence=max(0.0, min(1.0, float(score))),
                    )
                )
    return blocks
