#!/usr/bin/env python3
"""Measure WS63 prediction latency from HiSpark.AI serial tick markers."""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from collections import deque
from datetime import datetime
from pathlib import Path


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
PREDICT_OK_RE = re.compile(
    r"\[AI_MCU\]\[PREDICT\]\s+OK\s+seq=(\d+)\s+ticks=(-?\d+)"
)
FAIL_RE = re.compile(r"\[AI_MCU\]\[FAIL\]\s+stage=([A-Z0-9_]+)\s+code=(-?\d+)")
STAGE_RE = re.compile(r"\[AI_MCU\]\[(TASK|INIT|PREDICT)\]\s+([^\r\n]+)")
CREATE_FAIL = "[AI_MCU][TASK] CREATE_FAIL"


class ProtocolError(RuntimeError):
    """Raised when firmware reports failure or an invalid sample sequence."""


class ProtocolState:
    def __init__(self):
        self.last_stage = "no firmware log observed"
        self.last_sequence = None

    def consume(self, line):
        failure = FAIL_RE.search(line)
        if failure:
            self.last_stage = f"FAIL {failure.group(1)}"
            raise ProtocolError(
                f"firmware failure: stage={failure.group(1)} code={failure.group(2)}"
            )
        if CREATE_FAIL in line:
            self.last_stage = "TASK CREATE_FAIL"
            raise ProtocolError("firmware failure: task creation failed")
        stage = STAGE_RE.search(line)
        if stage:
            self.last_stage = f"{stage.group(1)} {stage.group(2)}"
        success = PREDICT_OK_RE.search(line)
        if not success:
            return None
        sequence = int(success.group(1))
        ticks = int(success.group(2))
        if sequence <= 0:
            raise ProtocolError(f"invalid prediction sequence: {sequence}")
        if ticks <= 0:
            raise ProtocolError(f"invalid prediction ticks: {ticks}")
        if self.last_sequence is not None and sequence != self.last_sequence + 1:
            raise ProtocolError(
                f"prediction sequence is not contiguous: {self.last_sequence} -> {sequence}"
            )
        self.last_sequence = sequence
        self.last_stage = f"PREDICT OK seq={sequence}"
        return sequence, ticks


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Read WS63 prediction ticks and save one stable latency window."
    )
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--port", required=True)
    parser.add_argument("--baudrate", type=int, required=True)
    parser.add_argument("--window", type=int, default=50)
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--ticks-per-us", type=float, required=True)
    parser.add_argument("--stable-tolerance", type=float, default=0.05)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=110.0)
    parser.add_argument(
        "--accuracy-proof",
        required=True,
        help="hs-debug-op-board-accuracy log containing ACCURACY_VERDICT=PASS",
    )
    parser.add_argument("--raw-log", required=True)
    return parser.parse_args(argv)


def validate_args(args):
    if not SAFE_ID.fullmatch(args.execution_id):
        raise ValueError("--execution-id contains unsafe characters")
    if args.baudrate <= 0:
        raise ValueError("--baudrate must be positive")
    if args.window < 2:
        raise ValueError("--window must be at least 2")
    if args.ticks_per_us <= 0:
        raise ValueError("--ticks-per-us must be positive")
    if not 0 <= args.stable_tolerance < 1:
        raise ValueError("--stable-tolerance must be in [0, 1)")
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be positive")


def validate_accuracy_proof(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    markers = re.findall(r"(?:^|\s)ACCURACY_VERDICT=([A-Z]+)", text)
    if not markers or any(value != markers[-1] for value in markers) or markers[-1] != "PASS":
        raise ValueError("--accuracy-proof requires a non-conflicting terminal PASS")


def ticks_to_us(ticks, ticks_per_us):
    return ticks / ticks_per_us


def render_table(samples, sequence, tick, port, baudrate, window, ticks_per_us):
    average = sum(samples) / len(samples)
    rows = [
        ("Current tick", f"{tick}", f"{ticks_to_us(tick, ticks_per_us):.3f}"),
        ("Sequence", f"{sequence}", "-"),
        ("Window samples", f"{len(samples)}/{window}", "-"),
        ("Average", f"{average:.3f}", f"{ticks_to_us(average, ticks_per_us):.3f}"),
        ("Minimum", f"{min(samples)}", f"{ticks_to_us(min(samples), ticks_per_us):.3f}"),
        ("Maximum", f"{max(samples)}", f"{ticks_to_us(max(samples), ticks_per_us):.3f}"),
        ("Range", f"{max(samples) - min(samples)}", f"{ticks_to_us(max(samples) - min(samples), ticks_per_us):.3f}"),
    ]
    lines = [
        f"WS63 prediction monitor port={port} baudrate={baudrate} updated={datetime.now():%H:%M:%S}",
        "+----------------+----------------+----------------+",
        "| Metric         | Ticks          | Microseconds    |",
        "+----------------+----------------+----------------+",
    ]
    lines.extend(f"| {name:<14} | {ticks:>14} | {us:>14} |" for name, ticks, us in rows)
    lines.append("+----------------+----------------+----------------+")
    return "\n".join(lines)


def print_status(samples, sequence, tick, args):
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(
        render_table(
            samples, sequence, tick, args.port, args.baudrate, args.window,
            args.ticks_per_us,
        )
    )
    sys.stdout.write("\n")
    sys.stdout.flush()


def is_stable(samples, tolerance):
    if len(samples) < 2:
        return False
    average = sum(samples) / len(samples)
    return average > 0 and all(abs(sample - average) / average <= tolerance for sample in samples)


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def build_result(args, samples):
    average_ticks = sum(samples) / len(samples)
    protocol = {
        "ticks_per_us": float(args.ticks_per_us),
        "window": int(args.window),
        "stable_tolerance": float(args.stable_tolerance),
        "timeout_seconds": float(args.timeout_seconds),
    }
    return {
        "format_version": 2,
        "execution_id": args.execution_id,
        "passed": True,
        "metric": {
            "name": "latency",
            "value": ticks_to_us(average_ticks, args.ticks_per_us),
            "unit": "us",
        },
        "protocol": protocol,
        "samples_ticks": list(samples),
        "statistics": {
            "average_ticks": average_ticks,
            "minimum_ticks": min(samples),
            "maximum_ticks": max(samples),
        },
        "accuracy": {"passed": True, "source": "hs-debug-op-board-accuracy"},
    }


def main(argv=None):
    args = parse_args(argv)
    validate_args(args)
    validate_accuracy_proof(args.accuracy_proof)
    try:
        import serial
    except ImportError:
        print("pyserial is required. Install it with: pip install pyserial", file=sys.stderr)
        return 1

    samples = deque(maxlen=args.window)
    protocol = ProtocolState()
    started_at = time.monotonic()
    raw_path = Path(args.raw_log)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = serial.Serial(args.port, args.baudrate, timeout=1)
    except serial.SerialException as exc:
        print(f"Failed to open serial port {args.port}: {exc}", file=sys.stderr)
        return 1

    try:
        with raw_path.open("w", encoding="utf-8") as raw_log, connection:
            print(
                f"Reading {args.port} at {args.baudrate}; window={args.window}; "
                f"tolerance={args.stable_tolerance * 100:.1f}%",
                flush=True,
            )
            while True:
                if time.monotonic() - started_at >= args.timeout_seconds:
                    print(
                        "Timed out waiting for stable prediction samples; "
                        f"last stage: {protocol.last_stage}",
                        file=sys.stderr,
                    )
                    return 1
                raw = connection.readline()
                if not raw:
                    continue
                line = raw.decode(args.encoding, errors="replace").strip()
                raw_log.write(line + "\n")
                raw_log.flush()
                try:
                    sample = protocol.consume(line)
                except ProtocolError as exc:
                    print(str(exc), file=sys.stderr)
                    return 1
                if sample is None:
                    continue
                sequence, ticks = sample
                samples.append(ticks)
                print_status(samples, sequence, ticks, args)
                if len(samples) == args.window and is_stable(samples, args.stable_tolerance):
                    result = build_result(args, samples)
                    _atomic_json(args.output, result)
                    print(f"LATENCY_VERDICT=PASS value={result['metric']['value']:.6f}us")
                    return 0
    except KeyboardInterrupt:
        print("\nInterrupted before a stable metric was saved.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
