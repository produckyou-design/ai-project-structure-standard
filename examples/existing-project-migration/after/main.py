"""main.py — Application Entry Layer (CLI).

책임: 입력 수집 -> trace_id 발급 -> 표준 요청 생성 -> Coordinator 호출 -> 결과 표시.
비즈니스 로직과 외부 API 접근은 하지 않는다.

이 파일은 `before/app.py` 와 같은 기능(주문 상태 조회)을 계층형 구조로 다시 구현한 것이다.
차이는 `README.md` 대조표를 참고한다.

실행:
  python main.py A100
  python main.py A101 A999
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import make_request, new_trace_id
from order_api_adapter import OrderApiAdapter
from order_coordinator import OrderCoordinator
from order_service import OrderService


def build_coordinator() -> OrderCoordinator:
    """조립(부팅)은 Entry Layer 의 책임이다. 계층: Entry -> Coordinator -> Service -> Adapter."""
    return OrderCoordinator(OrderService(OrderApiAdapter()))


def main(argv: list[str] | None = None) -> int:
    # Windows 콘솔(cp949)에서 한글 JSON 출력이 깨지지 않도록 UTF-8 로 재구성
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    order_ids = argv if argv is not None else sys.argv[1:]
    if not order_ids:
        order_ids = ["A100", "A101", "A999"]  # A999 는 존재하지 않는 주문 (오류 예시)

    coordinator = build_coordinator()
    exit_code = 0
    for order_id in order_ids:
        trace_id = new_trace_id()
        request = make_request("order", "get_status", {"order_id": order_id},
                               trace_id=trace_id, caller="ui.cli")
        result = coordinator.handle(request)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["success"]:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
