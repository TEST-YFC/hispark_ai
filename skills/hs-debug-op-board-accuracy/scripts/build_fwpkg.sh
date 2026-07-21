#!/bin/bash
# ===================================================================
# hs-debug-op-board-accuracy 固件编译脚本
#
# 从 hs-verify-op 的测试用例模型构建 .fwpkg 固件。
# 针对单个模型编译固件。
#
# 用法:
#   bash build_fwpkg.sh --model <model.onnx> \
#       --model-name <name> \
#       --framework <onnx|tflite> \
#       --output-dir <dir> \
#       [--quantized] \
#       [--calib-dir <dir>]
#
# 前置条件:
#   MSLITE_PKG          - MindSpore Lite 编译产物目录
#   SDK_PATH            - WS63 SDK 路径 (缺省自动 clone 到 vendor/WS63/sdk)
#   以下由 build_mslite.sh 自动设置:
#     HISPARK_RISCV_TOOLCHAIN_PATH
# ===================================================================
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
CFG_DIR="$SCRIPT_DIR/cfg"
SKILL_DIR=$(cd "$SCRIPT_DIR/.." && pwd -P)
HISPARK_ROOT=$(cd "$SKILL_DIR/../../.." && pwd -P)

usage() {
    cat <<EOF
Usage: bash build_fwpkg.sh --model <path> --model-name <name> --framework <onnx|tflite> --output-dir <dir> [--quantized] [--calib-dir <dir>]

Arguments:
  --model       模型文件路径 (.onnx 或 .tflite)
  --model-name  模型名称 (用于输出文件命名)
  --framework   模型框架: onnx 或 tflite
  --output-dir  输出目录 (.fwpkg 存放位置)
  --quantized   生成 INT8 量化固件 (缺省生成 fp32)
  --calib-dir   校准数据目录 (量化时需要; 缺省使用 --model 所在目录下的 input/calib_*)
EOF
}

# ---- arg parsing ----
MODEL=""
MODEL_NAME=""
FRAMEWORK=""
OUTPUT_DIR=""
QUANTIZED=false
CALIB_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)      MODEL="$2"; shift 2 ;;
        --model-name) MODEL_NAME="$2"; shift 2 ;;
        --framework)  FRAMEWORK="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --quantized)  QUANTIZED=true; shift ;;
        --calib-dir)  CALIB_DIR="$2"; shift 2 ;;
        -h|--help)    usage; exit 0 ;;
        *)            echo "ERROR: unknown arg: $1"; usage; exit 1 ;;
    esac
done

[[ -z "$MODEL" ]]       && { echo "ERROR: missing --model"; usage; exit 1; }
[[ -z "$MODEL_NAME" ]]  && { echo "ERROR: missing --model-name"; usage; exit 1; }
[[ -z "$FRAMEWORK" ]]   && { echo "ERROR: missing --framework"; usage; exit 1; }
[[ -z "$OUTPUT_DIR" ]]  && { echo "ERROR: missing --output-dir"; usage; exit 1; }
[[ ! -f "$MODEL" ]]     && { echo "ERROR: model not found: $MODEL"; exit 2; }

# converter_lite expects uppercase framework names
FRAMEWORK=$(echo "$FRAMEWORK" | tr '[:lower:]' '[:upper:]')

mkdir -p "$OUTPUT_DIR"

# ---- prerequisites ----
echo "=========================================="
echo "  build_fwpkg: $MODEL_NAME"
echo "=========================================="
echo "  Model     : $MODEL"
echo "  Framework : $FRAMEWORK"
echo "  Quantized : $QUANTIZED"

# MSLITE_PKG
if [[ -z "${MSLITE_PKG:-}" ]]; then
    # auto-detect from hispark output
    compressed=$(find "$HISPARK_ROOT/src/mindspore-lite/output" -maxdepth 1 -name "mindspore-lite-*-linux-x64.tar.gz" 2>/dev/null | head -1)
    if [[ -n "$compressed" ]]; then
        dir_name=$(basename "$compressed" .tar.gz)
        MSLITE_PKG="$HISPARK_ROOT/src/mindspore-lite/output/$dir_name"
        if [[ ! -d "$MSLITE_PKG" ]]; then
            tar -xzf "$compressed" -C "$(dirname "$compressed")"
        fi
    fi
fi
if [[ -z "${MSLITE_PKG:-}" ]] || [[ ! -x "$MSLITE_PKG/tools/converter/converter/converter_lite" ]]; then
    echo "ERROR: MSLITE_PKG not set or converter_lite not found"
    echo "  Run hs-dev-op-implement step6 first."
    exit 3
fi
echo "  MSLITE_PKG: $MSLITE_PKG"

# RISCV toolchain: prefer SDK-bundled GCC, fallback to BiSheng
SDK_GCC="$SDK_PATH/src/tools/bin/compiler/riscv/cc_riscv32_musl_105/cc_riscv32_musl/bin"
if [[ -x "$SDK_GCC/riscv32-linux-musl-gcc" ]]; then
    HISPARK_RISCV_TOOLCHAIN_PATH="${HISPARK_RISCV_TOOLCHAIN_PATH:-$(dirname "$SDK_GCC")}"
elif [[ -z "${HISPARK_RISCV_TOOLCHAIN_PATH:-}" ]]; then
    echo "ERROR: HISPARK_RISCV_TOOLCHAIN_PATH not set and SDK GCC not found"
    echo "  Run build_mslite.sh first (it auto-detects and exports this)."
    exit 3
fi
echo "  RISCV toolchain: $HISPARK_RISCV_TOOLCHAIN_PATH"

# SDK_PATH
if [[ -z "${SDK_PATH:-}" ]]; then
    SDK_PATH="$HISPARK_ROOT/vendor/WS63/sdk"
fi
if [[ ! -d "$SDK_PATH/src" ]]; then
    echo "[sdk] cloning WS63 SDK..."
    git clone https://gitcode.com/HiSpark/fbb_ws63.git "$SDK_PATH" || {
        echo "ERROR: failed to clone SDK"
        exit 3
    }
fi
echo "  SDK_PATH: $SDK_PATH"

# ADAPTOR_PATH
if [[ -z "${ADAPTOR_PATH:-}" ]]; then
    ADAPTOR_PATH="$HISPARK_ROOT/src/adaptor"
fi
echo "  ADAPTOR_PATH: $ADAPTOR_PATH"

export PATH="$MSLITE_PKG/tools/converter/converter:$PATH"
export LD_LIBRARY_PATH="$MSLITE_PKG/runtime/lib:$MSLITE_PKG/tools/converter/lib:${LD_LIBRARY_PATH:-}"

# ---- converter_lite ----
WORK_DIR="$OUTPUT_DIR/build_${MODEL_NAME}"
MODEL_DIR="$WORK_DIR/micro"
SAMPLE_PATH="$HISPARK_ROOT/src/samples/oh/lenet5"

rm -rf "$MODEL_DIR"
mkdir -p "$MODEL_DIR"

echo ""
echo "[convert] converting model..."

CONVERTER_CMD="converter_lite --fmk=$FRAMEWORK --modelFile=$MODEL --outputFile=$MODEL_DIR --inputDataFormat=NCHW --encryption=false --outputDataFormat=NCHW"

if $QUANTIZED; then
    # Prepare quantized config with calibration paths
    QUANT_CFG="$WORK_DIR/micro_quant.cfg"
    cp "$CFG_DIR/micro_quant.cfg" "$QUANT_CFG"

    # Determine calibration dirs
    if [[ -z "$CALIB_DIR" ]]; then
        CASE_DIR=$(dirname "$MODEL")/..
        if [[ -d "$CASE_DIR/input/calib_0" ]]; then
            CALIB_DIR="$CASE_DIR/input"
        else
            echo "ERROR: --quantized requires --calib-dir (or model must be under hs-verify-op case dir)"
            exit 2
        fi
    fi

    # Build calibrate_path: A:dir0,B:dir1,...
    calib_parts=""
    for d in "$CALIB_DIR"/calib_*; do
        if [[ -d "$d" ]]; then
            idx=$(basename "$d" | sed 's/calib_//')
            letter=$(printf "\\x$(printf '%x' $((65 + idx)))" 2>/dev/null || python3 -c "print(chr(65+$idx))")
            [[ -n "$calib_parts" ]] && calib_parts="$calib_parts,"
            calib_parts="${calib_parts}${letter}:${d}"
        fi
    done
    if [[ -z "$calib_parts" ]]; then
        echo "ERROR: no calib_* dirs found in $CALIB_DIR"
        exit 2
    fi
    echo "  calibrate_path: $calib_parts"

    sed -i "s|{CALIBRATE_PATH}|$calib_parts|" "$QUANT_CFG"
    CONVERTER_CMD="$CONVERTER_CMD --configFile=$QUANT_CFG"
else
    CONVERTER_CMD="$CONVERTER_CMD --configFile=$CFG_DIR/micro_default.cfg"
fi

echo "  $CONVERTER_CMD"
eval "$CONVERTER_CMD" || { echo "ERROR: converter_lite failed"; exit 4; }

# ---- compiling micro ----
echo ""
echo "[compile] building micro runtime..."

compiling_micro() {
    local mindspore_lite_path="$MSLITE_PKG"
    cd "$MODEL_DIR" || exit 1
    rm -rf build
    cmake -S . -B build \
        -D OP_LIB="$mindspore_lite_path/tools/codegen/lib/riscv/libnnacl.a" \
        -D WRAPPER_LIB="$mindspore_lite_path/tools/codegen/lib/riscv/libwrapper.a" \
        -D RISCV_TOOLCHAIN_PATH="$HISPARK_RISCV_TOOLCHAIN_PATH/bin" \
        -D PKG_PATH="$mindspore_lite_path"
    cd build
    make -j4

    # Copy static libs to SDK
    rm -rf "$SDK_PATH/middleware/utils/ai_mcu/lib"
    mkdir -p "$SDK_PATH/middleware/utils/ai_mcu/lib"
    cp ./libmicro_runtime.a "$SDK_PATH/middleware/utils/ai_mcu/lib"
    cp ./src/libnet.a "$SDK_PATH/middleware/utils/ai_mcu/lib"
    echo "  libmicro_runtime.a + libnet.a -> SDK"
}

compiling_micro

# ---- ai_main.c ----
echo ""
echo "[ai_main] preparing sample..."

TEMPLATE="$SAMPLE_PATH/src/ai_main.c"
if [[ ! -f "$TEMPLATE" ]]; then
    echo "ERROR: ai_main.c template not found: $TEMPLATE"
    exit 4
fi

cp "$TEMPLATE" "$WORK_DIR/ai_main.c"

if $QUANTIZED; then
    quant_flag="1"
else
    quant_flag="0"
fi

# Set macros for this build
sed -i "s/#define AI_MCU_SAMPLE_NOT_QUANT .*/#define AI_MCU_SAMPLE_NOT_QUANT $([[ "$quant_flag" == "0" ]] && echo "1" || echo "0")/" "$WORK_DIR/ai_main.c"
sed -i "s/#define AI_MCU_SAMPLE_MICRO_QUANT .*/#define AI_MCU_SAMPLE_MICRO_QUANT $([[ "$quant_flag" == "1" ]] && echo "1" || echo "0")/" "$WORK_DIR/ai_main.c"
sed -i "s/#define AI_MCU_SAMPLE_TFLITE_QUANT .*/#define AI_MCU_SAMPLE_TFLITE_QUANT 0/" "$WORK_DIR/ai_main.c"

cp "$WORK_DIR/ai_main.c" "$SAMPLE_PATH/src/ai_main.c"

# ---- SDK build ----
echo ""
echo "[sdk] building firmware..."

# Ensure adaptor is in place
if [[ ! -d "$SDK_PATH/middleware/utils/ai_mcu/adaptor" ]]; then
    mkdir -p "$SDK_PATH/middleware/utils/ai_mcu"
    cp -rf "$ADAPTOR_PATH/adaptor" "$SDK_PATH/middleware/utils/ai_mcu"
fi
if [[ ! -f "$SDK_PATH/include/middleware/utils/ai.h" ]]; then
    mkdir -p "$SDK_PATH/include/middleware/utils"
    cp -rf "$ADAPTOR_PATH/include/ai.h" "$SDK_PATH/include/middleware/utils"
fi

export ENABLE_AI_CUSTOM_SAMPLE=y

# Patch SDK CMakeLists to include this sample
if ! grep -q "\$ENV{ENABLE_AI_CUSTOM_SAMPLE}" "$SDK_PATH/application/samples/CMakeLists.txt" 2>/dev/null; then
    sed -i '/COMPONENT_NAME/a\\nset(CONFIG_ENABLE_AI_CUSTOM_SAMPLE "$ENV{ENABLE_AI_CUSTOM_SAMPLE}")' "$SDK_PATH/application/samples/CMakeLists.txt"
fi
if ! grep -q "if(DEFINED CONFIG_ENABLE_AI_CUSTOM_SAMPLE)" "$SDK_PATH/application/samples/CMakeLists.txt" 2>/dev/null; then
    sed -i "/add_subdirectory_if_exist(custom)/i\if(DEFINED CONFIG_ENABLE_AI_CUSTOM_SAMPLE)\n  add_subdirectory(\n    \${CUR_DIR}\n    \${CMAKE_CURRENT_BINARY_DIR}/lenet5_build\n  )\nendif()\n" "$SDK_PATH/application/samples/CMakeLists.txt"
fi

# Patch SDK config to include ai_adaptor_cpu
if ! grep -q "ai_adaptor_cpu" "$SDK_PATH/build/config/target_config/ws63/config.py" 2>/dev/null; then
    python3 -c "
import ast
with open('$SDK_PATH/build/config/target_config/ws63/config.py', 'r') as f:
    content = f.read()
target = ast.literal_eval(content.split('=', 1)[1].strip().strip("'").strip('\"'))
if 'ws63-liteos-app' in target and 'ai_adaptor_cpu' not in target['ws63-liteos-app'].get('ram_component', []):
    target['ws63-liteos-app']['ram_component'].append('ai_adaptor_cpu')
with open('$SDK_PATH/build/config/target_config/ws63/config.py', 'w') as f:
    f.write(f'target = {repr(target)}\n')
    f.write('target_copy = {}\n')
    f.write('target_group = {}\n')
"
fi

# Build
origsample_cmake=$(<"$SDK_PATH/application/samples/CMakeLists.txt")
origcfg=$(<"$SDK_PATH/build/config/target_config/ws63/config.py")

cd "$SDK_PATH"
if [[ -f "$SDK_PATH/application/wb02_3.mk" ]]; then
    python3 build.py -c ws63-flashboot 2>&1 || true
fi
python3 build.py -c ws63-liteos-app 2>&1

# Collect output
FWPKG_SRC="$SDK_PATH/output/ws63/fwpkg/ws63-liteos-app/ws63-liteos-app_all.fwpkg"
if [[ ! -f "$FWPKG_SRC" ]]; then
    echo "ERROR: SDK build did not produce .fwpkg"
    exit 4
fi

FWPKG_DST="$OUTPUT_DIR/${MODEL_NAME}.fwpkg"
cp "$FWPKG_SRC" "$FWPKG_DST"

# Restore SDK to original state
echo "$origsample_cmake" > "$SDK_PATH/application/samples/CMakeLists.txt"
echo "$origcfg" > "$SDK_PATH/build/config/target_config/ws63/config.py"
cp "$TEMPLATE" "$SAMPLE_PATH/src/ai_main.c"

echo ""
echo "=========================================="
echo "  FWPKG_BUILD=PASS"
echo "  Firmware: $FWPKG_DST  ($(du -h "$FWPKG_DST" | cut -f1))"
echo "=========================================="
