"""test_phase8_audit_findings.py — Phase 8 독립 감사에서 발견된 결함의 회귀 방지.

각 테스트는 감사 중 실제로 재현한 우회/누락을 그대로 재현하고, 수정 후
차단되는지를 외부에서 관찰 가능한 결과(보고서 status, exit code, 파일 존재)로
검증한다.

발견 항목:
  1. verify_release: release manifest 가 없으면 manifest 의존 검사가 전부 NOT_RUN 이
     되고 나머지가 PASS 라서 전체 판정이 PASS(exit 0) → 릴리스 게이트 전체 우회.
  2. common.append_ledger: 마지막 항목의 자기 해시만 검사해서, 중간 항목을 고치고
     그 항목의 entry_hash 만 다시 계산하면 연결이 끊어진 채로 append 가 성공.
  3. common.git_branch: 커밋이 없는(unborn) 브랜치에서 'N/A' 를 반환해
     preflight 의 protected branch 검사가 조용히 통과.
  4. check_secrets / check_forbidden_patterns: 존재하지 않는 --path 를 조용히
     건너뛰어 "0건 탐지 → PASS" 가 됨 (미실행이 통과로 둔갑).
  5. checkpoint: 추적되지 않은 '디렉터리'(porcelain 이 'dir/' 로 축약 보고)의
     내부 파일이 통째로 보존되지 않음.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import common
from scripts import check_forbidden_patterns as cfp
from scripts import check_secrets as cs
from scripts import checkpoint
from scripts import create_release_manifest as crm
from scripts import preflight
from scripts import sign_ai_session as sign
from scripts import verify_release as vr
from scripts.common import git_head, sha256

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=str(repo), capture_output=True, text=True, errors="replace", check=True,
    )


def _find(report: dict, name: str) -> dict:
    for c in report["checks"]:
        if c["name"] == name:
            return c
    raise AssertionError(f"check 누락: {name} (실제: {[c['name'] for c in report['checks']]})")


def _make_verification(*, commit: str, run_id: str = "verif_audit_0001") -> dict:
    body = {
        "verification_run_id": run_id,
        "workspace": "irrelevant-for-test",
        "commit": commit,
        "worktree_status_hash": "",
        "config_source": "",
        "started_at": "2026-08-05T00:00:00+00:00",
        "ended_at": "2026-08-05T00:00:01+00:00",
        "status": "PASS",
        "checks": [{"name": "tests", "status": "PASS", "detail": "synthetic"}],
        "summary": {"pass": 1, "fail": 0, "not_run": 0},
    }
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["result_hash"] = sha256(canonical)
    return body


def _release_setup(git_repo: Path, tmp_path: Path) -> dict:
    """정상 릴리스 후보 한 벌을 만든다 (manifest/verification 은 저장소 밖)."""
    artifact = git_repo / "app.bin"
    artifact.write_bytes(b"audit payload")
    (git_repo / ".ai-standard.json").write_text(json.dumps({
        "project_name": "audit", "release_enabled": True,
        "require_rollback": True, "require_human_approval": True,
    }), encoding="utf-8")
    _git(git_repo, "add", "app.bin", ".ai-standard.json")
    _git(git_repo, "commit", "-m", "artifact")
    commit = git_head(git_repo)

    verification_path = tmp_path / "verification.json"
    verification_path.write_text(
        json.dumps(_make_verification(commit=commit), ensure_ascii=False), encoding="utf-8")

    manifest = crm.build_manifest(
        git_repo, version="1.0.0", artifact_args=["app.bin"],
        verification_path=str(verification_path),
        rollback_point="prev-commit", approved_by="auditor",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return {"manifest_path": manifest_path, "verification_path": verification_path,
            "manifest": manifest, "commit": commit}


# ---------- 1. manifest 부재로 게이트 전체 우회 ----------


def test_missing_manifest_blocks_release_instead_of_passing(git_repo: Path, tmp_path: Path) -> None:
    """manifest 파일을 지우면 전체 판정이 PASS 가 아니라 FAIL 이어야 한다.

    회귀 전 동작: manifest 의존 검사 7건이 NOT_RUN 이 되고 나머지가 PASS 라서
    전체 status 가 PASS, exit 0 → 검증도 artifact 도 없이 릴리스가 통과됐다.
    """
    ctx = _release_setup(git_repo, tmp_path)
    ctx["manifest_path"].unlink()

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "FAIL", report["checks"]
    assert _find(report, "manifest_exists")["status"] == "FAIL"


def test_missing_manifest_cli_exits_1(git_repo: Path, tmp_path: Path) -> None:
    ctx = _release_setup(git_repo, tmp_path)
    ctx["manifest_path"].unlink()

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_release.py"),
         "--workspace", str(git_repo), "--manifest", str(ctx["manifest_path"]),
         "--verification", str(ctx["verification_path"]), "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "FAIL"


def test_manifest_missing_required_field_blocks_release(git_repo: Path, tmp_path: Path) -> None:
    """필수 필드가 빠진 manifest 도 릴리스 후보로 인정하지 않는다."""
    ctx = _release_setup(git_repo, tmp_path)
    broken = {k: v for k, v in ctx["manifest"].items() if k != "artifacts"}
    ctx["manifest_path"].write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "FAIL"
    check = _find(report, "manifest_exists")
    assert check["status"] == "FAIL"
    assert "artifacts" in check["detail"]


def test_normal_release_still_passes_with_manifest_exists(git_repo: Path, tmp_path: Path) -> None:
    """수정이 정상 흐름을 깨지 않는다 (manifest_exists 포함 전부 PASS)."""
    ctx = _release_setup(git_repo, tmp_path)

    report = vr.run_verify_release(
        git_repo, manifest_path=str(ctx["manifest_path"]),
        verification_path=str(ctx["verification_path"]),
    )

    assert report["status"] == "PASS", report["checks"]
    assert _find(report, "manifest_exists")["status"] == "PASS"


# ---------- 2. ledger 해시 체인 전체 검증 ----------


def test_tampered_middle_entry_with_recomputed_hash_is_rejected(git_repo: Path) -> None:
    """중간 항목을 고치고 그 항목의 entry_hash 만 다시 계산해도 append 가 거부된다.

    회귀 전 동작: append_ledger 가 마지막 항목의 자기 해시만 봤기 때문에,
    중간 항목을 변조하고 재해시하면 연결(previous_entry_hash)이 끊어진 채로도
    append 가 성공해서 해시 체인이 사실상 장식이 됐다.
    """
    first = sign.run_start(git_repo, task="첫 항목")
    sign.run_start(git_repo, task="둘째 항목")
    ledger_file = git_repo / ".ai" / "ledger.jsonl"
    entries = [json.loads(l) for l in ledger_file.read_text(encoding="utf-8").splitlines() if l.strip()]

    entries[0]["task"] = "몰래 바뀐 작업"
    entries[0]["entry_hash"] = common._entry_digest(entries[0])  # 자기 무결성만 위장
    ledger_file.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in entries) + "\n",
        encoding="utf-8")

    with pytest.raises(common.GitError, match="integrity violation"):
        sign.run_start(git_repo, task="변조 후 append 시도")

    # 거부됐으므로 항목 수가 늘지 않아야 한다
    after = [l for l in ledger_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(after) == 2
    assert first["run_id"]  # sanity


def test_verify_ledger_chain_detects_broken_link_and_accepts_intact_chain(git_repo: Path) -> None:
    sign.run_start(git_repo, task="A")
    sign.run_start(git_repo, task="B")
    sign.run_start(git_repo, task="C")
    entries = common.read_ledger(git_repo)

    ok, reason = common.verify_ledger_chain(entries)
    assert ok is True and reason == ""

    broken = [dict(e) for e in entries]
    broken[1]["previous_entry_hash"] = "0" * 64
    broken[1]["entry_hash"] = common._entry_digest(broken[1])
    ok, reason = common.verify_ledger_chain(broken)
    assert ok is False
    assert "previous_entry_hash" in reason


# ---------- 3. unborn 브랜치의 protected branch 검사 ----------


def test_protected_branch_detected_on_repo_without_commits(tmp_path: Path) -> None:
    """커밋이 하나도 없어도 실제 브랜치 이름으로 protected branch 를 판정한다.

    회귀 전 동작: rev-parse 가 실패해 브랜치가 'N/A' 로 기록되고,
    'N/A 는 보호 대상이 아님' PASS 로 게이트가 무력화됐다.
    """
    repo = tmp_path / "unborn"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "master"], cwd=str(repo),
                   capture_output=True, text=True, check=True)

    assert common.git_branch(repo) == "master"

    report = preflight.run_preflight(repo)
    finding = next(f for f in report["findings"] if f["check"] == "protected_branch")
    assert finding["status"] == "FAIL"
    assert report["status"] == "FAIL"


def test_git_branch_still_reports_named_branch_with_commits(git_repo: Path) -> None:
    """수정이 기존 동작(커밋 있는 저장소)을 바꾸지 않는다."""
    assert common.git_branch(git_repo) == "main"


def test_git_branch_na_outside_git_repo(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert common.git_branch(plain) == "N/A"


# ---------- 4. 존재하지 않는 --path 를 PASS 로 두지 않는다 ----------


def test_check_secrets_missing_path_fails(tmp_path: Path) -> None:
    report = cs.run_scan(tmp_path, ["no_such_file.py"], False, [])
    assert report["status"] == "FAIL"
    assert any(f["pattern"] == "missing_scan_path" for f in report["findings"])


def test_check_secrets_missing_path_cli_exits_1(tmp_path: Path, capsys) -> None:
    rc = cs.main(["--workspace", str(tmp_path), "--path", "no_such_file.py", "--json"])
    out = capsys.readouterr().out
    assert rc == 1
    assert json.loads(out)["status"] == "FAIL"


def test_check_forbidden_patterns_missing_path_fails(tmp_path: Path) -> None:
    report = cfp.run_scan(tmp_path, ["nope/missing_dir"], None)
    assert report["status"] == "FAIL"
    assert any(f["pattern"] == "missing_scan_path" for f in report["findings"])


def test_existing_path_still_scans_normally(tmp_path: Path) -> None:
    """수정이 정상 경로 스캔을 깨지 않는다."""
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
    assert cs.run_scan(tmp_path, ["ok.py"], False, [])["status"] == "PASS"
    assert cfp.run_scan(tmp_path, ["ok.py"], None)["status"] == "PASS"


# ---------- 5. 추적되지 않은 디렉터리 보존 ----------


def test_checkpoint_preserves_files_inside_untracked_directory(git_repo: Path) -> None:
    """porcelain 이 'pkg/' 로 축약 보고하는 신규 디렉터리도 내부 파일까지 보존한다.

    회귀 전 동작: 디렉터리는 is_file() 이 아니라 통째로 건너뛰어,
    새로 만든 모듈 디렉터리가 체크포인트에 하나도 남지 않았다.
    """
    pkg = git_repo / "newpkg"
    (pkg / "sub").mkdir(parents=True)
    (pkg / "mod.py").write_text("value = 1\n", encoding="utf-8")
    (pkg / "sub" / "deep.txt").write_text("deep\n", encoding="utf-8")

    result = checkpoint.create_checkpoint(git_repo, name="cp_untracked_dir")
    cp_dir = Path(result["path"])

    assert (cp_dir / "new_files" / "newpkg" / "mod.py").read_text(encoding="utf-8") == "value = 1\n"
    assert (cp_dir / "new_files" / "newpkg" / "sub" / "deep.txt").read_text(encoding="utf-8") == "deep\n"
    copied = result["manifest"]["untracked_copied"]
    assert "newpkg/mod.py" in copied
    assert "newpkg/sub/deep.txt" in copied


def test_checkpoint_does_not_recurse_into_its_own_storage(git_repo: Path) -> None:
    """.ai/ 전체가 추적되지 않은 상태여도 체크포인트가 자기 저장소를 재귀 복사하지 않는다."""
    ai_dir = git_repo / ".ai"
    ai_dir.mkdir()
    (ai_dir / "CURRENT.md").write_text("# CURRENT\n", encoding="utf-8")

    checkpoint.create_checkpoint(git_repo, name="cp_first")
    result = checkpoint.create_checkpoint(git_repo, name="cp_second")
    cp_dir = Path(result["path"])

    nested = list((cp_dir / "new_files").rglob("checkpoints"))
    assert nested == [], f"체크포인트 저장소가 자기 자신 안으로 복사됨: {nested}"
