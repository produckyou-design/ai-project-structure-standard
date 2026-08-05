# ERROR_STANDARD.md

- 상태: ACTIVE (Phase 4)
- 계약: `schemas/error.schema.json`
- 카탈로그 양식: `templates/ERROR_CATALOG.md`

---

## 1. 오류 코드와 trace_id 의 분리

```text
오류 코드 = 실패의 종류 (같은 원인이면 항상 같은 코드)
trace_id  = 실제 발생한 개별 사건 (발생할 때마다 다름)
```

- 오류 코드로 "무엇이 실패하는가"를 집계한다.
- trace_id 로 "이 사용자의 이 요청이 어디서 실패했는가"를 추적한다.
- 하나의 trace_id 아래 여러 오류 코드가 기록될 수 있다 (예: 네트워크 실패 → 캐시 폴백 실패).

## 2. 오류 코드를 발급하는 경계

모든 함수에 오류 코드를 붙이지 않는다. 다음 경계에서만 발급한다.

```text
인증(auth) · 권한(permission) · 네트워크(network) · 외부 공급자(provider)
저장(storage) · 데이터 파싱(parsing) · 업데이트(update) · 설정(config)
계약 버전(contract) · 배포(release) · 복구(recovery)
```

경계 내부의 순수 함수·도메인 계산은 언어의 일반 예외/반환값을 그대로 쓴다.
경계를 넘는 순간(Adapter→Coordinator, Coordinator→호출자)에 표준 오류로 정규화한다.

## 3. 코드 형식

```text
<APP>-<CATEGORY>-<SUBJECT>-<DISCRIMINATOR>
```

- 대문자·숫자·하이픈만 사용. 최소 4토큰 권장, 스키마는 3토큰 이상 강제.
- 예:

```text
APP-AUTH-TOKEN-401
APP-DATA-PROVIDER-429
APP-STORAGE-WRITE-500
APP-UPDATE-MANIFEST-409
```

- 새 코드는 프로젝트의 `ERROR_CATALOG.md` 에 등록한 뒤 사용한다.
  카탈로그 미등록 코드는 문서 정합성 검사(Phase 5)의 대상이다.

## 4. trace_id 전파 규칙

- trace_id 는 Entry Layer(UI/Route)에서 1회 발급한다.
- UI, 백엔드, Worker, 외부 API 호출 헤더(예: `X-Trace-Id`)를 지나도 같은 값을 유지한다.
- 재시도 시 `request_id` 는 새로 발급하고 `trace_id` 는 유지한다.
- 로그·오류 보고·결과 봉투에 항상 trace_id 를 포함한다.

## 5. 오류 객체 규칙 (`error.schema.json`)

| 필드 | 필수 | 규칙 |
|---|---|---|
| `code` | 필수 | 카탈로그에 등록된 실패 종류 |
| `trace_id` | 필수 | 요청에서 이어받은 사건 ID |
| `category` | 필수 | §2 경계 목록 중 하나 |
| `retryable` | 필수 | 재시도로 해소 가능 여부. 무한 재시도 금지 |
| `user_message` | 권장 | 사용자에게 보여도 되는 문장. 시크릿·경로·스택 금지 |
| `source` | 권장 | 정규화한 계층 (예: `adapter.provider_x`) |
| `details` | 선택 | 디버깅 상세. 시크릿 원문 금지 (마스킹 필수) |
| `occurred_at` | 권장 | 발생 시각 (ISO-8601) |

## 6. 처리 규칙

- 실패를 예외로 상위 계층에 그대로 흘리지 않고, Coordinator 가 `success=false` 결과 봉투로 정규화한다.
- 빈 except/catch 로 예외를 삼키지 않는다 (금지 패턴 검사 대상).
- `retryable=true` 라도 재시도 횟수·간격 상한을 둔다.
- 캐시 폴백으로 성공을 반환하면 `is_stale=true` 와 `source` 로 명시한다.
- 오류 로그는 공통 마스킹을 거친다. 토큰·키·쿠키·비밀번호를 남기지 않는다.
