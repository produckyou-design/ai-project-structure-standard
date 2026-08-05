"""app.py — 나쁜 예 (migration 이전 상태).

이 파일은 `docs/MIGRATION_GUIDE.md` 와 `examples/existing-project-migration/README.md` 가
설명하는 "이전(before)" 상태를 보여주기 위한 의도적인 나쁜 예다.
실제 외부 네트워크는 쓰지 않는다 (`_fake_order_api` 가 로컬 함수로 흉내낸다).

드러나는 나쁜 패턴 3가지 (README.md 대조표와 함께 읽는다):

1. UI 함수가 외부 API 를 직접 호출한다 (Coordinator/Adapter 없이 바로 호출).
2. 같은 상태(주문 조회 결과)를 서로 다른 두 곳에 중복 보관한다.
3. 실패 원인을 구분하지 않고 조용히 삼킨 뒤 기본값으로 뭉갠다.

실행:
  python app.py
"""
from __future__ import annotations

import sys

# ---------------------------------------------------------------------------
# "외부 주문 API" 를 흉내내는 함수. 실제 프로젝트라면 이 자리에 HTTP 호출이
# 있었을 것이다. 이 예제는 외부 네트워크를 쓰지 않는다.
# ---------------------------------------------------------------------------
_ORDER_BACKEND = {
    "A100": "SHIPPED",
    "A101": "PROCESSING",
    "A102": "DELIVERED",
}


def _fake_order_api(order_id: str) -> str:
    """외부 주문 조회 API 호출을 흉내낸다 (네트워크 없음)."""
    if order_id not in _ORDER_BACKEND:
        raise KeyError(order_id)
    return _ORDER_BACKEND[order_id]


# ---------------------------------------------------------------------------
# 나쁜 패턴: 상태 중복 보관.
# "UI 캐시"(_ui_status_cache) 와 "최근 조회 기록"(_recent_lookups) 이라는
# 서로 다른 두 저장소가 같은 정보를 각자 들고 있다. 소유자가 둘로 나뉘면
# 한쪽만 갱신되었을 때 서로 어긋난다 (중앙화 원칙 위반).
# ---------------------------------------------------------------------------
_ui_status_cache: dict[str, str] = {}
_recent_lookups: list[str] = []


def get_order_status_for_display(order_id: str) -> str:
    """UI 계층 함수가 외부 API 를 직접 호출한다.

    나쁜 패턴: 오류를 삼킨다. 주문이 없는 경우와 그 밖의 모든 실패를
    구분하지 않고 "UNKNOWN" 으로 뭉갠다. 실패 원인은 어디에도 남지 않으므로
    호출자는 왜 실패했는지 알 방법이 없다.
    """
    if order_id in _ui_status_cache:
        return _ui_status_cache[order_id]

    try:
        status = _fake_order_api(order_id)  # UI -> 외부 API 직접 호출
    except Exception:
        # 원인을 구분하지 않고 기본값으로 무시한다 (오류를 삼킴).
        status = "UNKNOWN"

    _ui_status_cache[order_id] = status              # 상태 저장소 1
    _recent_lookups.append(f"{order_id}:{status}")   # 상태 저장소 2 (중복)
    return status


def print_order_status(order_id: str) -> None:
    status = get_order_status_for_display(order_id)
    print(f"[주문 {order_id}] 상태: {status}")


def main() -> int:
    # Windows 콘솔(cp949)에서 한글 출력이 깨지지 않도록 UTF-8 로 재구성
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    for order_id in ("A100", "A101", "A999"):  # A999 는 존재하지 않는 주문
        print_order_status(order_id)

    print(f"UI 캐시: {_ui_status_cache}")
    print(f"별도 조회 기록: {_recent_lookups}")
    print(
        "두 저장소는 지금은 우연히 같은 내용이지만, 한쪽만 무효화되거나 "
        "갱신되는 순간 서로 어긋난다. 이것이 상태 중복의 위험이다."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
