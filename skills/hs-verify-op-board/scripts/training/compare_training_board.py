#!/usr/bin/env python3
"""Strict, hardware-free comparison of saved training raw logs and Host golden."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from training_protocol import (IDENTITY, OPTIONAL_IDENTITY, METADATA, identity, index_tensors,
                               parameter_keys, parse_raw, read_json, sha256, write_json)


def close(actual, reference, atol, rtol, dtype="float32"):
    if len(actual) != len(reference):
        return False
    if dtype == "int32":
        return all(type(x) is int and type(y) is int and x == y
                   for x, y in zip(actual, reference))
    return all(abs(x - y) <= atol + rtol * abs(y) for x, y in zip(actual, reference))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--expected", type=Path, required=True)
    ap.add_argument("--observed", type=Path, help="Collector JSON; raw log is independently replayed")
    ap.add_argument("--raw-log", type=Path, help="Raw log override or direct replay input")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--atol", type=float, default=1e-5)
    ap.add_argument("--rtol", type=float, default=1e-5)
    a = ap.parse_args(argv)
    if not a.observed and not a.raw_log:
        ap.error("--observed or --raw-log is required")
    if a.output.resolve() in {p.resolve() for p in (a.expected, a.observed, a.raw_log) if p}:
        ap.error("output must not overwrite evidence")
    report = {"schema_version": 1, "verification_kind": "training", "status": "FAIL",
              "checks": [], "missing": [], "extra": [], "failed": [], "errors": [],
              "parameters_observed": False, "parameter_checks": [],
              "atol": a.atol, "rtol": a.rtol}
    # Non-finite CLI values must never leak into JSON output.
    report.update({k: v if math.isfinite(v) else None for k, v in (("atol", a.atol), ("rtol", a.rtol))})
    try:
        if any(not math.isfinite(v) or v < 0 for v in (a.atol, a.rtol)):
            raise ValueError("tolerances must be finite and nonnegative")
        exp = read_json(a.expected)
        if exp.get("verification_kind") != "training":
            raise ValueError("expected verification_kind must be training")
        training_config = exp.get("training_config")
        if training_config is not None:
            if (not isinstance(training_config, dict)
                    or not isinstance(training_config.get("sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", training_config["sha256"])):
                raise ValueError("expected training config SHA256 is invalid")
            report["training_config_sha256"] = training_config["sha256"]
        report.update(identity(exp))
        for field in ("case_sha256", "host_summary_sha256"):
            value = exp.get(field)
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError(f"expected {field} SHA256 is invalid")
            report[field] = value
        expected = index_tensors(exp.get("tensors"))
        if not expected:
            raise ValueError("expected tensors must not be empty")
        if "tolerances" in exp:
            if exp["tolerances"] != {"atol": a.atol, "rtol": a.rtol}:
                raise ValueError("CLI tolerances differ from frozen expected tolerances")
        obs = read_json(a.observed) if a.observed else None
        if obs is not None:
            if obs.get("verification_kind") != "training":
                raise ValueError("observed verification_kind must be training")
            identity(obs)
            index_tensors(obs.get("tensors"))
            if obs.get("capture_complete") is not True:
                raise ValueError("observed capture_complete must be true")
            if obs.get("parse_status", "PASS") != "PASS" or obs.get("errors"):
                raise ValueError("observed contains protocol errors")
            if "parameters_observed" in obs and type(obs["parameters_observed"]) is not bool:
                raise ValueError("parameters_observed must be boolean")
        raw_path = a.raw_log
        if raw_path is None:
            name = obs.get("raw_log")
            if not isinstance(name, str) or not name:
                raise ValueError("raw log required; pass --raw-log for legacy observed JSON")
            raw_path = Path(name)
            if not raw_path.is_absolute():
                raw_path = a.observed.parent / raw_path
        if raw_path.resolve() == a.output.resolve():
            ap.error("output must not overwrite referenced raw log")
        parsed = parse_raw(raw_path.read_bytes(), exp)
        report.update({"raw_log": str(raw_path.resolve()), "raw_log_sha256": parsed["raw_log_sha256"],
                       "expected_sha256": sha256(a.expected), "capture_complete": parsed["capture_complete"],
                       "parse_status": parsed["parse_status"],
                       "device_identity_fields": parsed.get("device_identity_fields", []),
                       "external_identity_fields": parsed.get("external_identity_fields", [])})
        if not parsed["capture_complete"]:
            report["errors"].extend(parsed["errors"])
            raise ValueError("raw protocol validation failed")
        actual = index_tensors(parsed["tensors"])
        if obs is not None:
            for key in IDENTITY + OPTIONAL_IDENTITY:
                if key in obs and key in exp and obs[key] != exp[key]:
                    raise ValueError(f"observed/expected identity mismatch: {key}")
                if key in parsed and key in obs and parsed[key] != obs[key]:
                    raise ValueError(f"observed/raw identity mismatch: {key}")
            if obs.get("raw_log_sha256") != parsed["raw_log_sha256"]:
                raise ValueError("observed/raw SHA256 mismatch")
            if index_tensors(obs["tensors"]) != actual:
                raise ValueError("observed tensors differ from raw replay")
            report["observed"] = str(a.observed.resolve())
            report["observed_sha256"] = sha256(a.observed)
            report["capture_transport_status"] = obs.get("transport_status", "UNKNOWN")
            report["backend_returncode"] = obs.get("backend_returncode")
            report["capture_attempt_id"] = obs.get("capture_attempt_id")
        else:
            report["capture_transport_status"] = "UNKNOWN"
            report["backend_returncode"] = None
        report["missing"] = sorted(set(expected) - set(actual))
        report["extra"] = sorted(set(actual) - set(expected))
        for key, item in expected.items():
            got = actual.get(key)
            if got is None:
                report["checks"].append({"key": key, "status": "FAIL", "reason": "missing tensor"})
                continue
            metadata_ok = all(item[k] == got.get(k) for k in METADATA if k in item)
            if item.get("dtype") == "int32" and any(type(x) is not int for x in got["data"]):
                ok = False
            else:
                ok = metadata_ok and close(got["data"], item["data"], a.atol, a.rtol,
                                           item.get("dtype", "float32"))
            row = {"key": key, "status": "PASS" if ok else "FAIL",
                   "expected_elements": len(item["data"]), "observed_elements": len(got["data"]),
                   "metadata_verified": all(k in item and k in got for k in ("dtype", "shape", "elements"))}
            report["checks"].append(row)
            if not ok:
                report["failed"].append(key)
        required = parameter_keys(exp)
        report["required_parameters"] = sorted(required)
        report["parameters_observed"] = bool(required) and required <= set(actual)
        if obs is not None and "parameters_observed" in obs and obs["parameters_observed"] != report["parameters_observed"]:
            raise ValueError("parameters_observed conflicts with expected parameter coverage")
        rules = exp.get("parameter_checks", [])
        if not isinstance(rules, list):
            raise ValueError("parameter_checks must be a list")
        for rule in rules:
            if not isinstance(rule, dict) or rule.get("kind") not in ("equal", "must_change"):
                raise ValueError("parameter check kind must be equal or must_change")
            left, right = rule.get("left"), rule.get("right")
            if not isinstance(left, str) or not isinstance(right, str) or left not in expected or right not in expected:
                raise ValueError("parameter check must reference expected tensor keys")
            refs = expected[left]["data"], expected[right]["data"]
            if len(refs[0]) != len(refs[1]):
                raise ValueError("parameter check shape mismatch")
            want_equal = rule["kind"] == "equal"
            if (refs[0] == refs[1]) != want_equal:
                raise ValueError("golden contradicts parameter check")
            ok = (left in actual and right in actual and
                  len(actual[left]["data"]) == len(actual[right]["data"]) and
                  ((actual[left]["data"] == actual[right]["data"]) == want_equal))
            report["parameter_checks"].append({**rule, "status": "PASS" if ok else "FAIL"})
        errors = report["missing"] or report["extra"] or report["failed"] or any(
            row["status"] != "PASS" for row in report["parameter_checks"])
        report["status"] = "FAIL" if errors else ("PASS" if report["parameters_observed"] else "NOT_RUN")
        report["reason"] = "" if report["parameters_observed"] else "No expected runtime parameter observations"
    except FileNotFoundError as exc:
        report["status"] = "NOT_RUN"
        report["errors"].append(str(exc))
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        report["status"] = "FAIL"
        report["errors"].append(str(exc))
    report["tensor_count"] = len(report["checks"])
    write_json(a.output, report)
    print(json.dumps(report, ensure_ascii=False, allow_nan=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
