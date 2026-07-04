#!/bin/bash
# ONNX RISC-V driver (hs-verify-op Step R2/R3). fp32 vs INT8 differ ONLY by {CFG_FILE}.
# converter (riscv cfg) -> sed-rewrite CMakeLists to host x86 static libs -> build -> run.
# Comparison is done in Python by run_all_cases.py (parses printed tensors), so no calib here.
# Placeholders {MSLITE_PKG} {MODEL_FILE} {CFG_FILE} {INPUT_FILE}.
export GLOG_v=3
export MSLITE_PKG="{MSLITE_PKG}"
export LD_LIBRARY_PATH="$MSLITE_PKG/tools/converter/lib:$MSLITE_PKG/runtime/lib:$LD_LIBRARY_PATH"

rm -rf onnx_riscv_micro
"$MSLITE_PKG/tools/converter/converter/converter_lite" --fmk=ONNX \
    --modelFile="{MODEL_FILE}" --outputFile=./onnx_riscv_micro \
    --configFile="{CFG_FILE}" --encryption=false \
    --inputDataFormat=NCHW --outputDataFormat=NCHW \
    || { echo "[ERR] converter_lite failed"; exit 1; }

cd onnx_riscv_micro || { echo "[ERR] no onnx_riscv_micro dir"; exit 1; }

# Rewrite the RISC-V toolchain vars to host x86 CPU static libs so it builds/runs on the
# build host with no real RISC-V board, then append a benchmark target.
sed -i "s|^set(CMAKE_C_COMPILER.*|set(OP_LIB $MSLITE_PKG/tools/codegen/lib/cpu/libnnacl.a)|"        CMakeLists.txt
sed -i "s|^set(CMAKE_CXX_COMPILER.*|set(WRAPPER_LIB $MSLITE_PKG/tools/codegen/lib/cpu/libwrapper.a)|" CMakeLists.txt
sed -i "s|^set(CMAKE_C_FLAGS.*|set(MS_ROOT_DIR $MSLITE_PKG)|"   CMakeLists.txt
sed -i "s|^set(CMAKE_CXX_FLAGS.*|set(PKG_PATH $MSLITE_PKG)|"    CMakeLists.txt
printf '\nfile(GLOB BENCH_SRC ./benchmark/*.c)\nadd_executable(benchmark ${BENCH_SRC})\ntarget_link_libraries(benchmark PRIVATE micro_runtime)\n' >> CMakeLists.txt

# Disable the generated benchmark's 10-element print cap so the FULL output tensor is
# dumped; otherwise outputs >10 elements are truncated and cosine vs full ref mismatches.
sed -i -E "s@^([[:space:]]*)element_num = element_num > (MAX_ELEMENT_NUM|10) \?.*@\1// print cap disabled by hs-verify-op harness@" benchmark/benchmark.c 2>/dev/null
sed -i -E "s@^([[:space:]]*)const size_t MAX_ELEMENT_NUM = 10;@\1// MAX_ELEMENT_NUM unused after print cap lifted@" benchmark/benchmark.c 2>/dev/null

rm -rf build && mkdir build && cd build || { echo "[ERR] mkdir build"; exit 1; }
cmake -DPKG_PATH="$MSLITE_PKG" -DCMAKE_BUILD_TYPE=Debug .. || { echo "[ERR] cmake failed"; exit 1; }
make -j"$(nproc)" || { echo "[ERR] make failed"; exit 1; }

./benchmark "{INPUT_FILE}"
