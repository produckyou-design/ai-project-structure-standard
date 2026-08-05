# web-service 예제 — 계층형 Coordinator 최소 구현

표준 라이브러리만 사용하는 최소 상태(health) 서비스다.
거대한 전역 오케스트레이터 없이, status 도메인 하나가 표준 계층을 따른다.

```text
server.py             Entry Layer (Route) — HTTP 수신, trace_id 확보, 요청 생성, 응답 변환
status_coordinator.py Coordinator         — 요청 정규화, 라우팅, 오류 정규화, 결과 봉투
status_service.py     Service             — 상태 판정 규칙
system_adapter.py     Adapter             — 운영체제(외부 경계) 접근의 단일 소유자
contracts.py          계약 헬퍼            — schemas/{request,result,error}.schema.json 준수
```

## 실행

```bash
python server.py --once
```

서버 모드 (127.0.0.1 에만 바인딩):

```bash
python server.py
```

```bash
curl http://127.0.0.1:8765/status
```

## 계약 확인 포인트

- 게이트웨이에서 온 `X-Trace-Id` 헤더가 있으면 같은 trace_id 를 유지하고, 없으면 Route 가 발급한다.
- 응답 헤더 `X-Trace-Id` 로 trace_id 를 되돌려 전 구간 추적을 잇는다.
- 실패도 같은 결과 봉투(`success=false` + `error.schema.json`)로 반환한다.
- Coordinator 에 HTTP·OS 접근 코드가 없다 (Route/Adapter 의 책임).

스키마 정합성은 `tests/test_contract_schemas.py` 가 검증한다.
