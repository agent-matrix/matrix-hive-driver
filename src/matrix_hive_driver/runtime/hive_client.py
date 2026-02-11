from __future__ import annotations

from typing import Any

import requests

from matrix_hive_driver.driver.config import settings
from matrix_hive_driver.driver.errors import DriverRuntimeError


class HiveClient:
    """Thin HTTP client to a Hive Runtime service.

    Expected endpoints (adapt to your Hive runtime exposure):
      POST /runs           -> {run_id: "..."}
      GET  /runs/{id}      -> status payload
      GET  /runs/{id}/events -> {events:[...]}
      POST /runs/{id}/cancel
    """

    def start(self, graph: dict[str, Any], metadata: dict[str, Any]) -> str:
        url = f"{settings.hive_endpoint.rstrip('/')}/runs"
        payload = {"graph": graph, "metadata": metadata}
        try:
            r = requests.post(url, json=payload, timeout=30)
            if r.status_code >= 400:
                raise DriverRuntimeError(f"Hive start failed {r.status_code}: {r.text[:500]}")
            data = r.json()
            return str(data.get("run_id"))
        except requests.RequestException as e:
            raise DriverRuntimeError(f"Hive request failed: {e}") from e

    def status(self, run_id: str) -> dict[str, Any]:
        url = f"{settings.hive_endpoint.rstrip('/')}/runs/{run_id}"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code >= 400:
                raise DriverRuntimeError(f"Hive status failed {r.status_code}: {r.text[:500]}")
            return r.json()
        except requests.RequestException as e:
            raise DriverRuntimeError(f"Hive request failed: {e}") from e

    def events(self, run_id: str) -> list[dict[str, Any]]:
        url = f"{settings.hive_endpoint.rstrip('/')}/runs/{run_id}/events"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code >= 400:
                raise DriverRuntimeError(f"Hive events failed {r.status_code}: {r.text[:500]}")
            return list(r.json().get("events", []))
        except requests.RequestException as e:
            raise DriverRuntimeError(f"Hive request failed: {e}") from e

    def cancel(self, run_id: str) -> None:
        url = f"{settings.hive_endpoint.rstrip('/')}/runs/{run_id}/cancel"
        try:
            r = requests.post(url, timeout=20)
            if r.status_code >= 400:
                raise DriverRuntimeError(f"Hive cancel failed {r.status_code}: {r.text[:500]}")
        except requests.RequestException as e:
            raise DriverRuntimeError(f"Hive request failed: {e}") from e
