# FILE_RESPONSIBILITIES.md

- 상태: ACTIVE (Phase 0 완료)
- 목적: 모든 파일의 단일 책임을 정의하여 중복 생성과 책임 혼재를 방지한다.
- 규칙: 새 파일을 만들기 전에 이 문서를 검색한다. 한 파일이 500줄을 넘으면 책임 분리를 검토한다.

---

## 1. 루트 문서

| 파일 | 책임 |
|---|---|
| `README.md` | 영어판 저장소 소개 (GitHub 기본 노출본). 내용은 `README.ko.md`와 1:1 대응 |
| `README.ko.md` | 한국어판 저장소 소개 (원본). 해결 문제, 핵심 원칙, 설치·빠른 시작, 적용 방법, 실행 명령, 구조, 라이선스 (Phase 7) |
| `LICENSE` | 공개 배포 라이선스 (Phase 7) |
| `SKILL.md` | AI 스킬 정의: 사용 시점, 적용 절차, 계층형 Coordinator 판단 기준, 서명·검증·배포 규칙 (Phase 7) |
| `AGENTS.example.md` | 에이전트 규칙 예시: 조사 우선, 서명, 인계, 검증 게이트 (Phase 7) |
| `CHANGELOG.md` | 버전별 변경 기록 (Phase 7 이후 유지) |
| `CONTRIBUTING.md` | 기여 절차, 테스트·검증 요구 (Phase 7) |
| `FLASH_BUILD_PROMPT.md` | 이 저장소의 마스터 프롬프트 (원본, 수정 금지) |
| `.ai-standard.example.yml` | 프로젝트 설정 예시 (Phase 2) |
| `.gitignore` | 클라이언트 데이터·Python 부산물 제외 (Phase 0) |

## 2. docs/ — 표준 문서

| 파일 | 책임 |
|---|---|
| `IMPLEMENTATION_PLAN.md` | 실행 계획, Phase 분리, 통과 조건 (본 문서, Phase 0) |
| `FILE_RESPONSIBILITIES.md` | 파일별 단일 책임 목록 (본 문서, Phase 0) |
| `TEST_PLAN.md` | 테스트 계획과 완료 조건 (Phase 0) |
| `DECISIONS/ADR-0001-layered-coordinator.md` | 계층형 Coordinator 채택 근거 (Phase 0) |
| `ARCHITECTURE_STANDARD.md` | 계층 구조, Coordinator 책임, 중앙화 경계 (Phase 4) |
| `AI_WORKFLOW.md` | AI 작업 흐름: 조사→서명→구현→검증→인계 (Phase 5) |
| `GIT_STANDARD.md` | Git 상태 확인, 브랜치, 서명 연계 (Phase 7) |
| `SECURITY_STANDARD.md` | 구조적 보안 규칙과 자동 검사 연결 (Phase 3) |
| `ERROR_STANDARD.md` | 오류 코드와 trace_id 분리, 경계 목록 (Phase 4) |
| `DOCUMENTATION_STANDARD.md` | 문서가 현재 상태를 반영하는 규칙, 정합성 검사 (Phase 5) |
| `RELEASE_STANDARD.md` | 릴리스 전 필수 조건, 검증 후 변경 금지 (Phase 6) |
| `ROLLBACK_STANDARD.md` | 코드/데이터 롤백 분리, 직전 정상본 보존 (Phase 6) |
| `MIGRATION_GUIDE.md` | 기존 프로젝트 점진적 적용 (Phase 7) |
| `EXAMPLES.md` | 예제 사용법과 나쁜 예/좋은 예 대조 (Phase 7) |

## 3. templates/ — 프로젝트에 복사해 쓰는 템플릿

| 파일 | 책임 |
|---|---|
| `AI_START_HERE.md` | AI가 처음 진입할 때 읽는 시작 문서 (Phase 2) |
| `ARCHITECTURE.md` | 프로젝트 계층 구조 기록 (Phase 2) |
| `CURRENT.md` | 현재 작업 중 상태 (Phase 1) |
| `STATUS.md` | 항목별 PASS/FAIL/NOT_RUN 상태표 (Phase 1) |
| `WORK_LOG.md` | 작업 로그 (Phase 1) |
| `SESSION_HANDOFF.md` | 다음 AI 인계 번들 (Phase 1) |
| `ERROR_CATALOG.md` | 오류 코드 카탈로그 (Phase 4) |
| `RUNBOOK.md` | 운영 절차 (Phase 6) |
| `RELEASE_CHECKLIST.md` | 배포 전 체크리스트 (Phase 5) |
| `DEPLOY_LOG.md` | 배포 기록 (Phase 6) |
| `SECURITY.md` | 구조적 보안 적용 사항 (Phase 2/3) |
| `ADR_TEMPLATE.md` | ADR 양식 (Phase 7) |

## 4. schemas/ — 언어 중립 계약

| 파일 | 책임 |
|---|---|
| `ai_signature.schema.json` | AI 시작·종료 서명 필드 (Phase 1) |
| `project_config.schema.json` | `.ai-standard.yml` 검증 (Phase 2) |
| `request.schema.json` | 요청 계약 (Phase 4) |
| `result.schema.json` | 결과 계약 (Phase 4) |
| `error.schema.json` | 오류 계약 (Phase 4) |
| `verification.schema.json` | 검증 결과 저장 포맷 (Phase 5) |
| `release_manifest.schema.json` | 릴리스 매니페스트 (Phase 6) |

## 5. scripts/ — 실행 도구

| 파일 | 책임 |
|---|---|
| `common.py` | 공통 유틸: Git 조회, 해시, 설정 로드, JSONL, 마스킹, 경로 처리 (모든 스크립트가 재사용) |
| `sign_ai_session.py` | AI 시작·종료 서명 생성, ledger append (Phase 1) |
| `checkpoint.py` | Git 상태·patch·신규 파일·문서 스냅샷 (자동 commit 없음) (Phase 1) |
| `create_handoff.py` | 단일 Markdown 인계 번들 생성 (Phase 1) |
| `preflight.py` | 작업 전 위험 경계 검사 (Phase 2) |
| `check_secrets.py` | 시크릿 원문 비노출 탐지 (Phase 3) |
| `check_forbidden_patterns.py` | 금지 패턴 탐지, 설정 예외 지원 (Phase 3) |
| `verify_project.py` | 검증 명령 실행, verification.json 저장 (Phase 5) |
| `check_document_sync.py` | 기계적 문서 정합성 검사 (Phase 5) |
| `create_release_manifest.py` | 릴리스 매니페스트 생성, artifact hash (Phase 6) |
| `verify_release.py` | 릴리스 검증 게이트, 롤백 지점 확인 (Phase 6) |

## 6. examples/ — 실행 가능한 예제

| 경로 | 책임 |
|---|---|
| `python-desktop/` | 데스크톱 앱 계층형 구조 최소 예제 (Phase 4에서 계약, Phase 7에서 완성) |
| `web-service/` | 웹 서비스 계층형 구조 최소 예제 (Phase 4에서 계약, Phase 7에서 완성) |
| `existing-project-migration/` | 기존 프로젝트 점진적 마이그레이션 예제 (Phase 7) |

공통 원칙: 거대한 전역 오케스트레이터 금지. UI/Route → Domain Coordinator → Service → Adapter/Repository 계층을 보여준다.

## 7. tests/ — 검증

| 파일 | 책임 |
|---|---|
| `test_signatures.py` | 서명 생성·ledger·해시 체인 (Phase 1) |
| `test_checkpoint.py` | 체크포인트 파일 보존 (Phase 1) |
| `test_handoff.py` | 인계 번들 내용·민감정보 미출력 (Phase 1) |
| `test_preflight.py` | preflight 시나리오 (Phase 2) |
| `test_secret_scan.py` | 시크릿 탐지·마스킹·예외·압축·diff (Phase 3) |
| `test_forbidden_patterns.py` | 금지 패턴 탐지·예외 (Phase 3) |
| `test_project_verification.py` | verify_project 동작 (Phase 5) |
| `test_document_sync.py` | 문서 정합성 (Phase 5) |
| `test_release_manifest.py` | 매니페스트 생성·해시 (Phase 6) |
| `test_release_verification.py` | 검증 게이트·변조 차단 (Phase 6) |

## 8. .ai/ — 작업 상태 기록

| 파일 | 책임 |
|---|---|
| `CURRENT.md` | 현재 진행 중 작업, 허용 범위, 블로커 (각 Phase 종료 시 갱신) |
| `STATUS.md` | 요구사항 대조 상태표 (PASS/FAIL/NOT_RUN) |
| `ledger.jsonl` | append-only AI 작업 서명 기록 (스크립트가 생성·추가) |

## 9. 책임 경계 규칙

- Coordinator는 요청 정규화·순서·중복 병합·상태·캐시 정책·타임아웃·취소·결과 조합·오류 정규화만 담당.
- 실제 파일 처리, 네트워크 전송, DB 접근, 암호화, 파싱은 Service/Adapter/Repository/Gateway에 둔다.
- `templates/SECURITY.md`와 `docs/SECURITY_STANDARD.md`는 각각 "프로젝트 적용 기록"과 "표준 정의"로 책임이 다르다.
