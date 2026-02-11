from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@dataclass
class EvidenceBundle:
    run_id: str
    created_at: str
    events: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_bytes(self) -> bytes:
        return json.dumps(
            {
                "run_id": self.run_id,
                "created_at": self.created_at,
                "events": self.events,
                "summary": self.summary,
            },
            indent=2,
            sort_keys=True,
        ).encode("utf-8")


def build_evidence_bundle(
    run_id: str, hive_events: list[dict[str, Any]]
) -> tuple[EvidenceBundle, str]:
    created_at = datetime.now(timezone.utc).isoformat()
    summary = {"event_count": len(hive_events)}
    bundle = EvidenceBundle(
        run_id=run_id,
        created_at=created_at,
        events=hive_events,
        summary=summary,
    )
    digest = _sha256(bundle.to_bytes())
    return bundle, digest
