"""notes_repository.py — Adapter/Repository 계층.

파일 I/O 만 담당한다. 도메인 규칙 판단과 오류 코드 발급은 하지 않는다.
저수준 실패는 언어 예외(OSError, ValueError)로 올리고,
Coordinator 가 표준 오류로 정규화한다.
"""
from __future__ import annotations

import json
from pathlib import Path


class NotesRepository:
    """노트 목록을 JSON 파일 하나에 저장한다 (파일 쓰기의 단일 소유자)."""

    def __init__(self, data_file: Path):
        self._data_file = Path(data_file)

    def load_all(self) -> list[dict]:
        if not self._data_file.exists():
            return []
        raw = self._data_file.read_text(encoding="utf-8")
        loaded = json.loads(raw) if raw.strip() else []
        if not isinstance(loaded, list):
            raise ValueError("노트 데이터 파일 형식이 잘못됨 (list 가 아님)")
        return loaded

    def save_all(self, notes: list[dict]) -> None:
        self._data_file.parent.mkdir(parents=True, exist_ok=True)
        self._data_file.write_text(
            json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8"
        )
