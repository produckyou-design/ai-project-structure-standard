"""check_document_sync.py — Phase 5: 기계 판정 가능한 문서 정합성 검사.

용법:
  python scripts/check_document_sync.py [--config PATH] [--workspace PATH] [--json]

검사 항목 (기계적으로 검증 가능한 핵심 불일치만):
  - README 에 적힌 스크립트·스키마·템플릿 경로가 실제 존재하는지
  - 설정의 필수 문서(required_documents)가 존재하는지
  - 설정의 verify_commands / test_command 가 비어 있지 않은지
  - CURRENT 와 STATUS 가 모순되는지 (STATUS 에 FAIL 이 있는데 CURRENT 블로커가 '없음')
  - STATUS 의 PASS 항목에 근거(증적) 칸이 채워져 있는지
  - 코드에서 쓰는 오류 코드가 프로젝트 ERROR_CATALOG 에 등록됐는지 (카탈로그가 있을 때만)

모든 자연어 문서 내용을 판정하려 하지 않는다.

CURRENT.md 의 "## 블로커"/"없음" 표기는 templates/ 관례(한국어)를 그대로 검사한다 —
이 검사 로직 자체는 CLI 출력 번역과 무관하게 유지한다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import configure_utf8_io, resolve_workspace  # noqa: E402
from preflight import load_config  # noqa: E402

# README 안의 저장소 상대 경로 (백틱/괄호 안 포함)
_PATH_REF = re.compile(
    r"\b((?:scripts|schemas|templates|docs|examples|tests)/[A-Za-z0-9_./\-]+\.(?:py|json|md|ya?ml|txt))\b"
)
# 소스 코드 안의 표준 오류 코드 리터럴 ("APP-AUTH-TOKEN-401" 형태)
_ERROR_CODE = re.compile(r"[\"']([A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,})[\"']")
# 3칸 이상 표의 행: | 항목 | 상태 | 근거 |
_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
_CODE_FILE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", ".cs", ".rb", ".swift"}
_CATALOG_LOCATIONS = ("ERROR_CATALOG.md", "docs/ERROR_CATALOG.md")


def _check_readme_references(ws: Path) -> list[dict]:
    readme = ws / "README.md"
    if not readme.is_file():
        return [{"check": "readme_references", "status": "NOT_RUN", "detail": "README.md not found"}]
    findings = []
    missing = []
    refs = sorted(set(_PATH_REF.findall(readme.read_text(encoding="utf-8", errors="replace"))))
    for ref in refs:
        if not (ws / ref).exists():
            missing.append(ref)
    if missing:
        findings.append({"check": "readme_references", "status": "FAIL",
                         "detail": f"README references path(s) that don't exist: {', '.join(missing[:10])}"})
    else:
        findings.append({"check": "readme_references", "status": "PASS",
                         "detail": f"all {len(refs)} README-referenced path(s) exist"})
    return findings


def _check_required_documents(ws: Path, config: dict) -> list[dict]:
    required = config.get("required_documents", [])
    if not required:
        return [{"check": "required_documents", "status": "NOT_RUN", "detail": "no required_documents configured"}]
    missing = [doc for doc in required if not (ws / doc).is_file()]
    if missing:
        return [{"check": "required_documents", "status": "FAIL",
                 "detail": f"required document(s) missing: {', '.join(missing)}"}]
    return [{"check": "required_documents", "status": "PASS",
             "detail": f"all {len(required)} required document(s) exist"}]


def _check_config_commands(config: dict, config_error: str | None) -> list[dict]:
    if config_error:
        return [{"check": "config_commands", "status": "FAIL", "detail": f"config error: {config_error}"}]
    empty = [i for i, c in enumerate(config.get("verify_commands", [])) if not str(c).strip()]
    if empty:
        return [{"check": "config_commands", "status": "FAIL",
                 "detail": f"verify_commands has empty command(s) (index: {empty})"}]
    return [{"check": "config_commands", "status": "PASS",
             "detail": "config commands are non-empty"}]


def _check_current_status_consistency(ws: Path) -> list[dict]:
    current = ws / ".ai" / "CURRENT.md"
    status = ws / ".ai" / "STATUS.md"
    if not current.is_file() and not status.is_file():
        return [{"check": "current_status", "status": "NOT_RUN", "detail": ".ai/CURRENT.md and STATUS.md not found"}]
    if current.is_file() != status.is_file():
        missing = "STATUS.md" if current.is_file() else "CURRENT.md"
        return [{"check": "current_status", "status": "FAIL",
                 "detail": f"only .ai/{missing} is missing (the pair should be kept together)"}]
    status_text = status.read_text(encoding="utf-8", errors="replace")
    current_text = current.read_text(encoding="utf-8", errors="replace")
    # 표 셀에 FAIL 이 기록되어 있는데 CURRENT 블로커가 '없음'이면 모순
    has_fail_cell = any(
        re.search(r"\|\s*FAIL\s*(\(|\|)", line) for line in status_text.splitlines()
    )
    blocker_match = re.search(r"##\s*블로커\s*\n+([^\n#]*)", current_text)
    blocker_none = bool(blocker_match and "없음" in blocker_match.group(1))
    if has_fail_cell and blocker_none:
        return [{"check": "current_status", "status": "FAIL",
                 "detail": "STATUS has a FAIL entry but CURRENT's blocker section says 'none' (contradiction)"}]
    return [{"check": "current_status", "status": "PASS", "detail": "no contradiction between CURRENT and STATUS"}]


def _check_status_evidence(ws: Path) -> list[dict]:
    status = ws / ".ai" / "STATUS.md"
    if not status.is_file():
        return [{"check": "status_evidence", "status": "NOT_RUN", "detail": ".ai/STATUS.md not found"}]
    problems = []
    for lineno, line in enumerate(status.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        row = _TABLE_ROW.match(line.strip())
        if not row:
            continue
        cells = [c.strip() for c in row.group(1).split("|")]
        # | 항목 | 상태 | 근거 | 형식(3칸)만 판정한다. 상태만 있는 2칸 표는 대상이 아니다.
        if len(cells) == 3 and cells[1] == "PASS" and not cells[2]:
            problems.append(f"line {lineno}: '{cells[0]}' is PASS but has no evidence")
    if problems:
        return [{"check": "status_evidence", "status": "FAIL",
                 "detail": "; ".join(problems[:5])}]
    return [{"check": "status_evidence", "status": "PASS",
             "detail": "evidence column is filled in for all PASS entries"}]


def _check_error_codes_cataloged(ws: Path) -> list[dict]:
    catalog_path = next((ws / loc for loc in _CATALOG_LOCATIONS if (ws / loc).is_file()), None)
    if catalog_path is None:
        return [{"check": "error_codes", "status": "NOT_RUN",
                 "detail": "no project ERROR_CATALOG.md (templates/ is excluded as a form)"}]
    catalog_text = catalog_path.read_text(encoding="utf-8", errors="replace")
    used: dict[str, str] = {}
    for path in sorted(ws.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _CODE_FILE_SUFFIXES:
            continue
        rel_parts = path.relative_to(ws).parts
        if rel_parts and rel_parts[0] in (".git", "templates", ".ai"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for code in _ERROR_CODE.findall(text):
            used.setdefault(code, str(path.relative_to(ws)))
    missing = {c: p for c, p in used.items() if c not in catalog_text}
    if missing:
        detail = ", ".join(f"{c} ({p})" for c, p in sorted(missing.items())[:5])
        return [{"check": "error_codes", "status": "FAIL",
                 "detail": f"error code(s) not registered in the catalog: {detail}"}]
    return [{"check": "error_codes", "status": "PASS",
             "detail": f"all {len(used)} used error code(s) are registered in the catalog"}]


def run_document_sync(workspace: Path, config_path: str | None = None) -> dict:
    ws = resolve_workspace(workspace)
    config, config_error, _unknown = load_config(ws, config_path)
    findings: list[dict] = []
    findings += _check_readme_references(ws)
    findings += _check_required_documents(ws, config)
    findings += _check_config_commands(config, config_error)
    findings += _check_current_status_consistency(ws)
    findings += _check_status_evidence(ws)
    findings += _check_error_codes_cataloged(ws)

    has_fail = any(f["status"] == "FAIL" for f in findings)
    executed = any(f["status"] in ("PASS", "FAIL") for f in findings)
    return {
        "status": "FAIL" if has_fail else ("PASS" if executed else "NOT_RUN"),
        "workspace": str(ws),
        "findings": findings,
        "summary": {
            "pass": sum(1 for f in findings if f["status"] == "PASS"),
            "fail": sum(1 for f in findings if f["status"] == "FAIL"),
            "not_run": sum(1 for f in findings if f["status"] == "NOT_RUN"),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="check_document_sync", description="Machine-checkable document sync checks")
    parser.add_argument("--config", default=None, help="config file path")
    parser.add_argument("--workspace", default=None, help="workspace path (default: current directory)")
    parser.add_argument("--json", action="store_true", help="output as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_utf8_io()
    args = build_parser().parse_args(argv)
    report = run_document_sync(resolve_workspace(args.workspace), config_path=args.config)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"document sync: {report['status']}  (pass {report['summary']['pass']} / "
              f"fail {report['summary']['fail']} / not_run {report['summary']['not_run']})")
        for f in report["findings"]:
            print(f"  [{f['status']:<7}] {f['check']}: {f['detail']}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
