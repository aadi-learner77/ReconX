import hashlib
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class StorageAdapter:
    """Local-disk storage adapter storing immutable uploads outside web roots using UUID keys."""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        settings = get_settings()
        self.root = Path(root_dir or settings.storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, content: bytes, extension: str) -> tuple[str, str]:
        safe_ext = extension.lower().lstrip(".")
        storage_key = f"{uuid4().hex}.{safe_ext}"
        target = (self.root / storage_key).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError("Resolved storage path escapes storage root")
        target.write_bytes(content)
        checksum = hashlib.sha256(content).hexdigest()
        return storage_key, checksum

    def read_bytes(self, storage_key: str) -> bytes:
        target = (self.root / Path(storage_key).name).resolve()
        if not str(target).startswith(str(self.root)) or not target.exists():
            raise FileNotFoundError(f"Stored file missing for key {storage_key}")
        return target.read_bytes()

    def resolve_path(self, storage_key: str) -> Path:
        target = (self.root / Path(storage_key).name).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError("Invalid storage key")
        return target
