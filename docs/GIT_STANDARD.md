# GIT_STANDARD.md — Git 작업 표준 (Phase 7)

- 상태: ACTIVE (Phase 7)
- 관련 도구: `scripts/preflight.py`, `scripts/sign_ai_session.py`, `scripts/checkpoint.py`
- 근거: `FLASH_BUILD_PROMPT.md` §5 (Git과 AI 서명 표준)

## 1. 목적

모든 코드 프로젝트는 Git으로 관리한다. 작업을 시작하기 전에 실제 저장소 상태를
조사하지 않고 "아마 이럴 것이다"로 가정하지 않는다. 이 표준은 그 확인 절차를
`scripts/preflight.py` 하나의 명령으로 자동화한다.

## 2. 작업 시작 시 확인 항목과 실제 명령

| 확인 항목 | 수동 명령 | 자동화 |
|---|---|---|
| 현재 브랜치 | `git rev-parse --abbrev-ref HEAD` | `preflight.py` → `git_repo` |
| HEAD | `git rev-parse HEAD` | `preflight.py` → `git_repo` |
| 최근 커밋 | `git log --oneline -5` | (수동 확인 권장, preflight 범위 아님) |
| 작업트리 상태 | `git status --porcelain` | `preflight.py` → `worktree` |
| staged diff | `git diff --cached` | (수동 확인 권장) |
| unstaged diff | `git diff` | (수동 확인 권장) |
| 추적되지 않은 파일 | `git status --porcelain` (`??` 항목) | `preflight.py` → `untracked` |
| protected branch 여부 | `.ai-standard.yml` 의 `protected_branches` 와 현재 브랜치 비교 | `preflight.py` → `protected_branch` |

한 번에 실행:

```bash
python scripts/preflight.py            # 사람이 읽는 출력
python scripts/preflight.py --json     # 기계 판독용 출력
```

`preflight.py` 는 Git 저장소가 아닌 디렉터리, protected branch, 미커밋 변경,
필수 문서 누락, 잘못된 설정 파일도 함께 검사한다 (전체 12종 검사는
`docs/FILE_RESPONSIBILITIES.md`와 `scripts/preflight.py --help` 참고).

## 3. protected branch 에서 직접 작업 금지

`.ai-standard.yml` 의 `protected_branches` (기본값: `main`, `master`, `develop`)에
있는 브랜치에서 직접 작업하면 `preflight.py` 가 `protected_branch` 검사를 FAIL로
보고한다. FAIL을 무시하고 계속 진행하지 않는다 — feature 브랜치를 만들고
그 브랜치에서 작업한다.

```bash
git checkout -b feature/<작업-슬러그>
```

## 4. 여러 AI/세션이 병렬 작업할 때

- 별도 브랜치 또는 별도 Git worktree를 사용한다. 같은 브랜치에서 동시에 파일을
  수정하지 않는다.
- 각 세션은 자신의 `allowed_scope`(수정 가능 파일)를 시작 서명에 명시하고,
  다른 세션의 범위(`forbidden_scope`)를 침범하지 않는다.
- worktree를 쓰면 `preflight.py --workspace <worktree-경로>` 로 각 worktree를
  독립적으로 검사할 수 있다.

## 5. 서명과 커밋의 연계

- AI 시작 서명(`sign_ai_session.py start`)은 `base_commit`(작업 시작 시점 HEAD)과
  `git_status_hash`(작업 시작 시점 작업트리 상태)를 기록한다.
- AI 종료 서명(`sign_ai_session.py end`)은 `end_commit`, `diff_hash`,
  `changed_files`/`created_files`/`deleted_files`를 기록한다.
- 체크포인트(`checkpoint.py`)는 이 표준이 요구하는 "직전 정상 상태로 되돌릴 수 있는
  지점"의 근거 중 하나가 된다. **체크포인트는 자동 커밋을 만들지 않는다** — 커밋
  여부와 시점은 사람 또는 별도 절차가 결정한다.
- 커밋 자체를 자동으로 만들거나 서명하지 않는다. 서명은 `.ai/ledger.jsonl`에
  별도로 append-only 기록되며, 실제 Git 커밋 이력과는 독립적이다. 커밋 메시지에
  `run_id`를 남기면 둘을 사람이 대조하기 쉬워진다(선택 사항, 자동화하지 않음).
- 서명되지 않은 변경은 이 표준상 정식 결과로 승인하지 않는다 — 작업 시작·종료마다
  `sign_ai_session.py`를 실행한다 (`docs/AI_WORKFLOW.md`, 실제 명령은
  `SKILL.md` §8 참고).

## 6. 자동 push 금지

- 이 표준의 어떤 스크립트도 `git push`, GitHub Release 생성, 외부 배포를
  수행하지 않는다 (`create_release_manifest.py`/`verify_release.py`도 마찬가지 —
  `docs/RELEASE_STANDARD.md` §1).
- push는 사람이 명시적으로 실행하는 별도 단계다. AI가 스스로 판단해 push하지
  않는다.
- force push, 히스토리 재작성(`git rebase -i`, `git filter-branch` 등)은 사람의
  명시적 지시 없이 수행하지 않는다.

## 7. 커밋하지 않는 경우

체크포인트만으로 작업 중간 상태를 보존할 수 있다. 커밋 여부가 불확실하면
커밋하지 않고 체크포인트와 인계 번들(`create_handoff.py`)로 상태를 남긴 뒤
사람의 판단을 기다린다. 기록되지 않은 작업은 존재하지 않은 것으로 본다 —
커밋하지 않더라도 서명·체크포인트·인계는 남긴다.
