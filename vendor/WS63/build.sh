#!/bin/bash
set -ex

cur_path=$(cd $(dirname $0) && pwd -P)
echo $cur_path
hiSpark_ai_path="$cur_path/../.."
if [ $# -lt 1 ]; then
    echo "Usage: $0 <bisheng_compiler_path> [--daily]"
    exit 1
fi
bisheng_path=$1
shift
is_daily=false
target="all"

while [ $# -gt 0 ]; do
    if [ "$1" = "--target" ]; then
        if [ $# -lt 2 ]; then
            echo "Error: --target requires an argument (linux, windows, or all)"
            exit 1
        fi
        target="$2"
        if [ "$target" != "linux" ] && [ "$target" != "windows" ] && [ "$target" != "all" ]; then
            echo "Error: --target must be linux, windows, or all"
            exit 1
        fi
        shift 2
    elif [ "$1" = "--daily" ]; then
        is_daily=true
        shift
    else
        echo "Error: Unknown option: $1"
        echo "Usage: $0 <bisheng_compiler_path> [--target <linux|windows|all>] [--daily]"
        exit 1
    fi
done

echo "Configuration:"
echo "  bisheng_path: $bisheng_path"
echo "  target: $target"
echo "  is_daily: $is_daily"

# 编译mindspore-lite

export MSLITE_ENABLE_MICRO=ON
export MSLITE_ENABLE_INT8=ON
export MSLITE_ENABLE_TRAIN=OFF
export MSLITE_ENABLE_TESTCASES=OFF
export MSLITE_TARGET_RISCV=ON
export HISPARK_RISCV_TOOLCHAIN_PATH="${bisheng_path}/"

# 根据target参数决定执行哪些平台
build_linux=false
build_windows=false

if [ "$target" = "linux" ]; then
    build_linux=true
elif [ "$target" = "windows" ]; then
    build_windows=true
elif [ "$target" = "all" ]; then
    build_linux=true
    build_windows=true
fi

# 构建Linux平台
if [ "$build_linux" = true ]; then
    pushd ${hiSpark_ai_path}/src/mindspore-lite
    echo "========== Building for Linux =========="
    bash build.sh -I x86_64 -j8
    popd
    pushd ${hiSpark_ai_path}
    if [ ! -d "sdk" ]; then
        rm -rf "sdk"
        git clone https://gitcode.com/HiSpark/fbb_ws63.git sdk
    fi
    popd

    pushd ${cur_path}
    if [ "$is_daily" = true ]; then
        bash ai_daily.sh --daily || exit 1
    else 
        bash ai_daily.sh || exit 1
    fi
    popd
fi

# 构建Windows平台
if [ "$build_windows" = true ]; then
    echo "========== Building for Windows =========="
    pushd ${hiSpark_ai_path}/src/mindspore-lite
    cp output/*.tar.gz ${hiSpark_ai_path}/archives/ 2>/dev/null || true
    # 执行构建
    bash cross_build_windows.sh || { echo "Build for Win64 failed!"; exit 1; }
    if ls output/*.tar.gz 1>/dev/null 2>&1; then
        mkdir -p ${hiSpark_ai_path}/archives
        cp output/*.tar.gz ${hiSpark_ai_path}/archives/
    fi
    popd
fi

exit 0