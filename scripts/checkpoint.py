"""checkpoint.py — Git 체크포인트 생성 (Phase 1).

체크포인트는 .ai/checkpoints/<name>/ 아래에 다음을 저장한다.
- manifest.json   : 메타데이터 + 해시
- git_status.txt  : git status --porcelain
- changes.patch   : git diff (워킹트리 변경)
- new_files/      : 추적되지 않은 신규 파일 사본
- state/          : .ai/CURRENT.md, .ai/STATUS.md 등 현재 상태 문서
- docs/           : docs/**/*.md 사본

자동 commit 을 만들지 않는다.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    GitError,
    changed_files,
    configure_utf8_io,
    git_branch,
    git_diff,
    git_head,
    git_status_hash,
    git_status_porcelain,
    is_git_repo,
    now_iso,
    repo_root,
    resolve_workspace,
    sha256,
    untracked_files,
)

CHECKPOINT_SUBDIR = ".ai/checkpoints"
_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_name(name: str) -> str:
    cleaned = _NAME_RE.sub("_", name.strip()) or "checkpoint"
    if cleaned in (".", ".."):
        raise ValueError(f"잘못된 체크포인트 이름: {name!r}")
    return cleaned


def _copy_subdir(root: Path, subdir: str, dest: Path, patterns: list[str]) -> list[str]:
    """root/subdir 아래에서 patterns(glob)에 매칭되는 파일을 dest 에 상대 경로로 복사한다.

    복사 대상 경로는 subdir 을 기준으로 한 상대 경로로 유지된다.
    """
    base = root / subdir
    copied: list[str] = []
    for pattern in patterns:
        for src in sorted(base.glob(pattern)):
            if not src.is_file():
                continue
            rel = src.relative_to(base)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            copied.append(f"{subdir}/{rel}")
    return copied


def create_checkpoint(workspace: Path, name: str | None = None) -> dict:
    """체크포인트를 생성하고 생성 경로와 manifest 를 반환한다."""
    if not is_git_repo(workspace):
        raise GitError(f"Git 저장소가 아닙니다: {workspace}")
    root = repo_root(workspace)
    cp_name = safe_name(name) if name else now_iso().replace(":", "-").replace("+", "Z")
    dest = root / CHECKPOINT_SUBDIR / cp_name
    dest.mkdir(parents=True, exist_ok=True)

    # 1) Git 상태
    status_text = git_status_porcelain(workspace)
    (dest / "git_status.txt").write_text(status_text or "(clean)", encoding="utf-8")

    # 2) patch
    patch = git_diff(workspace)
    (dest / "changes.patch").write_text(patch, encoding="utf-8")

    # 3) 신규(추적되지 않은) 파일 사본 — 루트 밖 경로는 건너뛴다
    untracked = untracked_files(workspace)
    new_files_dest = dest / "new_files"
    copied_new: list[str] = []
    checkpoints_root = (root / CHECKPOINT_SUBDIR).resolve()
    for rel in untracked:
        src = (root / rel).resolve()
        try:
            src.relative_to(root)
        except ValueError:
            continue
        if src.is_dir():
            # git porcelain 은 추적되지 않은 디렉터리를 'newpkg/' 처럼 한 줄로 축약해
            # 보고한다. 디렉터리라고 건너뛰면 신규 파일이 통째로 보존되지 않으므로
            # (체크포인트의 목적이 깨진다) 내부 파일까지 펼쳐서 복사한다.
            # 체크포인트 저장소 자신은 제외한다 (자기 복사 재귀 방지).
            for inner in sorted(p for p in src.rglob("*") if p.is_file()):
                if inner.resolve().is_relative_to(checkpoints_root):
                    continue
                inner_rel = inner.relative_to(root).as_posix()
                target = new_files_dest / inner_rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(inner, target)
                copied_new.append(inner_rel)
            continue
        if not src.is_file():
            continue
        target = new_files_dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied_new.append(rel)
    (dest / "untracked_files.txt").write_text("\n".join(untracked) or "(none)", encoding="utf-8")

    # 4) 현재 상태 문서
    state_files = _copy_subdir(root, ".ai", dest / "state", ["CURRENT.md", "STATUS.md"])
    doc_files = _copy_subdir(root, "docs", dest / "docs", ["**/*.md"])

    # 5) manifest
    manifest = {
        "name": cp_name,
        "created_at": now_iso(),
        "branch": git_branch(workspace),
        "head": git_head(workspace),
        "git_status_hash": git_status_hash(workspace),
        "patch_hash": sha256(patch),
        "patch_bytes": len(patch.encode("utf-8")),
        "auto_commit": False,
        "changed_files": changed_files(workspace),
        "untracked_copied": copied_new,
        "state_files": state_files,
        "doc_files": doc_files,
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(dest), "manifest": manifest}


def main(argv: list[str] | None = None) -> int:
    configure_utf8_io()
    parser = argparse.ArgumentParser(prog="checkpoint", description="Git 체크포인트 생성 (자동 commit 없음)")
    parser.add_argument("--name", default=None, help="체크포인트 이름 (기본: 타임스탬프)")
    parser.add_argument("--workspace", default=None, help="작업 저장소 경로 (기본: 현재 디렉터리)")
    args = parser.parse_args(argv)
    try:
        result = create_checkpoint(resolve_workspace(args.workspace), name=args.name)
    except (GitError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result["manifest"], ensure_ascii=False, indent=2))
    print(f"checkpoint: {result['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
