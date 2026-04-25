#!/bin/bash
set -ex
set -o pipefail

CUR_DIR=$(cd $(dirname $0) && pwd -P)
hispark_ai_path="$CUR_DIR/../.."
is_daily=false
if [ "$1" = "--daily" ]; then
    is_daily=true
fi

export PATH=~:$PATH
export SDK_PATH=$hispark_ai_path/sdk/src
export ADAPTOR_PATH=$hispark_ai_path/src/adaptor
export GLOG_v=2
export ENABLE_AI_CUSTOM_SAMPLE=y

MODEL_PATH=$CUR_DIR/model
CFG_PATH=$CUR_DIR/config
MICRO_PATH=$CUR_DIR/micro
OUTPUT_PATH=$CUR_DIR/output
RESULT_PATH=$hispark_ai_path/archives
compressed_file=$(find "$hispark_ai_path/src/mindspore-lite/output" -maxdepth 1 -type f -name "mindspore-lite-*-linux-x64.tar.gz" | head -n 1)

if [ -n "$compressed_file" ]; then
    tar -xzf "$compressed_file" -C "$hispark_ai_path/src/mindspore-lite/output/"
    dir_name=$(basename "$compressed_file" .tar.gz)
    mindspore_lite_path="$hispark_ai_path/src/mindspore-lite/output/$dir_name"
else
    echo "build fail cause: No mindspore-lite-*-linux-x64.tar.gz file found in $hispark_ai_path/src/mindspore-lite/output/"
    exit 1
fi

sample_path=$hispark_ai_path/src/samples/oh/lenet5
sample_path_1=$hispark_ai_path/src/samples/oh/gru

export PATH=$mindspore_lite_path/tools/converter/converter:$PATH
export LD_LIBRARY_PATH=$mindspore_lite_path/runtime/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$mindspore_lite_path/tools/converter/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$SDK_PATH/../gcc_lib:$LD_LIBRARY_PATH

for dir in MICRO_PATH RESULT_PATH; do
    if [ -d "${!dir}" ]; then
        echo "Removing existing $dir: ${!dir}"
        rm -rf "${!dir}"
    fi
    mkdir -p "${!dir}"
done

compiling_micro() {
        # Compiling Micro
        rm -rf build
        cmake -S . -B build \
                -D OP_LIB="$mindspore_lite_path/tools/codegen/lib/riscv/libnnacl.a" \
                -D WRAPPER_LIB="$mindspore_lite_path/tools/codegen/lib/riscv/libwrapper.a" \
                -D RISCV_TOOLCHAIN_PATH="$SDK_PATH/tools/bin/compiler/riscv/cc_riscv32_musl_105/cc_riscv32_musl/bin" \
                -D PKG_PATH="$mindspore_lite_path"
        cd build
        make -j4

        # Copying a Static Library
        rm -rf $SDK_PATH/middleware/utils/ai_mcu/lib
        mkdir -p $SDK_PATH/middleware/utils/ai_mcu/lib
        cp -rf ./libmicro_runtime.a $SDK_PATH/middleware/utils/ai_mcu/lib
        cp -rf ./src/libnet.a $SDK_PATH/middleware/utils/ai_mcu/lib
}

process_quantized_sample() {
    local model=$1
    local sample_model_path=$2
    local quant_cfg_path=$3
    local model_dir="$MICRO_PATH/${model}_fp32_quant"
    # Create directory and convert model
    rm -rf "$model_dir"
    mkdir -p "$model_dir"
    if converter_lite --fmk=ONNX --modelFile="$sample_model_path" \
        --outputFile="$model_dir" --configFile="$quant_cfg_path/micro_quant.cfg" \
        --inputDataFormat=NCHW --encryption=false --outputDataFormat=NCHW; then
        # Compile micro
        cd "$model_dir" || exit 1
        compiling_micro
        pushd "$quant_cfg_path"
        ./build.sh
        popd
        cp "${quant_cfg_path}/output/ws63-ai-liteos-sample.fwpkg" \
            "${RESULT_PATH}/ws63-ai-liteos_${model}_WS63_${model}.fwpkg"
    else
        if [ "$is_daily" = false ]; then
            exit 1
        fi
    fi
}

build_save()
{
    local model=$1
    local quantized=$2
    # Copy Output fwpkg
    if [ "$quantized" -eq 1 ]; then
        temp='onnx_quant'
    elif [ "$quantized" -eq 0 ]; then
        temp='default'
    elif [ "$quantized" -eq 2 ]; then
        temp='tflite_quant'
    fi
    cp "${sample_path}/output/ws63-ai-liteos-sample.fwpkg" \
        "${RESULT_PATH}/ws63-ai-liteos_${temp}_WS63_${model}.fwpkg"
    files=($(find "$MODEL_PATH/$model/" -type f -name "output*.npy"))
    # Check the number of documents
    if [ ${#files[@]} -eq 0 ]; then
        echo "Error: No output*.npy files found in $MODEL_PATH/$model/" >&2
        exit 1
    elif [ ${#files[@]} -eq 1 ]; then
        # Only one file → Copy and rename it to {model}.npy
        cp -v "${files[0]}" "${RESULT_PATH}/ws63-ai-liteos_${temp}_WS63_${model}.npy"
    else
        # Multiple files → Copy entire directory structure
        first_file=$(find "$MODEL_PATH/$model/" -type f -name "output_0.npy" | head -1)
        if [ -n "$first_file" ]; then
            cp -v "$first_file" "${RESULT_PATH}/ws63-ai-liteos_${temp}_WS63_${model}.npy"
        fi
    fi
}

process_fp32() {
    local model=$1
    local output_name=$2
    local model_name=$3
    local bin_basename=$4

    local model_dir="$MICRO_PATH/${model}_fp32"
    start_time=$(date +%s)
    echo "Processing non-quantized model: $model"
    
    # Create directory and convert model
    rm -rf "$model_dir"
    mkdir -p "$model_dir"
    if converter_lite --fmk=ONNX --modelFile="$MODEL_PATH/$model/$model.onnx" \
        --outputFile="$model_dir" --configFile="$CFG_PATH/micro_default.cfg" \
        --inputDataFormat=NCHW --encryption=false --outputDataFormat=NCHW; then
    
        cd "$model_dir" || exit 1
        compiling_micro
        
        cp "$MODEL_PATH/$model/ai_main.c" "$sample_path/src/ai_main.c"
        pushd "$sample_path"
        ./build.sh
        popd
        build_save "$model" 0
    else
        if [ "$is_daily" = false ]; then
            exit 1
        fi
    fi
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo "######### Build target:ws63-ai-liteos_default_WS63_$model success"
    echo "ws63-ai-liteos_default_WS63_$model takes ${duration} s"

}

# Function to perform quantized operations
process_quantized() {
    local model=$1
    local output_name=$2
    local model_name=$3
    local bin_basename=$4
    local model_dir="$MICRO_PATH/${model}_fp32_quant"
    local quant_cfg="$CFG_PATH/micro_${model}_quant.cfg"
    start_time=$(date +%s)
    # Check if quant config exists
    if [ ! -f "$quant_cfg" ]; then
        echo "Quantization config not found: $quant_cfg"
        return
    fi
    echo "Processing quantized model: $model"
    
    # Create directory and convert model
    rm -rf "$model_dir"
    mkdir -p "$model_dir"
    if converter_lite --fmk=ONNX --modelFile="$MODEL_PATH/$model/$model.onnx" \
        --outputFile="$model_dir" --configFile="$quant_cfg" \
        --inputDataFormat=NCHW --encryption=false --outputDataFormat=NCHW; then
    
        # Compile micro
        cd "$model_dir" || exit 1
        compiling_micro
        
        cp "$MODEL_PATH/$model/ai_main_quant.c" "$sample_path/src/ai_main.c"
        pushd "$sample_path"
        ./build.sh
        popd
        build_save "$model" 1
    else
        if [ "$is_daily" = false ]; then
            exit 1
        fi
    fi
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo "######### Build target:ws63-ai-liteos_onnx_quant_WS63_$model success"
    echo "ws63-ai-liteos_onnx_quant_WS63_$model takes ${duration} s"
}

process_tflite() {
    local model=$1
    local output_name=$2
    local model_name=$3
    local bin_basename=$4
    local model_dir="$MICRO_PATH/${model}_fp32_tflite"
    start_time=$(date +%s)
    echo "Processing quantized model: $model"
    
    # Create directory and convert model
    rm -rf "$model_dir"
    mkdir -p "$model_dir"
    if converter_lite --fmk=TFLITE --modelFile="$MODEL_PATH/$model/${model%_tf}.tflite" \
        --outputFile="$model_dir" --configFile="$CFG_PATH/micro_default.cfg" \
        --inputDataFormat=NHWC --encryption=false --outputDataFormat=NHWC; then
    
        # Compile micro
        cd "$model_dir" || exit 1
        compiling_micro

        cp "$MODEL_PATH/$model/ai_main.c" "$sample_path/src/ai_main.c"
        pushd "$sample_path"
        ./build.sh
        popd
        build_save "$model" 0
    else
        if [ "$is_daily" = false ]; then
            exit 1
        fi
    fi
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo "######### Build target:ws63-ai-liteos_default_WS63_$model success"
    echo "ws63-ai-liteos_default_WS63_$model takes ${duration} s"
    
}

process_quantized_tflite() {
    local model=$1
    local output_name=$2
    local model_name=$3
    local bin_basename=$4
    local model_dir="$MICRO_PATH/${model}_fp32_quant"
    local quant_cfg="$CFG_PATH/micro_${model}_quant.cfg"
    start_time=$(date +%s)
    # Check if quant config exists
    if [ ! -f "$quant_cfg" ]; then
        echo "Quantization config not found: $quant_cfg"
        return
    fi
    echo "Processing quantized model: $model"
    
    # Create directory and convert model
    rm -rf "$model_dir"
    mkdir -p "$model_dir"
    if converter_lite --fmk=TFLITE --modelFile="$MODEL_PATH/$model/${model%_tf}.tflite" \
        --outputFile="$model_dir" --configFile="$quant_cfg" \
        --inputDataFormat=NHWC --encryption=false --outputDataFormat=NHWC; then

        # Compile micro
        cd "$model_dir" || exit 1
        compiling_micro
        
        cp "$MODEL_PATH/$model/ai_main_quant.c" "$sample_path/src/ai_main.c"
        pushd "$sample_path"
        ./build.sh
        popd
        build_save "$model" 2
    else
        if [ "$is_daily" = false ]; then
            exit 1
        fi
    fi
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo "######### Build target:ws63-ai-liteos_tflite_quant_WS63_$model success"
    echo "ws63-ai-liteos_tflite_quant_WS63_$model takes ${duration} s"
}


main_daily() {
    # Process each model in MODEL_PATH
    for model_dir in "$MODEL_PATH"/*; do
        if [ -d "$model_dir" ]; then
            model=$(basename "$model_dir")
            echo "Found model: $model"
            if [[ "$model" == *"_tf"* ]]; then
                process_tflite "$model" "" "" "" | tee "${RESULT_PATH}/build-ws63-ai-liteos_default_WS63_${model}.log" 2>&1 || true
                process_quantized_tflite "$model" "" "" "" | tee "${RESULT_PATH}/build-ws63-ai-liteos_tflite_quant_WS63_${model}.log" 2>&1 || true
            else
                # Process non-quantized version
                process_fp32 "$model" "" "" "" | tee "${RESULT_PATH}/build-ws63-ai-liteos_default_WS63_${model}.log" 2>&1 || true
                # Process quantized version
                process_quantized "$model" "" "" "" | tee "${RESULT_PATH}/build-ws63-ai-liteos_onnx_quant_WS63_${model}.log" 2>&1 || true

            fi
        fi
    done
    cp "$hispark_ai_path/ai_main_temp.c" "$sample_path/src/ai_main.c"
    sample
    echo "All models processed successfully"
}

main_build() {
    for model_dir in "$MODEL_PATH"/*; do
        if [ -d "$model_dir" ]; then
            model=$(basename "$model_dir")
            echo "Found model: $model"
            if ! [[ "$model" =~ ^(NeuralNetwork|MathModel)(_tf)?$ ]]; then
                echo "Skipping model: $model (not in allowed list)"
                continue
            fi
            if [[ "$model" == *"_tf"* ]]; then
                process_tflite "$model" "" "" "" | tee "${RESULT_PATH}/build-ws63-ai-liteos_default_WS63_${model}.log" 2>&1
                process_quantized_tflite "$model" "" "" "" | tee "${RESULT_PATH}/build-ws63-ai-liteos_tflite_quant_WS63_${model}.log" 2>&1
            else
                # Process non-quantized version
                process_fp32 "$model" "" "" "" | tee "${RESULT_PATH}/build-ws63-ai-liteos_default_WS63_${model}.log" 2>&1
                # Process quantized version
                process_quantized "$model" "" "" "" | tee "${RESULT_PATH}/build-ws63-ai-liteos_onnx_quant_WS63_${model}.log" 2>&1

            fi
        fi
    done
    cp "$hispark_ai_path/ai_main_temp.c" "$sample_path/src/ai_main.c"
    sample
    echo "All models processed successfully"
}

sample() {
    #let5
    {
        pushd ${sample_path}
        python scripts/preproc_mnist_data.py \
            --orig_path ./data \
            --train_path ./data/train_data \
            --test_path ./data/test_data \
            --train_file_format bin \
            --test_file_format all \
            --test_data_type float32
        cfg_file="${sample_path}/micro_quant.cfg"
        cat > "$cfg_file" << EOF
[micro_param]
enable_micro=true
target=RISCV
support_parallel=false

[common_quant_param]
quant_type=FULL_QUANT
bit_num=8

[data_preprocess_param]
calibrate_path=Input3:${sample_path}/data/train_data/bin
calibrate_size=60000
input_type=BIN

[full_quant_param]
activation_quant_method=MAX_MIN
bias_correction=true
enable_all_ops=false
EOF
        popd
        start_time=$(date +%s)
        process_quantized_sample "lenet5" "${sample_path}/model/mnist-12.onnx" "$sample_path"
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        
        echo "######### Build target:ws63-ai-liteos_lenet5_WS63_lenet5 success"
        echo "ws63-ai-liteos_lenet5_WS63_lenet5 takes ${duration} s"
    } | tee "${RESULT_PATH}/build-ws63-ai-liteos_lenet5_WS63_lenet5.log" 2>&1

    #gru
    {
        pushd ${sample_path_1}
        python scripts/preproc_wav_data.py \
            --data_root_dir ./data/origin_data \
            --quant_data_dir ./data/quant_data \
            --validation_data_dir ./data/validation_data \
            --onnx_model_path ./model/GRU_S_STREAM.onnx \
            --sample_num 50 --fp16 true
        cfg_file="${sample_path_1}/micro_quant.cfg"
        quant_data_dir="${sample_path_1}/data/quant_data/quant_mfcc_input"
        hidden_states_dir="${sample_path_1}/data/quant_data/quant_hidden_states"
        # 计算两个目录的文件数量
        mfcc_count=$(find "$quant_data_dir" -type f | wc -l)
        hidden_count=$(find "$hidden_states_dir" -type f | wc -l)
        echo "mfcc_input count: $mfcc_count"
        echo "hidden_states count: $hidden_count"
        # 取最小值作为校准数量
        calibrate_size=$(( mfcc_count < hidden_count ? mfcc_count : hidden_count ))
        echo "calibrate_size: $calibrate_size"

        cat > "$cfg_file" << EOF
[micro_param]
enable_micro=true
target=RISCV
support_parallel=false

[common_quant_param]
quant_type=FULL_QUANT
bit_num=8

[data_preprocess_param]
calibrate_path=mfcc_input:${quant_data_dir},hidden_states:${hidden_states_dir}
calibrate_size=${calibrate_size}
input_type=BIN

[full_quant_param]
activation_quant_method=MAX_MIN
bias_correction=true
enable_all_ops=false
EOF
        popd

        start_time=$(date +%s)
        process_quantized_sample "gru" "${sample_path_1}/model/GRU_S_STREAM.onnx" "$sample_path_1"
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        
        echo "######### Build target:ws63-ai-liteos_gru_WS63_gru success"
        echo "ws63-ai-liteos_gru_WS63_gru takes ${duration} s"
    } | tee "${RESULT_PATH}/build-ws63-ai-liteos_gru_WS63_gru.log" 2>&1
    echo "All sample models have been processed."
}

cp "$sample_path/src/ai_main.c" "$hispark_ai_path/ai_main_temp.c"
if [ "$is_daily" = true ]; then
    main_daily
else
    main_build
fi
exit 0