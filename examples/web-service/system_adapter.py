"""system_adapter.py — Adapter/Gateway 계층.

운영체제(외부 경계) 접근만 담당한다. 도메인 판단은 하지 않는다.
"""
from __future__ import annotations

import platform
import time

_STARTED_MONOTONIC = time.monotonic()


class SystemAdapter:
    """실행 환경 정보의 단일 소유자."""

    def runtime_info(self) -> dict:
        return {
            "python": platform.python_version(),
            "os": platform.system(),
        }

    def uptime_seconds(self) -> int:
        return int(time.monotonic() - _STARTED_MONOTONIC)
