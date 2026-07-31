# HiSpark AI Samples仓

## Sample案例说明
HiSpark.AI提供了以下Sample供开发参考：
| 平台 | 应用 | AI功能 |
| ---- | ---- | ---- |
| ws63 | LeNet-5手写数字图像识别 | MindSpore Lite Micro工具链量化，转换，编译，SDK集成 |
| ws63 | Gru-S音频固定词识别 | MindSpore Lite Micro工具链量化，转换，编译，SDK集成 |
| 3322 | LeNet-5手写数字图像识别 | CANN工具链量化，转换，编译，SDK集成 |
| 3322 | Gru-S音频固定词识别 | CANN工具链量化，转换，编译，SDK集成 |
| 1156 | LeNet-5手写数字图像识别 | CANN工具链转换，编译，SDK集成 |
| 1156 | Gru-S音频固定词识别 | CANN工具链转换，编译，SDK集成 |


## **HiSpark.AI CPU平台快速入门指南**

- **准备hispark_ai工具链**
获取MSLite工具链，或根据上述源码编译指南进行编译。MSLite安装包目录结构如下：
    ```
    ├── runtime
    │   ├── include
    │   │   ├── api
    │   │   ├── c_api
    │   │   └── ...
    │   ├── lib
    │   │   ├── libmindspore-lite.so
    │   │   └── ...
    │   └── third_party
    └── tools
        ├── benchmark
        ├── codegen
        │   ├── include
        │   │   ├── nnacl_c
        │   │   └── wrapper
        │   └── lib
        │       ├── cpu
        │       └── riscv
        └── converter
            ├── converter
            │   └── converter_lite
            ├── include
            │   ├── api
            │   └── ...
            ├── lib
            │   ├── libmindspore_converter.so
            │   ├── libmindspore_core.so
            │   └── ...
            └── third_party
                └── proto
    ```

- **准备待部署模型与数据**
  - 准备好待部署模型。可直接使用 HiSpark.AI LeNet-5以及Gru Sample中的mnist-12.onnx以及GRU_S_STREAM.onnx。
  - 准备好量化数据。**无需量化可跳过此步骤。** 准备一个文件夹，将float32格式的量化数据存储为.bin格式，可直接使用 HiSpark.AI LeNet-5以及Gru Sample中的 运行数据预处理脚本之后的npy_data文件夹。

- **准备SDK**
  - 从开源社区下载fbb_ws63的源码
    ```
      git clone https://gitee.com/HiSpark/fbb_ws63.git
    ```

- **准备Samples**
  进入sample一级目录，如LeNet-5就进入{hispark_ai_root}/src/samples/OH/Lenet5目录，而Gru就进入{hispark_ai_root}/src/samples/OH/Gru目录。Sample目录结构如下：
    ```
    {sample_path}
    ├── build.sh
    ├── CMakeLists.txt
    ├── model
    │   ├── xxx.onnx
    │   └── README.md
    ├── README.md
    ├── scripts
    │   ├── preproc_xxx_data.py
    │   └── README.md
    └── src
        ├── ai_main.c
        ├── ai_main.h
        └── CMakeLists.txt
    ```

- **模型编译**
  - 使用MSLite包中带的converter_lite工具进行模型转换，生成目标代码
    ```
     # mslite_pkg_path变量为解压的HiSpark.AI MSLite压缩包路径，一级文件夹名称为mindspore-{package_item}-lite-{version}-linux-64
     # model_path为原始模型路径，如mnist-12.onnx
     # generate_code_path为生成代码路径
     # cfg_path为配置文件路径
     export PATH=${mslite_pkg_path}/tools/converter/converter:$PATH
     export LD_LIBRARY_PATH=${mslite_pkg_path}/tools/converter/lib:$LD_LIBRARY_PATH
     converter_lite --fmk=ONNX --modelFile={model_path} --outputFile={generate_code_path} --configFile={cfg_path} --inputDataFormat=NCHW --outputDataFormat=NCHW
    ```
    其中cfg_path所配置的文件内容如下：
    ```
    [micro_param]
    enable_micro=true
    target=RISCV
    support_parallel=false
    ```
  - 自动代码生成的目录如下
    ```
    {generate_code_path}
    ├── benchmark
    ├── CMakeLists.txt
    ├── include
    │   ├── model_handle.h
    │   └── ...
    └── src
        ├── allocator.c
        ├── allocator.h
        ├── CMakeLists.txt
        ├── context.c
        ├── context.h
        ├── model0
        │   ├── model0.c
        │   ├── net0.c
        │   ├── net0.h
        │   ├── weight0.c
        │   └── weight0.h
        ├── model.c
        ├── model.h
        ├── net.cmake
        ├── tensor.c
        └── tensor.h
    ```
  - 静态链接库编译
    ```
    # sdk_path为下载的SDK路径
    # mslite_pkg_path为HiSpark.AI的工具链路径
    # generate_code_path为生成代码路径
    # hcc_version为SDK编译器版本，如cc_riscv32_musl_105
    cd {generate_code_path}
    rm -rf build
    cmake -S . -B build -D OP_LIB="${mslite_pkg_path}/tools/codegen/lib/riscv/libnnacl.a" -D WRAPPER_LIB="${mslite_pkg_path}/tools/codegen/lib/riscv/libwrapper.a" -D RISCV_TOOLCHAIN_PATH="${sdk_path}/src/tools/bin/compiler/riscv/${hcc_version}/cc_riscv32_musl/bin" -D PKG_PATH="${mslite_pkg_path}"
    cd build
    make -j4
    ```
    编译产物存放于build文件夹下，目录结构如下。libnet.a以及libmicro_runtime.a分别放置在build/src路径以及build路径下：
    ```
    {generate_code_path}/build
    ├── CMakeCache.txt
    ├── CMakeFiles
    │   ├── x.xx.x
    │   ├── Makefile2
    │   └── ...
    ├── cmake_install.cmake
    ├── libmicro_runtime.a
    ├── Makefile
    └── src
        ├── CMakeFiles
        ├── cmake_install.cmake
        ├── libnet.a
        └── Makefile
    ```
    将libnet.a以及libmicro_runtime.a拷贝到${sdk_path}/src/middleware/utils/ai_mcu/lib目录下。
    ```
    # sdk_path为SDK的源码目录 (https://gitee.com/HiSpark/fbb_ws63)
    mkdir -p ${sdk_path}/src/middleware/utils/ai_mcu/lib
    cp -rf {generate_code_path}/build/libmicro_runtime.a ${sdk_path}/src/middleware/utils/ai_mcu/lib
    cp -rf {generate_code_path}/build/src/libnet.a ${sdk_path}/src/middleware/utils/ai_mcu/lib
    ```

- **SDK编译**
    配置对应环境变量，在samples下运行build.sh脚本，即可完成编译
    ```
    cd ${sample_path}
    export SDK_PATH=${sdk_path}/src
    export ADAPTOR_PATH=${adaptor_path}
    ./build.sh
    ```
    编译成功后，ws63-ai-liteos-sample.fwpkg镜像文件会生成在${sample_path}/output目录下

- **烧录调试**
    使用BurnTool工具进行ws63-ai-liteos-sample.fwpkg的烧录。
    烧录成功运行后，会看到串口打印的运行成功信息，如Gru下：
    ```
    [AI_MCU] Get Tcxo Time 115 ms
    [AI_MCU] Data size: [48]
    Shape: [1 12 ]
    DataType: 43
    [AI_MCU] Data: [0.95731][0.00266][0.00294][0.00590][0.00286][0.00374][0.00285][0.00685][0.00231][0.00307][0.00654][0.00292]
    [AI_MCU] ai_mcu_sample_process
    ```

## **HiSpark.AI NPU平台快速入门指南**

- **准备CANN工具链**
获取CANN工具链安装包及Dockerfile。构建并运行Docker容器。CANN安装包目录结构如下：
    ```
    ├── CANN-amct-*-linux.x86_64.tar.gz amct.tar.gz
    ├── CANN-compiler-*-linux.x86_64.run compiler.run
    ├── CANN-opp-*-linux.x86_64.run opp.run
    ├── CANN-runtime-*-linux.x86_64.run runtime.run
    └── CANN-toolkit-*-linux.x86_64.run toolkit.run
    ```

- **准备待部署模型与数据**
  - 准备好待部署模型。可直接使用 HiSpark.AI LeNet-5以及Gru Sample中的mnist-12.onnx以及GRU_S_STREAM.onnx。
  - 准备好量化数据。**无需量化可跳过此步骤。** 准备一个文件夹，将float32格式的量化数据存储为.bin格式，可直接使用 HiSpark.AI LeNet-5以及Gru Sample中的 运行数据预处理脚本之后的npy_data文件夹。

- **准备SDK**
  - 从开源社区下载SDK源码

- **准备Samples**
  进入sample一级目录，如LeNet-5就进入{hispark_ai_root}/src/samples/OH/Lenet5目录，而Gru就进入{hispark_ai_root}/src/samples/OH/Gru目录。Sample目录结构如下：
    ```
    {sample_path}
    ├── build.sh
    ├── build_npu.sh
    ├── CMakeLists.txt
    ├── model
    │   ├── xxx.onnx
    │   └── README.md
    ├── README.md
    ├── scripts
    │   ├── preproc_xxx_data.py
    │   └── README.md
    └── src
        ├── ai_main.c
        ├── ai_xxx_main_npu.c
        ├── ai_main.h
        └── CMakeLists.txt
    ```

- **模型量化**
  - 使用CANN工具链中的AMCT工具进行模型量化，具体可参考对应sample README中的量化指南
  ```
  amct_onnx calibration --model "xxx" --save_path "xxx" --input_shape "xxx" --data_dir "xxx" --data_types "xxx" --batch_num xxx
  ```
  参数说明：
  - --model：原始ONNX模型路径
  - --save_path: 量化后模型的存放路径
  - --input_shape: 指定模型输入的shape
  - --data_dir: 与模型匹配的bin格式数据集路径
  - --data_types: 输入数据的类型
  - --batch_num: 训练后量化推理阶段的batch数

  运行成功后生成
  - xxx_fake_quant_model.onnx
  - xxx_deploy_model.onnx

- **模型转换**
  - 使用CANN工具链中的ATC工具进行模型转换，具体可参考对应sample README中的转换指南
  ```
  atc --model=xxx.onnx --framework=5 --output=xxx --input_fp16_nodes="xxx" --output_type=xxx --soc_version=xxx --input_shape="xxx" --mode=xxx
  ```
  参数说明
  - --model: 网络模型文件路径与文件名
  - --framework: 原始网络模型框架类型。5表示ONNX
  - --output：存放转换后的离线模型的路径以及文件名
  - --input_fp16_nodes：指定输入数据类型为FP16的输入节点名称
  - --output_type：指定网络输出数据类型
  - --soc_version：指定模型转换时昇腾AI处理器的版本
  - --input_shape：指定模型输入数据的shape
  - --mode：运行模式

  运行成功后生成
  - mode选择30：xxx.exeom
  - mode选择0：xxx.om

- **3322 SDK编译**
    配置对应环境变量，在具体sample（如gru）下运行build_npu.sh脚本，即可完成编译
    ```
    cd ${sample_path}
    export SDK_PATH=${sdk_path}
    export ADAPTOR_PATH=${adaptor_path}
    bash build_npu.sh 3322
    ```
    编译成功后3322-ai-liteos-sample.fwpkg镜像文件会生成在`${sample_path}/output`目录下

- **1156 SDK编译**
    配置对应环境变量，在具体sample（如gru）下运行build_npu.sh脚本，即可完成编译
    ```
    cd ${sample_path}
    export SDK_PATH=${SDK_PATH}
    export ADAPTOR_PATH=${ADAPTOR_PATH}
    export COMPILER_PATH=${COMPILER_PATH}
    export ACL_HEADER_PATH=${ACL_HEADER_PATH}
    bash ${SAMPLE_PATH}/oh/gru/build_npu.sh 1156
    ```
    编译成功后可执行文件gru1156会生成在`${sample_path}/src/build`路径下，so文件libai_adaptor_tiny.so，在`${ADAPTOR_PATH}/adaptor/npu/build`路径下

- **3322 烧录调试**
    使用BurnTool工具进行3322-ai-liteos-sample.fwpkg的烧录。
    使用Debugkits工具将模型和输入数据上传到单板
    使用sscom工具发送AT^SAMPLE运行，会看到串口打印的运行成功信息，如Gru下：
    ```
    [AI_NPU] the predict cost time 89 ms
    [AI_NPU] Data size: [24]
    [AI_NPU] Shape: [1 12]
    [AI_NPU] DataType: 42
    [AI_NPU] Data: [0.00000][0.01210][0.00000][0.00017][0.00000][0.00000][0.00000][0.00006][0.00000][0.00000][0.00012][0.98779]
    ```

- **1156 上板调试**
    将可执行文件，lib，ko挂载到单板
    重新加载ko，配置lib路径
    执行可执行文件,会看到串口打印的运行成功信息，如Gru下：
    ```
    [AI_NPU] the predict cost time 89 ms
    [AI_NPU] Data size: [24]
    [AI_NPU] Shape: [1 12]
    [AI_NPU] DataType: 42
    [AI_NPU] Data: [0.00000][0.01210][0.00000][0.00017][0.00000][0.00000][0.00000][0.00006][0.00000][0.00000][0.00012][0.98779]
    ```
