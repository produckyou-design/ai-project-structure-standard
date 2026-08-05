"""test_preflight.py — Phase 2: preflight 와 프로젝트 설정 검증.

외부에서 관찰 가능한 결과(preflight 보고서)를 검증한다.
- 정상 임시 저장소
- Git 이 아닌 폴더
- protected branch
- 미커밋 변경
- 잘못된 설정
- 필수 문서 누락
- 시크릿 파일이 Git 에 추적되는 경우
- 설정 파일 없음(기본값), YAML 설정, CLI 출력
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import preflight


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        errors="replace",
        check=True,
    )


def _finding(report: dict, check: str) -> dict:
    for f in report["findings"]:
        if f["check"] == check:
            return f
    raise AssertionError(f"finding 누락: {check} (보고된 checks: {[x['check'] for x in report['findings']]})")


def _write_config(repo: Path, data: dict) -> None:
    (repo / ".ai-standard.json").write_text(json.dumps(data), encoding="utf-8")


def test_clean_repo_passes(git_repo: Path) -> None:
    _git(git_repo, "checkout", "-b", "feature/clean")
    report = preflight.run_preflight(git_repo)
    assert report["status"] == "PASS"
    assert _finding(report, "git_repo")["status"] == "PASS"
    assert _finding(report, "protected_branch")["status"] == "PASS"
    assert _finding(report, "worktree")["status"] == "PASS"
    assert _finding(report, "config_valid")["status"] == "PASS"
    assert report["branch"] == "feature/clean"


def test_non_git_directory_fails(tmp_path: Path) -> None:
    folder = tmp_path / "nongit"
    folder.mkdir()
    (folder / "file.txt").write_text("x", encoding="utf-8")
    report = preflight.run_preflight(folder)
    assert report["status"] == "FAIL"
    assert report["git_repo"] is False
    assert _finding(report, "git_repo")["status"] == "FAIL"


def test_protected_branch_fails(git_repo: Path) -> None:
    # git_repo fixture 는 main 브랜치, 기본 protected_branches 는 main 포함
    report = preflight.run_preflight(git_repo)
    assert report["status"] == "FAIL"
    assert _finding(report, "protected_branch")["status"] == "FAIL"
    assert _finding(report, "protected_branch")["detail"].startswith("protected branch")


def test_uncommitted_changes_warn(git_repo: Path) -> None:
    _git(git_repo, "checkout", "-b", "feature/dirty")
    (git_repo / "README.md").write_text("# modified\n", encoding="utf-8")
    report = preflight.run_preflight(git_repo)
    assert report["status"] == "WARN"
    finding = _finding(report, "worktree")
    assert finding["status"] == "WARN"
    assert "README.md" in finding["detail"]


def test_invalid_config_reports_fail(git_repo: Path) -> None:
    _write_config(git_repo, {"risk_level": "critical"})
    report = preflight.run_preflight(git_repo)
    finding = _finding(report, "config_valid")
    assert finding["status"] == "FAIL"
    assert "risk_level" in finding["detail"]
    assert report["status"] == "FAIL"


def test_missing_required_document_fails(git_repo: Path) -> None:
    _write_config(git_repo, {"required_documents": ["README.md", "docs/ARCHITECTURE.md"]})
    report = preflight.run_preflight(git_repo)
    assert _finding(report, "required_document:README.md")["status"] == "PASS"
    assert _finding(report, "required_document:docs/ARCHITECTURE.md")["status"] == "FAIL"
    assert report["status"] == "FAIL"


def test_secret_file_tracked_in_git_fails(git_repo: Path) -> None:
    (git_repo / ".env").write_text("TOKEN=sk-test-abcdef123456\n", encoding="utf-8")
    _git(git_repo, "add", ".env")
    _git(git_repo, "commit", "-m", "add env")
    report = preflight.run_preflight(git_repo)
    finding = _finding(report, "secret_files_tracked")
    assert finding["status"] == "FAIL"
    assert ".env" in finding["detail"]
    assert report["status"] == "FAIL"


def test_no_config_uses_safe_defaults(git_repo: Path) -> None:
    report = preflight.run_preflight(git_repo)
    assert report["project_name"] == "unnamed-project"
    assert report["risk_level"] == "low"
    finding = _finding(report, "config_valid")
    assert finding["status"] == "PASS"
    assert "defaults" in finding["detail"]


def test_yaml_config_is_loaded(git_repo: Path) -> None:
    (git_repo / ".ai-standard.yml").write_text(
        "project_name: demo-project\nrisk_level: high\n", encoding="utf-8"
    )
    report = preflight.run_preflight(git_repo)
    assert report["project_name"] == "demo-project"
    assert report["risk_level"] == "high"


def test_verify_and_test_tool_checks(git_repo: Path) -> None:
    _write_config(git_repo, {"test_command": "pytest", "verify_commands": ["pytest", "definitely-not-a-tool-xyz"]})
    report = preflight.run_preflight(git_repo)
    assert _finding(report, "test_tool")["status"] == "PASS"
    assert _finding(report, "verify_tool:definitely-not-a-tool-xyz")["status"] == "WARN"


def test_unknown_config_key_warns(git_repo: Path) -> None:
    _git(git_repo, "checkout", "-b", "feature/cfg")
    _write_config(git_repo, {"protected_branchs": ["main"]})  # 오타: protected_branches
    report = preflight.run_preflight(git_repo)
    finding = _finding(report, "config_valid")
    assert finding["status"] == "WARN"
    assert "protected_branchs" in finding["detail"]
    assert report["status"] == "WARN"


def test_missing_protected_file_fails(git_repo: Path) -> None:
    _write_config(git_repo, {"protected_files": ["SECURITY.md"]})
    report = preflight.run_preflight(git_repo)
    finding = _finding(report, "protected_file:SECURITY.md")
    assert finding["status"] == "FAIL"
    assert "존재하지 않음" in finding["detail"]
    assert report["status"] == "FAIL"


def test_utf8_bom_config_is_loaded(git_repo: Path) -> None:
    # Windows 편집기가 저장하는 UTF-8 BOM 설정도 읽을 수 있어야 한다
    (git_repo / ".ai-standard.yml").write_bytes(b"\xef\xbb\xbfproject_name: bom-project\n")
    report = preflight.run_preflight(git_repo)
    assert report["project_name"] == "bom-project"
    assert _finding(report, "config_valid")["status"] == "PASS"


def test_cli_text_and_json_output(git_repo: Path, capsys: pytest.CaptureFixture) -> None:
    _git(git_repo, "checkout", "-b", "feature/cli")
    rc = preflight.main(["--workspace", str(git_repo)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "preflight: PASS" in out
    assert "protected_branch" in out

    rc = preflight.main(["--workspace", str(git_repo), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data["status"] == "PASS"
    assert data["branch"] == "feature/cli"
