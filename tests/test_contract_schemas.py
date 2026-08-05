"""Phase 4: 요청·결과·오류 스키마와 예제 계약 헬퍼의 정합성 검증.

- 스키마 자체가 유효한 draft-07 인지
- 최소/전체 인스턴스 검증, 필수 필드 누락·형식 위반 거부
- 예제(contracts.py)가 실제로 스키마에 맞는 객체를 생성하는지
- 오류 코드(실패 종류)와 trace_id(개별 사건)의 분리
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft7Validator
from referencing import Registry, Resource

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = PROJECT_ROOT / "schemas"


def _load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


REQUEST_SCHEMA = _load("request.schema.json")
RESULT_SCHEMA = _load("result.schema.json")
ERROR_SCHEMA = _load("error.schema.json")

# result.schema.json 이 error.schema.json 을 상대 $ref 로 참조한다.
# 각 스키마를 $id 로 등록하면 상대 참조가 $id 기준으로 해석된다.
_REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema))
    for schema in (REQUEST_SCHEMA, RESULT_SCHEMA, ERROR_SCHEMA)
)


def _validator(schema: dict) -> Draft7Validator:
    return Draft7Validator(schema, registry=_REGISTRY)


def validate(schema: dict, instance: dict) -> list[str]:
    """오류 메시지 목록을 반환한다. 빈 목록이면 유효."""
    return [e.message for e in _validator(schema).iter_errors(instance)]


VALID_ERROR = {
    "code": "APP-AUTH-TOKEN-401",
    "trace_id": "trace-abc123",
    "category": "auth",
    "user_message": "로그인이 만료되었습니다.",
    "retryable": True,
    "source": "coordinator.auth",
    "details": {},
    "occurred_at": "2026-08-04T12:00:00+00:00",
}


class TestSchemasAreValidDraft7:
    @pytest.mark.parametrize("schema", [REQUEST_SCHEMA, RESULT_SCHEMA, ERROR_SCHEMA])
    def test_schema_itself_valid(self, schema):
        Draft7Validator.check_schema(schema)


class TestRequestSchema:
    def test_minimal_valid(self):
        assert validate(REQUEST_SCHEMA, {
            "request_id": "req-1", "trace_id": "trace-1",
            "capability": "notes", "operation": "add", "contract_version": "1.0",
        }) == []

    def test_missing_trace_id_rejected(self):
        errors = validate(REQUEST_SCHEMA, {
            "request_id": "req-1", "capability": "notes",
            "operation": "add", "contract_version": "1.0",
        })
        assert any("trace_id" in e for e in errors)

    def test_unknown_field_rejected(self):
        errors = validate(REQUEST_SCHEMA, {
            "request_id": "req-1", "trace_id": "trace-1", "capability": "notes",
            "operation": "add", "contract_version": "1.0", "global_state": {},
        })
        assert errors  # additionalProperties: false

    def test_invalid_priority_rejected(self):
        errors = validate(REQUEST_SCHEMA, {
            "request_id": "req-1", "trace_id": "trace-1", "capability": "notes",
            "operation": "add", "contract_version": "1.0", "priority": "urgent!!",
        })
        assert errors


class TestErrorSchema:
    def test_valid_error(self):
        assert validate(ERROR_SCHEMA, VALID_ERROR) == []

    def test_code_format_enforced(self):
        bad = dict(VALID_ERROR, code="not a code")
        assert validate(ERROR_SCHEMA, bad)

    def test_code_needs_three_tokens(self):
        bad = dict(VALID_ERROR, code="APP-AUTH")
        assert validate(ERROR_SCHEMA, bad)

    def test_category_restricted_to_boundaries(self):
        bad = dict(VALID_ERROR, category="everything")
        assert validate(ERROR_SCHEMA, bad)

    def test_retryable_required(self):
        bad = {k: v for k, v in VALID_ERROR.items() if k != "retryable"}
        assert validate(ERROR_SCHEMA, bad)

    def test_error_code_is_kind_not_incident(self):
        """오류 코드는 실패 종류이고 trace_id 가 개별 사건이다: 같은 코드 + 다른 trace_id 가 모두 유효."""
        incident_a = dict(VALID_ERROR, trace_id="trace-event-a")
        incident_b = dict(VALID_ERROR, trace_id="trace-event-b")
        assert validate(ERROR_SCHEMA, incident_a) == []
        assert validate(ERROR_SCHEMA, incident_b) == []


class TestResultSchema:
    def test_success_result(self):
        assert validate(RESULT_SCHEMA, {
            "success": True, "data": {"id": 1}, "error": None,
            "trace_id": "trace-1", "contract_version": "1.0",
        }) == []

    def test_failure_requires_error_object(self):
        errors = validate(RESULT_SCHEMA, {
            "success": False, "data": None, "error": None,
            "trace_id": "trace-1", "contract_version": "1.0",
        })
        assert errors  # success=false 인데 error 가 null

    def test_failure_with_error(self):
        assert validate(RESULT_SCHEMA, {
            "success": False, "data": None, "error": VALID_ERROR,
            "trace_id": "trace-1", "contract_version": "1.0",
        }) == []

    def test_success_with_error_rejected(self):
        errors = validate(RESULT_SCHEMA, {
            "success": True, "data": {}, "error": VALID_ERROR,
            "trace_id": "trace-1", "contract_version": "1.0",
        })
        assert errors  # success=true 면 error 는 null 이어야 함


def _example_modules(example: str):
    """예제 디렉터리를 sys.path 에 얹고 (contracts, coordinator 조립 함수) 를 반환한다."""
    example_dir = PROJECT_ROOT / "examples" / example
    sys.path.insert(0, str(example_dir))
    try:
        for mod in list(sys.modules):
            if mod in ("contracts", "notes_coordinator", "notes_service", "notes_repository",
                       "status_coordinator", "status_service", "system_adapter",
                       "main", "server"):
                del sys.modules[mod]
        if example == "python-desktop":
            import contracts
            import main
            return contracts, main
        import contracts
        import server
        return contracts, server
    finally:
        sys.path.remove(str(example_dir))


class TestPythonDesktopExampleConformsToSchemas:
    def test_add_and_list_roundtrip(self, tmp_path):
        contracts, main_mod = _example_modules("python-desktop")
        coordinator = main_mod.build_coordinator(tmp_path / "notes.json")
        trace_id = contracts.new_trace_id()

        request = contracts.make_request("notes", "add", {"text": "hello"},
                                         trace_id=trace_id, caller="test")
        assert validate(REQUEST_SCHEMA, request) == []
        result = coordinator.handle(request)
        assert validate(RESULT_SCHEMA, result) == []
        assert result["success"] is True
        assert result["trace_id"] == trace_id

        listing = coordinator.handle(
            contracts.make_request("notes", "list", trace_id=trace_id, caller="test"))
        assert validate(RESULT_SCHEMA, listing) == []
        assert [n["text"] for n in listing["data"]] == ["hello"]

    def test_validation_failure_produces_schema_valid_error(self, tmp_path):
        contracts, main_mod = _example_modules("python-desktop")
        coordinator = main_mod.build_coordinator(tmp_path / "notes.json")
        trace_id = contracts.new_trace_id()
        result = coordinator.handle(
            contracts.make_request("notes", "add", {"text": "   "},
                                   trace_id=trace_id, caller="test"))
        assert result["success"] is False
        assert validate(RESULT_SCHEMA, result) == []
        assert validate(ERROR_SCHEMA, result["error"]) == []
        assert result["error"]["trace_id"] == trace_id

    def test_storage_failure_normalized_not_raised(self, tmp_path):
        contracts, main_mod = _example_modules("python-desktop")
        broken = tmp_path / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        coordinator = main_mod.build_coordinator(broken)
        result = coordinator.handle(
            contracts.make_request("notes", "list",
                                   trace_id=contracts.new_trace_id(), caller="test"))
        assert result["success"] is False
        assert result["error"]["code"] == "NOTES-STORAGE-WRITE-500"
        assert validate(ERROR_SCHEMA, result["error"]) == []


class TestWebServiceExampleConformsToSchemas:
    def test_health_roundtrip(self):
        contracts, server_mod = _example_modules("web-service")
        coordinator = server_mod.build_coordinator()
        result = server_mod.handle_status(coordinator)
        assert validate(RESULT_SCHEMA, result) == []
        assert result["success"] is True
        assert result["data"]["status"] == "ok"

    def test_incoming_trace_id_is_preserved(self):
        contracts, server_mod = _example_modules("web-service")
        coordinator = server_mod.build_coordinator()
        result = server_mod.handle_status(coordinator, trace_id="trace-from-gateway")
        assert result["trace_id"] == "trace-from-gateway"

    def test_unknown_operation_returns_contract_error(self):
        contracts, server_mod = _example_modules("web-service")
        coordinator = server_mod.build_coordinator()
        result = coordinator.handle(
            contracts.make_request("status", "reboot-all",
                                   trace_id=contracts.new_trace_id()))
        assert result["success"] is False
        assert result["error"]["category"] == "contract"
        assert validate(RESULT_SCHEMA, result) == []

    def test_retry_keeps_trace_id_but_new_request_id(self):
        contracts, _ = _example_modules("web-service")
        trace_id = contracts.new_trace_id()
        first = contracts.make_request("status", "health", trace_id=trace_id)
        retry = contracts.make_request("status", "health", trace_id=trace_id)
        assert first["trace_id"] == retry["trace_id"]
        assert first["request_id"] != retry["request_id"]
