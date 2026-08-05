# AI Project Structure Standard
## DeepSeek V4 Flash 분할 제작 프롬프트

이 문서는 DeepSeek V4 Flash처럼 비용 효율이 높은 모델이 긴 요구사항을 한 번에 놓치지 않도록, 작업을 검증 가능한 단계로 나눠 실행하기 위한 마스터 프롬프트다.

목표는 범용 소프트웨어 프로젝트에 적용할 수 있는 공개 배포용 구조 표준 스킬 저장소를 실제로 완성하는 것이다.

---

# 0. 사용 방법

이 문서 전체를 작업 저장소의 루트에 넣는다.

권장 파일명:

```text
FLASH_BUILD_PROMPT.md
```

V4 Flash에는 처음부터 전체 구현을 맡기지 않는다.

다음 순서로 진행한다.

```text
1. 공통 절대 규칙 전달
2. Phase 0 실행
3. 결과와 테스트 확인
4. 다음 Phase 실행
5. 마지막에 독립 감사 실행
```

각 Phase가 끝날 때마다 반드시 다음을 확인한다.

```text
- 실제 파일이 생성 또는 수정됐는가
- 실행 명령을 실제로 돌렸는가
- 테스트 결과가 기록됐는가
- FAIL 또는 NOT_RUN이 숨겨지지 않았는가
- 다음 AI가 이어받을 수 있는 기록이 남았는가
```

가능하면 Phase마다 새 세션을 사용한다.

같은 세션을 계속 사용할 경우에도 직전 Phase의 완료 보고와 실제 Git diff를 먼저 읽게 한다.

---

# 1. 공통 절대 규칙

아래 내용은 모든 Phase 시작 시 함께 전달한다.

```text
너는 범용 AI 소프트웨어 구조 표준 스킬 저장소를 제작한다.

계획이나 목차만 작성하고 끝내지 않는다.
각 Phase에서 요구한 파일과 실행 가능한 코드를 실제로 만든다.

작업 전에 현재 저장소와 Git 상태를 조사한다.
존재하지 않는 파일, 함수, 명령, 테스트 결과를 가정하지 않는다.

실행하지 않은 검사는 PASS가 아니라 NOT_RUN으로 기록한다.
테스트 실패를 숨기거나 완료로 처리하지 않는다.
빈 파일, placeholder, TODO만 있는 파일은 구현 완료로 인정하지 않는다.

한 Phase의 범위를 넘어 다음 Phase까지 임의로 구현하지 않는다.
다음 Phase에 필요한 인터페이스만 최소한으로 준비할 수 있다.

기존 파일이 있으면 역할과 내용을 조사한 뒤 재사용한다.
같은 역할의 파일이나 클래스를 중복 생성하지 않는다.
기존 프로젝트를 한 번에 전면 재작성하지 않는다.

하나의 거대한 전역 오케스트레이터를 만들지 않는다.
도메인별 Coordinator와 공통 Service를 사용하는 계층형 구조를 표준으로 한다.

Git push, GitHub Release, 외부 배포, 운영 데이터 수정은 하지 않는다.
시크릿 값을 출력하거나 저장소에 넣지 않는다.

모든 작업은 다음을 남겨야 한다.

- 변경 파일
- 실행 명령
- 테스트 결과
- 실패 또는 미실행 항목
- 남은 한계
- 다음 Phase가 읽을 인계 기록

완료 보고보다 실제 Git diff와 실행 결과를 우선한다.
```

---

# 2. 최종 목표

완성할 저장소의 권장 이름:

```text
ai-project-structure-standard
```

핵심 목적:

```text
AI가 장기간 소프트웨어 프로젝트를 개발할 때
계층형 오케스트레이션, 기능 분리, Git 관리,
AI 작업 서명, 오류 추적, 문서 인계,
구조적 보안, 검증 게이트,
안전한 배포와 롤백을 일관되게 적용하도록 하는 범용 개발 표준
```

최종 저장소의 권장 구조:

```text
ai-project-structure-standard/
├── README.md
├── LICENSE
├── SKILL.md
├── AGENTS.example.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── FLASH_BUILD_PROMPT.md
│
├── docs/
│   ├── ARCHITECTURE_STANDARD.md
│   ├── AI_WORKFLOW.md
│   ├── GIT_STANDARD.md
│   ├── SECURITY_STANDARD.md
│   ├── ERROR_STANDARD.md
│   ├── DOCUMENTATION_STANDARD.md
│   ├── RELEASE_STANDARD.md
│   ├── ROLLBACK_STANDARD.md
│   ├── MIGRATION_GUIDE.md
│   └── EXAMPLES.md
│
├── templates/
│   ├── AI_START_HERE.md
│   ├── ARCHITECTURE.md
│   ├── CURRENT.md
│   ├── STATUS.md
│   ├── WORK_LOG.md
│   ├── SESSION_HANDOFF.md
│   ├── ERROR_CATALOG.md
│   ├── RUNBOOK.md
│   ├── RELEASE_CHECKLIST.md
│   ├── DEPLOY_LOG.md
│   ├── SECURITY.md
│   └── ADR_TEMPLATE.md
│
├── schemas/
│   ├── request.schema.json
│   ├── result.schema.json
│   ├── error.schema.json
│   ├── ai_signature.schema.json
│   ├── verification.schema.json
│   └── release_manifest.schema.json
│
├── scripts/
│   ├── common.py
│   ├── preflight.py
│   ├── checkpoint.py
│   ├── sign_ai_session.py
│   ├── create_handoff.py
│   ├── verify_project.py
│   ├── check_secrets.py
│   ├── check_forbidden_patterns.py
│   ├── check_document_sync.py
│   ├── verify_release.py
│   └── create_release_manifest.py
│
├── examples/
│   ├── python-desktop/
│   ├── web-service/
│   └── existing-project-migration/
│
└── tests/
    ├── test_signatures.py
    ├── test_checkpoint.py
    ├── test_secret_scan.py
    ├── test_forbidden_patterns.py
    ├── test_release_manifest.py
    ├── test_handoff.py
    └── test_project_verification.py
```

구조는 실제 구현 과정에서 합리적으로 조정할 수 있다.

다만 파일 수를 채우기 위한 빈 파일은 만들지 않는다.

---

# 3. 핵심 아키텍처 표준

## 3.1 계층형 Coordinator

표준 구조:

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

예시:

```text
AuthCoordinator
MarketDataCoordinator
NewsCoordinator
UpdateCoordinator
StorageCoordinator
PaymentCoordinator
```

## 3.2 최상위 Application Coordinator

필요한 경우에만 둔다.

담당 가능 범위:

```text
- 앱 부팅
- 앱 종료
- 로그인 이후 초기화
- 여러 도메인에 걸친 실행 순서
- 업데이트 후 재시작
- 전체 장애 복구 모드
- 사용자 또는 워크스페이스 전환
```

직접 수행하면 안 되는 것:

```text
- DB 쿼리
- 외부 API 파싱
- 인증 세부 로직
- 뉴스 처리
- 결제 처리
- 파일 저장
- 기능별 캐시 관리
```

## 3.3 중앙화할 경계

다음에는 명확한 단일 소유자를 둔다.

```text
- 외부 네트워크 요청
- 인증
- 권한 판정
- DB 쓰기
- 파일 쓰기
- 비밀정보 저장
- 오류 정규화
- 로그 마스킹
- 업데이트
- 백그라운드 작업
- 기능 간 상태 변경
```

순수 계산 함수까지 Coordinator를 거치게 만들지 않는다.

## 3.4 기존 프로젝트 적용

```text
1. 현재 호출 경로 조사
2. 상태 소유자 조사
3. 직접 호출과 우회 경로 목록화
4. 기존 Coordinator와 Gateway 재사용 판단
5. 위험 경계부터 중앙화
6. 기능별로 점진적 이전
7. 회귀 테스트
8. 레거시 경로 제거
```

이름보다 책임과 단일 소유권을 우선한다.

---

# 4. 구조적 보안 표준

공통 스킬에서는 비용이 들거나 과도한 방어를 필수로 요구하지 않는다.

코딩 단계에서 구조적으로 적용 가능한 것만 강제한다.

필수 규칙:

```text
- 시크릿을 코드, 로그, Git, 테스트 결과, 빌드에 넣지 않는다.
- 보안 저장 실패 시 평문 저장으로 우회하지 않는다.
- 외부 입력, API 응답, 파일 경로, URL, 원격 설정을 검증한다.
- 파일, URL, API 경로, 실행 프로그램은 허용 목록을 우선한다.
- shell=True, eval, exec, 사용자 입력 기반 명령 실행을 기본 금지한다.
- 브리지와 내부 API는 필요한 기능만 공개한다.
- UI 버튼 숨김을 권한 검증으로 인정하지 않는다.
- 관리자, 유료 등급, 결제 상태를 로컬 Boolean만으로 신뢰하지 않는다.
- 민감 작업은 백엔드와 공통 권한 계층에서 다시 검증한다.
- 로컬 서버는 기본적으로 127.0.0.1에만 바인딩한다.
- 외부 요청은 공통 Transport 또는 Gateway에서 처리한다.
- TLS 검증을 끄지 않는다.
- 무한 재시도를 하지 않는다.
- 로그와 오류 보고에서 토큰, 키, 쿠키, 비밀번호를 마스킹한다.
- 개발용 인증 우회와 관리자 강제 활성화는 운영 빌드에서 차단한다.
- 변조 감지를 이유로 사용자 데이터를 삭제하지 않는다.
```

필수 제외 대상:

```text
- 유료 코드 서명 인증서
- HSM
- TPM 필수
- 강한 DRM
- 안티디버깅
- 패커
- 과도한 난독화
- 백신 기능
- 프로세스 감시
- 하드웨어 지문 수집
- 상용 보안 솔루션
```

필요한 프로젝트가 별도로 선택하게 한다.

---

# 5. Git과 AI 서명 표준

모든 코드 프로젝트는 Git으로 관리한다.

작업 시작 시 확인:

```text
- 현재 브랜치
- HEAD
- 최근 커밋
- git status
- staged diff
- unstaged diff
- 추적되지 않은 파일
```

여러 AI가 병렬 작업하면 별도 브랜치 또는 worktree를 사용한다.

AI 시작 서명:

```text
run_id
parent_run_id
provider
actual_model_id
claimed_model
role
effort
started_at
workspace
branch
base_commit
git_status_hash
task
allowed_scope
forbidden_scope
expected_tests
documents_read
```

AI 종료 서명:

```text
run_id
provider
actual_model_id
role
status
ended_at
base_commit
end_commit
diff_hash
changed_files
created_files
deleted_files
tests_run
tests_passed
tests_failed
documents_updated
decisions_made
known_issues
remaining_work
rollback_point
handoff_note
```

실제 모델 ID를 확인할 수 없으면 `UNKNOWN`으로 기록한다.

AI의 자기신고를 검증된 실제 모델 ID로 단정하지 않는다.

저장 위치:

```text
.ai/ledger.jsonl
docs/WORK_LOG.md
```

ledger는 append-only 방식으로 작성한다.

가능하면 각 항목에 이전 항목 해시와 현재 항목 해시를 포함한다.

---

# 6. 오류와 추적 표준

오류 코드와 trace ID를 구분한다.

```text
오류 코드 = 실패 종류
trace_id = 실제 발생한 개별 사건
```

모든 함수에 오류 코드를 붙이지 않는다.

다음 경계에만 사용한다.

```text
인증
권한
네트워크
외부 공급자
저장
데이터 파싱
업데이트
설정
계약 버전
배포
복구
```

예시:

```text
APP-AUTH-TOKEN-401
APP-DATA-PROVIDER-429
APP-STORAGE-WRITE-500
APP-UPDATE-MANIFEST-409
```

UI, 백엔드, Worker, 외부 API를 지나더라도 같은 trace ID를 유지할 수 있게 설계한다.

---

# 7. 검증과 배포 표준

모든 작업의 기본 검증:

```text
- 문법 검사
- 정적 분석
- 단위 테스트
- git diff --check
- 시크릿 검사
- 금지 패턴 검사
- 변경 파일 확인
- 문서 정합성 확인
```

실행하지 않은 검사는 `NOT_RUN`이다.

배포 전 필수 조건:

```text
- 승인된 커밋
- AI 시작·종료 서명
- 깨끗한 작업트리
- 필수 테스트 통과
- 시크릿 검사 통과
- 빌드 성공
- 실제 실행 확인
- 롤백 경로 확인
- changelog
- 배포 산출물 해시
- 최종 승인
```

검증 후 산출물이 변경되면 기존 승인은 무효다.

검증한 산출물과 배포 산출물의 해시가 같아야 한다.

자동 Git push와 자동 라이브 배포는 하지 않는다.

---

# 8. 롤백 표준

롤백할 수 없는 변경은 라이브에 적용하지 않는다.

최소 보존 대상:

```text
- 직전 정상 실행파일
- 직전 정상 설치파일
- 직전 정상 manifest
- 직전 정상 설정
- 직전 정상 커밋
- 마이그레이션 전 데이터 백업
```

코드 롤백과 데이터 롤백을 분리한다.

업데이트 실패 시 기존 정상 버전을 보존한다.

자동 복구된 실패 버전을 무한 재시도하지 않는다.

---

# 9. Phase 0
## 저장소 조사와 실행 계획

V4 Flash에 다음 프롬프트를 전달한다.

```text
[공통 절대 규칙을 먼저 붙여 넣는다]

Phase 0만 수행해라.

목표:
현재 작업 디렉터리와 Git 상태를 조사하고,
범용 AI Project Structure Standard 저장소를 구현하기 위한
검증 가능한 실행 계획을 작성한다.

이번 Phase에서는 핵심 구현 코드를 작성하지 않는다.
단, 작업 상태 기록용 최소 디렉터리와 문서는 만들 수 있다.

반드시 수행할 것:

1. 현재 디렉터리와 기존 파일 조사
2. Git 저장소 여부, 브랜치, HEAD, status 확인
3. 기존 파일과 충돌 가능성 확인
4. 최종 저장소 구조 초안 작성
5. 각 파일의 실제 책임 정의
6. 공통 모듈과 중복 방지 계획 작성
7. Phase 1부터 Phase 7까지 작업 범위 분리
8. 각 Phase의 테스트와 완료 조건 정의
9. 과도한 기능과 필수 기능 구분
10. 현재 상태 인계 문서 작성

생성할 파일:

- docs/IMPLEMENTATION_PLAN.md
- docs/FILE_RESPONSIBILITIES.md
- docs/TEST_PLAN.md
- docs/DECISIONS/ADR-0001-layered-coordinator.md
- .ai/CURRENT.md
- .ai/STATUS.md

ADR에는 다음을 명확히 기록해라.

- 거대한 단일 오케스트레이터를 사용하지 않는 이유
- 계층형 Domain Coordinator를 채택한 이유
- 최상위 Application Coordinator가 필요한 조건
- 기존 프로젝트에서 점진적으로 적용하는 방법
- 포기한 대안
- 예상 위험
- 롤백 방법

완료 전에 다음을 확인해라.

- 생성 문서가 서로 모순되지 않는가
- 다음 Phase가 파일 책임을 이해할 수 있는가
- 빈 템플릿만 만들지 않았는가
- Git diff를 확인했는가

최종 보고:

- 조사 결과
- 생성 파일
- 결정 사항
- Phase별 계획
- 실행한 명령
- 미실행 항목
- 다음 Phase 입력
```

## Phase 0 통과 조건

```text
[ ] Git 상태가 기록됨
[ ] 기존 파일 충돌 여부가 기록됨
[ ] 파일별 책임이 정의됨
[ ] Phase가 검증 가능한 단위로 나뉨
[ ] 계층형 Coordinator ADR이 작성됨
[ ] 구현을 시작하지 않고 설계를 고정함
```

---

# 10. Phase 1
## AI 서명, 체크포인트, 인계 하네스

```text
[공통 절대 규칙을 먼저 붙여 넣는다]

Phase 1만 수행해라.

먼저 다음을 읽어라.

- docs/IMPLEMENTATION_PLAN.md
- docs/FILE_RESPONSIBILITIES.md
- docs/TEST_PLAN.md
- docs/DECISIONS/ADR-0001-layered-coordinator.md
- .ai/CURRENT.md
- 현재 Git status와 diff

목표:
AI 작업 시작·종료 서명,
Git 체크포인트,
다른 AI 인계 번들을 실제로 생성하는 최소 하네스를 구현한다.

이번 Phase 구현 범위:

- scripts/common.py
- scripts/sign_ai_session.py
- scripts/checkpoint.py
- scripts/create_handoff.py
- schemas/ai_signature.schema.json
- templates/WORK_LOG.md
- templates/SESSION_HANDOFF.md
- templates/CURRENT.md
- templates/STATUS.md
- tests/test_signatures.py
- tests/test_checkpoint.py
- tests/test_handoff.py

필수 동작:

1. 시작 서명 생성
2. 종료 서명 생성
3. 실제 Git 브랜치, HEAD, status 자동 수집
4. diff hash 생성
5. actual_model_id를 확인할 수 없으면 UNKNOWN 기록
6. .ai/ledger.jsonl append-only 기록
7. previous_entry_hash와 current_entry_hash 연결
8. 체크포인트에 Git 상태, patch, 신규 파일, 현재 문서 저장
9. 체크포인트는 자동 commit을 만들지 않음
10. 단일 Markdown 인계 번들 생성
11. 인계 번들에 현재 상태, 변경, 테스트, 블로커, 다음 작업 포함
12. 민감정보 원문을 출력하지 않음

구현 후 실제로 수행:

- 임시 Git 저장소에서 시작 서명 생성
- 파일 하나 수정
- 체크포인트 생성
- 종료 서명 생성
- 인계 번들 생성
- ledger 해시 연결 검증
- 전체 관련 테스트 실행

완료 기준:

- 시작·종료 서명이 실제 JSONL에 기록됨
- 체크포인트가 실제 파일을 보존함
- 인계 번들이 이전 대화 없이 이해 가능함
- 테스트가 전부 통과함
- 실행하지 않은 검사는 NOT_RUN으로 남음

Phase 1 범위를 넘어 시크릿 검사나 릴리스 도구를 구현하지 마라.

종료 시 .ai/CURRENT.md, .ai/STATUS.md와 인계 기록을 갱신해라.
```

## Phase 1 통과 조건

```text
[ ] 시작 서명 생성 성공
[ ] 종료 서명 생성 성공
[ ] ledger append-only 검증
[ ] 해시 체인 검증
[ ] 체크포인트 생성 성공
[ ] 인계 번들 생성 성공
[ ] 관련 테스트 PASS
```

---

# 11. Phase 2
## Preflight와 프로젝트 설정

```text
[공통 절대 규칙을 먼저 붙여 넣는다]

Phase 2만 수행해라.

먼저 Phase 1 인계 번들과 현재 Git diff를 읽어라.

목표:
프로젝트를 수정하기 전에 상태와 위험 경계를 확인하는 preflight,
그리고 언어·프레임워크에 종속되지 않는 설정 체계를 구현한다.

구현 범위:

- scripts/preflight.py
- .ai-standard.example.yml
- schemas/project_config.schema.json 또는 동등한 검증 방식
- templates/AI_START_HERE.md
- templates/ARCHITECTURE.md
- templates/SECURITY.md
- tests/test_preflight.py

preflight 필수 확인:

- Git 저장소 여부
- 브랜치와 HEAD
- protected branch 여부
- 작업트리 상태
- 추적되지 않은 파일
- 필수 문서 존재
- 보호 파일 존재 여부
- 시크릿 파일이 Git에 추적되는지
- 실행 환경
- 테스트 도구 존재 여부
- 프로젝트 위험 등급
- 설정 파일 유효성

설정 파일은 다음을 지원한다.

- 프로젝트 이름
- 위험 등급
- protected branch
- 검증 명령
- 테스트 명령
- 금지 패턴
- 허용 예외
- 허용 도메인
- 필수 문서
- 보호 파일
- 릴리스 활성화 여부
- 사람 승인 필요 여부
- 롤백 필요 여부

설정 파일이 없을 때는 안전한 기본값으로 동작한다.

특정 언어만 지원하도록 하드코딩하지 않는다.

실제로 다음을 검증한다.

- 정상 임시 저장소
- Git이 아닌 폴더
- protected branch
- 미커밋 변경
- 잘못된 설정
- 필수 문서 누락

Phase 2 범위를 넘어 시크릿 탐지와 릴리스 manifest를 구현하지 마라.
```

---

# 12. Phase 3
## 시크릿 검사와 구조적 보안 검사

```text
[공통 절대 규칙을 먼저 붙여 넣는다]

Phase 3만 수행해라.

먼저 이전 Phase의 인계 번들, 테스트 결과, Git diff를 확인해라.

목표:
비용 없는 구조적 보안 규칙을 자동 검사하는 도구를 구현한다.

구현 범위:

- scripts/check_secrets.py
- scripts/check_forbidden_patterns.py
- docs/SECURITY_STANDARD.md
- templates/SECURITY.md
- tests/test_secret_scan.py
- tests/test_forbidden_patterns.py

시크릿 검사 대상:

- 소스 파일
- Git diff
- 설정 파일
- 로그
- 테스트 결과
- 빌드 산출물
- 압축 파일 내부의 텍스트 파일
- 개인키 형태
- Authorization 헤더
- 일반적인 API 키와 웹훅

실제 값을 출력하지 않는다.

출력 가능 정보:

- 파일
- 줄
- 패턴 종류
- 심각도
- 마스킹된 일부 문자열

금지 패턴 기본 후보:

- shell=True
- eval(
- exec(
- verify=False
- 0.0.0.0 바인딩
- 빈 except 또는 catch
- 예외 무조건 삼키기
- 하드코딩된 관리자 권한
- 개발용 인증 우회
- 사용자 입력 기반 subprocess
- 임의 URL 프록시
- 평문 비밀정보 fallback

모든 탐지를 무조건 오류로 처리하지 않는다.

프로젝트 설정에서 예외를 허용할 수 있지만,
다음이 필요하다.

- 정확한 파일 또는 범위
- 허용 이유
- 만료 또는 재검토 조건
- 관련 ADR 또는 문서

테스트에는 실제 비밀값을 쓰지 않고 synthetic token만 사용한다.

다음 검사를 실제 수행한다.

- 탐지되어야 할 샘플
- 탐지되면 안 되는 샘플
- 마스킹 검증
- 허용 예외 검증
- 압축 파일 검사
- Git diff 검사

유료 인증서, DRM, TPM, HSM, 안티디버깅은 구현하지 않는다.
```

---

# 13. Phase 4
## 표준 요청·결과·오류 스키마

```text
[공통 절대 규칙을 먼저 붙여 넣는다]

Phase 4만 수행해라.

목표:
도메인 Coordinator 사이에서 사용할 수 있는
언어 중립적인 요청, 결과, 오류 계약을 정의한다.

구현 범위:

- schemas/request.schema.json
- schemas/result.schema.json
- schemas/error.schema.json
- docs/ARCHITECTURE_STANDARD.md
- docs/ERROR_STANDARD.md
- templates/ERROR_CATALOG.md
- examples/python-desktop 최소 계약 예제
- examples/web-service 최소 계약 예제
- 관련 schema 검증 테스트

요청 스키마 최소 필드:

- request_id
- trace_id
- capability
- operation
- parameters
- caller
- priority
- timeout_ms
- created_at
- contract_version

결과 스키마 최소 필드:

- success
- data
- error
- source
- fetched_at
- is_stale
- trace_id
- duration_ms
- contract_version

오류 스키마 최소 필드:

- code
- trace_id
- category
- user_message
- retryable
- source
- details
- occurred_at

모든 필드를 무조건 필수로 만들지 말고,
실제 상호운용에 필요한 최소 필수값을 판단해라.

오류 코드와 trace_id 역할을 분리한다.

모든 함수에 오류 코드를 붙이는 설계를 금지한다.

예제는 계층형 구조를 보여야 한다.

- UI 또는 Route
- Domain Coordinator
- Service
- Adapter 또는 Repository

거대한 GlobalOrchestrator 예제를 만들지 않는다.
```

---

# 14. Phase 5
## 검증 실행기와 문서 정합성

```text
[공통 절대 규칙을 먼저 붙여 넣는다]

Phase 5만 수행해라.

목표:
프로젝트별 검증 명령을 실행하고
결과를 기계 판독 가능한 verification.json으로 저장하는 도구를 구현한다.

구현 범위:

- scripts/verify_project.py
- scripts/check_document_sync.py
- schemas/verification.schema.json
- docs/DOCUMENTATION_STANDARD.md
- docs/AI_WORKFLOW.md
- templates/RELEASE_CHECKLIST.md
- tests/test_project_verification.py
- tests/test_document_sync.py

verify_project 필수 동작:

- 설정 파일 읽기
- 문법 검사 실행
- 정적 분석 실행
- 단위 테스트 실행
- 사용자 정의 검사 실행
- 시크릿 검사 연결
- 금지 패턴 검사 연결
- git diff --check
- 검사별 시작·종료 시각
- 명령
- exit code
- PASS / FAIL / NOT_RUN
- 로그 위치
- 대상 커밋
- 결과 파일 hash

어떤 명령도 실행하지 않았는데 PASS로 기록하지 않는다.

문서 정합성 검사 예:

- README에 적힌 스크립트가 실제 존재하는지
- 필수 템플릿이 존재하는지
- 설정 파일의 명령이 비어 있지 않은지
- CURRENT와 STATUS가 모순되는지
- 완료라고 기록된 항목의 검증 증적이 존재하는지
- 오류 코드가 카탈로그에 등록됐는지

모든 자연어 문서 내용을 완벽히 판정하려 하지 않는다.
기계적으로 검증 가능한 핵심 불일치만 검사한다.
```

---

# 15. Phase 6
## 릴리스 manifest와 롤백 게이트

```text
[공통 절대 규칙을 먼저 붙여 넣는다]

Phase 6만 수행해라.

목표:
검증된 산출물만 릴리스 후보로 인정하고,
롤백 경로가 없으면 차단하는 도구를 구현한다.

구현 범위:

- scripts/create_release_manifest.py
- scripts/verify_release.py
- schemas/release_manifest.schema.json
- docs/RELEASE_STANDARD.md
- docs/ROLLBACK_STANDARD.md
- templates/DEPLOY_LOG.md
- templates/RUNBOOK.md
- tests/test_release_manifest.py
- tests/test_release_verification.py

release manifest 최소 정보:

- release_id
- version
- source_commit
- build_run_id
- artifact 목록
- 파일별 hash
- 파일 크기
- 전체 artifact hash
- manifest hash
- created_at
- verification_run_id
- rollback_point
- approved_by

verify_release 필수 검사:

- 작업트리 clean
- 대상 source commit 일치
- verification 결과 존재
- 필수 검사가 PASS
- FAIL 또는 NOT_RUN 여부
- artifact hash 일치
- manifest hash 일치
- 롤백 지점 존재
- 버전 중복과 내용 변경 여부
- 사람 승인 필요 프로젝트의 승인 필드

검증 후 artifact가 변경되면 차단한다.

실제 배포, Git push, GitHub Release 생성은 하지 않는다.

롤백 문서에는 다음을 포함한다.

- 코드 롤백과 데이터 롤백 분리
- 직전 정상본 보존
- 업데이트 실패 시 기존 버전 유지
- 실패 버전 무한 재시도 금지
- DB 마이그레이션 전 백업
- 복원 테스트
```

---

# 16. Phase 7
## SKILL, README, 예제, 전체 통합

```text
[공통 절대 규칙을 먼저 붙여 넣는다]

Phase 7만 수행해라.

이 Phase 전에는 Phase 1부터 Phase 6까지 실제 테스트 결과가 존재해야 한다.

목표:
완성된 도구와 규칙을 바탕으로
실제로 사용할 수 있는 SKILL.md, README, 문서 템플릿과 예제를 완성한다.

구현 범위:

- SKILL.md
- README.md
- AGENTS.example.md
- CONTRIBUTING.md
- CHANGELOG.md
- LICENSE
- docs/GIT_STANDARD.md
- docs/MIGRATION_GUIDE.md
- docs/EXAMPLES.md
- 나머지 필수 templates
- examples/python-desktop
- examples/web-service
- examples/existing-project-migration

SKILL.md 필수 내용:

1. 언제 사용하는지
2. 신규 프로젝트 적용
3. 기존 프로젝트 적용
4. 조사 우선 원칙
5. 계층형 Coordinator 판단 기준
6. 새 오케스트레이터 생성 금지 조건
7. Git 작업 절차
8. AI 시작·종료 서명
9. 체크포인트와 인계
10. 오류와 trace
11. 구조적 보안
12. 검증 게이트
13. 배포 금지 조건
14. 롤백
15. 완료 보고 형식

README 필수 순서:

- 소개
- 해결하는 문제
- 핵심 원칙
- 설치
- 빠른 시작
- 신규 프로젝트 적용
- 기존 프로젝트 적용
- 실제 실행 명령
- 저장소 구조
- AI 서명 예시
- 검증 예시
- 릴리스와 롤백
- 비목표
- 기여
- 라이선스

예제 조건:

- 최소 실행 가능
- 과도하게 큰 앱 금지
- 계층형 Coordinator 구조가 드러남
- 거대한 전역 오케스트레이터 금지
- README 명령으로 실행 가능
- 직접 API 호출과 상태 중복의 나쁜 예를 마이그레이션 예제에 포함
- 개선 전후 차이를 설명

최상위 원칙을 README와 SKILL에 반영해라.

- 중앙 계층은 통제하되 실제 기능을 독점하지 않는다.
- 같은 상태와 외부 경계에는 하나의 소유자를 둔다.
- 기록되지 않은 작업은 존재하지 않은 것으로 본다.
- 서명되지 않은 AI 변경은 정식 결과로 승인하지 않는다.
- AI 설명보다 Git diff와 실행 결과를 우선한다.
- 실행하지 않은 검사는 NOT_RUN이다.
- 검증되지 않은 산출물은 배포하지 않는다.
- 롤백할 수 없는 변경은 라이브에 적용하지 않는다.
- 시크릿은 코드, 로그, Git, 빌드에 넣지 않는다.
- 기존 정상 동작을 보존하며 점진적으로 개선한다.

완료 전에 README의 모든 명령을 직접 재현해라.
```

---

# 17. Phase 8
## 동일 모델 새 세션 감사

구현 세션을 종료한 뒤 V4 Flash 새 세션에서 실행한다.

```text
너는 구현자가 아니라 독립 감사자다.

구현자의 완료 보고를 신뢰하지 마라.
원본 FLASH_BUILD_PROMPT.md와 실제 저장소를 직접 대조해라.

먼저 다음을 수행해라.

1. Git 상태와 전체 파일 목록 확인
2. placeholder, TODO, pass, 빈 구현 검색
3. README의 모든 실행 명령 재현
4. 전체 테스트 실행
5. 시크릿 검사 실행
6. 금지 패턴 검사 실행
7. 샘플 저장소에서 preflight 실행
8. AI 시작 서명 생성
9. 체크포인트 생성
10. 종료 서명 생성
11. 인계 번들 생성
12. verification.json 생성
13. release manifest 생성
14. artifact 변조 후 verify_release 차단 확인
15. NOT_RUN이 PASS로 처리되지 않는지 확인

다음 문제를 집중적으로 찾아라.

- 문서에만 있고 구현되지 않은 기능
- 구현됐지만 테스트되지 않은 기능
- 테스트가 실제 기능을 검증하지 않는 경우
- JSON Schema와 Python 필드 불일치
- 특정 언어에 불필요하게 종속된 부분
- 거대한 전역 오케스트레이터로 변질된 예제
- Coordinator에 실제 기능 로직이 과도하게 들어간 부분
- Git 저장소가 아닌 환경에서의 실패
- Windows와 Unix 경로 차이
- 시크릿 원문 출력
- 검증 없이 릴리스가 통과되는 우회
- ledger 기존 항목 수정 가능성
- 해시 체인이 실제로 검증되지 않는 문제
- README 명령 불일치
- 빈 문서와 중복 문서

문제를 발견하면 실제로 수정하고 테스트를 다시 실행해라.

수정 후 최초 요구사항을 항목별 표로 대조해라.

각 항목 상태는 다음 중 하나만 사용한다.

- PASS
- FAIL
- NOT_RUN
- NOT_APPLICABLE

근거 없는 PASS를 기록하지 마라.
```

---

# 18. Phase 9
## 강한 모델 최종 감사용 선택 프롬프트

V4 Flash 결과를 Claude Sonnet, Opus, Codex 등으로 마지막 검수할 때 사용한다.

```text
이 저장소는 DeepSeek V4 Flash가 단계별로 구현한
범용 AI Project Structure Standard다.

너는 최종 독립 검수자다.

구현자의 문서와 완료 보고를 신뢰하지 말고,
FLASH_BUILD_PROMPT.md의 요구사항과 실제 코드,
Git diff, 테스트 결과를 직접 대조해라.

우선순위:

1. 실행 가능한가
2. 검증 게이트가 우회되지 않는가
3. AI 서명과 ledger가 실제로 이어지는가
4. 문서, 스키마, 코드가 일치하는가
5. 계층형 Coordinator 원칙이 제대로 반영됐는가
6. 기존 프로젝트를 과도하게 갈아엎도록 유도하지 않는가
7. 구조적 보안 규칙이 자동 검사로 연결되는가
8. 검증되지 않은 artifact가 release 검증을 통과하지 않는가
9. 롤백 경로가 실제 필수 조건인가
10. README 명령이 재현 가능한가

전체 테스트와 README 명령을 직접 실행해라.

발견한 문제는 보고만 하지 말고,
현재 범위에서 수정 가능한 것은 실제로 수정해라.

실행하지 않은 항목은 PASS로 기록하지 마라.

마지막 보고:

- 결론
- 실제 실행 명령
- 테스트 결과
- 수정한 문제
- 남은 FAIL
- 남은 NOT_RUN
- 사용 가능한 수준인지
- 공개 저장소로 배포하기 전 필요한 마지막 작업
```

---

# 19. Flash 작업 시 추가 통제 규칙

V4 Flash가 작업을 크게 벌이지 않도록 매 Phase에 다음 문구를 추가할 수 있다.

```text
이번 Phase에서 수정 가능한 파일 목록을 먼저 선언해라.

선언하지 않은 파일을 수정해야 한다면
수정 전에 이유를 CURRENT 문서에 기록해라.

한 파일이 500줄을 넘으면
책임이 섞였는지 먼저 검토해라.

Coordinator에는 다음만 허용한다.

- 요청 정규화
- 순서
- 중복 병합
- 상태
- 캐시 정책
- 타임아웃
- 취소
- 결과 조합
- 오류 정규화

실제 파일 처리, 네트워크 전송, DB 접근,
암호화, 파싱은 별도 Service, Adapter,
Repository 또는 Gateway에 둬라.

새 파일을 만들기 전에 같은 책임의 기존 파일을 검색해라.

테스트는 구현 내부를 그대로 복제하지 말고
외부에서 관찰 가능한 결과를 검증해라.
```

---

# 20. 실패 시 복구 프롬프트

Flash가 중간에 멈추거나 엉뚱한 작업을 했을 때 사용한다.

```text
새 기능을 추가하지 마라.

현재 저장소를 복구 모드로 조사해라.

1. 현재 Git status와 diff 확인
2. 마지막 정상 체크포인트 확인
3. 현재 Phase의 허용 범위 확인
4. 범위를 벗어난 변경 목록 작성
5. 정상 변경과 잘못된 변경 분리
6. 테스트 가능한 최소 상태로 복구
7. 기존 정상 변경을 임의로 삭제하지 않음
8. 실패 원인과 다음 실행 명령 기록
9. 인계 번들 생성

불명확한 변경을 임의로 완료 처리하지 마라.
필요하면 FAIL 상태로 남기되 다음 AI가 이어갈 수 있게 해라.
```

---

# 21. 최종 완료 체크리스트

```text
[ ] 계층형 Domain Coordinator 표준
[ ] 거대 전역 오케스트레이터 금지
[ ] 기존 프로젝트 점진적 마이그레이션
[ ] Git preflight
[ ] AI 시작 서명
[ ] AI 종료 서명
[ ] append-only ledger
[ ] ledger hash chain
[ ] 체크포인트
[ ] 다른 AI 인계 번들
[ ] 요청·결과·오류 스키마
[ ] 오류 코드와 trace ID 분리
[ ] 구조적 시크릿 보호
[ ] 시크릿 검사
[ ] 금지 패턴 검사
[ ] 프로젝트별 검증 실행기
[ ] PASS / FAIL / NOT_RUN
[ ] 문서 정합성 검사
[ ] release manifest
[ ] artifact hash 검증
[ ] 검증 후 변경 차단
[ ] 롤백 지점 필수
[ ] 코드 롤백과 데이터 롤백 분리
[ ] SKILL.md
[ ] README 명령 재현
[ ] Python 데스크톱 예제
[ ] 웹서비스 예제
[ ] 기존 프로젝트 마이그레이션 예제
[ ] 전체 테스트 PASS
[ ] 새 세션 독립 감사
[ ] Git push와 외부 배포 미실행
```

---

# 22. 최종 원칙

```text
중앙 계층은 통제하되 실제 기능을 독점하지 않는다.

같은 상태와 외부 경계에는 하나의 명확한 소유자를 둔다.

기록되지 않은 작업은 존재하지 않은 것으로 본다.

서명되지 않은 AI 변경은 정식 결과로 승인하지 않는다.

AI의 설명보다 Git diff와 실행 결과를 우선한다.

실행하지 않은 검사는 PASS가 아니라 NOT_RUN이다.

검증되지 않은 산출물은 배포하지 않는다.

검증 후 변경된 산출물은 다시 검증한다.

롤백할 수 없는 변경은 라이브에 적용하지 않는다.

운영 데이터로 테스트하지 않는다.

시크릿은 코드, 로그, Git, 빌드에 넣지 않는다.

문서는 계획이 아니라 현재 실제 상태를 기록한다.

기존 정상 동작을 보존하면서 점진적으로 개선한다.

라이브 서비스 유지가 새 기능 배포보다 우선한다.
```
