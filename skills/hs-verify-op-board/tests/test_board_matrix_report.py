import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "board_matrix_report.py"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def make_expected(tmp_path, count=2):
    cases = []
    for idx in range(1, count + 1):
        case = tmp_path / "host" / f"tc{idx}"
        (case / "model").mkdir(parents=True, exist_ok=True)
        (case / "input").mkdir()
        (case / "gt").mkdir()
        (case / "model" / "model.onnx").write_bytes(b"model")
        cases.append({
            "operator": "Add", "framework": "onnx", "case_id": str(idx),
            "mode": "fp32", "host_path": "riscv_fp32", "host_status": "PASS",
            "model": str((case / "model" / "model.onnx").resolve()),
            "input_dir": str((case / "input").resolve()),
            "gt_dir": str((case / "gt").resolve()),
        })
    manifest = tmp_path / "board_expected_matrix.json"
    write_json(manifest, {
        "schema_version": 1, "run_id": "run-1", "operator": "Add",
        "expected_count": len(cases), "cases": cases,
    })
    return manifest, cases


def make_pass_result(tmp_path, case):
    evidence = tmp_path / "evidence" / f"tc{case['case_id']}"
    evidence.mkdir(parents=True)
    firmware = evidence / "firmware.fwpkg"
    flash = evidence / "flash.log"
    monitor = evidence / "monitor.log"
    accuracy = evidence / "accuracy.log"
    serial_probe = evidence / "serial_probe.json"
    firmware.write_bytes(b"firmware")
    flash.write_text('{"success": true}\n', encoding="utf-8")
    monitor.write_text("tensor output", encoding="utf-8")
    accuracy.write_text("ACCURACY_VERDICT=PASS\n", encoding="utf-8")
    serial_probe.write_text(
        '{"schema_version": 1, "probed_at_utc": "2026-01-01T00:00:00Z"}\n',
        encoding="utf-8",
    )
    return {
        "run_id": "run-1", "operator": "Add",
        "framework": case["framework"], "case_id": case["case_id"],
        "mode": case["mode"], "status": "PASS",
        "model": case["model"], "input_dir": case["input_dir"],
        "gt_dir": case["gt_dir"], "firmware": str(firmware.resolve()),
        "flash_log": str(flash.resolve()), "monitor": str(monitor.resolve()),
        "accuracy_log": str(accuracy.resolve()),
        "serial_probe": str(serial_probe.resolve()),
    }


def run_report(manifest, results, output):
    return subprocess.run([
        sys.executable, str(SCRIPT), "--expected", str(manifest),
        "--results-dir", str(results), "--output-dir", str(output),
    ], text=True, capture_output=True, check=False)


def test_full_matrix_requires_every_expected_case(tmp_path):
    manifest, cases = make_expected(tmp_path)
    results = tmp_path / "results"
    write_json(results / "tc1" / "board_result.json", make_pass_result(tmp_path, cases[0]))

    completed = run_report(manifest, results, tmp_path / "report")

    assert completed.returncode != 0
    assert "BOARD_RECORDS expected=2 recorded=1" in completed.stdout
    assert "BOARD_MATRIX expected=2 executed=1 pass=1 fail=0 not_run=1" in completed.stdout
    assert "onnx tc2 fp32 NOT_RUN" in completed.stdout
    assert "ACCURACY_VERDICT=NOT_RUN" in completed.stdout
    assert "BOARD_MATRIX_GATE=NOT_RUN" in completed.stdout


def test_full_matrix_pass_lists_every_case(tmp_path):
    manifest, cases = make_expected(tmp_path)
    results = tmp_path / "results"
    for case in cases:
        write_json(results / f"tc{case['case_id']}" / "board_result.json",
                   make_pass_result(tmp_path, case))

    completed = run_report(manifest, results, tmp_path / "report")

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "BOARD_MATRIX expected=2 executed=2 pass=2 fail=0 not_run=0" in completed.stdout
    assert "onnx tc1 fp32 PASS" in completed.stdout
    assert "onnx tc2 fp32 PASS" in completed.stdout
    assert "BOARD_MATRIX_GATE=PASS" in completed.stdout


def test_not_run_receipts_are_accounted_but_not_executed(tmp_path):
    manifest, cases = make_expected(tmp_path)
    results = tmp_path / "results"
    for case in cases:
        write_json(results / f"tc{case['case_id']}" / "board_result.json", {
            "run_id": "run-1", "operator": "Add",
            "framework": case["framework"], "case_id": case["case_id"],
            "mode": case["mode"], "status": "NOT_RUN",
            "reason": "no compatible development board detected",
        })

    completed = run_report(manifest, results, tmp_path / "report")

    assert completed.returncode != 0
    assert "BOARD_RECORDS expected=2 recorded=2" in completed.stdout
    assert "BOARD_MATRIX expected=2 executed=0 pass=0 fail=0 not_run=2" in completed.stdout
    assert "BOARD_MATRIX_GATE=NOT_RUN" in completed.stdout
    assert "ACCURACY_VERDICT=NOT_RUN" in completed.stdout

    report = json.loads(
        (tmp_path / "report" / "board_case_results.json").read_text(encoding="utf-8")
    )
    assert report["schema_version"] == 2
    assert report["recorded"] == 2
    assert report["executed"] == 0


def test_pass_requires_serial_probe_receipt(tmp_path):
    manifest, cases = make_expected(tmp_path, count=1)
    results = tmp_path / "results"
    result = make_pass_result(tmp_path, cases[0])
    result.pop("serial_probe")
    write_json(results / "tc1" / "board_result.json", result)

    completed = run_report(manifest, results, tmp_path / "report")

    assert completed.returncode != 0
    assert "missing PASS evidence field serial_probe" in completed.stdout
    assert "BOARD_MATRIX_GATE=FAIL" in completed.stdout


def test_evidence_logs_accept_utf16_with_bom(tmp_path):
    manifest, cases = make_expected(tmp_path, count=1)
    results = tmp_path / "results"
    result = make_pass_result(tmp_path, cases[0])
    Path(result["flash_log"]).write_bytes('{"success": true}\n'.encode("utf-16"))
    Path(result["accuracy_log"]).write_bytes(
        "ACCURACY_VERDICT=PASS\n".encode("utf-16")
    )
    write_json(results / "tc1" / "board_result.json", result)

    completed = run_report(manifest, results, tmp_path / "report")

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_evidence_logs_accept_binary_serial_prefix(tmp_path):
    manifest, cases = make_expected(tmp_path, count=1)
    results = tmp_path / "results"
    result = make_pass_result(tmp_path, cases[0])
    Path(result["accuracy_log"]).write_bytes(
        b"\x80\x00\xdd" + b"ACCURACY_VERDICT=PASS\n"
    )
    write_json(results / "tc1" / "board_result.json", result)

    completed = run_report(manifest, results, tmp_path / "report")

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_flash_summary_must_be_the_final_nonempty_line(tmp_path):
    manifest, cases = make_expected(tmp_path, count=1)
    results = tmp_path / "results"
    result = make_pass_result(tmp_path, cases[0])
    Path(result["flash_log"]).write_text(
        '{"success": true}\nwarning after summary\n', encoding="utf-8"
    )
    write_json(results / "tc1" / "board_result.json", result)

    completed = run_report(manifest, results, tmp_path / "report")

    assert completed.returncode != 0
    assert "final non-empty line is not valid JSON" in completed.stdout
    assert "BOARD_MATRIX_GATE=FAIL" in completed.stdout


def test_duplicate_expected_identity_keeps_raw_manifest_denominator(tmp_path):
    manifest, cases = make_expected(tmp_path, count=2)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["cases"].append(dict(cases[1]))
    payload["expected_count"] = len(payload["cases"])
    write_json(manifest, payload)

    completed = run_report(manifest, tmp_path / "results", tmp_path / "report")

    assert completed.returncode != 0
    assert "BOARD_RECORDS expected=3" in completed.stdout
    assert "BOARD_MATRIX expected=3" in completed.stdout
    report = json.loads(
        (tmp_path / "report" / "board_case_results.json").read_text(encoding="utf-8")
    )
    assert any("duplicate expected identity" in error for error in report["errors"])


@pytest.mark.parametrize(
    "bad_case",
    [
        {},
        [],
        {"framework": "onnx", "case_id": "1", "mode": None},
        {"framework": "onnx", "case_id": " 1", "mode": "fp32"},
        {"framework": {}, "case_id": "1", "mode": "fp32"},
    ],
)
def test_invalid_expected_identity_fails_closed(tmp_path, bad_case):
    manifest = tmp_path / "board_expected_matrix.json"
    write_json(
        manifest,
        {
            "schema_version": 1,
            "run_id": "run-1",
            "operator": "Add",
            "expected_count": 1,
            "cases": [bad_case],
        },
    )

    completed = run_report(manifest, tmp_path / "results", tmp_path / "report")

    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    report = json.loads(
        (tmp_path / "report" / "board_case_results.json").read_text(encoding="utf-8")
    )
    assert any("invalid expected identity" in error for error in report["errors"])


def test_non_object_board_result_fails_closed(tmp_path):
    manifest, cases = make_expected(tmp_path, count=1)
    results = tmp_path / "results"
    write_json(results / "tc1" / "board_result.json", ["not", "an", "object"])

    completed = run_report(manifest, results, tmp_path / "report")

    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    report = json.loads(
        (tmp_path / "report" / "board_case_results.json").read_text(encoding="utf-8")
    )
    assert any("invalid result JSON" in error for error in report["errors"])


@pytest.mark.parametrize("invalid_path", [["firmware"], {"path": "firmware"}, 123])
def test_non_string_pass_evidence_fails_closed(tmp_path, invalid_path):
    manifest, cases = make_expected(tmp_path, count=1)
    results = tmp_path / "results"
    result = make_pass_result(tmp_path, cases[0])
    result["firmware"] = invalid_path
    write_json(results / "tc1" / "board_result.json", result)

    completed = run_report(manifest, results, tmp_path / "report")

    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    report = json.loads(
        (tmp_path / "report" / "board_case_results.json").read_text(encoding="utf-8")
    )
    assert any("PASS evidence field firmware" in error for error in report["errors"])


@pytest.mark.parametrize("field", ["run_id", "operator"])
def test_manifest_and_result_cannot_both_omit_identity(field, tmp_path):
    manifest, cases = make_expected(tmp_path, count=1)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload.pop(field)
    write_json(manifest, payload)
    result = make_pass_result(tmp_path, cases[0])
    result.pop(field)
    results = tmp_path / "results"
    write_json(results / "tc1" / "board_result.json", result)

    completed = run_report(manifest, results, tmp_path / "report")

    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    report = json.loads(
        (tmp_path / "report" / "board_case_results.json").read_text(encoding="utf-8")
    )
    assert f"manifest {field} must be a non-empty string" in report["errors"]
