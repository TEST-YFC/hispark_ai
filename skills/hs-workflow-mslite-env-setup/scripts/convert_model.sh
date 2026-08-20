#!/bin/bash
# ONNX 模型转换为 C 语言 Micro 工程
# 用法: bash scripts/convert_model.sh <onnx_model> <output_dir>

set -e

if [ $# -lt 2 ]; then
    echo "用法: bash convert_model.sh <onnx_model> <output_dir>"
    echo "示例: bash convert_model.sh ./model/mnist-12.onnx ./output/micro_gen"
    exit 1
fi

MODEL_FILE=$(realpath "$1")
mkdir -p "$2"
OUTPUT_DIR=$(realpath "$2")
CONFIG_FILE=$(dirname "$OUTPUT_DIR")/micro_config.cfg

echo "[convert_model] 模型: $MODEL_FILE"
echo "[convert_model] 输出: $OUTPUT_DIR"
echo "[convert_model] 配置: $CONFIG_FILE"

# 检查 MSLite 包
if [ -z "$MSLITE_PKG" ]; then
    echo "[convert_model] 错误: 请先 source scripts/setup_env.sh"
    exit 1
fi

# 创建配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[convert_model] 创建 micro_config.cfg ..."
    cat > "$CONFIG_FILE" << 'CFG_EOF'
[micro_param]
enable_micro=true
target=RISCV
support_parallel=false
CFG_EOF
fi

# 自动绑定本轮工具包的 converter 动态库。每次工具调用可能是新 shell，因此必须在
# 启动 converter 的同一进程中执行，不能依赖用户先前手工 export。
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/converter_runtime_env.sh"
export PATH="$MSLITE_PKG/tools/converter/converter:$PATH"
echo "[convert_model] CONVERTER_RUNTIME_GATE=PASS libraries=$CONVERTER_RUNTIME_LIBRARY_DIRS"

# converter CLI随版本变化：支持加密的构建默认可能开启加密，而2.8等构建又完全没有
# --encryption参数。必须在与真实转换相同的动态库环境中探测，不能硬编码版本参数。
CONVERTER="$MSLITE_PKG/tools/converter/converter/converter_lite"
HELP_LOG=/tmp/mslite_converter_help.log
if ! "$CONVERTER" --help > "$HELP_LOG" 2>&1; then
    echo "[convert_model] 错误: 已自动配置本轮工具包动态库，但converter_lite仍无法启动: $HELP_LOG" >&2
    tail -20 "$HELP_LOG" >&2
    exit 1
fi
ENCRYPTION_ARGS=()
if grep -Eq '(^|[^[:alnum:]_])--encryption([=[:space:]]|$)' "$HELP_LOG"; then
    ENCRYPTION_ARGS+=(--encryption=false)
    echo "[convert_model] converter encryption=supported; using --encryption=false"
else
    echo "[convert_model] converter encryption=unsupported; omitted"
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 执行转换, 输出捕获到日志用于成功标志校验与失败诊断。
# 注意: converter_lite 失败时 (退出码非0, 如 255) 必须落到下方校验分支打印诊断,
# 不能被第 5 行的 set -e 提前终结, 故在此显式关闭 errexit, 退出码经 CONV_RC 捕获后重新开启。
CONV_LOG=/tmp/mslite_convert.log
echo "[convert_model] 执行转换... (日志: $CONV_LOG)"
set +e
"$CONVERTER" \
    --fmk=ONNX \
    --modelFile="$MODEL_FILE" \
    --outputFile="$OUTPUT_DIR" \
    --configFile="$CONFIG_FILE" \
    --inputDataFormat=NCHW \
    "${ENCRYPTION_ARGS[@]}" \
    --outputDataFormat=NCHW > "$CONV_LOG" 2>&1
CONV_RC=$?
set -e

# 校验输出: converter_lite 成功时向 stdout 打印 "CONVERT RESULT SUCCESS:0"
# (见 mindspore-lite/tools/converter/converter.cc:1373)。仅凭退出码不可靠
# (存在返回0但产物未生成的情形), 故以该成功标志为准, 并复核 micro 工程标志文件 net.cmake。
# 不依赖文件计数: 输出目录可能残留上一次的旧产物, 计数无法区分本次是否真正成功。
if grep -q "CONVERT RESULT SUCCESS:" "$CONV_LOG" && [ -f "$OUTPUT_DIR/src/net.cmake" ]; then
    echo "[convert_model] ✓ 转换成功 (exit=$CONV_RC)"
    GEN_FILES=$(find "$OUTPUT_DIR" -type f | wc -l)
    echo "[convert_model] 产物文件数: $GEN_FILES"
    echo "[convert_model] 产物大小: $(du -sh "$OUTPUT_DIR" | cut -f1)"
else
    echo "[convert_model] ✗ 转换失败 (exit=$CONV_RC), 日志尾部:"
    tail -20 "$CONV_LOG"
    echo "[convert_model] 完整日志: $CONV_LOG"
    exit 1
fi
