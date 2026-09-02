#!/usr/bin/env python3
"""Validate full board-case coverage and write deterministic delivery reports."""

import argparse
import json
import re
import sys
from pathlib import Path


IDENTITY_FIELDS = ("framework", "case_id", "mode")
PASS_EVIDENCE = ("model", "input_dir", "gt_dir", "firmware",
                 "flash_log", "monitor", "accuracy_log", "serial_probe")


def identity(item):
    if not isinstance(item, dict):
        raise ValueError("case record must be a JSON object")
    values = []
    for name in IDENTITY_FIELDS:
        if name not in item:
            raise ValueError(f"missing identity field {name}")
        value = item[name]
        allowed = (str, int) if name == "case_id" else (str,)
        if isinstance(value, bool) or not isinstance(value, allowed):
            kind = "string or integer" if name == "case_id" else "string"
            raise ValueError(f"identity field {name} must be a {kind}")
        normalized = str(value)
        if not normalized or normalized != normalized.strip():
            raise ValueError(f"identity field {name} must be non-empty without surrounding whitespace")
        values.append(normalized)
    return tuple(values)


def _read_text(path):
    """Read tool output written as UTF-8, BOM/UTF-16, or a Windows code page."""
    raw = Path(path).read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            pass
    utf8_text = raw.decode("utf-8", errors="replace")
    if "[AI_MCU]" in utf8_text or "ACCURACY_VERDICT" in utf8_text:
        return utf8_text
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\x00" not in text:
            return text
    for encoding in ("utf-16-le", "utf-16-be"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_json(path):
    return json.loads(_read_text(path))


def last_json_line(path):
    lines = [line.strip() for line in _read_text(path).splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"flash log has no non-empty lines: {path}")
    final_line = lines[-1]
    try:
        payload = json.loads(final_line)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"flash log final non-empty line is not valid JSON: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"flash log final JSON is not an object: {path}")
    return payload


def validate_pass_evidence(result, expected):
    errors = []
    evidence_paths = {}
    for field in PASS_EVIDENCE:
        raw = result.get(field)
        if not raw:
            errors.append(f"missing PASS evidence field {field}")
            continue
        if not isinstance(raw, str) or raw != raw.strip():
            errors.append(f"PASS evidence field {field} must be a non-empty path string")
            continue
        path = Path(raw)
        evidence_paths[field] = path
        if not path.is_absolute() or not path.exists():
            errors.append(f"{field} missing/not absolute: {path}")
        elif path.is_file() and path.stat().st_size == 0:
            errors.append(f"{field} is empty: {path}")

    for field in ("model", "input_dir", "gt_dir"):
        expected_raw = expected.get(field)
        if not isinstance(expected_raw, str) or not expected_raw or expected_raw != expected_raw.strip():
            errors.append(f"Host matrix field {field} must be a non-empty path string")
            continue
        expected_path = Path(expected_raw)
        if not expected_path.is_absolute():
            errors.append(f"Host matrix field {field} is not absolute: {expected_path}")
            continue
        result_path = evidence_paths.get(field)
        if result_path is not None and result_path.is_absolute():
            if result_path.resolve() != expected_path.resolve():
                errors.append(f"{field} does not match Host matrix")

    flash_log = evidence_paths.get("flash_log")
    if flash_log is not None and flash_log.is_file():
        try:
            flash = last_json_line(flash_log)
            if flash.get("success") is not True:
                errors.append("flash log final JSON is not success=true")
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

    accuracy_log = evidence_paths.get("accuracy_log")
    if accuracy_log is not None and accuracy_log.is_file():
        text = _read_text(accuracy_log)
        if re.search(r"ACCURACY_VERDICT=PASS\s*$", text, re.MULTILINE) is None:
            errors.append("accuracy log has no exact ACCURACY_VERDICT=PASS")
    serial_probe = evidence_paths.get("serial_probe")
    if serial_probe is not None and serial_probe.is_file():
        try:
            probe = load_json(serial_probe)
            if not isinstance(probe, dict) or not probe.get("probed_at_utc"):
                errors.append("serial_probe is not a valid probe receipt")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid serial_probe receipt: {exc}")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", required=True,
                        help="Host-generated board_expected_matrix.json")
    parser.add_argument("--results-dir", required=True,
                        help="directory containing one */board_result.json per expected row")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    expected_path = Path(args.expected).resolve()
    results_dir = Path(args.results_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    errors = []

    try:
        manifest = load_json(expected_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BOARD_MATRIX_GATE=FAIL reason=invalid_expected_manifest detail={exc}")
        return 1
    if not isinstance(manifest, dict):
        print("BOARD_MATRIX_GATE=FAIL reason=invalid_expected_manifest detail=root must be a JSON object")
        return 1
    for field in ("run_id", "operator"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value or value != value.strip():
            errors.append(f"manifest {field} must be a non-empty string")

    expected_cases = manifest.get("cases")
    if not isinstance(expected_cases, list) or not expected_cases:
        errors.append("expected matrix must contain at least one board case")
        expected_cases = []
    if manifest.get("expected_count") != len(expected_cases):
        errors.append("expected_count does not match cases length")

    expected_by_key = {}
    for index, item in enumerate(expected_cases):
        try:
            key = identity(item)
        except ValueError as exc:
            errors.append(f"invalid expected identity at index {index}: {exc}")
            continue
        if key in expected_by_key:
            errors.append(f"duplicate expected identity: {key}")
        else:
            expected_by_key[key] = item
        if item.get("host_status") != "PASS":
            errors.append(f"Host variant is not PASS: {key}")

    results_by_key = {}
    if results_dir.is_dir():
        for path in sorted(results_dir.rglob("board_result.json")):
            try:
                item = load_json(path)
                key = identity(item)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                errors.append(f"invalid result JSON {path}: {exc}")
                continue
            item["result_file"] = str(path.resolve())
            if key in results_by_key:
                errors.append(f"duplicate board result identity: {key}")
            else:
                results_by_key[key] = item
    else:
        errors.append(f"results directory missing: {results_dir}")

    for key in sorted(set(results_by_key) - set(expected_by_key)):
        errors.append(f"unexpected board result identity: {key}")

    rows = []
    pass_count = fail_count = not_run_count = 0
    for key, expected in expected_by_key.items():
        result = results_by_key.get(key)
        if result is None:
            status, reason = "NOT_RUN", "missing board_result.json"
            not_run_count += 1
        else:
            if result.get("run_id") != manifest.get("run_id"):
                errors.append(f"run_id mismatch: {key}")
            if result.get("operator") != manifest.get("operator"):
                errors.append(f"operator mismatch: {key}")
            status = result.get("status")
            reason = str(result.get("reason", ""))
            if status == "PASS":
                evidence_errors = validate_pass_evidence(result, expected)
                if evidence_errors:
                    status = "FAIL"
                    reason = "; ".join(evidence_errors)
                    errors.extend(f"{key}: {item}" for item in evidence_errors)
                    fail_count += 1
                else:
                    pass_count += 1
            elif status == "FAIL":
                fail_count += 1
                if not reason:
                    errors.append(f"FAIL result has no reason: {key}")
            elif status == "NOT_RUN":
                not_run_count += 1
                if not reason:
                    errors.append(f"NOT_RUN result has no reason: {key}")
            else:
                fail_count += 1
                status = "FAIL"
                reason = f"invalid status: {result.get('status')!r}"
                errors.append(f"{key}: {reason}")
        rows.append({
            "framework": key[0], "case_id": key[1], "mode": key[2],
            "status": status, "reason": reason,
            "result_file": "" if result is None else result.get("result_file", ""),
        })

    # Keep the manifest's raw row count as the denominator.  A duplicate
    # identity is still an invalid manifest and must fail, but collapsing it
    # into expected_by_key must not make the report appear complete.
    expected_count = len(expected_cases)
    recorded_count = len(set(results_by_key) & set(expected_by_key))
    # A NOT_RUN receipt only accounts for why a row was skipped.  It is not
    # evidence that real-board flash/serial/accuracy execution happened.
    executed_count = pass_count + fail_count
    if errors or fail_count:
        accuracy_verdict = "FAIL"
    elif not_run_count or executed_count != expected_count:
        accuracy_verdict = "NOT_RUN"
    else:
        accuracy_verdict = "PASS"
    matrix_gate = accuracy_verdict

    report = {
        "schema_version": 2,
        "run_id": manifest.get("run_id"),
        "operator": manifest.get("operator"),
        "expected_manifest": str(expected_path),
        "expected": expected_count,
        "recorded": recorded_count,
        "executed": executed_count,
        "passed": pass_count,
        "failed": fail_count,
        "not_run": not_run_count,
        "board_matrix_gate": matrix_gate,
        "accuracy_verdict": accuracy_verdict,
        "errors": errors,
        "cases": rows,
    }
    json_path = output_dir / "board_case_results.json"
    summary_path = output_dir / "board_verify_summary.txt"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    lines = [
        f"RUN_ID={report['run_id']}",
        f"operator={report['operator']}",
        f"BOARD_RECORDS expected={expected_count} recorded={recorded_count}",
        f"BOARD_MATRIX expected={expected_count} executed={executed_count} "
        f"pass={pass_count} fail={fail_count} not_run={not_run_count}",
    ]
    for row in rows:
        lines.append(
            f"{row['framework']} tc{row['case_id']} {row['mode']} "
            f"{row['status']}" + (f" reason={row['reason']}" if row['reason'] else "")
        )
    lines.extend([
        f"BOARD_MATRIX_GATE={matrix_gate}",
        f"ACCURACY_VERDICT={accuracy_verdict}",
    ])
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"BOARD_CASE_RESULTS={json_path}")
    print(f"BOARD_VERIFY_SUMMARY={summary_path}")
    return 0 if matrix_gate == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
