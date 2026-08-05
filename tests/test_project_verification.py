"""test_project_verification.py — Phase 5: verify_project 실동작 검증.

외부에서 관찰 가능한 결과(.ai/verification.json, run_verification() 반환값)를 검증한다.
- 실행한 검사만 PASS/FAIL 로 기록되고, 실행하지 않은 검사는 NOT_RUN 으로 남는다.
- 결과 파일이 schemas/verification.schema.json 에 유효하다.
- result_hash 로 결과 파일의 변조를 탐지한다.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

from scripts import check_forbidden_patterns as cfp
from scripts import verify_project as vp

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "verification.schema.json"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        errors="replace",
        check=True,
    )


def _write_config(repo: Path, data: dict) -> None:
    (repo / ".ai-standard.json").write_text(json.dumps(data), encoding="utf-8")


def _write_script(repo: Path, name: str, exit_code: int) -> str:
    """워크스페이스 안에 종료 코드가 정해진 스크립트를 만들고, 상대 경로 명령 문자열을 반환한다.

    `python -c "..."` 형태는 Windows 에서 _split_command() 가 posix=False 로
    분리하면서 따옴표가 토큰에 그대로 남는다 (예: '"import sys; sys.exit(0)"').
    이 문자열은 그 자체로 유효한 파이썬 문자열 리터럴이라 조용히 아무 일도
    하지 않고 종료코드 0으로 끝나버려 종료코드를 검증하는 테스트에 쓸 수 없다.
    그래서 실제 파일로 스크립트를 두고 공백 없는 상대경로로 호출한다.
    """
    script = repo / name
    script.write_text(f"import sys\nsys.exit({exit_code})\n", encoding="utf-8")
    return f"{sys.executable} {name}"


def _check(report: dict, name: str) -> dict:
    for c in report["checks"]:
        if c["name"] == name:
            return c
    raise AssertionError(f"check 누락: {name} (보고된 checks: {[c['name'] for c in report['checks']]})")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_passing_test_command_records_pass_exit_code_and_log(git_repo: Path) -> None:
    command = _write_script(git_repo, "exit0.py", 0)
    _write_config(git_repo, {"test_command": command})
    report = vp.run_verification(git_repo)
    check = _check(report, "tests")
    assert check["status"] == "PASS"
    assert check["exit_code"] == 0
    assert Path(check["log_file"]).is_file()
    assert "$ " in Path(check["log_file"]).read_text(encoding="utf-8")


def test_failing_test_command_records_fail_and_exit_code(git_repo: Path) -> None:
    command = _write_script(git_repo, "exit3.py", 3)
    _write_config(git_repo, {"test_command": command})
    report = vp.run_verification(git_repo)
    check = _check(report, "tests")
    assert check["status"] == "FAIL"
    assert check["exit_code"] == 3
    assert report["status"] == "FAIL"


def test_missing_tool_in_verify_commands_is_not_run(git_repo: Path) -> None:
    _write_config(git_repo, {"verify_commands": ["no_such_tool_xyz --check"]})
    report = vp.run_verification(git_repo)
    check = _check(report, "verify:no_such_tool_xyz")
    assert check["status"] == "NOT_RUN"
    assert check["status"] != "PASS"


def test_unconfigured_verify_and_test_commands_are_not_run(git_repo: Path) -> None:
    # verify_commands / test_command 를 아예 지정하지 않으면 해당 검사는
    # NOT_RUN 으로 기록되어야 한다. 실행하지 않은 검사를 PASS 로 조작하지 않는다.
    report = vp.run_verification(git_repo)
    verify_check = _check(report, "verify_commands")
    test_check = _check(report, "tests")
    assert verify_check["status"] == "NOT_RUN"
    assert test_check["status"] == "NOT_RUN"
    assert verify_check["status"] != "PASS"
    assert test_check["status"] != "PASS"


def test_result_file_is_valid_against_schema(git_repo: Path) -> None:
    vp.run_verification(git_repo)
    out = git_repo / ".ai" / "verification.json"
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=_schema())


def test_result_hash_verifies_and_detects_tampering(git_repo: Path) -> None:
    vp.run_verification(git_repo)
    out = git_repo / ".ai" / "verification.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert vp.verify_result_hash(data) is True

    tampered = dict(data)
    # result_hash 는 그대로 두고 본문만 조작한다. 현재 값과 다른 값으로 바꿔야
    # 실제 변조가 된다 (우연히 같은 값이면 해시가 그대로 일치해버린다).
    other_status = next(s for s in ("PASS", "FAIL", "NOT_RUN") if s != data["status"])
    tampered["status"] = other_status
    assert vp.verify_result_hash(tampered) is False


def test_non_git_directory_git_diff_check_not_run(tmp_path: Path) -> None:
    folder = tmp_path / "nongit"
    folder.mkdir()
    report = vp.run_verification(folder)
    check = _check(report, "git_diff_check")
    assert check["status"] == "NOT_RUN"
    assert report["commit"] == "NONE"


def test_custom_out_path_is_used(git_repo: Path) -> None:
    out_path = git_repo / "custom_out.json"
    report = vp.run_verification(git_repo, out_path=str(out_path))
    assert out_path.is_file()
    assert report["_out_path"] == str(out_path)
    # 기본 위치에는 생성되지 않는다
    assert not (git_repo / ".ai" / "verification.json").is_file()


def test_cli_json_output_matches_run_verification(git_repo: Path, capsys: pytest.CaptureFixture) -> None:
    rc = vp.main(["--workspace", str(git_repo), "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["status"] in ("PASS", "FAIL", "NOT_RUN")
    assert rc == (1 if data["status"] == "FAIL" else 0)


def test_config_error_is_recorded_as_fail(git_repo: Path) -> None:
    (git_repo / ".ai-standard.json").write_text(json.dumps({"risk_level": "critical"}), encoding="utf-8")
    report = vp.run_verification(git_repo)
    check = _check(report, "config")
    assert check["status"] == "FAIL"
    assert report["status"] == "FAIL"


def test_verification_logs_do_not_cause_forbidden_pattern_false_positives(git_repo: Path) -> None:
    """회귀 방지: verify_project 는 자기 검사 단계로 check_forbidden_patterns.py 를
    subprocess 로 실행하고, 그 표준출력(탐지된 패턴 이름과 컨텍스트, 예:
    "shell_true ... shell=True")을 그대로 .ai/verification_logs/*/forbidden_patterns.log
    에 남긴다. 그 로그 파일을 다시 스캔 대상에 포함하면 로그에 복사된 컨텍스트가
    또 매칭되어 자기참조 오탐이 생긴다 (이 저장소에서 실제로 발생했던 회귀:
    check_forbidden_patterns.py 가 verify_project.py 자신이 남긴 로그를 재탐지해
    FAIL 로 회귀함). collect_files() 가 .ai/verification_logs 하위를 구조적으로
    제외하는지 검증한다.
    """
    # 실제로 탐지될 금지 패턴을 하나 심어서, verify_project 내부의 forbidden_patterns
    # 검사가 진짜로 FAIL 하고 그 탐지 내용이 로그에 복사되게 만든다.
    (git_repo / "src").mkdir()
    (git_repo / "src" / "bad.py").write_text("subprocess.run(cmd, shell=True)\n", encoding="utf-8")

    vp.run_verification(git_repo)
    log_dir = git_repo / ".ai" / "verification_logs"
    assert log_dir.is_dir()
    log_files = list(log_dir.rglob("forbidden_patterns.log"))
    assert log_files, "forbidden_patterns.log 가 생성되어야 회귀 재현 조건이 성립한다"
    log_text = log_files[0].read_text(encoding="utf-8")
    assert "shell_true" in log_text or "shell=True" in log_text, (
        "로그에 실제 탐지 내용이 복사되어야 회귀를 재현할 수 있다"
    )

    # verification_logs 를 포함해 저장소 전체를 다시 스캔해도, 로그 파일 자체가
    # finding 경로로 나오면 안 된다 (구조적으로 제외되어야 함).
    scan = cfp.run_scan(git_repo, [], None)
    offending = [f for f in scan["findings"] if "verification_logs" in f["path"]]
    assert offending == []
