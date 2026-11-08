"""Shopping-list item photos — magic-byte sniffing and tiny file storage.

Pure helpers: no FastAPI, no config. Files are stored under a random name
(``<uuid hex>.<ext>``) so a stored name can never carry a path.
"""
import re
import uuid
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024
NAME_RE = re.compile(r"^[0-9a-f]{32}\.(jpg|png|gif|webp)$")


def sniff(data: bytes) -> str | None:
    """Return the file extension for JPEG/PNG/GIF/WebP bytes, else None."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def save(directory: Path, data: bytes, ext: str) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    tmp = directory / f"{name}.tmp"
    tmp.write_bytes(data)
    tmp.replace(directory / name)
    return name


def remove(directory: Path, name: str | None) -> None:
    if name and NAME_RE.fullmatch(name):
        (directory / name).unlink(missing_ok=True)
