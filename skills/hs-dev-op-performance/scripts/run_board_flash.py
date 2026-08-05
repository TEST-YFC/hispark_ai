#!/usr/bin/env python3
"""Run the HiSpark.AI Board flash/accuracy script with performance identity markers."""

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class BoardRunError(RuntimeError):
    """Raised when the Board command cannot be bound to one prepared run."""


def _option(arguments, name):
    matches = [arguments[index + 1] for index, value in enumerate(arguments[:-1]) if value == name]
    if len(matches) != 1:
        raise BoardRunError(f"expected exactly one {name} argument")
    return matches[0]


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Delegate to hs-debug-op-board-accuracy flash.sh with run identity"
    )
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--board-skill")
    args, flash_args = parser.parse_known_args(argv)
    if not SAFE_ID.fullmatch(args.execution_id):
        parser.error("--execution-id contains unsafe characters")
    if not flash_args:
        parser.error("pass the normal flash.sh arguments")
    skill_root = Path(__file__).resolve().parents[1]
    board_skill = (
        Path(args.board_skill).expanduser().resolve()
        if args.board_skill
        else skill_root.parent / "hs-debug-op-board-accuracy"
    )
    flash_script = board_skill / "scripts" / "flash.sh"
    if not flash_script.is_file():
        raise BoardRunError(f"Board flash script not found: {flash_script}")
    firmware = Path(_option(flash_args, "--firmware")).expanduser().resolve()
    if not firmware.is_file():
        raise BoardRunError(f"firmware not found: {firmware}")
    print(f"HS_PERF_EXECUTION_ID={args.execution_id}", flush=True)
    print(f"HS_PERF_FIRMWARE_SHA256={_sha256(firmware)}", flush=True)
    return subprocess.run(["bash", str(flash_script), *flash_args]).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BoardRunError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
