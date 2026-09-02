#!/usr/bin/env python3
"""Executable contract tests for the resumable operator workflow state."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
STATE_SCRIPT = SKILL_ROOT / "scripts" / "workflow_state.py"
TEMPLATE = SKILL_ROOT / "references" / "workflow-todo.template.md"


def load_state_module():
    spec = importlib.util.spec_from_file_location("workflow_state", STATE_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


WORKFLOW = load_state_module()


def invoke(state_dir: Path, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(STATE_SCRIPT), *args, "--state-dir", str(state_dir)]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    assert result.returncode == expected, f"{command}\nstdout={result.stdout}\nstderr={result.stderr}"
    return result


def init_run(
    tmp_path: Path,
    run_id: str = "bitshift-test",
    mode: str = "AUTO_ALL",
    *,
    with_sdk: bool = True,
) -> Path:
    state_dir = tmp_path / run_id
    init_args = [
        "init",
        "--operator",
        "BitShift",
        "--run-id",
        run_id,
        "--mode",
        mode,
        "--template",
        str(TEMPLATE),
    ]
    if mode == "AUTO_ALL" and with_sdk:
        init_args.extend(("--sdk-root", str(tmp_path / "firmware-sdk")))
    invoke(state_dir, *init_args)
    return state_dir


def confirm_run(
    state_dir: Path,
    *,
    phrase: str = "确认执行",
    confirmed_mode: str | None = None,
    sdk_root: Path | None = None,
    expected: int = 0,
) -> subprocess.CompletedProcess[str]:
    mode = confirmed_mode or read_state(state_dir)["mode"]
    args = [
        "confirm",
        "--run-id",
        state_dir.name,
        "--phrase",
        phrase,
        "--confirmed-mode",
        mode,
    ]
    if sdk_root is not None:
        args.extend(("--sdk-root", str(sdk_root)))
    return invoke(state_dir, *args, expected=expected)


def finish_current(state_dir: Path, task_id: str, status: str = "PASS", *evidence: str) -> None:
    if task_id != "stage0.scope_environment":
        invoke(state_dir, "start", "--run-id", state_dir.name, "--task", task_id)
    args = [
        "finish",
        "--run-id",
        state_dir.name,
        "--task",
        task_id,
        "--status",
        status,
        "--attempt-token",
        attempt_token(state_dir, task_id),
    ]
    if not evidence:
        evidence = (f"receipt:{task_id}",)
    for item in evidence:
        args.extend(("--evidence", item))
    invoke(state_dir, *args)


def pass_to_host_or_board(
    state_dir: Path, *, board_status: str = "PASS", firmware_status: str = "PASS"
) -> None:
    finish_current(state_dir, "stage0.scope_environment", "PASS", "env-probe.json")
    confirm_run(state_dir)
    for task in (
        "stage1.plan",
        "stage1.initial_docs",
        "stage1.pre_source_gate",
        "stage2.implementation",
        "stage2.code_review",
        "stage3.mslite_build",
        "stage4.host_verify",
    ):
        finish_current(state_dir, task, "PASS", f"{task}.json")
    finish_current(
        state_dir,
        "stage6.firmware_matrix",
        firmware_status,
        *[f"board/tc{i}/{mode}.fwpkg" for i in range(1, 13) for mode in ("fp32", "int8")],
    )
    if firmware_status != "PASS":
        return
    finish_current(
        state_dir,
        "stage7.board_matrix",
        board_status,
        *[f"board/tc{i}/{mode}.json" for i in range(1, 13) for mode in ("fp32", "int8")],
    )


def finish_terminal_docs_and_report(state_dir: Path) -> None:
    finish_current(state_dir, "stage5.final_docs", "PASS", "docs/design.md", "docs/verify.md")
    invoke(state_dir, "finalize", "--run-id", state_dir.name, "--evidence", "workflow-summary.txt")


def read_state(state_dir: Path) -> dict:
    return json.loads((state_dir / "workflow_state.json").read_text(encoding="utf-8"))


def attempt_token(state_dir: Path, task_id: str) -> str:
    state = read_state(state_dir)
    return next(item for item in state["tasks"] if item["id"] == task_id)["attempt_token"]


def test_init_generates_todo_checkpoint_and_event_log(tmp_path):
    state_dir = init_run(tmp_path)
    state = read_state(state_dir)
    WORKFLOW.validate_task_manifest()
    assert state["schema_version"] == 1
    assert state["run_id"] == "bitshift-test"
    assert state["current_task"] == "stage0.scope_environment"
    assert state["tasks"][0]["status"] == "RUNNING"
    assert (state_dir / "workflow_todo.md").is_file()
    assert (state_dir / "workflow_events.jsonl").is_file()
    todo = (state_dir / "workflow_todo.md").read_text(encoding="utf-8")
    assert "{{" not in todo
    assert "stage7.board_matrix" in todo
    assert "[~]" in todo
    assert str(tmp_path / "firmware-sdk") in todo
    assert list(state_dir.glob("*.tmp")) == []


def test_bitshift_auto_all_stub_completes_12_case_two_mode_matrix(tmp_path):
    state_dir = init_run(tmp_path)
    pass_to_host_or_board(state_dir)
    finish_terminal_docs_and_report(state_dir)
    state = read_state(state_dir)
    assert state["overall_status"] == "PASS"
    assert state["current_task"] is None
    assert all(item["status"] == "PASS" for item in state["tasks"])
    firmware = next(item for item in state["tasks"] if item["id"] == "stage6.firmware_matrix")
    board = next(item for item in state["tasks"] if item["id"] == "stage7.board_matrix")
    assert len(firmware["evidence"]) == 24
    assert len(board["evidence"]) == 24
    assert state["confirmation_count"] == 1
    assert sum(event["event"] == "EXECUTION_CONFIRMED" for event in state["events"]) == 1
    todo = (state_dir / "workflow_todo.md").read_text(encoding="utf-8")
    completed_task_rows = [
        line
        for line in todo.splitlines()
        if line.startswith("- [x] `stage") or line.startswith("- [x] `terminal.report`")
    ]
    assert len(completed_task_rows) == len(WORKFLOW.TASKS)
    assert "（PASS）" in todo
    # Every executable task has a start/finish pair except the implicit
    # stage0 probe and the one-shot confirmation; finalization adds its own
    # event.  The exact count is intentionally allowed to grow with retries.
    assert len(state["events"]) >= len(WORKFLOW.TASKS) + 9


def test_auto_all_board_not_run_is_incomplete_but_final_docs_still_run(tmp_path):
    state_dir = init_run(tmp_path)
    pass_to_host_or_board(state_dir, board_status="NOT_RUN")
    finish_terminal_docs_and_report(state_dir)
    state = read_state(state_dir)
    statuses = {item["id"]: item["status"] for item in state["tasks"]}
    assert statuses["stage6.firmware_matrix"] == "PASS"
    assert statuses["stage7.board_matrix"] == "NOT_RUN"
    assert statuses["stage5.final_docs"] == "PASS"
    assert state["overall_status"] == "INCOMPLETE"


def test_terminal_report_is_required_before_any_success_status(tmp_path):
    state_dir = init_run(tmp_path)
    pass_to_host_or_board(state_dir)
    finish_current(state_dir, "stage5.final_docs", "PASS")
    state = read_state(state_dir)
    assert state["current_task"] == "terminal.report"
    assert state["overall_status"] == "INCOMPLETE"
    status = invoke(state_dir, "status", "--run-id", state_dir.name)
    assert "OP_WORKFLOW=INCOMPLETE" in status.stdout
    invoke(state_dir, "finalize", "--run-id", state_dir.name, "--evidence", "workflow-summary.txt")
    assert read_state(state_dir)["overall_status"] == "PASS"


def test_confirmation_is_one_shot_and_subsequent_steps_need_no_prompt(tmp_path):
    state_dir = init_run(tmp_path)
    finish_current(state_dir, "stage0.scope_environment", "PASS")
    confirm_run(state_dir)
    duplicate = invoke(
        state_dir,
        "confirm",
        "--run-id",
        state_dir.name,
        "--phrase",
        "确认执行",
        "--confirmed-mode",
        "AUTO_ALL",
        expected=2,
    )
    assert "CONFIRMATION_ALREADY_RECORDED" in duplicate.stderr
    # No interactive input is supplied; the next task starts directly.
    invoke(state_dir, "start", "--run-id", state_dir.name, "--task", "stage1.plan")


def test_auto_all_confirmation_requires_user_sdk_and_matching_mode(tmp_path):
    state_dir = init_run(tmp_path, run_id="sdk-confirm", with_sdk=False)
    finish_current(state_dir, "stage0.scope_environment", "PASS", "env-probe.json")
    missing = confirm_run(state_dir, expected=2)
    assert "requires the user's absolute firmware SDK path" in missing.stderr
    conflict = confirm_run(
        state_dir,
        phrase="只做电脑端验证",
        confirmed_mode="HOST_ONLY",
        sdk_root=tmp_path / "firmware-sdk",
        expected=2,
    )
    assert "CONFIRMED_MODE_MISMATCH" in conflict.stderr
    confirm_run(
        state_dir,
        sdk_root=tmp_path / "firmware-sdk",
    )
    state = read_state(state_dir)
    assert state["firmware_sdk_root"] == str(tmp_path / "firmware-sdk")
    assert state["confirmation"]["mode"] == "AUTO_ALL"
    assert state["confirmation"]["sdk_root"] == str(tmp_path / "firmware-sdk")


def test_confirmation_mode_is_explicit_and_phrase_is_audit_only(tmp_path):
    state_dir = init_run(tmp_path, run_id="host-confirm", mode="HOST_ONLY")
    finish_current(state_dir, "stage0.scope_environment", "PASS", "env-probe.json")
    confirm_run(state_dir, phrase="确认，只做 Host，不需要烧录")
    state = read_state(state_dir)
    assert state["confirmation"]["phrase"] == "确认，只做 Host，不需要烧录"
    assert state["confirmation"]["mode"] == "HOST_ONLY"

    mismatch_dir = init_run(tmp_path, run_id="host-confirm-mismatch", mode="HOST_ONLY")
    finish_current(mismatch_dir, "stage0.scope_environment", "PASS", "env-probe.json")
    mismatch = confirm_run(mismatch_dir, confirmed_mode="AUTO_ALL", expected=2)
    assert "CONFIRMED_MODE_MISMATCH" in mismatch.stderr


def test_finish_requires_evidence_for_terminal_result(tmp_path):
    state_dir = init_run(tmp_path)
    finish_current(state_dir, "stage0.scope_environment", "PASS")
    confirm_run(state_dir)
    started = invoke(state_dir, "start", "--run-id", state_dir.name, "--task", "stage1.plan")
    token = next(line.split("=", 1)[1] for line in started.stdout.splitlines() if line.startswith("ATTEMPT_TOKEN="))
    missing = invoke(
        state_dir,
        "finish",
        "--run-id",
        state_dir.name,
        "--task",
        "stage1.plan",
        "--status",
        "PASS",
        "--attempt-token",
        token,
        expected=2,
    )
    assert "at least one evidence reference is required" in missing.stderr


def test_todo_projection_is_required_for_state_reads(tmp_path):
    state_dir = init_run(tmp_path)
    (state_dir / "workflow_todo.md").unlink()
    result = invoke(state_dir, "status", "--run-id", state_dir.name, expected=2)
    assert "TODO file does not exist" in result.stderr


def test_todo_projection_metadata_tampering_fails_closed(tmp_path):
    state_dir = init_run(tmp_path)
    todo = state_dir / "workflow_todo.md"
    todo.write_text(
        todo.read_text(encoding="utf-8").replace("`AUTO_ALL`", "`HOST_ONLY`"),
        encoding="utf-8",
    )
    result = invoke(state_dir, "status", "--run-id", state_dir.name, expected=2)
    assert "TODO metadata does not match" in result.stderr


def test_host_only_marks_board_not_requested_and_has_scoped_terminal_status(tmp_path):
    state_dir = init_run(tmp_path, run_id="bitshift-host-only", mode="HOST_ONLY")
    finish_current(state_dir, "stage0.scope_environment", "PASS", "env-probe.json")
    confirm_run(state_dir, phrase="只做电脑端验证")
    for task in (
        "stage1.plan",
        "stage1.initial_docs",
        "stage1.pre_source_gate",
        "stage2.implementation",
        "stage2.code_review",
        "stage3.mslite_build",
        "stage4.host_verify",
        "stage5.final_docs",
    ):
        finish_current(state_dir, task, "PASS", f"{task}.json")
    invoke(state_dir, "finalize", "--run-id", state_dir.name, "--evidence", "workflow-summary.txt")
    state = read_state(state_dir)
    statuses = {item["id"]: item["status"] for item in state["tasks"]}
    assert statuses["stage6.firmware_matrix"] == "NOT_REQUESTED"
    assert statuses["stage7.board_matrix"] == "NOT_REQUESTED"
    assert state["overall_status"] == "HOST_ONLY_PASS"


def test_failure_freezes_execution_tasks_but_allows_terminal_docs_and_retry(tmp_path):
    state_dir = init_run(tmp_path)
    finish_current(state_dir, "stage0.scope_environment", "PASS")
    confirm_run(state_dir)
    for task in ("stage1.plan", "stage1.initial_docs", "stage1.pre_source_gate", "stage2.implementation", "stage2.code_review"):
        finish_current(state_dir, task, "PASS")
    finish_current(state_dir, "stage3.mslite_build", "FAIL", "first-error.log")
    failed = read_state(state_dir)
    statuses = {item["id"]: item["status"] for item in failed["tasks"]}
    assert statuses["stage4.host_verify"] == "BLOCKED"
    assert statuses["stage6.firmware_matrix"] == "BLOCKED"
    assert statuses["stage5.final_docs"] == "PENDING"
    assert statuses["terminal.report"] == "PENDING"
    assert failed["overall_status"] == "FAIL"
    invoke(state_dir, "retry", "--run-id", state_dir.name, "--task", "stage3.mslite_build")
    retried = read_state(state_dir)
    assert retried["current_task"] == "stage3.mslite_build"
    assert retried["tasks"][7]["status"] == "PENDING"


def test_retry_cannot_skip_an_earlier_failed_predecessor(tmp_path):
    state_dir = init_run(tmp_path)
    finish_current(state_dir, "stage0.scope_environment", "PASS")
    confirm_run(state_dir)
    finish_current(state_dir, "stage1.plan", "PASS")
    finish_current(state_dir, "stage1.initial_docs", "PASS")
    finish_current(state_dir, "stage1.pre_source_gate", "PASS")
    finish_current(state_dir, "stage2.implementation", "FAIL", "implementation-error.log")
    skipped = invoke(
        state_dir,
        "retry",
        "--run-id",
        state_dir.name,
        "--task",
        "stage3.mslite_build",
        expected=2,
    )
    assert "RETRY_PRECONDITION" in skipped.stderr


def test_schema_tampering_and_orphaned_init_fail_closed(tmp_path):
    state_dir = init_run(tmp_path)
    tampered = read_state(state_dir)
    tampered["overall_status"] = "PASS"
    (state_dir / "workflow_state.json").write_text(
        json.dumps(tampered, ensure_ascii=False), encoding="utf-8"
    )
    result = invoke(state_dir, "status", "--run-id", state_dir.name, expected=2)
    assert "overall_status mismatch" in result.stderr

    orphan = tmp_path / "orphan"
    orphan.mkdir()
    (orphan / "workflow_events.jsonl").write_text("old\n", encoding="utf-8")
    result = invoke(
        orphan,
        "init",
        "--operator",
        "BitShift",
        "--run-id",
        "orphan-run",
        expected=2,
    )
    assert "refusing to overwrite" in result.stderr
    assert not (orphan / "workflow_state.json").exists()


def test_non_board_skip_status_tampering_fails_closed(tmp_path):
    for skipped_status in ("NOT_REQUESTED", "NOT_RUN"):
        state_dir = init_run(tmp_path, run_id=f"tampered-{skipped_status.lower()}")
        finish_current(state_dir, "stage0.scope_environment", "PASS")
        confirm_run(state_dir)
        tampered = read_state(state_dir)
        # Keep all predecessors terminal so the edited implementation task is
        # not rejected merely by the predecessor-order check; this exercises
        # the dedicated board-only status contract.
        target = tampered["tasks"][2]
        target["status"] = skipped_status
        target["completed_at"] = tampered["created_at"]
        target["heartbeat_at"] = None
        target["owner_pid"] = None
        target["attempt_token"] = None
        tampered["current_task"] = "stage1.initial_docs"
        (state_dir / "workflow_state.json").write_text(
            json.dumps(tampered, ensure_ascii=False), encoding="utf-8"
        )
        result = invoke(state_dir, "status", "--run-id", state_dir.name, expected=2)
        assert f"{skipped_status} is only valid for board tasks" in result.stderr


def test_confirmed_run_cannot_retry_stage0_scope(tmp_path):
    state_dir = init_run(tmp_path, run_id="confirmed-stage0-retry")
    finish_current(state_dir, "stage0.scope_environment", "PASS")
    confirm_run(state_dir)
    result = invoke(
        state_dir,
        "retry",
        "--run-id",
        state_dir.name,
        "--task",
        "stage0.scope_environment",
        expected=2,
    )
    assert "cannot retry stage0.scope_environment after execution confirmation" in result.stderr


def test_resume_rejects_malformed_timezone_timestamp(tmp_path):
    state_dir = init_run(tmp_path, run_id="bad-heartbeat-timestamp")
    tampered = read_state(state_dir)
    tampered["tasks"][0]["heartbeat_at"] = "2026-09-02T12:00:00"
    (state_dir / "workflow_state.json").write_text(
        json.dumps(tampered, ensure_ascii=False), encoding="utf-8"
    )
    result = invoke(state_dir, "resume", "--run-id", state_dir.name, expected=2)
    assert "timezone-aware ISO-8601 timestamp" in result.stderr


def test_status_rejects_malformed_confirmation_timestamp(tmp_path):
    state_dir = init_run(tmp_path, run_id="bad-confirmation-timestamp")
    finish_current(state_dir, "stage0.scope_environment", "PASS")
    confirm_run(state_dir)
    tampered = read_state(state_dir)
    tampered["confirmation"]["at"] = "2026-09-02T12:00:00"
    (state_dir / "workflow_state.json").write_text(
        json.dumps(tampered, ensure_ascii=False), encoding="utf-8"
    )
    result = invoke(state_dir, "status", "--run-id", state_dir.name, expected=2)
    assert "timezone-aware ISO-8601 timestamp" in result.stderr


def test_confirmation_count_tampering_and_event_sidecar_fail_closed(tmp_path):
    state_dir = init_run(tmp_path)
    tampered = read_state(state_dir)
    tampered["confirmation_count"] = 1
    (state_dir / "workflow_state.json").write_text(
        json.dumps(tampered, ensure_ascii=False), encoding="utf-8"
    )
    result = invoke(state_dir, "status", "--run-id", state_dir.name, expected=2)
    assert "confirmation_count and execution_confirmed disagree" in result.stderr

    # Restore the checkpoint from a fresh run, then damage only the JSONL
    # sidecar.  Recovery must not silently trust a mismatched event history.
    state_dir = init_run(tmp_path, run_id="event-sidecar")
    (state_dir / "workflow_events.jsonl").write_text("{broken\n", encoding="utf-8")
    result = invoke(state_dir, "status", "--run-id", state_dir.name, expected=2)
    assert "event log is corrupt" in result.stderr

    state_dir = init_run(tmp_path, run_id="missing-field")
    tampered = read_state(state_dir)
    del tampered["created_at"]
    (state_dir / "workflow_state.json").write_text(
        json.dumps(tampered, ensure_ascii=False), encoding="utf-8"
    )
    result = invoke(state_dir, "status", "--run-id", state_dir.name, expected=2)
    assert "created_at" in result.stderr


def test_retry_board_stage_requires_successful_firmware_predecessor(tmp_path):
    state_dir = init_run(tmp_path)
    pass_to_host_or_board(state_dir, firmware_status="NOT_RUN")
    skipped = invoke(
        state_dir,
        "retry",
        "--run-id",
        state_dir.name,
        "--task",
        "stage7.board_matrix",
        expected=2,
    )
    assert "RETRY_PRECONDITION" in skipped.stderr


def test_final_docs_can_retry_after_recording_upstream_failure(tmp_path):
    state_dir = init_run(tmp_path)
    finish_current(state_dir, "stage0.scope_environment", "PASS")
    confirm_run(state_dir)
    for task in (
        "stage1.plan",
        "stage1.initial_docs",
        "stage1.pre_source_gate",
        "stage2.implementation",
        "stage2.code_review",
    ):
        finish_current(state_dir, task, "PASS")
    finish_current(state_dir, "stage3.mslite_build", "FAIL", "build-error.log")
    finish_current(state_dir, "stage5.final_docs", "FAIL", "doc-error.log")
    invoke(state_dir, "retry", "--run-id", state_dir.name, "--task", "stage5.final_docs")
    assert read_state(state_dir)["current_task"] == "stage5.final_docs"


def test_upstream_retry_invalidates_previously_finalized_downstream_results(tmp_path):
    state_dir = init_run(tmp_path)
    finish_current(state_dir, "stage0.scope_environment", "PASS")
    confirm_run(state_dir)
    for task in (
        "stage1.plan",
        "stage1.initial_docs",
        "stage1.pre_source_gate",
        "stage2.implementation",
        "stage2.code_review",
    ):
        finish_current(state_dir, task, "PASS")
    finish_current(state_dir, "stage3.mslite_build", "FAIL")
    finish_current(state_dir, "stage5.final_docs", "PASS")
    invoke(state_dir, "finalize", "--run-id", state_dir.name, "--evidence", "workflow-summary.txt")
    invoke(state_dir, "retry", "--run-id", state_dir.name, "--task", "stage3.mslite_build")
    state = read_state(state_dir)
    assert state["current_task"] == "stage3.mslite_build"
    assert next(item for item in state["tasks"] if item["id"] == "stage5.final_docs")["status"] == "PENDING"
    assert next(item for item in state["tasks"] if item["id"] == "terminal.report")["status"] == "PENDING"
    assert next(item for item in state["tasks"] if item["id"] == "stage3.mslite_build")["evidence"] == []
    assert next(item for item in state["tasks"] if item["id"] == "stage5.final_docs")["evidence"] == []
    retry_event = next(event for event in reversed(state["events"]) if event["event"] == "TASK_RETRY_SCHEDULED")
    assert "stage3.mslite_build" in retry_event["invalidated_evidence"]


def test_stale_attempt_token_cannot_finish_a_restarted_task(tmp_path):
    state_dir = init_run(tmp_path)
    finish_current(state_dir, "stage0.scope_environment", "PASS")
    confirm_run(state_dir)
    first_start = invoke(state_dir, "start", "--run-id", state_dir.name, "--task", "stage1.plan")
    first_token = next(line.split("=", 1)[1] for line in first_start.stdout.splitlines() if line.startswith("ATTEMPT_TOKEN="))
    invoke(state_dir, "resume", "--run-id", state_dir.name, "--force")
    second_start = invoke(state_dir, "start", "--run-id", state_dir.name, "--task", "stage1.plan")
    second_token = next(line.split("=", 1)[1] for line in second_start.stdout.splitlines() if line.startswith("ATTEMPT_TOKEN="))
    assert first_token != second_token
    stale = invoke(
        state_dir,
        "finish",
        "--run-id",
        state_dir.name,
        "--task",
        "stage1.plan",
        "--status",
        "PASS",
        "--attempt-token",
        first_token,
        "--evidence",
        "stale-result.json",
        expected=2,
    )
    assert "ATTEMPT_TOKEN_MISMATCH" in stale.stderr
    invoke(
        state_dir,
        "finish",
        "--run-id",
        state_dir.name,
        "--task",
        "stage1.plan",
        "--status",
        "PASS",
        "--attempt-token",
        second_token,
        "--evidence",
        "plan-result.json",
    )


def test_environment_failure_still_allows_terminal_docs_and_finalize(tmp_path):
    state_dir = init_run(tmp_path)
    finish_current(state_dir, "stage0.scope_environment", "FAIL", "env-error.log")
    assert read_state(state_dir)["current_task"] == "stage5.final_docs"
    finish_current(state_dir, "stage5.final_docs", "PASS", "blocked-run.md")
    invoke(state_dir, "finalize", "--run-id", state_dir.name, "--evidence", "workflow-summary.txt")
    state = read_state(state_dir)
    assert state["overall_status"] == "FAIL"
    assert state["tasks"][1]["status"] == "BLOCKED"
    assert state["tasks"][-1]["status"] == "PASS"


def test_resume_rejects_negative_stale_after(tmp_path):
    state_dir = init_run(tmp_path)
    result = invoke(
        state_dir,
        "resume",
        "--run-id",
        state_dir.name,
        "--stale-after",
        "-1",
        expected=2,
    )
    assert "stale-after must be non-negative" in result.stderr


def test_bad_template_does_not_leave_half_initialized_run(tmp_path):
    state_dir = tmp_path / "bad-template"
    result = invoke(
        state_dir,
        "init",
        "--operator",
        "BitShift",
        "--run-id",
        "bad-template",
        "--template",
        str(tmp_path / "missing-template.md"),
        expected=2,
    )
    assert "TODO template does not exist" in result.stderr
    assert not state_dir.exists()


def test_revision_rejects_concurrent_stale_writer(tmp_path):
    state_dir = init_run(tmp_path)
    first = WORKFLOW.load_state(state_dir, state_dir.name)
    second = WORKFLOW.load_state(state_dir, state_dir.name)
    first["tasks"][0]["note"] = "writer-A"
    WORKFLOW.persist(state_dir, first, TEMPLATE, "TEST_WRITER_A", "stage0.scope_environment")
    second["tasks"][0]["note"] = "writer-B"
    try:
        WORKFLOW.persist(state_dir, second, TEMPLATE, "TEST_WRITER_B", "stage0.scope_environment")
    except WORKFLOW.StateError as exc:
        assert "CONCURRENT_STATE_UPDATE" in str(exc)
    else:
        raise AssertionError("stale writer unexpectedly overwrote the checkpoint")
    state = read_state(state_dir)
    assert state["tasks"][0]["note"] == "writer-A"
    assert all(event["event"] != "TEST_WRITER_B" for event in state["events"])


def test_resume_recovers_interrupted_task_and_rejects_stale_run_id(tmp_path):
    state_dir = init_run(tmp_path)
    finish_current(state_dir, "stage0.scope_environment", "PASS")
    confirm_run(state_dir)
    invoke(state_dir, "start", "--run-id", state_dir.name, "--task", "stage1.plan")
    # A short-lived `start` CLI does not own the downstream worker.  A fresh
    # checkpoint with no registered owner therefore needs explicit recovery.
    fresh = invoke(state_dir, "resume", "--run-id", state_dir.name, expected=2)
    assert "no registered owner" in fresh.stderr
    invoke(state_dir, "resume", "--run-id", state_dir.name, "--force")
    state = read_state(state_dir)
    assert state["current_task"] == "stage1.plan"
    recovered = next(item for item in state["tasks"] if item["id"] == "stage1.plan")
    assert recovered["status"] == "PENDING"
    assert recovered["started_at"] is None
    stale = invoke(state_dir, "status", "--run-id", "another-run", expected=2)
    assert "RUN_ID_MISMATCH" in stale.stderr
    (state_dir / "workflow_state.json").write_text("{broken", encoding="utf-8")
    corrupt = invoke(state_dir, "status", "--run-id", state_dir.name, expected=2)
    assert "corrupt" in corrupt.stderr


def test_terminal_report_is_finalize_only(tmp_path):
    state_dir = init_run(tmp_path)
    pass_to_host_or_board(state_dir)
    finish_current(state_dir, "stage5.final_docs", "PASS")
    started = invoke(
        state_dir,
        "start",
        "--run-id",
        state_dir.name,
        "--task",
        "terminal.report",
        expected=2,
    )
    assert "dedicated command" in started.stderr
    finished = invoke(
        state_dir,
        "finish",
        "--run-id",
        state_dir.name,
        "--task",
        "terminal.report",
        "--status",
        "PASS",
        expected=2,
    )
    assert "dedicated command" in finished.stderr
    invoke(state_dir, "finalize", "--run-id", state_dir.name, "--evidence", "workflow-summary.txt")
