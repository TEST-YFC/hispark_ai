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

# 设置 converter 环境
export PATH="$MSLITE_PKG/tools/converter/converter:$PATH"
export LD_LIBRARY_PATH="$MSLITE_PKG/tools/converter/lib:$LD_LIBRARY_PATH"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 执行转换
echo "[convert_model] 执行转换..."
converter_lite \
    --fmk=ONNX \
    --modelFile="$MODEL_FILE" \
    --outputFile="$OUTPUT_DIR" \
    --configFile="$CONFIG_FILE" \
    --inputDataFormat=NCHW \
    --encryption=false \
    --outputDataFormat=NCHW

echo "[convert_model] 转换完成"

# 检查产物
GEN_FILES=$(find "$OUTPUT_DIR" -type f | wc -l)
echo "[convert_model] 产物文件数: $GEN_FILES"
echo "[convert_model] 产物大小: $(du -sh "$OUTPUT_DIR" | cut -f1)"
