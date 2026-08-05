# ARCHITECTURE_STANDARD.md

- 상태: ACTIVE (Phase 4)
- 근거: `docs/DECISIONS/ADR-0001-layered-coordinator.md`
- 계약: `schemas/request.schema.json`, `schemas/result.schema.json`, `schemas/error.schema.json`

이 문서는 AI 가 장기간 개발하는 소프트웨어 프로젝트의 표준 계층 구조를 정의한다.
언어와 프레임워크에 종속되지 않는다.

---

## 1. 표준 계층

```text
UI / API / 외부 요청 / 백그라운드 작업
                    |
          Application Entry Layer
                    |
          Domain Coordinator
                    |
        Domain Service / Use Case
                    |
       Adapter / Repository / Gateway
                    |
    DB / 파일 / 외부 API / 운영체제 / 서버
```

| 계층 | 책임 | 금지 |
|---|---|---|
| Entry (UI/Route/CLI) | 입력 수집, 요청 계약 생성, 결과 표시 | 비즈니스 로직, 직접 저장/네트워크 접근 |
| Domain Coordinator | 요청 정규화, 순서, 중복 병합, 상태, 캐시 정책, 타임아웃, 취소, 결과 조합, 오류 정규화 | 파일 처리, 네트워크 전송, DB 접근, 암호화, 파싱 |
| Service / Use Case | 도메인 규칙, 검증, 계산 | 외부 경계 직접 접근 (Adapter 를 통해서만) |
| Adapter / Repository / Gateway | 파일·DB·외부 API·OS 접근, 응답 파싱, 저수준 오류를 표준 오류로 변환 | 도메인 규칙 판단 |

순수 계산 함수까지 Coordinator 를 거치게 만들지 않는다.

## 2. 도메인별 Coordinator

하나의 거대한 전역 오케스트레이터를 만들지 않는다.
도메인마다 독립 Coordinator 를 둔다.

```text
AuthCoordinator
MarketDataCoordinator
NewsCoordinator
UpdateCoordinator
StorageCoordinator
PaymentCoordinator
```

이름보다 책임과 단일 소유권을 우선한다. 기존 프로젝트에 같은 책임의
클래스(Manager, Controller 등)가 이미 있으면 재사용하고 새로 만들지 않는다.

## 3. 최상위 Application Coordinator

**필요한 경우에만** 둔다. 필요 조건: 여러 도메인에 걸친 실행 순서가 실제로 존재할 때.

허용 범위:

- 앱 부팅 / 종료
- 로그인 이후 초기화
- 여러 도메인에 걸친 실행 순서
- 업데이트 후 재시작
- 전체 장애 복구 모드
- 사용자·워크스페이스 전환

직접 수행 금지: DB 쿼리, 외부 API 파싱, 인증 세부 로직, 뉴스 처리, 결제 처리,
파일 저장, 기능별 캐시 관리. 이것들은 각 도메인 Coordinator 이하 계층의 책임이다.

## 4. 중앙화할 경계 (단일 소유자)

다음에는 명확한 단일 소유자를 둔다.

| 경계 | 소유자 예 |
|---|---|
| 외부 네트워크 요청 | 공통 Transport / HttpGateway |
| 인증 | AuthCoordinator + AuthService |
| 권한 판정 | PermissionService (UI 숨김은 권한 검증이 아님) |
| DB 쓰기 | 도메인별 Repository |
| 파일 쓰기 | StorageService / FileRepository |
| 비밀정보 저장 | SecretStore (평문 fallback 금지) |
| 오류 정규화 | 각 Coordinator 의 오류 경계 (`error.schema.json`) |
| 로그 마스킹 | 공통 로깅 유틸 (`common.mask_sensitive` 상당) |
| 업데이트 | UpdateCoordinator |
| 백그라운드 작업 | 도메인별 Worker + 소유 Coordinator |
| 기능 간 상태 변경 | 상태를 소유한 Coordinator 를 통해서만 |

## 5. 계층 간 계약

Coordinator 경계를 지나는 호출은 표준 계약을 사용한다.

- 요청: `request.schema.json` — 필수 `request_id`, `trace_id`, `capability`, `operation`, `contract_version`
- 결과: `result.schema.json` — 필수 `success`, `trace_id`, `contract_version`. 실패면 `error` 필수
- 오류: `error.schema.json` — 필수 `code`, `trace_id`, `category`, `retryable`

원칙:

- `trace_id` 는 UI→Coordinator→Service→Adapter 전 구간에서 동일하게 유지한다.
- 재시도는 `request_id` 를 새로 발급하되 `trace_id` 는 유지한다.
- 실패도 예외 전파가 아니라 동일한 결과 봉투(`success=false`)로 반환한다.
- 계층 내부 함수 호출(Service→순수 함수 등)까지 계약 봉투를 강제하지 않는다.
  계약은 Coordinator 경계에서만 필수다.

실행 가능한 최소 예제: `examples/python-desktop/`, `examples/web-service/`.

## 6. 기존 프로젝트 적용

한 번에 전면 재작성하지 않는다. 순서:

```text
1. 현재 호출 경로 조사
2. 상태 소유자 조사
3. 직접 호출과 우회 경로 목록화
4. 기존 Coordinator/Gateway 재사용 판단
5. 위험 경계(네트워크·인증·저장)부터 중앙화
6. 기능별로 점진적 이전
7. 회귀 테스트
8. 레거시 경로 제거
```

상세 절차는 `docs/MIGRATION_GUIDE.md` (Phase 7).

## 7. 크기 규칙

- 한 파일이 500줄을 넘으면 책임 혼재를 먼저 검토한다.
- Coordinator 에 파싱·저장·전송 코드가 들어오면 Service/Adapter 로 내린다.
- 새 파일을 만들기 전 `docs/FILE_RESPONSIBILITIES.md` 에서 같은 책임의 기존 파일을 검색한다.
