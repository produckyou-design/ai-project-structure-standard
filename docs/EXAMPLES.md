# EXAMPLES.md — 예제 사용법과 나쁜 예/좋은 예 대조 (Phase 7)

- 상태: ACTIVE (Phase 7)
- 예제 3종: `examples/python-desktop/`, `examples/web-service/`, `examples/existing-project-migration/`

세 예제 모두 거대한 전역 오케스트레이터 없이 도메인 하나가 표준 계층
(Entry → Domain Coordinator → Service → Adapter/Repository)을 따른다.
계층 정의는 `docs/ARCHITECTURE_STANDARD.md`, 계약(요청/결과/오류)은
`schemas/{request,result,error}.schema.json`.

## 1. python-desktop — 로컬 파일 저장 최소 예제

```text
main.py               Entry Layer
notes_coordinator.py  Coordinator
notes_service.py      Service
notes_repository.py   Repository (파일 쓰기의 단일 소유자)
contracts.py          계약 헬퍼
```

```bash
python examples/python-desktop/main.py add "장보기 목록 작성"
python examples/python-desktop/main.py list
```

성공/실패 모두 같은 결과 봉투(JSON)로 출력된다. 실패 시 exit code 1.
자세한 내용은 `examples/python-desktop/README.md`.

## 2. web-service — 표준 라이브러리 HTTP 서비스 최소 예제

```text
server.py             Entry Layer (Route)
status_coordinator.py Coordinator
status_service.py     Service
system_adapter.py     Adapter (OS 접근의 단일 소유자)
contracts.py          계약 헬퍼
```

```bash
python examples/web-service/server.py --once      # 서버 없이 1건 처리
python examples/web-service/server.py             # http://127.0.0.1:8765/status
```

로컬 서버는 127.0.0.1(루프백)에만 바인딩한다(`docs/SECURITY_STANDARD.md` §2).
자세한 내용은 `examples/web-service/README.md`.

## 3. existing-project-migration — 나쁜 예 / 좋은 예 대조

```bash
python examples/existing-project-migration/before/app.py
python examples/existing-project-migration/after/main.py A100 A101 A999
```

### 나쁜 예 / 좋은 예 대조표

| 판단 기준 | 나쁜 예 (`before/app.py`) | 좋은 예 (`after/`) |
|---|---|---|
| 외부 경계 호출자 | UI 함수가 직접 호출 | Adapter 1개만 호출 |
| 상태 소유자 | 2곳 중복(`_ui_status_cache`, `_recent_lookups`) | Coordinator 1곳(`_status_cache`) |
| 실패 처리 | 원인 구분 없이 `"UNKNOWN"`으로 뭉갬 | `error.schema.json` 오류 객체로 정규화, 코드로 원인 구분 |
| 추적 가능성 | 개별 실패를 구분할 ID 없음 | `trace_id`가 요청→오류까지 유지 |
| 계층 | 함수 1개에 호출·캐시·오류 처리가 결합 | Entry/Coordinator/Service/Adapter 4계층 분리 |

전체 대조와 8단계 이전 절차는 `docs/MIGRATION_GUIDE.md`와
`examples/existing-project-migration/README.md`를 참고한다.

## 4. 공통 확인 포인트 (세 예제 모두)

- `trace_id`는 Entry에서 1회 발급되어 오류 객체까지 유지된다.
- 실패는 예외 전파가 아니라 `success=false` + 오류 객체다.
- Coordinator에는 파일 I/O·네트워크·OS 접근 코드가 없다(Service/Adapter의 책임).
- 오류 코드(예: `NOTES-STORAGE-WRITE-500`, `ORDER-PROVIDER-NOTFOUND-404`)는
  실패의 종류, `trace_id`는 개별 사건 — `docs/ERROR_STANDARD.md` §1.

## 5. 예제를 새 프로젝트의 출발점으로 쓸 때

1. 도메인 이름을 프로젝트의 실제 도메인으로 바꾼다(`notes`/`status`/`order` →
   실제 capability 이름).
2. Adapter가 접근하는 실제 자원(DB, 외부 API, OS)에 맞게 저수준 구현을 바꾼다.
3. Coordinator의 캐시/타임아웃/재시도 정책을 프로젝트 요구에 맞게 조정한다.
4. 오류 코드를 프로젝트의 `ERROR_CATALOG.md`에 등록한다
   (`templates/ERROR_CATALOG.md`를 프로젝트 루트에 복사해 시작).
5. 스키마 정합성을 검증하는 테스트를 프로젝트 테스트 스위트에 추가한다
   (예제의 `tests/test_contract_schemas.py` 패턴 참고).
