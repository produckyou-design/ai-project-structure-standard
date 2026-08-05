"""status_service.py — Domain Service / Use Case 계층.

상태 판정 규칙만 담당한다. OS 접근은 Adapter 를 통해서만 한다.
"""
from __future__ import annotations

from system_adapter import SystemAdapter


class StatusService:
    def __init__(self, adapter: SystemAdapter):
        self._adapter = adapter

    def health(self) -> dict:
        info = self._adapter.runtime_info()
        uptime = self._adapter.uptime_seconds()
        return {
            "status": "ok",
            "uptime_seconds": uptime,
            "runtime": info,
        }
