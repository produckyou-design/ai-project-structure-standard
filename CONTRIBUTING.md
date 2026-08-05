# CONTRIBUTING — 기여 절차

이 저장소는 스스로도 자신이 정의한 표준(서명, 검증 게이트, 문서 정합성)을
따른다. 기여 시에도 같은 절차를 적용한다.

## 1. 이슈/제안

버그, 표준 개선, 새 예제 제안은 이슈로 먼저 남긴다. 무엇이 문제인지(현재
동작)와 무엇을 원하는지(기대 동작)를 구분해서 적는다. 표준 자체(문서/스키마)
변경 제안이면 관련 ADR이 있는지 `docs/DECISIONS/`에서 먼저 확인한다.

## 2. 브랜치

```bash
python scripts/preflight.py            # protected branch 에서 직접 작업하지 않는다
git checkout -b feature/<작업-슬러그>
```

상세: `docs/GIT_STANDARD.md`.

## 3. 변경

- 같은 책임의 기존 파일이 있는지 `docs/FILE_RESPONSIBILITIES.md`에서 먼저
  찾는다. 중복 생성하지 않는다.
- 계층형 Coordinator 원칙(`docs/ARCHITECTURE_STANDARD.md`)을 따른다 — 거대한
  전역 오케스트레이터를 추가하지 않는다.
- 문서를 고치면 관련 코드/스키마와 모순되지 않는지 확인한다. 코드를 고치면
  관련 문서를 함께 갱신한다(문서는 계획이 아니라 현재 상태를 기록한다).
- 새 오류 코드를 추가하면 사용 전에 프로젝트의 `ERROR_CATALOG.md`에 등록한다
  (`docs/ERROR_STANDARD.md`).

## 4. 테스트 추가 요구

- 동작을 바꾸는 변경은 그 동작을 검증하는 테스트를 함께 추가하거나 갱신한다.
- 테스트는 구현 내부를 그대로 복제하지 말고 외부에서 관찰 가능한 결과를
  검증한다.
- 시크릿·금지 패턴 테스트에는 실제 비밀값을 쓰지 않는다. synthetic token만
  쓴다.

## 5. 문서 동기화 요구

- README에 새 스크립트/문서/예제 경로를 추가했다면 실제로 그 경로가 존재해야
  한다 — `python scripts/check_document_sync.py`가 이를 검사한다.
- `.ai/CURRENT.md`, `.ai/STATUS.md`를 쓰는 프로젝트라면 두 문서가 서로
  모순되지 않아야 한다(예: STATUS에 FAIL이 있는데 CURRENT 블로커가 "없음").

## 6. PR 전 필수 실행

PR을 올리기 전에 아래를 실제로 실행하고, 결과(PASS/FAIL/NOT_RUN와 요약)를
PR 설명에 남긴다. 실행하지 않은 항목은 "실행하지 않음"이라고 적는다 —
실행한 것처럼 적지 않는다.

```bash
python -m pytest tests/
python scripts/check_secrets.py
python scripts/check_forbidden_patterns.py
python scripts/verify_project.py
```

## 7. PR

- 변경한 파일, 실행한 명령과 결과, 남은 한계를 PR 설명에 명시한다.
- 표준 문서(`docs/*_STANDARD.md`) 자체를 바꾸는 PR은 관련 ADR을 함께
  추가하거나 갱신한다(`templates/ADR_TEMPLATE.md`).

## 8. 커밋 메시지 관례

- 한 커밋은 한 가지 의도를 담는다(기능 추가/버그 수정/문서 갱신/리팩터링을
  섞지 않는다).
- 제목은 무엇을 바꿨는지가 아니라 "왜"가 드러나게 짧게 쓴다. 본문에 변경
  범위와 검증 방법을 남긴다.
- AI가 작업한 커밋이라면 가능하면 `run_id`(서명에서 발급된 값)를 본문에
  남긴다 — 자동화하지는 않지만, 사람이 `.ai/ledger.jsonl`과 대조하기 쉬워진다.
- 자동 `git push`, force push, 히스토리 재작성은 사람의 명시적 지시 없이
  하지 않는다.

## 9. 하지 않는 것

- Git push, GitHub Release 생성, 실제 배포, 운영 데이터 수정을 기여 절차의
  일부로 자동 수행하지 않는다.
- 시크릿 값을 이슈, PR, 커밋, 로그에 원문으로 남기지 않는다.
