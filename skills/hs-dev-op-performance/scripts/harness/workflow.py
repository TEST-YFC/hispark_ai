"""Current-repository performance run preparation, evidence binding, and archival."""

import hashlib
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from .evidence import (
    load_metric,
    validate_board_log,
    validate_build_log,
    validate_flash_log,
    validate_host_summary,
    validate_serial_log,
)


FORMAT_VERSION = 1
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
EVIDENCE_NAMES = {
    "host": "host_summary.txt",
    "build": "firmware_build.log",
    "flash": "flash.log",
    "board": "board_accuracy.log",
    "metric": "onboard_metric.json",
    "serial": "serial_raw.log",
}


class WorkflowError(RuntimeError):
    """Raised when a performance workflow transition is invalid."""


def _safe_name(value, field):
    if not isinstance(value, str) or not SAFE_NAME.fullmatch(value):
        raise WorkflowError(f"invalid {field}: {value!r}")
    return value


def _now():
    return datetime.now().astimezone()


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_sha256(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise WorkflowError(f"directory not found: {root}")
    digest = hashlib.sha256()
    files = sorted(
        path for path in root.rglob("*")
        if path.is_file() and not any(part in {"build", "__pycache__", ".git"} for part in path.parts)
    )
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _copy_file(source, destination):
    source = Path(source).resolve()
    destination = Path(destination)
    if not source.is_file():
        raise WorkflowError(f"file not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source == destination.resolve():
        return destination
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return destination


def _git(source_root, *args, check=True):
    proc = subprocess.run(
        ["git", *args], cwd=source_root, capture_output=True, text=True, check=False
    )
    if check and proc.returncode != 0:
        raise WorkflowError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc


def _git_head(source_root):
    return _git(source_root, "rev-parse", "HEAD").stdout.strip()


def _require_git_root(path, label):
    path = Path(path).resolve()
    top = Path(_git(path, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if path != top:
        raise WorkflowError(f"{label} must be the git checkout root: {top}")
    return path


def _dirty_paths(source_root):
    tracked = _git(source_root, "diff", "HEAD", "--name-only", "--").stdout.splitlines()
    untracked = _git(
        source_root, "ls-files", "--others", "--exclude-standard"
    ).stdout.splitlines()
    return sorted({value.strip() for value in [*tracked, *untracked] if value.strip()})


def _path_hashes(source_root, relative_paths):
    result = {}
    for relative in relative_paths:
        path = Path(source_root) / relative
        result[relative] = _sha256(path) if path.is_file() else None
    return result


def _normalize_allowed(values):
    normalized = []
    for value in values:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise WorkflowError(f"allowed change must be a safe relative path: {value!r}")
        normalized.append(path.as_posix().rstrip("/"))
    return sorted(set(normalized))


def _within_allowed(relative, allowed):
    path = Path(relative)
    return any(path == Path(root) or Path(root) in path.parents for root in allowed)


def _repo_root(value):
    root = Path(value).expanduser().resolve()
    required = (
        root / "README.md",
        root / "skills" / "hs-dev-op-performance" / "SKILL.md",
        root / "src",
    )
    if not all(path.exists() for path in required):
        raise WorkflowError(f"not a HiSpark.AI repository root: {root}")
    return root


def _source_root(repo_root, value):
    root = (
        Path(value).expanduser().resolve()
        if value
        else repo_root / "src" / "mindspore-lite"
    )
    if not root.is_dir():
        raise WorkflowError(f"MindSpore Lite source root not found: {root}")
    return _require_git_root(root, "MindSpore Lite source")


def _case_root(repo_root, operator, target, framework, case):
    return (
        repo_root
        / "src"
        / "mslite-op-output"
        / operator
        / "performance"
        / target
        / framework
        / case
    )


def _baseline_path(case_root):
    return case_root / "experiments" / "baseline" / "result.json"


def _load_json(path, label):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"cannot load {label} {path}: {exc}") from exc


def prepare_run(
    *, repo_root, operator, case, framework, mode, target, task_type,
    source_root=None, variable="", note="", change_kind="nnacl",
    allowed_changes=(), ticks_per_us=24.0, window=50, stable_tolerance=0.05,
    timeout_seconds=110.0,
):
    """Create one immutable run identity before source changes or evidence collection."""
    for field, value in (
        ("operator", operator), ("case", case), ("framework", framework),
        ("mode", mode), ("target", target),
    ):
        _safe_name(value, field)
    if framework not in ("onnx", "tflite") or mode not in ("fp32", "int8"):
        raise WorkflowError("unsupported framework or mode")
    if task_type not in ("baseline", "optimization"):
        raise WorkflowError(f"invalid task_type: {task_type}")
    if change_kind not in ("nnacl", "generated-code"):
        raise WorkflowError(f"invalid change_kind: {change_kind}")
    if ticks_per_us <= 0 or window < 2 or not 0 <= stable_tolerance < 1 or timeout_seconds <= 0:
        raise WorkflowError("invalid measurement protocol")
    if task_type == "optimization":
        _safe_name(variable, "variable")
        if not note.strip():
            raise WorkflowError("optimization requires a non-empty note")
    elif variable or note:
        raise WorkflowError("baseline does not accept variable or note")

    repo_root = _repo_root(repo_root)
    source_root = _source_root(repo_root, source_root)
    allowed = _normalize_allowed(allowed_changes)
    if task_type == "optimization" and change_kind == "nnacl" and not allowed:
        raise WorkflowError("NNACL optimization requires at least one --allowed-change")
    if _dirty_paths(source_root):
        raise WorkflowError("each run must start from a clean source checkout")

    case_root = _case_root(repo_root, operator, target, framework, case)
    baseline_path = _baseline_path(case_root)
    baseline = None
    source_commit = _git_head(source_root)
    if task_type == "baseline":
        if baseline_path.exists():
            raise WorkflowError("an archived baseline already exists")
    else:
        baseline = _load_json(baseline_path, "baseline")
        if baseline.get("status") != "BASELINE":
            raise WorkflowError("optimization requires a passing baseline")
        if baseline.get("source", {}).get("commit") != source_commit:
            raise WorkflowError("source commit differs from the archived baseline")

    execution_id = f"{_now():%Y%m%dT%H%M%S%f}_{secrets.token_hex(4)}"
    run_dir = case_root / "runs" / execution_id
    run_dir.mkdir(parents=True)
    protocol = {
        "ticks_per_us": float(ticks_per_us),
        "window": int(window),
        "stable_tolerance": float(stable_tolerance),
        "timeout_seconds": float(timeout_seconds),
    }
    manifest = {
        "format_version": FORMAT_VERSION,
        "execution_id": execution_id,
        "created_at": _now().isoformat(),
        "status": "PENDING",
        "repo_root": str(repo_root),
        "source_root": str(source_root),
        "identity": {
            "operator": operator,
            "case": case,
            "framework": framework,
            "mode": mode,
            "target": target,
        },
        "task_type": task_type,
        "variable": variable or None,
        "note": note,
        "change_kind": change_kind,
        "source": {"commit": source_commit, "allowed_changes": allowed},
        "protocol": protocol,
        "bindings": {},
    }
    manifest_path = run_dir / "manifest.json"
    _atomic_json(manifest_path, manifest)
    return manifest_path, manifest


def _load_manifest(path, require_pending=True):
    path = Path(path).expanduser().resolve()
    manifest = _load_json(path, "run manifest")
    if manifest.get("format_version") != FORMAT_VERSION:
        raise WorkflowError("unsupported run manifest format")
    execution_id = _safe_name(manifest.get("execution_id"), "execution_id")
    identity = manifest.get("identity") or {}
    for field in ("operator", "case", "framework", "mode", "target"):
        _safe_name(identity.get(field), field)
    repo_root = _repo_root(manifest.get("repo_root"))
    expected = (
        _case_root(repo_root, identity["operator"], identity["target"], identity["framework"], identity["case"])
        / "runs" / execution_id / "manifest.json"
    ).resolve()
    if path != expected:
        raise WorkflowError("run manifest is outside its canonical HiSpark.AI case directory")
    if require_pending and manifest.get("status") != "PENDING":
        raise WorkflowError(f"run is not pending: {manifest.get('status')}")
    return path, manifest


def bind_evidence(manifest_path, kind, source):
    """Bind an immutable file hash to this run and copy it to the canonical run directory."""
    if kind not in EVIDENCE_NAMES:
        raise WorkflowError(f"invalid evidence kind: {kind}")
    manifest_path, manifest = _load_manifest(manifest_path)
    destination = manifest_path.parent / "evidence" / EVIDENCE_NAMES[kind]
    _copy_file(source, destination)
    manifest["bindings"][kind] = {
        "file": destination.relative_to(manifest_path.parent).as_posix(),
        "sha256": _sha256(destination),
        "bound_at": _now().isoformat(),
        "source_name": Path(source).name,
    }
    _atomic_json(manifest_path, manifest)
    return destination


def _bound_files(manifest_path, manifest):
    missing = [kind for kind in EVIDENCE_NAMES if kind not in manifest["bindings"]]
    if missing:
        raise WorkflowError(f"missing evidence bindings: {', '.join(missing)}")
    files = {}
    for kind, binding in manifest["bindings"].items():
        relative = Path(binding["file"])
        if relative.is_absolute() or ".." in relative.parts:
            raise WorkflowError(f"unsafe evidence binding: {binding['file']}")
        path = (manifest_path.parent / relative).resolve()
        if manifest_path.parent.resolve() not in path.parents or not path.is_file():
            raise WorkflowError(f"bound evidence is missing or escaped: {path}")
        if _sha256(path) != binding.get("sha256"):
            raise WorkflowError(f"bound evidence changed after binding: {kind}")
        files[kind] = path
    return files


def _validate_source_for_record(manifest):
    source_root = Path(manifest["source_root"])
    if _git_head(source_root) != manifest["source"]["commit"]:
        raise WorkflowError("source HEAD changed after run preparation")
    dirty = _dirty_paths(source_root)
    if manifest["task_type"] == "baseline" or manifest["change_kind"] == "generated-code":
        if dirty:
            raise WorkflowError("this run requires a clean MindSpore Lite source checkout")
    else:
        if not dirty:
            raise WorkflowError("NNACL optimization did not change any source file")
        unexpected = [
            value for value in dirty
            if not _within_allowed(value, manifest["source"]["allowed_changes"])
        ]
        if unexpected:
            raise WorkflowError(f"source changes exceed allowed paths: {unexpected}")
    return dirty


def _capture_patch(source_root, allowed, dirty_paths, destination):
    args = ["diff", "HEAD", "--"]
    args.extend(allowed)
    patch = _git(source_root, *args).stdout if allowed else ""
    untracked = set(
        _git(source_root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    )
    for relative in dirty_paths:
        if relative not in untracked:
            continue
        proc = _git(
            source_root, "diff", "--no-index", "--", "/dev/null", relative, check=False
        )
        if proc.returncode not in (0, 1):
            raise WorkflowError(f"cannot capture untracked source diff: {relative}")
        patch += proc.stdout
    Path(destination).write_text(
        patch or "# source tree unchanged; see snapshot hash for generated-code runs\n",
        encoding="utf-8",
    )


def _git_provenance(path, label, exclude_prefixes=()):
    path = Path(path).expanduser().resolve()
    if not path.is_dir():
        raise WorkflowError(f"{label} repository not found: {path}")
    path = _require_git_root(path, label)
    dirty = [
        value for value in _dirty_paths(path)
        if not any(value == prefix.rstrip("/") or value.startswith(prefix) for prefix in exclude_prefixes)
    ]
    return {
        "path": str(path),
        "commit": _git_head(path),
        "dirty_paths": dirty,
    }


def archive_success(
    *, manifest_path, firmware, codes_dir, cpu_archive, riscv_archive, sdk_root,
):
    """Validate and atomically archive one prepared run."""
    manifest_path, manifest = _load_manifest(manifest_path)
    identity = manifest["identity"]
    evidence_files = _bound_files(manifest_path, manifest)
    dirty = _validate_source_for_record(manifest)
    host = validate_host_summary(
        evidence_files["host"], identity["operator"], identity["framework"], identity["mode"]
    )
    build = validate_build_log(evidence_files["build"], manifest["execution_id"])
    flash = validate_flash_log(evidence_files["flash"], manifest["execution_id"])
    board = validate_board_log(evidence_files["board"], manifest["execution_id"])
    metric, metric_value = load_metric(
        evidence_files["metric"], manifest["execution_id"], manifest["protocol"]
    )
    serial = validate_serial_log(evidence_files["serial"], metric)

    firmware = Path(firmware).expanduser().resolve()
    codes_dir = Path(codes_dir).expanduser().resolve()
    cpu_archive = Path(cpu_archive).expanduser().resolve()
    riscv_archive = Path(riscv_archive).expanduser().resolve()
    for label, path in (
        ("firmware", firmware), ("CPU archive", cpu_archive), ("RISC-V archive", riscv_archive)
    ):
        if not path.is_file():
            raise WorkflowError(f"{label} not found: {path}")
    firmware_sha256 = _sha256(firmware)
    evidence_firmware_hashes = {
        build["firmware_sha256"], flash["firmware_sha256"], board["firmware_sha256"]
    }
    if evidence_firmware_hashes != {firmware_sha256}:
        raise WorkflowError("build, flash, board and archived firmware hashes differ")
    cpu_sha256 = _sha256(cpu_archive)
    riscv_sha256 = _sha256(riscv_archive)
    if cpu_sha256 == riscv_sha256:
        raise WorkflowError("CPU and RISC-V archives must be distinct build artifacts")
    codes_sha256 = _tree_sha256(codes_dir)

    repo_root = Path(manifest["repo_root"])
    case_root = _case_root(
        repo_root, identity["operator"], identity["target"], identity["framework"], identity["case"]
    )
    experiments = case_root / "experiments"
    baseline = None
    if manifest["task_type"] == "optimization":
        baseline = _load_json(_baseline_path(case_root), "baseline")
        if baseline["source"]["commit"] != manifest["source"]["commit"]:
            raise WorkflowError("baseline source commit changed")
        if baseline["protocol"] != manifest["protocol"]:
            raise WorkflowError("measurement protocol differs from baseline")
        if manifest["change_kind"] == "generated-code" and baseline["artifacts"]["codes_sha256"] == codes_sha256:
            raise WorkflowError("generated-code optimization did not change the code snapshot")

    run_name = "baseline" if manifest["task_type"] == "baseline" else manifest["execution_id"]
    destination = experiments / run_name
    if destination.exists():
        raise WorkflowError(f"experiment already exists: {destination}")
    experiments.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{run_name}.", dir=experiments))
    try:
        shutil.copytree(manifest_path.parent / "evidence", temporary / "evidence")
        shutil.copytree(
            codes_dir, temporary / "snapshot",
            ignore=shutil.ignore_patterns("build", "__pycache__", ".git"),
        )
        artifacts_dir = temporary / "artifacts"
        artifacts_dir.mkdir()
        copied = {
            "firmware": _copy_file(firmware, artifacts_dir / firmware.name),
            "cpu_nnacl": _copy_file(cpu_archive, artifacts_dir / "cpu_libnnacl.a"),
            "riscv_nnacl": _copy_file(riscv_archive, artifacts_dir / "riscv_libnnacl.a"),
        }
        _capture_patch(
            Path(manifest["source_root"]), manifest["source"]["allowed_changes"],
            dirty, temporary / "patch.diff"
        )
        baseline_value = baseline["performance"]["value"] if baseline else None
        speedup_raw = baseline_value / metric_value if baseline_value else None
        accepted = baseline is None or metric_value < baseline_value
        status = "BASELINE" if baseline is None else ("ACCEPTED" if accepted else "REJECTED")
        evidence = {
            "host": host,
            "firmware": build,
            "flash": flash,
            "board_accuracy": board,
            "metric": metric,
            "serial": serial,
            "sha256": {kind: _sha256(path) for kind, path in evidence_files.items()},
        }
        result = {
            "format_version": FORMAT_VERSION,
            "execution_id": manifest["execution_id"],
            "timestamp": _now().isoformat(),
            "status": status,
            "identity": identity,
            "task_type": manifest["task_type"],
            "variable": manifest["variable"],
            "note": manifest["note"],
            "change_kind": manifest["change_kind"],
            "source": {
                "commit": manifest["source"]["commit"],
                "dirty_paths": dirty,
                "file_sha256": _path_hashes(manifest["source_root"], dirty),
                "allowed_changes": manifest["source"]["allowed_changes"],
            },
            "protocol": manifest["protocol"],
            "performance": {
                "name": "latency",
                "value": metric_value,
                "unit": "us",
                "baseline_value": baseline_value,
                "speedup": round(speedup_raw, 6) if speedup_raw is not None else None,
            },
            "evidence": evidence,
            "provenance": {
                "hispark": _git_provenance(
                    repo_root, "HiSpark.AI", exclude_prefixes=("src/mslite-op-output/",)
                ),
                "mindspore_lite": _git_provenance(manifest["source_root"], "MindSpore Lite"),
                "sdk": _git_provenance(sdk_root, "target SDK"),
            },
            "artifacts": {
                "codes_sha256": codes_sha256,
                "firmware_sha256": _sha256(copied["firmware"]),
                "cpu_nnacl_sha256": _sha256(copied["cpu_nnacl"]),
                "riscv_nnacl_sha256": _sha256(copied["riscv_nnacl"]),
                "patch_sha256": _sha256(temporary / "patch.diff"),
            },
        }
        _atomic_json(temporary / "result.json", result)
        (temporary / "report.md").write_text(_render_report(result), encoding="utf-8")
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    manifest["status"] = "ARCHIVED"
    manifest["experiment"] = str(destination)
    _atomic_json(manifest_path, manifest)
    return destination


def _render_report(result):
    perf = result["performance"]
    lines = [
        f"# {result['execution_id']}", "", f"- status: {result['status']}",
        f"- operator: {result['identity']['operator']}",
        f"- case: {result['identity']['case']}",
        f"- source commit: {result['source']['commit']}",
        f"- latency: {perf['value']:.6f} us",
    ]
    if perf["baseline_value"] is not None:
        lines.extend([
            f"- baseline: {perf['baseline_value']:.6f} us",
            f"- speedup: {perf['speedup']:.6f}x",
        ])
    lines.extend(["", "All Host, firmware, flash, board-accuracy and metric evidence passed.", ""])
    return "\n".join(lines)


def archive_failure(*, manifest_path, stage, detail, log=None):
    """Archive a terminal failure without accepting new path components from the CLI."""
    _safe_name(stage, "stage")
    if not str(detail).strip():
        raise WorkflowError("failure detail must be non-empty")
    manifest_path, manifest = _load_manifest(manifest_path)
    identity = manifest["identity"]
    case_root = _case_root(
        Path(manifest["repo_root"]), identity["operator"], identity["target"],
        identity["framework"], identity["case"],
    )
    experiments = case_root / "experiments"
    destination = experiments / f"{manifest['execution_id']}_failed"
    if destination.exists():
        raise WorkflowError(f"experiment already exists: {destination}")
    experiments.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{manifest['execution_id']}.", dir=experiments))
    try:
        result = {
            "format_version": FORMAT_VERSION,
            "execution_id": manifest["execution_id"],
            "timestamp": _now().isoformat(),
            "status": "FAIL",
            "identity": identity,
            "task_type": manifest["task_type"],
            "variable": manifest["variable"],
            "failed_stage": stage,
            "detail": detail,
            "source": manifest["source"],
            "protocol": manifest["protocol"],
        }
        _atomic_json(temporary / "result.json", result)
        (temporary / "report.md").write_text(
            f"# {manifest['execution_id']}\n\n- status: FAIL\n- stage: {stage}\n- detail: {detail}\n",
            encoding="utf-8",
        )
        if log:
            _copy_file(log, temporary / "failure.log")
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    manifest["status"] = "FAILED"
    manifest["experiment"] = str(destination)
    _atomic_json(manifest_path, manifest)
    return destination


def summarize(*, repo_root, operator, case, framework, target):
    for field, value in (
        ("operator", operator), ("case", case), ("framework", framework), ("target", target)
    ):
        _safe_name(value, field)
    repo_root = _repo_root(repo_root)
    experiments = _case_root(repo_root, operator, target, framework, case) / "experiments"
    baseline_path = experiments / "baseline" / "result.json"
    baseline = _load_json(baseline_path, "baseline")
    records = []
    for path in sorted(experiments.glob("*/result.json")):
        record = _load_json(path, "experiment")
        records.append(record)
    candidates = [
        item for item in records
        if item.get("status") == "ACCEPTED"
        and isinstance(item.get("performance", {}).get("value"), (int, float))
        and not isinstance(item["performance"]["value"], bool)
        and math.isfinite(float(item["performance"]["value"]))
    ]
    best = min(candidates, key=lambda item: item["performance"]["value"], default=None)
    summary = {
        "format_version": FORMAT_VERSION,
        "baseline_execution_id": baseline.get("execution_id"),
        "total_records": len(records),
        "optimization_records": sum(item.get("task_type") == "optimization" for item in records),
        "best_execution_id": best.get("execution_id") if best else None,
        "best_variable": best.get("variable") if best else None,
        "records": records,
    }
    _atomic_json(experiments / "summary.json", summary)
    return summary
