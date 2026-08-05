"""test_release_verification.py — Phase 6: 릴리스 검증(롤백 게이트).

외부에서 관찰 가능한 결과(verify_release 보고서, 개별 check 의 PASS/FAIL/NOT_RUN)를 검증한다.
- 정상 흐름 전체 PASS
- artifact 변조 → artifact_hashes FAIL (검증 후 변경 차단, 핵심 게이트)
- manifest 변조 → manifest_hash FAIL
- verification.status == FAIL → verification_passed FAIL
- verification.status == NOT_RUN → verification_passed FAIL (NOT_RUN 을 PASS 로 인정하지 않음)
- verification.json 변조(result_hash 불일치) → verification_hash FAIL
- require_rollback + rollback_point 빈 값 → FAIL
- require_human_approval + approved_by 빈 값 → FAIL
- release_enabled=false → FAIL
- worktree dirty → worktree_clean FAIL
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import create_release_manifest as crm
from scripts import verify_release as vr
from scripts.common import git_head, sha256


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=str(repo), capture_output=True, text=True, errors="replace", check=True,
    )


def _write_config(repo: Path, **overrides) -> Path:
    data = {
        "project_name": "test-project",
        "release_enabled": True,
        "require_rollback": True,
        "require_human_approval": True,
    }
    data.update(overrides)
    path = repo / ".ai-standard.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _make_verification(*, commit: str, status: str = "PASS", run_id: str = "verif_test_0001") -> dict:
    checks = [{"name": "tests", "status": status if status != "NOT_RUN" else "NOT_RUN",
               "detail": "synthetic check"}]
    body = {
        "verification_run_id": run_id,
        "workspace": "irrelevant-for-test",
        "commit": commit,
        "worktree_status_hash": "",
        "config_source": "",
        "started_at": "2026-08-05T00:00:00+00:00",
        "ended_at": "2026-08-05T00:00:01+00:00",
        "status": status,
        "checks": checks,
        "summary": {
            "pass": 1 if status == "PASS" else 0,
            "fail": 1 if status == "FAIL" else 0,
            "not_run": 1 if status == "NOT_RUN" else 0,
        },
    }
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["result_hash"] = sha256(canonical)
    return body


def _find(report: dict, name: str) -> dict:
    for c in report["checks"]:
        if c["name"] == name:
            return c
    raise AssertionError(f"check 누락: {name} (실제: {[c['name'] for c in report['checks']]})")


def _setup_passing_release(
    git_repo: Path, tmp_path: Path,
    rollback_point: str = "prev-commit-abc", approved_by: str = "tester",
    **config_overrides,
):
    """artifact 커밋 + verification.json(PASS) + manifest 를 만들어 정상 흐름을 구성한다.

    verification.json/manifest 는 git_repo 밖(tmp_path 자매 경로)에 둬서
    작업트리를 깨끗하게 유지한다.
    """
    artifact = git_repo / "app.bin"
    artifact.write_bytes(b"release payload v1")
    _write_config(git_repo, **config_overrides)
    # artifact 와 설정 파일을 함께 커밋해 작업트리를 깨끗하게 유지한다
    # (검증/manifest 산출물은 git_repo 밖에 따로 둔다).
    _git(git_repo, "add", "app.bin", ".ai-standard.json")
    _git(git_repo, "commit", "-m", "add artifact")
    commit = git_head(git_repo)

    verification = _make_verification(commit=commit, status="PASS")
    verification_path = tmp_path / "verification.json"
    verification_path.write_text(json.dumps(verification, ensure_ascii=False), encoding="utf-8")

    manifest = crm.build_manifest(
        git_repo, version="1.0.0", artifact_args=["app.bin"],
        verification_path=str(verification_path),
        rollback_point=rollback_point,
        approved_by=approved_by,
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    return {
        "artifact": artifact,
        "commit": commit,
        "verification_path": verification_path,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "verification": verification,
    }


def test_normal_flow_passes(git_repo: Path, tmp_path: Path) -> None:
    ctx = _setup_passing_release(git_repo, tmp_path)

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "PASS", report["checks"]
    assert report["summary"]["fail"] == 0
    for name in (
        "worktree_clean", "source_commit_match", "verification_exists",
        "verification_passed", "verification_hash", "verification_run_match",
        "artifact_hashes", "total_hash", "manifest_hash",
        "rollback_point", "human_approval", "release_enabled",
    ):
        assert _find(report, name)["status"] == "PASS", f"{name}: {_find(report, name)}"


def test_artifact_tampering_after_verification_blocks_release(git_repo: Path, tmp_path: Path) -> None:
    ctx = _setup_passing_release(git_repo, tmp_path)

    # 검증 이후 artifact 파일 내용을 변경한다 (승인은 특정 해시에 대한 것이므로 무효화되어야 한다).
    ctx["artifact"].write_bytes(b"TAMPERED payload")

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "FAIL"
    assert _find(report, "artifact_hashes")["status"] == "FAIL"


def test_manifest_field_tampering_blocks_release(git_repo: Path, tmp_path: Path) -> None:
    ctx = _setup_passing_release(git_repo, tmp_path)

    tampered = dict(ctx["manifest"])
    tampered["version"] = "9.9.9-tampered"
    ctx["manifest_path"].write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "FAIL"
    assert _find(report, "manifest_hash")["status"] == "FAIL"


def test_verification_status_fail_blocks_release(git_repo: Path, tmp_path: Path) -> None:
    artifact = git_repo / "app.bin"
    artifact.write_bytes(b"payload")
    _write_config(git_repo)
    _git(git_repo, "add", "app.bin", ".ai-standard.json")
    _git(git_repo, "commit", "-m", "add artifact")
    commit = git_head(git_repo)

    verification = _make_verification(commit=commit, status="FAIL")
    verification_path = tmp_path / "verification.json"
    verification_path.write_text(json.dumps(verification, ensure_ascii=False), encoding="utf-8")

    manifest = crm.build_manifest(
        git_repo, version="1.0.0", artifact_args=["app.bin"],
        verification_path=str(verification_path), rollback_point="p", approved_by="t",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    report = vr.run_verify_release(
        git_repo, manifest_path=str(manifest_path), verification_path=str(verification_path),
    )

    assert report["status"] == "FAIL"
    assert _find(report, "verification_passed")["status"] == "FAIL"


def test_verification_status_not_run_is_not_treated_as_pass(git_repo: Path, tmp_path: Path) -> None:
    """checks 가 전부 NOT_RUN 이고 status == NOT_RUN 이면 verification_passed 는 PASS 로 통과되지 않는다."""
    artifact = git_repo / "app.bin"
    artifact.write_bytes(b"payload")
    _write_config(git_repo)
    _git(git_repo, "add", "app.bin", ".ai-standard.json")
    _git(git_repo, "commit", "-m", "add artifact")
    commit = git_head(git_repo)

    verification = _make_verification(commit=commit, status="NOT_RUN")
    verification_path = tmp_path / "verification.json"
    verification_path.write_text(json.dumps(verification, ensure_ascii=False), encoding="utf-8")

    manifest = crm.build_manifest(
        git_repo, version="1.0.0", artifact_args=["app.bin"],
        verification_path=str(verification_path), rollback_point="p", approved_by="t",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    report = vr.run_verify_release(
        git_repo, manifest_path=str(manifest_path), verification_path=str(verification_path),
    )

    assert report["status"] == "FAIL"
    check = _find(report, "verification_passed")
    assert check["status"] == "FAIL"
    assert "PASS" not in check["status"]  # sanity: 정확히 FAIL 문자열이지 PASS 가 아님
    assert check["status"] != "PASS"


def test_verification_json_tampering_detected_by_hash(git_repo: Path, tmp_path: Path) -> None:
    ctx = _setup_passing_release(git_repo, tmp_path)

    tampered = dict(ctx["verification"])
    tampered["commit"] = "0" * 40  # result_hash 는 그대로 두고 본문만 변조
    ctx["verification_path"].write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "FAIL"
    assert _find(report, "verification_hash")["status"] == "FAIL"


def test_require_rollback_with_empty_rollback_point_fails(git_repo: Path, tmp_path: Path) -> None:
    ctx = _setup_passing_release(git_repo, tmp_path, rollback_point="")

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "FAIL"
    assert _find(report, "rollback_point")["status"] == "FAIL"


def test_require_human_approval_with_empty_approved_by_fails(git_repo: Path, tmp_path: Path) -> None:
    ctx = _setup_passing_release(git_repo, tmp_path, approved_by="")

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "FAIL"
    assert _find(report, "human_approval")["status"] == "FAIL"


def test_release_disabled_fails(git_repo: Path, tmp_path: Path) -> None:
    ctx = _setup_passing_release(git_repo, tmp_path, release_enabled=False)

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "FAIL"
    assert _find(report, "release_enabled")["status"] == "FAIL"


def test_dirty_worktree_fails(git_repo: Path, tmp_path: Path) -> None:
    ctx = _setup_passing_release(git_repo, tmp_path)

    (git_repo / "uncommitted.txt").write_text("dirty", encoding="utf-8")

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "FAIL"
    assert _find(report, "worktree_clean")["status"] == "FAIL"


def test_require_rollback_false_with_empty_rollback_point_passes_with_warning(
    git_repo: Path, tmp_path: Path,
) -> None:
    ctx = _setup_passing_release(git_repo, tmp_path, require_rollback=False, rollback_point="")

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    check = _find(report, "rollback_point")
    assert check["status"] == "PASS"
    assert report["status"] == "PASS"


def test_cli_exit_code_matches_status(git_repo: Path, tmp_path: Path) -> None:
    import sys
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    script = PROJECT_ROOT / "scripts" / "verify_release.py"

    ctx = _setup_passing_release(git_repo, tmp_path)

    result = subprocess.run(
        [sys.executable, str(script), "--workspace", str(git_repo),
         "--manifest", str(ctx["manifest_path"]), "--verification", str(ctx["verification_path"]),
         "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
