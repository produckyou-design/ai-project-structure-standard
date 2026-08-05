"""Phase 1 — 인계 번들 테스트.

인계 번들이 이전 대화 없이 이해 가능하고 민감정보를 포함하지 않는지 검증한다.
"""
from __future__ import annotations

from pathlib import Path

import common
from scripts import create_handoff
from scripts import sign_ai_session as sign

FAKE_TOKEN = "sk-test1234567890abcdef"


def _prepare_state(repo: Path) -> None:
    ai_dir = repo / ".ai"
    ai_dir.mkdir(exist_ok=True)
    (ai_dir / "CURRENT.md").write_text(
        "# CURRENT\n\n## 현재 작업\n- Phase 1 테스트\n\n## 블로커\n- 없음\n", encoding="utf-8"
    )
    (ai_dir / "STATUS.md").write_text(
        "# STATUS\n\n| 항목 | 상태 |\n|---|---|\n| 테스트 | NOT_RUN |\n", encoding="utf-8"
    )


def test_handoff_bundle_created(git_repo: Path):
    _prepare_state(git_repo)
    result = create_handoff.create_handoff(git_repo)
    bundle = Path(result["path"])
    assert bundle.exists()
    assert bundle.is_relative_to(git_repo / ".ai" / "handoffs")
    text = bundle.read_text(encoding="utf-8")
    for header in ("# AI Session Handoff Bundle", "## 1. Overview", "## 3. Changes", "## 4.", "## 5. Blockers", "## 6. Next steps"):
        assert header in text
    assert "Phase 1 테스트" in text


def test_handoff_masks_secrets(git_repo: Path):
    _prepare_state(git_repo)
    current = git_repo / ".ai" / "CURRENT.md"
    current.write_text(f"작업 중 토큰 발견: {FAKE_TOKEN}\n", encoding="utf-8")
    result = create_handoff.create_handoff(git_repo)
    text = Path(result["path"]).read_text(encoding="utf-8")
    assert FAKE_TOKEN not in text
    assert "sk-***" in text


def test_handoff_masks_key_value_secrets(git_repo: Path):
    _prepare_state(git_repo)
    current = git_repo / ".ai" / "CURRENT.md"
    current.write_text(f"api_key = {FAKE_TOKEN}\n", encoding="utf-8")
    result = create_handoff.create_handoff(git_repo)
    text = Path(result["path"]).read_text(encoding="utf-8")
    assert FAKE_TOKEN not in text
    assert "api_key = ***" in text


def test_handoff_masks_underscore_key_names(git_repo: Path):
    _prepare_state(git_repo)
    current = git_repo / ".ai" / "CURRENT.md"
    secret = "client_secret = a1b2c3d4e5f6g7h8i9j0"
    current.write_text(f"{secret}\nSECRET_KEY = {FAKE_TOKEN}\n", encoding="utf-8")
    result = create_handoff.create_handoff(git_repo)
    text = Path(result["path"]).read_text(encoding="utf-8")
    assert "a1b2c3d4e5f6g7h8i9j0" not in text
    assert FAKE_TOKEN not in text
    assert "client_secret = ***" in text
    assert "SECRET_KEY = ***" in text


def test_handoff_marks_not_run(git_repo: Path):
    _prepare_state(git_repo)
    result = create_handoff.create_handoff(git_repo)
    text = Path(result["path"]).read_text(encoding="utf-8")
    assert "NOT_RUN" in text


def test_handoff_includes_test_results(git_repo: Path):
    _prepare_state(git_repo)
    start = sign.run_start(git_repo, task="테스트 결과 포함")
    sign.run_end(git_repo, "success", run_id=start["run_id"], tests_run="3", tests_passed="3", tests_failed="0")
    result = create_handoff.create_handoff(git_repo)
    text = Path(result["path"]).read_text(encoding="utf-8")
    assert "success" in text
    assert "tests_run: `3`" in text


def test_handoff_includes_changes(git_repo: Path):
    _prepare_state(git_repo)
    (git_repo / "README.md").write_text("# modified\n", encoding="utf-8")
    (git_repo / "added.txt").write_text("new\n", encoding="utf-8")
    result = create_handoff.create_handoff(git_repo)
    text = Path(result["path"]).read_text(encoding="utf-8")
    assert "README.md" in text
    assert "added.txt" in text
    assert common.git_branch(git_repo) in text


def test_handoff_requires_git_repo(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    try:
        create_handoff.create_handoff(plain)
    except common.GitError:
        pass
    else:
        raise AssertionError("Git 저장소가 아닌 경로에서 예외가 발생해야 한다")
