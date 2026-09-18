#!/usr/bin/env python3
"""Aggregate training Host case results into a schema-1 train_verify_summary.json."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sys
import tempfile

import numpy as np

VALID = {"PASS", "FAIL", "NOT_RUN", "NOT_REQUESTED", "BLOCKED", "PASS_EXPECTED_ERROR"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def confined(path, base):
    """Check against the absolute, lexical boundary, not its symlink target."""
    resolved = path.resolve()
    require(resolved == base or base in resolved.parents, f"path escapes expected directory: {path}")
    return resolved



def resolve_evidence_path(raw, base):
    """Resolve native paths or exact drive <-> /mnt/drive aliases, within base.

    No search, relocation, UNC/device aliases or drive-relative paths. Resolve
    symlinks as well as checking the lexical boundary before opening evidence.
    """
    require(isinstance(raw, str) and raw and not any(ord(c) < 32 for c in raw),
            "invalid evidence path")
    win = PureWindowsPath(raw)
    drive = re.fullmatch(r"([A-Za-z]):[/\\](.*)", raw)
    mount = re.fullmatch(r"/mnt/([a-z])/(.*)", raw)
    require(not raw.startswith(("//", "\\")), "unsupported UNC/device evidence path")
    if drive:
        letter, tail = drive.groups()
        tail = tail.replace("\\", "/")
        local = f"{letter.upper()}:/{tail}" if os.name == "nt" else f"/mnt/{letter.lower()}/{tail}"
    elif mount:
        letter, tail = mount.groups()
        require("\\" not in tail, "invalid WSL evidence path")
        local = f"{letter.upper()}:/{tail}" if os.name == "nt" else raw
    else:
        require(not win.drive and os.name != "nt" and raw.startswith("/") and "\\" not in raw,
                "unsupported or non-absolute evidence path")
        tail, local = raw, raw
    require(not any(part in (".", "..") for part in tail.split("/")),
            "evidence path contains traversal")
    # Avoid Windows normalization aliases (ADS, trailing dots/spaces, devices).
    for part in tail.split("/"):
        require(not any(c in part for c in '<>:"|?*') and not part.endswith((".", " ")),
                "invalid evidence path component")
        device = part.split(".", 1)[0].upper()
        require(device not in {"CON", "PRN", "AUX", "NUL"} and
                not re.fullmatch(r"(?:COM|LPT)[1-9\u00b9\u00b2\u00b3]", device), "reserved evidence path component")
    path, boundary = Path(local), Path(base).resolve()
    require(path == boundary or boundary in path.parents,
            f"evidence path escapes expected directory: {raw}")
    return confined(path, boundary)


def graph_evidence_index(records, net):
    require(isinstance(records, list) and bool(records), "graph evidence list missing")
    result = {}
    for record in records:
        require(isinstance(record, dict), "invalid graph evidence record")
        path = resolve_evidence_path(record.get("path"), net)
        require(path not in result, "duplicate graph evidence path")
        digest = record.get("sha256")
        require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest),
                "invalid graph evidence hash")
        result[path] = digest
    return result


def output_path(root, run_id):
    require(isinstance(run_id, str) and bool(run_id.strip()) and run_id not in (".", ".."),
            "run_id must be a non-empty single directory name")
    require(not any(c in run_id for c in '/\\<>:"|?*') and
            not any(ord(c) < 32 for c in run_id) and not run_id.endswith((".", " ")) and
            not PureWindowsPath(run_id).drive,
            "run_id must be a safe single directory name")
    # Reject Windows device aliases, including when auditing their paths on Linux.
    device = run_id.split(".", 1)[0].upper()
    require(device not in {"CON", "PRN", "AUX", "NUL"} and
            not re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", device), "reserved run_id")
    run_dir = root / "runs" / run_id
    confined(run_dir, run_dir)
    out = run_dir / "train_verify_summary.json"
    # Do not overwrite an input or another run's report through an output symlink.
    confined(out, out)
    return out


def load_plan(path):
    plan = json.loads(path.read_text(encoding="utf-8"))
    expected = plan.get("cases", plan) if isinstance(plan, dict) else plan
    require(isinstance(expected, list) and bool(expected), "expected must be a non-empty case list")
    ids = set()
    for item in expected:
        require(isinstance(item, dict), "expected case must be an object")
        cid = item.get("case_id")
        # Keep exactly the runner.load_case naming contract, including '-' and '_'.
        require(isinstance(cid, str) and re.fullmatch(r"[A-Za-z0-9_-]+", cid), "invalid case_id")
        require(cid not in ids, f"duplicate case_id: {cid}")
        ids.add(cid)
        require(isinstance(item.get("kind"), str) and item["kind"] in ("numerical", "reject"),
                f"invalid kind: {cid}")
        require(isinstance(item.get("test_point"), str) and bool(item["test_point"].strip()),
                f"invalid test_point: {cid}")
    return expected


def validate_graph_evidence(root, run_id, cid, summary):
    """Bind archived case to its original inputs before rechecking generated evidence."""
    case_dir = (root / "runs" / run_id / cid).resolve()
    case_path = confined(case_dir / "case.json", case_dir)
    require(case_path.is_file(), f"current case manifest missing: {cid}")
    case_bytes = case_path.read_bytes()
    case_hash = hashlib.sha256(case_bytes).hexdigest()
    require(summary.get('case_sha256') == case_hash, f'archived case hash mismatch: {cid}')
    case = json.loads(case_bytes)
    require(isinstance(case, dict) and case.get('case_id') == cid and
            case.get('kind') == summary.get('kind') and case.get('test_point') == summary.get('test_point'),
            f'archived case identity mismatch: {cid}')
    require(case.get("graph_expectations_version") == 1 and isinstance(case.get("graph_expectations"), dict),
            f"graph expectations missing: {cid}")
    records = summary.get('evidence')
    require(isinstance(records, list) and all(isinstance(r, dict) for r in records),
            f'locked input evidence missing: {cid}')
    # The runner archives the case unchanged: its model path is relative to the
    # ORIGINAL case, not this run directory. Original and archived case hashes
    # must agree. This works with existing schema-1 runs, without guessing paths.
    candidates = {resolve_evidence_path(r.get('path'), root) for r in records
                  if r.get('sha256') == case_hash}
    candidates.discard(case_path)
    require(len(candidates) == 1, f'original case identity missing or ambiguous: {cid}')
    origin = candidates.pop()
    require(origin.is_file() and sha256(origin) == case_hash, f'original case hash mismatch: {cid}')
    model = case.get('model')
    require(isinstance(model, dict) and isinstance(model.get('path'), str) and model['path']
            and isinstance(model.get('sha256'), str), f'model identity missing: {cid}')
    relative = Path(model['path'])
    require(not relative.is_absolute() and not PureWindowsPath(model['path']).drive,
            f'model path must be relative to original case: {cid}')
    model_path = confined(origin.parent / relative, origin.parent)
    model_records = {resolve_evidence_path(r.get('path'), root) for r in records
                     if r.get('sha256') == model['sha256']}
    require(model_path in model_records, f'locked model evidence mismatch: {cid}')
    net = case_dir / "net"
    checker_path = Path(__file__).with_name("check_training_graph.py")
    sys.path.insert(0, str(checker_path.parent))
    try:
        from check_training_graph import check_training_graph, check_source_model
        source = check_source_model(model_path, model['sha256'], case['graph_expectations'])
        result = check_training_graph(net, case["graph_expectations"] | {"graph_expectations_version": case["graph_expectations_version"]})
    finally:
        sys.path.pop(0)
    require(summary.get("graph_gate", {}).get("status") == "PASS", f"summary graph gate is not PASS: {cid}")
    result['source_graph'] = source
    return result


def validate_summary(data, item, run_id):
    cid = item["case_id"]
    require(isinstance(data, dict), f"summary must be an object: {cid}")
    # Missing version remains compatible with historical summaries; declared versions must match.
    if "schema_version" in data:
        require(type(data["schema_version"]) is int and data["schema_version"] == 1,
                f"invalid summary schema_version: {cid}")
    require(data.get("run_id") == run_id and data.get("verification_kind") == "training" and
            data.get("case_id") == cid, f"summary identity mismatch: {cid}")
    require(data.get("kind") == item["kind"] and data.get("test_point") == item["test_point"],
            f"case identity mismatch: {cid}")
    status = data.get("status")
    require(isinstance(status, str) and status in VALID, f"invalid status for {cid}: {status}")
    require(isinstance(data.get("reason", ""), str), f"invalid reason: {cid}")
    if "numerical_pass" in data:
        require(type(data["numerical_pass"]) is bool, f"numerical_pass must be boolean: {cid}")
    if status == "PASS":
        require(item["kind"] == "numerical" and data.get("numerical_pass") is True,
                f"PASS requires numerical kind and numerical_pass=true: {cid}")
    elif status == "PASS_EXPECTED_ERROR":
        require(item["kind"] == "reject" and data.get("numerical_pass") is False,
                f"PASS_EXPECTED_ERROR requires reject kind and numerical_pass=false: {cid}")
    else:
        require(data.get("numerical_pass") is not True,
                f"non-success status cannot claim numerical_pass=true: {cid}")
    return status


def aggregate_case(root, run_id, item):
    cid = item["case_id"]
    rel = Path("runs") / run_id / cid / "train_summary.json"
    row = {"case_id": cid, "kind": item["kind"], "test_point": item["test_point"],
           "status": "NOT_RUN", "reason": "Missing current-run case summary.",
           "summary": {"path": rel.as_posix(), "sha256": ""}}
    try:
        case_dir = root / "runs" / run_id / cid
        confined(case_dir, case_dir)
        path = confined(root / rel, case_dir)
        if not path.exists():
            return row
        require(path.is_file(), f"summary is not a file: {cid}")
        # Preserve evidence even if JSON or semantics are invalid.
        row["summary"]["sha256"] = sha256(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        row["status"] = validate_summary(data, item, run_id)
        if row["status"] == "PASS" and item["kind"] == "numerical":
            graph = validate_graph_evidence(root, run_id, cid, data)
            net = case_dir / "net"
            confined(net, net)
            expected_evidence = graph_evidence_index(data.get("graph_gate", {}).get("evidence"), net)
            actual_evidence = graph_evidence_index(graph["evidence"], net)
            require(expected_evidence == actual_evidence, f"graph evidence hash mismatch: {cid}")
            archived_case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
            if archived_case.get("graph_expectations", {}).get("gradient_barrier") is True:
                checks = {check.get("name"): check.get("status") for check in data.get("checks", [])
                          if isinstance(check, dict)}
                required_checks = [f"barrier_unchanged/{name}" for name in archived_case.get("barrier_weights", [])]
                required_checks += [f"upstream_update/{name}" for name in archived_case.get("upstream_weights", [])]
                require(required_checks, "gradient-barrier case has no required weight checks")
                for name in required_checks:
                    require(checks.get(name) == "PASS", f"required numerical check missing or failed: {name}")
            graph_paths = graph.get("upstream_paths", graph.get("parallel_upstream_paths", []))
            row["graph_gate"] = {"status": "PASS", "targets": len(graph["targets"]),
                                  "upstream_paths": len(graph_paths),
                                  "gradient_barrier": graph.get("gradient_barrier", False)}
        row["reason"] = data.get("reason", "")
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
        row.update(status="FAIL", reason=str(exc))
    return row


def write_report(out, report):
    out.parent.mkdir(parents=True, exist_ok=True)
    confined(out.parent, out.parent)
    confined(out, out)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=out.parent,
                                         prefix=".train_verify_", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, out)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()



ATOL = RTOL = 1e-5


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def relative_inside(base: Path, value: str) -> Path:
    require(isinstance(value, str) and value, "invalid relative path")
    raw = PureWindowsPath(value)
    require(not raw.drive and not raw.anchor and "\\" not in value,
            f"path must be relative: {value}")
    path = (base / value).resolve()
    require(path == base.resolve() or base.resolve() in path.parents,
            f"path escapes opdir: {value}")
    return path


def evidence(path: Path, root: Path) -> dict:
    resolved = path.resolve()
    require(resolved == root.resolve() or root.resolve() in resolved.parents,
            f"evidence escapes opdir: {path}")
    return {"path": resolved.relative_to(root.resolve()).as_posix(),
            "sha256": sha256(resolved), "bytes": resolved.stat().st_size}


def check_locked_file(base: Path, item, label: str) -> Path:
    require(isinstance(item, dict) and isinstance(item.get("path"), str),
            f"{label} path missing")
    path = (base / item["path"]).resolve()
    require(path == base or base in path.parents, f"{label} escapes case directory")
    require(path.is_file(), f"{label} missing: {path}")
    require(item.get("sha256") == sha256(path), f"{label} hash mismatch")
    require(type(item.get("bytes")) is int and item["bytes"] == path.stat().st_size,
            f"{label} byte count mismatch")
    return path


def json_values(array: np.ndarray, dtype: str) -> list:
    require(array.dtype == np.dtype("<f4" if dtype == "float32" else "<i4"),
            f"golden dtype mismatch: {array.dtype} != {dtype}")
    require(bool(np.isfinite(array).all()), "golden contains non-finite values")
    if dtype == "int32":
        require(all(type(int(x)) is int for x in array.reshape(-1)), "invalid integer value")
        return [int(x) for x in array.reshape(-1)]
    # Dump the exact float32-compatible value, not a higher-precision display value.
    return [float(np.float32(x)) for x in array.reshape(-1)]


def build_expected(root: Path, run_id: str, case: dict, golden_path: Path,
                   case_digest: str, summary_digest: str) -> dict:
    require(case.get("schema_version") == 1 and case.get("verification_kind") == "training",
            "invalid case version/kind")
    require(case.get("kind") == "numerical", "only numerical cases can enter board denominator")
    require(case.get("case_id") and re.fullmatch(r"[A-Za-z0-9_-]+", case["case_id"]),
            "invalid case_id")
    training = case.get("training", {})
    steps = training.get("steps")
    require(type(steps) is int and steps >= 2, "training steps must be at least 2")
    checkpoints = sorted(set((0, 1, steps)))
    training = {**training, "checkpoints": checkpoints}
    outputs = case.get("outputs")
    weights = case.get("weights")
    require(isinstance(outputs, list) and len(outputs) >= 2, "case outputs missing")
    require(isinstance(weights, list) and bool(weights), "case weights missing")
    with np.load(golden_path, allow_pickle=False) as archive:
        require(isinstance(archive, np.lib.npyio.NpzFile), "golden must be an NPZ archive")
        tensors = {}
        golden_keys = set()

        def add(key, array: np.ndarray, dtype: str, **metadata):
            require(key not in tensors, f"duplicate expected tensor key: {key}")
            item = {"key": key, "dtype": dtype, "shape": list(array.shape),
                    "elements": int(array.size), "data": json_values(array, dtype), **metadata}
            tensors[key] = item

        def golden(key: str, dtype: str, shape: list, label: str) -> np.ndarray:
            golden_keys.add(key)
            require(key in archive.files, f"golden array missing: {key}")
            array = archive[key]
            require(array.dtype == np.dtype("<f4" if dtype == "float32" else "<i4") and
                    list(array.shape) == shape, f"golden dtype/shape mismatch: {label}")
            return array

        predict_indices = []
        for output in outputs:
            require(isinstance(output, dict) and type(output.get("index")) is int and
                    output["index"] >= 0, "invalid output index")
            dtype = output.get("dtype", "float32")
            require(dtype == "float32", "unsupported output dtype; expected float32")
            shape = output.get("shape")
            require(isinstance(shape, list) and all(type(x) is int and x > 0 for x in shape),
                    "invalid output shape")
            if output.get("role") == "loss":
                continue
            predict_indices.append(output["index"])
            key = f"predict/output_{output['index']}"
            add(key, golden(key, dtype, shape, key), dtype, phase="predict", role="output",
                name=f"output_{output['index']}")
        require(predict_indices, "case has no non-loss Predict output")
        for step in checkpoints:
            for output in outputs:
                key = f"step_{step}/output_{output['index']}"
                add(key, golden(key, output.get("dtype", "float32"), output["shape"], key),
                    output.get("dtype", "float32"), phase="eval", step=step, role="output",
                    name=f"output_{output['index']}")

        names = set()
        references = set()
        parameter_checks = []
        required_parameters = []
        upstream = set(case.get("upstream_weights", []))
        frozen = set(case.get("frozen_weights", []))
        barrier = set(case.get("barrier_weights", []))
        barrier_flag = case.get("graph_expectations", {}).get("gradient_barrier", False)
        require(type(barrier_flag) is bool, "gradient_barrier must be a boolean")
        for weight in weights:
            require(isinstance(weight, dict), "invalid weight entry")
            name, reference = weight.get("name"), weight.get("reference")
            require(isinstance(name, str) and name and isinstance(reference, str) and reference,
                    "invalid weight identity")
            require(name not in names and reference not in references,
                    "duplicate weight identity")
            names.add(name)
            references.add(reference)
            dtype = weight.get("dtype", "float32")
            require(dtype in ("float32", "int32"), "unsupported weight dtype")
            shape = weight.get("shape")
            require(isinstance(shape, list) and all(type(x) is int and x > 0 for x in shape),
                    "invalid weight shape")
            first_key = f"step_0/weight/{reference}"
            final_key = f"step_{steps}/weight/{reference}"
            first = golden(first_key, dtype, shape, first_key)
            final = golden(final_key, dtype, shape, final_key)
            for step in checkpoints:
                key = f"step_{step}/weight/{name}"
                add(key, golden(f"step_{step}/weight/{reference}", dtype, shape, key), dtype,
                    phase="train", step=step, role="parameter", name=name)
                required_parameters.append(key)
            for phase, step in (("before", 0), ("after", steps)):
                key = f"{phase}/{name}"
                add(key, golden(f"step_{step}/weight/{reference}", dtype, shape, key), dtype,
                    phase=phase, role="parameter", name=name)
                required_parameters.append(key)
            changed = not np.array_equal(first, final)
            if name in upstream:
                require(changed, f"declared upstream weight did not change: {name}")
            if name in frozen or name in barrier:
                require(not changed, f"declared frozen/barrier weight changed: {name}")
            parameter_checks.append({
                "kind": "must_change" if changed else "equal",
                "left": f"step_0/weight/{name}",
                "right": f"step_{steps}/weight/{name}",
                "name": name,
            })
        require(upstream <= names, "upstream weight mapping mismatch")
        require(frozen <= names and barrier <= names and not (frozen & upstream),
                "frozen/barrier weight mapping mismatch")
        if barrier_flag:
            require(barrier, "barrier_weights required")
        else:
            require(not barrier, "barrier_weights is only valid for gradient_barrier")
        require(not barrier & upstream, "barrier weight cannot also be upstream")
        require(not barrier & frozen, "barrier weight cannot also be frozen")
        # Expected protocol keys can use weight names; golden uses reference names.
        require(set(archive.files) == golden_keys,
                "golden array set differs from expected tensors")

    model = case.get("model")
    require(isinstance(model, dict), "case model missing")
    return {
        "schema_version": 1,
        "verification_kind": "training",
        "run_id": run_id,
        "case_id": case["case_id"],
        "framework": case.get("framework", "onnx"),
        "dtype": case.get("dtype", "float32"),
        "test_point": case.get("test_point", ""),
        "model_sha256": model.get("sha256"),
        "case_sha256": case_digest,
        "golden_sha256": sha256(golden_path),
        "host_summary_sha256": summary_digest,
        "tolerances": {"atol": ATOL, "rtol": RTOL},
        "training": training,
        "training_config": None,
        "tensors": list(tensors.values()),
        "required_parameters": required_parameters,
        "parameter_checks": parameter_checks,
    }


def atomic_new_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists() and not path.with_name(path.name + ".tmp").exists(),
            f"output already exists: {path}")
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")
    try:
        os.link(temporary, path)
    except OSError as exc:
        raise ValueError(f"cannot publish output without overwrite ({path}): {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def export(root: Path, run_id: str, summary_path: Path, output_dir: Path) -> dict:
    run_dir = root / "runs" / run_id
    require(summary_path == run_dir / "train_verify_summary.json", "summary path mismatch")
    summary = load_json(summary_path)
    require(summary.get("schema_version") == 1 and summary.get("verification_kind") == "training",
            "invalid Host aggregate version/kind")
    require(summary.get("run_id") == run_id, "Host aggregate run_id mismatch")
    rows = summary.get("cases")
    require(isinstance(rows, list) and rows, "Host aggregate has no case rows")
    require(output_dir == run_dir / "board_expected", "output directory mismatch")
    require(not output_dir.exists() or (output_dir.is_dir() and not any(output_dir.iterdir())),
            "board_expected must be new or empty")

    cases = []
    expected_records = []
    excluded = []
    blocked = summary.get("status") != "PASS"
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get("case_id"), str), "invalid aggregate row")
        cid = row["case_id"]
        record = row.get("summary")
        require(isinstance(record, dict) and isinstance(record.get("path"), str) and
                isinstance(record.get("sha256"), str), f"summary evidence missing: {cid}")
        case_summary_path = relative_inside(root, record["path"])
        require(case_summary_path == run_dir / cid / "train_summary.json",
                f"summary path is not the current run case: {cid}")
        require(record["sha256"] == sha256(case_summary_path), f"summary hash mismatch: {cid}")
        case_summary = load_json(case_summary_path)
        require(case_summary.get("run_id") == run_id and case_summary.get("case_id") == cid,
                f"case summary identity mismatch: {cid}")
        origin = root / "cases" / cid / "case.json"
        require(origin.is_file(), f"original case missing: {origin}")
        origin_digest = sha256(origin)
        require(case_summary.get("case_sha256") == origin_digest,
                f"case summary does not lock original case: {cid}")
        case = load_json(origin)
        require(case.get("case_id") == cid, f"case identity mismatch: {cid}")
        if row.get("kind") != "numerical":
            excluded.append({"case_id": cid, "kind": row.get("kind"),
                             "reason": "reject cases are Host converter-boundary checks"})
            continue
        if row.get("status") != "PASS" or case_summary.get("status") != "PASS":
            blocked = True
            excluded.append({"case_id": cid, "kind": "numerical",
                             "reason": row.get("reason") or "Host numerical case is not PASS"})
            continue
        base = origin.parent
        model_path = check_locked_file(base, case.get("model"), "model")
        golden_path = check_locked_file(base, case.get("golden"), "golden")
        expected = build_expected(root, run_id, case, golden_path, origin_digest,
                                  record["sha256"])
        training_config_path = run_dir / cid / "micro_train.cfg"
        require(training_config_path.is_file(),
                f"training config missing: {training_config_path}")
        expected["training_config"] = evidence(training_config_path, root)
        expected["inputs"] = []
        for section in ("sequence", "eval"):
            samples = case.get(section, [])
            if section == "eval" and isinstance(samples, dict):
                samples = [samples]
            require(isinstance(samples, list), f"invalid {section} section")
            for sample in samples:
                for role in ("inputs", "labels"):
                    for item in sample.get(role, []):
                        path = check_locked_file(base, item, f"{section}.{role}")
                        expected["inputs"].append(evidence(path, root))
        expected_path = output_dir / f"{cid}.json"
        cases.append({
            "case_id": cid,
            "kind": "numerical",
            "test_point": case.get("test_point", ""),
            "model": evidence(model_path, root),
            "golden": evidence(golden_path, root),
            "case": evidence(origin, root),
            "host_summary": evidence(case_summary_path, root),
            "expected": {"path": expected_path.relative_to(root).as_posix()},
            "training": expected["training"],
            "training_config": expected["training_config"],
            "required_parameters": expected["required_parameters"],
        })
        expected_records.append(expected)

    require(cases or blocked, "no numerical case results")
    matrix = {
        "schema_version": 1,
        "verification_kind": "training",
        "run_id": run_id,
        "status": "BLOCKED_HOST_NOT_PASS" if blocked else "PASS",
        "host_summary": {"path": summary_path.relative_to(root).as_posix(),
                         "sha256": sha256(summary_path)},
        "cases": cases,
        "excluded_cases": excluded,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for item, expected in zip(cases, expected_records):
        atomic_new_json(root / item["expected"]["path"], expected)
        item["expected"]["sha256"] = sha256(root / item["expected"]["path"])

    matrix_path = output_dir / "training_board_expected_matrix.json"
    atomic_new_json(matrix_path, matrix)
    return matrix
def export_board_expected(root: Path, run_id: str) -> dict:
    """Export the frozen board matrix after the Host aggregate has been written."""
    return export(root, run_id, root / "runs" / run_id / "train_verify_summary.json",
                  root / "runs" / run_id / "board_expected")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--opdir", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--expected", type=Path, required=True, help="Plan JSON containing a cases array")
    ap.add_argument("--export-board-expected", action="store_true",
                    help="Also export the frozen WS63 training board expectation matrix")
    args = ap.parse_args(argv)
    try:
        root = args.opdir.resolve()
        out = output_path(root, args.run_id)
        # Never replace the caller's plan with the aggregate report.
        require(args.expected.resolve() != out, "expected plan aliases output report")
        report = {"schema_version": 1, "verification_kind": "training", "run_id": args.run_id,
                  "status": "FAIL", "cases": []}
        try:
            expected = load_plan(args.expected)
            rows = [aggregate_case(root, args.run_id, item) for item in expected]
            numerical = [r for r in rows if r["kind"] == "numerical"]
            passed = numerical and all(r["status"] == "PASS" for r in numerical) and all(
                r["status"] == ("PASS" if r["kind"] == "numerical" else "PASS_EXPECTED_ERROR")
                for r in rows)
            report.update(cases=rows, status="PASS" if passed else (
                "FAIL" if any(r["status"] == "FAIL" for r in rows) else "NOT_RUN"))
        except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
            report["errors"] = [str(exc)]
        write_report(out, report)
        board_matrix = None
        if args.export_board_expected:
            try:
                board_matrix = export_board_expected(root, args.run_id)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                report.setdefault("errors", []).append(f"board expected export failed: {exc}")
                report["status"] = "FAIL"
                write_report(out, report)
        result = {"status": report["status"], "path": out.as_posix(),
                  "cases": len(report["cases"])}
        if board_matrix is not None:
            result["board_expected"] = {"status": board_matrix["status"],
                                        "path": (root / "runs" / args.run_id / "board_expected/training_board_expected_matrix.json").as_posix()}
        print(json.dumps(result, ensure_ascii=False))
        return 0 if report["status"] == "PASS" and (
            board_matrix is None or board_matrix["status"] == "PASS") else 2
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
