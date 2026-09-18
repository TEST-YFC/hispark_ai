#!/usr/bin/env python3
"""Execute one generated Micro FP32 training case; never infer PASS from logs.

The caller supplies a locked model and independent reference arrays. This runner
checks numerical evidence and the generated training graph before building.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import zipfile

import numpy as np

ATOL = RTOL = 1e-5


def graph_checker():
    spec = importlib.util.spec_from_file_location(
        'hs_training_graph_checker', Path(__file__).with_name('check_training_graph.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def evidence(path):
    p = Path(path).resolve()
    return {"path": str(p), "sha256": sha256(p), "bytes": p.stat().st_size}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def shape_size(shape):
    require(isinstance(shape, list) and all(type(x) is int and x > 0 for x in shape), "invalid static shape")
    return math.prod(shape)


def resolve_file(base, item):
    base = Path(base).resolve()
    require(isinstance(item, dict) and isinstance(item.get("path"), str), "missing file path")
    raw = Path(item["path"])
    require(not raw.is_absolute(), "file path must be relative")
    p = (base / raw).resolve()
    require(p == base or base in p.parents, f"file path escapes case directory: {p}")
    require(p.is_file(), f"missing file: {p}")
    require(item.get("sha256") == sha256(p), f"source hash mismatch: {p}")
    return p


def read_tensor(path, shape, dtype="float32"):
    require(dtype in ("float32", "int32"), f"unsupported dtype: {dtype}")
    dt = np.dtype("<f4" if dtype == "float32" else "<i4")
    require(Path(path).stat().st_size == shape_size(shape) * dt.itemsize, f"tensor byte count: {path}")
    value = np.fromfile(path, dtype=dt).reshape(shape)
    require(np.isfinite(value).all(), f"non-finite tensor: {path}")
    return value


def compare(actual, reference, name):
    require(actual.shape == reference.shape, f"shape mismatch: {name}")
    require(actual.dtype == reference.dtype == np.dtype("float32"), f"dtype mismatch: {name}")
    require(actual.size > 0 and np.isfinite(actual).all() and np.isfinite(reference).all(), f"non-finite/empty: {name}")
    error = np.abs(actual.astype(np.float64) - reference.astype(np.float64))
    require(np.all(error <= ATOL + RTOL * np.abs(reference.astype(np.float64))), f"numerical mismatch: {name}; max_abs={error.max()}")
    return {"name": name, "status": "PASS", "elements": actual.size, "max_abs": float(error.max())}


def load_case(path):
    path = Path(path).resolve()
    c = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(c, dict), "case root must be an object")
    require(c.get("schema_version") == 1 and c.get("verification_kind") == "training", "case version/kind")
    require(isinstance(c.get("case_id"), str) and re.fullmatch(r"[A-Za-z0-9_-]+", c["case_id"]), "case_id")
    require(c.get("kind") in ("numerical", "reject"), "case kind")
    require(isinstance(c.get("test_point"), str) and bool(c["test_point"].strip()), "test_point")
    base = path.parent
    model = resolve_file(base, c["model"])
    files = [path, model]
    t = c.get("training", {})
    for key, default in (("learning_rate", 0.01), ("momentum", 0.0)):
        value = t.get(key, default)
        require(type(value) in (float, int) and math.isfinite(value) and value >= 0, key)
        t[key] = value
    require(re.fullmatch(r"[A-Za-z0-9_./-]+", t.get("label_tensor_name", "label")), "label name")
    blacklists = t.get("fusion_blacklists", [])
    require(isinstance(blacklists, list) and all(isinstance(x, str) and re.fullmatch(r"[A-Za-z0-9_./-]+", x) for x in blacklists), "fusion_blacklists")
    frozen = t.get("frozen_nodes", [])
    require(isinstance(frozen, list) and all(isinstance(x, str) and re.fullmatch(r"[A-Za-z0-9_./-]+", x) for x in frozen), "frozen node names")
    c["training"] = t
    c["model_path"] = str(model)
    if c["kind"] == "reject":
        require(isinstance(c.get("expected_error"), str) and c["expected_error"].strip(), "specific expected_error required")
        return c, files
    require(c.get("graph_expectations_version") == 1, "graph_expectations_version must be 1")
    ge = c.get("graph_expectations")
    require(isinstance(ge, dict) and isinstance(ge.get("targets"), list) and ge["targets"], "graph_expectations.targets required")
    barrier_flag = ge.get("gradient_barrier", False)
    require(type(barrier_flag) is bool, "gradient_barrier must be a boolean")
    barrier = barrier_flag is True
    for target in ge["targets"]:
        require(isinstance(target, dict) and isinstance(target.get("forward_name"), str) and
                isinstance(target.get("backward_name", target.get("forward_name")), str) and
                isinstance(target.get("forward_primitive"), int), "invalid graph target expectation")
        if not barrier:
            require(isinstance(target.get("backward_symbols"), list) and target["backward_symbols"],
                    "invalid graph target expectation")
    if barrier:
        require(not ge.get("upstream_paths"), "upstream_paths is not valid for gradient_barrier")
        for key in ("parallel_upstream_paths", "barrier_upstream_paths"):
            require(isinstance(ge.get(key), list) and ge[key], f"graph_expectations.{key} required")
    else:
        ups = ge.get("upstream_paths")
        require(isinstance(ups, list) and ups, "graph_expectations.upstream_paths required")
        for item in ups:
            require(isinstance(item, dict) and isinstance(item.get("upstream_backward"), dict) and
                    isinstance(item.get("optimizer"), dict) and
                    isinstance(item.get("forward_upstream"), dict) and
                    isinstance(item.get("forward_target"), dict), "invalid upstream path expectation")
    steps = t.get("steps")
    require(type(steps) is int and steps >= 2, "steps must be >= 2")
    require(isinstance(c.get("sequence"), list) and len(c["sequence"]) == steps, "sequence length")
    first_layout = None
    for sample in [*c["sequence"], c["eval"]]:
        require(isinstance(sample.get("inputs"), list) and sample["inputs"], "sample inputs")
        require(isinstance(sample.get("labels"), list) and len(sample["labels"]) == 1, "one CE label required")
        paths = []
        for role in ("inputs", "labels"):
            for spec in sample[role]:
                expected_dtype = "float32" if role == "inputs" else "int32"
                require(spec.get("dtype") == expected_dtype, "sample dtype")
                if role == "labels":
                    require(spec.get("shape") == [1], "batch=1 label shape")
                f = resolve_file(base, spec)
                read_tensor(f, spec["shape"], expected_dtype)
                require(not any(x in str(f) for x in (",", "\n", "\r")), "unsupported delimiter in input path")
                files.append(f)
                paths.append(str(f))
        layout = [(x["dtype"], x["shape"]) for x in sample["inputs"] + sample["labels"]]
        if first_layout is None:
            first_layout = layout
        require(layout == first_layout, "sample layouts differ")
        sample["argument"] = ",".join(paths)
    require(isinstance(c.get("reference_source"), str) and c["reference_source"].strip(), "reference_source")
    golden = resolve_file(base, c["golden"])
    files.append(golden)
    c["golden_path"] = str(golden)
    outputs = c.get("outputs", [])
    require(len(outputs) >= 2 and [x.get("index") for x in outputs] == list(range(len(outputs))), "ordered output indices")
    require(outputs[-1].get("role") == "loss" and all(x.get("role") == "logits" for x in outputs[:-1]), "logits followed by loss")
    require(shape_size(outputs[-1]["shape"]) == 1, "scalar loss")
    for x in outputs:
        shape_size(x["shape"])
        require(x.get("dtype", "float32") == "float32", "output dtype must be float32")
    weights = c.get("weights", [])
    require(weights, "weights required")
    names = [x.get("name") for x in weights]
    refs = [x.get("reference") for x in weights]
    require(all(isinstance(x, str) and x for x in names + refs), "weight names/reference keys")
    require(len(names) == len(set(names)) and len(refs) == len(set(refs)), "duplicate weight mapping")
    for x in weights:
        shape_size(x["shape"])
        require(x.get("dtype", "float32") in ("float32", "int32"), "weight dtype must be float32 or int32")
    upstream = c.get("upstream_weights", [])
    require(upstream and len(upstream) == len(set(upstream)) and set(upstream) <= set(names), "upstream weights")
    frozen_weights = c.get("frozen_weights", [])
    barrier_weights = c.get("barrier_weights", [])
    require(isinstance(barrier_weights, list) and len(barrier_weights) == len(set(barrier_weights)) and
            set(barrier_weights) <= set(names), "barrier weight mapping")
    require(not set(frozen_weights) & set(upstream), "frozen/upstream weight mapping")
    require(set(frozen_weights) <= set(names), "frozen weight mapping")
    if barrier:
        require(barrier_weights, "barrier_weights required")
    else:
        require(not barrier_weights, "barrier_weights is only valid for gradient_barrier")
    require(not set(barrier_weights) & set(upstream), "barrier/upstream weight mapping")
    require(not set(barrier_weights) & set(frozen_weights), "barrier/frozen weight mapping")
    if frozen:
        require(frozen_weights, "frozen snapshots required")
    c["source_graph"] = graph_checker().check_source_model(model, c["model"]["sha256"], ge)
    return c, list(dict.fromkeys(files))


def config_text(case):
    t = case["training"]
    result = ("[micro_param]\nenable_micro=true\ntarget=RISCV\nsupport_parallel=false\n\n"
              "[train]\ntrain_mode=fp32\ndump_training_graph=true\nloss=softmax_cross_entropy\n"
              f"label_tensor_name={t.get('label_tensor_name', 'label')}\noptimizer=sgd_with_momentum\n"
              f"learning_rate={t['learning_rate']}\nmomentum={t['momentum']}\nbatch_size=1\n")
    if t.get("frozen_nodes"):
        result += "frozen_node=" + ",".join(t["frozen_nodes"]) + "\n"
    if t.get("fusion_blacklists"):
        result += "\n[registry]\nfusion_blacklists=" + ",".join(t["fusion_blacklists"]) + "\n"
    return result


def converter_supports_encryption(returncode, help_text):
    """Recognize declared options, never infer support from a failed help probe."""
    require(returncode == 0, "converter --help probe failed; see converter_help.log")
    require(re.search(r"(?im)^\s*usage\s*:", help_text), "unrecognized converter --help output")
    options = set(re.findall(r"(?m)^[ \t]*--([A-Za-z][A-Za-z0-9_-]*)(?=[= \t\r\n]|$)", help_text))
    require({"fmk", "modelFile", "outputFile", "configFile"} <= options,
            "incomplete or unrecognized converter --help option declarations")
    return "encryption" in options


def benchmark_argv(case, benchmark, run_dir):
    steps = case["training"]["steps"]
    return [str(benchmark), case["sequence"][0]["argument"], str(steps), "0", "1", "1",
            case["eval"]["argument"], "", "0.9999", str(run_dir / "after"), str(run_dir / "before"),
            str(run_dir / "sequence.txt"), f"0,1,{steps}", str(run_dir / "checkpoints"), str(run_dir / "predict")]


def weight_arrays(directory, specs):
    path = directory / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(manifest, dict), "weight manifest root must be an object")
    items = manifest.get("weights", [])
    require(isinstance(items, list), "weight manifest weights must be a list")
    require(all(isinstance(x, dict) for x in items), "weight manifest entries must be objects")
    require(manifest.get("format_version") == 1 and manifest.get("weight_count") == len(items), "weight manifest format/count")
    require(all(isinstance(x.get("name"), str) and isinstance(x.get("file"), str) and
                isinstance(x.get("dtype"), str) and isinstance(x.get("shape"), list) and
                type(x.get("bytes")) is int for x in items), "malformed weight manifest entry")
    names = [x["name"] for x in items]
    require(len(names) == len(set(names)) and set(names) == {x["name"] for x in specs}, "weight name set mismatch")
    by_name = {x["name"]: x for x in specs}
    result = {}
    seen_files = set()
    for item in items:
        spec = by_name[item["name"]]
        require(item["dtype"] == spec.get("dtype", "float32") and item["shape"] == spec["shape"],
                "weight dtype/shape mismatch")
        require(item["bytes"] == 4 * shape_size(spec["shape"]), "weight manifest bytes mismatch")
        f = (directory / item["file"]).resolve()
        require(f.parent == directory.resolve() and f not in seen_files, "unsafe/duplicate weight file")
        seen_files.add(f)
        result[item["name"]] = read_tensor(f, spec["shape"], spec.get("dtype", "float32"))
    expected_bins = {directory / item["file"] for item in items}
    actual_bins = set(directory.glob("*.bin"))
    require(actual_bins == expected_bins, "weight binary file set mismatch")
    return result


def compare_run(case, run_dir):
    checks = []
    steps = case["training"]["steps"]
    checkpoints = [0, 1, steps]
    arrays = {}
    try:
        golden_file = np.load(case["golden_path"], allow_pickle=False)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise ValueError(f"invalid golden npz: {exc}") from exc
    with golden_file as golden:
        expected_keys = {f"predict/output_{x['index']}" for x in case["outputs"][:-1]}
        for step in checkpoints:
            expected_keys |= {f"step_{step}/output_{x['index']}" for x in case["outputs"]}
            expected_keys |= {f"step_{step}/weight/{x['reference']}" for x in case["weights"]}
        require(set(golden.files) == expected_keys, "reference array set mismatch")
        predict_files = set((run_dir / "predict").glob("*.bin"))
        require(predict_files == {run_dir / "predict" / f"step_-001_output_{x['index']}.bin" for x in case["outputs"][:-1]}, "predict file set mismatch")
        for output in case["outputs"][:-1]:
            i = output["index"]
            actual = read_tensor(run_dir / "predict" / f"step_-001_output_{i}.bin", output["shape"])
            checks.append(compare(actual, golden[f"predict/output_{i}"], f"predict/output_{i}"))
        dump = run_dir / "checkpoints"
        expected_output_files = {dump / f"step_{step:04d}_output_{x['index']}.bin" for step in checkpoints for x in case["outputs"]}
        require(set(dump.glob("*.bin")) == expected_output_files, "checkpoint output file set mismatch")
        for step in checkpoints:
            for output in case["outputs"]:
                i = output["index"]
                key = f"step_{step}/output_{i}"
                checks.append(compare(read_tensor(dump / f"step_{step:04d}_output_{i}.bin", output["shape"]), golden[key], key))
            arrays[step] = weight_arrays(dump / f"step_{step:04d}_weights", case["weights"])
            for spec in case["weights"]:
                key = f"step_{step}/weight/{spec['reference']}"
                actual_weight = arrays[step][spec["name"]]
                if spec.get("dtype", "float32") == "int32":
                    require(actual_weight.dtype == golden[key].dtype == np.dtype("int32"),
                            f"int32 weight dtype mismatch: {key}")
                    require(np.array_equal(actual_weight, golden[key]), f"int32 weight mismatch: {key}")
                    checks.append({"name": key, "status": "PASS", "elements": actual_weight.size})
                else:
                    checks.append(compare(actual_weight, golden[key], key))
        for phase, step in (("before", 0), ("after", steps)):
            exported = weight_arrays(run_dir / phase, case["weights"])
            for spec in case["weights"]:
                exported_weight = exported[spec["name"]]
                if spec.get("dtype", "float32") == "int32":
                    require(exported_weight.dtype == arrays[step][spec["name"]].dtype == np.dtype("int32"),
                            f"int32 weight dtype mismatch: {phase}/{spec['name']}")
                    require(np.array_equal(exported_weight, arrays[step][spec["name"]]),
                            f"int32 weight mismatch: {phase}/{spec['name']}")
                    checks.append({"name": f"{phase}/{spec['name']}", "status": "PASS",
                                   "elements": exported_weight.size})
                else:
                    checks.append(compare(exported_weight, arrays[step][spec["name"]], f"{phase}/{spec['name']}"))
        ref_map = {x["name"]: x["reference"] for x in case["weights"]}
        for name in case["upstream_weights"]:
            ref = ref_map[name]
            require(np.any(golden[f"step_1/weight/{ref}"] != golden[f"step_0/weight/{ref}"]), "zero reference upstream update")
            require(np.any(arrays[1][name] != arrays[0][name]), "zero actual upstream update")
            checks.append({"name": f"upstream_update/{name}", "status": "PASS"})
        for name in case.get("frozen_weights", []):
            for step in checkpoints[1:]:
                require(np.array_equal(arrays[0][name], arrays[step][name]), f"frozen parameter changed: {name}")
            checks.append({"name": f"frozen_unchanged/{name}", "status": "PASS"})
        for name in case.get("barrier_weights", []):
            for step in checkpoints[1:]:
                require(np.array_equal(arrays[0][name], arrays[step][name]),
                        f"parameter before gradient barrier changed: {name}")
                ref = next(x["reference"] for x in case["weights"] if x["name"] == name)
                require(np.array_equal(golden[f"step_0/weight/{ref}"], golden[f"step_{step}/weight/{ref}"]),
                        f"reference parameter before gradient barrier changed: {name}")
            checks.append({"name": f"barrier_unchanged/{name}", "status": "PASS"})
    return checks


def execute(case_path, pkg, run_dir, timeout=300, riscv_toolchain_path=None, jobs=None):
    require(jobs is None or (type(jobs) is int and jobs > 0),
            "jobs must be a positive integer")
    case_path, pkg, run_dir = (Path(x).resolve() for x in (case_path, pkg, run_dir))
    require(not run_dir.exists(), "run-dir must not exist; use a new directory")
    run_dir.mkdir(parents=True)
    shutil.copy2(case_path, run_dir / "case.json")
    summary = {"schema_version": 1, "verification_kind": "training", "run_id": run_dir.parent.name,
               "case_id": None, "status": "FAIL", "numerical_pass": False, "stages": [],
               "commands": [], "checks": [], "evidence": [], "riscv_toolchain_path": None, "not_evaluated": ["raw_gradients", "package_source_freshness", "graph_and_memory_semantics", "board"]}
    def stage(name, status, **fields):
        summary["stages"].append({"stage": name, "status": status, **fields})
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.pathsep.join([str(pkg / "tools/converter/lib"), str(pkg / "runtime/lib"), env.get("LD_LIBRARY_PATH", "")])
    def command(name, argv):
        log = run_dir / f"{name}.log"
        record = {"stage": name, "argv": [str(x) for x in argv], "exit_code": None, "log": str(log), "timeout_seconds": timeout}
        with log.open("w", encoding="utf-8") as stream:
            kwargs = dict(cwd=run_dir, env=env, stdout=stream, stderr=subprocess.STDOUT)
            if os.name == "posix":
                kwargs["start_new_session"] = True
            elif os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            try:
                proc = subprocess.Popen(argv, **kwargs)
            except OSError as exc:
                record["error"] = str(exc)
                stream.write(f"PROCESS START FAILED: {exc}\n")
                summary["commands"].append(record)
                raise
            try:
                rc = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                proc.wait()
                stream.write(f"\nTIMEOUT after {timeout}s\n")
                stream.flush()
                record["timed_out"] = True
                summary["commands"].append(record)
                return None, log
        record["exit_code"] = rc
        summary["commands"].append(record)
        return rc, log

    def verify_inputs(files):
        locked_paths = {str(Path(f).resolve()) for f in files}
        evidence_paths = {item["path"] for item in summary["evidence"]}
        require(locked_paths <= evidence_paths, "locked input evidence missing")
        # Recheck both case inputs and every tool/library captured as evidence.
        for item in summary["evidence"]:
            require(sha256(item["path"]) == item["sha256"], "source changed during run")
    try:
        c, files = load_case(case_path)
        summary.update(case_id=c["case_id"], kind=c["kind"], test_point=c["test_point"], case_sha256=sha256(case_path), reference_source=c.get("reference_source"))
        summary["evidence"] = [evidence(f) for f in files]
        if c["kind"] == "numerical":
            summary["source_graph"] = c["source_graph"]
            stage("source_graph", "PASS")
        converter = pkg / "tools/converter/converter/converter_lite"
        required = [converter]
        if c["kind"] == "numerical":
            required += [pkg / "tools/codegen/lib/cpu/libnnacl.a", pkg / "tools/codegen/lib/cpu/libwrapper.a"]
        missing = [str(x) for x in required if not x.is_file()]
        if c["kind"] == "numerical":
            missing += [x for x in ("cmake", "cc", "c++") if shutil.which(x) is None]
        if missing:
            summary["status"] = "NOT_RUN"
            stage("environment", "NOT_RUN", missing=missing)
            return summary
        stage("environment", "PASS")
        summary["evidence"] += [evidence(f) for f in required]
        capabilities = {"converter": evidence(converter), "supports_encryption": None,
                        "cwd": str(run_dir), "ld_library_path": env["LD_LIBRARY_PATH"],
                        "decision": "probe_not_completed"}
        summary["converter_capabilities"] = capabilities
        try:
            rc, help_log = command("converter_help", [str(converter), "--help"])
            capabilities.update(exit_code=rc, log=str(help_log))
            supported = converter_supports_encryption(rc, help_log.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError) as exc:
            capabilities["decision"] = "probe_failed"
            stage("converter_help", "FAIL", reason=str(exc))
            raise
        capabilities.update(supports_encryption=supported,
                            decision="declared_option" if supported else "not_declared_in_valid_help")
        stage("converter_help", "PASS", supports_encryption=supported)
        config = run_dir / "micro_train.cfg"
        config.write_text(config_text(c), encoding="utf-8")
        net = run_dir / "net"
        convert_args = [str(converter), "--fmk=ONNX", f"--modelFile={c['model_path']}",
                        f"--configFile={config}", f"--outputFile={net}"]
        if supported:
            convert_args.append("--encryption=false")
        rc, log = command("convert", convert_args)
        if c["kind"] == "reject":
            verify_inputs(files)
            normal_rejection = isinstance(rc, int) and 1 <= rc < 0xC0000000
            require(normal_rejection and c["expected_error"] in log.read_text(encoding="utf-8", errors="replace"), "expected converter rejection not observed")
            stage("convert", "PASS_EXPECTED_ERROR")
            summary["status"] = "PASS_EXPECTED_ERROR"
            return summary
        require(rc == 0, "converter failed; see convert.log")
        require((net / "CMakeLists.txt").is_file(), "generated CMakeLists.txt missing")
        try:
            checker = graph_checker()
            summary["graph_gate"] = checker.check_training_graph(net, {**c["graph_expectations"], "graph_expectations_version": c["graph_expectations_version"]})
            summary["evidence"].extend({"path": x["path"], "sha256": sha256(x["path"]), "bytes": x["bytes"]} for x in summary["graph_gate"]["evidence"])
        except (OSError, ValueError, re.error) as exc:
            summary["graph_gate"] = {"status": "FAIL", "reason": str(exc), "graph_expectations_version": c["graph_expectations_version"]}
            raise
        stage("graph_gate", "PASS")
        stage("convert", "PASS")
        toolchain = riscv_toolchain_path or os.environ.get("RISCV_TOOLCHAIN_PATH", "")
        if toolchain:
            toolchain_dir = Path(toolchain).expanduser()
            compiler_candidates = [toolchain_dir / "riscv32-linux-musl-gcc", toolchain_dir / "riscv32-unknown-linux-musl-gcc"]
            if os.name == "nt":
                compiler_candidates += [x.with_suffix(".exe") for x in compiler_candidates]
            require(toolchain_dir.is_dir(), f"RISC-V toolchain directory not found: {toolchain_dir}")
            require(any(x.is_file() for x in compiler_candidates), f"RISC-V compiler not found in: {toolchain_dir}")
        summary["riscv_toolchain_path"] = toolchain
        cmake_args = ["cmake", "-S", str(net), "-B", str(net / "build"), f"-DPKG_PATH={pkg}", f"-DOP_LIB={pkg}/tools/codegen/lib/cpu/libnnacl.a", f"-DWRAPPER_LIB={pkg}/tools/codegen/lib/cpu/libwrapper.a", f"-DMS_ROOT_DIR={pkg}", f"-DRISCV_TOOLCHAIN_PATH={toolchain}", "-DMSLITE_TRAIN_BENCHMARK=ON"]
        rc, _ = command("configure", cmake_args)
        require(rc == 0, "native CMake configuration failed")
        build_args = ["cmake", "--build", str(net / "build")]
        if jobs is not None:
            build_args.append(f"-j{jobs}")
        rc, _ = command("build", build_args)
        require(rc == 0, "native build failed")
        stage("build", "PASS")
        benchmark = net / "build/benchmark"
        require(benchmark.is_file(), "generated training benchmark missing")
        for folder in ("before", "after", "predict", "checkpoints"):
            (run_dir / folder).mkdir()
        for step in (0, 1, c["training"]["steps"]):
            (run_dir / "checkpoints" / f"step_{step:04d}_weights").mkdir()
        (run_dir / "sequence.txt").write_text("\n".join(x["argument"] for x in c["sequence"]) + "\n", encoding="utf-8")
        rc, _ = command("benchmark", benchmark_argv(c, benchmark, run_dir))
        require(rc == 0, "training execution failed")
        stage("training", "PASS")
        # Recheck locked inputs/references after the tools finish.
        verify_inputs(files)
        summary["checks"] = compare_run(c, run_dir)
        stage("numerical", "PASS")
        summary.update(status="PASS", numerical_pass=True)
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, zipfile.BadZipFile) as exc:
        stage("failure", "FAIL", reason=str(exc))
        summary.update(status="FAIL", numerical_pass=False)
    finally:
        for p in run_dir.rglob("*"):
            if not p.is_file() or p.name == "train_summary.json":
                continue
            try:
                summary["evidence"].append(evidence(p))
            except Exception as exc:
                summary.setdefault("evidence_collection_error", []).append({
                    "path": str(p.resolve()), "reason": str(exc)
                })
        (run_dir / "train_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--pkg", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--timeout", type=float, default=300, help="per-command timeout in seconds (default: 300)")
    parser.add_argument("--riscv-toolchain-path", default=None, help="RISC-V toolchain bin directory; defaults to RISCV_TOOLCHAIN_PATH")
    parser.add_argument("-j", "--jobs", type=int, default=None,
                        help="Host native build parallel jobs; omitted by default")
    args = parser.parse_args(argv)
    try:
        require(args.timeout > 0 and math.isfinite(args.timeout), "timeout must be a positive finite number")
        require(args.jobs is None or args.jobs > 0, "jobs must be a positive integer")
        result = execute(args.case, args.pkg, args.run_dir, timeout=args.timeout,
                         riscv_toolchain_path=args.riscv_toolchain_path, jobs=args.jobs)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"TRAIN_CASE={result['status']} numerical_pass={result['numerical_pass']}")
    return 0 if result["status"] in ("PASS", "PASS_EXPECTED_ERROR") else 2


if __name__ == "__main__":
    sys.exit(main())
