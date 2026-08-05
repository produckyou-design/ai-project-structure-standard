# Airframe

*(working slug: `ai-project-structure-standard`)*

AI가 여러 세션에 걸쳐 혼자 코드를 계속 짜게 두면, 결국 둘 중 하나로 무너진다.
UI가 DB와 외부 API를 아무 데서나 직접 찔러 상태가 사방에서 중복되거나 —
반대로 이걸 막겠다고 모든 로직을 삼킨 거대한 전역 오케스트레이터 하나가
탄생한다. 둘 다 "구조가 없어서" 생기는 사고다.

더 근본적인 문제는 따로 있다. **AI는 "테스트를 통과했습니다"라고 말할 수 있고,
그 말이 사실인지 확인할 방법이 이전에는 없었다.** 다음 세션의 AI(또는 다음
사람)는 그 진술을 믿거나, 처음부터 다시 확인하는 수밖에 없었다.

Airframe은 항공기의 뼈대(airframe)가 그렇듯, AI가 짜는 코드 아래 놓이는
구조적 골격이다 — 계층을 강제하고, 이륙 전 점검(preflight)을 거치게 하고,
모든 작업에 조종사 서명과 블랙박스 기록(해시 체인 ledger)을 남기고, 검증을
통과하지 못한 화물은 게이트에서 막는다. 추상적 권고가 아니라 실제로 실행되는
스크립트·스키마·템플릿·예제로 강제한다 — 이 README에 적힌 명령은 전부 실제로
돌려서 확인한 것이다.

특정 언어·프레임워크에 종속되지 않는다. 표준 자체의 도구(`scripts/`)는
Python으로 구현되어 있지만, 계층 구조·서명·검증·릴리스 원칙은 어떤 언어의
프로젝트에도 적용할 수 있다.

## 해결하는 문제

AI가 여러 세션에 걸쳐 코드를 작성하면 다음 문제가 반복된다.

- 기능이 커질수록 UI가 DB·외부 API를 직접 호출하는 경로가 늘어나고, 같은 상태를
  여러 곳이 중복 보관해 회귀가 발생한다.
- 반대로 이를 막으려고 만든 거대한 전역 오케스트레이터(GlobalOrchestrator)가
  모든 도메인 로직을 떠안아 수정 비용과 병목이 폭발한다.
- 어떤 AI가, 어떤 범위를, 실제로 검증했는지 기록이 없어 다음 세션(또는 다음
  AI)이 이전 작업을 신뢰할 수 없다.
- "테스트를 실행했다"는 진술과 실제 실행 여부를 구분할 방법이 없다.
- 검증되지 않았거나 검증 후 변조된 산출물이 그대로 배포된다.
- 롤백 경로 없이 배포되어 장애 시 되돌릴 방법이 없다.

이 저장소는 이 문제들을 추상적 권고가 아니라 실행 가능한 스크립트·스키마·
템플릿·예제로 강제한다.

## 왜 "Airframe"인가

이름은 장식이 아니라 실제 구조를 그대로 옮긴 것이다 — 아래 용어들은 전부
`scripts/`에 실제로 존재하는 도구다.

| 항공 용어 | 이 표준에서 | 실제 도구 |
|---|---|---|
| Preflight (이륙 전 점검) | 작업 착수 전 위험 경계 확인 | `scripts/preflight.py` |
| 조종사 서명 / 비행 기록 | AI 시작·종료 서명 | `scripts/sign_ai_session.py` |
| 블랙박스 (변조 불가 기록) | 해시 체인 ledger | `.ai/ledger.jsonl` |
| 교대 인수인계 브리핑 | 다음 AI/세션 인계 번들 | `scripts/create_handoff.py` |
| 화물 매니페스트 | 릴리스 산출물 목록·해시 | `scripts/create_release_manifest.py` |
| 관제탑 게이트 | 배포 전 검증 통과 여부 | `scripts/verify_release.py` |
| 비상 절차 | 롤백 지점·데이터/코드 롤백 분리 | `docs/ROLLBACK_STANDARD.md` |

핵심 규율 하나: **체크리스트에 없는 항목은 통과(PASS)가 아니라 미실행
(NOT_RUN)으로 남는다.** 확인하지 않은 걸 확인했다고 적지 않는다 — 이게
전체 표준을 관통하는 단 하나의 규칙이다.

## 핵심 원칙

- 중앙 계층은 통제하되 실제 기능을 독점하지 않는다.
- 같은 상태와 외부 경계에는 하나의 명확한 소유자를 둔다.
- 기록되지 않은 작업은 존재하지 않은 것으로 본다.
- 서명되지 않은 AI 변경은 정식 결과로 승인하지 않는다.
- AI의 설명보다 Git diff와 실행 결과를 우선한다.
- 실행하지 않은 검사는 PASS가 아니라 NOT_RUN이다.
- 검증되지 않은 산출물은 배포하지 않으며, 검증 후 변경된 산출물은 다시 검증한다.
- 롤백할 수 없는 변경은 라이브에 적용하지 않는다.
- 시크릿은 코드, 로그, Git, 빌드에 넣지 않는다.
- 기존 정상 동작을 보존하면서 점진적으로 개선한다 (한 번에 전면 재작성 금지).

## 말이 아니라 실행 결과로

이 문서에 적힌 숫자와 명령은 전부 실제로 실행해서 얻은 것이다 — 주장이 아니라
재현 가능한 결과다.

- `python -m pytest tests/ -q` → **154개 테스트 통과** (아래 "실제 실행 명령"의
  모든 도구가 대상, Phase 8 독립 감사의 회귀 테스트 포함).
- 릴리스 게이트가 실제로 막는다: 검증을 통과한 산출물의 파일 내용을 바꾼 뒤
  다시 검사하면 `artifact_hashes`가 FAIL로 걸린다 — [아래 "릴리스와 롤백"](#릴리스와-롤백)에
  실제 재현 결과 그대로 있다.
- ledger는 append-only 해시 체인이다 — 과거 항목을 고치면 다음 기록 시도가
  무결성 위반으로 거부된다 ([아래 "AI 서명 예시"](#ai-서명-예시)).
- 예제 3종(`examples/`)은 전부 실제로 실행 가능하다 — README에 적힌 명령
  그대로 복사해서 돌리면 된다.

과장할 필요가 없다. 확인 안 된 건 NOT_RUN이라고 적는 도구가, 스스로에 대해
확인 안 된 걸 PASS라고 적을 이유가 없다.

## 설치

이 저장소를 프로젝트에 "적용"하는 방법은 두 가지다.

**A. 스킬로 참조한다** — 이 저장소 경로를 그대로 두고, 작업 시 `SKILL.md`를
읽게 한다. 스크립트는 절대/상대 경로로 직접 호출한다.

```bash
python /path/to/ai-project-structure-standard/scripts/preflight.py --workspace .
```

**B. 프로젝트에 필요한 부분만 복사한다** — 최소한 다음을 프로젝트 루트에 복사한다.

```bash
cp -r scripts schemas <대상 프로젝트>/
cp templates/AI_START_HERE.md templates/ARCHITECTURE.md templates/CURRENT.md \
   templates/STATUS.md <대상 프로젝트>/
cp .ai-standard.example.yml <대상 프로젝트>/.ai-standard.yml
```

`.ai-standard.yml`(또는 `.json`/`.yaml`)이 없어도 모든 도구는 안전한 기본값으로
동작한다 — 설정은 선택 사항이다.

## 빠른 시작

```bash
# 1) 위험 경계 확인 (Git 저장소 여부, protected branch, 미커밋 변경 등)
python scripts/preflight.py

# 2) 작업 시작 서명
python scripts/sign_ai_session.py start --task "이번에 할 일 설명" \
  --allowed-scope "수정할 파일 목록" --forbidden-scope "건드리지 않을 파일"

# 3) ...코드 작업...

# 4) 시크릿·금지 패턴 검사 + 프로젝트 검증
python scripts/check_secrets.py
python scripts/check_forbidden_patterns.py
python scripts/verify_project.py

# 5) 작업 종료 서명과 인계 번들
python scripts/sign_ai_session.py end --status success --tests-run "pytest" \
  --tests-passed "N" --tests-failed "0"
python scripts/create_handoff.py
```

## 신규 프로젝트 적용

1. `templates/AI_START_HERE.md`, `templates/ARCHITECTURE.md`,
   `templates/CURRENT.md`, `templates/STATUS.md`를 프로젝트 루트(또는 `docs/`)에
   복사하고 값을 채운다.
2. `.ai-standard.example.yml`을 `.ai-standard.yml`로 복사하고 프로젝트 위험
   등급·protected branch·검증 명령을 채운다.
3. 도메인이 정해지면 `docs/ARCHITECTURE_STANDARD.md`를 따라 Entry → Domain
   Coordinator → Service → Adapter 계층으로 시작한다. 처음부터 최상위
   Application Coordinator를 만들지 않는다(필요 조건은 `SKILL.md` §5·§6).
4. `examples/python-desktop/` 또는 `examples/web-service/`를 뼈대로 복사해
   도메인 이름만 바꿔 시작해도 된다 (`docs/EXAMPLES.md` §5).
5. 작업마다 `SKILL.md` §7~§9의 절차(서명 → 작업 → 검증 → 인계)를 따른다.

## 기존 프로젝트 적용

한 번에 전면 재작성하지 않는다. `docs/MIGRATION_GUIDE.md`의 8단계
(현재 호출 경로 조사 → 상태 소유자 조사 → 직접 호출·우회 경로 목록화 →
기존 Coordinator/Gateway 재사용 판단 → 위험 경계부터 중앙화 → 기능별 점진
이전 → 회귀 테스트 → 레거시 경로 제거)를 따른다.

실행 가능한 나쁜 예/좋은 예 대조는 `examples/existing-project-migration/`에
있다.

```bash
python examples/existing-project-migration/before/app.py   # 나쁜 예: 직접 호출·상태 중복·오류 삼킴
python examples/existing-project-migration/after/main.py A100 A101 A999  # 개선 예
```

## 실제 실행 명령

| 목적 | 명령 |
|---|---|
| 위험 경계 확인 | `python scripts/preflight.py` |
| AI 시작 서명 | `python scripts/sign_ai_session.py start --task "..."` |
| AI 종료 서명 | `python scripts/sign_ai_session.py end --status success` |
| 체크포인트 | `python scripts/checkpoint.py --name <이름>` |
| 인계 번들 생성 | `python scripts/create_handoff.py` |
| 시크릿 검사 | `python scripts/check_secrets.py` |
| 금지 패턴 검사 | `python scripts/check_forbidden_patterns.py` |
| 프로젝트 검증 실행 | `python scripts/verify_project.py` |
| 문서 정합성 검사 | `python scripts/check_document_sync.py` |
| 릴리스 manifest 생성 | `python scripts/create_release_manifest.py --version <버전> --artifacts <파일...> --rollback-point <지점> --approved-by <이름>` |
| 릴리스 게이트 검사 | `python scripts/verify_release.py` |
| 전체 테스트 | `python -m pytest tests/ -q` |

각 스크립트의 전체 옵션은 `--help`로 확인한다 (예: `python scripts/preflight.py --help`).

## 저장소 구조

```text
ai-project-structure-standard/
├── README.md  LICENSE  SKILL.md  AGENTS.example.md  CHANGELOG.md  CONTRIBUTING.md
├── docs/
│   ├── ARCHITECTURE_STANDARD.md   GIT_STANDARD.md        SECURITY_STANDARD.md
│   ├── ERROR_STANDARD.md          RELEASE_STANDARD.md    ROLLBACK_STANDARD.md
│   ├── MIGRATION_GUIDE.md         EXAMPLES.md
│   ├── IMPLEMENTATION_PLAN.md     FILE_RESPONSIBILITIES.md   TEST_PLAN.md
│   └── DECISIONS/ADR-0001-layered-coordinator.md
├── templates/   (AI_START_HERE, ARCHITECTURE, CURRENT, STATUS, WORK_LOG,
│                 SESSION_HANDOFF, ERROR_CATALOG, RUNBOOK, DEPLOY_LOG,
│                 SECURITY, ADR_TEMPLATE 등 — 프로젝트에 복사해 쓰는 양식)
├── schemas/     (request/result/error/ai_signature/project_config/
│                 verification/release_manifest .schema.json)
├── scripts/     (common, preflight, sign_ai_session, checkpoint, create_handoff,
│                 check_secrets, check_forbidden_patterns, verify_project,
│                 check_document_sync, create_release_manifest, verify_release)
├── examples/
│   ├── python-desktop/               노트 CLI 앱 (Entry→Coordinator→Service→Repository)
│   ├── web-service/                  상태 서비스 (Route→Coordinator→Service→Adapter)
│   └── existing-project-migration/   before(나쁜 예) / after(개선 예)
└── tests/       (13개 파일, `python -m pytest tests/ -q`)
```

## AI 서명 예시

아래는 임시 데모 저장소에서 실제로 실행해 얻은 출력이다(경로·시각은 실행
환경마다 다르다). 값은 `scripts/common.mask_sensitive`로 마스킹된 것을 그대로
옮겼다 — 시크릿 원문은 여기에도 저장소 어디에도 남지 않는다.

```bash
python scripts/sign_ai_session.py start --task "데모: README 예시 수정" \
  --provider anthropic --claimed-model claude-sonnet-5 --role implementer \
  --effort medium --allowed-scope "README.md" --forbidden-scope "없음"
```

```json
{
  "kind": "start",
  "run_id": "run_20260804T2229360000_b92d35",
  "provider": "anthropic",
  "actual_model_id": "UNKNOWN",
  "claimed_model": "claude-sonnet-5",
  "role": "implementer",
  "branch": "feature/demo",
  "base_commit": "a4a5b084a79c3790331884e947cdc6ea0aefb045",
  "task": "데모: README 예시 수정",
  "allowed_scope": "README.md",
  "previous_entry_hash": "",
  "entry_hash": "9f09d788c1b38f97c2a63888636a66f9ee1535aa9261c8793450ceb6ec2f23fc"
}
ledger: <workspace>/.ai/ledger.jsonl
```

`actual_model_id`는 환경변수(`AI_ACTUAL_MODEL_ID` 등)로 확인할 수 없으면
언제나 `UNKNOWN`으로 기록된다 — AI의 자기 신고(`claimed_model`)를 검증된 값으로
단정하지 않는다.

```bash
python scripts/sign_ai_session.py end --status success \
  --tests-passed "0" --tests-failed "0" --documents-updated "README.md"
```

```json
{
  "kind": "end",
  "run_id": "run_20260804T2229360000_b92d35",
  "status": "success",
  "end_commit": "a4a5b084a79c3790331884e947cdc6ea0aefb045",
  "diff_hash": "bb859cbb91163eb52170a92e2c104682b3514e1e95219ca81729286231e7f758",
  "changed_files": ["README.md", ".ai/"],
  "previous_entry_hash": "9f09d788c1b38f97c2a63888636a66f9ee1535aa9261c8793450ceb6ec2f23fc",
  "entry_hash": "a03880be5bfb89644a0e382e0b34d0ede0419d5e268974645c8e93c9d30e930c"
}
```

`entry_hash`가 이전 항목의 `previous_entry_hash`로 이어져 해시 체인을 이룬다.
`.ai/ledger.jsonl`의 기존 항목을 고치면 이 연결이 끊어지고, 다음 `append_ledger`
호출이 무결성 위반으로 거부한다.

## 검증 예시

```bash
python scripts/verify_project.py
```

```text
verification: PASS  (commit: 8ee015c83c22, pass 5 / fail 0 / not_run 0)
  [PASS   ] verify:python: exit code 0
  [PASS   ] tests: exit code 0
  [PASS   ] secrets: exit code 0
  [PASS   ] forbidden_patterns: exit code 0
  [PASS   ] git_diff_check: exit code 0
result: <workspace>/.ai/verification.json
```

결과는 `schemas/verification.schema.json`을 따르는 `.ai/verification.json`으로
저장된다. 어떤 검사도 실행하지 않았다면 그 검사는 `NOT_RUN`으로 남고 `PASS`로
집계되지 않는다.

```bash
python scripts/check_document_sync.py
```

```text
document sync: PASS  (pass 4 / fail 0 / not_run 2)
  [PASS   ] readme_references: README 참조 경로 N건 모두 존재
  [NOT_RUN] required_documents: 설정에 필수 문서 미지정
  [PASS   ] config_commands: 설정 명령이 비어 있지 않음
  [PASS   ] current_status: CURRENT/STATUS 모순 없음
  [PASS   ] status_evidence: PASS 항목의 근거 칸이 채워져 있음
  [NOT_RUN] error_codes: 프로젝트 ERROR_CATALOG.md 없음 (templates/ 는 양식이므로 제외)
```

## 릴리스와 롤백

```bash
python scripts/create_release_manifest.py --version 0.1.0 --artifacts dist/app.txt \
  --verification .ai/verification.json --rollback-point <직전 정상 커밋> \
  --approved-by "승인자"
python scripts/verify_release.py
```

```text
verify_release: PASS  (release_id: rel_20260804T2337000000_1b44ae, version: 0.1.0, pass 13 / fail 0 / not_run 0)
  [PASS   ] worktree_clean  [PASS] manifest_exists  [PASS] source_commit_match
  [PASS   ] verification_exists  [PASS] verification_passed  [PASS] verification_hash
  [PASS   ] verification_run_match  [PASS] artifact_hashes  [PASS] total_hash
  [PASS   ] manifest_hash  [PASS] rollback_point  [PASS] human_approval
  [PASS   ] release_enabled
```

검증 이후 artifact 파일 내용을 바꾸고 다시 실행하면(실제로 재현한 결과):

```text
verify_release: FAIL  (pass 12 / fail 1 / not_run 0)
  [FAIL   ] artifact_hashes: 1개 artifact 문제: dist/app.txt: 해시 불일치 (변조 의심)
```

manifest 파일 자체를 지워도 통과되지 않는다 — `manifest_exists` 가 FAIL 로
차단한다 (릴리스 후보의 증적이 없으면 게이트를 지날 수 없다).

검증 후 산출물이 바뀌면 기존 승인은 자동으로 무효가 된다 — 이 게이트를 우회할
방법은 이 표준의 도구 안에 없다. 롤백 원칙(코드/데이터 롤백 분리, 직전 정상본
보존, 무한 재시도 금지)은 `docs/ROLLBACK_STANDARD.md`. `verify_release.py`도
`create_release_manifest.py`도 실제 배포·Git push·GitHub Release를 수행하지
않는다 — 통과 후 배포는 사람 또는 별도 절차가 수행한다.

## 비목표

- 유료 코드 서명 인증서, HSM, TPM 필수, 강한 DRM
- 안티디버깅, 패커, 과도한 난독화
- 백신 기능, 프로세스 감시, 하드웨어 지문 수집, 상용 보안 솔루션
- 특정 언어·프레임워크·클라우드 벤더 종속
- 실제 배포 실행, Git push, GitHub Release 생성, 운영 데이터 수정 (이 표준의
  어떤 스크립트도 수행하지 않는다)
- 자연어 문서 내용의 완전 자동 판정 (기계적으로 검증 가능한 핵심 불일치만 검사)

## 기여

`CONTRIBUTING.md` 참고. 요약: 이슈/제안 → 브랜치 → 변경 → 테스트/시크릿/금지
패턴/검증 실행 → PR.

## 라이선스

MIT License — `LICENSE` 참고.
