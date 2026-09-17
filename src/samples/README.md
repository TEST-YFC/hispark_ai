# HiSpark AI Samples 仓

## Sample 案例说明

HiSpark.AI 提供了以下 Sample 供开发参考：

| 平台       | 应用               | AI 功能                             |
| -------- | ---------------- | --------------------------------- |
| ws63     | LeNet-5 手写数字图像识别 | MindSpore Lite 工具链量化、转换、编译、SDK 集成 |
| ws63     | Gru-S 音频固定词识别    | MindSpore Lite 工具链量化、转换、编译、SDK 集成 |
| HiDiTing | LeNet-5 手写数字图像识别 | CANN 工具链量化、转换、编译、SDK 集成           |
| HiDiTing | Gru-S 音频固定词识别    | CANN 工具链量化、转换、编译、SDK 集成           |
| 1156     | LeNet-5 手写数字图像识别 | CANN 工具链转换、编译、SDK 集成              |
| 1156     | Gru-S 音频固定词识别    | CANN 工具链转换、编译、SDK 集成              |

## CPU 平台快速入门指南

CPU 平台对应 MindSpore Lite 工具链，适用于 WS63（RISC-V，KB 级 RAM）等超轻量模型部署平台。以下以 WS63 为例说明完整流程。

### 整体流程视图

```
      [ONNX模型]
          │
          ▼
      {MSLite工具链}
          │ (Micro转换)
          ▼
      [C语言工程] + [SDK]
          │
          ▼
      {毕昇编译器}
          │ (静态链接库编译)
          ▼
      [libnet.a + libmicro_runtime.a]
          │
          ▼
      [SDK & sample模块 & adaptor模块]
          │ (SDK编译)
          ▼
      [fwpkg镜像]
          │
          ▼
      [WS63烧录]
          │
          ▼
      [运行推理]
```

### 准备工具链

获取 mindspore-lite 工具链，需参考主 README 的[源码编译](#源码编译)自行编译 mindspore-lite 源码，工具链为编译产物，其目录结构如下：

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

### 准备待部署模型与数据

- 准备好待部署的 ONNX 模型。
- 准备好量化数据。**无需量化可跳过此步骤。** 准备一个文件夹，将 float32 格式的量化数据存储为 `.bin` 格式。

> **提示**：模型可使用下述 Sample 的 ONNX 模型文件，量化数据生成及配置文件可参考对应 Sample 目录下的 README.md。

### 准备 Sample

| Sample   | ${sample_path} |
| -------- | -------------- |
| LeNet-5  | `${hispark_ai_root}/src/samples/oh/lenet5` |
| Gru      | `${hispark_ai_root}/src/samples/oh/gru` |

Sample 目录结构如下：

```
${sample_path}
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

### 准备 SDK

从开源社区下载 fbb_ws63 的源码：

```
git clone https://gitcode.com/HiSpark/fbb_ws63.git
```

### 模型编译

解压 mindspore-lite 编译产物得到 MS Lite 工具链：

```
cd ${hispark_ai_root}/src/mindspore-lite/output
# version 为 mindspore-lite 的版本号，随版本迭代变化，实际压缩包名称格式示例：mindspore-lite-2.8.0-linux-x64.tar.gz
tar zxvf mindspore-lite-${version}-linux-x64.tar.gz
# 将 MS Lite 工具链目录路径保存为 mslite_pkg_path 变量
export mslite_pkg_path=${hispark_ai_root}/src/mindspore-lite/output/mindspore-lite-${version}-linux-x64
```

创建模型转换配置文件（文件名可自定义，如 micro_config.cfg），文件内容如下：

```
[micro_param]
enable_micro=true
target=RISCV
support_parallel=false
```

使用编译产物中的 converter_lite 工具进行模型转换，生成目标代码：

```
# model_path 为原始模型路径，如 mnist-12.onnx
# generate_code_path 为代码生成目标路径
# mslite_pkg_path 为 MS Lite 工具链目录路径
# cfg_path 为模型转换配置文件路径
export PATH=${mslite_pkg_path}/tools/converter/converter:$PATH
export LD_LIBRARY_PATH=${mslite_pkg_path}/tools/converter/lib:$LD_LIBRARY_PATH
converter_lite --fmk=ONNX --modelFile=${model_path} --outputFile=${generate_code_path} --configFile=${cfg_path} --inputDataFormat=NCHW --encryption=false --outputDataFormat=NCHW
```

自动代码生成的目录如下：

```
${generate_code_path}
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

### 静态链接库编译

```
# sdk_path 为 SDK 的源码目录 (https://gitcode.com/HiSpark/fbb_ws63)
# hcc_version 为 SDK 编译器版本，需查看路径 ${sdk_path}/src/tools/bin/compiler/riscv/ 下对应版本，如 cc_riscv32_musl_105

cd ${generate_code_path}
rm -rf build
cmake -S . -B build -D OP_LIB="${mslite_pkg_path}/tools/codegen/lib/riscv/libnnacl.a" -D WRAPPER_LIB="${mslite_pkg_path}/tools/codegen/lib/riscv/libwrapper.a" -D RISCV_TOOLCHAIN_PATH="${sdk_path}/src/tools/bin/compiler/riscv/${hcc_version}/cc_riscv32_musl/bin" -D PKG_PATH="${mslite_pkg_path}"
cd build
make -j4
```

编译产物存放于 build 文件夹下，目录结构如下。libnet.a 以及 libmicro_runtime.a 分别放置在 build/src 路径以及 build 路径下：

```
${generate_code_path}/build
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

将 libnet.a 以及 libmicro_runtime.a 拷贝到 ${sdk_path}/src/middleware/utils/ai_mcu/lib 目录下：

```
# sdk_path 为 SDK 的源码目录 (https://gitcode.com/HiSpark/fbb_ws63)
mkdir -p ${sdk_path}/src/middleware/utils/ai_mcu/lib
cp -rf ${generate_code_path}/build/libmicro_runtime.a ${sdk_path}/src/middleware/utils/ai_mcu/lib
cp -rf ${generate_code_path}/build/src/libnet.a ${sdk_path}/src/middleware/utils/ai_mcu/lib
```

### SDK 编译

配置对应环境变量，在 Sample 目录下运行 build.sh 脚本，即可完成编译：

```
cd ${sample_path}
export SDK_PATH=${sdk_path}/src
export ADAPTOR_PATH=${hispark_ai_root}/src/adaptor
./build.sh
```

编译成功后，`ws63-ai-liteos-sample.fwpkg` 镜像文件会生成在 ${sample_path}/output 目录下。

### 烧录调试

使用 [BurnTool 工具](https://developers.hisilicon.com/cn/developerTool) 进行 `ws63-ai-liteos-sample.fwpkg` 的烧录。烧录成功运行后，会看到串口打印的运行成功信息，Gru 打印如下：

```
[AI_MCU] Get Tcxo Time 115 ms
[AI_MCU] Data size: [48]
Shape: [1 12 ]
DataType: 43
[AI_MCU] Data: [0.95731][0.00266][0.00294][0.00590][0.00286][0.00374][0.00285][0.00685][0.00231][0.00307][0.00654][0.00292]
[AI_MCU] ai_mcu_sample_process
```

## NPU 平台快速入门指南

NPU 平台对应 CANN 工具链，适用于 HiDiTing、Hi1156等端侧 NPU 平台。以下流程涵盖模型量化、转换、SDK 编译与上板调试，下面以HiDiTing为例演示快速入门方式。

### 准备 CANN 工具链

获取 CANN 工具链安装包及 Dockerfile，构建并运行 Docker 容器。CANN 安装包目录结构如下：

```
├── CANN-amct-*-linux.x86_64.tar.gz amct.tar.gz
├── CANN-compiler-*-linux.x86_64.run compiler.run
├── CANN-opp-*-linux.x86_64.run opp.run
├── CANN-runtime-*-linux.x86_64.run runtime.run
└── CANN-toolkit-*-linux.x86_64.run toolkit.run
```

### 准备待部署模型与数据

- 准备好待部署模型。可直接使用 HiSpark.AI LeNet-5 以及 Gru Sample 中的 mnist-12.onnx 以及 GRU_S_STREAM.onnx。
- 准备好量化数据。**1156E无需量化可跳过此步骤。** 准备一个文件夹，将 float32 格式的量化数据存储为 `.bin` 格式，可直接使用 HiSpark.AI LeNet-5 以及 Gru Sample 中运行数据预处理脚本之后的 npy_data 文件夹。

### 准备 SDK

使用商用发布SDK或从开源社区下载 SDK 源码。

### 准备 Sample

进入 Sample 目录，如 LeNet-5 就进入 `${hispark_ai_root}/src/samples/oh/lenet5` 目录，Gru 就进入 `${hispark_ai_root}/src/samples/oh/gru` 目录。Sample 目录结构如下：

```
${sample_path}
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

### HiDiTing模型量化

Hi1156E不涉及量化，直接参考**模型转换**章节。
HiDiTing使用 CANN 工具链中的 AMCT 工具进行模型量化，具体可参考对应 Sample README 中的量化指南：

```
amct_onnx calibration --model "xxx" --save_path "xxx" --input_shape "xxx" --data_dir "xxx" --data_types "xxx" --batch_num xxx
```

参数说明：

- `--model`：原始 ONNX 模型路径
- `--save_path`：量化后模型的存放路径
- `--input_shape`：指定模型输入的 shape
- `--data_dir`：与模型匹配的 bin 格式数据集路径
- `--data_types`：输入数据的类型
- `--batch_num`：训练后量化推理阶段的 batch 数

运行成功后生成：

- `xxx_fake_quant_model.onnx`
- `xxx_deploy_model.onnx`

### 模型转换

使用 CANN 工具链中的 ATC 工具进行模型转换，具体可参考对应 Sample README 中的转换指南：

```
atc --model=xxx.onnx --framework=5 --output=xxx --input_fp16_nodes="xxx" --output_type=xxx --soc_version=xxx --input_shape="xxx" --mode=xxx
```

参数说明：

- `--model`：网络模型文件路径与文件名
- `--framework`：原始网络模型框架类型。5 表示 ONNX
- `--output`：存放转换后的离线模型的路径以及文件名
- `--input_fp16_nodes`：指定输入数据类型为 FP16 的输入节点名称
- `--output_type`：指定网络输出数据类型
- `--soc_version`：指定模型转换时昇腾 AI 处理器的版本
- `--input_shape`：指定模型输入数据的 shape
- `--mode`：运行模式。HiDiTing指定30；Hi1156E指定0
模型转换成功后，HiDiTing生成.exeom模型，Hi1156E生成.om模型。
### HiDiTing SDK 编译

配置对应环境变量，在具体 Sample（如 gru）下运行 build_npu.sh 脚本，即可完成编译：

```
cd ${sample_path}
export SDK_PATH=${sdk_path}
export ADAPTOR_PATH=${adaptor_path}
bash build_npu.sh 3322
```

编译成功后 `3322-ai-liteos-sample.fwpkg` 镜像文件会生成在 `${sample_path}/output` 目录下。

### 1156 SDK 编译

配置对应环境变量，在具体 Sample（如 gru）下运行 build_npu.sh 脚本，即可完成编译：

```
cd ${sample_path}
export SDK_PATH=${SDK_PATH}
export ADAPTOR_PATH=${ADAPTOR_PATH}
export COMPILER_PATH=${COMPILER_PATH}
export ACL_HEADER_PATH=${ACL_HEADER_PATH}
bash ${SAMPLE_PATH}/oh/gru/build_npu.sh 1156
```

编译成功后可执行文件 gru1156 会生成在 `${sample_path}/src/build` 路径下，so 文件 libai_adaptor_tiny.so 在 `${ADAPTOR_PATH}/adaptor/npu/build` 路径下。

### HiDiTing 烧录调试

使用 BurnTool 工具进行 `3322-ai-liteos-sample.fwpkg` 的烧录；使用 Debugkits 工具将模型和输入数据上传到单板；使用 sscom 工具发送 `AT^SAMPLE` 运行，会看到串口打印的运行成功信息，如 Gru 下：

```
[AI_NPU] the predict cost time 89 ms
[AI_NPU] Data size: [24]
[AI_NPU] Shape: [1 12]
[AI_NPU] DataType: 42
[AI_NPU] Data: [0.00000][0.01210][0.00000][0.00017][0.00000][0.00000][0.00000][0.00006][0.00000][0.00000][0.00012][0.98779]
```

### 1156 上板调试

将可执行文件、lib、ko 挂载到单板；重新加载 ko，配置 lib 路径；执行可执行文件，会看到串口打印的运行成功信息，如 Gru 下：

```
[AI_NPU] the predict cost time 89 ms
[AI_NPU] Data size: [24]
[AI_NPU] Shape: [1 12]
[AI_NPU] DataType: 42
[AI_NPU] Data: [0.00000][0.01210][0.00000][0.00017][0.00000][0.00000][0.00000][0.00006][0.00000][0.00000][0.00012][0.98779]
```
