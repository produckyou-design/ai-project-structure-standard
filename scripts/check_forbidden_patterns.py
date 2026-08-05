"""check_forbidden_patterns.py — Phase 3: 구조적 보안 금지 패턴 탐지.

용법:
  python scripts/check_forbidden_patterns.py [--workspace PATH] [--path FILE_OR_DIR ...]
                                            [--config PATH] [--json]

내장 금지 패턴 (정확한 정규식은 docs/SECURITY_STANDARD.md §2 참고):
  - shell 을 True 로 하는 명령 실행
  - eval / exec / os.system 호출
  - TLS 검증을 끄는 옵션
  - 모든 인터페이스 바인딩
  - 빈 except/예외 삼키기, 하드코딩 관리자 권한, 개발용 인증 우회
  - 사용자 입력 기반 프록시, 평문 비밀정보 fallback

프로젝트 설정(.ai-standard)에서 추가 패턴(forbidden_patterns)과
예외(allow_exceptions)를 지원한다.
예외 형식: "파일:패턴:허용이유[:만료조건]" — 파일·패턴은 * 와일드카드 허용.
모든 탐지를 무조건 오류로 처리하지 않는다. 예외가 있으면 EXCEPTED 로 기록한다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    Finding,
    MAX_FILE_BYTES,
    collect_files,
    configure_utf8_io,
    is_excepted,
    looks_binary,
    mask_sensitive,
    missing_scan_paths,
    parse_exception_entries,
    resolve_workspace,
)

# 내장 금지 패턴: id -> (regex, 심각도)
_DEFAULT_PATTERNS: list[tuple[str, str, str]] = [
    ("shell_true", r"shell\s*=\s*True", "HIGH"),
    ("eval_call", r"\beval\s*\(", "HIGH"),
    ("exec_call", r"\bexec\s*\(", "HIGH"),
    ("os_system", r"\bos\.system\s*\(", "HIGH"),
    ("verify_false", r"\bverify\s*=\s*False", "HIGH"),
    ("bind_all", r"0\.0\.0\.0", "MEDIUM"),
    ("empty_except", r"except\s*:\s*(?:pass|continue)?\s*$", "MEDIUM"),
    ("swallow_exception", r"except\s+[^:]+:\s*(?:pass|continue)\s*$", "MEDIUM"),
    ("hardcoded_admin", r"\b(?:is_admin|is_superuser)\s*=\s*True", "HIGH"),
    ("dev_auth_bypass", r"\b(?:bypass|skip)[_-]?(?:auth|login|verification)", "HIGH"),
    ("user_input_proxy", r"\bproxy\s*=\s*(?:input|raw_input|request)\s*\(", "MEDIUM"),
    ("plaintext_fallback", r"\bplaintext\s*(?:fallback|password|secret|token)", "HIGH"),
]


def _mask_context(line: str) -> str:
    masked = mask_sensitive(line).strip()
    return masked if len(masked) <= 80 else masked[:77] + "..."


def _is_empty_except(lines: list[str], idx: int, line: str) -> bool:
    """빈 except(예외 삼키기) 판정.

    - 같은 줄: "except: pass" / "except: continue"
    - 다음 코드 줄이 pass/continue 인 경우: "except:" 줄만 있고 다음 줄이 pass
    """
    if re.search(r"except\s*:\s*(?:pass|continue)\s*$", line):
        return True
    if re.search(r"except\s*:\s*$", line):
        nxt = next((l.strip() for l in lines[idx + 1:] if l.strip()), "")
        return nxt in ("pass", "continue")
    return False


def scan_text(text: str, path: str, patterns: list[tuple[str, re.Pattern, str]],
              parsed_exceptions: list[tuple[str, str, str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    for idx, raw in enumerate(lines):
        line = raw.rstrip("\r\n")
        for pid, regex, sev in patterns:
            if pid == "empty_except":
                if _is_empty_except(lines, idx, line):
                    status = "EXCEPTED" if is_excepted(path, pid, parsed_exceptions) else "FAIL"
                    findings.append(Finding(path, idx + 1, pid, sev, _mask_context(line), status))
                continue
            if regex.search(line) is None:
                continue
            status = "EXCEPTED" if is_excepted(path, pid, parsed_exceptions) else "FAIL"
            findings.append(
                Finding(path, idx + 1, pid, sev, _mask_context(line), status)
            )
    return findings


def scan_file(path: Path, rel: str, patterns: list[tuple[str, re.Pattern, str]],
              parsed_exceptions: list[tuple[str, str, str, str]]) -> list[Finding]:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return []
        data = path.read_bytes()
    except OSError:
        return []
    if looks_binary(data):
        return []
    return scan_text(data.decode("utf-8", errors="replace"), rel, patterns, parsed_exceptions)


def _compile_patterns(patterns: list[tuple[str, str, str]],
                      findings: list[Finding], path: str) -> list[tuple[str, re.Pattern, str]]:
    """패턴을 컴파일한다. 잘못된 정규식은 finding 으로 기록하고 건너뛴다."""
    compiled: list[tuple[str, re.Pattern, str]] = []
    for pid, regex, sev in patterns:
        if pid == "empty_except":
            # 특수 처리되는 패턴: 컴파일하지 않고 배치한다
            compiled.append((pid, re.compile(r"(?!)"), sev))
            continue
        try:
            compiled.append((pid, re.compile(regex), sev))
        except re.error as exc:
            findings.append(
                Finding(path, 0, f"invalid_pattern:{pid}", "HIGH",
                        f"regex compile failed: {exc}", "FAIL")
            )
    return compiled


def run_scan(workspace: Path, paths: list[str], config: dict[str, Any] | None) -> dict[str, Any]:
    root = resolve_workspace(workspace)
    cfg = config or {}
    patterns = list(_DEFAULT_PATTERNS)
    for extra in cfg.get("forbidden_patterns", []):
        if isinstance(extra, str) and extra.strip():
            patterns.append((f"config:{extra}", extra, "MEDIUM"))
    parsed, _ = parse_exception_entries(
        [e for e in cfg.get("allow_exceptions", []) if isinstance(e, str)]
    )

    findings: list[Finding] = []
    compiled = _compile_patterns(patterns, findings, "<config>")
    # 지정된 경로가 없으면 검사하지 못한 것이다. 조용히 건너뛰면 오타 하나로
    # "0건 탐지 → PASS" 가 되므로 명시적으로 실패시킨다.
    for raw in missing_scan_paths(root, paths):
        findings.append(Finding(raw, 0, "missing_scan_path", "HIGH",
                                "specified path does not exist, could not be scanned", "FAIL"))
    for file_path in collect_files(root, paths):
        rel = str(file_path.relative_to(root)) if file_path.is_relative_to(root) else str(file_path)
        findings.extend(scan_file(file_path, rel, compiled, parsed))

    fail = [f for f in findings if f.status == "FAIL"]
    excepted = [f for f in findings if f.status == "EXCEPTED"]
    return {
        "status": "FAIL" if fail else "PASS",
        "findings": [f.to_dict() for f in findings],
        "summary": {"fail": len(fail), "excepted": len(excepted)},
    }


def load_config_data(workspace: Path, config_path: str | None) -> tuple[dict[str, Any] | None, str | None]:
    try:
        from preflight import find_config, load_config
    except ImportError:
        return None, None
    path = Path(config_path) if config_path else find_config(workspace)
    if path is None:
        return None, None
    config, error, _ = load_config(workspace, config_path)
    if error:
        return None, f"config error (proceeding with defaults): {error}"
    return config, None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="check_forbidden_patterns", description="Detect structural-security forbidden patterns")
    parser.add_argument("--workspace", default=None, help="workspace path (default: current directory)")
    parser.add_argument("--path", action="append", default=[], help="file/directory to scan (repeatable)")
    parser.add_argument("--config", default=None, help="config file path")
    parser.add_argument("--json", action="store_true", help="output as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_io()
    args = build_parser().parse_args(argv)
    workspace = resolve_workspace(args.workspace)
    config, warning = load_config_data(workspace, args.config)
    if warning:
        print(f"[WARN ] {warning}", file=sys.stderr)
    exceptions = [e for e in (config or {}).get("allow_exceptions", []) if isinstance(e, str)]
    _, malformed = parse_exception_entries(exceptions)
    for entry in malformed:
        print(f"[WARN ] malformed exception entry (ignored, expected 'file:pattern:reason[:expiry]'): {entry}",
              file=sys.stderr)
    report = run_scan(workspace, args.path, config)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"check_forbidden_patterns: {report['status']}  "
              f"(fail: {report['summary']['fail']}, excepted: {report['summary']['excepted']})")
        for f in report["findings"]:
            print(f"  [{f['status']:<6}] {f['pattern']} ({f['severity']}): "
                  f"{f['path']}:{f['line']} -> {f['masked']}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
