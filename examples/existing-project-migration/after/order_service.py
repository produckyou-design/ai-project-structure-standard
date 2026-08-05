"""order_service.py — Domain Service / Use Case 계층.

도메인 규칙(주문 ID 형식 검증)만 담당한다. 외부 API 접근은 Adapter 를 통해서만 한다.
"""
from __future__ import annotations

from order_api_adapter import OrderApiAdapter


class OrderValidationError(ValueError):
    """도메인 규칙 위반. Coordinator 가 표준 오류로 정규화한다."""


class OrderService:
    def __init__(self, adapter: OrderApiAdapter):
        self._adapter = adapter

    def get_status(self, order_id: str) -> str:
        order_id = order_id.strip()
        if not order_id:
            raise OrderValidationError("주문 ID 가 비어 있습니다")
        return self._adapter.fetch_status(order_id)
