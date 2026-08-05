# IMPLEMENTATION_PLAN.md

- 상태: ACTIVE (Phase 0 완료)
- 최종 업데이트: Phase 0

이 문서는 `FLASH_BUILD_PROMPT.md`의 요구사항을 검증 가능한 단위로 나눈 실행 계획이다.
각 Phase는 독립 세션으로 실행하는 것을 원칙으로 하며, Phase를 건너뛰거나 범위를 넘어서 임의로 구현하지 않는다.

---

## 1. 저장소 조사 결과 (Phase 0)

### 1.1 현재 상태

| 항목 | 값 |
|---|---|
| 작업 디렉터리 | `C:\Project\Skills\구조스킬` |
| Git 저장소 | Phase 0에서 `git init`으로 생성 (기존 저장소 없음) |
| 기본 브랜치 | `master` (git 기본값) |
| 기존 파일 | `FLASH_BUILD_PROMPT.md` (마스터 프롬프트, 원본) |
| 제외 대상 | `.freebuff/` (Freebuff 클라이언트 데이터) → `.gitignore` 처리 |
| 커밋 | 없음 (Phase 0 종료 시점 기준) |

### 1.2 기존 파일 충돌 가능성

- 프로젝트 루트에 존재하는 파일은 마스터 프롬프트뿐이다.
- `docs/`, `scripts/`, `schemas/`, `templates/`, `examples/`, `tests/`, `.ai/` 는 전부 신규 생성 예정이며 충돌 없음.
- 예외: `templates/SECURITY.md`(Phase 3)와 `docs/SECURITY_STANDARD.md`는 책임을 구분해 중복을 피한다.

---

## 2. 최종 저장소 구조 (목표)

```text
구조스킬/                        (ai-project-structure-standard)
├── README.md
├── LICENSE
├── SKILL.md
├── AGENTS.example.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── FLASH_BUILD_PROMPT.md
├── .ai-standard.example.yml
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
│   ├── EXAMPLES.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── FILE_RESPONSIBILITIES.md
│   ├── TEST_PLAN.md
│   └── DECISIONS/
│       └── ADR-0001-layered-coordinator.md
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
│   ├── release_manifest.schema.json
│   └── project_config.schema.json
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
├── tests/
│   ├── test_signatures.py
│   ├── test_checkpoint.py
│   ├── test_handoff.py
│   ├── test_preflight.py
│   ├── test_secret_scan.py
│   ├── test_forbidden_patterns.py
│   ├── test_project_verification.py
│   ├── test_document_sync.py
│   ├── test_release_manifest.py
│   └── test_release_verification.py
│
└── .ai/
    ├── CURRENT.md
    ├── STATUS.md
    └── ledger.jsonl        (실행 시 append-only로 생성)
```

구조는 실제 구현 중 합리적으로 조정할 수 있다. 파일 수를 채우기 위한 빈 파일은 만들지 않는다.

---

## 3. Phase별 작업 범위와 완료 조건

### Phase 0 — 저장소 조사와 실행 계획 (본 Phase)

**목표:** 설계 고정. 핵심 구현 코드는 작성하지 않는다.

**생성:** `docs/IMPLEMENTATION_PLAN.md`, `docs/FILE_RESPONSIBILITIES.md`, `docs/TEST_PLAN.md`, `docs/DECISIONS/ADR-0001-layered-coordinator.md`, `.ai/CURRENT.md`, `.ai/STATUS.md`

**통과 조건:**
- [ ] Git 상태가 기록됨
- [ ] 기존 파일 충돌 여부가 기록됨
- [ ] 파일별 책임이 정의됨
- [ ] Phase가 검증 가능한 단위로 나뉨
- [ ] 계층형 Coordinator ADR이 작성됨
- [ ] 구현을 시작하지 않고 설계를 고정함

### Phase 1 — AI 서명, 체크포인트, 인계 하네스

**범위:** `common.py`, `sign_ai_session.py`, `checkpoint.py`, `create_handoff.py`, `ai_signature.schema.json`, `templates/WORK_LOG.md`, `templates/SESSION_HANDOFF.md`, `templates/CURRENT.md`, `templates/STATUS.md`, `tests/test_signatures.py`, `tests/test_checkpoint.py`, `tests/test_handoff.py`

**검증:** 임시 Git 저장소에서 시작/종료 서명 생성 → 파일 수정 → 체크포인트 → 종료 서명 → 인계 번들 → ledger 해시 체인 검증 → 관련 테스트 전체 실행.

**통과 조건:**
- [ ] 시작 서명 생성 성공
- [ ] 종료 서명 생성 성공
- [ ] ledger append-only 검증
- [ ] 해시 체인 검증
- [ ] 체크포인트 생성 성공
- [ ] 인계 번들 생성 성공
- [ ] 관련 테스트 PASS

### Phase 2 — Preflight와 프로젝트 설정

**범위:** `preflight.py`, `.ai-standard.example.yml`, `project_config.schema.json`, `templates/AI_START_HERE.md`, `templates/ARCHITECTURE.md`, `templates/SECURITY.md`, `tests/test_preflight.py`

**검증:** 정상 임시 저장소 / Git 아님 / protected branch / 미커밋 변경 / 잘못된 설정 / 필수 문서 누락을 각각 실제 실행.

**통과 조건:**
- [ ] preflight가 모든 위험 경계를 검사
- [ ] 설정 파일이 언어 비의존적 기본값으로 동작
- [ ] test_preflight PASS

### Phase 3 — 시크릿 검사와 구조적 보안 검사

**범위:** `check_secrets.py`, `check_forbidden_patterns.py`, `docs/SECURITY_STANDARD.md`, `templates/SECURITY.md`, `tests/test_secret_scan.py`, `tests/test_forbidden_patterns.py`

**검증:** 탐지 대상/비대상 샘플, 마스킹, 허용 예외, 압축 파일, Git diff 검사를 synthetic token으로 실행.

**통과 조건:**
- [ ] 시크릿 검사가 원문을 출력하지 않음
- [ ] 금지 패턴 검사가 설정 기반 예외를 지원
- [ ] 관련 테스트 PASS

### Phase 4 — 표준 요청·결과·오류 스키마

**범위:** `request/result/error.schema.json`, `docs/ARCHITECTURE_STANDARD.md`, `docs/ERROR_STANDARD.md`, `templates/ERROR_CATALOG.md`, `examples/python-desktop`·`examples/web-service` 최소 계약 예제, 스키마 검증 테스트

**검증:** 최소 필수 필드만 필수로 지정, 계층형 Coordinator 구조(UI → Coordinator → Service → Adapter)를 예제로 증명. 거대한 GlobalOrchestrator 예제 금지.

### Phase 5 — 검증 실행기와 문서 정합성

**범위:** `verify_project.py`, `check_document_sync.py`, `verification.schema.json`, `docs/DOCUMENTATION_STANDARD.md`, `docs/AI_WORKFLOW.md`, `templates/RELEASE_CHECKLIST.md`, `tests/test_project_verification.py`, `tests/test_document_sync.py`

**검증:** 명령 미실행을 PASS로 기록하지 않음. 기계적으로 판정 가능한 문서 불일치만 검사.

### Phase 6 — 릴리스 manifest와 롤백 게이트

**범위:** `create_release_manifest.py`, `verify_release.py`, `release_manifest.schema.json`, `docs/RELEASE_STANDARD.md`, `docs/ROLLBACK_STANDARD.md`, `templates/DEPLOY_LOG.md`, `templates/RUNBOOK.md`, `tests/test_release_manifest.py`, `tests/test_release_verification.py`

**검증:** 검증 후 artifact 변경 시 차단, 롤백 지점 필수. 실제 배포/Git push/GitHub Release는 하지 않음.

### Phase 7 — SKILL, README, 예제, 전체 통합

**범위:** `SKILL.md`, `README.md`, `AGENTS.example.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE`, `docs/GIT_STANDARD.md`, `docs/MIGRATION_GUIDE.md`, `docs/EXAMPLES.md`, 나머지 템플릿, 예제 3종

**검증:** README의 모든 명령을 직접 재현. 예제는 최소 실행 가능하며 나쁜 예(직접 API 호출/상태 중복)와 개선 전후를 포함.

### Phase 8 — 동일 모델 새 세션 독립 감사

구현 완료 후 **새 세션**에서 실행. 문서에만 있는 기능, 테스트 없는 기능, 스키마/코드 불일치, Windows/Unix 경로, 시크릿 원문 출력, 검증 우회, ledger 수정 가능성, README 명령 불일치를 조사. 발견 시 실제 수정 후 요구사항 대조표(PASS/FAIL/NOT_RUN/NOT_APPLICABLE) 작성.

### Phase 9 — 강한 모델 최종 감사 (선택)

V4 Flash 결과를 다른 강한 모델로 검수할 때 사용하는 프롬프트. 저장소 자체의 구현 범위에는 속하지 않는다.

---

## 4. 공통 모듈과 중복 방지

- `scripts/common.py`가 Git 조회, 해시, 설정 로드, JSONL 기록, 마스킹 유틸을 단일 소유.
- 시크릿 검사·금지 패턴 검사·문서 정합성은 각각 독립 CLI이지만 `common.py`의 I/O와 출력 포맷을 재사용.
- 동일 책임 파일 중복 생성 금지. 새 파일을 만들기 전 `FILE_RESPONSIBILITIES.md`를 먼저 확인한다.

## 5. 필수 기능 vs 과도한 기능

- **필수:** 계층형 Coordinator 표준, 서명/ledger/해시 체인, 체크포인트/인계, preflight, 시크릿·금지 패턴 검사, 3종 스키마, verification, release manifest+롤백 게이트, SKILL/README/예제.
- **제외(과도):** 유료 코드 서명, HSM/TPM 필수, DRM, 안티디버깅, 패커, 난독화, 백신 기능, 프로세스 감시, 하드웨어 지문, 상용 보안 솔루션.
- 배포 대상은 공개 저장소이며, Git push·GitHub Release·외부 배포는 모든 Phase에서 금지.

## 6. 실행 원칙

- 실행하지 않은 검사는 `NOT_RUN`으로 기록한다.
- 완료 보고보다 Git diff와 실제 실행 결과를 우선한다.
- 다음 Phase는 직전 Phase의 인계 번들과 실제 Git diff를 먼저 읽고 시작한다.
