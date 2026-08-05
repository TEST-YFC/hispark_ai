#!/usr/bin/env python3
"""CLI for HiSpark.AI operator-performance experiment records."""

import argparse
import json
import sys

from harness.evidence import EvidenceError
from harness.workflow import (
    EVIDENCE_NAMES,
    WorkflowError,
    archive_failure,
    archive_success,
    bind_evidence,
    prepare_run,
    summarize,
)


def _identity(parser):
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--framework", choices=("onnx", "tflite"), required=True)
    parser.add_argument("--mode", choices=("fp32", "int8"), required=True)
    parser.add_argument("--target", required=True)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Prepare, bind, archive, and compare HiSpark.AI operator performance runs"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="freeze one run before collecting evidence")
    _identity(prepare)
    prepare.add_argument("--task-type", choices=("baseline", "optimization"), required=True)
    prepare.add_argument("--source-root")
    prepare.add_argument("--variable", default="")
    prepare.add_argument("--note", default="")
    prepare.add_argument("--change-kind", choices=("nnacl", "generated-code"), default="nnacl")
    prepare.add_argument("--allowed-change", action="append", default=[])
    prepare.add_argument("--ticks-per-us", type=float, default=24.0)
    prepare.add_argument("--window", type=int, default=50)
    prepare.add_argument("--stable-tolerance", type=float, default=0.05)
    prepare.add_argument("--timeout-seconds", type=float, default=110.0)

    bind = commands.add_parser("bind", help="bind one evidence file to a prepared run")
    bind.add_argument("--manifest", required=True)
    bind.add_argument("--kind", choices=tuple(EVIDENCE_NAMES), required=True)
    bind.add_argument("--source", required=True)

    record = commands.add_parser("record", help="validate and archive a complete run")
    record.add_argument("--manifest", required=True)
    record.add_argument("--firmware", required=True)
    record.add_argument("--codes-dir", required=True)
    record.add_argument("--cpu-archive", required=True)
    record.add_argument("--riscv-archive", required=True)
    record.add_argument("--sdk-root", required=True)

    fail = commands.add_parser("fail", help="archive a terminal failed run")
    fail.add_argument("--manifest", required=True)
    fail.add_argument("--stage", required=True)
    fail.add_argument("--detail", required=True)
    fail.add_argument("--log")

    summary = commands.add_parser("summarize", help="compare archived experiments")
    summary.add_argument("--repo-root", required=True)
    summary.add_argument("--operator", required=True)
    summary.add_argument("--case", required=True)
    summary.add_argument("--framework", choices=("onnx", "tflite"), required=True)
    summary.add_argument("--target", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        path, manifest = prepare_run(
            repo_root=args.repo_root,
            operator=args.operator,
            case=args.case,
            framework=args.framework,
            mode=args.mode,
            target=args.target,
            task_type=args.task_type,
            source_root=args.source_root,
            variable=args.variable,
            note=args.note,
            change_kind=args.change_kind,
            allowed_changes=args.allowed_change,
            ticks_per_us=args.ticks_per_us,
            window=args.window,
            stable_tolerance=args.stable_tolerance,
            timeout_seconds=args.timeout_seconds,
        )
        print(f"RUN_MANIFEST={path}")
        print(f"EXECUTION_ID={manifest['execution_id']}")
        return 0
    if args.command == "bind":
        path = bind_evidence(args.manifest, args.kind, args.source)
        print(f"EVIDENCE_BOUND={path}")
        return 0
    if args.command == "record":
        path = archive_success(
            manifest_path=args.manifest,
            firmware=args.firmware,
            codes_dir=args.codes_dir,
            cpu_archive=args.cpu_archive,
            riscv_archive=args.riscv_archive,
            sdk_root=args.sdk_root,
        )
        print(f"EXPERIMENT_SAVED={path}")
        return 0
    if args.command == "fail":
        path = archive_failure(
            manifest_path=args.manifest,
            stage=args.stage,
            detail=args.detail,
            log=args.log,
        )
        print(f"EXPERIMENT_SAVED={path}")
        return 0
    if args.command == "summarize":
        result = summarize(
            repo_root=args.repo_root,
            operator=args.operator,
            case=args.case,
            framework=args.framework,
            target=args.target,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EvidenceError, WorkflowError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
