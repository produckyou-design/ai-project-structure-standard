"""test_forbidden_patterns.py — Phase 3: 금지 패턴 탐지 검증.

외부에서 관찰 가능한 결과(report)를 검증한다.
탐지 대상/비대상 샘플, 설정 기반 예외를 확인한다.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts import check_forbidden_patterns as cfp


def _write(tmp: Path, name: str, content: str) -> Path:
    p = tmp / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _scan(tmp: Path, names: list[str], config: dict | None = None) -> dict:
    return cfp.run_scan(tmp, names, config)


def _patterns(report: dict) -> set[str]:
    return {f["pattern"] for f in report["findings"]}


def test_detects_shell_true(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "subprocess.run(cmd, shell=True)\n")
    report = _scan(tmp_path, ["a.py"])
    assert report["status"] == "FAIL"
    assert "shell_true" in _patterns(report)
    assert report["findings"][0]["line"] == 1


def test_detects_eval_exec_os_system(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "value = eval(expr)\nexec(code)\nos.system('ls')\n")
    report = _scan(tmp_path, ["a.py"])
    assert {"eval_call", "exec_call", "os_system"} <= _patterns(report)


def test_detects_verify_false(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "resp = requests.get(url, verify=False)\n")
    report = _scan(tmp_path, ["a.py"])
    assert "verify_false" in _patterns(report)


def test_detects_bind_all(tmp_path: Path) -> None:
    _write(tmp_path, "srv.py", "app.run(host='0.0.0.0', port=8080)\n")
    report = _scan(tmp_path, ["srv.py"])
    assert "bind_all" in _patterns(report)


def test_detects_empty_except(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "try:\n    do()\nexcept:\n    pass\n")
    report = _scan(tmp_path, ["a.py"])
    assert "empty_except" in _patterns(report)
    assert report["findings"][0]["line"] == 3

    _write(tmp_path, "b.py", "try:\n    do()\nexcept: pass\n")
    report = _scan(tmp_path, ["b.py"])
    assert "empty_except" in _patterns(report)


def test_detects_swallow_and_admin_and_bypass(tmp_path: Path) -> None:
    _write(tmp_path, "a.py",
           "try:\n    do()\nexcept Exception: pass\n"
           "is_admin = True\n"
           "bypass_auth = True\n")
    report = _scan(tmp_path, ["a.py"])
    assert {"swallow_exception", "hardcoded_admin", "dev_auth_bypass"} <= _patterns(report)


def test_does_not_detect_benign_code(tmp_path: Path) -> None:
    _write(tmp_path, "ok.py",
           "subprocess.run(['ls', '-la'])\n"
           "result = evaluate(expr)   # 단순 함수 이름은 탐지하지 않음\n"
           "executor = ThreadPoolExecutor()\n"
           "verify = True\n"
           "host = '127.0.0.1'\n"
           "except_helper()\n"
           "exceptional = True\n"
           "is_admin = check_permission()\n"
           "proxy = load_proxy_from_config()\n")
    report = _scan(tmp_path, ["ok.py"])
    assert report["status"] == "PASS"
    assert report["findings"] == []


def test_config_custom_patterns_are_scanned(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "TODO_XXX = 1\n")
    config = {"forbidden_patterns": [r"TODO_XXX"]}
    report = _scan(tmp_path, ["a.py"], config)
    assert report["status"] == "FAIL"
    assert any(p.startswith("config:") for p in _patterns(report))


def test_config_exception_marks_excepted(tmp_path: Path) -> None:
    _write(tmp_path, "legacy.py", "value = eval(expr)\n")
    _write(tmp_path, "new.py", "value = eval(expr)\n")
    config = {"allow_exceptions": ["legacy.py:eval_call:레거시 모듈, 전면 교체 예정:2026-12-31"]}
    report = _scan(tmp_path, ["legacy.py", "new.py"], config)
    by_path = {f["path"]: f["status"] for f in report["findings"]}
    assert by_path["legacy.py"] == "EXCEPTED"
    assert by_path["new.py"] == "FAIL"
    assert report["status"] == "FAIL"


def test_context_is_masked(tmp_path: Path, capsys) -> None:
    secret = "sk-test-abcdefghijklmnopqrstuvwxyz12"
    _write(tmp_path, "a.py", f"subprocess.run(cmd, shell=True)  # token={secret}\n")
    rc = cfp.main(["--workspace", str(tmp_path), "--json"])
    out = capsys.readouterr().out
    assert rc == 1
    assert secret not in out
    data = json.loads(out)
    assert data["status"] == "FAIL"
    assert "***" in data["findings"][0]["masked"]


def test_context_masks_jwt_not_covered_by_old_patterns(tmp_path: Path, capsys) -> None:
    # mask_sensitive 의 상위집합 확장 검증: JWT 도 컨텍스트에서 마스킹되어야 한다
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    _write(tmp_path, "a.py", f"x = eval(y)  # {jwt}\n")
    rc = cfp.main(["--workspace", str(tmp_path), "--json"])
    out = capsys.readouterr().out
    assert rc == 1
    assert jwt not in out
    data = json.loads(out)
    masked = data["findings"][0]["masked"]
    assert "eyJ***" in masked


def test_invalid_config_regex_is_reported_not_crash(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "x = 1\n")
    config = {"forbidden_patterns": ["(unclosed"]}
    report = _scan(tmp_path, ["a.py"], config)
    assert report["status"] == "FAIL"
    assert any(f["pattern"].startswith("invalid_pattern:") for f in report["findings"])
    assert "정규식 컴파일 실패" in report["findings"][0]["masked"]


def test_cli_text_output(tmp_path: Path, capsys) -> None:
    _write(tmp_path, "a.py", "x = eval(y)\n")
    rc = cfp.main(["--workspace", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "check_forbidden_patterns: FAIL" in out
    assert "eval_call" in out
