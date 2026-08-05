# RELEASE_CHECKLIST.md — 배포 전 체크리스트

> 프로젝트에 복사해 쓰는 배포 전 체크리스트 양식. 배포마다 새로 채운다(1회 배포 = 1개 사본).
> 자동 검사는 `scripts/verify_release.py` 가 §2 의 조건 대부분을 기계적으로 확인한다.
> 이 문서는 그 결과와, 자동 검사가 확인하지 못하는 항목(실제 실행 확인, 최종 승인 등)을
> 사람이 채워 넣은 기록이다.
> 상세 표준: `docs/RELEASE_STANDARD.md`, `docs/ROLLBACK_STANDARD.md`
> 배포 후 기록: `templates/DEPLOY_LOG.md` (이 체크리스트가 전부 PASS 여야 그 항목을 적는다)

- 프로젝트:
- 릴리스 버전:
- release_id: (`create_release_manifest.py` 출력)
- 작성자/담당:
- 작성 시각:

---

## 1. 체크리스트 사용 규칙

- 모든 항목은 **실제로 실행한 결과**로만 체크한다. "될 것 같다"는 근거가 아니다.
- 실행하지 않은 항목은 체크하지 않는다. 상태를 `PASS`/`FAIL`/`NOT_RUN` 중 하나로 남긴다
  (`docs/DOCUMENTATION_STANDARD.md` §5, NOT_RUN 원칙).
- 하나라도 `FAIL` 이면 배포하지 않는다. `FAIL` 인 채로 배포를 강행했다면 그 사실과 사유를
  `templates/DEPLOY_LOG.md` 에 숨기지 않고 남긴다.
- `verify_release.py` 가 기계적으로 확인하는 항목은 그 실행 결과를 그대로 증거로 쓴다.
  사람이 별도로 재확인할 필요는 없다 (단, 실행 자체는 반드시 한다).

## 2. 체크리스트

| # | 항목 | 확인 방법 / 명령 | 상태 (PASS/FAIL/NOT_RUN) | 증적 |
|---|---|---|---|---|
| 1 | 승인된 커밋 | `verify_release.py` 의 `source_commit_match` (manifest.source_commit == 현재 HEAD) | | 커밋 해시: |
| 2 | AI 시작·종료 서명 | `.ai/ledger.jsonl` 에 이번 작업의 `start`/`end` 쌍이 있는지 확인 (`python scripts/sign_ai_session.py end --status success` 실행 여부) | | run_id: |
| 3 | 깨끗한 작업트리 | `git status --porcelain` (비어 있어야 함) — `verify_release.py` 의 `worktree_clean` | | |
| 4 | 필수 테스트 통과 | `python -m pytest tests/ -q` (프로젝트의 `test_command`) | | 결과 요약(예: N passed): |
| 5 | 시크릿 검사 통과 | `python scripts/check_secrets.py` (exit 0, HIGH 탐지 없음) | | |
| 6 | 빌드 성공 | 프로젝트별 빌드 명령 (예: `python -m build`, `npm run build`) — 없으면 이 항목은 NOT_APPLICABLE 로 명시 | | 빌드 로그 위치: |
| 7 | 실제 실행 확인 | 빌드 산출물을 실제로 실행해 정상 기동 확인 (예: 헬스 체크, 스모크 테스트) — 사람이 직접 확인, 자동 검사 없음 | | 확인 방법과 결과: |
| 8 | 롤백 경로 확인 | `verify_release.py` 의 `rollback_point` 검사 + `docs/ROLLBACK_STANDARD.md` §2 최소 보존 대상 실재 확인 | | rollback_point: |
| 9 | changelog | `templates/DEPLOY_LOG.md` 에 이번 배포 항목이 작성됐는지 확인 | | |
| 10 | 배포 산출물 해시 | `python scripts/create_release_manifest.py ...` 로 `artifact_hashes` 기록 + `verify_release.py` 의 `artifact_hashes`/`total_hash`/`manifest_hash` 검사 | | manifest_hash: |
| 11 | 최종 승인 | `verify_release.py` 의 `human_approval` (require_human_approval=true 인 경우 `approved_by` 값 확인) | | approved_by: |

## 3. 실행 순서 (권장)

```bash
# 1) 테스트·시크릿·구조 검증
python -m pytest tests/ -q
python scripts/check_secrets.py
python scripts/verify_project.py

# 2) 릴리스 후보 manifest 생성 (승인된 커밋·산출물 해시 고정)
python scripts/create_release_manifest.py \
  --version <버전> \
  --artifacts <빌드 산출물 경로...> \
  --verification .ai/verification.json \
  --rollback-point <직전 정상 커밋 또는 배포 식별자> \
  --approved-by "<승인자>" \
  --build-run-id <빌드 식별자>

# 3) 릴리스 게이트 검사 (표 §2 의 대부분 항목을 이 한 번으로 확인)
python scripts/verify_release.py --json
```

`verify_release.py` 가 exit 0 을 반환해야 표의 1·3·8·10·11번 항목을 `PASS` 로 채울 수 있다.
exit 1 이면 어떤 검사가 실패했는지 출력에서 확인하고, 원인을 해소한 뒤 다시 실행한다
(manifest 를 다시 만들지, 코드를 고칠지는 실패한 검사에 따라 다르다 — `docs/RELEASE_STANDARD.md` §4 표 참고).

## 4. 체크리스트 결과 요약

- 전체 상태: PASS | FAIL | (진행 중)
- FAIL 또는 NOT_RUN 인 항목과 사유:
- 배포 진행 여부: 진행함 | 보류함 | (FAIL 인데 강행) — 강행한 경우 승인자와 사유:

## 5. 배포 후

- 이 체크리스트가 전부 `PASS` 로 끝났다면 `templates/DEPLOY_LOG.md` 에 배포 기록 항목을 추가한다.
- 실제 배포 실행(Git push, 배포 파이프라인 트리거, 아티팩트 업로드 등)은 이 표준의
  도구가 수행하지 않는다 — 사람 또는 별도 CI 가 수행하고, 그 결과를 `templates/DEPLOY_LOG.md` 에 남긴다.
