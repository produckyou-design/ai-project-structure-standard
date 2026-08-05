# DOCUMENTATION_STANDARD.md — 문서 정합성 표준

- 상태: ACTIVE (Phase 5)
- 관련 도구: `scripts/check_document_sync.py`
- 관련 스키마: 없음 (문서는 자유 서식, 정합성만 기계 검사)
- 관련 템플릿: `templates/CURRENT.md`, `templates/STATUS.md`, `templates/WORK_LOG.md`,
  `templates/SESSION_HANDOFF.md`, `templates/AI_START_HERE.md`

---

## 1. 원칙: 문서는 계획이 아니라 현재 상태를 기록한다

- 문서에는 "하기로 한 일"이 아니라 **실제로 확인된 상태**를 적는다.
  "구현 예정", "곧 테스트함" 같은 미래형 서술은 STATUS/CURRENT 에 남기지 않는다.
- 어떤 항목이 PASS 라고 적으려면, 그 판단의 근거(실행한 명령, 테스트 이름, 로그 위치)가
  같은 줄 또는 같은 문서 안에 있어야 한다. 근거 없는 PASS 는 기록하지 않는다.
- 실행하지 않은 검사는 PASS 가 아니라 **NOT_RUN** 이다 (§5).
- 문서와 실제 작업트리(Git 상태, 실제 파일)가 다르면 문서를 신뢰하지 않고
  `git status` / `git diff` 로 확인한 실제 상태를 기준으로 삼는다
  (`templates/AI_START_HERE.md` §1).
- 실패(FAIL)를 숨기지 않는다. 알려진 실패는 "알려진 실패" 섹션에 그대로 남긴다.

## 2. 문서 갱신 시점

문서는 다음 시점에 갱신한다. 그 외 시점에 임의로 고쳐 쓰지 않는다.

- **Phase 종료 시** — 해당 Phase 의 통과 조건을 STATUS 에 반영한다.
- **AI 세션 종료 시** — `sign_ai_session.py end` 실행 전후로 CURRENT/STATUS/WORK_LOG 를 갱신하고,
  이어서 `create_handoff.py` 로 인계 번들을 생성한다.
- **검증 실행(`verify_project.py`) 직후, 결과가 이전 기록과 달라졌을 때** — 새로 FAIL 이
  생겼거나 기존 FAIL 이 해소됐을 때는 즉시 STATUS 에 반영한다. 결과가 그대로면
  다시 쓰지 않아도 된다(불필요한 diff 를 만들지 않는다).

## 3. 문서별 역할 분리

같은 정보를 여러 문서에 중복해서 옮겨 적지 않는다. 문서마다 소유하는 질문이 다르다.

| 문서 | 답하는 질문 | 갱신 시점 | 갱신 주체 | 하지 않는 것 |
|---|---|---|---|---|
| `.ai/CURRENT.md` | 지금 무엇을 하고 있고, 무엇까지 손대도 되는가 | 작업 시작/종료, 허용 범위 변경 시 | 작업 중인 AI/개발자 | 과거 세션 이력을 전부 나열하지 않는다 (그건 WORK_LOG) |
| `.ai/STATUS.md` | 요구사항·Phase 별로 지금 PASS/FAIL/NOT_RUN 인가 | Phase 종료, 검증 실행 직후 | 작업 중인 AI/개발자 | 앞으로 할 일을 서술하지 않는다 (그건 CURRENT) |
| `.ai/WORK_LOG.md` | 세션별로 무엇을 했고 무엇을 검증했는가 (append-only 이력) | 세션 종료 시 | 작업 중인 AI/개발자 (추가만 함) | CURRENT/STATUS 의 최신 상태를 재복사하지 않는다. 세션 시점의 사실만 남긴다 |
| `.ai/handoffs/*.md` | 다음 세션이 이전 대화 없이 이어받을 최소 정보 | 세션 종료 시 `create_handoff.py` 실행 | `create_handoff.py` (자동 생성) | 사람이 직접 손으로 편집하지 않는다. 다시 생성해서 대체한다 |

- CURRENT 는 "지금", STATUS 는 "무엇이 통과했는가", WORK_LOG 는 "무엇을 했는가(이력)",
  handoff 는 "다음 세션이 읽을 요약"이라는 축으로 구분한다.
- 네 문서가 서로 모순되면 `check_document_sync.py` 의 `current_status` 검사가 이를 잡아낸다 (§4).

## 4. 기계 판정 가능한 정합성 검사

`check_document_sync.py` 는 자연어 문서의 내용 자체를 판정하지 않는다.
**기계적으로 참/거짓을 확인할 수 있는 것만** 검사한다. 아래 표는 그 6개 검사와
1:1 로 대응한다.

| 검사(check) | 검증 대상 | FAIL 조건 | NOT_RUN 조건 |
|---|---|---|---|
| `readme_references` | README.md 가 언급하는 `scripts/`·`schemas/`·`templates/`·`docs/`·`examples/`·`tests/` 하위 경로 | 언급된 경로 중 실제로 존재하지 않는 것이 있음 | README.md 자체가 없음 |
| `required_documents` | 설정(`.ai-standard.*`)의 `required_documents` 목록 | 목록에 있는 문서 파일이 실제로 없음 | 설정에 `required_documents` 미지정 |
| `config_commands` | 설정의 `verify_commands` / 설정 로드 자체 | `verify_commands` 안에 빈 문자열이 있음, 또는 설정 파싱·검증 자체가 실패함 | (없음 — 이 검사는 항상 PASS 또는 FAIL 로 판정된다) |
| `current_status` | `.ai/CURRENT.md` 의 블로커와 `.ai/STATUS.md` 의 표 셀 | STATUS 표에 `FAIL` 로 표기된 셀이 있는데 CURRENT 의 블로커가 "없음"으로 적혀 있음 (모순) | `.ai/CURRENT.md` 와 `.ai/STATUS.md` 가 둘 다 없음. 단, 둘 중 하나만 없으면 쌍이 깨진 것으로 보고 FAIL 로 판정한다 |
| `status_evidence` | `.ai/STATUS.md` 의 3칸 표(`\| 항목 \| 상태 \| 근거 \|`) | 상태 칸이 `PASS` 인데 근거 칸이 비어 있는 행이 있음 | `.ai/STATUS.md` 가 없음 |
| `error_codes` | 코드 파일에서 사용하는 `"APP-CATEGORY-SUBJECT-DISCRIMINATOR"` 형태의 오류 코드 문자열 vs 프로젝트 루트 또는 `docs/` 의 `ERROR_CATALOG.md` | 코드가 쓰는 오류 코드가 카탈로그 본문에 등록돼 있지 않음 | 프로젝트 `ERROR_CATALOG.md` 가 없음 (`templates/ERROR_CATALOG.md` 는 양식이므로 검사 대상에서 제외) |

- 이 검사들은 하나라도 FAIL 이면 전체 `status` 가 FAIL, 실행된 검사가 하나도 없으면
  전체가 NOT_RUN, 그 외에는 PASS 다 (`scripts/check_document_sync.py::run_document_sync`).
- 이 표에 없는 것(문장의 정확성, 최신성, 문체)은 이 도구가 판정하지 않는다. §6 참고.

## 5. NOT_RUN 원칙

- 검사를 실행하지 않았으면 결과는 PASS 가 아니라 **NOT_RUN** 이다. 실행 여부와 통과 여부를
  섞지 않는다.
- `verify_project.py` 와 `check_document_sync.py` 모두 이 원칙을 코드로 강제한다:
  실행된 검사(PASS/FAIL)가 하나도 없으면 전체 상태는 NOT_RUN 이지 PASS 가 아니다.
- 문서에 "완료"라고 적으려면 그 완료를 뒷받침하는 실행 근거(명령, 테스트 이름, 로그 경로,
  커밋 해시)가 있어야 한다. 근거 없이 완료로 적힌 항목은 감사(§8, Phase 8) 대상이다.
- 도구가 없거나(`shutil.which` 실패) 설정이 비어 있어서 실행할 수 없었던 검사를
  실행한 것처럼 기록하지 않는다.

## 6. 이 표준이 보장하지 않는 것

- 자연어 설명의 정확성 자체(예: "이 함수는 X 를 한다"는 문장이 실제로 맞는지)는
  기계 검사로 보장하지 않는다. 사람 또는 리뷰하는 AI 의 책임이다.
- 문서 스타일(어투, 문단 구성), 다국어 번역 동기화, 문서 커버리지(%)를 강제하지 않는다.
- `check_document_sync.py` 의 PASS 는 "문서가 완벽하다"가 아니라 "표에 정의된 6개 정합성
  조건을 위반하지 않았다"는 뜻으로 읽는다.

## 7. 위반 시 처리

- `check_document_sync.py` 가 FAIL 을 보고하면, 코드나 문서 중 실제 상태에 맞게 맞는 쪽을
  고친다. 검사를 통과시키기 위해 문서 내용을 얼버무리지 않는다(예: 존재하지 않는 경로를
  README 에서 지우는 대신 실제로 그 경로가 필요한지부터 확인한다).
- 반복적으로 같은 항목이 FAIL 하면 원인을 STATUS 의 "알려진 실패"에 남기고, 재발 방지를
  코드 수준에서 검토한다(예: Phase 5 자기참조 오탐 사례 — `docs/AI_WORKFLOW.md` 참고).
