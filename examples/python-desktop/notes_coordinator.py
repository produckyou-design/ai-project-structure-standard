"""notes_coordinator.py — Domain Coordinator 계층.

허용 책임: 요청 정규화, 라우팅, 오류 정규화, 결과 봉투 조합.
금지: 파일 처리, 파싱, 도메인 규칙 — Service/Repository 의 책임이다.

전역 오케스트레이터가 아니다. notes 도메인만 담당한다.
"""
from __future__ import annotations

import time

from contracts import fail_result, make_error, ok_result
from notes_service import NotesService, NoteValidationError


class NotesCoordinator:
    CAPABILITY = "notes"

    def __init__(self, service: NotesService):
        self._service = service

    def handle(self, request: dict) -> dict:
        """표준 요청을 받아 표준 결과 봉투로 반환한다. 예외를 밖으로 흘리지 않는다."""
        started = time.monotonic()

        def _elapsed_ms() -> int:
            return int((time.monotonic() - started) * 1000)

        trace_id = request.get("trace_id", "")
        if request.get("capability") != self.CAPABILITY:
            return fail_result(request, make_error(
                "NOTES-CONTRACT-CAPABILITY-400", "contract", trace_id=trace_id,
                retryable=False, user_message="지원하지 않는 요청입니다.",
                source="coordinator.notes",
                details={"capability": str(request.get("capability"))},
            ), duration_ms=_elapsed_ms())

        operation = request.get("operation")
        try:
            if operation == "add":
                note = self._service.add_note(str(request.get("parameters", {}).get("text", "")))
                return ok_result(request, note, source="repository.file",
                                 duration_ms=_elapsed_ms())
            if operation == "list":
                notes = self._service.list_notes()
                return ok_result(request, notes, source="repository.file",
                                 duration_ms=_elapsed_ms())
            return fail_result(request, make_error(
                "NOTES-CONTRACT-OPERATION-400", "contract", trace_id=trace_id,
                retryable=False, user_message="지원하지 않는 동작입니다.",
                source="coordinator.notes", details={"operation": str(operation)},
            ), duration_ms=_elapsed_ms())
        except NoteValidationError as exc:
            return fail_result(request, make_error(
                "NOTES-PARSING-VALIDATION-422", "parsing", trace_id=trace_id,
                retryable=False, user_message=str(exc), source="coordinator.notes",
            ), duration_ms=_elapsed_ms())
        except (OSError, ValueError) as exc:
            # 저장 경계의 저수준 실패를 표준 오류로 정규화 (원문 경로·스택 미노출)
            return fail_result(request, make_error(
                "NOTES-STORAGE-WRITE-500", "storage", trace_id=trace_id,
                retryable=True, user_message="노트 저장소에 접근할 수 없습니다.",
                source="repository.file", details={"reason": type(exc).__name__},
            ), duration_ms=_elapsed_ms())
