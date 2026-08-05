# AGENTS.md (example) — 프로젝트 루트에 복사해 쓰는 에이전트 규칙

> 이 파일을 프로젝트 루트에 `AGENTS.md`로 복사하고, 프로젝트에 맞게 값을 채운다.
> 표준 근거: `SKILL.md`, `docs/ARCHITECTURE_STANDARD.md`, `docs/SECURITY_STANDARD.md`.

## 1. 조사 우선

작업을 시작하기 전에 실제 저장소 상태를 조사한다. 존재하지 않는 파일·함수·
명령·테스트 결과를 가정하지 않는다.

```bash
python scripts/preflight.py --json
git status --porcelain
git diff
```

기존 파일이 있으면 역할과 내용을 조사한 뒤 재사용한다. 같은 책임의 파일이나
클래스를 중복 생성하지 않는다 — 새 파일을 만들기 전에
`docs/FILE_RESPONSIBILITIES.md`(또는 프로젝트의 동등 문서)에서 먼저 찾는다.

## 2. 서명 필수

작업 시작과 종료마다 서명을 남긴다. 서명 없는 변경은 정식 결과로 승인하지
않는다.

```bash
python scripts/sign_ai_session.py start --task "이번 작업" \
  --allowed-scope "수정할 파일" --forbidden-scope "건드리지 않을 파일"
python scripts/sign_ai_session.py end --status success \
  --tests-run "..." --tests-passed "N" --tests-failed "0"
```

## 3. 범위 선언

이번 작업에서 수정 가능한 파일 목록을 먼저 선언한다(`--allowed-scope` 또는
프로젝트의 CURRENT 문서). 선언하지 않은 파일을 수정해야 하면 수정 전에 이유를
CURRENT 문서에 기록한다. 다른 세션/다른 AI가 병행 작업 중인 파일은 건드리지
않는다.

## 4. 인계

작업을 마칠 때(또는 컨텍스트가 끊길 것 같을 때) 인계 번들을 남긴다. 인계
번들은 이전 대화 없이 다음 세션이 이해할 수 있어야 한다.

```bash
python scripts/checkpoint.py --name <이름>
python scripts/create_handoff.py
```

## 5. 검증 게이트

다음을 통과하지 못한 변경은 완료로 보고하지 않는다.

```bash
python -m pytest <프로젝트 테스트 명령>
python scripts/check_secrets.py
python scripts/check_forbidden_patterns.py
python scripts/verify_project.py
```

실행하지 않은 검사는 `NOT_RUN`으로 기록한다. 테스트 실패를 숨기거나 완료로
처리하지 않는다.

## 6. 금지 사항

- 자동 `git push`, GitHub Release 생성, 실제 배포 실행 — 사람이 명시적으로
  지시할 때만 수행한다.
- 시크릿(토큰·키·비밀번호·쿠키)을 코드, 로그, 커밋, 테스트 결과, 완료 보고에
  출력하거나 저장하지 않는다. 시크릿 검사 실패를 예외 처리로 우회하지 않는다.
- 요청받지 않은 전면 재작성. 기존 정상 동작을 보존하며 점진적으로 개선한다.
- 거대한 전역 오케스트레이터 신설. 도메인별 Coordinator + Service/Adapter
  계층을 따른다(`docs/ARCHITECTURE_STANDARD.md`).
- 실행하지 않은 검사를 PASS로 기록하는 일.
- 검증 없이 릴리스 산출물을 확정하거나 승인된 산출물을 재검증 없이 변경하는 일.
- 롤백 경로 없이 배포 가능한 상태로 확정하는 일.

## 7. 프로젝트별로 채울 값

```text
- protected_branches: (예: main, master)
- required_documents: (예: README.md, docs/ARCHITECTURE.md)
- test_command / verify_commands: (프로젝트 실제 명령)
- risk_level: (low | medium | high)
- release_enabled / require_human_approval / require_rollback
```

`.ai-standard.example.yml`을 `.ai-standard.yml`로 복사해 위 값을 채운다.
