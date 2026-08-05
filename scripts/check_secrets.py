"""check_secrets.py — Phase 3: 시크릿 원문을 출력하지 않는 탐지 도구.

용법:
  python scripts/check_secrets.py [--workspace PATH] [--path FILE_OR_DIR ...]
                                  [--git-diff] [--config PATH] [--json]

검사 대상:
  - 소스 파일, 설정 파일, 로그, 테스트 결과, 빌드 산출물(텍스트)
  - 압축 파일 내부의 텍스트 항목 (.zip, .tar, .tar.gz, .tgz)
  - Git diff 의 추가된 줄 (--git-diff)

원칙:
  - 실제 시크릿 값을 절대 출력하지 않는다. 파일·줄·패턴 종류·심각도·마스킹된 일부 문자열만 출력한다.
  - HIGH → FAIL, MEDIUM → WARN.
  - 예외는 프로젝트 설정(.ai-standard)의 allow_exceptions 로만 허용한다.
    형식: "파일:패턴:허용이유[:만료조건]" (파일·패턴은 * 와일드카드 지원)
  - 테스트에는 synthetic token 만 사용한다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tarfile
import zipfile
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
    run_git,
)

# 패턴 정의: id -> (regex, severity)
# severity: HIGH(FAIL) / MEDIUM(WARN)
_PATTERNS: list[tuple[str, str, str]] = [
    ("aws_access_key", r"\bAKIA[0-9A-Z]{16}\b", "HIGH"),
    ("google_api_key", r"\bAIza[0-9A-Za-z_-]{35}\b", "HIGH"),
    ("github_token", r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b", "HIGH"),
    ("slack_token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "HIGH"),
    ("openai_key", r"\bsk-ant-[A-Za-z0-9_-]{16,}\b|\bsk-[A-Za-z0-9_-]{20,}\b", "HIGH"),
    ("stripe_key", r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b", "HIGH"),
    ("slack_webhook", r"hooks\.slack\.com/services/[A-Z0-9]+/[A-Z0-9]+", "MEDIUM"),
    ("discord_webhook", r"discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]{16,}", "MEDIUM"),
    ("jwt_token", r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b", "MEDIUM"),
    ("authorization", r"(?i)authorization\s*[:=]\s*(?:basic|bearer)\s+\S+", "MEDIUM"),
    ("password", r"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*[\"'][^\"']{4,}[\"']", "MEDIUM"),
    ("api_key", r"(?i)\b(?:api[_-]?key|secret[_-]?key|client[_-]?secret|access[_-]?key|"
                r"token|webhook)\s*[:=]\s*[\"'][^\"']{8,}[\"']", "MEDIUM"),
]

_COMPILED = [(pid, re.compile(regex), sev) for pid, regex, sev in _PATTERNS]

# 다중줄(블록) 패턴: 개인키는 BEGIN~END 블록 전체를 탐지해야
# 단일 줄에 등장하는 문서용 샘플 문자열(BEGIN 만 있는 줄)과 구분된다.
_BLOCK_PATTERNS: list[tuple[str, str, str]] = [
    ("private_key",
     r"-----BEGIN [A-Z ]*PRIVATE KEY-----.{0,4096}?-----END [A-Z ]*PRIVATE KEY-----",
     "HIGH"),
]
_BLOCK_COMPILED = [
    (pid, re.compile(regex, re.DOTALL | re.IGNORECASE), sev)
    for pid, regex, sev in _BLOCK_PATTERNS
]


def mask_match(pattern_id: str, match_text: str) -> str:
    """매칭된 문자열을 마스킹한다. 원문은 반환하지 않는다."""
    if pattern_id == "private_key":
        return "-----BEGIN PRIVATE KEY----- (block masked)"
    if pattern_id == "authorization":
        return "authorization: ***"
    value = mask_sensitive(match_text)
    value = value.strip()
    if not value:
        return "***"
    if len(value) <= 6:
        return "***"
    return value[:4] + "***"


def scan_text(text: str, path: str, parsed_exceptions: list[tuple[str, str, str, str]]
              ) -> list[Finding]:
    findings: list[Finding] = []
    # 다중줄 패턴(개인키 블록)은 전체 텍스트에서 먼저 검사한다
    for pid, regex, sev in _BLOCK_COMPILED:
        for m in regex.finditer(text):
            lineno = text.count("\n", 0, m.start()) + 1
            status = "EXCEPTED" if is_excepted(path, pid, parsed_exceptions) else sev
            findings.append(
                Finding(path, lineno, pid, sev, mask_match(pid, m.group(0)), status)
            )
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\r\n")
        for pid, regex, sev in _COMPILED:
            m = regex.search(line)
            if m is None:
                continue
            status = "EXCEPTED" if is_excepted(path, pid, parsed_exceptions) else sev
            findings.append(
                Finding(path, lineno, pid, sev, mask_match(pid, m.group(0)), status)
            )
    return findings


def scan_file(path: Path, rel: str, parsed_exceptions: list[tuple[str, str, str, str]]
              ) -> list[Finding]:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return []
        data = path.read_bytes()
    except OSError:
        return []
    if looks_binary(data):
        return []
    text = data.decode("utf-8", errors="replace")
    return scan_text(text, rel, parsed_exceptions)


def scan_archive(path: Path, rel: str, parsed_exceptions: list[tuple[str, str, str, str]]
                 ) -> list[Finding]:
    findings: list[Finding] = []
    suffix = path.suffix.lower()
    try:
        if suffix == ".zip":
            with zipfile.ZipFile(path) as zf:
                for info in zf.infolist():
                    if info.is_dir() or info.file_size > MAX_FILE_BYTES:
                        continue
                    data = zf.read(info)
                    _scan_archive_member(data, f"{rel}!{info.filename}", parsed_exceptions, findings)
        elif suffix in (".tar", ".tgz") or path.name.lower().endswith(".tar.gz"):
            with tarfile.open(path) as tf:
                for member in tf.getmembers():
                    if not member.isfile() or member.size > MAX_FILE_BYTES:
                        continue
                    fh = tf.extractfile(member)
                    if fh is None:
                        continue
                    data = fh.read()
                    _scan_archive_member(data, f"{rel}!{member.name}", parsed_exceptions, findings)
    except (zipfile.BadZipFile, tarfile.TarError, OSError):
        pass
    return findings


def _scan_archive_member(data: bytes, member_path: str,
                         parsed_exceptions: list[tuple[str, str, str, str]],
                         findings: list[Finding]) -> None:
    if looks_binary(data):
        return
    text = data.decode("utf-8", errors="replace")
    findings.extend(scan_text(text, member_path, parsed_exceptions))


def scan_git_diff(workspace: Path, parsed_exceptions: list[tuple[str, str, str, str]]
                  ) -> list[Finding]:
    findings: list[Finding] = []
    for args in (["diff"], ["diff", "--cached"]):
        try:
            diff = run_git(workspace, args, check=False)
        except Exception:
            continue
        current = "git-diff"
        for lineno, raw in enumerate(diff.splitlines(), start=1):
            if raw.startswith("+++ b/"):
                current = f"git-diff:{raw[6:]}"
            elif raw.startswith("+") and not raw.startswith("+++"):
                line = raw[1:]
                for pid, regex, sev in _COMPILED:
                    m = regex.search(line)
                    if m is None:
                        continue
                    status = "EXCEPTED" if is_excepted(current, pid, parsed_exceptions) else sev
                    findings.append(
                        Finding(current, lineno, pid, sev, mask_match(pid, m.group(0)), status)
                    )
    return findings


def run_scan(workspace: Path, paths: list[str], git_diff: bool,
             exceptions: list[str]) -> dict[str, Any]:
    root = resolve_workspace(workspace)
    parsed, _ = parse_exception_entries(exceptions)
    findings: list[Finding] = []
    # 지정된 경로가 없으면 검사하지 못한 것이다. 조용히 건너뛰면 오타 하나로
    # "0건 탐지 → PASS" 가 되므로 명시적으로 실패시킨다.
    for raw in missing_scan_paths(root, paths):
        findings.append(Finding(raw, 0, "missing_scan_path", "HIGH",
                                "specified path does not exist, could not be scanned", "HIGH"))
    for file_path in collect_files(root, paths):
        rel = str(file_path.relative_to(root)) if file_path.is_relative_to(root) else str(file_path)
        if file_path.suffix.lower() in (".zip", ".tar", ".tgz") or file_path.name.lower().endswith(".tar.gz"):
            findings.extend(scan_archive(file_path, rel, parsed))
        else:
            findings.extend(scan_file(file_path, rel, parsed))
    if git_diff:
        findings.extend(scan_git_diff(root, parsed))

    fail = [f for f in findings if f.status == "HIGH"]
    warn = [f for f in findings if f.status == "MEDIUM"]
    excepted = [f for f in findings if f.status == "EXCEPTED"]
    status = "FAIL" if fail else ("WARN" if warn else "PASS")
    return {
        "status": status,
        "findings": [f.to_dict() for f in findings],
        "summary": {
            "fail": len(fail),
            "warn": len(warn),
            "excepted": len(excepted),
        },
    }


def load_exceptions(workspace: Path, config_path: str | None) -> tuple[list[str], str | None]:
    """프로젝트 설정의 allow_exceptions 를 읽는다. (exceptions, 경고메시지)"""
    try:
        from preflight import find_config, load_config
    except ImportError:
        return [], None
    path = Path(config_path) if config_path else find_config(workspace)
    if path is None:
        return [], None
    config, error, _ = load_config(workspace, config_path)
    if error:
        return [], f"config error (proceeding with defaults): {error}"
    return list(config.get("allow_exceptions", [])), None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="check_secrets", description="Detect secrets without exposing raw values")
    parser.add_argument("--workspace", default=None, help="workspace path (default: current directory)")
    parser.add_argument("--path", action="append", default=[], help="file/directory to scan (repeatable)")
    parser.add_argument("--git-diff", action="store_true", help="also scan added lines in the Git diff")
    parser.add_argument("--config", default=None, help="config file path")
    parser.add_argument("--json", action="store_true", help="output as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_io()
    args = build_parser().parse_args(argv)
    workspace = resolve_workspace(args.workspace)
    exceptions, warning = load_exceptions(workspace, args.config)
    if warning:
        print(f"[WARN ] {warning}", file=sys.stderr)
    _, malformed = parse_exception_entries(exceptions)
    for entry in malformed:
        print(f"[WARN ] malformed exception entry (ignored, expected 'file:pattern:reason[:expiry]'): {entry}",
              file=sys.stderr)
    report = run_scan(workspace, args.path, args.git_diff, exceptions)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"check_secrets: {report['status']}  "
              f"(fail: {report['summary']['fail']}, warn: {report['summary']['warn']}, "
              f"excepted: {report['summary']['excepted']})")
        for f in report["findings"]:
            print(f"  [{f['status']:<6}] {f['pattern']} ({f['severity']}): "
                  f"{f['path']}:{f['line']} -> {f['masked']}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
