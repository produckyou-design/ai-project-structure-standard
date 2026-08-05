# ERROR_CATALOG.md

> 프로젝트에 복사해 쓰는 템플릿. 오류 코드는 사용 전에 이 카탈로그에 등록한다.
> 형식: `<APP>-<CATEGORY>-<SUBJECT>-<DISCRIMINATOR>` (`docs/ERROR_STANDARD.md` 참조)

- 프로젝트:
- 갱신:

---

## 등록된 오류 코드

| 코드 | category | retryable | 의미 | user_message 예 | 발급 위치 |
|---|---|---|---|---|---|
| APP-AUTH-TOKEN-401 | auth | true | 액세스 토큰 만료/무효 | 로그인이 만료되었습니다. 다시 로그인해 주세요. | AuthCoordinator |
| APP-DATA-PROVIDER-429 | provider | true | 외부 공급자 요청 한도 초과 | 잠시 후 다시 시도해 주세요. | MarketDataAdapter |
| APP-STORAGE-WRITE-500 | storage | false | 로컬 저장 실패 | 저장에 실패했습니다. 디스크 상태를 확인해 주세요. | FileRepository |
| APP-UPDATE-MANIFEST-409 | update | false | 업데이트 manifest 불일치 | 업데이트를 적용할 수 없습니다. 기존 버전을 유지합니다. | UpdateCoordinator |

## 작성 규칙

- 같은 실패 종류에는 항상 같은 코드를 쓴다. 개별 사건 구분은 trace_id 가 담당한다.
- 코드를 삭제하지 않는다. 폐기 시 `(deprecated, 사유, 대체 코드)` 를 비고로 남긴다.
- user_message 에 시크릿, 내부 경로, 스택트레이스를 넣지 않는다.
- retryable=true 인 코드도 재시도 상한을 코드 사용처에 명시한다.

## 폐기된 코드

| 코드 | 폐기일 | 사유 | 대체 |
|---|---|---|---|
| (없음) | | | |
