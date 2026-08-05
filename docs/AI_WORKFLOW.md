# AI_WORKFLOW.md — AI 작업 흐름 표준

- 상태: ACTIVE (Phase 5)
- 관련 도구: `scripts/preflight.py`, `scripts/sign_ai_session.py`, `scripts/verify_project.py`,
  `scripts/check_document_sync.py`, `scripts/checkpoint.py`, `scripts/create_handoff.py`
- 빠른 시작 요약: `templates/AI_START_HERE.md` (프로젝트에 복사해서 쓰는 축약판)

---

## 0. 핵심 원칙

- **완료 보고보다 Git diff 를 우선한다.** "다 했습니다" 라는 서술은 증거가 아니다.
  실제로 무엇이 바뀌었는지는 `git status` / `git diff` 로 확인한다. 이 문서의 모든 단계는
  이 원칙 위에 있다: 각 단계는 관찰 가능한 산출물(로그, 서명, 커밋되지 않은 diff, 테스트
  결과)을 남기고, 다음 단계 또는 다음 세션은 그 산출물을 신뢰의 근거로 삼는다.
- **실행하지 않은 검사는 NOT_RUN 이다.** PASS 로 기록하려면 실제로 실행한 근거가 있어야
  한다 (`docs/DOCUMENTATION_STANDARD.md` §5).
- 이 흐름은 8단계다: 조사 → preflight → 시작 서명 → 구현 → 검증 → 체크포인트 → 종료 서명 → 인계 번들.
  단계를 건너뛰어야 하면(예: 아주 작은 수정) 왜 건너뛰었는지 CURRENT/WORK_LOG 에 남긴다.

## 1. 조사 (문서·Git 상태 읽기)

구현을 시작하기 전에 실제 상태부터 읽는다. 문서와 작업트리가 다르면 작업트리를 믿는다.

```bash
git status
git diff
git log --oneline -10
```

```text
읽는 순서 (templates/AI_START_HERE.md §1 과 동일):
1. README.md
2. .ai/CURRENT.md      — 현재 작업과 허용 범위
3. .ai/STATUS.md       — 요구사항 대조 상태
4. .ai/handoffs/ 최신 파일
5. docs/ARCHITECTURE.md (또는 프로젝트의 아키텍처 문서)
6. .ai/ledger.jsonl    — 서명 이력
```

## 2. Preflight (위험 경계 확인)

구현에 들어가기 전에 protected branch, 미커밋 변경, 시크릿 파일 추적 여부 등을 확인한다.

```bash
python scripts/preflight.py
python scripts/preflight.py --json   # 기계 판독용
```

- `status` 가 `FAIL` 이면 원인을 해결하거나, 왜 그대로 진행하는지 CURRENT 에 기록한다.
- protected branch(기본: `main`/`master`/`develop`)에서 직접 작업하지 않는다.

## 3. 시작 서명

작업을 시작한다는 서명을 append-only ledger 에 남긴다.

```bash
python scripts/sign_ai_session.py start \
  --task "Phase 5 완성: verify_project/check_document_sync 테스트와 문서" \
  --allowed-scope "tests/test_project_verification.py, tests/test_document_sync.py, docs/*.md, templates/RELEASE_CHECKLIST.md" \
  --expected-tests "tests/test_project_verification.py, tests/test_document_sync.py" \
  --documents-read ".ai/CURRENT.md, .ai/STATUS.md, docs/SECURITY_STANDARD.md"
```

- `run_id` 가 출력된다. 이후 `end` 단계에서 이 값으로 짝을 맞출 수 있다(생략하면 자동으로
  마지막 미종료 `start` 를 찾는다).
- 이 시점에 수정할 파일 목록을 `.ai/CURRENT.md` 의 "허용 범위"에 먼저 선언한다. 선언하지
  않은 파일을 나중에 고쳐야 하면 이유를 함께 남긴다.

## 4. 구현

- 같은 책임을 가진 기존 파일이 있는지 먼저 찾는다. 중복 구현하지 않는다.
- 시크릿을 코드·로그·Git·테스트 결과·빌드에 넣지 않는다.
- 단위 작업이 끝날 때마다 체크포인트를 남긴다(§6).

## 5. 검증 (verify_project.py)

구현 중간 또는 종료 직전에 프로젝트별 검증 명령을 실제로 실행한다.

```bash
python scripts/verify_project.py
python scripts/verify_project.py --json     # 기계 판독용
python scripts/check_document_sync.py       # 문서 정합성
```

- `verify_project.py` 는 설정(`.ai-standard.*`)의 `verify_commands`/`test_command`,
  시크릿 검사(`check_secrets.py`), 금지 패턴 검사(`check_forbidden_patterns.py`),
  `git diff --check` 를 실행하고 결과를 `.ai/verification.json` 에 저장한다
  (`schemas/verification.schema.json` 참고).
- 설정에 명령이 없어서 실행하지 못한 검사는 `NOT_RUN` 으로 기록된다. `PASS` 로 조작하지 않는다.
- `.ai/verification_logs/<run_id>/` 아래에 검사별 원본 로그가 남는다. 이 디렉터리는
  검사 도구의 스캔 대상에서 구조적으로 제외된다(`scripts/common.py::collect_files`) —
  검사기 자신의 출력을 다시 스캔해서 자기참조 오탐을 만들지 않기 위해서다.
- `verify_project.py` 의 exit code 는 `status == FAIL` 일 때만 1이다. 실행 결과를 보고
  넘어갈지, 고치고 다시 돌릴지 판단한다.

## 6. 체크포인트

작업 중간 지점을 저장한다(자동 커밋은 만들지 않는다).

```bash
python scripts/checkpoint.py --name <체크포인트명>
```

- `.ai/checkpoints/<name>/` 아래에 `git status`, `git diff`, 추적되지 않은 신규 파일 사본,
  `.ai/CURRENT.md`/`.ai/STATUS.md` 사본, `docs/**/*.md` 사본을 남긴다.
- 문제가 생겼을 때 이 시점으로 되짚어볼 수 있는 관찰 가능한 스냅샷이다.

## 7. 종료 서명

작업을 마치면 관련 테스트와 기본 검증을 실행한 뒤 종료 서명을 남긴다.

```bash
python -m pytest tests/ -q
python scripts/verify_project.py
python scripts/check_document_sync.py

python scripts/sign_ai_session.py end \
  --status success \
  --tests-run "python -m pytest tests/ -q" \
  --tests-passed "138" \
  --tests-failed "0" \
  --documents-updated ".ai/CURRENT.md, .ai/STATUS.md, .ai/WORK_LOG.md" \
  --remaining-work "없음" \
  --rollback-point "<직전 정상 커밋 해시>"
```

- `--status` 는 `success`/`fail`/`aborted` 중 하나다. 실패했는데 `success` 로 적지 않는다.
- 종료 서명은 실제 `git diff`/`git status` 를 읽어 `changed_files`/`created_files`/
  `deleted_files` 를 자동으로 기록한다 (서술이 아니라 관찰).

## 8. 인계 번들

다음 세션(다른 AI 일 수도 있다)이 이전 대화 없이 이어받을 수 있도록 단일 Markdown 을 생성한다.

```bash
python scripts/create_handoff.py
```

- `.ai/handoffs/handoff_<timestamp>.md` 를 생성한다. 현재 상태, 변경 사항, 테스트 결과,
  블로커, 다음 작업, 롤백 지점을 담는다 (`templates/SESSION_HANDOFF.md` 양식).
- 마지막으로 `.ai/CURRENT.md`, `.ai/STATUS.md`, `.ai/WORK_LOG.md` 를 실제 결과로 갱신한다.
  실행하지 않은 검사는 NOT_RUN 으로 남기고, FAIL 을 숨기지 않는다.

## 9. 금지 사항

- Git push, GitHub Release, 외부 배포, 운영 데이터 수정 (별도 승인 없이는 하지 않는다).
- 서명 없이 완료로 처리하는 일.
- 실행하지 않은 검사를 PASS 로 기록하는 일.
- 검증 없이 릴리스 산출물을 확정하는 일 (`templates/RELEASE_CHECKLIST.md` 참고).
- 시크릿 원문 출력 또는 저장소 저장.

## 10. 단계 요약

| 단계 | 명령 | 산출물 |
|---|---|---|
| 조사 | `git status`, `git diff` | 실제 상태 확인 (문서보다 우선) |
| preflight | `python scripts/preflight.py` | 위험 경계 보고서 |
| 시작 서명 | `python scripts/sign_ai_session.py start --task "..."` | `.ai/ledger.jsonl` 항목 |
| 구현 | (코드 편집) | diff |
| 검증 | `python scripts/verify_project.py`, `python scripts/check_document_sync.py` | `.ai/verification.json`, `.ai/verification_logs/` |
| 체크포인트 | `python scripts/checkpoint.py --name <name>` | `.ai/checkpoints/<name>/` |
| 종료 서명 | `python scripts/sign_ai_session.py end --status success` | `.ai/ledger.jsonl` 항목 |
| 인계 번들 | `python scripts/create_handoff.py` | `.ai/handoffs/handoff_<ts>.md` |
