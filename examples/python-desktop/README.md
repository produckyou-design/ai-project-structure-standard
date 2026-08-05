# python-desktop 예제 — 계층형 Coordinator 최소 구현

노트를 로컬 JSON 파일에 저장하는 최소 데스크톱(CLI) 앱이다.
거대한 전역 오케스트레이터 없이, notes 도메인 하나가 표준 계층을 따른다.

```text
main.py               Entry Layer   — 입력 수집, trace_id 발급, 요청 생성, 결과 표시
notes_coordinator.py  Coordinator   — 요청 정규화, 라우팅, 오류 정규화, 결과 봉투
notes_service.py      Service       — 도메인 규칙 (검증, 시각 기록)
notes_repository.py   Repository    — 파일 I/O (파일 쓰기의 단일 소유자)
contracts.py          계약 헬퍼      — schemas/{request,result,error}.schema.json 준수
```

## 실행

```bash
python main.py add "장보기 목록 작성"
python main.py list
```

- 데이터는 `notes.data.json` 에 저장된다 (`--data-file` 로 변경 가능, Git 추적 제외).
- 성공/실패 모두 같은 결과 봉투(JSON)로 출력된다. 실패 시 exit code 1.

## 계약 확인 포인트

- `trace_id` 는 Entry 에서 1회 발급되어 오류 객체까지 유지된다.
- 실패는 예외 전파가 아니라 `success=false` + `error.schema.json` 객체다.
- 오류 코드(`NOTES-STORAGE-WRITE-500` 등)는 실패의 종류이고, 개별 사건은 trace_id 가 구분한다.
- Coordinator 에는 파일 I/O·파싱 코드가 없다 (Repository/Service 의 책임).

스키마 정합성은 `tests/test_contract_schemas.py` 가 검증한다.
