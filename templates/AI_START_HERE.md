# AI_START_HERE — 작업 시작 가이드

> 이 프로젝트는 AI Project Structure Standard 를 따른다.
> 새 세션(또는 새 개발자)은 이 문서를 먼저 읽고 작업을 시작한다.
> 프로젝트별 세부 사항은 `docs/` 와 `.ai/` 아래 문서를 따른다.

## 1. 시작 전 읽을 문서 (이 순서)

```text
1. README.md                 — 프로젝트 개요와 빠른 시작
2. .ai/CURRENT.md            — 현재 진행 중인 작업과 허용 범위
3. .ai/STATUS.md             — 요구사항 대조 상태 (PASS/FAIL/NOT_RUN)
4. .ai/handoffs/ 최신 파일   — 이전 세션의 인계 번들
5. docs/ARCHITECTURE.md      — 계층 구조와 책임 경계
6. .ai/ledger.jsonl          — AI 작업 서명 기록 (append-only)
```

읽기 전에 `git status` 와 `git diff` 로 실제 작업트리 상태를 확인한다.
문서 내용과 작업트리가 다르면 문서를 우선하지 않고 실제 상태를 기준으로 조사한다.

## 2. 작업 시작 절차

```text
1. preflight 실행
   python scripts/preflight.py            # 위험 경계 확인 (기본: 현재 디렉터리)
   python scripts/preflight.py --json     # 기계 판독용 출력

2. preflight 결과 확인
   - FAIL 이 있으면 원인을 해결하거나, 왜 작업을 계속하는지 기록한다
   - protected branch 에서 직접 작업하지 않는다 (feature branch 사용)
   - 작업트리에 미커밋 변경이 있으면 먼저 정리하거나 의도를 기록한다

3. AI 시작 서명 생성
   python scripts/sign_ai_session.py start --task "수행할 작업 설명" \
     --allowed-scope "허용 범위" --forbidden-scope "건드리지 않을 범위"

4. 작업 허용 범위를 CURRENT 문서에 기록한다
   - 이번에 수정할 파일 목록을 먼저 선언한다
   - 선언하지 않은 파일을 수정해야 하면 이유를 CURRENT 문서에 기록한다
```

## 3. 작업 중 규칙

- 기록되지 않은 작업은 존재하지 않은 것으로 본다. 모든 단계를 문서에 남긴다.
- 같은 상태와 외부 경계에는 하나의 소유자만 둔다. 중복 구현하지 않는다.
- 시크릿을 코드, 로그, Git, 테스트 결과, 빌드에 넣지 않는다.
- 수정 전에 같은 책임의 기존 파일이 있는지 먼저 찾는다.
- 단위 작업이 끝날 때마다 체크포인트를 남긴다:

```text
python scripts/checkpoint.py --name <체크포인트명>
```

## 4. 작업 종료 절차

```text
1. 관련 테스트 실행 후 결과를 기록한다
   python -m pytest tests/ -q

2. 기본 검증 실행
   - 문법 검사 / 정적 분석 / git diff --check / 시크릿 검사 / 금지 패턴 검사

3. AI 종료 서명 생성
   python scripts/sign_ai_session.py end --status success

4. 인계 번들 생성
   python scripts/create_handoff.py

5. .ai/CURRENT.md, .ai/STATUS.md 를 실제 결과로 갱신한다
   - 실행하지 않은 검사는 NOT_RUN 으로 남긴다
   - FAIL 을 숨기지 않는다
```

## 5. 금지 사항

- Git push, GitHub Release, 외부 배포, 운영 데이터 수정
- 서명 없이 완료로 처리하는 일
- 실행하지 않은 검사를 PASS 로 기록하는 일
- 검증 없이 릴리스 산출물을 확정하는 일
- 거대한 전역 오케스트레이터 신설 (계층형 Coordinator 를 사용)
- 시크릿 원문 출력 또는 저장소 저장

## 6. 프로젝트별 설정 확인

프로젝트 루트의 `.ai-standard.json` / `.ai-standard.yml` 에
위험 등급, protected branch, 필수 문서, 검증 명령 등이 정의되어 있다.
설정이 없으면 preflight 가 안전한 기본값으로 동작한다.
