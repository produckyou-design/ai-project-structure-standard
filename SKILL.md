---
name: ai-project-structure-standard
description: AI가 장기간 소프트웨어 프로젝트를 개발할 때 계층형 Coordinator 구조, Git과 AI 작업 서명, 오류/trace 추적, 구조적 보안, 검증 게이트, 안전한 배포와 롤백을 일관되게 적용하기 위한 범용 개발 표준. 새 프로젝트를 시작하거나 기존 프로젝트에 구조를 도입할 때, AI 작업을 서명·검증·인계 가능한 형태로 남기고 싶을 때 사용한다.
---

# Airframe (ai-project-structure-standard)

이 스킬은 AI가 코드를 "어떻게 짜는가"가 아니라 "어떤 구조로, 어떤 기록을 남기며,
무엇을 검증한 뒤에만 배포하는가"를 표준화한다. 아래 15개 항목은 각각 실제
스크립트 명령과 연결된다 — 추상적 권고가 아니라 실행 가능한 절차다.

이름의 유래와 항공 용어 대응표는 [`README.md`](README.md)의 "왜 Airframe인가"
절 참고.

## 1. 언제 사용하는가

- 새 소프트웨어 프로젝트를 시작할 때 (계층 구조를 처음부터 잡는다).
- 기존 프로젝트에 구조를 점진적으로 도입할 때 (전면 재작성 없이).
- 여러 AI 세션·여러 AI가 같은 저장소를 오래 다룰 때 (서명·인계가 없으면
  이전 작업을 신뢰할 근거가 없다).
- 배포 전 검증 게이트와 롤백 경로가 필요한 프로젝트.

특정 언어·프레임워크에 종속되지 않는다. `scripts/`의 도구는 Python으로
구현되어 있지만 어떤 언어의 프로젝트에도 적용한다(설정 파일의
`test_command`/`verify_commands`로 실제 실행 명령을 지정한다).

## 2. 신규 프로젝트 적용

```bash
cp .ai-standard.example.yml <프로젝트>/.ai-standard.yml   # 값 채우기
cp templates/AI_START_HERE.md templates/ARCHITECTURE.md \
   templates/CURRENT.md templates/STATUS.md <프로젝트>/
python scripts/preflight.py --workspace <프로젝트>
```

도메인이 정해지면 `docs/ARCHITECTURE_STANDARD.md`를 따라 Entry → Domain
Coordinator → Service → Adapter 계층으로 시작한다. `examples/python-desktop/`
또는 `examples/web-service/`를 뼈대로 복사해도 된다.

## 3. 기존 프로젝트 적용

**한 번에 전면 재작성하지 않는다.** `docs/MIGRATION_GUIDE.md`의 8단계를 따른다.

```text
1. 현재 호출 경로 조사        5. 위험 경계부터 중앙화
2. 상태 소유자 조사           6. 기능별 점진적 이전
3. 직접 호출·우회 경로 목록화  7. 회귀 테스트
4. 기존 Coordinator/Gateway 재사용 판단  8. 레거시 경로 제거
```

실행 가능한 나쁜 예/좋은 예: `examples/existing-project-migration/`
(`python before/app.py` vs `python after/main.py`).

## 4. 조사 우선 원칙

코드를 작성하기 전에 실제 저장소 상태를 조사한다 — 가정하지 않는다.

```bash
python scripts/preflight.py --json     # Git 상태, protected branch, 위험 경계
git status --porcelain                 # 추적되지 않은 파일
git diff / git diff --cached           # unstaged / staged 변경
```

존재하지 않는 파일·함수·명령·테스트 결과를 가정하지 않는다. 실행하지 않은
검사는 `NOT_RUN`이지 `PASS`가 아니다.

## 5. 계층형 Coordinator 판단 기준

```text
UI / API / 외부 요청 / 백그라운드 작업
          |
Application Entry Layer
          |
  Domain Coordinator          — 요청 정규화, 순서, 중복 병합, 상태,
          |                     캐시 정책, 타임아웃, 취소, 결과 조합, 오류 정규화
Domain Service / Use Case      — 도메인 규칙, 검증, 계산
          |
Adapter / Repository / Gateway — 파일·DB·외부 API·OS 접근, 저수준 오류 변환
```

도메인마다 독립 Coordinator를 둔다(`AuthCoordinator`, `NewsCoordinator` 등).
순수 계산 함수까지 Coordinator를 거치게 하지 않는다. 근거와 예시:
`docs/ARCHITECTURE_STANDARD.md`, `docs/DECISIONS/ADR-0001-layered-coordinator.md`.

## 6. 새 오케스트레이터 생성 금지 조건

거대한 단일 전역 오케스트레이터(GlobalOrchestrator)를 만들지 않는다. 최상위
Application Coordinator는 **여러 도메인에 걸친 실행 순서가 실제로 존재할 때만**
둔다 — 앱 부팅/종료, 로그인 이후 초기화, 업데이트 후 재시작, 전체 장애 복구
모드, 사용자/워크스페이스 전환. 다음은 직접 하지 않는다: DB 쿼리, 외부 API
파싱, 인증 세부 로직, 결제 처리, 파일 저장, 기능별 캐시 관리 — 이것들은
도메인 Coordinator 이하 계층의 책임이다. 새 Coordinator를 만들기 전에
`docs/FILE_RESPONSIBILITIES.md`에서 같은 책임의 기존 파일을 먼저 찾는다.

## 7. Git 작업 절차

```bash
python scripts/preflight.py                       # 브랜치/HEAD/status 확인
git checkout -b feature/<작업>                     # protected branch FAIL 시
python scripts/checkpoint.py --name <이름>          # 단위 작업마다 (자동 commit 없음)
```

여러 AI가 병렬 작업하면 별도 브랜치 또는 worktree를 쓴다. 자동 `git push`,
GitHub Release, 외부 배포는 하지 않는다 — 사람이 명시적으로 실행하는 별도
단계다. 상세: `docs/GIT_STANDARD.md`.

## 8. AI 시작·종료 서명

```bash
python scripts/sign_ai_session.py start --task "이번 작업" \
  --allowed-scope "수정할 파일" --forbidden-scope "건드리지 않을 파일"
# ...작업...
python scripts/sign_ai_session.py end --status success \
  --tests-run "pytest" --tests-passed "N" --tests-failed "0"
```

`.ai/ledger.jsonl`에 append-only로 기록되고 `previous_entry_hash`/`entry_hash`로
해시 체인을 이룬다. 실제 모델 ID를 확인할 수 없으면(`AI_ACTUAL_MODEL_ID` 등
환경변수 미설정) `actual_model_id`는 항상 `UNKNOWN`이다 — AI의 자기 신고를
검증된 값으로 단정하지 않는다. 서명 없는 변경은 정식 결과로 승인하지 않는다.

## 9. 체크포인트와 인계

```bash
python scripts/checkpoint.py --name <이름>   # Git 상태·patch·신규 파일·문서 스냅샷
python scripts/create_handoff.py             # 단일 Markdown 인계 번들
```

체크포인트는 자동 commit을 만들지 않는다. 인계 번들은 이전 대화 없이 다음
세션이 이해할 수 있도록 현재 상태·변경·테스트·블로커·다음 작업·롤백 지점을
담는다. 민감정보 원문은 출력하지 않는다(마스킹).

## 10. 오류와 trace

```text
오류 코드 = 실패의 종류 (예: APP-STORAGE-WRITE-500)   → ERROR_CATALOG.md 에 등록
trace_id  = 실제 발생한 개별 사건                        → 요청에서 오류까지 유지
```

모든 함수에 오류 코드를 붙이지 않는다. 인증·권한·네트워크·외부 공급자·저장·
파싱·업데이트·설정·계약 버전·배포·복구 경계에서만 발급한다. 오류 계약은
`schemas/error.schema.json`, 규칙은 `docs/ERROR_STANDARD.md`, 카탈로그 양식은
`templates/ERROR_CATALOG.md`.

## 11. 구조적 보안

```bash
python scripts/check_secrets.py             # 시크릿 원문 비노출 탐지 (마스킹 출력)
python scripts/check_forbidden_patterns.py  # 구조적 금지 패턴 탐지 (설정 예외 지원)
```

비용이 들거나 과도한 방어(유료 인증서, HSM, TPM, DRM, 안티디버깅 등)는 요구하지
않는다. 코딩 단계에서 구조적으로 적용 가능한 규칙만 자동 검사로 강제한다 —
전체 목록과 심각도는 `docs/SECURITY_STANDARD.md` §2. 예외가 필요하면
`.ai-standard.yml`의 `allow_exceptions`에 파일·패턴·이유·만료조건을 남긴다
(형식: `docs/SECURITY_STANDARD.md` §4.1).

## 12. 검증 게이트

```bash
python scripts/verify_project.py        # 검증 명령·테스트·시크릿·금지패턴·git diff --check 실행
python scripts/check_document_sync.py   # README 참조·필수문서·CURRENT/STATUS 정합성
```

결과는 `schemas/verification.schema.json`을 따르는 `.ai/verification.json`에
저장된다. **어떤 명령도 실행하지 않았는데 PASS로 기록하지 않는다** — 미실행은
`NOT_RUN`이다.

## 13. 배포 금지 조건

다음 중 하나라도 해당하면 배포하지 않는다(`docs/RELEASE_STANDARD.md` §2).

```text
승인된 커밋 없음 · AI 시작/종료 서명 없음 · 작업트리 미정리 ·
필수 테스트 미통과 · 시크릿 검사 미통과 · 빌드 실패 ·
실제 실행 미확인 · 롤백 경로 미확인 · changelog 없음 ·
배포 산출물 해시 불일치 · 최종 승인 없음
```

검증 후 산출물이 바뀌면 기존 승인은 무효다. `python scripts/verify_release.py`가
이를 13종 검사(artifact hash 재계산 포함)로 자동 차단한다 — exit code 1이면
배포하지 않는다. 이 표준의 어떤 도구도 실제 배포, Git push, GitHub Release
생성을 수행하지 않는다.

## 14. 롤백

```bash
python scripts/create_release_manifest.py --version <버전> --artifacts <파일...> \
  --rollback-point <직전 정상 커밋/배포 식별자> --approved-by <이름>
python scripts/verify_release.py    # rollback_point 없으면 require_rollback=true 시 FAIL
```

코드 롤백과 데이터 롤백을 분리한다. 직전 정상 실행파일·설치파일·manifest·
설정·커밋과 마이그레이션 전 데이터 백업을 최소한 보존한다. 업데이트 실패 시
기존 정상 버전을 유지하고, 실패 버전을 무한 재시도하지 않는다. 상세:
`docs/ROLLBACK_STANDARD.md`, 절차 양식: `templates/RUNBOOK.md`.

## 15. 완료 보고 형식

완료를 주장하기 전에 다음을 모두 갖춘다 — 갖추지 못한 항목은 완료가 아니라
`NOT_RUN`/`FAIL`로 보고한다.

```text
- 변경 파일 (실제 git diff 기준)
- 실행한 명령과 그 실제 출력(exit code 포함)
- 테스트 결과 (PASS/FAIL/NOT_RUN, 개수)
- 실패 또는 미실행 항목 (숨기지 않는다)
- 남은 한계
- 다음 세션이 읽을 인계 기록 (create_handoff.py 산출물 경로)
```

완료 보고보다 실제 Git diff와 실행 결과를 우선한다. 근거 없는 PASS를
기록하지 않는다.
