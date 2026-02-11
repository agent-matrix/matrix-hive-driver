from __future__ import annotations

from typing import Any


def normalize_workspace(workspace: dict[str, Any]) -> dict[str, Any]:
    """Normalize and validate workspace configuration.

    In production, enforce:
    - allowed workdir base
    - container namespace/UID
    - read-only mounts where required
    """
    return dict(workspace or {})
