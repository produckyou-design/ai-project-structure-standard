"""sign_ai_session.py — AI 시작·종료 서명 생성 (Phase 1).

용법:
  python scripts/sign_ai_session.py start --task "..." [옵션]
  python scripts/sign_ai_session.py end --status success [옵션]

- 시작/종료 서명을 .ai/ledger.jsonl 에 append-only 로 기록한다.
- previous_entry_hash / entry_hash 로 해시 체인을 연결한다.
- Git 브랜치, HEAD, 작업트리 상태 해시를 실제로 수집한다.
- 민감정보 원문을 출력하지 않는다 (마스킹 후 출력).
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    GitError,
    append_ledger,
    changed_files,
    configure_utf8_io,
    deleted_files,
    git_branch,
    git_diff_hash,
    git_head,
    git_status_hash,
    is_git_repo,
    ledger_path,
    mask_value,
    now_iso,
    read_ledger,
    repo_root,
    resolve_actual_model_id,
    resolve_workspace,
    untracked_files,
)


def generate_run_id() -> str:
    stamp = now_iso().replace(":", "").replace("-", "").replace("+", "")
    return f"run_{stamp}_{secrets.token_hex(3)}"


def run_start(
    workspace: Path,
    task: str,
    *,
    run_id: str | None = None,
    parent_run_id: str = "",
    provider: str = "unknown",
    claimed_model: str = "unknown",
    role: str = "implementer",
    effort: str = "medium",
    allowed_scope: str = "",
    forbidden_scope: str = "",
    expected_tests: str = "",
    documents_read: str = "",
) -> dict:
    """시작 서명을 생성하고 ledger에 기록한다."""
    if not task.strip():
        raise ValueError("task 는 필수입니다.")
    if not is_git_repo(workspace):
        raise GitError(f"Git 저장소가 아닙니다: {workspace}")
    entry = {
        "kind": "start",
        "run_id": run_id or generate_run_id(),
        "parent_run_id": parent_run_id or "",
        "provider": provider,
        "actual_model_id": resolve_actual_model_id(),
        "claimed_model": claimed_model,
        "role": role,
        "effort": effort,
        "started_at": now_iso(),
        "workspace": str(repo_root(workspace)),
        "branch": git_branch(workspace),
        "base_commit": git_head(workspace),
        "git_status_hash": git_status_hash(workspace),
        "task": task,
        "allowed_scope": allowed_scope,
        "forbidden_scope": forbidden_scope,
        "expected_tests": expected_tests,
        "documents_read": documents_read,
    }
    return append_ledger(workspace, entry)


def run_end(
    workspace: Path,
    status: str,
    *,
    run_id: str | None = None,
    tests_run: str = "",
    tests_passed: str = "",
    tests_failed: str = "",
    documents_updated: str = "",
    decisions_made: str = "",
    known_issues: str = "",
    remaining_work: str = "",
    rollback_point: str = "",
    handoff_note: str = "",
) -> dict:
    """종료 서명을 생성하고 ledger에 기록한다.

    run_id 미지정 시 연결 가능한 마지막 start 항목을 자동으로 찾는다.
    """
    if status not in ("success", "fail", "aborted"):
        raise ValueError("status 는 success|fail|aborted 중 하나여야 합니다.")
    if not is_git_repo(workspace):
        raise GitError(f"Git 저장소가 아닙니다: {workspace}")

    entries = read_ledger(workspace)

    def _has_end(rid: str) -> bool:
        return any(e.get("kind") == "end" and e.get("run_id") == rid for e in entries)

    linked = None
    if run_id:
        linked = next((e for e in entries if e.get("run_id") == run_id and e.get("kind") == "start"), None)
        if linked is None:
            raise ValueError(f"run_id '{run_id}' 에 해당하는 start 항목이 ledger에 없습니다.")
    else:
        # 이미 end 가 있는 run 을 다시 선택하지 않는다 (중복 end 방지)
        linked = next((e for e in reversed(entries) if e.get("kind") == "start" and not _has_end(e["run_id"])), None)
        if linked is None:
            raise ValueError(
                "연결할 start 항목이 없습니다. --run-id 를 지정하거나 먼저 start 서명을 생성하세요."
            )

    entry = {
        "kind": "end",
        "run_id": run_id or linked["run_id"],
        "provider": linked.get("provider", ""),
        "actual_model_id": resolve_actual_model_id(),
        "role": linked.get("role", ""),
        "status": status,
        "ended_at": now_iso(),
        "base_commit": linked.get("base_commit", ""),
        "end_commit": git_head(workspace),
        "diff_hash": git_diff_hash(workspace),
        "changed_files": changed_files(workspace),
        "created_files": untracked_files(workspace),
        "deleted_files": deleted_files(workspace),
        "tests_run": tests_run,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "documents_updated": documents_updated,
        "decisions_made": decisions_made,
        "known_issues": known_issues,
        "remaining_work": remaining_work,
        "rollback_point": rollback_point,
        "handoff_note": handoff_note,
    }
    return append_ledger(workspace, entry)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sign_ai_session", description="AI 작업 시작·종료 서명 생성")
    parser.add_argument("--workspace", default=None, help="작업 저장소 경로 (기본: 현재 디렉터리)")
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("start", help="시작 서명 생성")
    sp.add_argument("--task", required=True, help="수행할 작업 설명")
    sp.add_argument("--run-id", default=None)
    sp.add_argument("--parent-run-id", default="")
    sp.add_argument("--provider", default="unknown")
    sp.add_argument("--claimed-model", default="unknown")
    sp.add_argument("--role", default="implementer")
    sp.add_argument("--effort", default="medium")
    sp.add_argument("--allowed-scope", default="")
    sp.add_argument("--forbidden-scope", default="")
    sp.add_argument("--expected-tests", default="")
    sp.add_argument("--documents-read", default="")

    ep = sub.add_parser("end", help="종료 서명 생성")
    ep.add_argument("--status", required=True, choices=["success", "fail", "aborted"])
    ep.add_argument("--run-id", default=None)
    ep.add_argument("--tests-run", default="")
    ep.add_argument("--tests-passed", default="")
    ep.add_argument("--tests-failed", default="")
    ep.add_argument("--documents-updated", default="")
    ep.add_argument("--decisions-made", default="")
    ep.add_argument("--known-issues", default="")
    ep.add_argument("--remaining-work", default="")
    ep.add_argument("--rollback-point", default="")
    ep.add_argument("--handoff-note", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_io()
    args = build_parser().parse_args(argv)
    workspace = resolve_workspace(args.workspace)
    try:
        if args.command == "start":
            entry = run_start(
                workspace, args.task,
                run_id=args.run_id, parent_run_id=args.parent_run_id,
                provider=args.provider, claimed_model=args.claimed_model,
                role=args.role, effort=args.effort,
                allowed_scope=args.allowed_scope, forbidden_scope=args.forbidden_scope,
                expected_tests=args.expected_tests, documents_read=args.documents_read,
            )
        else:
            entry = run_end(
                workspace, args.status,
                run_id=args.run_id,
                tests_run=args.tests_run, tests_passed=args.tests_passed, tests_failed=args.tests_failed,
                documents_updated=args.documents_updated, decisions_made=args.decisions_made,
                known_issues=args.known_issues, remaining_work=args.remaining_work,
                rollback_point=args.rollback_point, handoff_note=args.handoff_note,
            )
    except (GitError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    print(json.dumps(mask_value(entry), ensure_ascii=False, indent=2))
    print(f"ledger: {ledger_path(workspace)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
