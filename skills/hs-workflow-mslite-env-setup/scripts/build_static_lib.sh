#!/bin/bash
# micro_gen 静态库编译脚本 (RISC-V 交叉编译)
# 用法: bash scripts/build_static_lib.sh <micro_gen_dir>

set -e

if [ -z "$1" ]; then
    echo "用法: bash build_static_lib.sh <micro_gen_dir>"
    echo "示例: bash build_static_lib.sh src/samples/oh/lenet5/output/micro_gen"
    exit 1
fi

GEN_DIR=$(realpath "$1")

if [ -z "$MSLITE_PKG" ]; then
    echo "[build_static_lib] 错误: 请先 source scripts/setup_env.sh"
    exit 1
fi

RISCV_TOOLCHAIN="$BISHENG_ROOT/bin/riscv32"
RISCV_SYSROOT="$BISHENG_ROOT/riscv32-elf"
BUILD_DIR="$GEN_DIR/build"

echo "[build_static_lib] micro_gen: $GEN_DIR"
echo "[build_static_lib] 工具链:   $RISCV_TOOLCHAIN"
echo "[build_static_lib] sysroot:   $RISCV_SYSROOT"
echo "[build_static_lib] 编译目录: $BUILD_DIR"

# 补丁: CMakeLists.txt 添加 sysroot
if ! grep -q "sysroot" "$GEN_DIR/CMakeLists.txt" 2>/dev/null; then
    echo "[build_static_lib] 补丁: CMakeLists.txt 添加 --sysroot"
    sed -i 's|set(CMAKE_C_FLAGS "-march=rv32imafc|set(CMAKE_C_FLAGS "--sysroot=${RISCV_SYSROOT} -march=rv32imafc|' "$GEN_DIR/CMakeLists.txt"
    sed -i 's|set(CMAKE_CXX_FLAGS "-march=rv32imafc|set(CMAKE_CXX_FLAGS "--sysroot=${RISCV_SYSROOT} -march=rv32imafc|' "$GEN_DIR/CMakeLists.txt"
fi

# 补丁: allocator.h 添加 stdatomic.h
if ! grep -q "stdatomic.h" "$GEN_DIR/src/allocator.h" 2>/dev/null; then
    echo "[build_static_lib] 补丁: allocator.h 添加 stdatomic.h"
    sed -i '/^#include <stddef.h>/a #include <stdatomic.h>' "$GEN_DIR/src/allocator.h"
fi

# CMake 配置
echo "[build_static_lib] CMake 配置..."
rm -rf "$BUILD_DIR"
cmake -S "$GEN_DIR" -B "$BUILD_DIR" \
    -D OP_LIB="$MSLITE_PKG/tools/codegen/lib/riscv/libnnacl.a" \
    -D WRAPPER_LIB="$MSLITE_PKG/tools/codegen/lib/riscv/libwrapper.a" \
    -D RISCV_TOOLCHAIN_PATH="$RISCV_TOOLCHAIN" \
    -D RISCV_SYSROOT="$RISCV_SYSROOT" \
    -D PKG_PATH="$MSLITE_PKG"

# Make 编译
JOBS=${JOBS:-$(nproc)}
echo "[build_static_lib] Make 编译 (j=$JOBS)..."
cd "$BUILD_DIR"
make -j$JOBS

# 验证产物
echo "[build_static_lib] 产物:"
find "$BUILD_DIR" -name "*.a" -type f -exec ls -lh {} \;
echo "[build_static_lib] 编译完成"
