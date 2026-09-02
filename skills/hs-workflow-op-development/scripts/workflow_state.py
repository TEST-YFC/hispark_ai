#!/usr/bin/env python3
"""Create and maintain a resumable operator-workflow checkpoint.

The workflow is deliberately driven through this small, standard-library-only
state machine.  It keeps a human-readable TODO projection beside an atomic
JSON checkpoint, so a restarted agent can continue at the first unfinished
task without treating an old artifact as a new result.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 1
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
MODES = {"AUTO_ALL", "HOST_ONLY"}
STATUS_ORDER = ("PENDING", "RUNNING", "PASS", "FAIL", "NOT_RUN", "NOT_REQUESTED", "BLOCKED")
STATUSES = set(STATUS_ORDER)
TERMINAL_STATUSES = {"PASS", "FAIL", "NOT_RUN", "NOT_REQUESTED", "BLOCKED"}
OVERALL_STATUSES = {"PASS", "FAIL", "INCOMPLETE", "HOST_ONLY_PASS"}
TASK_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "references" / "workflow-todo.template.json"


@dataclass(frozen=True)
class TaskDef:
    task_id: str
    stage: str
    title: str
    manual: bool = False


# Keep this order stable: it is the workflow's execution contract.
TASKS = (
    TaskDef("stage0.scope_environment", "stage0", "冻结范围并只读探测环境"),
    TaskDef("stage0.confirm", "stage0-confirm", "展示方案并取得一次执行确认", manual=True),
    TaskDef("stage1.plan", "stage1", "生成并冻结实现计划、合同和能力清单"),
    TaskDef("stage1.initial_docs", "stage1", "生成初版设计文档和验证文档"),
    TaskDef("stage1.pre_source_gate", "stage1", "执行初版文档与源码指纹门禁"),
    TaskDef("stage2.implementation", "stage2", "自动写入或修复算子源码"),
    TaskDef("stage2.code_review", "stage2", "执行代码审查和实现质量门禁"),
    TaskDef("stage3.mslite_build", "stage3", "构建本轮 MindSpore Lite 工具包"),
    TaskDef("stage4.host_verify", "stage4", "生成并运行 Host 全量验证"),
    TaskDef("stage6.firmware_matrix", "stage6", "按矩阵自动接入并构建全部固件"),
    TaskDef("stage7.board_matrix", "stage7", "逐项烧录、采集串口并验收板端精度"),
    # The stage5 label is retained for compatibility with the surrounding
    # skills, but its terminal document backfill runs after board stages.
    TaskDef("stage5.final_docs", "stage5", "回填终版成对算子文档"),
    TaskDef("terminal.report", "terminal", "生成逐阶段终态报告"),
)
TASK_BY_ID = {task.task_id: task for task in TASKS}


class StateError(RuntimeError):
    """A user-actionable state transition error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_timestamp(value: Any, field: str) -> datetime:
    """Parse a required timezone-aware ISO-8601 timestamp.

    Checkpoint timestamps are part of the recovery contract.  Accept the
    standard UTC ``Z`` spelling as well as explicit numeric offsets, but do
    not silently reinterpret naive, malformed, or padded values.
    """

    if not isinstance(value, str) or not value or value != value.strip():
        raise StateError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise StateError(f"{field} must be a timezone-aware ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise StateError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    return parsed


def safe_run_id(value: str) -> str:
    if not RUN_ID_RE.fullmatch(value):
        raise StateError("run_id must match [A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
    return value


def normalized_evidence(values: list[str], task_id: str) -> list[str]:
    """Require a non-empty, auditable reference for a terminal task result."""

    if not isinstance(values, list):
        raise StateError(f"evidence must be a list: {task_id}")
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise StateError(f"evidence entries must be non-empty strings: {task_id}")
        cleaned = value.strip()
        if "\r" in cleaned or "\n" in cleaned:
            raise StateError(f"evidence entries must be single-line references: {task_id}")
        if cleaned not in result:
            result.append(cleaned)
    if not result:
        raise StateError(f"at least one evidence reference is required: {task_id}")
    return result


def new_attempt_token() -> str:
    """Return an opaque lease value for one concrete task attempt."""

    # Start with an option-safe character so callers can pass the value as a
    # separate argparse/PowerShell argument without needing `--key=value`.
    return f"t{secrets.token_hex(24)}"


def is_absolute_path(value: str) -> bool:
    """Accept native paths from either Windows or POSIX/WSL callers."""

    return Path(value).expanduser().is_absolute() or bool(re.match(r"^(?:[A-Za-z]:[\\/]|\\\\)", value))


def absolute_dir(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def state_paths(state_dir: Path) -> tuple[Path, Path, Path, Path]:
    return (
        state_dir / "workflow_state.json",
        state_dir / "workflow_todo.md",
        state_dir / "workflow_events.jsonl",
        state_dir / ".workflow_state.lock",
    )


@contextmanager
def lock_file(path: Path, timeout: float = 15.0, stale_after: float = 300.0) -> Iterator[None]:
    """Portable exclusive lock using O_EXCL (works on Windows and POSIX)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    fd: int | None = None
    owner_token = f"{os.getpid()}-{secrets.token_hex(16)}"

    def process_alive(pid: Any) -> bool:
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except PermissionError:
            # The process exists but this caller cannot signal it.
            return True
        except (OSError, ProcessLookupError):
            return False

    def reclaimable() -> bool:
        try:
            if time.time() - path.stat().st_mtime <= stale_after:
                return False
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                # An old/corrupt lock has no trustworthy owner.  Its age is
                # the only safe recovery signal available.
                return True
            return not process_alive(payload.get("pid"))
        except FileNotFoundError:
            return False

    while fd is None:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            payload = {"pid": os.getpid(), "token": owner_token, "created_at": utc_now()}
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                fd = None
                json.dump(payload, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            break
        except FileExistsError:
            if reclaimable():
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise StateError(f"state lock is busy: {path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("token") == owner_token:
                path.unlink()
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            pass


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        if os.name != "nt":
            try:
                directory_fd = os.open(path.parent, os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                # Directory fsync is an extra durability measure, not a
                # reason to fail a valid state update on unusual filesystems.
                pass
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateError(f"state file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"state file is corrupt (fail closed): {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StateError("state file root must be a JSON object")
    validate_state(value)
    return value


def event_log_content(events: list[dict[str, Any]]) -> str:
    """Serialize the bounded event history as newline-delimited JSON."""

    return "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events)


def read_event_log(path: Path) -> list[dict[str, Any]]:
    """Read the JSONL sidecar and fail closed on any malformed line."""

    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StateError(f"event log does not exist: {path}") from exc
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            raise StateError(f"event log contains a blank line at {path}:{line_number}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StateError(f"event log is corrupt at {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict) or not isinstance(value.get("event"), str):
            raise StateError(f"event log contains an invalid record at {path}:{line_number}")
        events.append(value)
    return events


def validate_event_log(state_dir: Path, state: dict[str, Any]) -> None:
    """Ensure the sidecar is exactly the event history in the checkpoint."""

    _, _, events_file, _ = state_paths(state_dir)
    sidecar_events = read_event_log(events_file)
    if sidecar_events != state["events"]:
        raise StateError("event log does not match workflow_state.json (fail closed)")


def task_record(task: TaskDef, status: str = "PENDING") -> dict[str, Any]:
    return {
        "id": task.task_id,
        "stage": task.stage,
        "title": task.title,
        "manual": task.manual,
        "status": status,
        "attempts": 0,
        "started_at": None,
        "completed_at": None,
        "heartbeat_at": None,
        "owner_pid": None,
        "attempt_token": None,
        "evidence": [],
        "note": None,
        "blocked_by": None,
    }


def make_state(
    operator: str,
    run_id: str,
    mode: str,
    environment: dict[str, Any],
    sdk_root: str | None,
) -> dict[str, Any]:
    if not operator.strip():
        raise StateError("operator must not be empty")
    mode = mode.upper()
    if mode not in MODES:
        raise StateError(f"mode must be one of {sorted(MODES)}")
    if sdk_root is not None:
        sdk_root = sdk_root.strip()
        if not is_absolute_path(sdk_root):
            raise StateError("sdk_root must be an absolute path supplied by the user")
    safe_run_id(run_id)
    records = [task_record(task) for task in TASKS]
    if mode == "HOST_ONLY":
        for record in records:
            if record["id"] in {"stage6.firmware_matrix", "stage7.board_matrix"}:
                record["status"] = "NOT_REQUESTED"
                record["completed_at"] = utc_now()
                record["note"] = "用户在 stage0 明确选择仅 Host 范围"
                record["evidence"] = ["scope:HOST_ONLY"]
    # The first task is the read-only stage0 probe. Creating this control
    # record is allowed before confirmation; no operator artifact is touched.
    records[0]["status"] = "RUNNING"
    records[0]["attempts"] = 1
    records[0]["started_at"] = utc_now()
    records[0]["heartbeat_at"] = records[0]["started_at"]
    # `init` is normally a short-lived CLI process.  Do not claim that PID as
    # the owner of the probe that the calling agent will perform afterwards;
    # an unknown owner is recovered only after a stale heartbeat (or force).
    records[0]["owner_pid"] = None
    records[0]["attempt_token"] = new_attempt_token()
    return {
        "schema_version": SCHEMA_VERSION,
        "revision": 0,
        "run_id": run_id,
        "operator": operator.strip(),
        "mode": mode,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "current_task": TASKS[0].task_id,
        "execution_confirmed": False,
        "confirmation_count": 0,
        "confirmation": None,
        "post_confirmation_prompt_count": 0,
        "environment": dict(environment),
        "firmware_sdk_root": sdk_root,
        "overall_status": "INCOMPLETE",
        "tasks": records,
        "artifacts": {},
        "events": [],
    }


def validate_task_manifest(path: Path = TASK_MANIFEST_PATH) -> None:
    """Ensure the checked-in task template and executable contract agree."""

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateError(f"task manifest does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"task manifest is corrupt: {path}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise StateError("task manifest schema is invalid")
    if manifest.get("status_values") != list(STATUS_ORDER):
        raise StateError("task manifest status_values do not match the state contract")
    raw_tasks = manifest.get("tasks")
    expected_tasks = [
        {"id": task.task_id, "stage": task.stage, "title": task.title, "manual": task.manual}
        for task in TASKS
    ]
    if raw_tasks != expected_tasks:
        raise StateError("task manifest tasks do not match the executable workflow contract")


def validate_state(state: dict[str, Any], expected_run_id: str | None = None) -> None:
    required_fields = {
        "schema_version",
        "revision",
        "run_id",
        "operator",
        "mode",
        "created_at",
        "updated_at",
        "current_task",
        "execution_confirmed",
        "confirmation_count",
        "confirmation",
        "post_confirmation_prompt_count",
        "environment",
        "firmware_sdk_root",
        "overall_status",
        "tasks",
        "artifacts",
        "events",
    }
    missing_fields = sorted(required_fields.difference(state))
    if missing_fields:
        raise StateError(f"state is missing required field(s): {','.join(missing_fields)}")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise StateError(f"unsupported state schema: {state.get('schema_version')!r}")
    run_id = state.get("run_id")
    if not isinstance(run_id, str):
        raise StateError("state run_id is missing")
    safe_run_id(run_id)
    revision = state.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        raise StateError("state revision is invalid")
    if expected_run_id is not None and run_id != expected_run_id:
        raise StateError(f"RUN_ID_MISMATCH expected={expected_run_id} actual={run_id}")
    if not isinstance(state.get("operator"), str) or not state["operator"].strip():
        raise StateError("state operator is missing")
    if state.get("mode") not in MODES:
        raise StateError("state mode is invalid")
    for field in ("created_at", "updated_at"):
        parse_timestamp(state[field], f"state {field}")
    if not isinstance(state.get("execution_confirmed"), bool):
        raise StateError("execution_confirmed must be boolean")
    confirmation_count = state.get("confirmation_count")
    if isinstance(confirmation_count, bool) or not isinstance(confirmation_count, int):
        raise StateError("confirmation_count must be an integer")
    if state.get("overall_status") not in OVERALL_STATUSES:
        raise StateError("overall_status is invalid")
    prompt_count = state.get("post_confirmation_prompt_count")
    if isinstance(prompt_count, bool) or not isinstance(prompt_count, int) or prompt_count != 0:
        raise StateError("post_confirmation_prompt_count must remain zero")
    confirmation = state.get("confirmation")
    if confirmation is not None and (
        not isinstance(confirmation, dict)
        or not isinstance(confirmation.get("phrase"), str)
        or not confirmation["phrase"].strip()
        or not isinstance(confirmation.get("at"), str)
        or confirmation.get("mode") not in MODES
        or "sdk_root" not in confirmation
    ):
        raise StateError("confirmation record is invalid")
    if confirmation is not None:
        parse_timestamp(confirmation["at"], "confirmation at")
        confirmation_sdk_root = confirmation.get("sdk_root")
        if confirmation_sdk_root is not None and (
            not isinstance(confirmation_sdk_root, str)
            or not is_absolute_path(confirmation_sdk_root)
        ):
            raise StateError("confirmation sdk_root must be an absolute path or null")
        if state["execution_confirmed"] and confirmation_sdk_root != state.get("firmware_sdk_root"):
            raise StateError("confirmation SDK path does not match the frozen workflow environment")
        if state["execution_confirmed"] and confirmation["mode"] != state["mode"]:
            raise StateError("confirmation mode does not match the frozen workflow scope")
    for field in ("environment", "artifacts"):
        if not isinstance(state.get(field), dict):
            raise StateError(f"state {field} must be an object")
    for key, value in state["artifacts"].items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise StateError("state artifacts contain an invalid record")
        if set(("status", "evidence", "updated_at")) - set(value):
            raise StateError(f"artifact record is incomplete: {key}")
        if value["status"] not in STATUSES:
            raise StateError(f"artifact status is invalid: {key}")
        if not isinstance(value["evidence"], list) or any(
            not isinstance(item, str)
            or not item.strip()
            or item != item.strip()
            or "\r" in item
            or "\n" in item
            for item in value["evidence"]
        ):
            raise StateError(f"artifact evidence is invalid: {key}")
        if value["status"] in TERMINAL_STATUSES and not value["evidence"]:
            raise StateError(f"terminal artifact has no evidence: {key}")
        parse_timestamp(value["updated_at"], f"artifact {key} updated_at")
    if not isinstance(state.get("events"), list):
        raise StateError("state events must be an array")
    if state.get("firmware_sdk_root") is not None and (
        not isinstance(state.get("firmware_sdk_root"), str)
        or not is_absolute_path(state["firmware_sdk_root"])
    ):
        raise StateError("firmware_sdk_root must be an absolute path or null")
    if state["execution_confirmed"] and state["mode"] == "AUTO_ALL" and not state.get("firmware_sdk_root"):
        raise StateError("confirmed AUTO_ALL state must retain the user's firmware SDK path")
    for event in state["events"]:
        if not isinstance(event, dict) or not isinstance(event.get("event"), str):
            raise StateError("state events contain an invalid record")
        parse_timestamp(event.get("at"), "state event at")
        if event.get("task_id") is not None and event["task_id"] not in TASK_BY_ID:
            raise StateError(f"state event references an unknown task: {event['task_id']!r}")
    records = state.get("tasks")
    if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
        raise StateError("state tasks must be an array of objects")
    if [item.get("id") for item in records] != [task.task_id for task in TASKS]:
        raise StateError("task list/order does not match workflow contract")
    for expected, item in zip(TASKS, records):
        required_task_fields = {
            "id",
            "stage",
            "title",
            "manual",
            "status",
            "attempts",
            "started_at",
            "completed_at",
            "heartbeat_at",
            "owner_pid",
            "attempt_token",
            "evidence",
            "note",
            "blocked_by",
        }
        missing_task_fields = sorted(required_task_fields.difference(item))
        if missing_task_fields:
            raise StateError(
                f"task {item.get('id')!r} is missing field(s): {','.join(missing_task_fields)}"
            )
        if item.get("stage") != expected.stage or item.get("title") != expected.title:
            raise StateError(f"task metadata does not match workflow contract: {item.get('id')!r}")
        if item.get("status") not in STATUSES:
            raise StateError(f"invalid task status for {item.get('id')!r}")
        # A skipped task is meaningful only for the board stages: NOT_RUN is
        # an external board/device outcome and NOT_REQUESTED is the explicit
        # HOST_ONLY scope decision.  Reject either value on implementation,
        # documentation, or control tasks so a hand-edited checkpoint cannot
        # silently bypass required work and reach a successful verdict.
        if item["status"] in {"NOT_RUN", "NOT_REQUESTED"} and expected.stage not in {"stage6", "stage7"}:
            raise StateError(
                f"{item['status']} is only valid for board tasks: {item.get('id')!r}"
            )
        if isinstance(item.get("attempts"), bool) or not isinstance(item.get("attempts"), int) or item["attempts"] < 0:
            raise StateError(f"invalid attempts for {item.get('id')!r}")
        if not isinstance(item.get("evidence"), list) or any(
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or "\r" in value
            or "\n" in value
            for value in item["evidence"]
        ):
            raise StateError(f"invalid evidence for {item.get('id')!r}")
        if item["status"] in TERMINAL_STATUSES and not item["evidence"]:
            raise StateError(f"terminal task has no evidence: {item.get('id')!r}")
        if item.get("manual") is not expected.manual:
            raise StateError(f"manual flag does not match workflow contract: {item.get('id')!r}")
        for field in ("started_at", "completed_at", "heartbeat_at"):
            if item[field] is not None:
                parse_timestamp(item[field], f"task {item.get('id')!r} {field}")
        if item["note"] is not None and (
            not isinstance(item["note"], str)
            or "\r" in item["note"]
            or "\n" in item["note"]
        ):
            raise StateError(f"invalid note for {item.get('id')!r}")
        if item["blocked_by"] is not None and item["blocked_by"] not in TASK_BY_ID:
            raise StateError(f"invalid blocked_by for {item.get('id')!r}")
        owner_pid = item.get("owner_pid")
        if owner_pid is not None and (
            isinstance(owner_pid, bool) or not isinstance(owner_pid, int) or owner_pid <= 0
        ):
            raise StateError(f"invalid owner_pid for {item.get('id')!r}")
        attempt_token = item["attempt_token"]
        if attempt_token is not None and (
            not isinstance(attempt_token, str) or not attempt_token.strip()
        ):
            raise StateError(f"invalid attempt_token for {item.get('id')!r}")
        if item["status"] == "RUNNING" and attempt_token is None:
            raise StateError(f"RUNNING task has no attempt_token: {item.get('id')!r}")
        if item["status"] != "RUNNING" and attempt_token is not None:
            raise StateError(f"non-running task has an attempt_token: {item.get('id')!r}")
        if item["status"] == "RUNNING" and item["heartbeat_at"] is None:
            raise StateError(f"RUNNING task has no heartbeat: {item.get('id')!r}")
        if item["status"] != "RUNNING" and (
            item["heartbeat_at"] is not None or item["owner_pid"] is not None
        ):
            raise StateError(f"non-running task retains an owner lease: {item.get('id')!r}")
    # A terminal result may not be placed behind an unfinished predecessor by
    # editing the JSON directly.  HOST_ONLY's explicit board skips are the
    # sole exception and are already fixed at initialization.
    unfinished_seen = False
    for item in records:
        if item["status"] in {"PENDING", "RUNNING"}:
            unfinished_seen = True
        elif unfinished_seen and item["status"] != "NOT_REQUESTED":
            raise StateError(
                f"task {item['id']!r} is terminal before its predecessor tasks finish"
            )
    current = state.get("current_task")
    if current is not None and current not in TASK_BY_ID:
        raise StateError(f"unknown current_task: {current!r}")
    expected_current = next_task(state)
    if current != expected_current:
        raise StateError(f"current_task does not point to first unfinished task: expected={expected_current!r} actual={current!r}")
    if confirmation_count not in (0, 1):
        raise StateError("confirmation_count must be 0 or 1")
    expected_confirmation_count = 1 if state["execution_confirmed"] else 0
    if confirmation_count != expected_confirmation_count:
        raise StateError(
            "confirmation_count and execution_confirmed disagree; refusing to continue"
        )
    if not state["execution_confirmed"] and confirmation is not None:
        raise StateError("unconfirmed state cannot contain a confirmation record")
    if state["execution_confirmed"] and confirmation is None:
        raise StateError("confirmed state must contain a confirmation record")
    by_id = task_map(state)
    if state["execution_confirmed"] != (by_id["stage0.confirm"]["status"] == "PASS"):
        raise StateError("execution confirmation flag and task status disagree")
    if state["mode"] == "HOST_ONLY":
        for task_id in ("stage6.firmware_matrix", "stage7.board_matrix"):
            if by_id[task_id]["status"] != "NOT_REQUESTED":
                raise StateError(f"HOST_ONLY board task must remain NOT_REQUESTED: {task_id}")
    else:
        for task_id in ("stage6.firmware_matrix", "stage7.board_matrix"):
            if by_id[task_id]["status"] == "NOT_REQUESTED":
                raise StateError(f"AUTO_ALL board task cannot be NOT_REQUESTED: {task_id}")
    firmware_status = by_id["stage6.firmware_matrix"]["status"]
    board_status = by_id["stage7.board_matrix"]["status"]
    if board_status in {"PASS", "FAIL"} and firmware_status != "PASS":
        raise StateError("board result requires a PASS firmware-matrix predecessor")
    if firmware_status == "NOT_RUN" and board_status not in {"NOT_RUN", "PENDING"}:
        raise StateError("NOT_RUN firmware matrix cannot have an executed board result")
    if firmware_status in {"FAIL", "BLOCKED"} and board_status not in {"BLOCKED", "PENDING"}:
        raise StateError("failed firmware matrix cannot have an executed board result")
    expected_overall = recompute_overall(state)
    if state["overall_status"] != expected_overall:
        raise StateError(
            f"overall_status mismatch (possible manual/stale edit): expected={expected_overall} actual={state['overall_status']}"
        )


def task_map(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in state["tasks"]}


def next_task(state: dict[str, Any]) -> str | None:
    for item in state["tasks"]:
        if item["status"] not in TERMINAL_STATUSES:
            return item["id"]
    return None


def recompute_overall(state: dict[str, Any]) -> str:
    report_status = task_map(state)["terminal.report"]["status"]
    statuses = [item["status"] for item in state["tasks"] if item["id"] != "terminal.report"]
    if any(status in {"FAIL", "BLOCKED"} for status in statuses):
        return "FAIL"
    # A successful stage matrix is not a terminal workflow result until the
    # report task itself has been written and atomically checkpointed.
    if report_status != "PASS":
        return "INCOMPLETE"
    if state["mode"] == "HOST_ONLY":
        board = {"stage6.firmware_matrix", "stage7.board_matrix"}
        by_id = task_map(state)
        if all(by_id[item]["status"] == "NOT_REQUESTED" for item in board) and all(
            by_id[item]["status"] == "PASS"
            for item in (
                "stage0.scope_environment",
                "stage0.confirm",
                "stage1.plan",
                "stage1.initial_docs",
                "stage1.pre_source_gate",
                "stage2.implementation",
                "stage2.code_review",
                "stage3.mslite_build",
                "stage4.host_verify",
                "stage5.final_docs",
            )
        ):
            return "HOST_ONLY_PASS"
    if any(status in {"PENDING", "RUNNING", "NOT_RUN"} for status in statuses):
        return "INCOMPLETE"
    return "PASS"


def checkbox(status: str) -> str:
    return {
        "PENDING": " ",
        "RUNNING": "~",
        "PASS": "x",
        "FAIL": "!",
        "BLOCKED": "!",
        "NOT_RUN": "?",
        "NOT_REQUESTED": "-",
    }[status]


def task_row_lines(state: dict[str, Any]) -> list[str]:
    records = task_map(state)
    rows: list[str] = []
    for task in TASKS:
        record = records[task.task_id]
        suffix = ""
        if record.get("note"):
            suffix = f"；{record['note']}"
        rows.append(
            f"- [{checkbox(record['status'])}] `{task.task_id}` {task.title} "
            f"（{record['status']}）{suffix}"
        )
    return rows


def render_todo(template_path: Path, state: dict[str, Any], state_file: Path) -> str:
    try:
        template = template_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StateError(f"TODO template does not exist: {template_path}") from exc
    replacements = {
        "{{OPERATOR}}": state["operator"],
        "{{RUN_ID}}": state["run_id"],
        "{{MODE}}": state["mode"],
        "{{SDK_ROOT}}": state.get("firmware_sdk_root") or "待用户提供",
        "{{STATE_FILE}}": str(state_file),
        "{{CREATED_AT}}": state["created_at"],
        "{{TASK_ROWS}}": "\n".join(task_row_lines(state)),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    if "{{" in template or "}}" in template:
        raise StateError("TODO template has unresolved placeholders")
    rendered = template.rstrip() + "\n"
    validate_todo_content(rendered, state, template_path)
    return rendered


def validate_todo_content(content: str, state: dict[str, Any], source: Path) -> None:
    """Check that a rendered TODO contains exactly the contract task rows."""

    if "{{" in content or "}}" in content:
        raise StateError(f"TODO file has unresolved placeholders: {source}")
    expected_headers = (
        f"- 算子：`{state['operator']}`",
        f"- 本轮 ID：`{state['run_id']}`",
        f"- 执行范围：`{state['mode']}`",
        f"- 固件 SDK：`{state.get('firmware_sdk_root') or '待用户提供'}`",
    )
    if any(header not in content.splitlines() for header in expected_headers):
        raise StateError(f"TODO metadata does not match workflow_state.json: {source}")
    expected_rows = task_row_lines(state)
    actual_rows = [
        line
        for line in content.splitlines()
        if line.startswith("- [") and any(f"`{task.task_id}`" in line for task in TASKS)
    ]
    if actual_rows != expected_rows:
        raise StateError(f"TODO file does not match workflow_state.json: {source}")


def validate_todo_projection(state_dir: Path, state: dict[str, Any]) -> None:
    """Fail closed when the human-readable TODO is missing or stale.

    The JSON checkpoint remains authoritative, but the TODO is an operational
    handoff artifact.  Comparing its generated task rows catches a deleted or
    hand-edited projection without imposing a fixed surrounding template.
    """

    _, todo_file, _, _ = state_paths(state_dir)
    try:
        content = todo_file.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StateError(f"TODO file does not exist: {todo_file}") from exc
    validate_todo_content(content, state, todo_file)


def append_event(state: dict[str, Any], event: str, task_id: str | None = None, **extra: Any) -> None:
    item: dict[str, Any] = {"at": utc_now(), "event": event}
    if task_id is not None:
        item["task_id"] = task_id
    item.update(extra)
    state["events"].append(item)
    # Keep the checkpoint bounded even for a long retrying run.
    state["events"] = state["events"][-500:]


def persist(state_dir: Path, state: dict[str, Any], template_path: Path, event: str, task_id: str | None = None, **extra: Any) -> None:
    state_file, todo_file, events_file, lock = state_paths(state_dir)
    with lock_file(lock):
        current_revision = None
        if state_file.exists():
            current = read_json(state_file)
            validate_event_log(state_dir, current)
            validate_todo_projection(state_dir, current)
            current_revision = current["revision"]
            base_revision = state.get("_base_revision", state["revision"])
            if current_revision != base_revision:
                raise StateError(
                    f"CONCURRENT_STATE_UPDATE expected_revision={base_revision} actual={current_revision}; "
                    "reload the same RUN_ID before retrying"
                )
        elif state.get("_base_revision") not in (None, 0):
            raise StateError("state file disappeared while updating; refusing to recreate it")
        base_revision = state.get("_base_revision", state["revision"])
        state["revision"] = base_revision + 1
        append_event(state, event, task_id, **extra)
        state["updated_at"] = utc_now()
        state["overall_status"] = recompute_overall(state)
        validate_state(state)
        todo_content = render_todo(template_path, state, state_file)
        serialized_state = public_state(state)
        serialized = json.dumps(serialized_state, ensure_ascii=False, indent=2) + "\n"
        atomic_write(state_file, serialized)
        atomic_write(todo_file, todo_content)
        # Rewrite the sidecar atomically as well.  An append could leave a
        # partial line or an old history after a crash, making recovery lie
        # about which checkpoint produced an event.
        atomic_write(events_file, event_log_content(state["events"]))
        state["_base_revision"] = state["revision"]


def load_state(state_dir: Path, expected_run_id: str | None = None) -> dict[str, Any]:
    state_file, _, _, _ = state_paths(state_dir)
    state = read_json(state_file)
    validate_state(state, expected_run_id)
    validate_event_log(state_dir, state)
    validate_todo_projection(state_dir, state)
    state["_base_revision"] = state["revision"]
    return state


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    """Drop in-memory optimistic-lock metadata from persisted/printed JSON."""

    return {key: value for key, value in state.items() if not key.startswith("_")}


def resolve_template(args: argparse.Namespace) -> Path:
    if getattr(args, "template", None):
        return absolute_dir(args.template) if Path(args.template).is_dir() else Path(args.template).expanduser().resolve()
    return Path(__file__).resolve().parent.parent / "references" / "workflow-todo.template.md"


def ensure_state_dir(args: argparse.Namespace) -> Path:
    value = getattr(args, "state_dir", None)
    if not value:
        raise StateError("--state-dir is required")
    return absolute_dir(value)


def cmd_init(args: argparse.Namespace) -> int:
    state_dir = ensure_state_dir(args)
    state_file, todo_file, events_file, lock = state_paths(state_dir)
    if any(path.exists() for path in (state_file, todo_file, events_file)):
        raise StateError(f"refusing to overwrite an existing workflow run: {state_dir}")
    environment: dict[str, Any] = {}
    if args.environment_json:
        try:
            value = json.loads(args.environment_json)
        except json.JSONDecodeError as exc:
            raise StateError(f"--environment-json must be a JSON object: {exc}") from exc
        if not isinstance(value, dict):
            raise StateError("--environment-json must be a JSON object")
        environment = value
    validate_task_manifest()
    state = make_state(args.operator, safe_run_id(args.run_id), args.mode, environment, args.sdk_root)
    template_path = resolve_template(args)
    # Render and validate before creating any files. A bad custom template
    # must not leave a half-initialized run behind.
    validate_state(state)
    todo_content = render_todo(template_path, state, state_file)
    state_dir.mkdir(parents=True, exist_ok=True)
    with lock_file(lock):
        if any(path.exists() for path in (state_file, todo_file, events_file)):
            raise StateError(f"refusing to overwrite an existing workflow run: {state_dir}")
        append_event(state, "RUN_INITIALIZED", state["current_task"])
        serialized = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        atomic_write(state_file, serialized)
        atomic_write(todo_file, todo_content)
        atomic_write(events_file, event_log_content(state["events"]))
    print(f"WORKFLOW_STATE=INITIALIZED RUN_ID={state['run_id']}")
    print(f"STATE_FILE={state_file}")
    print(f"TODO_FILE={todo_file}")
    print(f"EVENTS_FILE={events_file}")
    print(f"ATTEMPT_TOKEN={state['tasks'][0]['attempt_token']}")
    return 0


def require_current(state: dict[str, Any], task_id: str) -> dict[str, Any]:
    if task_id not in TASK_BY_ID:
        raise StateError(f"unknown task: {task_id}")
    if state.get("current_task") != task_id:
        raise StateError(
            f"OUT_OF_ORDER expected={state.get('current_task')} requested={task_id}; "
            "resume the same run instead of skipping a task"
        )
    record = task_map(state)[task_id]
    return record


def cmd_start(args: argparse.Namespace) -> int:
    state_dir = ensure_state_dir(args)
    state = load_state(state_dir, args.run_id)
    if args.task in {"stage0.confirm", "terminal.report"}:
        raise StateError(f"{args.task} is controlled by its dedicated command")
    record = require_current(state, args.task)
    if record["status"] == "PASS":
        raise StateError(f"ALREADY_COMPLETE task={args.task}")
    if record["status"] not in {"PENDING", "NOT_RUN"}:
        raise StateError(f"cannot start task={args.task} from status={record['status']}")
    if args.task not in {"stage0.scope_environment", "stage5.final_docs"} and not state["execution_confirmed"]:
        raise StateError("EXECUTION_CONFIRM_REQUIRED: only stage0 read-only probing is allowed before confirmation")
    record["status"] = "RUNNING"
    record["attempts"] += 1
    record["started_at"] = record["started_at"] or utc_now()
    record["heartbeat_at"] = utc_now()
    record["owner_pid"] = args.owner_pid
    record["attempt_token"] = new_attempt_token()
    # A new lease must never inherit evidence from an abandoned attempt.
    record["evidence"] = []
    record["note"] = None
    state["artifacts"][args.task] = {
        "status": "RUNNING",
        "evidence": [],
        "updated_at": utc_now(),
    }
    persist(state_dir, state, resolve_template(args), "TASK_STARTED", args.task)
    print(f"TASK_STATUS={args.task}:RUNNING")
    print(f"ATTEMPT_TOKEN={record['attempt_token']}")
    return 0


def cmd_confirm(args: argparse.Namespace) -> int:
    state_dir = ensure_state_dir(args)
    state = load_state(state_dir, args.run_id)
    if state["execution_confirmed"] or state["confirmation_count"]:
        raise StateError("CONFIRMATION_ALREADY_RECORDED: this run accepts exactly one manual confirmation")
    if task_map(state)["stage0.scope_environment"]["status"] != "PASS":
        raise StateError("cannot confirm before stage0.scope_environment is PASS")
    if not args.phrase.strip():
        raise StateError("a non-empty confirmation phrase is required")
    if args.confirmed_mode != state["mode"]:
        raise StateError(
            f"CONFIRMED_MODE_MISMATCH expected={state['mode']} actual={args.confirmed_mode}; "
            "use a new RUN_ID for a different scope"
        )
    if args.sdk_root is not None:
        sdk_root = args.sdk_root.strip()
        if not is_absolute_path(sdk_root):
            raise StateError("sdk_root must be an absolute path supplied by the user")
        state["firmware_sdk_root"] = sdk_root
    if state["mode"] == "AUTO_ALL" and not state.get("firmware_sdk_root"):
        raise StateError(
            "AUTO_ALL confirmation requires the user's absolute firmware SDK path; "
            "pass --sdk-root now or initialize a new run with it"
        )
    record = require_current(state, "stage0.confirm")
    if record["status"] == "PENDING":
        record["status"] = "RUNNING"
        record["attempts"] += 1
        record["started_at"] = utc_now()
        record["heartbeat_at"] = record["started_at"]
        record["owner_pid"] = os.getpid()
    confirmed_at = utc_now()
    record["status"] = "PASS"
    record["completed_at"] = confirmed_at
    record["heartbeat_at"] = None
    record["owner_pid"] = None
    record["note"] = "唯一一次人工确认；后续常规阶段由 agent 自动执行"
    record["evidence"] = ["manual-confirmation"]
    state["execution_confirmed"] = True
    state["confirmation_count"] = 1
    state["confirmation"] = {
        "phrase": args.phrase.strip(),
        "mode": args.confirmed_mode,
        "at": confirmed_at,
        "sdk_root": state.get("firmware_sdk_root"),
    }
    state["artifacts"]["stage0.confirm"] = {
        "status": "PASS",
        "evidence": ["manual-confirmation"],
        "updated_at": confirmed_at,
    }
    state["current_task"] = next_task(state)
    persist(
        state_dir,
        state,
        resolve_template(args),
        "EXECUTION_CONFIRMED",
        "stage0.confirm",
        confirmed_mode=args.confirmed_mode,
    )
    print("EXECUTION_CONFIRM_GATE=PASS")
    print(f"NEXT_TASK={state['current_task']}")
    return 0


def cmd_finish(args: argparse.Namespace) -> int:
    state_dir = ensure_state_dir(args)
    state = load_state(state_dir, args.run_id)
    if args.task in {"stage0.confirm", "terminal.report"}:
        raise StateError(f"{args.task} is controlled by its dedicated command")
    record = require_current(state, args.task)
    if not args.attempt_token or args.attempt_token != record.get("attempt_token"):
        raise StateError(f"ATTEMPT_TOKEN_MISMATCH task={args.task}; use the token returned by start")
    if record["status"] != "RUNNING":
        raise StateError(f"task must be RUNNING before finish: {args.task}={record['status']}")
    status = args.status.upper()
    if status not in {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "NOT_REQUESTED"}:
        raise StateError("finish status must be PASS, FAIL, BLOCKED, NOT_RUN or NOT_REQUESTED")
    task = TASK_BY_ID[args.task]
    if status == "NOT_REQUESTED" and state["mode"] != "HOST_ONLY":
        raise StateError("NOT_REQUESTED is reserved for an explicit HOST_ONLY run")
    if status in {"NOT_RUN", "NOT_REQUESTED"} and task.stage not in {"stage6", "stage7"}:
        raise StateError("only board stages may be NOT_RUN/NOT_REQUESTED")
    evidence = normalized_evidence(args.evidence, args.task)
    record["status"] = status
    record["completed_at"] = utc_now()
    record["heartbeat_at"] = None
    record["owner_pid"] = None
    record["attempt_token"] = None
    record["evidence"] = list(dict.fromkeys(record["evidence"] + evidence))
    record["note"] = args.note
    state["artifacts"][args.task] = {
        "status": status,
        "evidence": list(record["evidence"]),
        "updated_at": utc_now(),
    }
    if status in {"FAIL", "BLOCKED", "NOT_RUN"}:
        # Freeze every later executable task. Host-only skips remain explicit.
        index = next(index for index, item in enumerate(state["tasks"]) if item["id"] == args.task)
        for later in state["tasks"][index + 1 :]:
            if later["id"] in {"stage5.final_docs", "terminal.report"}:
                continue
            if later["status"] == "PENDING":
                # An unavailable board stage leaves later board work visibly
                # unexecuted; a real failure remains a hard BLOCKED gate.
                later_status = "NOT_RUN" if status == "NOT_RUN" and later["stage"] in {"stage6", "stage7"} else "BLOCKED"
                later["status"] = later_status
                later["blocked_by"] = args.task
                later["note"] = f"由 {args.task} 的 {status} 阻断，尚未执行"
                later["evidence"] = [f"blocked-by:{args.task}"]
                state["artifacts"][later["id"]] = {
                    "status": later_status,
                    "evidence": list(later["evidence"]),
                    "updated_at": utc_now(),
                }
    state["current_task"] = next_task(state)
    persist(state_dir, state, resolve_template(args), "TASK_FINISHED", args.task, status=status)
    print(f"TASK_STATUS={args.task}:{status}")
    print(f"NEXT_TASK={state['current_task'] or 'NONE'}")
    return 0


def cmd_retry(args: argparse.Namespace) -> int:
    state_dir = ensure_state_dir(args)
    state = load_state(state_dir, args.run_id)
    records = task_map(state)
    if args.task not in records:
        raise StateError(f"unknown task: {args.task}")
    if args.task == "stage0.scope_environment" and state["execution_confirmed"]:
        raise StateError(
            "cannot retry stage0.scope_environment after execution confirmation; "
            "start a new RUN_ID for a changed environment or scope"
        )
    if args.task in {"stage0.confirm", "terminal.report"}:
        raise StateError(f"{args.task} is controlled by its dedicated command")
    target = records[args.task]
    if target["status"] not in {"FAIL", "BLOCKED", "NOT_RUN"}:
        raise StateError(f"only a failed/blocked/not-run task can be retried: {args.task}")
    if args.task == "stage0.confirm":
        raise StateError("the manual confirmation cannot be retried or requested twice")
    target_index = next(index for index, item in enumerate(state["tasks"]) if item["id"] == args.task)
    # Final document backfill is deliberately allowed to rerun after an
    # upstream terminal failure: its job is to record that failure, not to
    # pretend the failed stage passed.  All earlier work must still be
    # terminal; executable retries retain the stricter PASS-only gate.
    predecessor_statuses = TERMINAL_STATUSES if args.task == "stage5.final_docs" else {"PASS", "NOT_REQUESTED"}
    unresolved = [
        item["id"]
        for item in state["tasks"][:target_index]
        if item["status"] not in predecessor_statuses
    ]
    if unresolved:
        raise StateError(
            f"RETRY_PRECONDITION unresolved predecessor(s)={','.join(unresolved)}; "
            "retry the earliest failed task first"
        )
    invalidated_evidence: dict[str, list[str]] = {}

    def reset_for_retry(item: dict[str, Any]) -> None:
        if item["evidence"]:
            invalidated_evidence[item["id"]] = list(item["evidence"])
        item["evidence"] = []
        item["status"] = "PENDING"
        item["blocked_by"] = None
        item["started_at"] = None
        item["completed_at"] = None
        item["heartbeat_at"] = None
        item["owner_pid"] = None
        item["attempt_token"] = None

    target["status"] = "PENDING"
    reset_for_retry(target)
    target["note"] = args.note or "自动回流后重试"
    state["artifacts"][args.task] = {
        "status": "PENDING",
        "evidence": [],
        "updated_at": utc_now(),
    }
    for later in state["tasks"][target_index + 1 :]:
        # Any downstream result, including a previously finalized PASS, is
        # stale after an upstream retry and must be recomputed in this run.
        # Explicit HOST_ONLY board skips remain out of scope.
        if state["mode"] == "HOST_ONLY" and later["id"] in {
            "stage6.firmware_matrix",
            "stage7.board_matrix",
        }:
            continue
        reset_for_retry(later)
        later["note"] = None
        if later["id"] in state["artifacts"]:
            state["artifacts"][later["id"]] = {
                "status": "PENDING",
                "evidence": [],
                "updated_at": utc_now(),
            }
    state["current_task"] = args.task
    persist(
        state_dir,
        state,
        resolve_template(args),
        "TASK_RETRY_SCHEDULED",
        args.task,
        invalidated_evidence=invalidated_evidence,
    )
    print(f"RETRY_TASK={args.task}")
    return 0


def cmd_heartbeat(args: argparse.Namespace) -> int:
    state_dir = ensure_state_dir(args)
    state = load_state(state_dir, args.run_id)
    record = require_current(state, args.task)
    if record["status"] != "RUNNING":
        raise StateError(f"cannot heartbeat a non-running task: {args.task}")
    if not args.attempt_token or args.attempt_token != record.get("attempt_token"):
        raise StateError(f"ATTEMPT_TOKEN_MISMATCH task={args.task}; use the token returned by start")
    record["heartbeat_at"] = utc_now()
    if args.owner_pid is not None:
        record["owner_pid"] = args.owner_pid
    persist(state_dir, state, resolve_template(args), "TASK_HEARTBEAT", args.task)
    print(f"HEARTBEAT={args.task}")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    state_dir = ensure_state_dir(args)
    if args.stale_after < 0:
        raise StateError("--stale-after must be non-negative")
    state = load_state(state_dir, args.run_id)
    running = [item for item in state["tasks"] if item["status"] == "RUNNING"]
    if len(running) > 1:
        raise StateError("multiple RUNNING tasks found; refusing to guess which process owns the run")
    if running:
        item = running[0]
        heartbeat = item.get("heartbeat_at")
        age = float("inf")
        if heartbeat:
            stamp = parse_timestamp(heartbeat, f"task {item['id']} heartbeat_at")
            age = (datetime.now(timezone.utc) - stamp).total_seconds()
        owner_alive = False
        owner_pid = item.get("owner_pid")
        if isinstance(owner_pid, int) and owner_pid > 0:
            try:
                os.kill(owner_pid, 0)
                owner_alive = True
            except PermissionError:
                owner_alive = True
            except (OSError, ProcessLookupError):
                owner_alive = False
        if not args.force:
            if owner_pid is None and age < args.stale_after:
                raise StateError(
                    f"RUNNING task has no registered owner and is not stale: {item['id']}"
                )
            if owner_pid is not None and owner_alive and age < args.stale_after:
                raise StateError(f"RUNNING task requires its owner or --force recovery: {item['id']}")
        abandoned_evidence = list(item["evidence"])
        item["status"] = "PENDING"
        item["evidence"] = []
        item["started_at"] = None
        item["heartbeat_at"] = None
        item["owner_pid"] = None
        item["attempt_token"] = None
        item["note"] = "从中断运行恢复；未把中间产物视为通过"
        state["artifacts"][item["id"]] = {
            "status": "PENDING",
            "evidence": [],
            "updated_at": utc_now(),
        }
        state["current_task"] = item["id"]
        persist(
            state_dir,
            state,
            resolve_template(args),
            "RUNNING_TASK_RECOVERED",
            item["id"],
            abandoned_evidence=abandoned_evidence,
        )
    else:
        state["current_task"] = next_task(state)
        persist(state_dir, state, resolve_template(args), "WORKFLOW_RESUMED")
    print(f"RESUME_TASK={state['current_task'] or 'NONE'}")
    print(f"OP_WORKFLOW={recompute_overall(state)}")
    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    state_dir = ensure_state_dir(args)
    state = load_state(state_dir, args.run_id)
    if state["current_task"] is None and task_map(state)["terminal.report"]["status"] == "PASS":
        # A repeated status/finalize call is safe after a restarted agent; it
        # does not create a second terminal event or change the verdict.
        print(f"OP_WORKFLOW={state['overall_status']}")
        print(f"STATE_FILE={state_paths(state_dir)[0]}")
        print(f"TODO_FILE={state_paths(state_dir)[1]}")
        print(f"EVENTS_FILE={state_paths(state_dir)[2]}")
        return 0
    if state["current_task"] != "terminal.report":
        raise StateError(
            f"cannot finalize before all workflow tasks are terminal: current={state['current_task']}"
        )
    report = task_map(state)["terminal.report"]
    if report["status"] == "RUNNING":
        raise StateError("terminal report is still RUNNING; recover it with resume before finalizing")
    if report["status"] not in {"PENDING"}:
        raise StateError(f"terminal report cannot be finalized from status={report['status']}")
    evidence = normalized_evidence(args.evidence, "terminal.report")
    if report["status"] == "PENDING":
        report["status"] = "RUNNING"
        report["attempts"] += 1
        report["started_at"] = utc_now()
        report["heartbeat_at"] = report["started_at"]
        report["owner_pid"] = os.getpid()
    report["status"] = "PASS"
    report["completed_at"] = utc_now()
    report["heartbeat_at"] = None
    report["owner_pid"] = None
    report["evidence"] = list(dict.fromkeys(report["evidence"] + evidence))
    report["note"] = args.note or "逐阶段状态、证据和未完成原因已记录"
    state["artifacts"]["terminal.report"] = {
        "status": "PASS",
        "evidence": list(report["evidence"]),
        "updated_at": utc_now(),
    }
    state["current_task"] = None
    persist(state_dir, state, resolve_template(args), "WORKFLOW_FINALIZED", "terminal.report")
    print(f"OP_WORKFLOW={state['overall_status']}")
    print(f"STATE_FILE={state_paths(state_dir)[0]}")
    print(f"TODO_FILE={state_paths(state_dir)[1]}")
    print(f"EVENTS_FILE={state_paths(state_dir)[2]}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state_dir = ensure_state_dir(args)
    state = load_state(state_dir, args.run_id)
    if args.format == "json":
        print(json.dumps(public_state(state), ensure_ascii=False, indent=2))
    else:
        print(f"RUN_ID={state['run_id']}")
        print(f"OPERATOR={state['operator']}")
        print(f"MODE={state['mode']}")
        print(f"OP_WORKFLOW={state['overall_status']}")
        print(f"EXECUTION_CONFIRM_GATE={'PASS' if state['execution_confirmed'] else 'PENDING'}")
        print(f"CURRENT_TASK={state['current_task'] or 'NONE'}")
        for item in state["tasks"]:
            print(f"{item['id']}={item['status']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a TODO and a new checkpoint")
    init.add_argument("--state-dir", required=True)
    init.add_argument("--operator", required=True)
    init.add_argument("--run-id", required=True)
    init.add_argument("--mode", default="AUTO_ALL", choices=sorted(MODES))
    init.add_argument("--sdk-root")
    init.add_argument("--environment-json")
    init.add_argument("--template")
    init.set_defaults(func=cmd_init)

    confirm = sub.add_parser("confirm", help="record the single stage0 execution confirmation")
    confirm.add_argument("--state-dir", required=True)
    confirm.add_argument("--run-id", required=True)
    confirm.add_argument("--template")
    confirm.add_argument("--phrase", "--confirmation", "--message", dest="phrase", required=True)
    confirm.add_argument(
        "--confirmed-mode",
        required=True,
        choices=sorted(MODES),
        help="scope explicitly accepted by the user; must match the initialized run mode",
    )
    confirm.add_argument(
        "--sdk-root",
        help="user-confirmed absolute firmware SDK path when it was not supplied at init",
    )
    confirm.set_defaults(func=cmd_confirm)

    for name, help_text in (("start", "start the next task"), ("finish", "finish the current task"), ("retry", "schedule a failed task again"), ("heartbeat", "refresh a running task"), ("resume", "recover/continue a run"), ("finalize", "write the terminal report"), ("status", "show the checkpoint")):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--state-dir", required=True)
        command.add_argument("--run-id", required=True)
        command.add_argument("--template")
        if name == "start":
            command.add_argument("--task", required=True, choices=[task.task_id for task in TASKS])
            command.add_argument("--owner-pid", type=int)
            command.set_defaults(func=cmd_start)
        elif name == "finish":
            command.add_argument("--task", required=True, choices=[task.task_id for task in TASKS])
            command.add_argument("--status", required=True)
            command.add_argument("--attempt-token", "--attempt-id", dest="attempt_token")
            command.add_argument("--evidence", action="append", default=[])
            command.add_argument("--note", default=None)
            command.set_defaults(func=cmd_finish)
        elif name == "retry":
            command.add_argument("--task", required=True, choices=[task.task_id for task in TASKS])
            command.add_argument("--note")
            command.set_defaults(func=cmd_retry)
        elif name == "heartbeat":
            command.add_argument("--task", required=True, choices=[task.task_id for task in TASKS])
            command.add_argument("--attempt-token", "--attempt-id", dest="attempt_token")
            command.add_argument("--owner-pid", type=int)
            command.set_defaults(func=cmd_heartbeat)
        elif name == "resume":
            command.add_argument("--force", action="store_true", help="recover a still-running owner explicitly")
            command.add_argument("--stale-after", type=float, default=300.0)
            command.set_defaults(func=cmd_resume)
        elif name == "finalize":
            command.add_argument("--evidence", action="append", default=[])
            command.add_argument("--note")
            command.set_defaults(func=cmd_finalize)
        else:
            command.add_argument("--format", choices=("summary", "json"), default="summary")
            command.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except StateError as exc:
        print(f"WORKFLOW_STATE_ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"WORKFLOW_STATE_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
