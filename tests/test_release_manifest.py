"""test_release_manifest.py — Phase 6: 릴리스 manifest 생성.

외부에서 관찰 가능한 결과(release_manifest.json, manifest_hash, exit code)를 검증한다.
- 스키마(schemas/release_manifest.schema.json) 유효성
- 파일 해시·크기 실제 일치 (텍스트/바이너리)
- manifest_hash 재계산 일치
- 존재하지 않는 artifact 는 실패
- verification.json 지정 시 verification_run_id 연동
- 디렉터리 artifact 확장
- CLI 종료 코드와 출력 파일
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from scripts import create_release_manifest as crm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "release_manifest.schema.json"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "create_release_manifest.py"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_manifest_valid_against_schema(git_repo: Path) -> None:
    artifact = git_repo / "app.exe"
    artifact.write_bytes(b"binary payload v1")

    manifest = crm.build_manifest(git_repo, version="1.0.0", artifact_args=["app.exe"])

    errors = list(Draft7Validator(_schema()).iter_errors(manifest))
    assert errors == [], f"스키마 위반: {[e.message for e in errors]}"


def test_schema_itself_is_valid_draft7() -> None:
    Draft7Validator.check_schema(_schema())


def test_artifact_hash_and_size_match(git_repo: Path) -> None:
    content = b"hello release artifact\x00binary-ish"
    artifact = git_repo / "dist" / "payload.bin"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(content)

    manifest = crm.build_manifest(git_repo, version="2.0.0", artifact_args=["dist/payload.bin"])

    assert len(manifest["artifacts"]) == 1
    entry = manifest["artifacts"][0]
    assert entry["path"] == "dist/payload.bin"
    assert entry["sha256"] == _sha256_bytes(content)
    assert entry["size_bytes"] == len(content)

    expected_total = _sha256_bytes(entry["sha256"].encode("utf-8"))
    assert manifest["total_artifact_hash"] == expected_total


def test_manifest_hash_recomputes(git_repo: Path) -> None:
    artifact = git_repo / "app.bin"
    artifact.write_bytes(b"payload")

    manifest = crm.build_manifest(git_repo, version="1.0.0", artifact_args=["app.bin"])

    assert crm.verify_manifest_hash(manifest) is True

    tampered = dict(manifest, version="9.9.9")
    assert crm.verify_manifest_hash(tampered) is False


def test_missing_artifact_raises(git_repo: Path) -> None:
    with pytest.raises(crm.ReleaseManifestError):
        crm.build_manifest(git_repo, version="1.0.0", artifact_args=["does_not_exist.bin"])


def test_missing_artifact_cli_exits_1(git_repo: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--version", "1.0.0",
         "--artifacts", "does_not_exist.bin", "--workspace", str(git_repo)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 1
    assert not (git_repo / ".ai" / "release_manifest.json").exists()


def test_verification_run_id_linked(git_repo: Path, tmp_path: Path) -> None:
    artifact = git_repo / "app.bin"
    artifact.write_bytes(b"payload")

    verification_path = tmp_path / "verification.json"
    verification_path.write_text(json.dumps({
        "verification_run_id": "verif_20260805T000000Z_abc123",
        "status": "PASS",
    }), encoding="utf-8")

    manifest = crm.build_manifest(
        git_repo, version="1.0.0", artifact_args=["app.bin"],
        verification_path=str(verification_path),
    )
    assert manifest["verification_run_id"] == "verif_20260805T000000Z_abc123"


def test_verification_run_id_empty_when_not_specified(git_repo: Path) -> None:
    artifact = git_repo / "app.bin"
    artifact.write_bytes(b"payload")

    manifest = crm.build_manifest(git_repo, version="1.0.0", artifact_args=["app.bin"])
    assert manifest["verification_run_id"] == ""


def test_binary_file_hash_matches_direct_hashlib(git_repo: Path) -> None:
    # NUL 바이트와 비 UTF-8 바이트를 포함한 순수 바이너리 콘텐츠.
    content = bytes(range(256)) * 4
    artifact = git_repo / "raw.bin"
    artifact.write_bytes(content)

    computed = crm.sha256_file_binary(artifact)
    assert computed == hashlib.sha256(content).hexdigest()

    manifest = crm.build_manifest(git_repo, version="1.0.0", artifact_args=["raw.bin"])
    assert manifest["artifacts"][0]["sha256"] == computed


def test_directory_artifact_expands_to_files(git_repo: Path) -> None:
    dist = git_repo / "dist"
    dist.mkdir()
    (dist / "a.txt").write_text("a", encoding="utf-8")
    (dist / "b.txt").write_text("b", encoding="utf-8")

    manifest = crm.build_manifest(git_repo, version="1.0.0", artifact_args=["dist"])
    paths = sorted(a["path"] for a in manifest["artifacts"])
    assert paths == ["dist/a.txt", "dist/b.txt"]


def test_cli_creates_output_file_and_exit_0(git_repo: Path) -> None:
    artifact = git_repo / "app.bin"
    artifact.write_bytes(b"payload")
    out_path = git_repo / "custom_manifest.json"

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--version", "1.0.0",
         "--artifacts", "app.bin", "--workspace", str(git_repo),
         "--out", str(out_path), "--rollback-point", "commit-abc", "--approved-by", "tester"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stderr
    assert out_path.is_file()
    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved["version"] == "1.0.0"
    assert saved["rollback_point"] == "commit-abc"
    assert saved["approved_by"] == "tester"
    assert crm.verify_manifest_hash(saved) is True


def test_source_commit_is_git_head(git_repo: Path) -> None:
    from scripts.common import git_head

    artifact = git_repo / "app.bin"
    artifact.write_bytes(b"payload")

    manifest = crm.build_manifest(git_repo, version="1.0.0", artifact_args=["app.bin"])
    assert manifest["source_commit"] == git_head(git_repo)
