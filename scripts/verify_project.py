"""verify_project.py — Phase 5: 프로젝트별 검증 명령 실행기.

용법:
  python scripts/verify_project.py [--config PATH] [--workspace PATH] [--out PATH] [--json]

- 설정(.ai-standard.yml)의 verify_commands(문법·정적 분석·사용자 정의)와 test_command 를 실행한다.
- 시크릿 검사·금지 패턴 검사·git diff --check 를 연결한다.
- 검사별 명령, 시작·종료 시각, exit code, PASS/FAIL/NOT_RUN, 로그 위치를 기록한다.
- 결과를 schemas/verification.schema.json 을 따르는 .ai/verification.json 으로 저장한다.
- 어떤 명령도 실행하지 않았는데 PASS 로 기록하지 않는다 (미실행 = NOT_RUN).
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    configure_utf8_io,
    git_head,
    git_status_hash,
    is_git_repo,
    now_iso,
    resolve_workspace,
    sha256,
)
from preflight import load_config  # noqa: E402  (설정 로드의 단일 소유자 재사용)

SCRIPTS_DIR = Path(__file__).resolve().parent
COMMAND_TIMEOUT_SECONDS = 900


def _split_command(command: str) -> list[str]:
    return shlex.split(command, posix=(os.name != "nt"))


def _run_check(name: str, argv: list[str], *, cwd: Path, log_dir: Path,
               display_command: str | None = None) -> dict:
    """명령 하나를 실행하고 check 항목을 반환한다. stdout/stderr 는 로그 파일에 남긴다."""
    command_str = display_command or " ".join(argv)
    tool = argv[0] if argv else ""
    if not tool or shutil.which(tool) is None:
        return {"name": name, "status": "NOT_RUN", "command": command_str,
                "exit_code": None, "detail": f"tool not found: {tool or '(empty command)'}"}
    started = now_iso()
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    log_file = log_dir / f"{safe_name}.log"
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=COMMAND_TIMEOUT_SECONDS,
        )
        exit_code: int | None = proc.returncode
        output = (proc.stdout or "") + (("\n--- stderr ---\n" + proc.stderr) if proc.stderr else "")
        status = "PASS" if exit_code == 0 else "FAIL"
        detail = f"exit code {exit_code}"
    except subprocess.TimeoutExpired:
        exit_code, status = None, "FAIL"
        output = f"timed out (exceeded {COMMAND_TIMEOUT_SECONDS}s)"
        detail = output
    except OSError as exc:
        exit_code, status = None, "FAIL"
        output = f"execution failed: {exc}"
        detail = output
    log_file.write_text(f"$ {command_str}\n\n{output}\n", encoding="utf-8")
    return {"name": name, "status": status, "command": command_str,
            "exit_code": exit_code, "started_at": started, "ended_at": now_iso(),
            "log_file": str(log_file), "detail": detail}


def run_verification(workspace: Path, config_path: str | None = None,
                     out_path: str | None = None) -> dict:
    """검증을 수행하고 결과 dict 를 반환한다. 결과는 out_path(기본 .ai/verification.json)에 저장한다."""
    ws = resolve_workspace(workspace)
    config, config_error, _unknown = load_config(ws, config_path)
    run_id = f"verif_{now_iso().replace(':', '').replace('-', '').replace('+', '')}_{secrets.token_hex(3)}"
    log_dir = ws / ".ai" / "verification_logs" / run_id
    started_at = now_iso()
    checks: list[dict] = []

    if config_error:
        checks.append({"name": "config", "status": "FAIL",
                       "detail": f"config error: {config_error}"})

    # 1) 사용자 정의 검증 명령 (문법 검사·정적 분석 포함, 언어 비의존)
    verify_commands = [c for c in config.get("verify_commands", [])]
    if verify_commands:
        for command in verify_commands:
            if not str(command).strip():
                checks.append({"name": "verify:(empty command)", "status": "FAIL",
                               "detail": "verify_commands contains an empty command"})
                continue
            argv = _split_command(str(command))
            checks.append(_run_check(f"verify:{argv[0]}", argv, cwd=ws, log_dir=log_dir,
                                     display_command=str(command)))
    else:
        checks.append({"name": "verify_commands", "status": "NOT_RUN",
                       "detail": "verify_commands not configured (lint/static analysis not run)"})

    # 2) 단위 테스트
    test_command = str(config.get("test_command", "") or "")
    if test_command.strip():
        checks.append(_run_check("tests", _split_command(test_command), cwd=ws,
                                 log_dir=log_dir, display_command=test_command))
    else:
        checks.append({"name": "tests", "status": "NOT_RUN",
                       "detail": "test_command not configured"})

    # 3) 시크릿 검사·금지 패턴 검사 연결 (본 표준 저장소의 검사기를 실행)
    for name, script in (("secrets", "check_secrets.py"),
                         ("forbidden_patterns", "check_forbidden_patterns.py")):
        script_path = SCRIPTS_DIR / script
        argv = [sys.executable, str(script_path), "--workspace", str(ws)]
        if config_path:
            argv += ["--config", str(config_path)]
        checks.append(_run_check(name, argv, cwd=ws, log_dir=log_dir,
                                 display_command=f"python scripts/{script} --workspace {ws}"))

    # 4) git diff --check
    commit = "NONE"
    worktree_hash = ""
    if is_git_repo(ws):
        commit = git_head(ws)
        worktree_hash = git_status_hash(ws)
        checks.append(_run_check("git_diff_check",
                                 ["git", "-c", "core.quotepath=false", "diff", "--check"],
                                 cwd=ws, log_dir=log_dir, display_command="git diff --check"))
    else:
        checks.append({"name": "git_diff_check", "status": "NOT_RUN",
                       "detail": "not a Git repository"})

    executed = [c for c in checks if c["status"] in ("PASS", "FAIL")]
    has_fail = any(c["status"] == "FAIL" for c in checks)
    overall = "FAIL" if has_fail else ("PASS" if executed else "NOT_RUN")

    report = {
        "verification_run_id": run_id,
        "workspace": str(ws),
        "commit": commit,
        "worktree_status_hash": worktree_hash,
        "config_source": str(config_path or ""),
        "started_at": started_at,
        "ended_at": now_iso(),
        "status": overall,
        "checks": checks,
        "summary": {
            "pass": sum(1 for c in checks if c["status"] == "PASS"),
            "fail": sum(1 for c in checks if c["status"] == "FAIL"),
            "not_run": sum(1 for c in checks if c["status"] == "NOT_RUN"),
        },
    }
    canonical = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    report["result_hash"] = sha256(canonical)

    out = Path(out_path) if out_path else ws / ".ai" / "verification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_out_path"] = str(out)
    return report


def verify_result_hash(report: dict) -> bool:
    """저장된 verification 결과의 result_hash 가 본문과 일치하는지 검증한다."""
    body = {k: v for k, v in report.items() if k not in ("result_hash", "_out_path")}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(canonical) == report.get("result_hash", "")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="verify_project", description="Run project-specific verification commands")
    parser.add_argument("--config", default=None, help="config file path (default: auto-detect .ai-standard.*)")
    parser.add_argument("--workspace", default=None, help="workspace path (default: current directory)")
    parser.add_argument("--out", default=None, help="result output path (default: .ai/verification.json)")
    parser.add_argument("--json", action="store_true", help="output as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_io()
    args = build_parser().parse_args(argv)
    report = run_verification(resolve_workspace(args.workspace),
                              config_path=args.config, out_path=args.out)
    out_path = report.pop("_out_path", "")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"verification: {report['status']}  (commit: {report['commit'][:12]}, "
              f"pass {report['summary']['pass']} / fail {report['summary']['fail']} / "
              f"not_run {report['summary']['not_run']})")
        for c in report["checks"]:
            print(f"  [{c['status']:<7}] {c['name']}: {c.get('detail', c.get('command', ''))}")
        print(f"result: {out_path}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
