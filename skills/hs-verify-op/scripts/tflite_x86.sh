#!/bin/bash
# TFLite x86 fp32 driver (hs-verify-op internal step2/step3/step5). Same as ONNX x86 but --fmk=TFLITE + NHWC.
# Placeholders {MSLITE_PKG} {MODEL_FILE} {CFG_FILE} {INPUT_FILE}.
export GLOG_v=3
export MSLITE_PKG="{MSLITE_PKG}"
export LD_LIBRARY_PATH="$MSLITE_PKG/tools/converter/lib:$MSLITE_PKG/runtime/lib:$LD_LIBRARY_PATH"

rm -rf tflite_x86_micro
"$MSLITE_PKG/tools/converter/converter/converter_lite" --fmk=TFLITE \
    --modelFile="{MODEL_FILE}" --outputFile=./tflite_x86_micro \
    --configFile="{CFG_FILE}" --encryption=false \
    --inputDataFormat=NHWC --outputDataFormat=NHWC \
    || { echo "[ERR] converter_lite failed"; exit 1; }

cd tflite_x86_micro || { echo "[ERR] no tflite_x86_micro dir"; exit 1; }

# Lift the generated benchmark's 10-element print cap so the FULL output tensor is dumped.
# Required: the harness computes cosine in Python from this dump (same as riscv); a truncated
# dump would mismatch the full reference. NOT a result-fudge — it only widens what is printed.
sed -i -E "s@^([[:space:]]*)element_num = element_num > (MAX_ELEMENT_NUM|10) \?.*@\1// print cap lifted by hs-verify-op harness (full-tensor dump for Python-side cosine)@" benchmark/benchmark.c 2>/dev/null
sed -i -E "s@^([[:space:]]*)const size_t MAX_ELEMENT_NUM = 10;@\1// MAX_ELEMENT_NUM unused after print cap lifted@" benchmark/benchmark.c 2>/dev/null

rm -rf build && mkdir build && cd build || { echo "[ERR] mkdir build"; exit 1; }
cmake -DPKG_PATH="$MSLITE_PKG" .. || { echo "[ERR] cmake failed"; exit 1; }
make -j"$(nproc)" || { echo "[ERR] make failed"; exit 1; }

# Run inference only: input + model weights, NO calib file and NO threshold. The benchmark
# must only PRINT the output tensors (PrintTensorHandle) — it must NOT run its built-in
# CompareOutputs. Cosine and the PASS/FAIL threshold are applied uniformly in Python by
# run_all_cases.py, identically to the riscv paths.
./benchmark "{INPUT_FILE}" ../src/model0/net0.bin
