#!/usr/bin/env python3
"""Run the HiSpark.AI Board firmware builder with a temporary timing hook."""

import argparse
import hashlib
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


class TimedBuildError(RuntimeError):
    """Raised when the Board builder no longer exposes the expected hook point."""


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _builder_option(arguments, name):
    matches = [arguments[index + 1] for index, value in enumerate(arguments[:-1]) if value == name]
    if len(matches) != 1:
        raise TimedBuildError(f"expected exactly one {name} argument")
    return matches[0]


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_builder(source, destination, board_scripts, injector):
    text = Path(source).read_text(encoding="utf-8")
    script_dir_line = 'SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)'
    if text.count(script_dir_line) != 1:
        raise TimedBuildError("Board builder SCRIPT_DIR contract changed")
    text = text.replace(
        script_dir_line,
        f"SCRIPT_DIR={shlex.quote(str(Path(board_scripts).resolve()))}",
    )
    template_copy = 'cp "$TEMPLATE" "$WORK_DIR/ai_main.c"\n'
    template_restore = 'cp "$TEMPLATE" "$SAMPLE_PATH/src/ai_main.c"'
    if text.count(template_copy) != 1 or text.count(template_restore) != 1:
        raise TimedBuildError("Board builder template restore contract changed")
    guarded_copy = (
        'HS_PERF_TEMPLATE_BACKUP="$WORK_DIR/ai_main.template.backup.c"\n'
        'cp "$TEMPLATE" "$HS_PERF_TEMPLATE_BACKUP"\n'
        "hs_perf_restore_template() {\n"
        '    cp "$HS_PERF_TEMPLATE_BACKUP" "$TEMPLATE"\n'
        '    rm -f "$HS_PERF_TEMPLATE_BACKUP"\n'
        "}\n"
        "trap hs_perf_restore_template EXIT\n\n"
        + template_copy
    )
    text = text.replace(template_copy, guarded_copy)
    text = text.replace(
        template_restore,
        "# Template restoration is handled by hs_perf_restore_template.",
    )
    anchor = "# Set macros for this build\n"
    if text.count(anchor) != 1:
        raise TimedBuildError("Board builder ai_main hook contract changed")
    command = (
        f"python3 {shlex.quote(str(Path(injector).resolve()))} "
        '--ai-main "$WORK_DIR/ai_main.c"\n\n'
    )
    text = text.replace(anchor, command + anchor)
    destination.write_text(text, encoding="utf-8")
    destination.chmod(0o755)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "delegate to hs-debug-op-board-accuracy build_fwpkg.sh with a "
            "temporary WS63 timing injection hook"
        )
    )
    parser.add_argument(
        "--board-skill",
        help="Override hs-debug-op-board-accuracy directory",
    )
    parser.add_argument(
        "--execution-id",
        required=True,
        help="Execution ID from run_optimization.py prepare",
    )
    args, builder_args = parser.parse_known_args(argv)
    if not SAFE_ID.fullmatch(args.execution_id):
        parser.error("--execution-id contains unsafe characters")
    skill_root = Path(__file__).resolve().parents[1]
    board_skill = (
        Path(args.board_skill).resolve()
        if args.board_skill
        else skill_root.parent / "hs-debug-op-board-accuracy"
    )
    board_scripts = board_skill / "scripts"
    builder = board_scripts / "build_fwpkg.sh"
    injector = Path(__file__).resolve().parent / "inject_ws63_timing.py"
    if not builder.is_file():
        raise TimedBuildError(f"Board builder not found: {builder}")
    if not builder_args:
        parser.error("pass the normal build_fwpkg.sh arguments")
    print(f"HS_PERF_EXECUTION_ID={args.execution_id}", flush=True)
    with tempfile.TemporaryDirectory(prefix="hs-perf-board-build-") as directory:
        temporary_builder = Path(directory) / "build_fwpkg.sh"
        prepare_builder(builder, temporary_builder, board_scripts, injector)
        returncode = subprocess.run(["bash", str(temporary_builder), *builder_args]).returncode
    if returncode != 0:
        return returncode
    output_dir = Path(_builder_option(builder_args, "--output-dir")).expanduser().resolve()
    model_name = _builder_option(builder_args, "--model-name")
    firmware = output_dir / f"{model_name}.fwpkg"
    if not firmware.is_file():
        raise TimedBuildError(f"timed firmware not found after passing build: {firmware}")
    print(f"HS_PERF_FIRMWARE_SHA256={_sha256(firmware)}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, TimedBuildError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
