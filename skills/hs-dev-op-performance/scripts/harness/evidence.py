"""Validate evidence emitted by HiSpark.AI operator skills."""

import json
import math
import re
from pathlib import Path


class EvidenceError(RuntimeError):
    """Raised when an evidence file is missing or not terminally passing."""


def _read(path, label):
    source = Path(path)
    if not source.is_file():
        raise EvidenceError(f"{label} not found: {source}")
    return source.read_text(encoding="utf-8", errors="replace")


def validate_host_summary(path, expected_operator, expected_framework, expected_mode):
    text = _read(path, "Host summary")
    verdicts = list(re.finditer(r"^VERDICT(?::|=)\s*(.+)$", text, re.MULTILINE))
    exits = list(re.finditer(r"^HARNESS_EXIT=(\d+)$", text, re.MULTILINE))
    if len(verdicts) != 1 or len(exits) != 1:
        raise EvidenceError("Host summary requires one VERDICT and one HARNESS_EXIT")
    if exits[0].start() <= verdicts[0].end():
        raise EvidenceError("HARNESS_EXIT must follow VERDICT")
    if text[verdicts[0].end():exits[0].start()].strip():
        raise EvidenceError("HARNESS_EXIT must be adjacent to VERDICT")
    verdict = verdicts[0].group(1)
    if exits[0].group(1) != "0" or re.search(r"\b[1-9]\d* FAIL\b", verdict):
        raise EvidenceError("Host accuracy did not pass")
    if re.search(r"^(?:ERROR|CASES_REDUCED)\b", text, re.MULTILINE):
        raise EvidenceError("Host summary contains an error or reduced denominator")
    operator = re.search(r"\bop=([^\s]+)", text)
    if operator is None or operator.group(1) != expected_operator:
        actual = operator.group(1) if operator else None
        raise EvidenceError(
            f"Host operator mismatch: {actual!r} != {expected_operator!r}"
        )
    header = re.search(r"^op=.*frameworks=(\[[^\n]+\]).*paths=(\[[^\n]+\])$", text, re.MULTILINE)
    if header is None:
        raise EvidenceError("Host summary is missing frameworks/paths identity")
    if not re.search(rf"['\"]{re.escape(expected_framework)}['\"]", header.group(1)):
        raise EvidenceError(f"Host summary does not cover {expected_framework}")
    if expected_mode not in header.group(2):
        raise EvidenceError(f"Host summary does not cover {expected_mode}")
    return {"verdict": verdict, "exit_code": 0}


def _terminal_marker(text, name, accepted=("PASS",)):
    matches = re.findall(rf"(?:^|\s){re.escape(name)}=([A-Z]+)", text)
    if not matches:
        raise EvidenceError(f"missing {name}")
    if any(value != matches[-1] for value in matches):
        raise EvidenceError(f"conflicting {name} markers: {matches}")
    if matches[-1] not in accepted:
        raise EvidenceError(f"{name} is {matches[-1]}, expected {accepted}")
    return matches[-1]


def validate_build_log(path, execution_id):
    text = _read(path, "firmware build log")
    run_ids = re.findall(r"^HS_PERF_EXECUTION_ID=([^\s]+)$", text, re.MULTILINE)
    if not run_ids or any(value != execution_id for value in run_ids):
        raise EvidenceError("firmware build log execution ID mismatch")
    firmware_hashes = re.findall(
        r"^HS_PERF_FIRMWARE_SHA256=([0-9a-f]{64})$", text, re.MULTILINE
    )
    if len(firmware_hashes) != 1:
        raise EvidenceError("firmware build log requires one firmware SHA256")
    return {
        "execution_id": execution_id,
        "fwpkg_build": _terminal_marker(text, "FWPKG_BUILD"),
        "firmware_sha256": firmware_hashes[0],
    }


def _artifact_identity(text, execution_id, label):
    run_ids = re.findall(r"^HS_PERF_EXECUTION_ID=([^\s]+)$", text, re.MULTILINE)
    if not run_ids or any(value != execution_id for value in run_ids):
        raise EvidenceError(f"{label} execution ID mismatch")
    hashes = re.findall(r"^HS_PERF_FIRMWARE_SHA256=([0-9a-f]{64})$", text, re.MULTILINE)
    if len(hashes) != 1:
        raise EvidenceError(f"{label} requires one firmware SHA256")
    return hashes[0]


def validate_flash_log(path, execution_id):
    text = _read(path, "flash log")
    result = {
        "execution_id": execution_id,
        "firmware_sha256": _artifact_identity(text, execution_id, "flash log"),
        "flash": _terminal_marker(text, "FLASH_VERDICT"),
    }
    if "ACCURACY_VERDICT=" in text:
        result["accuracy"] = _terminal_marker(text, "ACCURACY_VERDICT")
    return result


def validate_board_log(path, execution_id):
    text = _read(path, "board accuracy log")
    return {
        "execution_id": execution_id,
        "firmware_sha256": _artifact_identity(text, execution_id, "board log"),
        "accuracy": _terminal_marker(text, "ACCURACY_VERDICT"),
    }


def validate_serial_log(path, metric):
    text = _read(path, "serial raw log")
    ticks = [
        int(value) for value in re.findall(
            r"\[AI_MCU\]\[PREDICT\]\s+OK\s+seq=\d+\s+ticks=(\d+)", text
        )
    ]
    expected = metric.get("samples_ticks") or []
    if len(ticks) < len(expected) or ticks[-len(expected):] != expected:
        raise EvidenceError("serial log does not contain the metric's final sample window")
    return {"sample_count": len(ticks), "stable_window": expected}


def load_metric(path, execution_id, protocol):
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid metric result {source}: {exc}") from exc
    metric = data.get("metric")
    if data.get("format_version") != 2 or data.get("passed") is not True:
        raise EvidenceError("onboard metric result is not passing format_version=2")
    if data.get("execution_id") != execution_id:
        raise EvidenceError("onboard metric execution ID mismatch")
    if data.get("protocol") != protocol:
        raise EvidenceError("onboard metric protocol differs from prepared run")
    if not isinstance(metric, dict):
        raise EvidenceError("onboard metric is missing")
    name, value, unit = metric.get("name"), metric.get("value"), metric.get("unit")
    if name != "latency" or unit != "us":
        raise EvidenceError(f"metric mismatch: {name!r}/{unit!r} != 'latency'/'us'")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError("metric value must be numeric")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise EvidenceError("metric value must be finite and positive")
    samples = data.get("samples_ticks")
    if not isinstance(samples, list) or len(samples) != protocol["window"]:
        raise EvidenceError("metric must retain the complete stable sample window")
    if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in samples):
        raise EvidenceError("metric samples must be positive integer ticks")
    return data, value
