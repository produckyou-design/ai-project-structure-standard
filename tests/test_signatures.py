"""Phase 1 — AI 시작·종료 서명 테스트.

외부에서 관찰 가능한 결과(ledger 파일, 항목 필드, 해시 연결)를 검증한다.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import common
from scripts import sign_ai_session as sign


def _read_ledger(repo: Path) -> list[dict]:
    path = repo / ".ai" / "ledger.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_start_signature_writes_ledger(git_repo: Path):
    entry = sign.run_start(git_repo, task="Phase 1 구현")
    ledger = _read_ledger(git_repo)
    assert len(ledger) == 1
    assert ledger[0] == entry
    assert entry["kind"] == "start"
    assert entry["run_id"].startswith("run_")
    assert entry["branch"] == "main"
    assert entry["base_commit"] == common.git_head(git_repo)
    assert len(entry["entry_hash"]) == 64
    assert entry["previous_entry_hash"] == ""


def test_signature_schema_is_valid_json(git_repo: Path):
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "ai_signature.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["$id"]
    assert "start_signature" in schema["definitions"]
    assert "end_signature" in schema["definitions"]
    start_required = schema["definitions"]["start_signature"]["required"]
    end_required = schema["definitions"]["end_signature"]["required"]
    assert "run_id" in start_required and "run_id" in end_required
    assert "entry_hash" in start_required and "previous_entry_hash" in start_required
    # 첫 항목의 previous_entry_hash 는 빈 문자열을 허용해야 한다 (스키마-코드 일치)
    prev = schema["definitions"]["start_signature"]["properties"]["previous_entry_hash"]
    assert prev["$ref"] == "#/definitions/hash_or_empty"


def test_actual_model_id_unknown_without_env(git_repo: Path, monkeypatch):
    for key in common.MODEL_ID_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    entry = sign.run_start(git_repo, task="모델 ID 검증")
    assert entry["actual_model_id"] == "UNKNOWN"


def test_actual_model_id_from_env(git_repo: Path, monkeypatch):
    monkeypatch.setenv("AI_ACTUAL_MODEL_ID", "verified-model-42")
    entry = sign.run_start(git_repo, task="모델 ID 환경변수 검증")
    assert entry["actual_model_id"] == "verified-model-42"


def test_end_signature_links_to_start(git_repo: Path):
    start = sign.run_start(git_repo, task="링크 검증")
    end = sign.run_end(git_repo, "success", run_id=start["run_id"], tests_run="3", tests_passed="3")
    ledger = _read_ledger(git_repo)
    assert len(ledger) == 2
    assert ledger[1] == end
    assert end["kind"] == "end"
    assert end["run_id"] == start["run_id"]
    assert end["status"] == "success"
    assert end["previous_entry_hash"] == start["entry_hash"]
    assert end["base_commit"] == start["base_commit"]
    assert end["end_commit"] == common.git_head(git_repo)


def test_end_auto_links_last_start(git_repo: Path):
    sign.run_start(git_repo, task="첫 시작")
    end = sign.run_end(git_repo, "fail")
    assert end["status"] == "fail"


def test_end_does_not_duplicate_closed_run(git_repo: Path):
    start = sign.run_start(git_repo, task="완료된 run")
    sign.run_end(git_repo, "success", run_id=start["run_id"])
    sign.run_start(git_repo, task="새 run")
    # 자동 연결은 이미 end 가 있는 run 을 건너뛰고 새 run 을 선택한다
    end = sign.run_end(git_repo, "success")
    assert end["run_id"] != start["run_id"]
    assert len(_read_ledger(git_repo)) == 4


def test_ledger_tamper_detected_on_append(git_repo: Path):
    sign.run_start(git_repo, task="첫 항목")
    ledger = _read_ledger(git_repo)
    # 첫 항목의 내용을 변조 (실제로는 안 되는 일이지만 무결성 검사가 막아야 함)
    (git_repo / ".ai" / "ledger.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in ledger)
        .replace(ledger[0]["task"], "변조된 작업"),
        encoding="utf-8",
    )
    with pytest.raises(common.GitError, match="무결성 위반"):
        sign.run_start(git_repo, task="변조 후 append 시도")


def test_ledger_append_only_and_hash_chain(git_repo: Path):
    first = sign.run_start(git_repo, task="첫 항목")
    second = sign.run_start(git_repo, task="둘째 항목")
    third = sign.run_start(git_repo, task="셋째 항목")
    ledger = _read_ledger(git_repo)
    assert len(ledger) == 3
    assert ledger[1]["previous_entry_hash"] == first["entry_hash"]
    assert ledger[2]["previous_entry_hash"] == second["entry_hash"]
    assert third["previous_entry_hash"] == second["entry_hash"]
    # 첫 항목이 이후 기록에 의해 수정되지 않았는지 (append-only)
    assert ledger[0] == first


def test_git_info_collected_after_change(git_repo: Path):
    sign.run_start(git_repo, task="변경 전")
    (git_repo / "README.md").write_text("# modified\n", encoding="utf-8")
    assert common.git_diff_hash(git_repo) != common.sha256("")
    changed = common.changed_files(git_repo)
    assert "README.md" in changed


def test_end_records_file_changes(git_repo: Path):
    import subprocess

    (git_repo / "old.txt").write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "old.txt"], cwd=str(git_repo), check=True)
    subprocess.run(["git", "commit", "-m", "add old"], cwd=str(git_repo), check=True)
    sign.run_start(git_repo, task="변경 수집")
    (git_repo / "README.md").write_text("# modified\n", encoding="utf-8")
    (git_repo / "new_file.txt").write_text("new\n", encoding="utf-8")
    (git_repo / "old.txt").unlink()
    end = sign.run_end(git_repo, "success")
    assert "README.md" in end["changed_files"]
    assert "new_file.txt" in end["created_files"]
    assert "old.txt" in end["deleted_files"]
    assert len(end["diff_hash"]) == 64


def test_end_requires_git_repo(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(common.GitError):
        sign.run_end(plain, "success")
    with pytest.raises(common.GitError):
        sign.run_start(plain, task="git 아님")


def test_end_with_unknown_run_id_fails(git_repo: Path):
    sign.run_start(git_repo, task="시작")
    with pytest.raises(ValueError):
        sign.run_end(git_repo, "success", run_id="run_missing_000000")
