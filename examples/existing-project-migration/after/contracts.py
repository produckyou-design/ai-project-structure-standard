"""contracts.py — 표준 요청·결과·오류 계약 생성 헬퍼.

`schemas/{request,result,error}.schema.json` 과 필드가 일치한다.
예제는 독립 배포 단위이므로 `examples/python-desktop`, `examples/web-service` 와
동일한 헬퍼를 이 디렉터리에도 각각 보유한다 (재사용은 하되 중복 소유는 각 예제 안에서 닫는다).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

CONTRACT_VERSION = "1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_trace_id() -> str:
    """Entry Layer 에서 1회 발급. 재시도해도 유지한다."""
    return f"trace-{uuid.uuid4().hex[:12]}"


def make_request(capability: str, operation: str, parameters: dict | None = None,
                 *, trace_id: str, caller: str = "", timeout_ms: int = 3000) -> dict:
    """요청 계약 생성. request_id 는 매 요청 새로 발급한다."""
    return {
        "request_id": f"req-{uuid.uuid4().hex[:12]}",
        "trace_id": trace_id,
        "capability": capability,
        "operation": operation,
        "parameters": parameters or {},
        "caller": caller,
        "priority": "normal",
        "timeout_ms": timeout_ms,
        "created_at": _now(),
        "contract_version": CONTRACT_VERSION,
    }


def ok_result(request: dict, data, *, source: str, duration_ms: int = 0,
              is_stale: bool = False) -> dict:
    return {
        "success": True,
        "data": data,
        "error": None,
        "source": source,
        "fetched_at": _now(),
        "is_stale": is_stale,
        "trace_id": request["trace_id"],
        "duration_ms": duration_ms,
        "contract_version": CONTRACT_VERSION,
    }


def fail_result(request: dict, error: dict, *, duration_ms: int = 0) -> dict:
    return {
        "success": False,
        "data": None,
        "error": error,
        "source": error.get("source", ""),
        "fetched_at": _now(),
        "is_stale": False,
        "trace_id": request["trace_id"],
        "duration_ms": duration_ms,
        "contract_version": CONTRACT_VERSION,
    }


def make_error(code: str, category: str, *, trace_id: str, retryable: bool,
               user_message: str = "", source: str = "", details: dict | None = None) -> dict:
    """오류 계약 생성. code 는 실패의 종류, trace_id 는 개별 사건이다."""
    return {
        "code": code,
        "trace_id": trace_id,
        "category": category,
        "user_message": user_message,
        "retryable": retryable,
        "source": source,
        "details": details or {},
        "occurred_at": _now(),
    }
