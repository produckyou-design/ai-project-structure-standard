"""common.py — Phase 1 공통 유틸리티 (단일 소유 모듈).

모든 스크립트가 재사용하는 공통 기능을 제공한다.
- Git 상태 조회 (브랜치, HEAD, status, diff, 변경 파일)
- SHA-256 해시
- append-only JSONL ledger (.ai/ledger.jsonl)
- 시크릿 마스킹 (원문 미출력)
- 실제 모델 ID 결정 (확인 불가 시 UNKNOWN)

책임 경계: 도구 공통 I/O와 순수 계산만 담당한다.
"""
from __future__ import annotations

from fnmatch import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    """UTC ISO-8601 문자열 (초 단위)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(text: str) -> str:
    """텍스트의 SHA-256 헥스 다이제스트."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """파일 내용의 SHA-256 헥스 다이제스트."""
    return sha256(path.read_text(encoding="utf-8", errors="replace"))


# ---------- Git ----------


class GitError(RuntimeError):
    pass


def run_git(workspace: Path, args: list[str], check: bool = True) -> str:
    """workspace에서 git 명령을 실행하고 stdout을 반환한다.

    비ASCII 경로를 깨지 않도록 core.quotepath=false 를 적용한다.
    """
    try:
        # git for Windows 는 경로를 UTF-8 로 출력하므로 encoding 을 명시한다
        result = subprocess.run(
            ["git", "-c", "core.quotepath=false", *args],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise GitError(f"git 실행 실패 (워크스페이스 확인 필요): {exc}") from exc
    if check and result.returncode != 0:
        raise GitError(f"git {' '.join(args)} 실패: {result.stderr.strip()}")
    # porcelain 의 선행 공백(XY 상태 코드 이전)을 보존해야 하므로 strip() 대신 줄바꿈만 제거
    return result.stdout.rstrip("\r\n")


def is_git_repo(workspace: Path) -> bool:
    try:
        return run_git(workspace, ["rev-parse", "--is-inside-work-tree"]) == "true"
    except GitError:
        return False


def repo_root(workspace: Path) -> Path:
    return Path(run_git(workspace, ["rev-parse", "--show-toplevel"]))


def git_branch(workspace: Path) -> str:
    """현재 브랜치 이름.

    커밋이 하나도 없는(unborn) 브랜치에서는 rev-parse 가 실패한다. 이때 'N/A' 로
    두면 preflight 의 protected branch 검사가 조용히 통과해버리므로
    (실제로는 main/master 위에 있는데도), symbolic-ref 로 실제 이름을 읽는다.
    """
    try:
        branch = run_git(workspace, ["rev-parse", "--abbrev-ref", "HEAD"])
    except GitError:
        branch = ""
    if branch and branch != "HEAD":
        return branch
    try:
        symbolic = run_git(workspace, ["symbolic-ref", "--short", "HEAD"])
    except GitError:
        symbolic = ""
    if symbolic:
        return symbolic
    return "HEAD (detached)" if branch == "HEAD" else "N/A"


def git_head(workspace: Path) -> str:
    """HEAD 커밋 해시. 커밋이 없으면 'NONE'."""
    try:
        return run_git(workspace, ["rev-parse", "HEAD"]) or "NONE"
    except GitError:
        return "NONE"


def git_status_porcelain(workspace: Path) -> str:
    return run_git(workspace, ["status", "--porcelain"])


def git_status_hash(workspace: Path) -> str:
    """작업트리 상태의 해시. CLEAN이면 빈 문자열의 해시."""
    return sha256(git_status_porcelain(workspace))


def git_diff(workspace: Path) -> str:
    """워킹트리와 인덱스 간 diff (git diff)."""
    return run_git(workspace, ["diff"])


def git_diff_hash(workspace: Path) -> str:
    return sha256(git_diff(workspace))


def _porcelain_paths(workspace: Path) -> list[str]:
    return [line[3:] for line in git_status_porcelain(workspace).splitlines() if len(line) > 3]


def changed_files(workspace: Path) -> list[str]:
    return _porcelain_paths(workspace)


def untracked_files(workspace: Path) -> list[str]:
    return [line[3:] for line in git_status_porcelain(workspace).splitlines() if line.startswith("??")]


def deleted_files(workspace: Path) -> list[str]:
    # porcelain 형식은 'XY PATH'. X=인덱스, Y=워킹트리 상태. 삭제는 X 또는 Y 중 하나가 D
    return [
        line[3:]
        for line in git_status_porcelain(workspace).splitlines()
        if len(line) > 3 and (line[0] == "D" or line[1] == "D")
    ]


# ---------- ledger (append-only JSONL) ----------


def ledger_path(workspace: Path) -> Path:
    return repo_root(workspace) / ".ai" / "ledger.jsonl"


def read_ledger(workspace: Path) -> list[dict]:
    path = ledger_path(workspace)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def _entry_digest(body: dict) -> str:
    """entry_hash 필드를 제외한 본문의 정규 JSON 해시."""
    canonical = json.dumps(
        {k: v for k, v in body.items() if k != "entry_hash"},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical)


def verify_ledger_chain(entries: list[dict]) -> tuple[bool, str]:
    """ledger 전체의 해시 체인을 재계산해 검증한다. (ok, 사유) 를 반환한다.

    두 가지를 모두 확인한다.
      1. 자기 무결성 — 각 항목의 entry_hash 가 그 항목 본문의 해시와 일치하는가
      2. 연결 무결성 — previous_entry_hash 가 직전 항목의 entry_hash 와 이어지는가

    마지막 항목만 검사하면, 중간 항목을 고친 뒤 그 항목의 entry_hash 만 다시
    계산해 자기 무결성을 위장할 수 있다 (연결만 끊어진 채 통과). 그래서 전
    항목을 처음부터 재계산한다.
    """
    previous = ""
    for index, entry in enumerate(entries):
        if _entry_digest(entry) != entry.get("entry_hash", ""):
            return False, f"{index}번째 항목의 entry_hash 가 내용과 일치하지 않습니다"
        if entry.get("previous_entry_hash", "") != previous:
            return False, f"{index}번째 항목의 previous_entry_hash 가 직전 항목과 이어지지 않습니다"
        previous = entry.get("entry_hash", "")
    return True, ""


def append_ledger(workspace: Path, entry: dict) -> dict:
    """ledger에 append-only로 기록하고 해시를 채운 뒤 반환한다.

    - 이전 항목의 entry_hash를 previous_entry_hash로 연결한다.
    - entry_hash는 자기 자신(entry_hash 필드 제외)의 정규 JSON 해시다.
    - 기존 항목은 절대 수정하지 않는다.
    - append 전에 기존 항목 전체의 해시 체인을 재계산해 변조를 탐지하면 거부한다.
    """
    entries = read_ledger(workspace)
    if entries:
        chain_ok, reason = verify_ledger_chain(entries)
        if not chain_ok:
            raise GitError(
                f"ledger 무결성 위반: {reason}. append 를 거부합니다 (변조 가능성)."
            )
    previous_hash = entries[-1].get("entry_hash", "") if entries else ""
    body = {k: v for k, v in entry.items() if k != "entry_hash"}
    body["previous_entry_hash"] = previous_hash
    body["entry_hash"] = _entry_digest(body)
    path = ledger_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n")
    return body


# ---------- 시크릿 마스킹 ----------
# check_secrets.py 의 탐지 패턴 상위집합을 유지한다 (마스킹 단일 소유).
# 새 패턴을 추가할 때는 check_secrets._PATTERNS 와 함께 갱신한다.
_SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)sk-[A-Za-z0-9_-]{8,}"), "sk-***"),
    (re.compile(r"(?i)sk-ant-[A-Za-z0-9_-]{16,}"), "sk-ant-***"),
    (re.compile(r"(?i)\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b"), "sk_live_***"),
    (re.compile(r"(?i)ghp_[A-Za-z0-9]{20,}"), "ghp_***"),
    (re.compile(r"(?i)github_pat_[A-Za-z0-9_]{20,}"), "github_pat_***"),
    (re.compile(r"(?i)AKIA[0-9A-Z]{16}"), "AKIA***"),
    (re.compile(r"(?i)\bAIza[0-9A-Za-z_-]{35}\b"), "AIza***"),
    (re.compile(r"(?i)xox[baprs]-[A-Za-z0-9-]{10,}"), "xox***"),
    (re.compile(r"(?i)\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "eyJ***"),
    (re.compile(r"(?i)hooks\.slack\.com/services/[A-Z0-9]+/[A-Z0-9]+"), "hooks.slack.com/services/***"),
    (re.compile(r"(?i)discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]{16,}"),
     "discord.com/api/webhooks/***"),
    (re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
     "-----BEGIN PRIVATE KEY----- (마스킹됨)"),
    (re.compile(r"(?i)authorization\s*[:=]\s*\S+"), "authorization: ***"),
    (re.compile(
        r"(?i)((?:password|passwd|pwd|secret(?:[_-]?key)?|client[_-]?secret|app[_-]?secret|"
        r"token|api[_-]?key|access[_-]?key)\s*[:=]\s*)\S+"),
     r"\1***"),
]


def mask_sensitive(text: str) -> str:
    """민감정보 패턴을 마스킹한 문자열을 반환한다. 원문을 출력하지 않는다."""
    masked = text
    for pattern, repl in _SECRET_PATTERNS:
        masked = pattern.sub(repl, masked)
    return masked


def mask_value(value: Any) -> Any:
    """딕셔너리/리스트/문자열을 재귀적으로 마스킹한다."""
    if isinstance(value, str):
        return mask_sensitive(value)
    if isinstance(value, dict):
        return {k: mask_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [mask_value(v) for v in value]
    return value


# ---------- 실제 모델 ID ----------

MODEL_ID_ENV_KEYS = ("AI_ACTUAL_MODEL_ID", "ACTUAL_MODEL_ID", "FREEBUFF_MODEL_ID")


def resolve_actual_model_id() -> str:
    """실제 모델 ID를 확인할 수 없으면 UNKNOWN을 기록한다.

    자체 신고를 검증된 모델 ID로 단정하지 않는다.
    환경변수로 명시된 경우에만 실제 모델 ID로 사용한다.
    """
    for key in MODEL_ID_ENV_KEYS:
        value = os.environ.get(key)
        if value and value.strip():
            return value.strip()
    return "UNKNOWN"


def resolve_workspace(value: str | None) -> Path:
    return Path(value or os.getcwd()).resolve()


# ---------- 검사 도구 공통 (Phase 3) ----------

MAX_FILE_BYTES = 4 * 1024 * 1024  # 4MB 초과 파일/압축 멤버는 건너뛴다


class Finding:
    """검사 도구(check_secrets/check_forbidden_patterns) 공통 결과 항목."""

    __slots__ = ("path", "line", "pattern", "severity", "masked", "status")

    def __init__(self, path: str, line: int, pattern: str, severity: str,
                 masked: str, status: str):
        self.path = path
        self.line = line
        self.pattern = pattern
        self.severity = severity
        self.masked = masked
        self.status = status

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "line": self.line,
            "pattern": self.pattern,
            "severity": self.severity,
            "masked": self.masked,
            "status": self.status,
        }


def parse_exception_entries(exceptions: list[str]) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """예외 항목을 파싱한다.

    형식: "파일:패턴:허용이유[:만료조건]" (파일·패턴은 * 와일드카드 허용).
    반환: (entries, malformed) — malformed 는 형식이 잘못된 원본 항목.
    """
    entries: list[tuple[str, str, str, str]] = []
    malformed: list[str] = []
    for entry in exceptions:
        parts = entry.split(":", 3)
        if len(parts) < 3 or not parts[0] or not parts[1]:
            malformed.append(entry)
            continue
        file_pat, pattern_pat, reason = parts[0], parts[1], parts[2]
        expiry = parts[3] if len(parts) > 3 else ""
        entries.append((file_pat, pattern_pat, reason, expiry))
    return entries, malformed


def is_excepted(path: str, pattern_id: str, parsed: list[tuple[str, str, str, str]]) -> bool:
    """파싱된 예외 목록에서 (path, pattern_id) 가 허용되는지 판정한다.

    패턴은 id 전체(fnmatch) 또는 부분 문자열로도 일치한다.
    """
    for file_pat, pattern_pat, _reason, _expiry in parsed:
        if fnmatch(path, file_pat) and (
            fnmatch(pattern_id, pattern_pat) or pattern_pat.lower() in pattern_id.lower()
        ):
            return True
    return False


def looks_binary(data: bytes) -> bool:
    """NUL 바이트를 포함하면 바이너리로 간주한다."""
    return b"\x00" in data[:8192]


def _is_excluded_scan_path(rel_parts: tuple[str, ...]) -> bool:
    """.git 하위와 .ai/verification_logs 하위를 스캔에서 제외한다.

    .ai/verification_logs 는 verify_project.py 가 검사기(check_secrets.py /
    check_forbidden_patterns.py) 실행 결과를 그대로 로그로 남기는 위치다.
    그 로그 안에는 탐지된 패턴 이름과 원본 코드 컨텍스트가 문자열로 그대로
    적히므로, 이 디렉터리를 스캔 대상에 포함하면 검사기가 자기 자신의
    출력을 다시 탐지해 자기참조 오탐(false positive)을 일으킨다.
    이 표준을 쓰는 모든 프로젝트에서 재발하므로 프로젝트별 예외가 아니라
    수집 단계에서 구조적으로 제외한다.
    """
    if any(part == ".git" for part in rel_parts):
        return True
    for i in range(len(rel_parts) - 1):
        if rel_parts[i] == ".ai" and rel_parts[i + 1] == "verification_logs":
            return True
    return False


def missing_scan_paths(root: Path, given: list[str]) -> list[str]:
    """--path 로 지정됐지만 실제로 존재하지 않는 경로 목록.

    존재하지 않는 경로를 조용히 건너뛰면 오타 하나로 "검사 대상 0건 → PASS" 가
    되어 미실행이 통과로 둔갑한다. 호출자는 이 목록을 FAIL 로 보고해야 한다.
    """
    missing: list[str] = []
    for raw in given:
        candidate = Path(raw)
        candidate = candidate if candidate.is_absolute() else root / raw
        if not candidate.exists():
            missing.append(raw)
    return missing


def collect_files(root: Path, given: list[str]) -> list[Path]:
    """스캔할 파일 목록. .git 과 .ai/verification_logs 하위는 제외, 디렉터리는 재귀."""
    results: list[Path] = []
    bases = [Path(p) for p in given] if given else [root]
    for base in bases:
        base = base if base.is_absolute() else root / base
        if base.is_file():
            results.append(base)
        elif base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.is_file() and not _is_excluded_scan_path(p.relative_to(base).parts):
                    results.append(p)
    return results


def configure_utf8_io() -> None:
    """Windows 콘솔(cp949)에서 한글 출력이 깨지지 않도록 stdout/stderr 를 UTF-8 로 재구성한다."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
