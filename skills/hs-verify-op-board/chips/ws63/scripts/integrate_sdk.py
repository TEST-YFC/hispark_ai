#!/usr/bin/env python3
"""Install one generated operator case into a user-authorized WS63 SDK.

All mutations are fixed and idempotent. Existing differing adaptor files are
rejected unless --replace-adaptor is explicitly supplied after review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import sys


def fail(message: str) -> "NoReturn":
    print(f"SDK_INTEGRATION_GATE=FAIL reason={message}", file=sys.stderr)
    raise SystemExit(2)


def existing_absolute(value: str, name: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.exists():
        fail(f"{name}_must_be_existing_absolute_path:{value}")
    return path.resolve()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def powershell_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def validate_target(value: str) -> str:
    """Allow SDK target identifiers, not shell language.

    Target names come from ``fbb describe`` and are identifiers.  Keeping the
    accepted alphabet generic preserves support for future chips/SDKs while
    preventing generated wrapper scripts from carrying shell metacharacters.
    """
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise argparse.ArgumentTypeError(
            "target must contain only letters, digits, '.', '_' or '-'")
    return value


def without_managed_blocks(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    text = re.sub(r"\n?# BEGIN HISPARK AI [^\n]+\n.*?# END HISPARK AI [^\n]+(?:\n|$)",
                  "\n", text, flags=re.S)
    text = re.sub(r"\s+", " ", text).strip()
    return text.encode("utf-8")


def copy_tree_checked(source: Path, target: Path, replace: bool) -> list[str]:
    copied = []
    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue
        destination = target / item.relative_to(source)
        if destination.exists() and destination.read_bytes() != item.read_bytes() and not replace:
            if without_managed_blocks(destination.read_bytes()) != without_managed_blocks(item.read_bytes()):
                fail(f"adaptor_diff_requires_review_and_replace_flag:{destination}")
            # Keep our previously installed managed block; the run is idempotent.
            copied.append(str(destination))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)
        copied.append(str(destination))
    return copied


def marker_block(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    begin, end = f"# BEGIN {marker}", f"# END {marker}"
    replacement = f"{begin}\n{block.rstrip()}\n{end}"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if pattern.search(text):
        text = pattern.sub(replacement, text)
    else:
        text = text.rstrip() + "\n\n" + replacement + "\n"
    path.write_text(text, encoding="utf-8")


def marker_block_before(path: Path, marker: str, block: str, token: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    begin, end = f"# BEGIN {marker}", f"# END {marker}"
    replacement = f"{begin}\n{block.rstrip()}\n{end}"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    text = pattern.sub("", text).rstrip() + "\n"
    position = text.find(token)
    if position < 0:
        fail(f"cmake_insertion_token_missing:{path}:{token}")
    text = text[:position] + replacement + "\n\n" + text[position:]
    path.write_text(text, encoding="utf-8")


def marker_block_unless_native(path: Path, marker: str, block: str, required_tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if all(token in text for token in required_tokens):
        return
    marker_block(path, marker, block)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-root", required=True,
                        help="User-provided FIRMWARE_SDK_ROOT (repository root)")
    parser.add_argument("--hispark-root", required=True)
    parser.add_argument("--sample-dir", required=True)
    parser.add_argument("--model-lib-dir", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--mode", required=True, choices=("fp32", "int8"))
    parser.add_argument("--target", required=True, type=validate_target)
    parser.add_argument("--replace-adaptor", action="store_true")
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()

    sdk_root = existing_absolute(args.sdk_root, "sdk_root")
    sdk = sdk_root / "src" if (sdk_root / "src/application").is_dir() else sdk_root
    if not (sdk / "application").is_dir() or not (sdk / "middleware/utils").is_dir():
        fail(f"not_a_ws63_sdk:{sdk}")
    hispark = existing_absolute(args.hispark_root, "hispark_root")
    sample = existing_absolute(args.sample_dir, "sample_dir")
    libraries = existing_absolute(args.model_lib_dir, "model_lib_dir")
    receipt = Path(args.receipt)
    if not receipt.is_absolute():
        fail("receipt_must_be_absolute")
    for name in ("libmicro_runtime.a", "libnet.a"):
        if not (libraries / name).is_file():
            fail(f"missing_archive:{libraries / name}")
    if not (sample / "src/ai_main.c").is_file() or not (sample / "CMakeLists.txt").is_file():
        fail(f"invalid_generated_sample:{sample}")

    source_adaptor = hispark / "src/adaptor/adaptor"
    source_header = hispark / "src/adaptor/include/ai.h"
    if not source_adaptor.is_dir() or not source_header.is_file():
        fail(f"hispark_adaptor_missing:{hispark / 'src/adaptor'}")
    installed = copy_tree_checked(source_adaptor, sdk / "middleware/utils/ai_mcu/adaptor",
                                  args.replace_adaptor)
    header = sdk / "include/middleware/utils/ai.h"
    if header.exists() and header.read_bytes() != source_header.read_bytes() and not args.replace_adaptor:
        fail(f"ai_header_diff_requires_review_and_replace_flag:{header}")
    header.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_header, header)
    installed.append(str(header))

    variant = re.sub(r"[^a-zA-Z0-9_.-]", "_", f"{args.operator}_{args.case}_{args.mode}")
    variant_dir = sdk / "middleware/utils/ai_mcu/lib" / variant
    variant_dir.mkdir(parents=True, exist_ok=True)
    for name in ("libmicro_runtime.a", "libnet.a"):
        shutil.copy2(libraries / name, variant_dir / name)
        installed.append(str(variant_dir / name))

    adaptor_cmake = sdk / "middleware/utils/ai_mcu/adaptor/cpu/CMakeLists.txt"
    marker_block_before(adaptor_cmake, "HISPARK AI MODEL VARIANT", '''
set(AI_MODEL_VARIANT "$ENV{AI_MCU_MODEL_VARIANT}")
if(NOT "${AI_MODEL_VARIANT}" STREQUAL "")
    set(AI_MODEL_LIB_DIR "${ROOT_DIR}/middleware/utils/ai_mcu/lib/${AI_MODEL_VARIANT}")
    if(NOT EXISTS "${AI_MODEL_LIB_DIR}/libmicro_runtime.a" OR
       NOT EXISTS "${AI_MODEL_LIB_DIR}/libnet.a")
        message(FATAL_ERROR "AI model variant archives missing: ${AI_MODEL_LIB_DIR}")
    endif()
    set(LIBS
        "${AI_MODEL_LIB_DIR}/libmicro_runtime.a"
        "${AI_MODEL_LIB_DIR}/libnet.a"
    )
endif()
''', "build_component()")
    marker_block_unless_native(sdk / "middleware/utils/CMakeLists.txt", "HISPARK AI CPU ADAPTOR", '''
if("$ENV{ENABLE_AI_CUSTOM_SAMPLE}")
    add_subdirectory_if_exist(ai_mcu/adaptor/cpu)
endif()
''', ("ENABLE_AI_CUSTOM_SAMPLE", "ai_mcu/adaptor/cpu"))
    marker_block_unless_native(sdk / "application/samples/CMakeLists.txt", "HISPARK AI CUSTOM SAMPLE", '''
if("$ENV{ENABLE_AI_CUSTOM_SAMPLE}" AND DEFINED ENV{AI_CUSTOM_SAMPLE_DIR})
    add_subdirectory("$ENV{AI_CUSTOM_SAMPLE_DIR}" "${CMAKE_CURRENT_BINARY_DIR}/ai_custom_sample_build")
endif()
''', ("ENABLE_AI_CUSTOM_SAMPLE", "AI_CUSTOM_SAMPLE_DIR", "add_subdirectory"))
    target_cfg = sdk / "build/config/target_config/ws63/config.py"
    if not target_cfg.is_file():
        fail(f"target_config_missing:{target_cfg}")
    target_literal = repr(args.target)
    marker_block(target_cfg, "HISPARK AI TARGET COMPONENT", f'''
if {target_literal} in target:
    _hs_ai_components = target[{target_literal}].setdefault('ram_component', [])
    while '-:ai_adaptor_cpu' in _hs_ai_components:
        _hs_ai_components.remove('-:ai_adaptor_cpu')
    if 'ai_adaptor_cpu' not in _hs_ai_components:
        _hs_ai_components.append('ai_adaptor_cpu')
''')

    environment = {
        "FIRMWARE_SDK_ROOT": str(sdk_root), "FBB_SDK_DIR": str(sdk),
        "ENABLE_AI_CUSTOM_SAMPLE": "y", "AI_CUSTOM_SAMPLE_DIR": str(sample),
        "AI_MCU_MODEL_VARIANT": variant, "target": args.target,
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sdk_root": str(sdk_root), "sdk_src": str(sdk), "variant": variant,
        "sample": str(sample), "model_lib_dir": str(variant_dir),
        "environment": environment, "installed": installed,
        "archives": {name: digest(variant_dir / name) for name in ("libmicro_runtime.a", "libnet.a")},
    }
    receipt.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (receipt.parent / "ws63_board_env.ps1").write_text(
        "\n".join(f"$env:{key}={powershell_literal(value)}" for key, value in environment.items()) + "\n",
        encoding="utf-8")
    (receipt.parent / "ws63_board_env.sh").write_text(
        "\n".join(f"export {key}={shlex.quote(value)}" for key, value in environment.items()) + "\n",
        encoding="utf-8")
    (receipt.parent / "invoke_hs_dev_build.ps1").write_text(
        ". $PSScriptRoot\\ws63_board_env.ps1\n"
        "if (-not $env:AI_CUSTOM_SAMPLE_DIR -or -not $env:AI_MCU_MODEL_VARIANT) { "
        "throw 'WS63 board environment was not loaded' }\n"
        "Write-Output \"AI_CUSTOM_SAMPLE_DIR=$env:AI_CUSTOM_SAMPLE_DIR\"\n"
        "Write-Output \"AI_MCU_MODEL_VARIANT=$env:AI_MCU_MODEL_VARIANT\"\n"
        f"fbb build {powershell_literal(args.target)} --clean\n"
        "exit $LASTEXITCODE\n",
        encoding="utf-8")
    (receipt.parent / "invoke_hs_dev_build.sh").write_text(
        ". \"$(dirname \"$0\")/ws63_board_env.sh\"\n"
        ': "${AI_CUSTOM_SAMPLE_DIR:?missing AI_CUSTOM_SAMPLE_DIR}"\n'
        ': "${AI_MCU_MODEL_VARIANT:?missing AI_MCU_MODEL_VARIANT}"\n'
        'printf "AI_CUSTOM_SAMPLE_DIR=%s\\n" "$AI_CUSTOM_SAMPLE_DIR"\n'
        'printf "AI_MCU_MODEL_VARIANT=%s\\n" "$AI_MCU_MODEL_VARIANT"\n'
        f"fbb build {shlex.quote(args.target)} --clean\n",
        encoding="utf-8")
    print(f"SDK_INTEGRATION_GATE=PASS variant={variant} receipt={receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
