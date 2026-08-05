"""Phase 1 — 체크포인트 테스트.

체크포인트가 실제 파일을 보존하고 자동 commit 을 만들지 않는지 검증한다.
"""
from __future__ import annotations

import json
from pathlib import Path

import common
from scripts import checkpoint


def _load_manifest(cp_dir: Path) -> dict:
    return json.loads((cp_dir / "manifest.json").read_text(encoding="utf-8"))


def test_checkpoint_saves_patch_and_status(git_repo: Path):
    (git_repo / "README.md").write_text("# modified\n", encoding="utf-8")
    result = checkpoint.create_checkpoint(git_repo, name="cp1")
    cp_dir = Path(result["path"])
    assert cp_dir.name == "cp1"
    assert (cp_dir / "git_status.txt").exists()
    assert "README.md" in (cp_dir / "git_status.txt").read_text(encoding="utf-8")
    patch = (cp_dir / "changes.patch").read_text(encoding="utf-8")
    assert "README.md" in patch
    assert "-# initial" in patch


def test_checkpoint_copies_untracked_files(git_repo: Path):
    (git_repo / "new_file.txt").write_text("new content\n", encoding="utf-8")
    result = checkpoint.create_checkpoint(git_repo, name="cp_untracked")
    cp_dir = Path(result["path"])
    copied = cp_dir / "new_files" / "new_file.txt"
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == "new content\n"
    manifest = _load_manifest(cp_dir)
    assert "new_file.txt" in manifest["untracked_copied"]


def test_checkpoint_copies_state_docs(git_repo: Path):
    ai_dir = git_repo / ".ai"
    ai_dir.mkdir()
    (ai_dir / "CURRENT.md").write_text("# CURRENT test\n", encoding="utf-8")
    result = checkpoint.create_checkpoint(git_repo, name="cp_docs")
    cp_dir = Path(result["path"])
    assert (cp_dir / "state" / "CURRENT.md").read_text(encoding="utf-8") == "# CURRENT test\n"
    assert ".ai/CURRENT.md" in _load_manifest(cp_dir)["state_files"]


def test_checkpoint_does_not_auto_commit(git_repo: Path):
    head_before = common.git_head(git_repo)
    (git_repo / "README.md").write_text("# modified\n", encoding="utf-8")
    checkpoint.create_checkpoint(git_repo, name="cp_nocommit")
    assert common.git_head(git_repo) == head_before
    status = common.git_status_porcelain(git_repo)
    assert "README.md" in status  # 여전히 미커밋 상태


def test_checkpoint_manifest_metadata(git_repo: Path):
    (git_repo / "README.md").write_text("# modified\n", encoding="utf-8")
    result = checkpoint.create_checkpoint(git_repo, name="cp_meta")
    manifest = _load_manifest(Path(result["path"]))
    assert manifest["auto_commit"] is False
    assert manifest["branch"] == "main"
    assert manifest["head"] == common.git_head(git_repo)
    assert manifest["patch_hash"] == common.sha256(
        (Path(result["path"]) / "changes.patch").read_text(encoding="utf-8")
    )


def test_checkpoint_name_sanitized(git_repo: Path):
    result = checkpoint.create_checkpoint(git_repo, name="bad name/../x")
    cp_dir = Path(result["path"])
    assert cp_dir.is_relative_to(git_repo / ".ai" / "checkpoints")
    assert cp_dir.name == "bad_name_.._x"  # 경로 구분자는 제거되므로 단일 컴포넌트로 안전


def test_checkpoint_requires_git_repo(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    try:
        checkpoint.create_checkpoint(plain, name="x")
    except common.GitError:
        pass
    else:
        raise AssertionError("Git 저장소가 아닌 경로에서 예외가 발생해야 한다")
