# TEST_PLAN.md

- 상태: ACTIVE (Phase 0 완료)
- 원칙: 실행하지 않은 검사는 `NOT_RUN`으로 기록한다. 근거 없는 PASS를 기록하지 않는다.

---

## 1. 공통 검증 기준

모든 Phase는 다음 기본 검증을 적용한다.

- 문법 검사 (`python -m py_compile` 등)
- 정적 분석 가능 시 실행
- 단위 테스트 (`python -m pytest tests/ -v`)
- `git diff --check` (공백 오류)
- 시크릿 검사 (Phase 3 이후)
- 금지 패턴 검사 (Phase 3 이후)
- 변경 파일 확인
- 문서 정합성 확인 (Phase 5 이후)

## 2. Phase별 테스트

### Phase 0 (본 Phase)

| 검사 | 방법 | 기대 |
|---|---|---|
| Git 상태 기록 | `git status` | 저장소 초기화, `.freebuff/` 제외 확인 |
| 파일 충돌 없음 | 디렉터리 조사 | 신규 생성 경로와 충돌 없음 |
| 문서 정합성 | 4개 문서 상호 대조 | Phase 범위·책임·통과 조건이 일치 |
| 빈 파일 없음 | 파일 내용 검사 | 모든 문서가 실질 내용 포함 |

### Phase 1

| 테스트 | 검증 내용 |
|---|---|
| `test_signatures.py` | 시작/종료 서명 생성, 실제 Git 브랜치·HEAD·status 수집, diff hash, UNKNOWN 모델 처리, ledger append-only, previous/current hash 연결 |
| `test_checkpoint.py` | Git 상태·patch·신규 파일·문서 보존, 자동 commit 미생성 |
| `test_handoff.py` | 단일 MD 인계 번들, 상태·변경·테스트·블로커·다음 작업 포함, 민감정보 원문 미출력 |

실제 수행: 임시 Git 저장소에서 시작 서명 → 파일 수정 → 체크포인트 → 종료 서명 → 인계 번들 → ledger 해시 연결 검증 → 전체 관련 테스트 실행.

### Phase 2

| 테스트 | 검증 내용 |
|---|---|
| `test_preflight.py` | 정상 저장소 / Git 아님 / protected branch / 미커밋 변경 / 잘못된 설정 / 필수 문서 누락 시나리오 |

### Phase 3

| 테스트 | 검증 내용 |
|---|---|
| `test_secret_scan.py` | 탐지 대상·비대상 샘플, 마스킹(원문 미출력), 압축 파일 내부, Git diff 검사 |
| `test_forbidden_patterns.py` | 금지 패턴 탐지, 설정 기반 예외(파일·이유·만료 조건·ADR 연결) |

실제 비밀값은 사용하지 않고 synthetic token만 사용한다.

### Phase 4

| 테스트 | 검증 내용 |
|---|---|
| 스키마 검증 테스트 | request/result/error 스키마의 최소 필수 필드, 계약 버전, trace_id 유지 |
| 예제 구조 검증 | 계층형 구조, GlobalOrchestrator 부재 |

### Phase 5

| 테스트 | 검증 내용 |
|---|---|
| `test_project_verification.py` | 검사별 시작·종료 시각, 명령, exit code, PASS/FAIL/NOT_RUN, 로그 위치, 결과 hash. **명령 미실행 → NOT_RUN** |
| `test_document_sync.py` | README 스크립트 존재, 필수 템플릿 존재, CURRENT/STATUS 모순, 완료 항목의 검증 증적, 오류 코드 카탈로그 등록 |

### Phase 6

| 테스트 | 검증 내용 |
|---|---|
| `test_release_manifest.py` | 매니페스트 필드, 파일별 hash, 전체 hash, manifest hash |
| `test_release_verification.py` | 작업트리 clean, source commit 일치, 검증 결과 존재·PASS, hash 일치, 롤백 지점 존재, **검증 후 artifact 변경 시 차단**, 사람 승인 필드 |

### Phase 7

| 테스트 | 검증 내용 |
|---|---|
| README 명령 재현 | README에 적힌 모든 명령을 실제 실행 |
| 예제 실행 | 3개 예제가 README 명령으로 실행 가능 |

### Phase 8 — 독립 감사

새 세션에서 다음을 수행한다.

1. Git 상태와 전체 파일 목록 확인
2. placeholder/TODO/pass/빈 구현 검색
3. README의 모든 실행 명령 재현
4. 전체 테스트 실행
5. 시크릿 검사 실행
6. 금지 패턴 검사 실행
7. 샘플 저장소에서 preflight 실행
8~13. 서명·체크포인트·인계·verification·release manifest·verify_release 차단 검증
14. NOT_RUN이 PASS로 처리되지 않는지 확인

## 3. 상태 표기

각 항목은 `PASS`, `FAIL`, `NOT_RUN`, `NOT_APPLICABLE` 중 하나로만 기록한다.
테스트 실패를 숨기거나 완료로 처리하지 않는다. 실패 항목은 다음 Phase의 인계 번들에 반드시 남긴다.
