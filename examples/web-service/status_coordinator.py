"""status_coordinator.py — Domain Coordinator 계층.

허용 책임: 요청 정규화, 라우팅, 오류 정규화, 결과 봉투 조합.
전역 오케스트레이터가 아니다. status 도메인만 담당한다.
"""
from __future__ import annotations

import time

from contracts import fail_result, make_error, ok_result
from status_service import StatusService


class StatusCoordinator:
    CAPABILITY = "status"

    def __init__(self, service: StatusService):
        self._service = service

    def handle(self, request: dict) -> dict:
        started = time.monotonic()

        def _elapsed_ms() -> int:
            return int((time.monotonic() - started) * 1000)

        trace_id = request.get("trace_id", "")
        if request.get("capability") != self.CAPABILITY:
            return fail_result(request, make_error(
                "SVC-CONTRACT-CAPABILITY-400", "contract", trace_id=trace_id,
                retryable=False, user_message="지원하지 않는 요청입니다.",
                source="coordinator.status",
                details={"capability": str(request.get("capability"))},
            ), duration_ms=_elapsed_ms())

        operation = request.get("operation")
        try:
            if operation == "health":
                data = self._service.health()
                return ok_result(request, data, source="adapter.system",
                                 duration_ms=_elapsed_ms())
            return fail_result(request, make_error(
                "SVC-CONTRACT-OPERATION-404", "contract", trace_id=trace_id,
                retryable=False, user_message="지원하지 않는 동작입니다.",
                source="coordinator.status", details={"operation": str(operation)},
            ), duration_ms=_elapsed_ms())
        except OSError as exc:
            return fail_result(request, make_error(
                "SVC-PROVIDER-RUNTIME-500", "provider", trace_id=trace_id,
                retryable=True, user_message="상태 정보를 가져올 수 없습니다.",
                source="adapter.system", details={"reason": type(exc).__name__},
            ), duration_ms=_elapsed_ms())
