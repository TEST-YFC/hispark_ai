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
is_daily=false
if [ "$2" = "--daily" ]; then
    is_daily=true
fi

# 编译mindspore-lite
# cd ${hiSpark_ai_path} 
# git submodule update --init --remote --progress src/mindspore-lite
pushd ${hiSpark_ai_path}/src/mindspore-lite
export MSLITE_ENABLE_MICRO=ON
export MSLITE_ENABLE_INT8=ON
export MSLITE_ENABLE_TRAIN=OFF
export MSLITE_ENABLE_TESTCASES=OFF
export MSLITE_TARGET_RISCV=ON
export HISPARK_RISCV_TOOLCHAIN_PATH="${bisheng_path}/"
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

exit 0