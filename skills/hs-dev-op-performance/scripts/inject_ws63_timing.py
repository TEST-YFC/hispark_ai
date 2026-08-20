#!/usr/bin/env python3
"""Add the HiSpark.AI WS63 prediction-timing protocol to generated ai_main.c."""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path


FUNCTION = r"^static OH_AI_Status ai_mcu_sample_process\b"
NEXT_FUNCTION = r"^static void ai_mcu_sample_destroy\b"
MARKER = "[AI_MCU][PREDICT] OK seq=%u ticks=%u"


class InjectionError(RuntimeError):
    """Raised when the public board template is not safe to instrument."""


def _one(text, pattern, label):
    matches = list(re.finditer(pattern, text, re.MULTILINE))
    if len(matches) != 1:
        raise InjectionError(f"expected one {label}, found {len(matches)}")
    return matches[0]


def render(text):
    if MARKER in text:
        if text.count(MARKER) != 1:
            raise InjectionError("timing marker is duplicated")
        return text
    function = _one(text, FUNCTION, "ai_mcu_sample_process")
    next_function = _one(text, NEXT_FUNCTION, "ai_mcu_sample_destroy")
    if next_function.start() <= function.start():
        raise InjectionError("unsupported ai_mcu_sample_process boundary")
    body_offset = function.start()
    body = text[body_offset:next_function.start()]
    start = _one(body, r"^\s*uint64_t l1 = uapi_tcxo_get_count\(\);", "start tick")
    predict = _one(body, r"OH_AI_ModelPredict\(", "Predict call")
    end = _one(body, r"^\s*uint64_t l2 = uapi_tcxo_get_count\(\);", "end tick")
    post = _one(body, r"^\s*/\* PostProcess \*/", "PostProcess marker")
    checks = [
        match for match in re.finditer(
            r"^\s*if \(ret != OH_AI_STATUS_SUCCESS\)", body, re.MULTILINE
        )
        if end.start() < match.start() < post.start()
    ]
    if len(checks) != 1:
        raise InjectionError(
            f"expected one Predict failure check, found {len(checks)}"
        )
    check = checks[0]
    if not start.start() < predict.start() < end.start() < check.start() < post.start():
        raise InjectionError("unsupported Predict/timing statement order")
    text = re.sub(
        r'^\s*osal_printk\("\[AI_MCU\] Get Tcxo Time[^\n]*\n',
        "",
        text,
        flags=re.MULTILINE,
    )
    function = _one(text, FUNCTION, "ai_mcu_sample_process")
    text = (
        text[:function.start()]
        + "static uint32_t hs_perf_sequence = 0;\n\n"
        + text[function.start():]
    )
    post = _one(text, r"^\s*/\* PostProcess \*/", "PostProcess marker")
    indent = re.match(r"\s*", post.group()).group()
    insertion = (
        f"{indent}hs_perf_sequence++;\n"
        f'{indent}osal_printk("{MARKER}\\n", hs_perf_sequence, '
        "(uint32_t)(l2 - l1));\n"
    )
    return text[:post.start()] + insertion + text[post.start():]


def inject(path):
    path = Path(path).resolve()
    original = path.read_text(encoding="utf-8")
    updated = render(original)
    if updated == original:
        return False
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return True


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--ai-main", required=True)
    args = parser.parse_args(argv)
    print(f"TIMING_INJECTION={'CHANGED' if inject(args.ai_main) else 'UNCHANGED'}")


if __name__ == "__main__":
    try:
        main()
    except (InjectionError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
