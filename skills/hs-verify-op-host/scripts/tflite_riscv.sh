#!/bin/bash
# TFLite RISC-V driver (hs-verify-op-host Step R2/R3). Same as ONNX riscv but --fmk=TFLITE + NHWC.
# fp32 vs INT8 differ ONLY by {CFG_FILE}. Comparison done in Python by run_all_cases.py.
# Placeholders {MSLITE_PKG} {MODEL_FILE} {CFG_FILE} {INPUT_FILE}.
export GLOG_v=3
export MSLITE_PKG="{MSLITE_PKG}"
export LD_LIBRARY_PATH="$MSLITE_PKG/tools/converter/lib:$MSLITE_PKG/runtime/lib:$LD_LIBRARY_PATH"

rm -rf tflite_riscv_micro
"$MSLITE_PKG/tools/converter/converter/converter_lite" --fmk=TFLITE \
    --modelFile="{MODEL_FILE}" --outputFile=./tflite_riscv_micro \
    --configFile="{CFG_FILE}" {ENCRYPTION_ARG} \
    --inputDataFormat=NHWC --outputDataFormat=NHWC \
    || { echo "[ERR] converter_lite failed"; exit 1; }

cd tflite_riscv_micro || { echo "[ERR] no tflite_riscv_micro dir"; exit 1; }

sed -i "s|^set(CMAKE_C_COMPILER.*|set(OP_LIB $MSLITE_PKG/tools/codegen/lib/cpu/libnnacl.a)|"        CMakeLists.txt
sed -i "s|^set(CMAKE_CXX_COMPILER.*|set(WRAPPER_LIB $MSLITE_PKG/tools/codegen/lib/cpu/libwrapper.a)|" CMakeLists.txt
sed -i "s|^set(CMAKE_C_FLAGS.*|set(MS_ROOT_DIR $MSLITE_PKG)|"   CMakeLists.txt
sed -i "s|^set(CMAKE_CXX_FLAGS.*|set(PKG_PATH $MSLITE_PKG)|"    CMakeLists.txt
printf '\nfile(GLOB BENCH_SRC ./benchmark/*.c)\nadd_executable(benchmark ${BENCH_SRC})\ntarget_link_libraries(benchmark PRIVATE micro_runtime)\n' >> CMakeLists.txt

sed -i -E "s@^([[:space:]]*)element_num = element_num > (MAX_ELEMENT_NUM|10) \?.*@\1// print cap disabled by hs-verify-op-host harness@" benchmark/benchmark.c 2>/dev/null
sed -i -E "s@^([[:space:]]*)const size_t MAX_ELEMENT_NUM = 10;@\1// MAX_ELEMENT_NUM unused after print cap lifted@" benchmark/benchmark.c 2>/dev/null

rm -rf build && mkdir build && cd build || { echo "[ERR] mkdir build"; exit 1; }
cmake -DPKG_PATH="$MSLITE_PKG" -DCMAKE_BUILD_TYPE=Debug .. || { echo "[ERR] cmake failed"; exit 1; }
make -j"$(nproc)" || { echo "[ERR] make failed"; exit 1; }

./benchmark "{INPUT_FILE}"
