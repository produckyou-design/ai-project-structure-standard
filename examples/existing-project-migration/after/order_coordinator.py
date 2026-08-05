"""order_coordinator.py — Domain Coordinator 계층.

허용 책임: 요청 정규화, 라우팅, 캐시 정책(상태의 단일 소유자), 오류 정규화, 결과 봉투 조합.
금지: 외부 API 접근, 파싱, 도메인 규칙 — Adapter/Service 의 책임이다.

`before/app.py` 는 캐시를 두 곳(_ui_status_cache, _recent_lookups)에 나눠 가졌다.
여기서는 이 Coordinator 하나만 조회 상태를 캐시한다 (단일 소유자).
전역 오케스트레이터가 아니다. order 도메인만 담당한다.
"""
from __future__ import annotations

import time

from contracts import fail_result, make_error, ok_result
from order_api_adapter import OrderNotFoundError
from order_service import OrderService, OrderValidationError


class OrderCoordinator:
    CAPABILITY = "order"

    def __init__(self, service: OrderService):
        self._service = service
        self._status_cache: dict[str, str] = {}  # 상태의 단일 소유자 (중복 보관 없음)

    def handle(self, request: dict) -> dict:
        """표준 요청을 받아 표준 결과 봉투로 반환한다. 예외를 밖으로 흘리지 않는다."""
        started = time.monotonic()

        def _elapsed_ms() -> int:
            return int((time.monotonic() - started) * 1000)

        trace_id = request.get("trace_id", "")
        if request.get("capability") != self.CAPABILITY:
            return fail_result(request, make_error(
                "ORDER-CONTRACT-CAPABILITY-400", "contract", trace_id=trace_id,
                retryable=False, user_message="지원하지 않는 요청입니다.",
                source="coordinator.order",
                details={"capability": str(request.get("capability"))},
            ), duration_ms=_elapsed_ms())

        operation = request.get("operation")
        if operation != "get_status":
            return fail_result(request, make_error(
                "ORDER-CONTRACT-OPERATION-400", "contract", trace_id=trace_id,
                retryable=False, user_message="지원하지 않는 동작입니다.",
                source="coordinator.order", details={"operation": str(operation)},
            ), duration_ms=_elapsed_ms())

        order_id = str(request.get("parameters", {}).get("order_id", ""))
        if order_id in self._status_cache:
            return ok_result(request, {"order_id": order_id, "status": self._status_cache[order_id]},
                             source="cache", duration_ms=_elapsed_ms())

        try:
            status = self._service.get_status(order_id)
        except OrderValidationError as exc:
            # 실패 원인을 구분해 표준 오류로 정규화한다 (오류를 삼키지 않는다).
            return fail_result(request, make_error(
                "ORDER-PARSING-VALIDATION-422", "parsing", trace_id=trace_id,
                retryable=False, user_message=str(exc), source="coordinator.order",
            ), duration_ms=_elapsed_ms())
        except OrderNotFoundError as exc:
            missing_id = exc.args[0] if exc.args else order_id
            return fail_result(request, make_error(
                "ORDER-PROVIDER-NOTFOUND-404", "provider", trace_id=trace_id,
                retryable=False, user_message="주문을 찾을 수 없습니다.",
                source="adapter.order_api", details={"order_id": str(missing_id)},
            ), duration_ms=_elapsed_ms())

        self._status_cache[order_id] = status
        return ok_result(request, {"order_id": order_id, "status": status},
                         source="adapter.order_api", duration_ms=_elapsed_ms())
