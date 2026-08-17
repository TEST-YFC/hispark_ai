import argparse
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
REPO_ROOT = SKILL_ROOT.parents[1]
sys.path.insert(0, str(SCRIPTS))

import inject_ws63_timing
import build_timed_fwpkg
import measure_latency
import run_board_flash
from harness.evidence import EvidenceError, load_metric, validate_host_summary
from harness.workflow import (
    EVIDENCE_NAMES,
    WorkflowError,
    archive_success,
    bind_evidence,
    prepare_run,
    summarize,
)


def run(command, cwd):
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def init_git(path, files):
    path.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q"], path)
    run(["git", "config", "user.email", "test@example.com"], path)
    run(["git", "config", "user.name", "Test"], path)
    for relative, content in files.items():
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    run(["git", "add", "."], path)
    run(["git", "commit", "-qm", "baseline"], path)


class TimingInjectionTests(unittest.TestCase):
    def test_current_ai_main_template_is_supported_and_idempotent(self):
        template = REPO_ROOT / "src" / "samples" / "oh" / "lenet5" / "src" / "ai_main.c"
        original = template.read_text(encoding="utf-8")
        updated = inject_ws63_timing.render(original)
        self.assertEqual(updated.count(inject_ws63_timing.MARKER), 1)
        self.assertNotIn("[AI_MCU] Get Tcxo Time", updated)
        self.assertLess(updated.index("if (ret != OH_AI_STATUS_SUCCESS)"), updated.index(inject_ws63_timing.MARKER))
        self.assertEqual(inject_ws63_timing.render(updated), updated)

    def test_current_board_builder_exposes_the_timing_hook(self):
        board_scripts = REPO_ROOT / "skills" / "hs-debug-op-board-accuracy" / "scripts"
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "build_fwpkg.sh"
            build_timed_fwpkg.prepare_builder(
                board_scripts / "build_fwpkg.sh",
                destination,
                board_scripts,
                SCRIPTS / "inject_ws63_timing.py",
            )
            text = destination.read_text(encoding="utf-8")
            self.assertIn("inject_ws63_timing.py", text)
            self.assertIn("trap hs_perf_restore_template EXIT", text)

    def test_board_wrapper_prints_execution_and_firmware_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            board = root / "board" / "scripts"
            board.mkdir(parents=True)
            flash = board / "flash.sh"
            flash.write_text(
                "#!/bin/bash\nexit 0\n",
                encoding="utf-8",
            )
            firmware = root / "model.fwpkg"
            firmware.write_bytes(b"firmware")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = run_board_flash.main([
                    "--execution-id", "run-1",
                    "--board-skill", str(board.parent),
                    "--firmware", str(firmware),
                    "--gt-dir", str(root),
                ])
            self.assertEqual(status, 0)
            self.assertIn("HS_PERF_EXECUTION_ID=run-1", output.getvalue())
            self.assertIn(
                f"HS_PERF_FIRMWARE_SHA256={hashlib.sha256(b'firmware').hexdigest()}",
                output.getvalue(),
            )


class MeasurementTests(unittest.TestCase):
    def args(self, **overrides):
        values = {
            "execution_id": "run-1",
            "baudrate": 115200,
            "window": 3,
            "ticks_per_us": 24.0,
            "stable_tolerance": 0.05,
            "timeout_seconds": 110.0,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_protocol_requires_positive_contiguous_samples(self):
        state = measure_latency.ProtocolState()
        self.assertEqual(
            state.consume("[AI_MCU][PREDICT] OK seq=7 ticks=240"), (7, 240)
        )
        self.assertEqual(
            state.consume("[AI_MCU][PREDICT] OK seq=8 ticks=241"), (8, 241)
        )
        with self.assertRaises(measure_latency.ProtocolError):
            state.consume("[AI_MCU][PREDICT] OK seq=10 ticks=242")

    def test_result_retains_protocol_and_complete_window(self):
        args = self.args()
        result = measure_latency.build_result(args, [240, 241, 239])
        self.assertEqual(result["format_version"], 2)
        self.assertEqual(result["execution_id"], "run-1")
        self.assertEqual(result["samples_ticks"], [240, 241, 239])
        self.assertEqual(result["protocol"]["window"], 3)

    def test_invalid_measurement_arguments_fail_early(self):
        for override in (
            {"ticks_per_us": 0}, {"window": 1}, {"stable_tolerance": 1.0},
            {"timeout_seconds": 0}, {"execution_id": "../escape"},
        ):
            with self.subTest(override=override), self.assertRaises(ValueError):
                measure_latency.validate_args(self.args(**override))

    def test_interrupt_is_nonzero_and_does_not_publish_metric(self):
        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def readline(self):
                raise KeyboardInterrupt

        fake_serial = types.SimpleNamespace(
            Serial=lambda *_args, **_kwargs: FakeConnection(),
            SerialException=RuntimeError,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proof = root / "board.log"
            proof.write_text("ACCURACY_VERDICT=PASS\n", encoding="utf-8")
            output = root / "nested" / "metric.json"
            argv = [
                "--execution-id", "run-1", "--port", "COM1", "--baudrate", "115200",
                "--ticks-per-us", "24", "--window", "2", "--stable-tolerance", "0.05",
                "--timeout-seconds", "110", "--accuracy-proof", str(proof),
                "--raw-log", str(root / "raw.log"), "--output", str(output),
            ]
            with (
                mock.patch.dict(sys.modules, {"serial": fake_serial}),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(measure_latency.main(argv), 130)
            self.assertFalse(output.exists())

    def test_metric_output_creates_parent_and_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "metric.json"
            measure_latency._atomic_json(path, {"passed": True})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"passed": True})


class EvidenceTests(unittest.TestCase):
    def test_host_identity_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / "verify_summary.txt"
            summary.write_text(
                "hs-debug-op-host-accuracy summary\n"
                "op=ExampleOp  frameworks=['onnx']  paths=['riscv_int8']\n"
                "VERDICT: op=ExampleOp  2/2 variant-cases PASS, 0 FAIL\n"
                "HARNESS_EXIT=0\n",
                encoding="utf-8",
            )
            validate_host_summary(summary, "ExampleOp", "onnx", "int8")
            with self.assertRaises(EvidenceError):
                validate_host_summary(summary, "OtherOp", "onnx", "int8")

    def test_metric_protocol_and_execution_id_are_bound(self):
        protocol = {
            "ticks_per_us": 24.0,
            "window": 2,
            "stable_tolerance": 0.05,
            "timeout_seconds": 110.0,
        }
        data = {
            "format_version": 2,
            "execution_id": "run-1",
            "passed": True,
            "metric": {"name": "latency", "value": 10.0, "unit": "us"},
            "protocol": protocol,
            "samples_ticks": [240, 240],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metric.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            load_metric(path, "run-1", protocol)
            with self.assertRaises(EvidenceError):
                load_metric(path, "run-2", protocol)


class WorkflowIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "HiSpark.AI"
        self.source = self.root / "src" / "mindspore-lite"
        self.sdk = Path(self.temporary.name) / "ws63-sdk"
        self.root.mkdir(parents=True)
        (self.root / "README.md").write_text("# HiSpark.AI\n", encoding="utf-8")
        skill = self.root / "skills" / "hs-dev-op-performance"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: hs-dev-op-performance\n---\n", encoding="utf-8")
        (self.root / "src").mkdir(exist_ok=True)
        init_git(self.root, {"tracked.txt": "root\n"})
        init_git(self.source, {"kernel.c": "baseline\n"})
        init_git(self.sdk, {"sdk.txt": "sdk\n"})

    def tearDown(self):
        self.temporary.cleanup()

    def prepare(self, task_type, **extra):
        values = {
            "repo_root": self.root,
            "operator": "ExampleOp",
            "case": "case1",
            "framework": "onnx",
            "mode": "int8",
            "target": "ws63",
            "task_type": task_type,
            "source_root": self.source,
            "ticks_per_us": 24.0,
            "window": 2,
            "stable_tolerance": 0.05,
            "timeout_seconds": 110.0,
        }
        values.update(extra)
        return prepare_run(**values)

    def write_evidence(self, manifest_path, manifest, latency, firmware_sha256=None):
        firmware_sha256 = firmware_sha256 or ("0" * 64)
        evidence = {
            "host": (
                "hs-debug-op-host-accuracy summary\n"
                "op=ExampleOp  frameworks=['onnx']  paths=['riscv_int8']\n"
                "VERDICT: op=ExampleOp  2/2 variant-cases PASS, 0 FAIL\n"
                "HARNESS_EXIT=0\n"
            ),
            "build": (
                f"HS_PERF_EXECUTION_ID={manifest['execution_id']}\n"
                "FWPKG_BUILD=PASS\n"
                f"HS_PERF_FIRMWARE_SHA256={firmware_sha256}\n"
            ),
            "flash": "FLASH_VERDICT=PASS\n",
            "board": "ACCURACY_VERDICT=PASS\n",
            "serial": (
                "[AI_MCU][PREDICT] OK seq=1 ticks=240\n"
                "[AI_MCU][PREDICT] OK seq=2 ticks=240\n"
            ),
            "metric": json.dumps({
                "format_version": 2,
                "execution_id": manifest["execution_id"],
                "passed": True,
                "metric": {"name": "latency", "value": latency, "unit": "us"},
                "protocol": manifest["protocol"],
                "samples_ticks": [240, 240],
            }),
        }
        identity = (
            f"HS_PERF_EXECUTION_ID={manifest['execution_id']}\n"
            f"HS_PERF_FIRMWARE_SHA256={firmware_sha256}\n"
        )
        evidence["flash"] = identity + evidence["flash"]
        evidence["board"] = identity + evidence["board"]
        source_dir = Path(self.temporary.name) / f"evidence-{manifest['execution_id']}"
        source_dir.mkdir()
        for kind, content in evidence.items():
            path = source_dir / EVIDENCE_NAMES[kind]
            path.write_text(content, encoding="utf-8")
            bind_evidence(manifest_path, kind, path)

    def archive(self, manifest_path, manifest, latency):
        artifacts = Path(self.temporary.name) / f"artifacts-{manifest['execution_id']}"
        artifacts.mkdir()
        firmware = artifacts / "model.fwpkg"
        cpu = artifacts / "cpu.a"
        riscv = artifacts / "riscv.a"
        codes = artifacts / "codes"
        codes.mkdir()
        firmware.write_bytes(b"firmware")
        cpu.write_bytes(b"cpu")
        riscv.write_bytes(b"riscv")
        (codes / "net0.c").write_text(f"code-{manifest['execution_id']}\n", encoding="utf-8")
        self.write_evidence(
            manifest_path,
            manifest,
            latency,
            hashlib.sha256(firmware.read_bytes()).hexdigest(),
        )
        return archive_success(
            manifest_path=manifest_path,
            firmware=firmware,
            codes_dir=codes,
            cpu_archive=cpu,
            riscv_archive=riscv,
            sdk_root=self.sdk,
        )

    def test_baseline_and_same_commit_single_path_optimization(self):
        baseline_path, baseline_manifest = self.prepare("baseline")
        baseline_dir = self.archive(baseline_path, baseline_manifest, 10.0)
        self.assertEqual(baseline_dir.name, "baseline")

        run_path, run_manifest = self.prepare(
            "optimization",
            variable="loop-order",
            note="change loop order",
            change_kind="nnacl",
            allowed_changes=["kernel.c"],
        )
        (self.source / "kernel.c").write_text("optimized\n", encoding="utf-8")
        experiment = self.archive(run_path, run_manifest, 9.96)
        result = json.loads((experiment / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "ACCEPTED")
        self.assertGreater(result["performance"]["speedup"], 1.0)
        summary = summarize(
            repo_root=self.root, operator="ExampleOp", case="case1",
            framework="onnx", target="ws63",
        )
        self.assertEqual(summary["best_execution_id"], run_manifest["execution_id"])

    def test_invalid_variable_and_out_of_scope_change_are_rejected(self):
        baseline_path, baseline_manifest = self.prepare("baseline")
        self.archive(baseline_path, baseline_manifest, 10.0)
        with self.assertRaises(WorkflowError):
            self.prepare(
                "optimization", variable="x/../../../escape", note="bad",
                allowed_changes=["kernel.c"],
            )
        run_path, run_manifest = self.prepare(
            "optimization", variable="safe", note="safe",
            allowed_changes=["allowed.c"],
        )
        (self.source / "kernel.c").write_text("outside scope\n", encoding="utf-8")
        self.write_evidence(run_path, run_manifest, 9.0)
        artifacts = Path(self.temporary.name) / "reject-artifacts"
        artifacts.mkdir()
        for name in ("firmware.fwpkg", "cpu.a", "riscv.a"):
            (artifacts / name).write_bytes(name.encode())
        codes = artifacts / "codes"
        codes.mkdir()
        (codes / "net0.c").write_text("code\n", encoding="utf-8")
        with self.assertRaises(WorkflowError):
            archive_success(
                manifest_path=run_path,
                firmware=artifacts / "firmware.fwpkg",
                codes_dir=codes,
                cpu_archive=artifacts / "cpu.a",
                riscv_archive=artifacts / "riscv.a",
                sdk_root=self.sdk,
            )

    def test_bound_evidence_cannot_be_modified(self):
        manifest_path, manifest = self.prepare("baseline")
        self.write_evidence(manifest_path, manifest, 10.0)
        bound = manifest_path.parent / "evidence" / EVIDENCE_NAMES["flash"]
        bound.write_text("FLASH_VERDICT=FAIL\n", encoding="utf-8")
        artifacts = Path(self.temporary.name) / "tamper-artifacts"
        artifacts.mkdir()
        for name in ("firmware.fwpkg", "cpu.a", "riscv.a"):
            (artifacts / name).write_bytes(name.encode())
        codes = artifacts / "codes"
        codes.mkdir()
        (codes / "net0.c").write_text("code\n", encoding="utf-8")
        with self.assertRaisesRegex(WorkflowError, "changed after binding"):
            archive_success(
                manifest_path=manifest_path,
                firmware=artifacts / "firmware.fwpkg",
                codes_dir=codes,
                cpu_archive=artifacts / "cpu.a",
                riscv_archive=artifacts / "riscv.a",
                sdk_root=self.sdk,
            )


if __name__ == "__main__":
    unittest.main()
