import json
from pathlib import Path
import subprocess
import sys


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
    firmware.write_bytes(b"firmware")
    flash.write_text('{"success": true}\n', encoding="utf-8")
    monitor.write_text("tensor output", encoding="utf-8")
    accuracy.write_text("ACCURACY_VERDICT=PASS\n", encoding="utf-8")
    return {
        "run_id": "run-1", "operator": "Add",
        "framework": case["framework"], "case_id": case["case_id"],
        "mode": case["mode"], "status": "PASS",
        "model": case["model"], "input_dir": case["input_dir"],
        "gt_dir": case["gt_dir"], "firmware": str(firmware.resolve()),
        "flash_log": str(flash.resolve()), "monitor": str(monitor.resolve()),
        "accuracy_log": str(accuracy.resolve()),
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
