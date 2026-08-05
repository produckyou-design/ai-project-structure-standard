# DEPLOY_LOG.md

> 프로젝트에 복사해 쓰는 배포 기록 양식. 배포할 때마다 새 항목을 위에 추가한다(append 방식).
> 자동 검사는 `scripts/create_release_manifest.py`, `scripts/verify_release.py` 가 담당한다.
> 이 문서는 그 결과와 실제 배포 절차를 사람이 읽을 수 있게 남긴 기록이다.
> 상세 표준: `docs/RELEASE_STANDARD.md`, `docs/ROLLBACK_STANDARD.md`

- 프로젝트:
- 최종 업데이트:

---

## 배포 기록 항목 형식

새 배포마다 아래 블록을 복사해 채운다.

```text
### <release_id> — v<version> (<YYYY-MM-DD HH:MM UTC>)

- release_id:
- version:
- 배포 시각:
- 담당:
- source_commit:
- manifest_hash:
- verify_release 결과: PASS | FAIL  (요약: pass X / fail Y / not_run Z)
- verify_release 실행 명령과 exit code:
- 배포 방법: (예: 수동 실행파일 교체 / CI 파이프라인 / 컨테이너 이미지 배포)
- 배포 후 확인 결과: (실제 실행 확인, 헬스 체크 결과)
- 롤백 지점(rollback_point):
- 이슈/특이사항:
```

## 예시 항목

### rel_20260805T120000Z_a1b2c3 — v1.0.0 (2026-08-05 12:00 UTC)

- release_id: rel_20260805T120000Z_a1b2c3
- version: 1.0.0
- 배포 시각: 2026-08-05 12:05 UTC
- 담당: (이름)
- source_commit: (커밋 해시)
- manifest_hash: (64자 16진수)
- verify_release 결과: PASS (pass 12 / fail 0 / not_run 0)
- verify_release 실행 명령과 exit code: `python scripts/verify_release.py --json` → exit 0
- 배포 방법: (예: 수동 실행파일 교체)
- 배포 후 확인 결과: (예: 헬스 체크 200 OK, 버전 표시 v1.0.0 확인)
- 롤백 지점(rollback_point): (직전 정상 커밋 또는 배포 식별자)
- 이슈/특이사항: (없음 / 발생한 문제와 조치)

## 작성 규칙

- verify_release 가 FAIL 을 반환했는데 배포를 강행한 경우, 그 사실과 사유를
  반드시 남긴다(우회했다는 사실을 숨기지 않는다).
- manifest_hash 와 verify_release 실행 결과는 실제 실행 없이 채우지 않는다.
- 배포 후 확인 결과는 "될 것이다"가 아니라 실제로 확인한 내용을 적는다.
- 롤백이 실제로 발생했다면 그 사실도 새 항목으로 기록한다(코드 롤백/데이터
  롤백 구분, 되돌린 지점, 사유).
