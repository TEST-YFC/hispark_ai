#!/bin/bash
set -ex

cur_path=$(cd $(dirname $0) && pwd -P)
echo $cur_path
hiSpark_ai_path="$cur_path/../.."
if [ $# -lt 1 ]; then
    echo "Usage: $0 <bisheng_compiler_path> [--arm-path <arm_compiler_path>] [--target <linux|windows|all>] [--daily] [--daily-num <num>] [--cache] [--j <num>]"
    exit 1
fi
bisheng_path=$1
shift
is_daily=false
daily_num=""
target="all"
arm_path=""
cache=false
j_num=""

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
    elif [ "$1" = "--arm-path" ]; then
        if [ $# -lt 2 ]; then
            echo "Error: --arm-path requires an argument"
            exit 1
        fi
        arm_path="$2"
        shift 2
    elif [ "$1" = "--daily" ]; then
        is_daily=true
        shift
    elif [ "$1" = "--cache" ]; then
        cache=true
        shift
    elif [ "$1" = "--daily-num" ]; then
        if [ $# -lt 2 ]; then
            echo "Error: --daily-num requires an argument"
            exit 1
        fi
        daily_num="$2"
        shift 2
    elif [ "$1" = "--j" ]; then
        if [ $# -lt 2 ]; then
            echo "Error: --j requires an argument"
            exit 1
        fi
        j_num="$2"
        shift 2
    else
        echo "Error: Unknown option: $1"
        echo "Usage: $0 <bisheng_compiler_path> [--arm-path <arm_compiler_path>] [--target <linux|windows|all>] [--daily] [--daily-num <num>] [--cache] [--j <num>]"
        exit 1
    fi
done

echo "Configuration:"
echo "  bisheng_path: $bisheng_path"
echo "  arm_path: $arm_path"
echo "  target: $target"
echo "  is_daily: $is_daily"
echo "  daily_num: $daily_num"
echo "  cache: $cache"
echo "  j_num: $j_num"

# cache为true时为mindspore-lite构建脚本追加增量编译参数-i，否则全量编译
if [ "$cache" = true ]; then
    cache_flag="-i"
else
    cache_flag=""
fi

# 并行编译任务数：外部--j传入时使用指定值，否则默认使用核数
if [ -n "$j_num" ]; then
    j_flag="-j${j_num}"
else
    j_flag="-j$(nproc)"
fi

# 编译mindspore-lite

export MSLITE_ENABLE_MICRO=ON
export MSLITE_ENABLE_INT8=ON
export MSLITE_ENABLE_TRAIN=OFF
export MSLITE_ENABLE_TESTCASES=OFF
export MSLITE_ENABLE_GITEE_MIRROR=ON
export MSLITE_TARGET_RISCV=ON
export HISPARK_RISCV_TOOLCHAIN_PATH="${bisheng_path}/"
export HISPARK_ARM_TOOLCHAIN_PATH="${arm_path}/"

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
    if [ -d build/riscv ] || [ -d build/arm ]; then
        rm -rf build/riscv build/arm
        echo "Removed stale cross-build dirs: build/riscv build/arm"
    fi
    bash build.sh -I x86_64 ${j_flag} ${cache_flag}
    popd
    pushd ${hiSpark_ai_path}
    if [ -d "sdk" ]; then
        rm -rf "sdk"
        git clone --depth 1 https://gitcode.com/HiSpark/fbb_ws63.git sdk
    fi
    popd

    pushd ${cur_path}
    if [ "$is_daily" = true ]; then
        if [ -n "$daily_num" ]; then
            bash ai_daily.sh --daily --daily-num "$daily_num" || exit 1
        else
            bash ai_daily.sh --daily || exit 1
        fi
    else 
        bash ai_daily.sh || exit 1
    fi
    popd
fi

# 构建Windows平台
if [ "$build_windows" = true ]; then
    echo "========== Building for Windows =========="
    pushd ${hiSpark_ai_path}/src/mindspore-lite
    if [ -d build/riscv ] || [ -d build/arm ]; then
        rm -rf build/riscv build/arm
        echo "Removed stale cross-build dirs: build/riscv build/arm"
    fi
    cp output/*.tar.gz ${hiSpark_ai_path}/archives/ 2>/dev/null || true
    # 执行构建
    bash build_cross_win64.sh ${cache_flag} || { echo "Build for Win64 failed!"; exit 1; }
    if ls output/*.tar.gz 1>/dev/null 2>&1; then
        mkdir -p ${hiSpark_ai_path}/archives
        cp output/*.tar.gz ${hiSpark_ai_path}/archives/
    fi
    popd
fi

exit 0