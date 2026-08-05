"""server.py — Application Entry Layer (Route).

책임: HTTP 요청 수신 → trace_id 확보 → 표준 요청 생성 → Coordinator 호출 → HTTP 응답 변환.
표준 라이브러리만 사용한다. 보안 표준에 따라 127.0.0.1 에만 바인딩한다.

실행:
  python server.py --once          # 서버 없이 요청 1건 처리 결과 출력 (테스트용)
  python server.py                 # http://127.0.0.1:8765/status
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import make_request, new_trace_id
from status_coordinator import StatusCoordinator
from status_service import StatusService
from system_adapter import SystemAdapter

BIND_HOST = "127.0.0.1"  # 로컬 서버는 기본적으로 루프백에만 바인딩한다
DEFAULT_PORT = 8765


def build_coordinator() -> StatusCoordinator:
    """조립은 Entry Layer 의 책임. 계층: Route → Coordinator → Service → Adapter."""
    return StatusCoordinator(StatusService(SystemAdapter()))


def handle_status(coordinator: StatusCoordinator, trace_id: str | None = None) -> dict:
    """Route 1건 처리: 계약 생성 → Coordinator 호출. trace_id 는 유입값을 유지한다."""
    request = make_request(
        "status", "health",
        trace_id=trace_id or new_trace_id(), caller="route./status",
    )
    return coordinator.handle(request)


class StatusHandler(BaseHTTPRequestHandler):
    coordinator: StatusCoordinator = None  # serve() 에서 주입

    def do_GET(self):  # noqa: N802 (http.server 규약)
        if self.path.split("?")[0] != "/status":
            self.send_error(404, "not found")
            return
        # 게이트웨이를 지나온 trace_id 가 있으면 유지한다
        incoming_trace = self.headers.get("X-Trace-Id")
        result = handle_status(self.coordinator, trace_id=incoming_trace)
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(200 if result["success"] else 500)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("X-Trace-Id", result["trace_id"])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"[server] {fmt % args}")


def serve(port: int = DEFAULT_PORT) -> None:
    StatusHandler.coordinator = build_coordinator()
    httpd = HTTPServer((BIND_HOST, port), StatusHandler)
    print(f"listening on http://{BIND_HOST}:{port}/status (Ctrl+C 로 종료)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def main(argv: list[str] | None = None) -> int:
    # Windows 콘솔(cp949)에서 한글 JSON 출력이 깨지지 않도록 UTF-8 로 재구성
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(prog="web-service", description="계층형 구조 최소 예제 (상태 서비스)")
    parser.add_argument("--once", action="store_true", help="서버 없이 요청 1건 처리 결과 출력")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    if args.once:
        result = handle_status(build_coordinator())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["success"] else 1
    serve(args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
