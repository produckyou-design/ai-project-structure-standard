# SECURITY_STANDARD.md — 구조적 보안 표준

- 상태: ACTIVE (Phase 3)
- 관련 도구: `scripts/check_secrets.py`, `scripts/check_forbidden_patterns.py`
- 프로젝트 적용 기록: `templates/SECURITY.md`

## 1. 목적

비용이 들거나 과도한 방어(유료 인증서, HSM, TPM 필수, DRM, 안티디버깅, 백신 등)를
요구하지 않고, **코딩 단계에서 구조적으로 적용 가능한 보안 규칙**만 자동 검사로 강제한다.

## 2. 자동 검사 연결

| 규칙 | 검사 도구 |
|---|---|
| 시크릿을 코드/로그/Git/테스트 결과/빌드에 넣지 않는다 | `check_secrets.py` |
| 시크릿 원문을 출력하지 않는다 (마스킹) | `check_secrets.py` |
| `shell=True`, `eval(`, `exec(`, `os.system(` 금지 | `check_forbidden_patterns.py` |
| TLS 검증 끄기(`verify=False`) 금지 | `check_forbidden_patterns.py` |
| `0.0.0.0` 바인딩 금지 (로컬 서버는 127.0.0.1) | `check_forbidden_patterns.py` |
| 빈 except / 예외 무조건 삼키기 금지 | `check_forbidden_patterns.py` |
| 하드코딩 관리자 권한 금지 | `check_forbidden_patterns.py` |
| 개발용 인증 우회 금지 | `check_forbidden_patterns.py` |
| 사용자 입력 기반 프록시 금지 | `check_forbidden_patterns.py` |
| 평문 비밀정보 fallback 금지 | `check_forbidden_patterns.py` |
| 시크릿 파일이 Git 에 추적되는지 | `preflight.py` (`secret_files_tracked`) |

## 3. 시크릿 검사 (check_secrets.py)

### 3.1 검사 대상

- 소스 파일, 설정 파일, 로그, 테스트 결과, 빌드 산출물(텍스트 파일)
- 압축 파일 내부의 텍스트 항목: `.zip`, `.tar`, `.tar.gz`, `.tgz`
- Git diff 의 추가된 줄 (`--git-diff`)
- 4MB 초과 파일과 바이너리(NUL 포함) 파일은 건너뛴다.

### 3.2 패턴과 심각도

| 패턴 | 심각도 | 예 |
|---|---|---|
| `private_key` | HIGH | `-----BEGIN RSA PRIVATE KEY-----` |
| `aws_access_key` | HIGH | `AKIA...` |
| `google_api_key` | HIGH | `AIza...` |
| `github_token` | HIGH | `ghp_...`, `github_pat_...` |
| `slack_token` | HIGH | `xoxb-...` |
| `openai_key` | HIGH | `sk-ant-...`, `sk-...`(20자 이상) — 아래 예외 문서 참고 |
| `stripe_key` | HIGH | `sk_live_...`, `pk_test_...` |
| `slack_webhook` | MEDIUM | `hooks.slack.com/services/...` |
| `discord_webhook` | MEDIUM | `discord.com/api/webhooks/...` |
| `jwt_token` | MEDIUM | `eyJ...` 3세그먼트 |
| `authorization` | MEDIUM | `Authorization: ***` (Bearer/Basic 헤더) |
| `password` | MEDIUM | `password = "..."` |
| `api_key` | MEDIUM | `api_key = "..."`, `client_secret = "..."` |

상태 결정: HIGH → **FAIL** (exit 1), MEDIUM → **WARN**, 예외 → **EXCEPTED**.

### 3.3 마스킹 규칙

실제 시크릿 값을 절대 출력하지 않는다. 출력 가능 정보:

- 파일, 줄 번호
- 패턴 종류, 심각도
- 마스킹된 일부 문자열 (예: `sk-te***`)

개인키 블록과 Authorization 헤더는 블록 단위로 마스킹한다.

### 3.4 실행

```bash
python scripts/check_secrets.py                      # 저장소 전체
python scripts/check_secrets.py --path scripts docs  # 특정 경로만
python scripts/check_secrets.py --git-diff           # diff 의 추가된 줄 검사
python scripts/check_secrets.py --json               # 기계 판독 출력
```

## 4. 금지 패턴 검사 (check_forbidden_patterns.py)

- 내장 패턴은 §2 표의 목록과 같다.
- 프로젝트 설정의 `forbidden_patterns` 로 정규식 패턴을 추가할 수 있다.
- 모든 탐지를 무조건 오류로 처리하지 않는다. 설정의 `allow_exceptions` 로 예외를 허용한다.

### 4.1 예외 형식

```
파일:패턴:허용이유[:만료조건]
```

- `파일` 과 `패턴` 은 `*` 와일드카드를 지원한다.
- `패턴` 은 패턴 id 전체 또는 부분 문자열로 일치한다.
- `만료조건` 을 넣으면 재검토 시점을 남길 수 있다.

```yaml
allow_exceptions:
  - "tests/fixtures/*.py:eval_call:테스트용 평가 코드. fixture 로 한정:2026-12-31"
```

### 4.2 상태

예외에 걸리면 `EXCEPTED` 로 기록되고 FAIL 집계에서 제외된다.
예외 없는 탐지는 **FAIL** (exit 1) 이다.

## 5. 테스트 원칙

- 테스트에는 **실제 비밀값을 사용하지 않는다.** synthetic token 만 사용한다.
- 테스트 검증 항목: 탐지 대상/비대상 샘플, 마스킹(원문 미출력), 허용 예외, 압축 파일, Git diff.

## 6. 제외 대상 (이 표준이 요구하지 않음)

- 유료 코드 서명 인증서, HSM, TPM 필수, 강한 DRM
- 안티디버깅, 패커, 과도한 난독화
- 백신 기능, 프로세스 감시, 하드웨어 지문 수집, 상용 보안 솔루션

필요한 프로젝트가 별도로 선택한다.

## 7. 사고 대응

- 시크릿이 코드·로그·Git·빌드에 노출된 경우: 즉시 회전(rotate)하고 노출 경위를 기록한다.
- 노출된 커밋 기록이 있다면 Git 히스토리 정리와 함께 재발 방지(예외 남기지 않기)를 적용한다.
