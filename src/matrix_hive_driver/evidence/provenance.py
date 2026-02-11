from __future__ import annotations

from typing import Any


def build_provenance(metadata: dict[str, Any]) -> dict[str, Any]:
    """Build provenance metadata for an execution.

    Placeholder: enrich with git SHA, image digests, policy/budget IDs, etc.
    """
    return {"metadata": metadata}
