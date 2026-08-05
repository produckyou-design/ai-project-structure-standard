# Changelog

이 프로젝트는 [Keep a Changelog](https://keepachangelog.com/) 형식을 따른다.

## [Unreleased] — Phase 8 독립 감사 (2026-08-05)

FLASH_BUILD_PROMPT.md §17 에 따른 새 세션 독립 감사에서 발견·수정된 항목.

### Fixed

- **(critical)** `scripts/verify_release.py` — release manifest 파일이 없으면
  manifest 의존 검사 7종이 전부 NOT_RUN 이 되고 나머지가 PASS 라서 전체 판정이
  PASS(exit 0) 로 나던 게이트 우회를 차단. `manifest_exists` 검사(필수 필드
  확인 포함)를 추가해 총 13종 검사가 됨.
- **(major)** `scripts/checkpoint.py` — 추적되지 않은 **디렉터리**(porcelain 이
  `dir/` 로 축약 보고) 내부의 신규 파일이 체크포인트에 보존되지 않던 문제 수정.
  내부 파일까지 펼쳐 복사하며, 체크포인트 저장소 자신은 재귀 복사에서 제외.
- **(major)** `scripts/common.py` `append_ledger` — 마지막 항목의 자기 해시만
  검사해 중간 항목 변조+재해시가 통과되던 문제 수정. append 전에 전체 해시
  체인(자기 무결성+연결 무결성)을 재계산하는 `verify_ledger_chain()` 추가.
- **(minor)** `scripts/common.py` `git_branch` — 커밋이 없는(unborn) 브랜치에서
  `N/A` 를 반환해 preflight 의 protected branch 검사가 무력화되던 문제 수정
  (`git symbolic-ref --short HEAD` 폴백).
- **(minor)** `scripts/check_secrets.py` / `scripts/check_forbidden_patterns.py` —
  존재하지 않는 `--path` 를 조용히 건너뛰어 "0건 탐지 → PASS" 가 되던 문제 수정
  (`missing_scan_path` FAIL 로 보고).
- 문서 정합: README 검증 예시 집계(pass 4/not_run 2), 릴리스 게이트 예시(13종),
  테스트 개수(154), `SKILL.md`·`docs/RELEASE_STANDARD.md` 의 12종→13종 표기.

### Added

- `tests/test_phase8_audit_findings.py` — 위 결함들의 회귀 방지 테스트 15개.

## [0.1.0] - 2026-08-05

Phase 0~7에 걸쳐 실제로 구현되고 테스트된 항목만 기록한다(계획 단계 항목은
포함하지 않는다).

### Added

**Phase 0 — 저장소 조사와 실행 계획**
- `docs/IMPLEMENTATION_PLAN.md`, `docs/FILE_RESPONSIBILITIES.md`,
  `docs/TEST_PLAN.md`
- `docs/DECISIONS/ADR-0001-layered-coordinator.md` — 계층형 Domain Coordinator
  채택 근거, 최상위 Application Coordinator 조건, 점진적 마이그레이션 절차

**Phase 1 — AI 서명, 체크포인트, 인계 하네스**
- `scripts/common.py` — Git 조회, 해시, append-only ledger, 시크릿 마스킹,
  실제 모델 ID 판정 공통 유틸
- `scripts/sign_ai_session.py` — AI 시작/종료 서명 생성, 해시 체인 연결
- `scripts/checkpoint.py` — Git 상태·patch·신규 파일·문서 스냅샷 (자동 commit 없음)
- `scripts/create_handoff.py` — 단일 Markdown 인계 번들 생성
- `schemas/ai_signature.schema.json`
- `templates/WORK_LOG.md`, `templates/SESSION_HANDOFF.md`,
  `templates/CURRENT.md`, `templates/STATUS.md`
- `tests/test_signatures.py`, `tests/test_checkpoint.py`, `tests/test_handoff.py`

**Phase 2 — Preflight와 프로젝트 설정**
- `scripts/preflight.py` — 12종 위험 경계 검사 (git_repo, protected_branch,
  worktree, untracked, required_document, protected_file,
  secret_files_tracked, environment, test_tool, verify_tool, config_valid,
  risk_level)
- `.ai-standard.example.yml`, `schemas/project_config.schema.json`
- `templates/AI_START_HERE.md`, `templates/ARCHITECTURE.md`,
  `templates/SECURITY.md`
- `tests/test_preflight.py`

**Phase 3 — 시크릿 검사와 구조적 보안 검사**
- `scripts/check_secrets.py` — 시크릿 원문 비노출 탐지 (마스킹 출력, 압축
  파일·Git diff 검사 포함)
- `scripts/check_forbidden_patterns.py` — 구조적 금지 패턴 탐지, 설정 기반
  예외(`allow_exceptions`) 지원
- `docs/SECURITY_STANDARD.md`
- `tests/test_secret_scan.py`, `tests/test_forbidden_patterns.py`

**Phase 4 — 표준 요청·결과·오류 스키마**
- `schemas/request.schema.json`, `schemas/result.schema.json`,
  `schemas/error.schema.json`
- `docs/ARCHITECTURE_STANDARD.md`, `docs/ERROR_STANDARD.md`
- `templates/ERROR_CATALOG.md`
- `examples/python-desktop/` — 노트 CLI 앱 (Entry→Coordinator→Service→Repository)
- `examples/web-service/` — 상태 서비스 (Route→Coordinator→Service→Adapter,
  127.0.0.1 바인딩)
- `tests/test_contract_schemas.py`

**Phase 5 — 검증 실행기와 문서 정합성**
- `scripts/verify_project.py` — 검증 명령·테스트·시크릿·금지패턴·
  `git diff --check` 실행, `.ai/verification.json` 저장 (미실행 항목은
  `NOT_RUN`으로 기록)
- `scripts/check_document_sync.py` — README 참조 경로·필수 문서·설정 명령·
  CURRENT/STATUS 정합성·오류 코드 카탈로그 등록 여부 검사
- `schemas/verification.schema.json`
- `tests/test_project_verification.py`, `tests/test_document_sync.py`

**Phase 6 — 릴리스 manifest와 롤백 게이트**
- `scripts/create_release_manifest.py` — artifact 바이너리 해시, manifest hash
- `scripts/verify_release.py` — 12종 검사(작업트리 clean, source commit 일치,
  verification 존재/PASS/해시 일치, artifact/전체/manifest 해시 일치,
  rollback_point, human_approval, release_enabled). 검증 후 artifact 변경 시
  차단 확인됨
- `schemas/release_manifest.schema.json`
- `docs/RELEASE_STANDARD.md`, `docs/ROLLBACK_STANDARD.md`
- `templates/DEPLOY_LOG.md`, `templates/RUNBOOK.md`
- `tests/test_release_manifest.py`, `tests/test_release_verification.py`

**Phase 7 — SKILL, README, 예제, 전체 통합**
- `SKILL.md`, `README.md`, `AGENTS.example.md`, `CONTRIBUTING.md`, `LICENSE`
- `docs/GIT_STANDARD.md`, `docs/MIGRATION_GUIDE.md`, `docs/EXAMPLES.md`
- `templates/ADR_TEMPLATE.md`
- `examples/existing-project-migration/` — `before/`(나쁜 예: UI의 직접 외부
  API 호출·상태 중복·오류 삼킴) / `after/`(개선 예: Entry→Coordinator→
  Service→Adapter) 대조, 8단계 마이그레이션 절차와 연결

**Phase 5 후속 (같은 릴리스에 포함)**
- `docs/AI_WORKFLOW.md`, `docs/DOCUMENTATION_STANDARD.md`,
  `templates/RELEASE_CHECKLIST.md` — 별도 세션에서 완성되어 이 릴리스에
  포함됨.

### Known limitations

- Phase 8(동일 모델 새 세션 독립 감사)은 이 저장소의 구현 범위가 아니라
  별도 감사 절차다 (`FLASH_BUILD_PROMPT.md` §17). 감사 결과는 위
  [Unreleased] 절에 기록되어 있다.
