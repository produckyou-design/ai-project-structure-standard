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
            return f"{field} 는 문자열이어야 합니다"
    for field in (
        "protected_branches", "verify_commands", "forbidden_patterns",
        "allow_exceptions", "allowed_domains", "required_documents",
        "protected_files", "secret_files",
    ):
        if field in config and not isinstance(config[field], list):
            return f"{field} 는 배열이어야 합니다"
    for field in ("release_enabled", "require_human_approval", "require_rollback"):
        if field in config and not isinstance(config[field], bool):
            return f"{field} 는 boolean 이어야 합니다"
    if "risk_level" in config and config["risk_level"] not in ("low", "medium", "high"):
        return "risk_level 은 low|medium|high 중 하나여야 합니다"
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
        raise ConfigError(f"설정 파일이 없습니다: {path}")
    try:
        # Windows 편집기가 저장하는 UTF-8 BOM 도 읽을 수 있도록 utf-8-sig 사용
        if path.suffix.lower() == ".json":
            loaded = json.loads(path.read_text(encoding="utf-8-sig"))
        else:
            import yaml
            loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    except Exception as exc:
        return dict(DEFAULT_CONFIG), f"설정 파싱 실패: {exc}", []
    if not isinstance(loaded, dict):
        return dict(DEFAULT_CONFIG), "설정 최상위는 객체여야 합니다", []
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
                         "detail": f"Git 저장소. 브랜치 {branch}, HEAD {head}"})
        if branch in config.get("protected_branches", []):
            findings.append({"check": "protected_branch", "status": "FAIL",
                             "detail": f"protected branch({branch})에서 직접 작업 금지. feature branch 를 사용하라."})
        else:
            findings.append({"check": "protected_branch", "status": "PASS",
                             "detail": f"{branch} 는 보호 대상이 아님"})

        lines = porcelain.splitlines()
        dirty = [ln[3:] for ln in lines if len(ln) > 3 and not ln.startswith("??")]
        untracked = [ln[3:] for ln in lines if ln.startswith("??")]
        if dirty:
            findings.append({"check": "worktree", "status": "WARN",
                             "detail": f"미커밋 변경 {len(dirty)} 개: {', '.join(dirty[:5])}"})
        else:
            findings.append({"check": "worktree", "status": "PASS", "detail": "작업트리 변경 없음"})
        if untracked:
            findings.append({"check": "untracked", "status": "INFO",
                             "detail": f"추적되지 않은 파일 {len(untracked)} 개: {', '.join(untracked[:5])}"})
        else:
            findings.append({"check": "untracked", "status": "PASS", "detail": "추적되지 않은 파일 없음"})
    else:
        findings.append({"check": "git_repo", "status": "FAIL", "detail": f"Git 저장소가 아님: {ws}"})
        for check in ("protected_branch", "worktree", "untracked", "protected_file", "secret_files_tracked"):
            findings.append({"check": check, "status": "NOT_RUN", "detail": "Git 저장소 아님"})

    # 필수 문서
    for doc in config.get("required_documents", []):
        if (ws / doc).is_file():
            findings.append({"check": f"required_document:{doc}", "status": "PASS",
                             "detail": f"필수 문서 존재: {doc}"})
        else:
            findings.append({"check": f"required_document:{doc}", "status": "FAIL",
                             "detail": f"필수 문서 누락: {doc}"})
    if not config.get("required_documents"):
        findings.append({"check": "required_document", "status": "INFO", "detail": "필수 문서 미설정"})

    if git_ok:
        changed = [ln[3:] for ln in porcelain.splitlines() if len(ln) > 3]
        for pf in config.get("protected_files", []):
            if not (ws / pf).is_file():
                findings.append({"check": f"protected_file:{pf}", "status": "FAIL",
                                 "detail": f"보호 파일이 존재하지 않음: {pf}"})
            elif pf in changed:
                findings.append({"check": f"protected_file:{pf}", "status": "FAIL",
                                 "detail": f"보호 파일이 변경됨: {pf}"})
            else:
                findings.append({"check": f"protected_file:{pf}", "status": "PASS",
                                 "detail": f"보호 파일 변경 없음: {pf}"})
        if not config.get("protected_files"):
            findings.append({"check": "protected_file", "status": "INFO", "detail": "보호 파일 미설정"})

        tracked = run_git(ws, ["ls-files"]).splitlines()
        patterns = config.get("secret_files", [])
        matched = sorted({
            f for f in tracked
            if any(fnmatch.fnmatch(f, p) or fnmatch.fnmatch(f.lower(), p.lower()) for p in patterns)
        })
        if matched:
            findings.append({"check": "secret_files_tracked", "status": "FAIL",
                             "detail": f"시크릿 파일이 Git 에 추적됨: {', '.join(matched)}"})
        else:
            findings.append({"check": "secret_files_tracked", "status": "PASS",
                             "detail": "시크릿 패턴 파일이 추적되지 않음"})

    # 실행 환경
    findings.append({"check": "environment", "status": "INFO",
                     "detail": f"Python {platform.python_version()} / {platform.system()}"})

    def _tool_exists(command: str) -> bool:
        parts = command.split()
        return bool(parts) and shutil.which(parts[0]) is not None

    test_cmd = config.get("test_command", "")
    if test_cmd:
        if _tool_exists(test_cmd):
            findings.append({"check": "test_tool", "status": "PASS", "detail": f"테스트 도구 존재: {test_cmd}"})
        else:
            findings.append({"check": "test_tool", "status": "WARN", "detail": f"테스트 도구를 찾을 수 없음: {test_cmd}"})
    else:
        findings.append({"check": "test_tool", "status": "INFO", "detail": "테스트 명령 미설정"})

    for cmd in config.get("verify_commands", []):
        if _tool_exists(cmd):
            findings.append({"check": f"verify_tool:{cmd}", "status": "PASS", "detail": f"검증 도구 존재: {cmd}"})
        else:
            findings.append({"check": f"verify_tool:{cmd}", "status": "WARN", "detail": f"검증 도구를 찾을 수 없음: {cmd}"})
    if not config.get("verify_commands"):
        findings.append({"check": "verify_tool", "status": "INFO", "detail": "검증 명령 미설정"})

    # 설정 유효성
    source = str(config_path) if config_path else str(find_config(ws) or "defaults")
    if config_error:
        findings.append({"check": "config_valid", "status": "FAIL", "detail": config_error})
    elif unknown_keys:
        findings.append({"check": "config_valid", "status": "WARN",
                         "detail": f"알 수 없는 설정 키 (오타 가능성): {', '.join(unknown_keys)} (source: {source})"})
    else:
        findings.append({"check": "config_valid", "status": "PASS", "detail": f"설정 유효 (source: {source})"})

    # 위험 등급
    findings.append({"check": "risk_level", "status": "INFO", "detail": f"위험 등급: {config.get('risk_level')}"})

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
    parser = argparse.ArgumentParser(prog="preflight", description="프로젝트 수정 전 위험 경계 확인")
    parser.add_argument("--config", default=None, help="설정 파일 경로 (기본: .ai-standard.json/.yml/.yaml 자동 탐색)")
    parser.add_argument("--workspace", default=None, help="작업 저장소 경로 (기본: 현재 디렉터리)")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
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
