"""test_secret_scan.py — Phase 3: 시크릿 탐지 검증.

외부에서 관찰 가능한 결과(report)를 검증한다.
실제 비밀값은 사용하지 않고 synthetic token 만 사용한다.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from scripts import check_secrets as cs

PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nMIIE...synthetic\n-----END PRIVATE KEY-----"
AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
GH_TOKEN = "ghp_abcdefghijklmnopqrstuvwxyzABCD"
OPENAI_KEY = "sk-test-abcdefghijklmnopqrstuvwxyz12"
AUTH_HEADER = "Authorization: Bearer abcdef1234567890abcdef"
JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
UNIQUE = "sk-zyxwvutsrqponmlkjihgfedcbazzzzz"  # 마스킹 검증용 고유 토큰


def _write(tmp: Path, name: str, content: str) -> Path:
    p = tmp / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _scan(tmp: Path, names: list[str], git_diff: bool = False,
          exceptions: list[str] | None = None, workspace: Path | None = None) -> dict:
    return cs.run_scan(workspace or tmp, names, git_diff, exceptions or [])


def _patterns(report: dict) -> set[str]:
    return {f["pattern"] for f in report["findings"]}


def test_detects_private_key(tmp_path: Path) -> None:
    _write(tmp_path, "key.pem", PRIVATE_KEY)
    report = _scan(tmp_path, ["key.pem"])
    assert report["status"] == "FAIL"
    assert "private_key" in _patterns(report)
    assert report["summary"]["fail"] == 1


def test_detects_high_severity_tokens(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", f"aws = '{AWS_KEY}'\ngh = '{GH_TOKEN}'\nsk = '{OPENAI_KEY}'\n")
    report = _scan(tmp_path, ["a.py"])
    assert report["status"] == "FAIL"
    assert {"aws_access_key", "github_token", "openai_key"} <= _patterns(report)
    for f in report["findings"]:
        assert f["severity"] == "HIGH"
        assert f["status"] == "HIGH"


def test_detects_medium_severity_as_warn(tmp_path: Path) -> None:
    _write(tmp_path, "a.txt", f"{AUTH_HEADER}\njwt={JWT}\n")
    report = _scan(tmp_path, ["a.txt"])
    assert report["status"] == "WARN"
    assert {"authorization", "jwt_token"} <= _patterns(report)
    for f in report["findings"]:
        assert f["status"] == "MEDIUM"
    assert report["summary"]["fail"] == 0
    assert report["summary"]["warn"] == 2


def test_does_not_detect_benign_content(tmp_path: Path) -> None:
    _write(tmp_path, "ok.py",
           "# 일반 코드는 탐지하지 않는다\n"
           "token = get_token()\n"
           "key = config.key\n"
           "sk = 'short'\n"
           "sha256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'\n"
           "url = 'https://example.com/sk-abc/asset'\n")
    report = _scan(tmp_path, ["ok.py"])
    assert report["status"] == "PASS"
    assert report["findings"] == []


def test_masking_never_outputs_raw_secret(tmp_path: Path, capsys) -> None:
    _write(tmp_path, "s.txt", f"key = '{UNIQUE}'\n")
    rc = cs.main(["--workspace", str(tmp_path), "--json"])
    out = capsys.readouterr().out
    assert rc == 1
    assert UNIQUE not in out  # 원문 미출력
    data = json.loads(out)
    assert data["status"] == "FAIL"
    for f in data["findings"]:
        assert "***" in f["masked"]
        assert f["masked"] != f  # 마스킹된 값은 원문과 다름


def test_truncated_begin_line_is_not_flagged(tmp_path: Path) -> None:
    # END 블록 없는 단일 줄 BEGIN 은 문서용 샘플로 간주해 탐지하지 않는다
    _write(tmp_path, "doc.md", "샘플: `-----BEGIN PRIVATE KEY-----` (설명용)\n")
    report = _scan(tmp_path, ["doc.md"])
    assert report["status"] == "PASS"
    assert report["findings"] == []


def test_scan_zip_archive_content(tmp_path: Path) -> None:
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("config/secret.cfg", f"api_key = '{AWS_KEY}'\n")
        zf.writestr("README.txt", "hello\n")
    report = _scan(tmp_path, ["bundle.zip"])
    assert report["status"] == "FAIL"
    paths = {f["path"] for f in report["findings"]}
    assert any("!config/secret.cfg" in p for p in paths)


def test_scan_git_diff_added_lines(git_repo: Path) -> None:
    (git_repo / "README.md").write_text("# init\n# added\n" f"OPENAI={OPENAI_KEY}\n", encoding="utf-8")
    report = _scan(git_repo, [], git_diff=True)
    assert report["status"] == "FAIL"
    assert "openai_key" in _patterns(report)
    # diff 의 추가된 줄에서도 탐지되어야 한다 (파일 스캔과 함께)
    assert any(f["path"].startswith("git-diff:") for f in report["findings"])


def test_allow_exception_marks_excepted(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", f"sk = '{OPENAI_KEY}'\n")
    report = _scan(tmp_path, ["a.py"], exceptions=["*:openai_key:테스트 픽스처"])
    assert report["status"] == "PASS"
    assert report["summary"]["excepted"] == 1
    assert report["findings"][0]["status"] == "EXCEPTED"


def test_binary_file_is_skipped(tmp_path: Path) -> None:
    p = tmp_path / "data.bin"
    p.write_bytes(b"\x00\x01\x02" + OPENAI_KEY.encode() + b"\x00\xff")
    report = _scan(tmp_path, ["data.bin"])
    assert report["status"] == "PASS"
    assert report["findings"] == []


def test_cli_text_output(tmp_path: Path, capsys) -> None:
    _write(tmp_path, "a.py", f"gh = '{GH_TOKEN}'\n")
    rc = cs.main(["--workspace", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "check_secrets: FAIL" in out
    assert "github_token" in out
    assert GH_TOKEN not in out
