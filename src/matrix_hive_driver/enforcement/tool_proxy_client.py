from __future__ import annotations

from typing import Any

import requests

from matrix_hive_driver.driver.config import settings
from matrix_hive_driver.driver.errors import DriverRuntimeError


class ToolProxyClient:
    """Client for Matrix Architect's controlled tool proxy (or Guardian-gated gateway).

    All effectful tool calls from Hive must go through this proxy —
    never directly to external services.
    """

    def invoke(self, tool: str, args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        payload = {"tool": tool, "args": args, "context": context}
        try:
            r = requests.post(settings.tool_proxy_endpoint, json=payload, timeout=120)
            if r.status_code >= 400:
                raise DriverRuntimeError(f"Tool proxy error {r.status_code}: {r.text[:500]}")
            return r.json()
        except requests.RequestException as e:
            raise DriverRuntimeError(f"Tool proxy request failed: {e}") from e
