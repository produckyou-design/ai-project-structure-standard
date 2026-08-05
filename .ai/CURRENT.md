# CURRENT

- 갱신: Phase 8 독립 감사 완료, director 재검증 완료 (2026-08-05)

## Phase 8 독립 감사 결과 (완료)

새 세션(fable) 독립 감사자가 FLASH_BUILD_PROMPT.md §17 전 절차를 수행. 구현자(Phase 1~7)의 완료 보고를 신뢰하지 않고 원본 요구사항과 실제 저장소를 직접 대조함.

**발견·수정된 결함 5건** (director가 각각 직접 재검증, 아래는 재검증 결과):

1. **critical** — `release_manifest.json`이 없으면 매니페스트 의존 검사 7종이 전부 NOT_RUN이 되고 나머지가 PASS라서 **릴리스 게이트가 exit 0으로 통째로 열림** (검증·해시·롤백·승인 증적 없이 통과). `verify_release.py`에 `manifest_exists` 검사 추가로 차단.
   - director 재검증: 이 저장소에 실제로 `.ai/release_manifest.json`이 없는 상태에서 `python scripts/verify_release.py` 직접 실행 → `manifest_exists` FAIL, exit 1 확인 (라이브 재현).
2. **major** — ledger 해시 체인이 마지막 항목만 검증해 중간 항목 변조+재해시가 통과됨. `verify_ledger_chain()`으로 전체 체인 재계산 후 append.
   - director 재검증: `append_ledger()` 내부에서 실제로 호출되는 것을 소스로 확인.
3. **major** — 체크포인트가 untracked 디렉터리 내부 신규 파일(예: 새 모듈)을 누락. 재귀 복사로 수정.
4. **major급** — 커밋 0개(unborn) 브랜치에서 `git_branch`가 `N/A`를 반환해 protected_branch 검사가 무력화됨 — **이 저장소 자신이 그 상태로 PASS 통과 중이었음**. `symbolic-ref` 폴백으로 수정.
   - director 재검증: 수정 후 `python scripts/preflight.py` 실행 → `protected_branch: FAIL`(master, unborn) 확인 (라이브 재현). **이 저장소는 현재 preflight FAIL 상태** — 배포 전 첫 커밋 필요.
5. **minor** — 존재하지 않는 `--path`가 조용히 스캔 0건 → PASS. `missing_scan_path` FAIL 추가.

회귀 테스트 15개(`tests/test_phase8_audit_findings.py`) 신규 — director가 본문 확인, 실제 subprocess/report 필드 검증(가짜 assert 없음).

**전체 테스트**: 139 → **154 passed** (director 직접 재실행 확인).

문서 갱신(README/SKILL/RELEASE_STANDARD/CHANGELOG)도 12종→13종 검사 수로 일치시킴 — director 확인.

**감사자가 명시적으로 문제 없다고 확인한 항목**: 시크릿 원문 미노출, 스키마-코드 필드 일치, 언어 종속성 없음, Coordinator 로직 과잉 없음, Windows/Unix 경로 처리, 문서 오기(README-CLI 플래그) 추가 발견 0건.

**미수정 관찰 3건** (게이트 우회로 이어지지 않는 품질 항목, 보고만 됨): `common.sha256_file` 미사용 dead util, tar 아카이브 스캔 테스트 미커버(zip만), `verification_logs` 제외가 `.ai`를 직접 base로 줄 때는 미적용.

## 배포 전 필요 항목 (감사자 보고, STATUS.md 참고)

1. 첫 커밋 생성 + 브랜치 정책 결정 (현재 preflight FAIL 상태)
2. `.gitignore`에 `.ai/` 추적 여부 결정
3. `.ai-standard.yml` 예외 만료일(2026-12-31) 재검토
4. 저장소 명칭 통일: README "Airframe" / 디렉터리 "구조스킬" / 권장 slug "ai-project-structure-standard" 3중 — 사용자 확인 결과 "Airframe" 최종.

## 브랜딩 (director 직접 작업, 저비용·가역적) — "Airframe" 최종

- 사용자 요청으로 프로젝트 이름을 "Airframe"으로 제안·반영.
- 중간에 "ADP"(약자)로 변경했다가, 그 지시가 다른 스킬(agent-director)에 대한 것이었다는 정정을 받아 원래 제안인 "Airframe"으로 되돌림. README.md·SKILL.md 전체에 ADP 잔여 없음 확인(grep).
- 기술 slug `ai-project-structure-standard` 는 SKILL.md frontmatter `name:` 필드에 그대로 유지 (스킬 식별자 대규모 변경은 범위 밖으로 판단).
- 기존 명령·예제·구조 트리 등 검증된 절은 내용 변경 없이 유지.
- 재검증: `check_document_sync.py`(readme_references 21건 실존), `check_forbidden_patterns.py`, `check_secrets.py` 전부 exit 0.

## 현재 작업

- Phase 0 (저장소 조사와 실행 계획) — 완료
- Phase 1 (AI 서명, 체크포인트, 인계 하네스) — 완료
- Phase 2 (Preflight와 프로젝트 설정) — 완료
- Phase 3 (시크릿 검사와 구조적 보안 검사) — 완료
- Phase 4 (표준 요청·결과·오류 스키마) — 완료
- Phase 5 (검증 실행기와 문서 정합성) — 완료
- Phase 6 (릴리스 manifest와 롤백 게이트) — 완료
- Phase 7 (SKILL, README, 예제, 전체 통합) — 완료
- 다음 Phase: Phase 8 (동일 모델 새 세션 독립 감사) — 새 세션에서 수행 권장

## 진행 상황 (Phase 5~7, director 모드 위임 + 직접 재검증)

Phase 5~7은 director 모드로 두 implementer(T-001, T-003)에게 병렬/순차 위임했다.
director 가 각 완료 보고를 신뢰하지 않고 직접 diff·테스트·CLI 실행으로 재검증했다.

- [x] `scripts/verify_project.py`, `scripts/check_document_sync.py`, `schemas/verification.schema.json` — director 가 직접 구현 (Phase 5 스크립트)
- [x] `tests/test_project_verification.py`(11) + `tests/test_document_sync.py`(14) — T-001 구현, director 재검증
- [x] `docs/DOCUMENTATION_STANDARD.md`, `docs/AI_WORKFLOW.md`, `templates/RELEASE_CHECKLIST.md` — T-001 구현
- [x] 회귀 수정: `scripts/common.py` `collect_files()` 가 `.ai/verification_logs` 하위를 스캔에서 구조적으로 제외 (verify_project 실행 로그가 금지 패턴 검사기 자신의 출력을 재탐지하는 자기참조 오탐을 차단). director 지시로 T-001 이 수정.
- [x] `scripts/create_release_manifest.py`, `scripts/verify_release.py`(12개 게이트), `schemas/release_manifest.schema.json` — T-002 구현 (병렬 세션)
- [x] `docs/RELEASE_STANDARD.md`, `docs/ROLLBACK_STANDARD.md`, `templates/DEPLOY_LOG.md`, `templates/RUNBOOK.md` — T-002 구현
- [x] `tests/test_release_manifest.py`(12) + `tests/test_release_verification.py`(12) — T-002 구현. director 가 별도 임시 저장소에서 CLI 로 독립 재현: 정상 흐름 PASS, artifact 변조 후 `artifact_hashes` FAIL 로 실제 차단됨을 확인.
- [x] `SKILL.md`, `README.md`, `AGENTS.example.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE`, `docs/GIT_STANDARD.md`, `docs/MIGRATION_GUIDE.md`, `docs/EXAMPLES.md`, `templates/ADR_TEMPLATE.md` — T-003 구현
- [x] `examples/existing-project-migration/`(before: 직접 호출·상태 중복·오류 삼킴의 나쁜 예 / after: Entry→Coordinator→Service→Adapter) — T-003 구현. director 가 before/app.py, after/main.py 를 직접 실행해 확인.
- [x] `templates/AI_START_HERE.md` 의 존재하지 않는 `--scope` 플래그 문서 오류(T-003 이 발견·보고) — director 가 `--allowed-scope`/`--forbidden-scope` 로 직접 1줄 수정 (Phase 2 소유 파일의 사소한 오기 수정, 저비용·가역적 판단)

## 검증 결과 (director 직접 재실행, 2026-08-05)

- `python -m pytest tests/ -q` → **139 passed**
- `python scripts/check_secrets.py` → PASS (exit 0)
- `python scripts/check_forbidden_patterns.py` → PASS (exit 0) — verification_logs 자기참조 오탐 회귀를 director 가 직접 재확인 후 수정 확인
- `python scripts/check_document_sync.py` → PASS (pass 4 / fail 0 / not_run 2, exit 0). readme_references: README 참조 경로 21건 모두 존재
- `python scripts/preflight.py` → PASS (exit 0)
- `python examples/existing-project-migration/before/app.py` → exit 0 (director 직접 실행)
- `python examples/existing-project-migration/after/main.py A100 A101 A102` → exit 0, 표준 결과 봉투 출력 확인 (director 직접 실행)
- release 게이트 변조 차단 — director 가 별도 임시 저장소에서 독립 재현: artifact 변조 후 `verify_release` FAIL 확인 (exit 1)

## 허용 범위

- 이번 세션: director 모드로 Phase 5~7 을 위임·검증하며 진행했다.
- 커밋, Git push, 외부 배포는 하지 않는다.
- director 가 직접 수정한 파일(임계값 이하 저비용 수정으로 판단): `templates/AI_START_HERE.md` (1줄, 존재하지 않는 CLI 플래그 문서 오류)

## 블로커

- 없음.

## 알려진 이슈 (해결 안 함, 다음 세션 참고)

- 없음. (AI_START_HERE.md 플래그 오기는 위에서 수정 완료)

## 인계 메모

- 다음 권장 단계: Phase 8 (동일 모델 새 세션 독립 감사, FLASH_BUILD_PROMPT.md §17) — 이 저장소의 완료 보고를 신뢰하지 말고 원본 요구사항과 실제 코드를 대조. 사용자가 이 단계에서 추론 강도를 max 로 올릴 예정.
- Phase 8 감사 시 특히 확인할 것: (1) `.ai/verification_logs` 제외 수정이 다른 우회를 만들지 않는지, (2) release manifest artifact 경로가 상대/절대 혼용 시 안전한지, (3) Windows 경로·UTF-8 처리가 전 스크립트에 일관적인지, (4) README 명령이 실제 재현되는지 전체 재확인.
- `.ai-standard.yml` 의 허용 예외(만료 2026-12-31)를 재검토할 시점이 되면 갱신 필요.
