"""main.py — Application Entry Layer (데스크톱 UI 를 CLI 로 최소화한 예제).

책임: 입력 수집 → trace_id 발급 → 표준 요청 생성 → Coordinator 호출 → 결과 표시.
비즈니스 로직과 저장 접근은 하지 않는다.

실행:
  python main.py add "장보기 목록 작성"
  python main.py list
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import make_request, new_trace_id
from notes_coordinator import NotesCoordinator
from notes_repository import NotesRepository
from notes_service import NotesService

DEFAULT_DATA_FILE = Path(__file__).resolve().parent / "notes.data.json"


def build_coordinator(data_file: Path = DEFAULT_DATA_FILE) -> NotesCoordinator:
    """조립(부팅)은 Entry Layer 의 책임이다. 계층: Entry → Coordinator → Service → Repository."""
    return NotesCoordinator(NotesService(NotesRepository(data_file)))


def main(argv: list[str] | None = None) -> int:
    # Windows 콘솔(cp949)에서 한글 JSON 출력이 깨지지 않도록 UTF-8 로 재구성
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(prog="notes", description="계층형 구조 최소 예제 (노트 앱)")
    parser.add_argument("--data-file", default=str(DEFAULT_DATA_FILE))
    sub = parser.add_subparsers(dest="command", required=True)
    add_p = sub.add_parser("add", help="노트 추가")
    add_p.add_argument("text")
    sub.add_parser("list", help="노트 목록")
    args = parser.parse_args(argv)

    coordinator = build_coordinator(Path(args.data_file))
    trace_id = new_trace_id()
    if args.command == "add":
        request = make_request("notes", "add", {"text": args.text},
                               trace_id=trace_id, caller="ui.cli")
    else:
        request = make_request("notes", "list", trace_id=trace_id, caller="ui.cli")

    result = coordinator.handle(request)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
