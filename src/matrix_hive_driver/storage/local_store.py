from __future__ import annotations

from pathlib import Path

DATA_DIR = Path("data") / "artifacts"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def write_bytes(relpath: str, content: bytes) -> str:
    p = DATA_DIR / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return str(p.resolve())
