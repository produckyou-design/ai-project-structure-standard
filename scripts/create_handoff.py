"""create_handoff.py — 단일 Markdown 인계 번들 생성 (Phase 1).

.ai/handoffs/handoff_<timestamp>.md 를 생성한다.
- 현재 상태 (CURRENT.md)
- 변경 사항 (Git status, diff stat)
- 테스트 결과 (ledger 의 최근 종료 서명)
- 블로커, 다음 작업, 롤백 지점, 알려진 제한
- 민감정보는 마스킹된다 (원문 미출력)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    GitError,
    changed_files,
    configure_utf8_io,
    deleted_files,
    git_branch,
    git_head,
    git_status_porcelain,
    is_git_repo,
    mask_sensitive,
    now_iso,
    read_ledger,
    repo_root,
    resolve_workspace,
    run_git,
    untracked_files,
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _diff_stat_lines(workspace: Path) -> list[str]:
    try:
        return run_git(workspace, ["diff", "--stat"]).splitlines()
    except GitError:
        return []


def _latest(entries: list[dict], kind: str) -> dict | None:
    return next((e for e in reversed(entries) if e.get("kind") == kind), None)


def create_handoff(workspace: Path, out: str | None = None) -> dict:
    """인계 번들 마크다운을 생성하고 생성 경로를 반환한다."""
    if not is_git_repo(workspace):
        raise GitError(f"Git 저장소가 아닙니다: {workspace}")
    root = repo_root(workspace)
    entries = read_ledger(workspace)
    latest_start = _latest(entries, "start")
    latest_end = _latest(entries, "end")

    current_md = _read_text(root / ".ai" / "CURRENT.md")
    status_md = _read_text(root / ".ai" / "STATUS.md")
    changed = changed_files(workspace)
    untracked = untracked_files(workspace)
    deleted = deleted_files(workspace)
    diff_stat = _diff_stat_lines(workspace)

    if latest_end:
        test_section = (
            "## 4. 테스트 결과 (마지막 종료 서명)\n"
            f"- run_id: `{latest_end.get('run_id', '-')}`  status: `{latest_end.get('status', '-')}`\n"
            f"- tests_run: `{latest_end.get('tests_run', '-')}`  passed: `{latest_end.get('tests_passed', '-')}`  "
            f"failed: `{latest_end.get('tests_failed', '-')}`"
        )
    else:
        test_section = "## 4. 테스트 결과\n- NOT_RUN (아직 기록된 종료 서명/테스트 결과 없음)"

    sections = [
        "# AI 세션 인계 번들",
        f"> 생성 시각: `{now_iso()}`  |  자동 생성: `scripts/create_handoff.py`\n"
        "> 이 문서는 이전 대화 없이 다음 AI 가 이어받을 수 있도록 구성된 인계 번들이다.",
        "## 1. 개요\n"
        f"- 브랜치: `{git_branch(workspace)}`\n"
        f"- HEAD: `{git_head(workspace)}`\n"
        f"- 작업트리: {len(changed)} 개 변경 (신규 {len(untracked)} / 삭제 {len(deleted)})",
        "## 2. 현재 상태 (CURRENT.md)\n```markdown\n" + (current_md or "(CURRENT.md 없음)") + "\n```",
        "## 3. 변경 사항\n"
        + ("- 변경/신규/삭제 목록은 아래와 같다.\n" + "".join(f"  - {p}\n" for p in changed) if changed else "- 변경 없음")
        + ("\n```text\n" + "\n".join(diff_stat) + "\n```" if diff_stat else ""),
        test_section,
        "## 5. 블로커\n"
        + (f"- {latest_end.get('known_issues')}" if latest_end and latest_end.get("known_issues") else "- 없음 (기록 기준)"),
        "## 6. 다음 작업\n"
        + (f"- {latest_end.get('remaining_work')}" if latest_end and latest_end.get("remaining_work")
           else "- CURRENT.md 의 인계 메모를 참고한다."),
        "## 7. 롤백 지점\n"
        + (f"- {latest_end.get('rollback_point')}" if latest_end and latest_end.get("rollback_point")
           else f"- 직전 정상 커밋: `{git_head(workspace)}`"),
        "## 8. 알려진 제한\n"
        + (f"- {latest_end.get('known_issues')}" if latest_end and latest_end.get("known_issues") else "- 기록 없음"),
        "## 9. 상태표 (STATUS.md)\n```markdown\n" + (status_md or "(STATUS.md 없음)") + "\n```",
        "## 10. 검증\n"
        "- 이 번들은 생성 시점의 실제 Git 상태를 기준으로 작성되었다.\n"
        "- 민감정보는 마스킹되어 포함된다. 서명·체크포인트·테스트 결과는 ledger 와 .ai/ 의 원본을 우선한다.",
    ]
    body = mask_sensitive("\n\n---\n\n".join(sections)) + "\n"

    ts = now_iso().replace(":", "-").replace("+", "Z")
    out_path = Path(out) if out else root / ".ai" / "handoffs" / f"handoff_{ts}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")
    return {"path": str(out_path), "lines": len(body.splitlines())}


def main(argv: list[str] | None = None) -> int:
    configure_utf8_io()
    parser = argparse.ArgumentParser(prog="create_handoff", description="AI 인계 번들 생성")
    parser.add_argument("--out", default=None, help="출력 경로 (기본: .ai/handoffs/handoff_<ts>.md)")
    parser.add_argument("--workspace", default=None, help="작업 저장소 경로 (기본: 현재 디렉터리)")
    args = parser.parse_args(argv)
    try:
        result = create_handoff(resolve_workspace(args.workspace), out=args.out)
    except GitError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    print(f"handoff: {result['path']} ({result['lines']} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
