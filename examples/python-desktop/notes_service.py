"""notes_service.py — Domain Service / Use Case 계층.

도메인 규칙(검증, 시각 기록)만 담당한다.
파일 접근은 Repository 를 통해서만 한다.
"""
from __future__ import annotations

from datetime import datetime, timezone

from notes_repository import NotesRepository

MAX_NOTE_LENGTH = 500


class NoteValidationError(ValueError):
    """도메인 규칙 위반. Coordinator 가 표준 오류로 정규화한다."""


class NotesService:
    def __init__(self, repository: NotesRepository):
        self._repository = repository

    def add_note(self, text: str) -> dict:
        text = text.strip()
        if not text:
            raise NoteValidationError("노트 내용이 비어 있습니다")
        if len(text) > MAX_NOTE_LENGTH:
            raise NoteValidationError(f"노트는 {MAX_NOTE_LENGTH}자를 넘을 수 없습니다")
        notes = self._repository.load_all()
        note = {
            "id": len(notes) + 1,
            "text": text,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        notes.append(note)
        self._repository.save_all(notes)
        return note

    def list_notes(self) -> list[dict]:
        return self._repository.load_all()
