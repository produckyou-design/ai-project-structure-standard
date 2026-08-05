"""order_api_adapter.py — Adapter 계층.

외부 주문 API 접근의 단일 소유자. `before/app.py` 에서는 UI 함수가 이 접근을
직접 했지만, 여기서는 Adapter 하나만 이 책임을 가진다.
도메인 규칙 판단은 하지 않는다. 저수준 실패는 언어 예외로 올리고
Coordinator 가 표준 오류로 정규화한다.

실제 네트워크는 쓰지 않는다 (README.md 참고: 외부 API 를 로컬 함수로 흉내낸다).
"""
from __future__ import annotations

_ORDER_BACKEND = {
    "A100": "SHIPPED",
    "A101": "PROCESSING",
    "A102": "DELIVERED",
}


class OrderNotFoundError(KeyError):
    """주문을 찾을 수 없음. Coordinator 가 표준 오류로 정규화한다."""


class OrderApiAdapter:
    """외부 주문 조회 API 접근의 단일 소유자 (Repository/Gateway 상당)."""

    def fetch_status(self, order_id: str) -> str:
        if order_id not in _ORDER_BACKEND:
            raise OrderNotFoundError(order_id)
        return _ORDER_BACKEND[order_id]
