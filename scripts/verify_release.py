"""verify_release.py — Phase 6: 릴리스 후보 검증(롤백 게이트).

용법:
  python scripts/verify_release.py [--manifest PATH] [--verification PATH]
      [--workspace PATH] [--config PATH] [--json]

검증된 산출물만 릴리스 후보로 인정하고, 검증 후 변조되었거나 롤백 경로가 없으면 차단한다.

검사 항목 (하나라도 FAIL 이면 전체 FAIL, exit 1):
  1. worktree_clean          — 작업트리가 깨끗한가
  2. manifest_exists         — release manifest 존재 + 필수 필드 (없으면 릴리스 후보 자체가 없음)
  3. source_commit_match     — manifest.source_commit == 현재 HEAD
  4. verification_exists     — verification.json 존재 + 필수 필드
  5. verification_passed     — verification.status == PASS (FAIL/NOT_RUN 은 실패)
  6. verification_hash       — verification.json 의 result_hash 재계산 일치 (변조 감지)
  7. verification_run_match  — manifest.verification_run_id == verification.verification_run_id
  8. artifact_hashes         — manifest 의 각 artifact 가 현재도 존재하고 해시가 일치 (핵심 게이트)
  9. total_hash              — 전체 artifact hash 재계산 일치
  10. manifest_hash          — manifest 자체 해시 재계산 일치 (manifest 변조 차단)
  11. rollback_point         — require_rollback=true 인데 rollback_point 가 비면 FAIL
  12. human_approval         — require_human_approval=true 인데 approved_by 가 비면 FAIL
  13. release_enabled        — release_enabled=false 면 FAIL

실제 배포, Git push, GitHub Release 생성은 절대 하지 않는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    configure_utf8_io,
    git_head,
    git_status_porcelain,
    is_git_repo,
    resolve_workspace,
    sha256,
)
from preflight import load_config  # noqa: E402  (설정 로드의 단일 소유자 재사용)
from verify_project import verify_result_hash  # noqa: E402  (result_hash 계산 방식 재사용)

VERIFICATION_REQUIRED_FIELDS = (
    "verification_run_id", "workspace", "commit", "started_at", "ended_at",
    "status", "checks", "summary", "result_hash",
)

# schemas/release_manifest.schema.json 의 required 와 일치시킨다.
MANIFEST_REQUIRED_FIELDS = (
    "release_id", "version", "source_commit", "artifacts",
    "total_artifact_hash", "manifest_hash", "created_at",
)


def _check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def _load_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, f"file does not exist: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"read/parse failed: {exc}"


def _manifest_body_hash(manifest: dict) -> str:
    body = {k: v for k, v in manifest.items() if k != "manifest_hash"}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(canonical)


def run_verify_release(
    workspace: Path,
    *,
    manifest_path: str | None = None,
    verification_path: str | None = None,
    config_path: str | None = None,
) -> dict:
    """릴리스 게이트 검사를 수행하고 보고서를 반환한다 (파일을 쓰지 않는다)."""
    ws = resolve_workspace(workspace)
    config, config_error, _unknown = load_config(ws, config_path)
    checks: list[dict] = []

    if config_error:
        checks.append(_check("config", "FAIL", f"config error: {config_error}"))

    manifest_file = Path(manifest_path) if manifest_path else ws / ".ai" / "release_manifest.json"
    verification_file = Path(verification_path) if verification_path else ws / ".ai" / "verification.json"

    manifest, manifest_error = _load_json(manifest_file)
    verification, verification_error = _load_json(verification_file)

    # 1) worktree_clean
    if not is_git_repo(ws):
        checks.append(_check("worktree_clean", "FAIL", f"not a Git repository: {ws}"))
    else:
        porcelain = git_status_porcelain(ws)
        if porcelain.strip() == "":
            checks.append(_check("worktree_clean", "PASS", "working tree clean"))
        else:
            dirty_lines = porcelain.splitlines()
            checks.append(_check(
                "worktree_clean", "FAIL",
                f"working tree not clean ({len(dirty_lines)} change(s)): {', '.join(dirty_lines[:5])}",
            ))

    # 2) manifest_exists
    # manifest 가 없으면 "검증된 릴리스 후보" 자체가 존재하지 않는다. 이때 manifest
    # 의존 검사들만 NOT_RUN 으로 남기면, 남은 검사가 전부 PASS 라서 전체 판정이
    # PASS(exit 0) 로 나와 게이트가 통째로 우회된다. 그래서 부재 자체를 FAIL 로
    # 판정한다 (verification_exists 와 대칭).
    if manifest is None:
        checks.append(_check("manifest_exists", "FAIL", f"failed to load release manifest: {manifest_error}"))
    else:
        missing_fields = [f for f in MANIFEST_REQUIRED_FIELDS if f not in manifest]
        if missing_fields:
            checks.append(_check("manifest_exists", "FAIL",
                                 f"manifest missing required field(s): {', '.join(missing_fields)}"))
        else:
            checks.append(_check("manifest_exists", "PASS", f"release manifest present: {manifest_file}"))

    # 3) source_commit_match
    if manifest is None:
        checks.append(_check("source_commit_match", "NOT_RUN", f"failed to load manifest: {manifest_error}"))
    elif not is_git_repo(ws):
        checks.append(_check("source_commit_match", "FAIL", "not a Git repository, cannot check HEAD"))
    else:
        head = git_head(ws)
        source_commit = str(manifest.get("source_commit", ""))
        if source_commit and source_commit == head:
            checks.append(_check("source_commit_match", "PASS", f"source_commit == HEAD ({head[:12]})"))
        else:
            checks.append(_check(
                "source_commit_match", "FAIL",
                f"manifest.source_commit({source_commit[:12] or '(none)'}) != HEAD({head[:12]})",
            ))

    # 4) verification_exists
    if verification is None:
        checks.append(_check("verification_exists", "FAIL", f"failed to load verification.json: {verification_error}"))
    else:
        missing = [f for f in VERIFICATION_REQUIRED_FIELDS if f not in verification]
        if missing:
            checks.append(_check("verification_exists", "FAIL", f"missing required field(s): {', '.join(missing)}"))
        else:
            checks.append(_check("verification_exists", "PASS", f"verification.json present: {verification_file}"))

    # 5) verification_passed  (FAIL/NOT_RUN 모두 실패로 취급 — NOT_RUN 을 PASS 로 인정하지 않는다)
    if verification is None:
        checks.append(_check("verification_passed", "NOT_RUN", "cannot judge: verification.json failed to load"))
    else:
        v_status = verification.get("status")
        if v_status == "PASS":
            checks.append(_check("verification_passed", "PASS", "verification.status == PASS"))
        else:
            checks.append(_check(
                "verification_passed", "FAIL",
                f"verification.status == {v_status!r} (not PASS; NOT_RUN is not accepted as passing)",
            ))

    # 6) verification_hash (변조 감지)
    if verification is None:
        checks.append(_check("verification_hash", "NOT_RUN", "cannot judge: verification.json failed to load"))
    else:
        try:
            ok = verify_result_hash(verification)
        except (TypeError, ValueError) as exc:
            ok = False
            checks.append(_check("verification_hash", "FAIL", f"result_hash computation failed: {exc}"))
        else:
            checks.append(_check(
                "verification_hash", "PASS" if ok else "FAIL",
                "result_hash recomputation matches" if ok else "result_hash recomputation mismatch (possible tampering)",
            ))

    # 7) verification_run_match
    if manifest is None or verification is None:
        checks.append(_check("verification_run_match", "NOT_RUN",
                             "cannot judge: manifest or verification.json failed to load"))
    else:
        m_run = str(manifest.get("verification_run_id", ""))
        v_run = str(verification.get("verification_run_id", ""))
        if m_run and m_run == v_run:
            checks.append(_check("verification_run_match", "PASS", f"verification_run_id matches: {m_run}"))
        else:
            checks.append(_check(
                "verification_run_match", "FAIL",
                f"manifest.verification_run_id({m_run or '(none)'}) != verification.verification_run_id({v_run or '(none)'})",
            ))

    # 8) artifact_hashes (검증 후 변조 차단 — 핵심 게이트)
    if manifest is None:
        checks.append(_check("artifact_hashes", "NOT_RUN", "cannot judge: manifest failed to load"))
    else:
        artifacts = manifest.get("artifacts", [])
        if not isinstance(artifacts, list) or not artifacts:
            checks.append(_check("artifact_hashes", "FAIL", "manifest has no artifacts"))
        else:
            problems: list[str] = []
            for entry in artifacts:
                rel = str(entry.get("path", ""))
                expected_hash = str(entry.get("sha256", ""))
                target = Path(rel)
                target = target if target.is_absolute() else ws / rel
                if not target.is_file():
                    problems.append(f"{rel}: file missing")
                    continue
                actual_hash = _sha256_file_binary(target)
                if actual_hash != expected_hash:
                    problems.append(f"{rel}: hash mismatch (possible tampering)")
            if problems:
                checks.append(_check("artifact_hashes", "FAIL",
                                     f"{len(problems)} artifact issue(s): {'; '.join(problems[:5])}"))
            else:
                checks.append(_check("artifact_hashes", "PASS", f"{len(artifacts)} artifact hash(es) match"))

    # 9) total_hash
    if manifest is None:
        checks.append(_check("total_hash", "NOT_RUN", "cannot judge: manifest failed to load"))
    else:
        artifacts = manifest.get("artifacts", [])
        recomputed = sha256("".join(sorted(str(a.get("sha256", "")) for a in artifacts)))
        recorded = str(manifest.get("total_artifact_hash", ""))
        if recomputed == recorded:
            checks.append(_check("total_hash", "PASS", "total_artifact_hash recomputation matches"))
        else:
            checks.append(_check("total_hash", "FAIL", "total_artifact_hash recomputation mismatch (possible tampering)"))

    # 10) manifest_hash (manifest 자체 변조 차단)
    if manifest is None:
        checks.append(_check("manifest_hash", "NOT_RUN", "cannot judge: manifest failed to load"))
    else:
        recomputed = _manifest_body_hash(manifest)
        recorded = str(manifest.get("manifest_hash", ""))
        if recomputed == recorded:
            checks.append(_check("manifest_hash", "PASS", "manifest_hash recomputation matches"))
        else:
            checks.append(_check("manifest_hash", "FAIL", "manifest_hash recomputation mismatch (possible tampering)"))

    # 11) rollback_point
    require_rollback = bool(config.get("require_rollback", False))
    if manifest is None:
        checks.append(_check("rollback_point", "NOT_RUN", "cannot judge: manifest failed to load"))
    else:
        rollback_point = str(manifest.get("rollback_point", "") or "").strip()
        if require_rollback and not rollback_point:
            checks.append(_check("rollback_point", "FAIL", "require_rollback=true but rollback_point is empty"))
        elif not rollback_point:
            checks.append(_check("rollback_point", "PASS", "no rollback_point (require_rollback=false, warning)"))
        else:
            checks.append(_check("rollback_point", "PASS", f"rollback_point: {rollback_point}"))

    # 12) human_approval
    require_approval = bool(config.get("require_human_approval", False))
    if manifest is None:
        checks.append(_check("human_approval", "NOT_RUN", "cannot judge: manifest failed to load"))
    else:
        approved_by = str(manifest.get("approved_by", "") or "").strip()
        if require_approval and not approved_by:
            checks.append(_check("human_approval", "FAIL", "require_human_approval=true but approved_by is empty"))
        else:
            checks.append(_check(
                "human_approval", "PASS",
                f"approved_by: {approved_by}" if approved_by else "no approver set (require_human_approval=false)",
            ))

    # 13) release_enabled
    release_enabled = bool(config.get("release_enabled", False))
    if release_enabled:
        checks.append(_check("release_enabled", "PASS", "release_enabled=true"))
    else:
        checks.append(_check("release_enabled", "FAIL", "release_enabled=false: releases are disabled for this project"))

    has_fail = any(c["status"] == "FAIL" for c in checks)
    executed = [c for c in checks if c["status"] in ("PASS", "FAIL")]
    overall = "FAIL" if has_fail else ("PASS" if executed else "NOT_RUN")

    return {
        "workspace": str(ws),
        "manifest_path": str(manifest_file),
        "verification_path": str(verification_file),
        "release_id": (manifest or {}).get("release_id", ""),
        "version": (manifest or {}).get("version", ""),
        "status": overall,
        "checks": checks,
        "summary": {
            "pass": sum(1 for c in checks if c["status"] == "PASS"),
            "fail": sum(1 for c in checks if c["status"] == "FAIL"),
            "not_run": sum(1 for c in checks if c["status"] == "NOT_RUN"),
        },
    }


def _sha256_file_binary(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="verify_release", description="Verify a release candidate (rollback gate)")
    parser.add_argument("--manifest", default=None, help="release manifest path (default: .ai/release_manifest.json)")
    parser.add_argument("--verification", default=None, help="verification.json path (default: .ai/verification.json)")
    parser.add_argument("--workspace", default=None, help="workspace path (default: current directory)")
    parser.add_argument("--config", default=None, help="config file path (default: auto-detect .ai-standard.*)")
    parser.add_argument("--json", action="store_true", help="output as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_io()
    args = build_parser().parse_args(argv)
    report = run_verify_release(
        resolve_workspace(args.workspace),
        manifest_path=args.manifest,
        verification_path=args.verification,
        config_path=args.config,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"verify_release: {report['status']}  (release_id: {report['release_id'] or '(none)'}, "
              f"version: {report['version'] or '(none)'}, "
              f"pass {report['summary']['pass']} / fail {report['summary']['fail']} / "
              f"not_run {report['summary']['not_run']})")
        for c in report["checks"]:
            print(f"  [{c['status']:<7}] {c['name']}: {c['detail']}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
