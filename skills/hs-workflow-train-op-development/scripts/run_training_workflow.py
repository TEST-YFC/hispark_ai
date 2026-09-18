#!/usr/bin/env python3
"""按固定顺序运行训练阶段命令；命令成功不代表训练证据已经通过审计。"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ORDER = ["design", "implementation", "build", "model", "host", "aggregate", "board", "final"]


def write_summary(path, payload):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_command(command, cwd, timeout, log, env):
    """保存实时日志，超时终止本命令的进程组，不读取旧日志。"""
    options = {"cwd": cwd, "env": env}
    if os.name == "posix":
        options["start_new_session"] = True
    elif os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    with log.open("x", encoding="utf-8") as stream:
        try:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, **options)
        except OSError as exc:
            stream.write(f"PROCESS START FAILED: {exc}\n")
            return {"status": "FAIL", "reason": str(exc), "error_type": type(exc).__name__}
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                # PID comes directly from this invocation, never from a name-based search.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                if process.poll() is None:
                    process.kill()
            process.wait()
            stream.write(f"\nTIMEOUT after {timeout}s\n")
            return {"status": "FAIL", "reason": "命令超时", "timed_out": True,
                    "returncode": process.returncode}
    return {"status": "PASS" if code == 0 else "FAIL", "returncode": code}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--allow-board-not-run", action="store_true")
    args = parser.parse_args(argv)
    raw = args.plan.read_bytes()
    plan = json.loads(raw.decode("utf-8"))
    if not isinstance(plan, dict) or plan.get("verification_kind") != "training":
        raise ValueError("verification_kind must be training")
    stages = plan.get("stages")
    if not isinstance(stages, dict) or set(stages) - set(ORDER):
        raise ValueError("stages must be an object containing only known stages")
    run_dir = args.run_dir.resolve()
    run_id = plan.get("run_id", run_dir.name)
    if not isinstance(run_id, str) or run_id != run_dir.name:
        raise ValueError("run_id must match run-dir name")
    # Never erase or overwrite previous execution evidence.
    if run_dir.exists() and (not run_dir.is_dir() or any(run_dir.iterdir())):
        raise ValueError("run-dir must be new or empty")
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "train_workflow_summary.json"
    results = []
    blocked = False
    summary = {"schema_version": 2, "verification_kind": "training", "run_id": run_id,
               "plan_sha256": hashlib.sha256(raw).hexdigest(), "started_at_unix": time.time(),
               "status": "RUNNING", "command_status": "RUNNING", "workflow_status": "NOT_VERIFIED",
               "evidence_status": "NOT_CHECKED", "board_verified": False, "stages": results}
    write_summary(summary_path, summary)
    for name in ORDER:
        item = stages.get(name, {})
        if blocked and name != "final":
            results.append({"stage": name, "status": "NOT_RUN", "reason": "前一阶段未通过"})
            write_summary(summary_path, summary)
            continue
        if not isinstance(item, dict):
            item = {"invalid": True}
        command = item.get("command")
        enabled = item.get("enabled", True)
        reason = item.get("reason")
        skip = name == "board" and (enabled is False or command is None or command == [])
        if skip and args.allow_board_not_run and isinstance(reason, str) and reason.strip():
            results.append({"stage": name, "status": "NOT_REQUESTED" if enabled is False else "NOT_RUN",
                            "reason": reason, "policy_skip": True})
            write_summary(summary_path, summary)
            continue
        error = None
        if enabled is not True:
            error = "必需阶段不能禁用；板端排除须显式允许并提供原因"
        elif not isinstance(command, list) or not command or not command[0] or any(not isinstance(x, str) for x in command):
            error = "未提供有效阶段命令"
        elif "invalid" in item:
            error = "阶段配置必须是对象"
        try:
            timeout = float(item.get("timeout", 3600))
            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError("timeout must be positive and finite")
        except (ValueError, TypeError) as exc:
            error = str(exc)
        if error:
            results.append({"stage": name, "status": "FAIL", "reason": error})
            blocked = True
            write_summary(summary_path, summary)
            continue
        env = os.environ.copy()
        env.update(TRAIN_WORKFLOW_SUMMARY=str(summary_path), TRAIN_RUN_ID=run_id,
                   TRAIN_PREVIOUS_COMMAND_STATUS="FAIL" if blocked else "PASS")
        if name == "final":
            summary["command_status"] = "FAIL" if blocked else "RUNNING"
            write_summary(summary_path, summary)
        started = time.monotonic()
        log = run_dir / f"{name}.log"
        try:
            result = run_command(command, item.get("cwd"), timeout, log, env)
        except (OSError, ValueError, TypeError) as exc:
            result = {"status": "FAIL", "reason": str(exc), "error_type": type(exc).__name__}
        results.append({"stage": name, "argv": command, "log": log.name,
                        "elapsed_sec": round(time.monotonic() - started, 3), **result})
        blocked = blocked or result["status"] != "PASS"
        write_summary(summary_path, summary)
    summary.update(status="FAIL" if blocked else "COMMANDS_COMPLETED",
                   command_status="FAIL" if blocked else "PASS", finished_at_unix=time.time())
    write_summary(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 2 if blocked else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
