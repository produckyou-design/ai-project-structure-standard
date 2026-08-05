"""create_release_manifest.py — Phase 6: 릴리스 manifest 생성.

용법:
  python scripts/create_release_manifest.py --version 1.0.0 --artifacts <파일/디렉터리...>
      [--workspace PATH] [--out PATH] [--verification PATH]
      [--rollback-point TEXT] [--approved-by NAME] [--build-run-id ID]

- 지정된 artifact(파일 또는 디렉터리)를 바이너리로 해시하여 release manifest 를 만든다.
- manifest 는 schemas/release_manifest.schema.json 을 따르는 JSON 으로 저장한다(기본: .ai/release_manifest.json).
- manifest_hash 는 verify_project.py 의 result_hash 와 같은 방식(manifest_hash 필드 제외 본문의
  정규 JSON(ensure_ascii=False, sort_keys=True, separators=(",", ":")) SHA-256)으로 계산한다.
- 존재하지 않는 artifact 경로가 있으면 오류로 종료한다(exit 1).
- 실제 배포, Git push, GitHub Release 생성은 하지 않는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    configure_utf8_io,
    git_head,
    is_git_repo,
    now_iso,
    resolve_workspace,
    sha256,
)

READ_CHUNK_BYTES = 65536


class ReleaseManifestError(RuntimeError):
    pass


def sha256_file_binary(path: Path) -> str:
    """파일 내용을 바이너리로 읽어 SHA-256 헥스 다이제스트를 계산한다.

    common.sha256_file 은 텍스트 기반(utf-8 디코드)이라 artifact(빌드 산출물, 바이너리
    포함)에는 부적합하므로 이 스크립트 안에서 바이너리 전용 해시 함수를 둔다.
    """
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(READ_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_label(workspace: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(workspace).as_posix()
    except ValueError:
        return resolved.as_posix()


def resolve_artifact_files(workspace: Path, given: list[str]) -> list[Path]:
    """artifact 인자(파일/디렉터리)를 실제 파일 목록으로 펼친다.

    존재하지 않는 경로는 ReleaseManifestError 로 즉시 실패시킨다(부분 성공 없음).
    디렉터리는 재귀적으로 펼치되 .git 디렉터리는 건너뛴다.
    """
    if not given:
        raise ReleaseManifestError("--artifacts 는 최소 1개 이상 지정해야 합니다")
    results: list[Path] = []
    for raw in given:
        candidate = Path(raw)
        candidate = candidate if candidate.is_absolute() else workspace / candidate
        if candidate.is_file():
            results.append(candidate)
        elif candidate.is_dir():
            found = [
                p for p in sorted(candidate.rglob("*"))
                if p.is_file() and not any(part == ".git" for part in p.relative_to(candidate).parts)
            ]
            if not found:
                raise ReleaseManifestError(f"artifact 디렉터리에 파일이 없습니다: {raw}")
            results.extend(found)
        else:
            raise ReleaseManifestError(f"artifact 경로가 존재하지 않습니다: {raw}")
    return results


def _read_verification_run_id(verification_path: str | None) -> str:
    if not verification_path:
        return ""
    path = Path(verification_path)
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(data.get("verification_run_id", "") or "")


def build_manifest(
    workspace: Path,
    *,
    version: str,
    artifact_args: list[str],
    verification_path: str | None = None,
    rollback_point: str = "",
    approved_by: str = "",
    build_run_id: str = "",
) -> dict:
    """release manifest 를 만들어 반환한다 (파일 저장은 하지 않음)."""
    files = resolve_artifact_files(workspace, artifact_args)

    artifacts: list[dict] = []
    for file_path in files:
        file_hash = sha256_file_binary(file_path)
        artifacts.append({
            "path": _relative_label(workspace, file_path),
            "sha256": file_hash,
            "size_bytes": file_path.stat().st_size,
        })
    # 경로 기준으로 정렬해 manifest 를 결정적으로 만든다.
    artifacts.sort(key=lambda a: a["path"])

    total_artifact_hash = sha256("".join(sorted(a["sha256"] for a in artifacts)))
    source_commit = git_head(workspace) if is_git_repo(workspace) else "NONE"
    release_id = f"rel_{now_iso().replace(':', '').replace('-', '').replace('+', '')}_{secrets.token_hex(3)}"

    manifest = {
        "release_id": release_id,
        "version": version,
        "source_commit": source_commit,
        "build_run_id": build_run_id,
        "artifacts": artifacts,
        "total_artifact_hash": total_artifact_hash,
        "created_at": now_iso(),
        "verification_run_id": _read_verification_run_id(verification_path),
        "rollback_point": rollback_point,
        "approved_by": approved_by,
    }
    canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    manifest["manifest_hash"] = sha256(canonical)
    return manifest


def verify_manifest_hash(manifest: dict) -> bool:
    """저장된 manifest 의 manifest_hash 가 본문과 일치하는지 검증한다."""
    body = {k: v for k, v in manifest.items() if k != "manifest_hash"}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(canonical) == manifest.get("manifest_hash", "")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="create_release_manifest", description="릴리스 manifest 생성")
    parser.add_argument("--version", required=True, help="릴리스 버전")
    parser.add_argument("--artifacts", nargs="+", required=True, help="artifact 파일/디렉터리 (반복 가능)")
    parser.add_argument("--workspace", default=None, help="작업 저장소 경로 (기본: 현재 디렉터리)")
    parser.add_argument("--out", default=None, help="저장 경로 (기본: .ai/release_manifest.json)")
    parser.add_argument("--verification", default=None, help="verification.json 경로 (verification_run_id 연동)")
    parser.add_argument("--rollback-point", default="", help="롤백 지점(커밋/태그/배포 식별자)")
    parser.add_argument("--approved-by", default="", help="승인자 이름")
    parser.add_argument("--build-run-id", default="", help="빌드 실행 식별자")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_io()
    args = build_parser().parse_args(argv)
    ws = resolve_workspace(args.workspace)
    try:
        manifest = build_manifest(
            ws,
            version=args.version,
            artifact_args=args.artifacts,
            verification_path=args.verification,
            rollback_point=args.rollback_point,
            approved_by=args.approved_by,
            build_run_id=args.build_run_id,
        )
    except ReleaseManifestError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else ws / ".ai" / "release_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"release_manifest: {manifest['release_id']}  (version: {manifest['version']}, "
              f"artifacts: {len(manifest['artifacts'])}, commit: {manifest['source_commit'][:12]})")
        print(f"manifest_hash: {manifest['manifest_hash']}")
        print(f"result: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
