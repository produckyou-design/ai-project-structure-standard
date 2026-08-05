# RELEASE_STANDARD.md — 릴리스 표준 (Phase 6)

- 상태: ACTIVE (Phase 6)
- 관련 도구: `scripts/create_release_manifest.py`, `scripts/verify_release.py`
- 관련 스키마: `schemas/release_manifest.schema.json`, `schemas/verification.schema.json`
- 관련 문서: `docs/ROLLBACK_STANDARD.md`, `templates/DEPLOY_LOG.md`, `templates/RUNBOOK.md`
- 근거: `FLASH_BUILD_PROMPT.md` §7 (검증과 배포 표준)

## 1. 목적

**검증된 산출물만 릴리스 후보로 인정하고, 검증 후 변조되었거나 롤백 경로가 없으면
배포를 차단한다.** 이 표준은 실제 배포 실행 도구가 아니라 배포 전 게이트다.
Git push, GitHub Release 생성, 실제 배포 실행은 이 표준의 범위 밖이며
`create_release_manifest.py`/`verify_release.py` 어느 쪽도 수행하지 않는다.

## 2. 배포 전 필수 조건 (마스터 프롬프트 §7)

배포를 진행하려면 아래 조건이 모두 충족되어야 한다.

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

두 가지 핵심 원칙:

- **검증 후 산출물이 변경되면 기존 승인은 무효다.** 승인은 특정 해시를 가진 특정
  산출물에 대한 것이지, "버전 1.0.0" 같은 이름에 대한 것이 아니다. artifact 파일
  하나라도 재검증 없이 바뀌면 그 릴리스 후보는 더 이상 승인된 상태가 아니다.
- **검증한 산출물과 배포 산출물의 해시가 같아야 한다.** verify_project 가 검사한
  작업트리 상태(commit)에서 만든 artifact 와, 실제로 배포하려는 artifact 는
  동일한 파일이어야 한다. `verify_release.py` 는 이를 `artifact_hashes`,
  `total_hash`, `manifest_hash` 검사로 강제한다.

## 3. release manifest

`create_release_manifest.py` 가 만드는 `.ai/release_manifest.json` 은 릴리스
후보를 나타내는 기계 판독 가능한 단일 문서다. 필수 필드는
`schemas/release_manifest.schema.json` 이 강제한다.

| 필드 | 의미 |
|---|---|
| `release_id` | 릴리스 후보 식별자 (`rel_<타임스탬프>_<16진수6자>`) |
| `version` | 릴리스 버전 |
| `source_commit` | manifest 생성 시점의 git HEAD |
| `build_run_id` | 빌드 실행 식별자 (선택) |
| `artifacts[]` | `{path, sha256, size_bytes}` — 파일별 바이너리 해시와 크기 |
| `total_artifact_hash` | artifact 해시들을 정렬해 이어붙인 문자열의 SHA-256 |
| `manifest_hash` | `manifest_hash` 필드를 제외한 본문의 정규 JSON SHA-256 |
| `created_at` | 생성 시각 |
| `verification_run_id` | 근거로 삼은 `verification.json` 의 실행 ID (미지정 시 빈 문자열) |
| `rollback_point` | 롤백 시 되돌아갈 지점 |
| `approved_by` | 인간 승인자 |

artifact 파일은 텍스트가 아니라 **바이너리로 해시**한다(`common.sha256_file` 은
텍스트 전용이라 빌드 산출물에는 쓰지 않는다).

## 4. verify_release 검사 13종과 원칙의 매핑

| # | 검사 | 확인 내용 | 매핑되는 §2/§7 원칙 |
|---|---|---|---|
| 1 | `worktree_clean` | `git status --porcelain` 이 비어 있는가 | 깨끗한 작업트리 |
| 2 | `manifest_exists` | release manifest 존재 + 스키마 필수 필드 | 릴리스 후보의 증적 존재 (없으면 검증 대상 자체가 없음) |
| 3 | `source_commit_match` | manifest.source_commit == 현재 HEAD | 승인된 커밋 |
| 4 | `verification_exists` | verification.json 존재 + 스키마 필수 필드 | 필수 테스트 통과의 증적 존재 |
| 5 | `verification_passed` | verification.status == PASS (FAIL/NOT_RUN 은 실패) | 실행하지 않은 검사는 PASS 가 아니다 |
| 6 | `verification_hash` | verification.json 의 result_hash 재계산 일치 | 검증 결과 변조 차단 |
| 7 | `verification_run_match` | manifest.verification_run_id == verification.verification_run_id | 검증한 산출물과 배포 산출물의 근거 일치 |
| 8 | `artifact_hashes` | 각 artifact 가 현재도 존재하고 해시가 일치 | **검증 후 변경되면 승인 무효** (핵심 게이트) |
| 9 | `total_hash` | 전체 artifact hash 재계산 일치 | manifest 내부 일관성 |
| 10 | `manifest_hash` | manifest 자체 해시 재계산 일치 | manifest 변조 차단 |
| 11 | `rollback_point` | `require_rollback=true` 인데 비어 있으면 FAIL | 롤백 경로 확인 |
| 12 | `human_approval` | `require_human_approval=true` 인데 approved_by 가 비어 있으면 FAIL | 최종 승인 |
| 13 | `release_enabled` | `release_enabled=false` 면 FAIL | 프로젝트가 릴리스를 허용하는지 |

하나라도 FAIL 이면 전체 결과는 FAIL 이고 `verify_release.py` 는 exit 1 로 종료한다.
NOT_RUN 은 PASS 로 간주하지 않는다 — 특히 `verification_passed` 는
`verification.status` 가 `FAIL` 이든 `NOT_RUN` 이든 모두 실패로 취급한다.

## 5. 실행 명령 예시

```bash
# 1) 릴리스 후보 manifest 생성
python scripts/create_release_manifest.py \
  --version 1.0.0 \
  --artifacts dist/app.exe dist/app.manifest \
  --verification .ai/verification.json \
  --rollback-point <직전 정상 커밋 또는 배포 식별자> \
  --approved-by "홍길동" \
  --build-run-id build-2026-08-05-01

# 2) 릴리스 게이트 검사
python scripts/verify_release.py --json
```

exit code 0 은 게이트 통과를, 1 은 차단을 의미한다. 통과 후에도 실제 배포는
별도 절차(사람 또는 별도 CI)가 수행하며, 이 표준의 도구는 배포를 실행하지 않는다.

## 6. 이 표준이 하지 않는 것

- Git push, GitHub Release 생성, 실제 배포 실행
- 운영 데이터 변경
- 릴리스 승인 자동화 (승인 필드는 사람이 채워 넣는 값이다)
