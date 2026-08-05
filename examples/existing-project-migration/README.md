# existing-project-migration 예제 — 점진적 마이그레이션 최소 실행 예제

기존(레거시) 코드에서 계층형 Coordinator 구조로 옮기는 과정을 최소 실행 가능한
형태로 보여준다. 같은 기능(주문 상태 조회)을 `before/`(나쁜 예)와 `after/`(개선 예)
양쪽에 구현했다. 절차 상세는 `docs/MIGRATION_GUIDE.md`, 원칙 근거는
`docs/DECISIONS/ADR-0001-layered-coordinator.md` §6 을 따른다.

외부 네트워크는 쓰지 않는다. "외부 주문 API" 는 로컬 함수(`_fake_order_api` /
`OrderApiAdapter`)로 흉내낸다 — 나쁜 패턴이 드러나는 것은 흉내낸 호출을
**어디서 부르는가**(UI에서 직접 vs Adapter 경유)이지, 실제 네트워크 유무가 아니다.

## 개선 전후 차이 대조표

| 항목 | before/ (나쁜 예) | after/ (개선 예) |
|---|---|---|
| 외부 API 호출 | `get_order_status_for_display()`(UI 함수)가 `_fake_order_api()`를 직접 호출 | `OrderApiAdapter.fetch_status()` 하나만 호출 (Adapter 단일 소유) |
| 상태 보관 | `_ui_status_cache` 와 `_recent_lookups` 두 곳에 중복 보관, 소유자 불명확 | `OrderCoordinator._status_cache` 하나만 보관 (Coordinator 단일 소유) |
| 오류 처리 | `except Exception: status = "UNKNOWN"` — 실패 종류를 구분하지 않고 삼킴, 원인이 어디에도 남지 않음 | `OrderNotFoundError` / `OrderValidationError` 를 구분해 `error.schema.json` 오류 객체로 정규화 (`ORDER-PROVIDER-NOTFOUND-404` 등), 실패도 같은 결과 봉투로 반환 |
| 계층 | UI 함수 1개에 호출·캐시·오류 처리가 전부 섞임 | Entry(`main.py`) → Coordinator(`order_coordinator.py`) → Service(`order_service.py`) → Adapter(`order_api_adapter.py`) 4계층 분리 |
| trace 가능성 | 실패해도 개별 사건을 추적할 ID가 없음 | Entry 에서 발급한 `trace_id` 가 오류 객체까지 유지됨 |

## 실행

```bash
# 나쁜 예 (그대로 실행 가능하다 — 무엇이 문제인지 출력에서 확인한다)
python before/app.py

# 개선 예 (성공/실패 모두 표준 결과 봉투로 출력, 실패 시 exit code 1)
python after/main.py A100 A101 A999
```

`after/main.py` 인자를 생략하면 `A100 A101 A999`(정상 2건 + 존재하지 않는 주문 1건)로
기본 실행된다.

## 이전 순서 (이 예제가 보여주는 범위)

`docs/MIGRATION_GUIDE.md` 8단계 중 이 최소 예제가 보여주는 부분은 다음과 같다.

1. **현재 호출 경로 조사** — `before/app.py` 에서 UI 함수가 외부 API를 직접 부르는
   지점(`get_order_status_for_display`)을 확인한다.
2. **상태 소유자 조사** — `_ui_status_cache` 와 `_recent_lookups` 두 곳이 같은 정보를
   중복 보관하고 있음을 확인한다.
3. **위험 경계부터 중앙화** — 외부 API 접근을 `OrderApiAdapter` 하나로 모은다.
4. **상태를 한 곳으로 합침** — 캐시를 `OrderCoordinator._status_cache` 하나로 합친다.
5. **오류를 정규화** — 삼켜지던 예외를 `error.schema.json` 오류 객체로 바꾼다.
6. **회귀 확인** — 같은 입력(`A100`, `A101`, `A999`)에 대해 `before/`와 `after/`의
   실질적 동작(정상 조회 2건, 존재하지 않는 주문 1건 실패)이 같음을 확인한다.

실제 프로젝트에서는 한 번에 전체 도메인을 옮기지 않는다. 이 예제는 도메인 하나
(주문 조회)만 옮긴 최소 단위이며, 나머지 5단계(기존 Coordinator/Gateway 재사용 판단,
기능별 점진 이전, 레거시 경로 제거 등)는 `docs/MIGRATION_GUIDE.md` 를 따른다.

## 계약 확인 포인트

- `trace_id` 는 Entry(`main.py`)에서 1회 발급되어 오류 객체까지 유지된다.
- 실패는 예외 전파가 아니라 `success=false` + `error.schema.json` 객체다.
- 오류 코드(`ORDER-PROVIDER-NOTFOUND-404` 등)는 실패의 종류이고, 개별 사건은
  trace_id 가 구분한다.
- `OrderCoordinator` 에는 외부 API 호출 코드가 없다 (Adapter/Service 의 책임).
