#!/usr/bin/env python3
"""Finalize a completed training workflow without rerunning business commands."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import tempfile

# Share exactly the Host path identity policy; do not maintain another mapper.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hs-verify-op-host/scripts/training"))
try:
    from aggregate_training_results import resolve_evidence_path
finally:
    sys.path.pop(0)

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from check_board_reference import ATOL, RTOL, check_expected_against_golden
finally:
    sys.path.pop(0)

ORDER = [
    "design", "implementation", "build", "model", "host", "aggregate",
    "board", "final",
]

BOARD_MATRIX_ROOT_KEYS = {
    "schema_version", "verification_kind", "run_id", "status", "cases"
}
BOARD_MATRIX_ROW_KEYS = {"case_id", "status", "report"}
BOARD_MATRIX_REPORT_KEYS = {"path", "sha256"}


class IntegrityError(ValueError):
    """A persisted identity, path, or hash is inconsistent."""


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def confined(root: Path, value: Path | str) -> Path:
    raw = str(value)
    if not Path(raw).anchor and not PureWindowsPath(raw).drive:
        # Keep relative-path compatibility; absolute aliases use the shared resolver.
        base = root.resolve()
        path = (base / raw).resolve()
        if not path.is_relative_to(base):
            raise IntegrityError(f"path outside opdir: {raw}")
        return path
    try:
        return resolve_evidence_path(raw, root)
    except ValueError as exc:
        raise IntegrityError(f"path outside opdir or invalid evidence path: {value}: {exc}") from exc


def set_gate(gates: dict, name: str, status: str, reason: str, **extra) -> None:
    gates[name] = {"status": status, "reason": reason, **extra}


def run_audit(args, root: Path) -> dict:
    audit_script = args.audit_script.resolve()
    facts = confined(root, args.facts)
    design = confined(root, args.design)
    verify = confined(root, args.verify)
    command = [
        sys.executable,
        str(audit_script),
        "--opdir", str(root),
        "--facts", str(facts),
        "--design", str(design),
        "--verify", str(verify),
        "--publication", "final",
    ]
    result = subprocess.run(
        command,
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )
    issues = []
    markers = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            markers[key] = value.strip()
        if line.startswith("TRAIN_MANUAL_ISSUES="):
            try:
                issues = json.loads(line.split("=", 1)[1])
            except json.JSONDecodeError:
                issues = [line]
    if result.returncode != 0 and not issues:
        issues = [result.stderr.strip() or "audit returned non-zero"]
    valid = result.returncode == 0 and all(markers.get(key) == "PASS" for key in (
        "TRAIN_MANUAL_STATUS", "TRAIN_MANUAL_FACTS_SYNC",
        "TRAIN_MANUAL_CONTENT_SYNC", "TRAIN_MANUAL_CASE_SYNC"))
    return {
        "status": "PASS" if valid else "FAIL",
        "returncode": result.returncode,
        "issues": issues,
    }


audit = run_audit


def rows_equal(saved: dict, fresh: dict) -> bool:
    keys = (
        "case_id", "test_point", "kind", "status", "reason", "summary",
        "graph_gate",
    )
    return all(saved.get(key) == fresh.get(key) for key in keys)


def check_summary(summary: dict, run_dir: Path) -> tuple[str, dict]:
    run_id = summary.get("run_id")
    if run_id != run_dir.name:
        raise IntegrityError("summary run_id does not match run directory")
    if summary.get("verification_kind") != "training":
        raise IntegrityError("summary verification_kind is not training")
    if summary.get("status") not in {"COMMANDS_COMPLETED", "FAIL"}:
        raise ValueError("workflow summary is not terminal")

    stages = summary.get("stages")
    if not isinstance(stages, list) or any(not isinstance(item, dict) for item in stages):
        raise ValueError("workflow summary stages are missing or malformed")
    names = [item.get("stage") for item in stages]
    if names != ORDER or len(set(names)) != len(ORDER):
        raise IntegrityError("workflow stages are not unique and ordered")

    board = stages[-2]
    board_skip = (
        board.get("policy_skip") is True
        and board.get("status") in {"NOT_RUN", "NOT_REQUESTED"}
        and isinstance(board.get("reason"), str)
        and bool(board["reason"].strip())
    )
    incomplete = []
    failed = summary.get("status") == "FAIL" or summary.get("command_status") == "FAIL"
    for item in stages:
        status = item.get("status")
        if item is board and board_skip:
            if item.get("argv") or "returncode" in item or "exit_code" in item:
                raise IntegrityError("skipped board carries execution evidence")
            continue
        if status == "NOT_RUN" and failed:
            continue  # scheduler blocks later stages after an actual failure
        if status not in {"PASS", "FAIL"}:
            raise IntegrityError(f"stage {item.get('stage')} has invalid status")
        failed = failed or status == "FAIL"
        argv = item.get("argv")
        if not isinstance(argv, list) or not argv or not argv[0] or any(not isinstance(x, str) for x in argv):
            incomplete.append("command missing")
        # Scheduler stores returncode; Host runner's exit_code is not its alias.
        rc = item.get("returncode")
        if "returncode" not in item:
            incomplete.append("returncode missing")
        elif type(rc) is not int or (rc == 0) != (status == "PASS"):
            raise IntegrityError(f"stage {item.get('stage')} status/returncode mismatch")
        if "exit_code" in item and (type(item["exit_code"]) is not int or item["exit_code"] != rc):
            raise IntegrityError("conflicting exit_code and scheduler returncode")
        if item.get("timed_out") and status == "PASS":
            raise IntegrityError("timed out stage cannot PASS")
        log = item.get("log")
        if not isinstance(log, str) or not log:
            incomplete.append("log missing")
            continue
        log_path = confined(run_dir, log)
        if not log_path.is_file():
            incomplete.append("log missing")
            continue
        recorded_hash = item.get("log_sha256")
        if recorded_hash is not None and sha256(log_path) != recorded_hash:
            raise IntegrityError("scheduler log hash mismatch")
    if failed:
        return run_id, {"status": "FAIL", "reason": "scheduler reports failure"}
    if summary.get("command_status") != "PASS":
        raise IntegrityError("terminal summary command_status mismatch")
    if incomplete:
        return run_id, {"status": "NOT_VERIFIED", "reason": "; ".join(sorted(set(incomplete)))}
    return run_id, {"status": "PASS", "reason": "scheduler commands and logs checked; business evidence checked separately"}


def check_host_aggregate(root: Path, run_id: str, run_dir: Path, expected_cases=None) -> tuple[str, dict]:
    path = run_dir / "train_verify_summary.json"
    if not path.is_file():
        return "NOT_VERIFIED", {"reason": "Host aggregate is missing"}
    aggregate = load_json(path)
    if aggregate.get("run_id") != run_id:
        raise IntegrityError("aggregate run_id mismatch")
    if aggregate.get("verification_kind") != "training":
        raise IntegrityError("aggregate verification_kind mismatch")
    if aggregate.get("status") == "FAIL":
        return "FAIL", {"reason": "aggregate explicitly reports FAIL"}
    cases = aggregate.get("cases")
    if not isinstance(cases, list) or not cases:
        return "NOT_VERIFIED", {"reason": "aggregate cases are missing"}

    ids = case_ids(cases)
    if expected_cases is not None and ids != case_ids(expected_cases):
        raise IntegrityError("aggregate expected case coverage/order mismatch")

    aggregate_dir = Path(__file__).parents[2] / "hs-verify-op-host" / "scripts" / "training"
    sys.path.insert(0, str(aggregate_dir))
    try:
        from aggregate_training_results import aggregate_case
        fresh = [aggregate_case(root, run_id, item) for item in cases]
    finally:
        sys.path.pop(0)

    if any(not rows_equal(saved, current) for saved, current in zip(cases, fresh)):
        raise IntegrityError("aggregate differs from current case or graph evidence")
    if aggregate.get("status") != "PASS":
        return "NOT_VERIFIED", {"reason": "aggregate is not PASS", "cases": fresh}
    if not any(c.get("kind") == "numerical" for c in fresh) or any(
        c.get("status") != ("PASS" if c.get("kind") == "numerical" else "PASS_EXPECTED_ERROR") for c in fresh
    ):
        raise IntegrityError("aggregate PASS contradicts current case results")
    return "PASS", {"reason": "aggregate and every case were rechecked", "cases": fresh}


def check_facts_checks(facts: dict) -> tuple[str, dict]:
    checks = facts.get("checks")
    if not isinstance(checks, dict):
        return "NOT_VERIFIED", {"reason": "facts checks are missing"}
    required = checks.get("required")
    observed = checks.get("observed")
    if not isinstance(required, list) or not isinstance(observed, list):
        return "NOT_VERIFIED", {"reason": "facts checks.required/observed are missing"}
    observed_by_name = {
        item.get("name"): item for item in observed if isinstance(item, dict)
    }
    missing = [
        name for name in required
        if observed_by_name.get(name, {}).get("status") != "PASS"
    ]
    if missing:
        return "NOT_VERIFIED", {
            "reason": "required structural checks are incomplete",
            "missing": missing,
        }
    return "PASS", {"reason": "required structural checks are PASS"}


def case_ids(cases):
    if not isinstance(cases, list) or not cases:
        raise IntegrityError("expected cases missing")
    ids = [c.get("case_id") if isinstance(c, dict) else None for c in cases]
    if any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
        raise IntegrityError("missing or duplicate case identity")
    return ids


def checked_record(root, item):
    if not isinstance(item, dict) or not isinstance(item.get("path"), str):
        raise IntegrityError("invalid evidence reference")
    path = confined(root, item["path"])
    if not path.is_file() or sha256(path) != item.get("sha256"):
        raise IntegrityError("evidence missing or hash-mismatched")
    return path


def check_board_case_identity(root, facts, report):
    """Bind board identity to the source case/model actually used by Host."""
    case_id = report.get("case_id")
    expected = next((c for c in facts["expected_cases"] if c["case_id"] == case_id), None)
    if expected is None or expected.get("kind") != "numerical":
        raise IntegrityError("board case is not an expected numerical case")
    case_path = confined(root, f"cases/{case_id}/case.json")
    records = [r for r in facts.get("sources", [])
               if confined(root, r["path"]) == case_path]
    if len(records) != 1:
        raise IntegrityError("board case needs one locked case source")
    locked = load_json(checked_record(root, records[0]))
    if locked.get("verification_kind") != "training" or any(
        locked.get(k) != expected.get(k) for k in ("case_id", "kind", "test_point")
    ):
        raise IntegrityError("board locked case identity mismatch")
    # Match runner.resolve_file: model.path is relative to the ORIGINAL case
    # directory, not the archived runs/<run>/<case>/case.json copy.
    model = locked.get("model")
    if not isinstance(model, dict) or not isinstance(model.get("path"), str) or Path(model["path"]).is_absolute():
        raise IntegrityError("board locked case model reference is invalid")
    model_path = checked_record(case_path.parent, model)
    if report.get("model_sha256") != sha256(model_path):
        raise IntegrityError("board model identity differs from locked case")
    host_path = confined(root, f"runs/{facts['run_id']}/{case_id}/train_summary.json")
    host = load_json(host_path)
    if (host.get("case_sha256") != records[0]["sha256"]
            or host.get("case_id") != case_id or host.get("run_id") != facts["run_id"]
            or host.get("status") != "PASS" or host.get("numerical_pass") is not True):
        raise IntegrityError("board locked case differs from Host PASS case")
    return case_path, locked


def replay_board_report(root, facts, report):
    """Replay archived raw tensors only. No hardware, capture, training or flash."""
    if report.get("verification_kind") != "training" or report.get("run_id") != facts["run_id"]:
        raise IntegrityError("board report identity/run mismatch")
    if report.get("status") != "PASS" or report.get("verified") is False:
        raise IntegrityError("board report is not verified PASS")
    case_path, locked = check_board_case_identity(root, facts, report)
    sources = facts.get("sources", [])

    def by_hash(key):
        digest = report.get(key)
        matches = [x for x in sources if digest and x.get("sha256") == digest]
        if not matches:
            raise ValueError(f"board replay input missing: {key}")
        return checked_record(root, matches[0])

    expected = by_hash("expected_sha256")
    try:
        reference = check_expected_against_golden(case_path, locked, load_json(expected), report)
    except FileNotFoundError:
        raise  # Missing golden is NOT_VERIFIED, not a fabricated comparison PASS.
    except ValueError as exc:
        raise IntegrityError(f"board reference contradicts locked golden: {exc}") from exc
    raw = checked_record(root, {"path": report.get("raw_log"), "sha256": report.get("raw_log_sha256")})
    observed = by_hash("observed_sha256") if report.get("observed_sha256") else None
    comparator = Path(__file__).resolve().parents[2] / "hs-verify-op-board/scripts/training/compare_training_board.py"
    with tempfile.TemporaryDirectory(prefix="training-board-replay-") as tmp:
        output = Path(tmp) / "compare.json"
        command = [sys.executable, str(comparator), "--expected", str(expected),
                   "--raw-log", str(raw), "--output", str(output),
                   "--atol", str(ATOL), "--rtol", str(RTOL)]
        if observed:
            command += ["--observed", str(observed)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not output.is_file():
            raise IntegrityError("archived board raw comparison failed")
        fresh = load_json(output)
    # Raw and collector paths may have been relocated within opdir. Their hashes
    # and every semantic field still have to agree exactly.
    for key, value in fresh.items():
        if key not in ("raw_log", "observed") and report.get(key) != value:
            raise IntegrityError(f"board report differs from replay: {key}")
    if fresh.get("status") != "PASS" or fresh.get("parameters_observed") is not True:
        raise IntegrityError("board parameter evidence did not pass")
    return {**fresh, "reference_binding": reference}


def check_board(root: Path, facts: dict, board_stage: dict, policy: str) -> tuple[str, dict]:
    status = board_stage.get("status")
    board_status = facts.get("board_status")
    data = {"board_verified": False, "board_status": board_status, "policy": policy}
    if status == "FAIL" or board_status == "FAIL":
        return "FAIL", {**data, "reason": "board explicitly failed"}
    if board_stage.get("policy_skip") is True:
        if status not in {"NOT_RUN", "NOT_REQUESTED"}:
            raise IntegrityError("board policy_skip conflicts with status")
        if board_status is not None and board_status != status:
            raise IntegrityError("board skip conflicts with facts")
        if facts.get("board_evidence"):
            raise IntegrityError("skipped board carries board evidence")
        reasons = (board_stage.get("reason"), facts.get("board_reason"))
        if board_status is None or any(not isinstance(x, str) or not x.strip() for x in reasons):
            return "NOT_VERIFIED", {**data, "reason": "board skip needs aligned facts and reasons"}
        return ("PASS" if policy == "HOST_ONLY" else "NOT_VERIFIED"), {
            **data, "reason": "explicit board skip; no board verification", "policy_skip": True}
    if status != "PASS" or board_status != "PASS":
        return "NOT_VERIFIED", {**data, "reason": "board command cannot substitute for board evidence"}
    evidence = facts.get("board_evidence")
    if isinstance(evidence, str):  # existing manual facts schema uses a sources path
        evidence = next((x for x in facts.get("sources", []) if x.get("path") == evidence), None)
    if not evidence:
        return "NOT_VERIFIED", {**data, "reason": "board evidence missing"}
    path = checked_record(root, evidence)
    report = load_json(path)
    if report.get("status") != "PASS" or report.get("run_id") != facts.get("run_id") or report.get("verification_kind") != "training":
        raise IntegrityError("board report status/run/type mismatch")
    case_ids(facts.get("expected_cases"))
    expected = [c for c in facts["expected_cases"] if c.get("kind") == "numerical"]
    expected_ids = case_ids(expected)
    # Never filter failed/missing Host cases out of the required board matrix.
    if facts.get("host_status") != "PASS" or any(c.get("status") != "PASS" for c in expected):
        raise IntegrityError("board PASS requires every expected numerical Host case PASS")
    host_status, host_data = check_host_aggregate(
        root, facts["run_id"], confined(root, f"runs/{facts['run_id']}"), facts["expected_cases"])
    if host_status != "PASS":
        return host_status, {**data, "reason": host_data["reason"]}
    if "cases" in report:
        if set(report) != BOARD_MATRIX_ROOT_KEYS:
            raise IntegrityError("board matrix root fields mismatch")
        if type(report.get("schema_version")) is not int or report["schema_version"] != 1:
            raise IntegrityError("board matrix schema_version must be 1")
        rows = report["cases"]
        ids = case_ids(rows)
        if set(ids) != set(expected_ids):
            raise IntegrityError("board expected case coverage mismatch")
        reports_by_id = {}
        for row in rows:
            if set(row) != BOARD_MATRIX_ROW_KEYS:
                raise IntegrityError("board matrix row fields mismatch")
            report_record = row.get("report")
            if not isinstance(report_record, dict) or set(report_record) != BOARD_MATRIX_REPORT_KEYS:
                raise IntegrityError("board matrix report fields mismatch")
            if row.get("status") != "PASS":
                raise IntegrityError("board matrix row is not PASS")
            item = load_json(checked_record(root, row.get("report")))
            if item.get("case_id") != row["case_id"]:
                raise IntegrityError("board matrix row/report case identity mismatch")
            reports_by_id[row["case_id"]] = item
        reports = [reports_by_id[cid] for cid in expected_ids]
    else:
        if len(expected_ids) != 1 or report.get("case_id") != expected_ids[0]:
            raise IntegrityError("single board report requires exactly one expected numerical case")
        reports = [report]
    fresh = [replay_board_report(root, facts, item) for item in reports]
    return "PASS", {**data, "reason": "board reports and raw comparisons rechecked",
                    "board_verified": True, "comparison_replayed": True,
                    "cases": [x["case_id"] for x in fresh],
                    "reference_bindings": {x["case_id"]: x["reference_binding"] for x in fresh}}


def write_verdict(output: Path, payload: dict, protected: set[Path]) -> Path:
    """Publish a new result atomically; never replace any existing artifact."""
    # Keep the unresolved destination for exclusive creation (including symlinks).
    output = output.absolute()
    if output.resolve() in protected or os.path.lexists(output):
        raise IntegrityError(f"output would overwrite an input or existing artifact: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        # Unlike os.replace, link creation fails if another writer creates output.
        # The temporary file is on the same filesystem. No overwrite fallback.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink()
    return output


def protected_outputs(root: Path, run_dir, args, facts: dict) -> set[Path]:
    """Reserve named inputs even when missing; existing files are always protected."""
    values = [args.facts, args.design, args.verify]
    try:
        run = confined(root, run_dir)
        values += [run / "train_workflow_summary.json", run / "train_verify_summary.json"]
    except ValueError:
        pass  # The main audit reports the invalid run path; do not map it here.
    sources = facts.get("sources", [])
    if isinstance(sources, list):
        values += [row["path"] for row in sources
                   if isinstance(row, dict) and isinstance(row.get("path"), str)]
    protected = {args.audit_script.resolve()}
    for value in values:
        try:
            protected.add(confined(root, value))
        except ValueError:
            pass  # An invalid evidence path never authorizes replacing a file.
    return protected


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--opdir", type=Path, required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--facts", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--verify", required=True)
    parser.add_argument(
        "--audit-script", type=Path,
        default=Path(__file__).parents[2] / "hs-design-op-manual" / "scripts" / "training" / "audit_manual_inputs.py",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--board-policy", choices=("AUTO_ALL", "HOST_ONLY"), default="AUTO_ALL")
    args = parser.parse_args(argv)

    root = args.opdir.resolve()
    run_dir = args.run_dir
    output = args.output
    gates = {}
    issues = []
    run_id = None
    facts = {}
    verdict = "NOT_VERIFIED"
    try:
        run_dir = confined(root, run_dir)
        output = output or run_dir / "train_final_verdict.json"
        args.facts = confined(root, args.facts)
        args.design = confined(root, args.design)
        args.verify = confined(root, args.verify)
        summary = load_json(run_dir / "train_workflow_summary.json")
        run_id, summary_gate = check_summary(summary, run_dir)
        set_gate(gates, "summary", **summary_gate)
        if summary_gate["status"] != "PASS":
            issues.append(summary_gate["reason"])

        facts_path = confined(root, args.facts)
        facts = load_json(facts_path)
        if facts.get("run_id") != run_id:
            raise IntegrityError("facts run_id mismatch")
        set_gate(gates, "run_identity", "PASS", "summary, facts and run directory agree")

        host_status, host_data = check_host_aggregate(root, run_id, run_dir, facts.get("expected_cases"))
        set_gate(gates, "host_aggregate", host_status, **host_data)
        if host_status != "PASS":
            issues.append(host_data["reason"])

        checks_status, checks_data = check_facts_checks(facts)
        set_gate(gates, "checks", checks_status, **checks_data)
        if checks_status != "PASS":
            issues.append(checks_data["reason"])

        audit_data = audit(args, root)
        audit_details = dict(audit_data)
        audit_details.pop("status", None)
        set_gate(
            gates,
            "audit",
            audit_data["status"],
            "final publication audit",
            **audit_details,
        )
        if audit_data["status"] != "PASS":
            issues.append("final publication audit failed")

        board_status, board_data = check_board(root, facts, summary["stages"][-2], args.board_policy)
        set_gate(gates, "board", board_status, **board_data)
        if board_status != "PASS":
            issues.append(board_data["reason"])

        statuses = [gate["status"] for gate in gates.values()]
        verdict = "FAIL" if "FAIL" in statuses else (
            "NOT_VERIFIED" if "NOT_VERIFIED" in statuses else "PASS"
        )
    except IntegrityError as exc:
        verdict = "FAIL"
        issues.append(str(exc))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        verdict = "FAIL" if any(gate.get("status") == "FAIL" for gate in gates.values()) else "NOT_VERIFIED"
        issues.append(str(exc))

    host_delivered = (
        verdict != "FAIL" and facts.get("host_status") == "PASS"
        and all(gates.get(k, {}).get("status") == "PASS" for k in ("host_aggregate", "checks", "audit"))
        and gates.get("board", {}).get("board_status") == "NOT_RUN"
    )
    payload = {
        "schema_version": 1,
        "verification_kind": "training",
        "run_id": run_id,
        "verdict": verdict,
        "delivery_status": "HOST_PASS_BOARD_NOT_RUN" if host_delivered else verdict,
        "business_verified": verdict == "PASS",
        "board_verified": gates.get("board", {}).get("board_verified", False),
        "board_status": gates.get("board", {}).get("board_status"),
        "replayed": False,
        "training_rerun": False,
        "flash_rerun": False,
        "gates": gates,
        "issues": issues,
    }
    output = output or root / "train_final_verdict.json"
    try:
        output = write_verdict(output, payload, protected_outputs(root, run_dir, args, facts))
    except (OSError, ValueError) as exc:
        payload.update(verdict="FAIL", delivery_status="FAIL", business_verified=False)
        payload["issues"].append(f"verdict output refused: {exc}")
        # Do not fall back to another path or overwrite an earlier verdict.
        print(json.dumps({**payload, "path": str(output), "output_written": False}, ensure_ascii=False))
        return 2
    print(json.dumps({"verdict": verdict, "path": output.as_posix()}, ensure_ascii=False))
    return 0 if verdict == "PASS" else 2 if verdict == "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
