import io
from pathlib import Path

import openpyxl
import pymupdf
from fastapi import status
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import AppError

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".csv"}
DANGEROUS_INNER_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".js", ".vbs", ".dll", ".php"}

MAGIC_MIME_MAP = {
    ".pdf": ("application/pdf",),
    ".png": ("image/png",),
    ".jpg": ("image/jpeg",),
    ".jpeg": ("image/jpeg",),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
    ".csv": ("text/csv",),
}


def detect_magic_mime(data: bytes, ext: str) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"PK\x03\x04"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if ext == ".csv":
        try:
            text = data.decode("utf-8")
            if "\x00" not in text and ("," in text or "\n" in text or len(text.strip()) > 0):
                return "text/csv"
        except UnicodeDecodeError:
            return None
    return None


def validate_uploaded_file(filename: str, content: bytes) -> tuple[str, str]:
    """Validate extension, double-extension, size limit, magic MIME, and integrity."""
    settings = get_settings()
    if not filename:
        raise AppError("INVALID_FILENAME", "Filename is required.", status.HTTP_400_BAD_REQUEST)

    lower_name = Path(filename).name.lower()
    suffixes = Path(lower_name).suffixes
    if not suffixes:
        raise AppError(
            "UNSUPPORTED_FILE_TYPE",
            "File has no extension.",
            status.HTTP_400_BAD_REQUEST,
        )
    if any(s in DANGEROUS_INNER_EXTENSIONS for s in suffixes[:-1]):
        raise AppError(
            "UNSAFE_FILE_NAME",
            "Suspicious double extension detected.",
            status.HTTP_400_BAD_REQUEST,
        )

    ext = suffixes[-1]
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(
            "UNSUPPORTED_FILE_TYPE",
            f"Unsupported file extension '{ext}'. Allowed: PDF, PNG, JPG/JPEG, XLSX, CSV.",
            status.HTTP_400_BAD_REQUEST,
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) == 0:
        raise AppError("CORRUPT_FILE", "Uploaded file is empty.", status.HTTP_400_BAD_REQUEST)
    if len(content) > max_bytes:
        raise AppError(
            "FILE_TOO_LARGE",
            f"File exceeds {settings.max_upload_size_mb} MB limit.",
            status.HTTP_413_CONTENT_TOO_LARGE,
        )

    detected_mime = detect_magic_mime(content, ext)
    expected_mimes = MAGIC_MIME_MAP[ext]
    if detected_mime not in expected_mimes:
        raise AppError(
            "MIME_MISMATCH",
            f"File content signature does not match extension '{ext}'.",
            status.HTTP_400_BAD_REQUEST,
        )

    # Structural integrity check so corrupt files fail cleanly on upload
    try:
        if ext == ".pdf":
            doc = pymupdf.open(stream=content, filetype="pdf")
            if doc.page_count < 1:
                raise ValueError("PDF has 0 pages")
            doc.close()
        elif ext in {".png", ".jpg", ".jpeg"}:
            with Image.open(io.BytesIO(content)) as img:
                img.verify()
        elif ext == ".xlsx":
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
            wb.close()
    except Exception as exc:
        raise AppError(
            "CORRUPT_FILE",
            f"Uploaded {ext} file is corrupted or unreadable.",
            status.HTTP_400_BAD_REQUEST,
        ) from exc

    return ext.lstrip("."), detected_mime
