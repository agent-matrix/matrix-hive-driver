from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ArtifactRef:
    type: str
    uri: str
    sha256: str
    created_at: str
    metadata: dict[str, Any]
