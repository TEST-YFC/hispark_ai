#!/usr/bin/env python3
"""Capture or replay training serial logs; never claim numerical training PASS."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from training_protocol import DONE_PATTERN, parse_raw, read_json, write_json


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--port")
    source.add_argument("--input-log", type=Path, help="Replay saved raw bytes without device I/O")
    ap.add_argument("--baudrate", type=int, default=115200)
    ap.add_argument("--output", type=Path, help="New live raw log; optional copy path for replay")
    ap.add_argument("--protocol-output", type=Path, required=True)
    ap.add_argument("--expected", type=Path, help="Frozen Host expected JSON for identity binding")
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--fbb-monitor", action="store_true")
    ap.add_argument("--reset", action="store_true", help="Forward --reset to fbb monitor (live fbb only)")
    ap.add_argument("--sdk-dir", type=Path, help="Set child FBB_SDK_DIR; not forwarded as a CLI flag")
    a = ap.parse_args(argv)
    if not math.isfinite(a.seconds) or a.seconds <= 0 or a.baudrate <= 0:
        ap.error("seconds and baudrate must be positive and finite")
    if not a.input_log and not a.output:
        ap.error("live capture requires --output")
    if a.reset and (a.input_log or not a.fbb_monitor):
        ap.error("--reset requires live --fbb-monitor")
    if a.input_log and (a.fbb_monitor or a.sdk_dir):
        ap.error("replay cannot use live backend options")
    raw_path = (a.output or a.input_log).resolve()
    protocol_path = a.protocol_output.resolve()
    protected = [x.resolve() for x in (a.input_log, a.expected) if x]
    if protocol_path == raw_path or protocol_path in protected or (a.output and raw_path == (a.expected.resolve() if a.expected else None)):
        ap.error("input, expected, raw and protocol output paths must not overwrite each other")
    # Exclusive new attempt paths prevent stale evidence reuse.
    if protocol_path.exists() or (a.output and raw_path.exists()):
        ap.error("output already exists; use new attempt paths")
    expected = read_json(a.expected) if a.expected else None
    started = datetime.now(timezone.utc).isoformat()
    backend_rc = None
    transport_error = ""
    stdout = stderr = ""
    cmd = None
    raw = b""
    try:
        if a.input_log:
            raw = a.input_log.read_bytes()
            if a.output:
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                with raw_path.open("xb") as stream:
                    stream.write(raw)
        elif a.fbb_monitor:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            cmd = ["fbb", "monitor", "--port", a.port, "--baud", str(a.baudrate),
                   "--chip", "ws63", "--timeout", str(a.seconds), "--log", str(raw_path),
                   "--until", DONE_PATTERN, "--json-summary"]
            if a.reset:
                cmd.append("--reset")
            env = os.environ.copy()
            if a.sdk_dir:
                env["FBB_SDK_DIR"] = str(a.sdk_dir.resolve())
            proc = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace",
                                  capture_output=True, check=False, env=env, timeout=a.seconds + 30)
            backend_rc = proc.returncode
            stdout, stderr = proc.stdout, proc.stderr
            raw = raw_path.read_bytes()
        else:
            import serial
            deadline = time.monotonic() + a.seconds
            pending = b""
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            with raw_path.open("xb") as log, serial.Serial(a.port, a.baudrate, timeout=0.25) as ser:
                while time.monotonic() < deadline:
                    chunk = ser.readline()
                    if not chunk:
                        continue
                    log.write(chunk)
                    log.flush()
                    raw += chunk
                    pending += chunk
                    stop = False
                    while b"\n" in pending:
                        line, pending = pending.split(b"\n", 1)
                        if line.startswith(b"TRAIN_DONE "):
                            stop = parse_raw(raw, expected)["capture_complete"]
                    if stop:
                        break
            backend_rc = 0 if parse_raw(raw, expected)["capture_complete"] else 4
    except (OSError, ImportError, subprocess.SubprocessError) as exc:
        transport_error = str(exc)
        if isinstance(exc, subprocess.TimeoutExpired):
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            stdout = stdout.decode("utf-8", "replace") if isinstance(stdout, bytes) else stdout
            stderr = stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else stderr
        if raw_path.exists():
            raw = raw_path.read_bytes()
    payload = parse_raw(raw, expected)
    payload.update({"raw_log": str(raw_path), "port": a.port, "baudrate": a.baudrate,
                    "capture_attempt_id": uuid.uuid4().hex, "started_at_utc": started,
                    "ended_at_utc": datetime.now(timezone.utc).isoformat(),
                    "backend": "replay" if a.input_log else ("fbb" if a.fbb_monitor else "pyserial"),
                    "backend_returncode": backend_rc, "backend_command": cmd,
                    "backend_stdout": stdout, "backend_stderr": stderr,
                    "transport_error": transport_error,
                    "transport_status": "NOT_RUN" if a.input_log and not transport_error else
                        ("PASS" if backend_rc == 0 and not transport_error else "FAIL")})
    write_json(protocol_path, payload)
    print(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    return 0 if payload["capture_complete"] and not transport_error and (a.input_log or backend_rc == 0) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
