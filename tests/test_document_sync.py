"""test_document_sync.py — Phase 5: check_document_sync 의 기계 판정 정합성 검사 검증.

check_document_sync 는 자연어 문서의 내용을 판정하지 않고, 기계적으로 확인 가능한
정합성만 검사한다: README 참조 경로 존재, 필수 문서 존재, 설정 명령 비어있지 않음,
CURRENT/STATUS 모순, STATUS PASS 근거, 오류 코드 카탈로그 등록.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import check_document_sync as cds

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_config(ws: Path, data: dict) -> None:
    (ws / ".ai-standard.json").write_text(json.dumps(data), encoding="utf-8")


def _finding(report: dict, check: str) -> dict:
    for f in report["findings"]:
        if f["check"] == check:
            return f
    raise AssertionError(f"finding 누락: {check} (보고된 checks: {[x['check'] for x in report['findings']]})")


# ---------- readme_references ----------


def test_readme_referencing_existing_paths_passes(tmp_path: Path) -> None:
    _write(tmp_path / "scripts" / "real.py", "# real\n")
    _write(tmp_path / "README.md", "관련 스크립트: `scripts/real.py`\n")
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "readme_references")
    assert finding["status"] == "PASS"


def test_readme_referencing_missing_path_fails(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "관련 스크립트: `scripts/foo.py`\n")
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "readme_references")
    assert finding["status"] == "FAIL"
    assert "scripts/foo.py" in finding["detail"]
    assert report["status"] == "FAIL"


def test_no_readme_is_not_run(tmp_path: Path) -> None:
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "readme_references")
    assert finding["status"] == "NOT_RUN"


# ---------- config_commands ----------


def test_empty_verify_command_fails_config_commands(tmp_path: Path) -> None:
    _write_config(tmp_path, {"verify_commands": ["pytest", ""]})
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "config_commands")
    assert finding["status"] == "FAIL"
    assert report["status"] == "FAIL"


def test_nonempty_commands_pass_config_commands(tmp_path: Path) -> None:
    _write_config(tmp_path, {"verify_commands": ["pytest"], "test_command": "pytest"})
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "config_commands")
    assert finding["status"] == "PASS"


# ---------- status_evidence ----------


def test_status_pass_row_without_evidence_fails(tmp_path: Path) -> None:
    _write(
        tmp_path / ".ai" / "STATUS.md",
        "# STATUS\n\n| 항목 | 상태 | 근거 |\n|---|---|---|\n| 빌드 | PASS |  |\n",
    )
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "status_evidence")
    assert finding["status"] == "FAIL"
    assert "빌드" in finding["detail"]


def test_status_pass_row_with_evidence_passes(tmp_path: Path) -> None:
    _write(
        tmp_path / ".ai" / "STATUS.md",
        "# STATUS\n\n| 항목 | 상태 | 근거 |\n|---|---|---|\n| 빌드 | PASS | CI 로그 확인 |\n",
    )
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "status_evidence")
    assert finding["status"] == "PASS"


def test_no_status_file_status_evidence_not_run(tmp_path: Path) -> None:
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "status_evidence")
    assert finding["status"] == "NOT_RUN"


# ---------- current_status ----------


def test_status_fail_with_no_blocker_is_contradiction(tmp_path: Path) -> None:
    _write(
        tmp_path / ".ai" / "STATUS.md",
        "# STATUS\n\n| 항목 | 상태 | 근거 |\n|---|---|---|\n| 테스트 | FAIL | 실패함 |\n",
    )
    _write(tmp_path / ".ai" / "CURRENT.md", "# CURRENT\n\n## 블로커\n\n없음.\n")
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "current_status")
    assert finding["status"] == "FAIL"
    assert report["status"] == "FAIL"


def test_status_fail_with_blocker_recorded_is_consistent(tmp_path: Path) -> None:
    _write(
        tmp_path / ".ai" / "STATUS.md",
        "# STATUS\n\n| 항목 | 상태 | 근거 |\n|---|---|---|\n| 테스트 | FAIL | 실패함 |\n",
    )
    _write(tmp_path / ".ai" / "CURRENT.md", "# CURRENT\n\n## 블로커\n\n테스트 3건 실패, 원인 조사 중.\n")
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "current_status")
    assert finding["status"] == "PASS"


# ---------- error_codes ----------


def test_no_error_catalog_is_not_run(tmp_path: Path) -> None:
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "error_codes")
    assert finding["status"] == "NOT_RUN"


def test_unregistered_error_code_in_source_fails(tmp_path: Path) -> None:
    _write(tmp_path / "ERROR_CATALOG.md", "# ERROR_CATALOG\n\n(등록된 코드 없음)\n")
    _write(tmp_path / "app.py", 'raise ValueError("APP-STORAGE-WRITE-500")\n')
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "error_codes")
    assert finding["status"] == "FAIL"
    assert "APP-STORAGE-WRITE-500" in finding["detail"]
    assert report["status"] == "FAIL"


def test_registered_error_code_in_source_passes(tmp_path: Path) -> None:
    _write(tmp_path / "ERROR_CATALOG.md", "# ERROR_CATALOG\n\n| APP-STORAGE-WRITE-500 | ... |\n")
    _write(tmp_path / "app.py", 'raise ValueError("APP-STORAGE-WRITE-500")\n')
    report = cds.run_document_sync(tmp_path)
    finding = _finding(report, "error_codes")
    assert finding["status"] == "PASS"


# ---------- 저장소 자체 ----------


def test_self_check_via_subprocess_is_not_fail() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/check_document_sync.py"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
