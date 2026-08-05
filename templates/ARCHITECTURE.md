# ARCHITECTURE — 아키텍처 문서

> 이 문서는 이 프로젝트의 실제 아키텍처를 기록한다.
> 계획이 아니라 현재 상태를 기준으로 작성한다.
> (프로젝트에 맞게 내용을 채운다. 예시 값은 모두 교체한다.)

- 최종 업데이트: (YYYY-MM-DD)
- 관련 ADR: `docs/DECISIONS/ADR-0001-layered-coordinator.md`

## 1. 계층 구조

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

## 2. 도메인 목록과 Coordinator

| 도메인 | Coordinator | 담당 기능 | Service/Adapter |
|---|---|---|---|
| (예: 인증) | (예: `AuthCoordinator`) | (예: 로그인, 토큰 갱신) | (예: `AuthService`, `OAuthAdapter`) |
|  |  |  |  |

규칙:

- Coordinator 는 요청 정규화, 순서, 상태, 결과 조합, 오류 정규화만 담당한다.
- 실제 파일 처리, 네트워크 전송, DB 접근, 암호화, 파싱은 Service / Adapter / Repository 에 둔다.
- 순수 계산 함수까지 Coordinator 를 거치게 하지 않는다.

## 3. 최상위 Application Coordinator (필요한 경우에만)

담당 가능 범위:

- 앱 부팅 / 종료
- 로그인 이후 초기화
- 여러 도메인에 걸친 실행 순서
- 업데이트 후 재시작
- 전체 장애 복구 모드
- 사용자 또는 워크스페이스 전환

직접 수행하면 안 되는 것:

- DB 쿼리, 외부 API 파싱, 인증 세부 로직
- 파일 저장, 기능별 캐시 관리
- 도메인별 실제 기능 로직

## 4. 중앙화할 경계 (단일 소유자)

다음은 반드시 한 곳에서만 소유한다.

- 외부 네트워크 요청 (Transport / Gateway)
- 인증 / 권한 판정
- DB 쓰기 / 파일 쓰기
- 비밀정보 저장
- 오류 정규화 (오류 코드 + trace_id)
- 로그 마스킹
- 업데이트 / 백그라운드 작업
- 기능 간 상태 변경

## 5. 오류와 trace

- 오류 코드 = 실패 종류 (예: `APP-STORAGE-WRITE-500`)
- trace_id = 실제 발생한 개별 사건
- UI / 백엔드 / Worker / 외부 API 를 지나도 같은 trace_id 를 유지한다
- 모든 함수에 오류 코드를 붙이지 않는다. 경계(인증/권한/네트워크/저장/파싱/설정/배포/복구)에만 쓴다

## 6. 기존 프로젝트 점진적 적용

```text
1. 현재 호출 경로 조사
2. 상태 소유자 조사
3. 직접 호출과 우회 경로 목록화
4. 기존 Coordinator 와 Gateway 재사용 판단
5. 위험 경계부터 중앙화
6. 기능별로 점진적 이전
7. 회귀 테스트
8. 레거시 경로 제거
```

이름보다 책임과 단일 소유권을 우선한다.
기존 정상 동작을 보존하면서 점진적으로 개선한다.

## 7. 반드시 피할 것

- 거대한 단일 전역 오케스트레이터 (GlobalOrchestrator)
- Coordinator 에 실제 기능 로직이 과도하게 들어가는 것
- 같은 상태를 여러 곳에서 관리하는 것
- 검증되지 않은 변경을 라이브에 적용하는 것
