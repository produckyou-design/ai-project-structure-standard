"""preflight.py — Phase 2: 프로젝트 수정 전 상태와 위험 경계 확인.

용법:
  python scripts/preflight.py [--config PATH] [--workspace PATH] [--json]

검사 항목:
  - Git 저장소 여부, 브랜치와 HEAD
  - protected branch 여부
  - 작업트리 상태(미커밋 변경, 추적되지 않은 파일)
  - 필수 문서 존재
  - 보호 파일 변경 여부
  - 시크릿 파일이 Git 에 추적되는지
  - 실행 환경(Python/OS)
  - 테스트 도구·검증 명령 존재
  - 프로젝트 위험 등급
  - 설정 파일 유효성

설정 파일(.ai-standard.json/.yml/.yaml)이 없으면 안전한 기본값으로 동작한다.
특정 언어·프레임워크에 하드코딩하지 않는다.

CLI 출력(사용자에게 실제로 찍히는 메시지)은 영어다. docstring/주석은 한국어로 유지한다.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    configure_utf8_io,
    git_branch,
    git_head,
    git_status_porcelain,
    is_git_repo,
    resolve_workspace,
    run_git,
)

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "project_config.schema.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "project_name": "unnamed-project",
    "risk_level": "low",
    "protected_branches": ["main", "master", "develop"],
    "verify_commands": [],
    "test_command": "",
    "forbidden_patterns": [],
    "allow_exceptions": [],
    "allowed_domains": [],
    "required_documents": [],
    "protected_files": [],
    "secret_files": [".env", ".env.*", "*.pem", "*.key", "id_rsa", "id_ed25519", "*.p12", "*.jks"],
    "release_enabled": False,
    "require_human_approval": False,
    "require_rollback": False,
}

CONFIG_FILENAMES = [".ai-standard.json", ".ai-standard.yml", ".ai-standard.yaml"]


class ConfigError(ValueError):
    pass


def _manual_type_check(config: dict) -> str | None:
    """jsonschema 가 없을 때 사용하는 경량 타입 검증. 문제 없으면 None."""
    for field in ("project_name", "test_command"):
        if field in config and not isinstance(config[field], str):
            return f"{field} must be a string"
    for field in (
        "protected_branches", "verify_commands", "forbidden_patterns",
        "allow_exceptions", "allowed_domains", "required_documents",
        "protected_files", "secret_files",
    ):
        if field in config and not isinstance(config[field], list):
            return f"{field} must be an array"
    for field in ("release_enabled", "require_human_approval", "require_rollback"):
        if field in config and not isinstance(config[field], bool):
            return f"{field} must be a boolean"
    if "risk_level" in config and config["risk_level"] not in ("low", "medium", "high"):
        return "risk_level must be one of low|medium|high"
    return None


_SCHEMA_CACHE: dict | None = None


def _load_schema() -> dict:
    """스키마를 1회만 읽고 캐시한다."""
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        _SCHEMA_CACHE = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return _SCHEMA_CACHE


def _validate_config(config: dict) -> str | None:
    """설정을 스키마로 검증한다. 문제 없으면 None."""
    try:
        import jsonschema
    except ImportError:
        return _manual_type_check(config)
    try:
        jsonschema.validate(instance=config, schema=_load_schema())
        return None
    except Exception as exc:  # jsonschema.ValidationError, JSONDecodeError 등
        return str(exc)


def find_config(workspace: Path) -> Path | None:
    for name in CONFIG_FILENAMES:
        candidate = workspace / name
        if candidate.is_file():
            return candidate
    return None


def load_config(workspace: Path, config_path: str | None = None) -> tuple[dict, str | None, list[str]]:
    """설정을 로드한다.

    반환: (config, error_message, unknown_keys).
    - 설정 파일이 없으면 (DEFAULT_CONFIG, None, [])
    - 파일은 있지만 파싱·검증에 실패하면 (DEFAULT_CONFIG, 오류메시지, [])
    - 스키마에 없는 알 수 없는 키는 unknown_keys 로 반환한다 (오타 감지용).
    """
    path = Path(config_path) if config_path else find_config(workspace)
    if path is None:
        return dict(DEFAULT_CONFIG), None, []
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    try:
        # Windows 편집기가 저장하는 UTF-8 BOM 도 읽을 수 있도록 utf-8-sig 사용
        if path.suffix.lower() == ".json":
            loaded = json.loads(path.read_text(encoding="utf-8-sig"))
        else:
            import yaml
            loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    except Exception as exc:
        return dict(DEFAULT_CONFIG), f"config parse failed: {exc}", []
    if not isinstance(loaded, dict):
        return dict(DEFAULT_CONFIG), "config top level must be an object", []
    merged = {**DEFAULT_CONFIG, **loaded}
    unknown = sorted(set(loaded) - set(DEFAULT_CONFIG))
    return merged, _validate_config(merged), unknown


def run_preflight(workspace: Path, config_path: str | None = None) -> dict:
    """preflight 검사를 수행하고 보고서를 반환한다."""
    ws = resolve_workspace(workspace)
    config, config_error, unknown_keys = load_config(ws, config_path)
    findings: list[dict] = []

    git_ok = is_git_repo(ws)
    branch, head, porcelain = "N/A", "N/A", ""
    if git_ok:
        branch = git_branch(ws)
        head = git_head(ws)
        porcelain = git_status_porcelain(ws)
        findings.append({"check": "git_repo", "status": "PASS",
                         "detail": f"Git repository. branch {branch}, HEAD {head}"})
        if branch in config.get("protected_branches", []):
            findings.append({"check": "protected_branch", "status": "FAIL",
                             "detail": f"direct work on protected branch ({branch}) is not allowed. Use a feature branch."})
        else:
            findings.append({"check": "protected_branch", "status": "PASS",
                             "detail": f"{branch} is not a protected branch"})

        lines = porcelain.splitlines()
        dirty = [ln[3:] for ln in lines if len(ln) > 3 and not ln.startswith("??")]
        untracked = [ln[3:] for ln in lines if ln.startswith("??")]
        if dirty:
            findings.append({"check": "worktree", "status": "WARN",
                             "detail": f"{len(dirty)} uncommitted change(s): {', '.join(dirty[:5])}"})
        else:
            findings.append({"check": "worktree", "status": "PASS", "detail": "working tree clean"})
        if untracked:
            findings.append({"check": "untracked", "status": "INFO",
                             "detail": f"{len(untracked)} untracked file(s): {', '.join(untracked[:5])}"})
        else:
            findings.append({"check": "untracked", "status": "PASS", "detail": "no untracked files"})
    else:
        findings.append({"check": "git_repo", "status": "FAIL", "detail": f"not a Git repository: {ws}"})
        for check in ("protected_branch", "worktree", "untracked", "protected_file", "secret_files_tracked"):
            findings.append({"check": check, "status": "NOT_RUN", "detail": "not a Git repository"})

    # 필수 문서
    for doc in config.get("required_documents", []):
        if (ws / doc).is_file():
            findings.append({"check": f"required_document:{doc}", "status": "PASS",
                             "detail": f"required document present: {doc}"})
        else:
            findings.append({"check": f"required_document:{doc}", "status": "FAIL",
                             "detail": f"required document missing: {doc}"})
    if not config.get("required_documents"):
        findings.append({"check": "required_document", "status": "INFO", "detail": "no required documents configured"})

    if git_ok:
        changed = [ln[3:] for ln in porcelain.splitlines() if len(ln) > 3]
        for pf in config.get("protected_files", []):
            if not (ws / pf).is_file():
                findings.append({"check": f"protected_file:{pf}", "status": "FAIL",
                                 "detail": f"protected file does not exist: {pf}"})
            elif pf in changed:
                findings.append({"check": f"protected_file:{pf}", "status": "FAIL",
                                 "detail": f"protected file was changed: {pf}"})
            else:
                findings.append({"check": f"protected_file:{pf}", "status": "PASS",
                                 "detail": f"protected file unchanged: {pf}"})
        if not config.get("protected_files"):
            findings.append({"check": "protected_file", "status": "INFO", "detail": "no protected files configured"})

        tracked = run_git(ws, ["ls-files"]).splitlines()
        patterns = config.get("secret_files", [])
        matched = sorted({
            f for f in tracked
            if any(fnmatch.fnmatch(f, p) or fnmatch.fnmatch(f.lower(), p.lower()) for p in patterns)
        })
        if matched:
            findings.append({"check": "secret_files_tracked", "status": "FAIL",
                             "detail": f"secret-pattern file(s) tracked by Git: {', '.join(matched)}"})
        else:
            findings.append({"check": "secret_files_tracked", "status": "PASS",
                             "detail": "no secret-pattern files are tracked"})

    # 실행 환경
    findings.append({"check": "environment", "status": "INFO",
                     "detail": f"Python {platform.python_version()} / {platform.system()}"})

    def _tool_exists(command: str) -> bool:
        parts = command.split()
        return bool(parts) and shutil.which(parts[0]) is not None

    test_cmd = config.get("test_command", "")
    if test_cmd:
        if _tool_exists(test_cmd):
            findings.append({"check": "test_tool", "status": "PASS", "detail": f"test tool found: {test_cmd}"})
        else:
            findings.append({"check": "test_tool", "status": "WARN", "detail": f"test tool not found: {test_cmd}"})
    else:
        findings.append({"check": "test_tool", "status": "INFO", "detail": "no test_command configured"})

    for cmd in config.get("verify_commands", []):
        if _tool_exists(cmd):
            findings.append({"check": f"verify_tool:{cmd}", "status": "PASS", "detail": f"verify tool found: {cmd}"})
        else:
            findings.append({"check": f"verify_tool:{cmd}", "status": "WARN", "detail": f"verify tool not found: {cmd}"})
    if not config.get("verify_commands"):
        findings.append({"check": "verify_tool", "status": "INFO", "detail": "no verify_commands configured"})

    # 설정 유효성
    source = str(config_path) if config_path else str(find_config(ws) or "defaults")
    if config_error:
        findings.append({"check": "config_valid", "status": "FAIL", "detail": config_error})
    elif unknown_keys:
        findings.append({"check": "config_valid", "status": "WARN",
                         "detail": f"unknown config key(s) (possible typo): {', '.join(unknown_keys)} (source: {source})"})
    else:
        findings.append({"check": "config_valid", "status": "PASS", "detail": f"config valid (source: {source})"})

    # 위험 등급
    findings.append({"check": "risk_level", "status": "INFO", "detail": f"risk level: {config.get('risk_level')}"})

    has_fail = any(f["status"] == "FAIL" for f in findings)
    has_warn = any(f["status"] == "WARN" for f in findings)
    return {
        "status": "FAIL" if has_fail else ("WARN" if has_warn else "PASS"),
        "project_name": config.get("project_name"),
        "risk_level": config.get("risk_level"),
        "config_source": source,
        "git_repo": git_ok,
        "branch": branch,
        "head": head,
        "findings": findings,
        "summary": {
            "fail": sum(1 for f in findings if f["status"] == "FAIL"),
            "warn": sum(1 for f in findings if f["status"] == "WARN"),
            "pass": sum(1 for f in findings if f["status"] in ("PASS", "INFO")),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="preflight", description="Check risk boundaries before modifying a project")
    parser.add_argument("--config", default=None, help="config file path (default: auto-detect .ai-standard.json/.yml/.yaml)")
    parser.add_argument("--workspace", default=None, help="workspace path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="output as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_io()
    args = build_parser().parse_args(argv)
    try:
        report = run_preflight(resolve_workspace(args.workspace), config_path=args.config)
    except ConfigError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"preflight: {report['status']}  (project: {report['project_name']}, "
              f"risk: {report['risk_level']}, source: {report['config_source']})")
        for f in report["findings"]:
            print(f"  [{f['status']:<6}] {f['check']}: {f['detail']}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
