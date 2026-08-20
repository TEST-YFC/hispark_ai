#!/usr/bin/env python3
# coding: utf-8
"""Unit tests for the hs-verify-op-host FIXED harness (scripts/run_all_cases.py).

WHY THIS FILE EXISTS
--------------------
run_all_cases.py is "immutable infrastructure" shared by every operator. SKILL.md's
Red Flags leave exactly one door open to edit it: a genuine harness capability gap,
done as a *deliberate maintenance* with SKILL.md updated and a regression on existing
operators. The problem that door creates is that a maintenance edit can SILENTLY break
the very functions that keep the verdict honest — and the failure mode is the worst
kind: red turns green without anyone noticing.

These tests pin those functions so a harness edit that breaks them fails LOUDLY here
instead of quietly fabricating PASSes on real hardware runs. They need no MSLite,
no converter_lite, no board — only numpy + the harness module itself, so they run in
seconds and can gate any change to run_all_cases.py.

The module is loaded BY PATH (not copied/inlined) so these tests stay coupled to the
real signatures: rename or re-signature a harness function and the import or the call
breaks here, which is exactly the early warning we want.

    pytest tests/test_harness_core.py -v
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pytest

# --------------------------------------------------------------------------- #
# Load the REAL harness by path (executes module-level defs, not main()).
# --------------------------------------------------------------------------- #
HARNESS_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run_all_cases.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("run_all_cases", HARNESS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # defines functions/consts; __name__ != "__main__"
    return mod


h = _load_harness()


def test_onnx_reference_falls_back_only_for_ort_not_implemented(monkeypatch):
    class FailingSession:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("NOT_IMPLEMENTED: unsupported dtype")

    model = types.SimpleNamespace(
        graph=types.SimpleNamespace(
            input=[types.SimpleNamespace(name="X")],
            output=[types.SimpleNamespace(name="Z")],
        )
    )
    evaluator = types.SimpleNamespace(run=lambda *_args: [np.asarray([7], dtype=np.uint16)])
    fake_onnx = types.ModuleType("onnx")
    fake_onnx.load = lambda _path: model
    fake_reference = types.ModuleType("onnx.reference")
    fake_reference.ReferenceEvaluator = lambda _model: evaluator
    monkeypatch.setitem(sys.modules, "onnxruntime", types.SimpleNamespace(InferenceSession=FailingSession))
    monkeypatch.setitem(sys.modules, "onnx", fake_onnx)
    monkeypatch.setitem(sys.modules, "onnx.reference", fake_reference)

    in_names, out_names, outputs = h.run_reference("onnx", Path("model.onnx"), [np.asarray([1])])

    assert in_names == ["X"]
    assert out_names == ["Z"]
    np.testing.assert_array_equal(outputs[0], np.asarray([7], dtype=np.uint16))


def test_onnx_reference_does_not_mask_other_ort_errors(monkeypatch):
    class FailingSession:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("INVALID_ARGUMENT: malformed model")

    monkeypatch.setitem(sys.modules, "onnxruntime", types.SimpleNamespace(InferenceSession=FailingSession))
    with pytest.raises(RuntimeError, match="INVALID_ARGUMENT"):
        h.run_reference("onnx", Path("model.onnx"), [np.asarray([1])])


def test_onnx_reference_uses_official_integer_result_on_runtime_disagreement(monkeypatch):
    class Session:
        def get_inputs(self):
            return [types.SimpleNamespace(name="X")]

        def get_outputs(self):
            return [types.SimpleNamespace(name="Z")]

        def run(self, *_args):
            return [np.asarray([13], dtype=np.uint32)]

    model = types.SimpleNamespace(
        graph=types.SimpleNamespace(
            input=[types.SimpleNamespace(name="X")],
            output=[types.SimpleNamespace(name="Z")],
        )
    )
    fake_onnx = types.ModuleType("onnx")
    fake_onnx.load = lambda _path: model
    fake_reference = types.ModuleType("onnx.reference")
    fake_reference.ReferenceEvaluator = lambda _model: types.SimpleNamespace(
        run=lambda *_args: [np.asarray([0], dtype=np.uint32)]
    )
    monkeypatch.setitem(sys.modules, "onnxruntime", types.SimpleNamespace(InferenceSession=lambda *_a, **_k: Session()))
    monkeypatch.setitem(sys.modules, "onnx", fake_onnx)
    monkeypatch.setitem(sys.modules, "onnx.reference", fake_reference)

    _, _, outputs = h.run_reference("onnx", Path("model.onnx"), [np.asarray([1])])

    np.testing.assert_array_equal(outputs[0], np.asarray([0], dtype=np.uint32))


def test_dependency_repair_installs_missing_module_and_reimports(monkeypatch):
    installed = {"value": False}
    commands = []
    fake_module = types.SimpleNamespace(__version__="1.2.3")

    def fake_import(name):
        if name == "demo_dep" and not installed["value"]:
            raise ModuleNotFoundError("No module named demo_dep", name="demo_dep")
        return fake_module

    def fake_run(command, check=False):
        commands.append(command)
        installed["value"] = True
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(h.importlib, "import_module", fake_import)
    monkeypatch.setattr(h.subprocess, "run", fake_run)
    result = h._install_python_dependency("demo_dep")

    assert result is fake_module
    assert commands
    assert commands[0][:4] == [h.sys.executable, "-m", "pip", "install"]


def test_dependency_repair_does_not_reinstall_for_transitive_import_error(monkeypatch):
    def fake_import(_name):
        raise ModuleNotFoundError("No module named native_runtime", name="native_runtime")

    monkeypatch.setattr(h.importlib, "import_module", fake_import)
    monkeypatch.setattr(
        h.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("pip must not run for a transitive import error"),
    )
    with pytest.raises(ModuleNotFoundError, match="native_runtime"):
        h._install_python_dependency("demo_dep")


def _fake_spec(op_name="Hardmax", onnx=None, tflite=None, **extra):
    """A minimal stand-in for an op_spec module (only the attrs the gates read)."""
    ns = types.SimpleNamespace(
        OP_NAME=op_name,
        ONNX_TEST_CASES=onnx or [],
        TFLITE_TEST_CASES=tflite or [],
    )
    for k, v in extra.items():
        setattr(ns, k, v)
    return ns


def test_full_harness_rejects_custom_threshold_before_signoff(tmp_path):
    completed = subprocess.run(
        [sys.executable, str(HARNESS_PATH), "--spec", str(tmp_path / "missing_spec.py"),
         "--threshold-int8", "0.9"],
        text=True, capture_output=True, check=False,
    )
    assert completed.returncode != 0
    assert "完整 Host 签收只允许固定阈值" in completed.stderr


def test_converter_encryption_capability_uses_flag_only_when_help_declares_it(tmp_path, monkeypatch):
    pkg = tmp_path / "pkg"
    converter = pkg / "tools" / "converter" / "converter" / "converter_lite"
    converter.parent.mkdir(parents=True)
    converter.write_text("")
    library = pkg / "tools" / "converter" / "lib" / "libmindspore_converter.so"
    library.parent.mkdir(parents=True)
    library.write_text("")
    (pkg / "runtime" / "lib").mkdir(parents=True)
    calls = []

    def fake_run(*args, **kwargs):
        calls.append(args[0])
        assert kwargs["env"]["LD_LIBRARY_PATH"].startswith(
            str(pkg / "tools" / "converter" / "lib")
        )
        assert str(pkg / "runtime" / "lib") in kwargs["env"]["LD_LIBRARY_PATH"]
        return types.SimpleNamespace(stdout="options: --encryption=<bool>", stderr="", returncode=0)

    h._CONVERTER_CAPABILITY_CACHE.clear()
    monkeypatch.setattr(h.subprocess, "run", fake_run)
    first = h._converter_encryption_capability(str(pkg))
    second = h._converter_encryption_capability(str(pkg))

    assert first[0] == "--encryption=false"
    assert "supported; using" in first[1]
    assert second == first
    assert len(calls) == 1


def test_converter_encryption_capability_omits_unknown_flag_for_28_style_help(tmp_path, monkeypatch):
    pkg = tmp_path / "pkg"
    converter = pkg / "tools" / "converter" / "converter" / "converter_lite"
    converter.parent.mkdir(parents=True)
    converter.write_text("")
    library = pkg / "tools" / "converter" / "lib" / "libmindspore_converter.so"
    library.parent.mkdir(parents=True)
    library.write_text("")

    h._CONVERTER_CAPABILITY_CACHE.clear()
    monkeypatch.setattr(
        h.subprocess, "run",
        lambda *args, **kwargs: types.SimpleNamespace(
            stdout="Usage: converter_lite --fmk --modelFile --outputFile", stderr="", returncode=0
        ),
    )

    argument, diagnostic = h._converter_encryption_capability(str(pkg))
    assert argument == ""
    assert "unsupported; omitted" in diagnostic


def test_converter_encryption_capability_rejects_failed_help_probe(tmp_path, monkeypatch):
    pkg = tmp_path / "pkg"
    converter = pkg / "tools" / "converter" / "converter" / "converter_lite"
    converter.parent.mkdir(parents=True)
    converter.write_text("")
    library = pkg / "tools" / "converter" / "lib" / "libmindspore_converter.so"
    library.parent.mkdir(parents=True)
    library.write_text("")

    h._CONVERTER_CAPABILITY_CACHE.clear()
    monkeypatch.setattr(
        h.subprocess, "run",
        lambda *args, **kwargs: types.SimpleNamespace(
            stdout="", stderr="missing shared library", returncode=127
        ),
    )

    with pytest.raises(RuntimeError, match=r"CONVERTER_HELP_FAIL.*rc=127.*missing shared library"):
        h._converter_encryption_capability(str(pkg))


def test_converter_runtime_env_prepends_current_package_and_filters_old_package(tmp_path):
    pkg = tmp_path / "current/pkg"
    current = pkg / "tools/converter/lib"
    current.mkdir(parents=True)
    (current / "libmindspore_converter.so").write_text("")
    runtime = pkg / "runtime/lib"
    runtime.mkdir(parents=True)
    old = tmp_path / "old/pkg/tools/converter/lib"
    old.mkdir(parents=True)
    (old / "libmindspore_converter.so").write_text("")
    unrelated = tmp_path / "custom/lib"
    unrelated.mkdir(parents=True)

    env, directories = h._converter_runtime_env(
        str(pkg), {"LD_LIBRARY_PATH": os.pathsep.join((str(old), str(unrelated)))}
    )
    entries = env["LD_LIBRARY_PATH"].split(os.pathsep)

    assert entries[0] == str(current.resolve())
    assert str(runtime.resolve()) in directories
    assert str(old.resolve()) not in entries
    assert str(unrelated.resolve()) in entries


def test_converter_runtime_env_reports_missing_library_as_environment_gate(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    with pytest.raises(RuntimeError, match="CONVERTER_RUNTIME_GATE=FAIL.*NOT_FOUND"):
        h._converter_runtime_env(str(pkg), {})


def test_onnx_target_identity_accepts_exact_operator(tmp_path, monkeypatch):
    spec = _fake_spec("Fill", ONNX_TARGET_OP_TYPE="Fill")
    monkeypatch.setattr(h, "_onnx_op_types", lambda _: ["Constant", "Fill"])
    h._assert_target_source_op(spec, "onnx", tmp_path / "model.onnx")


def test_fill_rewritten_to_broadcastto_is_rejected_as_op_mismatch(tmp_path, monkeypatch):
    spec = _fake_spec("Fill", ONNX_TARGET_OP_TYPE="Fill")
    monkeypatch.setattr(h, "_onnx_op_types", lambda _: ["Constant", "BroadcastTo"])
    with pytest.raises(RuntimeError, match="OP_MISMATCH.*target op_type 'Fill' absent"):
        h._assert_target_source_op(spec, "onnx", tmp_path / "model.onnx")


def test_tflite_target_identity_rejects_substitute_builtin(tmp_path, monkeypatch):
    spec = _fake_spec("Fill", TFLITE_TARGET_BUILTIN=94)
    monkeypatch.setattr(h, "_tflite_builtin_codes", lambda _: [130])
    with pytest.raises(RuntimeError, match="OP_MISMATCH.*target builtin 94 absent"):
        h._assert_target_source_op(spec, "tflite", tmp_path / "model.tflite")


# =========================================================================== #
# A. cosine_similarity — THE single most safety-critical function.
#    A regression here silently launders mismatches into PASSes, so it gets the
#    most thorough coverage. The contract (SKILL.md Red Flags): defined for every
#    input, NEVER NaN; both-zero -> 1.0; exactly-one-zero -> 0.0.
# =========================================================================== #

def test_cosine_identical_is_one():
    v = [1.0, 2.0, 3.0, 4.0]
    assert h.cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal_is_zero():
    assert h.cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_opposite_is_minus_one():
    assert h.cosine_similarity([1.0, 2.0], [-1.0, -2.0]) == pytest.approx(-1.0)


def test_cosine_positive_scaling_is_one():
    # cosine is scale-invariant for positive scaling
    assert h.cosine_similarity([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(1.0)


def test_cosine_both_all_zero_is_one():
    # both produced nothing -> they match (per the contract)
    assert h.cosine_similarity([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]) == 1.0


def test_cosine_exactly_one_all_zero_is_zero_not_one():
    # the trap: device produced all-zero while reference is non-zero == real FAIL.
    # Must be 0.0, never silently mapped to a passing 1.0.
    assert h.cosine_similarity([0.0, 0.0, 0.0], [1.0, 2.0, 3.0]) == 0.0
    assert h.cosine_similarity([1.0, 2.0, 3.0], [0.0, 0.0, 0.0]) == 0.0


@pytest.mark.parametrize("a,b", [
    ([0.0, 0.0], [0.0, 0.0]),          # both zero
    ([0.0, 0.0], [1.0, 1.0]),          # one zero
    ([1.0, 2.0], [3.0, 4.0]),          # ordinary
    ([1e-30, 1e-30], [1e-30, 1e-30]),  # tiny but non-zero norm
])
def test_cosine_never_nan(a, b):
    # A NaN reaching a verdict means the cosine wasn't really computed — a bug to
    # fix, never a PASS to fabricate. The function must be total.
    out = h.cosine_similarity(a, b)
    assert not np.isnan(out)
    assert not np.isinf(out)


def test_cosine_flattens_multidim():
    # The judge validates shape first; the numeric cosine primitive then flattens values.
    a = np.array([[1.0, 2.0], [3.0, 4.0]])
    b = np.array([1.0, 2.0, 3.0, 4.0])
    assert h.cosine_similarity(a, b) == pytest.approx(1.0)


def test_cosine_in_valid_range():
    rng = np.linspace(-5, 5, 50)
    for shift in (-3, 0, 2, 7):
        out = h.cosine_similarity(rng, rng + shift)
        assert -1.0 - 1e-9 <= out <= 1.0 + 1e-9


# =========================================================================== #
# B. parse_benchmark_outputs — the ONLY device-output source the harness trusts.
#    It must pick up "name: ... Data:" headers + the following CSV line, and
#    return nothing when there is no such block (-> path recorded as FAIL).
# =========================================================================== #

def test_parse_single_tensor():
    stdout = "some log\nname:out tensor Data:\n1.0,2.0,3.0\ntrailing log\n"
    outs = h.parse_benchmark_outputs(stdout)
    assert len(outs) == 1
    assert np.allclose(outs[0], [1.0, 2.0, 3.0])


def test_parse_multiple_tensors():
    stdout = ("name:a Data:\n1.0,2.0\n"
              "name:b Data:\n3.0,4.0,5.0\n")
    outs = h.parse_benchmark_outputs(stdout)
    assert len(outs) == 2
    assert np.allclose(outs[0], [1.0, 2.0])
    assert np.allclose(outs[1], [3.0, 4.0, 5.0])


def test_parse_handles_trailing_comma():
    stdout = "name:out Data:\n1.0,2.0,3.0,\n"
    outs = h.parse_benchmark_outputs(stdout)
    assert len(outs) == 1
    assert np.allclose(outs[0], [1.0, 2.0, 3.0])


def test_parse_no_match_returns_empty():
    # no "Data:" header -> no parsed tensors -> caller treats the path as FAIL.
    assert h.parse_benchmark_outputs("nothing here\njust logs\n") == []


def test_parse_empty_data_line_is_preserved_for_metadata_validation():
    stdout = "name:out Data:\n\n"
    tensors = h.parse_benchmark_tensors(stdout)
    assert len(tensors) == 1
    assert tensors[0]["data"].size == 0
    assert tensors[0]["shape"] is None


def test_parse_shape_metadata_rejects_negative_and_malformed_dimensions():
    for header in (
        "name:out, Elements: 4, Shape: [-1 4], Data:",
        "name:out, Elements: 6, Shape: [2 x 3], Data:",
        "name:out, Elements: 6, Shape: [2,,3], Data:",
    ):
        tensor = h.parse_benchmark_tensors(header + "\n1,2,3,4\n")[0]
        assert tensor["shape"] is None
        assert "invalid shape metadata" in tensor["shape_error"]


def test_parse_real_printtensor_shape_scalar_and_zero_dimension():
    real = h.parse_benchmark_tensors(
        "name: out, DataType: 43, Elements: 10, Shape: [1 10 ], Data:\n"
        "0,1,2,3,4,5,6,7,8,9,\n"
    )[0]
    scalar = h.parse_benchmark_tensors(
        "name: scalar, Elements: 1, Shape: [], Data:\n3.5,\n"
    )[0]
    empty = h.parse_benchmark_tensors(
        "name: empty, Elements: 0, Shape: [2 0], Data:\n\n"
    )[0]

    assert real["shape"] == (1, 10)
    assert real["data"].shape == (1, 10)
    assert scalar["data"].shape == ()
    assert empty["data"].shape == (2, 0)
    assert empty["data_error"] is None


def test_parse_rejects_huge_dimension_and_shape_trailing_junk():
    huge = h.parse_benchmark_tensors(
        "name:out, Elements: 1, Shape: [999999999999999999999], Data:\n1\n"
    )[0]
    junk = h.parse_benchmark_tensors(
        "name:out, Elements: 2, Shape: [2]oops, Data:\n1,2\n"
    )[0]
    assert huge["shape"] is None
    assert "too large" in huge["shape_error"]
    assert junk["shape"] is None
    assert "invalid shape metadata header" in junk["shape_error"]


def test_judge_reports_negative_shape_as_structured_fail(tmp_path):
    case = tmp_path / "tc1"
    gt_dir = case / "gt"
    gt_dir.mkdir(parents=True)
    np.save(gt_dir / "output.npy", np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32))

    status, cos, msg = h.judge_path_from_stdout(
        case, "x86_fp32",
        "name:out, Elements: 4, Shape: [-1 4], Data:\n1,2,3,4\n", "", 0,
    )

    assert status == "FAIL"
    assert cos is None
    assert "invalid shape metadata" in msg


def test_judge_accepts_valid_empty_tensor(tmp_path):
    case = tmp_path / "tc1"
    gt_dir = case / "gt"
    gt_dir.mkdir(parents=True)
    np.save(gt_dir / "output.npy", np.empty((2, 0), dtype=np.float32))

    status, cos, msg = h.judge_path_from_stdout(
        case, "x86_fp32",
        "name:out, Elements: 0, Shape: [2 0], Data:\n\n", "", 0,
    )

    assert status == "PASS"
    assert cos == 1.0
    assert msg == ""


@pytest.mark.parametrize("payload", ["1,,2", "1,BAD,2", "1,nan,2", "1,1e999,2"])
def test_judge_reports_invalid_benchmark_data_without_traceback(tmp_path, payload):
    case = tmp_path / "tc1"
    gt_dir = case / "gt"
    gt_dir.mkdir(parents=True)
    np.save(gt_dir / "output.npy", np.array([1.0, 2.0], dtype=np.float32))

    status, cos, msg = h.judge_path_from_stdout(
        case, "x86_fp32",
        f"name:out, Elements: 2, Shape: [2], Data:\n{payload}\n", "", 0,
    )

    assert status == "FAIL"
    assert cos is None
    assert "invalid tensor data" in msg


def test_judge_rejects_missing_elements_metadata(tmp_path):
    case = tmp_path / "tc1"
    gt_dir = case / "gt"
    gt_dir.mkdir(parents=True)
    np.save(gt_dir / "output.npy", np.array([1.0], dtype=np.float32))

    status, cos, msg = h.judge_path_from_stdout(
        case, "x86_fp32", "name:out, Shape: [1], Data:\n1\n", "", 0,
    )

    assert status == "FAIL"
    assert cos is None
    assert "Elements metadata missing" in msg


# =========================================================================== #
# C. assert_int8_genuine — INT8_NOT_GENUINE gate. Proves the int8 kernel was
#    actually CALLED in generated net*.c, defeating the flat-cos=1.0 fp32-fallback
#    trap. Disabling it (INT8_KERNEL_SYMBOL="") is reserved for int8-exempt ops.
# =========================================================================== #

def _write_net(work_dir: Path, body: str):
    d = work_dir / "onnx_riscv_micro" / "src" / "model0"
    d.mkdir(parents=True, exist_ok=True)
    (d / "net0.c").write_text(body)


def test_int8_genuine_when_default_symbol_called(tmp_path):
    spec = _fake_spec("Hardmax")  # default symbol -> HardmaxInt8
    _write_net(tmp_path, "int ret = HardmaxInt8(input, output);\n")
    status, why = h.assert_int8_genuine(spec, tmp_path)
    assert status == "genuine"
    assert "HardmaxInt8" in why


def test_int8_not_genuine_when_symbol_absent(tmp_path):
    spec = _fake_spec("Hardmax")
    _write_net(tmp_path, "int ret = HardmaxFp32(input, output);\n")  # fp32 fallback
    status, why = h.assert_int8_genuine(spec, tmp_path)
    assert status == "missing"
    assert "not called" in why


def test_int8_definition_present_but_not_called_is_not_genuine(tmp_path):
    # The symbol's *definition* may be copied into the project even on fp32 fallback;
    # only a CALL (symbol followed by "(") in net*.c counts. A bare mention must not pass.
    spec = _fake_spec("Hardmax")
    _write_net(tmp_path, "// see HardmaxInt8 elsewhere; not invoked here\n")
    status, _ = h.assert_int8_genuine(spec, tmp_path)
    assert status == "missing"


def test_int8_custom_symbol(tmp_path):
    # activation subtypes use non-default names (e.g. HardSwish -> HSwishInt8)
    spec = _fake_spec("HardSwish", INT8_KERNEL_SYMBOL="HSwishInt8")
    _write_net(tmp_path, "HSwishInt8(x, y);\n")
    status, why = h.assert_int8_genuine(spec, tmp_path)
    assert status == "genuine"
    assert "HSwishInt8" in why


def test_int8_symbol_list(tmp_path):
    spec = _fake_spec("Foo", INT8_KERNEL_SYMBOL=["BarInt8", "FooInt8"])
    _write_net(tmp_path, "FooInt8(a, b);\n")
    status, _ = h.assert_int8_genuine(spec, tmp_path)
    assert status == "genuine"


def test_int8_check_disabled_by_empty_symbol_is_exempt_not_genuine(tmp_path):
    # int8-exempt ops (pure index/non-float output) opt out explicitly.
    spec = _fake_spec("Argmax", INT8_KERNEL_SYMBOL="")
    # no net*.c at all; this is an explicit exemption, not proof of an int8 call.
    status, why = h.assert_int8_genuine(spec, tmp_path)
    assert status == "exempt"
    assert "disabled" in why


def test_int8_no_net_files_is_not_genuine(tmp_path):
    spec = _fake_spec("Hardmax")  # check enabled, but codegen produced nothing
    status, why = h.assert_int8_genuine(spec, tmp_path)
    assert status == "missing"
    assert "no generated net" in why


# =========================================================================== #
# D. check_case_regression — CASES_REDUCED gate ("delete a FAIL case to go green").
# =========================================================================== #

def _write_summary(path: Path, op: str, entries):
    """entries: list of (framework, case_id, status). Mirrors the real summary format."""
    lines = ["hs-verify-op-host summary", f"op={op}  frameworks=['onnx']", "-" * 60]
    for fw, cid, st in entries:
        lines.append(f"{fw:<6} tc{cid:<3} x86_fp32    {st:<4} cos=1.000000")
    lines += ["-" * 60, "VERDICT: ...", "HARNESS_EXIT=0"]
    path.write_text("\n".join(lines) + "\n")


def test_regression_no_prev_summary_is_silent(tmp_path):
    spec = _fake_spec("Hardmax", onnx=[{"id": 1}])
    assert h.check_case_regression(tmp_path / "nope.txt", spec, ["onnx"]) == []


def test_regression_different_op_is_ignored(tmp_path):
    summ = tmp_path / "verify_summary.txt"
    _write_summary(summ, "SomeOtherOp", [("onnx", 1, "PASS"), ("onnx", 2, "FAIL")])
    spec = _fake_spec("Hardmax", onnx=[{"id": 1}])  # fewer cases, but different op
    assert h.check_case_regression(summ, spec, ["onnx"]) == []


def test_regression_no_shrink_is_silent(tmp_path):
    summ = tmp_path / "verify_summary.txt"
    _write_summary(summ, "Hardmax", [("onnx", 1, "PASS"), ("onnx", 2, "PASS")])
    spec = _fake_spec("Hardmax", onnx=[{"id": 1}, {"id": 2}])
    assert h.check_case_regression(summ, spec, ["onnx"]) == []


def test_regression_shrink_without_ack_exits(tmp_path, monkeypatch):
    monkeypatch.delenv("OP_VERIFY_ACK_REDUCED", raising=False)
    summ = tmp_path / "verify_summary.txt"
    _write_summary(summ, "Hardmax", [("onnx", 1, "PASS"), ("onnx", 2, "FAIL")])
    spec = _fake_spec("Hardmax", onnx=[{"id": 1}])  # tc2 (a prior FAIL) deleted
    with pytest.raises(SystemExit):
        h.check_case_regression(summ, spec, ["onnx"])


def test_regression_shrink_with_ack_returns_traced_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("OP_VERIFY_ACK_REDUCED", "1")
    summ = tmp_path / "verify_summary.txt"
    _write_summary(summ, "Hardmax", [("onnx", 1, "PASS"), ("onnx", 2, "FAIL")])
    spec = _fake_spec("Hardmax", onnx=[{"id": 1}])
    lines = h.check_case_regression(summ, spec, ["onnx"])
    assert lines  # non-empty trace folded into the VERDICT
    assert any("ACK_REDUCED" in ln for ln in lines)
    assert any("tc2" in ln for ln in lines)


# =========================================================================== #
# E. capability checklist gates — validate_checklist_refs (pre-run) +
#    report_capability_coverage (post-run). Defends "rewrite the checklist to
#    match existing cases" by keeping coverage measured against the COMMITMENT.
# =========================================================================== #

def test_checklist_valid_passes(monkeypatch):
    spec = _fake_spec("Hardmax", onnx=[{"id": 1, "params": {"axis": 0}}, {"id": 2}])
    checklist = {"capabilities": [
        {"id": "c1", "desc": "axis 0", "covered_by": [1], "match": {"axis": 0}},
        {"id": "c2", "desc": "another", "covered_by": [2]},
    ]}
    # no exception == pass
    h.validate_checklist_refs(checklist, spec, ["onnx"])


def test_checklist_empty_covered_by_exits():
    spec = _fake_spec("Hardmax", onnx=[{"id": 1}])
    checklist = {"capabilities": [{"id": "c1", "desc": "x", "covered_by": []}]}
    with pytest.raises(SystemExit):
        h.validate_checklist_refs(checklist, spec, ["onnx"])


def test_checklist_dangling_ref_exits():
    spec = _fake_spec("Hardmax", onnx=[{"id": 1}])
    checklist = {"capabilities": [{"id": "c1", "desc": "x", "covered_by": [99]}]}
    with pytest.raises(SystemExit):
        h.validate_checklist_refs(checklist, spec, ["onnx"])


def test_checklist_match_mismatch_exits():
    # covered_by points at a case whose params don't satisfy the declared predicate
    spec = _fake_spec("Hardmax", onnx=[{"id": 1, "params": {"axis": -1}}])
    checklist = {"capabilities": [
        {"id": "c1", "desc": "axis 0", "covered_by": [1], "match": {"axis": 0}},
    ]}
    with pytest.raises(SystemExit):
        h.validate_checklist_refs(checklist, spec, ["onnx"])


def test_coverage_all_covered():
    checklist = {"capabilities": [
        {"id": "c1", "desc": "a", "covered_by": [1]},
        {"id": "c2", "desc": "b", "covered_by": [2, 3]},
    ]}
    lines, uncovered = h.report_capability_coverage(checklist, passed_case_ids={1, 3})
    assert uncovered == 0
    assert any("[COVERED]" in ln and "c1" in ln for ln in lines)


def test_coverage_uncovered_when_no_covering_case_passed():
    checklist = {"capabilities": [
        {"id": "c1", "desc": "a", "covered_by": [1]},
        {"id": "c2", "desc": "b", "covered_by": [2]},
    ]}
    # tc2 did not pass -> c2 uncovered -> run must be non-green
    lines, uncovered = h.report_capability_coverage(checklist, passed_case_ids={1})
    assert uncovered == 1
    assert any("[UNCOVERED]" in ln and "c2" in ln for ln in lines)


# =========================================================================== #
# F. _err_msg — turns a failed path into an actionable reason. The crash/timeout
#    classification must not regress into a generic "no output" message.
# =========================================================================== #

def test_errmsg_timeout_from_returncode(tmp_path):
    msg = h._err_msg("", "", tmp_path, rc=-9)
    assert "TIMEOUT" in msg


def test_errmsg_timeout_from_text(tmp_path):
    msg = h._err_msg("", "[ERR] path timed out after 1200s and was killed", tmp_path, rc=0)
    assert "TIMEOUT" in msg


def test_errmsg_sigabrt(tmp_path):
    # bash reports 128+signal; SIGABRT == 6 -> rc 134
    msg = h._err_msg("", "", tmp_path, rc=134)
    assert "SIGABRT" in msg


def test_errmsg_sigsegv(tmp_path):
    msg = h._err_msg("", "", tmp_path, rc=139)  # 128 + 11
    assert "SIGSEGV" in msg


def test_errmsg_heap_corruption_signature(tmp_path):
    msg = h._err_msg("malloc(): corrupted top size\n", "", tmp_path, rc=0)
    assert "heap corruption" in msg.lower()


def test_errmsg_generic_build_error(tmp_path):
    msg = h._err_msg("foo\n[ERR] converter_lite failed: op not registered\nbar", "", tmp_path, rc=1)
    assert "op not registered" in msg


# =========================================================================== #
# G. make_cfg — multi-input calibration path formatting (riscv_int8 only).
#    Generalizes to any input count (TFLite Select/Where have 3 inputs).
# =========================================================================== #

def test_make_cfg_non_int8_returns_template_unchanged():
    # x86 / riscv fp32 cfgs have no placeholders -> the template path itself is returned
    out = h.make_cfg("x86_fp32", "micro_x86.cfg", Path("/tmp"), ["in"], [])
    assert out == h.SCRIPT_DIR / "micro_x86.cfg"


def test_make_cfg_int8_fills_one_entry_per_input(tmp_path):
    in_names = ["cond", "x", "y"]
    calib_dirs = [tmp_path / "c0", tmp_path / "c1", tmp_path / "c2"]
    out = h.make_cfg("riscv_int8", "micro_riscv_quant.cfg", tmp_path, in_names, calib_dirs)
    text = out.read_text()
    assert "{CALIBRATE_PATH}" not in text  # placeholder must be filled
    # one name:dir entry per input, comma-joined
    for name, d in zip(in_names, calib_dirs):
        assert f"{name}:{d}" in text
    assert text.count(",") >= 2  # 3 entries -> at least 2 separators on the calibrate line


# =========================================================================== #
# H. Single-case rerun contract — _run.sh can be rerun manually, and the latest
#    stdout is what refreshes output*.npy + the local judge result against stable
#    gt/output*.npy. This keeps manual tc reproduction and full harness runs on
#    the same parser/cosine/threshold path.
# =========================================================================== #

def test_judge_path_from_stdout_refreshes_outputs_and_reports_latest_result(tmp_path):
    case = tmp_path / "tc1"
    gt_dir = case / "gt"
    out_dir = case / "output" / "x86_fp32"
    gt_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)
    np.save(gt_dir / "output.npy", np.array([1.0, 2.0, 3.0], dtype=np.float32))
    np.save(out_dir / "output.npy", np.array([1.0, 2.0, 3.0], dtype=np.float32))  # stale PASS

    status, cos, msg = h.judge_path_from_stdout(
        case, "x86_fp32",
        "name:out, Elements: 3, Shape: [3 ], Data:\n0.0,0.0,0.0\n", "", 0,
    )

    assert status == "FAIL"
    assert cos == 0.0
    assert "cos 0.000000 < 0.999" in msg
    assert np.allclose(np.load(out_dir / "output.npy"), [0.0, 0.0, 0.0])
    assert "FAIL" in (out_dir / "judge.txt").read_text()


def test_judge_path_from_stdout_reports_truncated_tensor_as_structured_fail(tmp_path):
    case = tmp_path / "tc1"
    gt_dir = case / "gt"
    gt_dir.mkdir(parents=True)
    np.save(gt_dir / "output.npy", np.array([1.0, 2.0, 3.0], dtype=np.float32))

    status, cos, msg = h.judge_path_from_stdout(
        case, "x86_fp32",
        "name:out, Elements: 3, Shape: [3 ], Data:\n1.0,2.0\n", "", 0,
    )

    assert status == "FAIL"
    assert cos is None
    assert "data truncated" in msg
    assert "FAIL" in (case / "output" / "x86_fp32" / "judge.txt").read_text()


def test_judge_path_from_stdout_rejects_same_values_with_wrong_shape(tmp_path):
    case = tmp_path / "tc1"
    gt_dir = case / "gt"
    gt_dir.mkdir(parents=True)
    np.save(gt_dir / "output.npy", np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32))

    status, cos, msg = h.judge_path_from_stdout(
        case, "x86_fp32",
        "name:out, Elements: 4, Shape: [4 ], Data:\n1.0,2.0,3.0,4.0\n", "", 0,
    )

    assert status == "FAIL"
    assert cos is None
    assert "shape mismatch" in msg


@pytest.mark.skipif(os.name == "nt", reason="POSIX bash wrapper paths are exercised in WSL")
def test_run_driver_generates_rerunnable_wrapper_that_refreshes_judgement(tmp_path, monkeypatch):
    script_dir = tmp_path / "skill_scripts"
    script_dir.mkdir()
    (script_dir / "dummy_driver.sh").write_text(
        "echo 'name:out, Elements: 3, Shape: [3 ], Data:'\n"
        "echo '1.0,2.0,3.0'\n"
        "echo 'driver stderr' >&2\n"
    )
    (script_dir / "micro_x86.cfg").write_text("")
    monkeypatch.setattr(h, "SCRIPT_DIR", script_dir)
    monkeypatch.setitem(h.DRIVER, ("onnx", "x86_fp32"), ("dummy_driver.sh", "micro_x86.cfg"))
    monkeypatch.setattr(h, "_converter_encryption_capability", lambda _pkg: ("", "mock capability"))
    monkeypatch.setattr(h, "_converter_runtime_env", lambda _pkg: ({}, ()))

    case = tmp_path / "tc1"
    gt_dir = case / "gt"
    gt_dir.mkdir(parents=True)
    np.save(gt_dir / "output.npy", np.array([1.0, 2.0, 3.0], dtype=np.float32))
    build_dir = case / "convert" / "x86_fp32"
    log_dir = case / "output" / "x86_fp32"
    spec_path = tmp_path / "op_spec.py"
    spec_path.write_text("OP_NAME = 'Dummy'\n")

    stdout, stderr, rc = h.run_driver(
        "onnx", "x86_fp32", build_dir, log_dir, "/pkg",
        case / "model" / "model.onnx", script_dir / "micro_x86.cfg", [],
        case_dir=case, spec_path=spec_path,
    )
    assert rc == 0
    assert "1.0,2.0,3.0" in stdout
    assert "driver stderr" in stderr
    assert np.allclose(np.load(log_dir / "output.npy"), [1.0, 2.0, 3.0])

    np.save(log_dir / "output.npy", np.array([9.0, 9.0, 9.0], dtype=np.float32))
    completed = subprocess.run(["bash", str(log_dir / "_run.sh")], cwd=str(tmp_path),
                               text=True, capture_output=True, check=False)

    assert completed.returncode == 0
    assert np.allclose(np.load(log_dir / "output.npy"), [1.0, 2.0, 3.0])
    assert "PASS" in (log_dir / "judge.txt").read_text()


# =========================================================================== #
# I. Native integer/exempt INT8 contract + model input integrity.
# =========================================================================== #

def test_int8_exempt_note_is_not_reported_as_genuine(tmp_path):
    case = tmp_path / "tc1"
    gt_dir = case / "gt"
    gt_dir.mkdir(parents=True)
    np.save(gt_dir / "output.npy", np.array([1.0, 2.0, 3.0], dtype=np.float32))
    spec = _fake_spec("ConvInteger", INT8_KERNEL_SYMBOL="")

    status, cos, msg = h.judge_path_from_stdout(
        case, "riscv_int8",
        "name:out, Elements: 3, Shape: [3 ], Data:\n1.0,2.0,3.0\n", "", 0,
        spec=spec, build_dir=tmp_path / "build",
    )

    assert status == "PASS"
    assert cos == pytest.approx(1.0)
    assert "int8_exempt=yes" in msg
    assert "int8_genuine=yes" not in msg


def test_assert_model_input_contract_rejects_missing_dynamic_input(tmp_path):
    class ValueInfo:
        def __init__(self, name):
            self.name = name

    spec = _fake_spec("ConvInteger")
    tc = {"id": 1}
    with pytest.raises(ValueError, match="make_inputs.*returned 1 arrays.*model has 2 dynamic inputs"):
        h.assert_model_input_contract(
            "onnx", tc, spec, [ValueInfo("x"), ValueInfo("w")], [np.zeros((1,), np.int8)], set()
        )


def test_board_matrix_entry_is_emitted_only_for_riscv_variants(tmp_path):
    assert h.make_board_matrix_entry(
        tmp_path, "Add", "onnx", "broadcast", "x86_fp32", "PASS", 1.0
    ) is None

    entry = h.make_board_matrix_entry(
        tmp_path, "Add", "onnx", "broadcast", "riscv_int8", "PASS", 0.998
    )
    assert entry["framework"] == "onnx"
    assert entry["case_id"] == "broadcast"
    assert entry["mode"] == "int8"
    assert entry["host_path"] == "riscv_int8"
    assert entry["host_status"] == "PASS"
    assert entry["model"].endswith("output\\onnx\\tcbroadcast\\model\\model.onnx") \
        or entry["model"].endswith("output/onnx/tcbroadcast/model/model.onnx")


def test_load_spec_requires_only_selected_framework_builder(tmp_path):
    spec_path = tmp_path / "op_spec.py"
    spec_path.write_text(
        "OP_NAME = 'OnlyOnnx'\n"
        "ONNX_TEST_CASES = []\n"
        "TFLITE_TEST_CASES = []\n"
        "def build_onnx_model(*args): pass\n"
        "def make_inputs(*args): return []\n"
    )

    spec = h.load_spec(spec_path, ["onnx"])
    assert spec.OP_NAME == "OnlyOnnx"
    with pytest.raises(SystemExit, match="build_tflite_model"):
        h.load_spec(spec_path, ["onnx", "tflite"])
