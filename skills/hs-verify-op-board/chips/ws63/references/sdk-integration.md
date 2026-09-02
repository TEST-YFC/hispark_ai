# WS63 算子板测固件接入规范

本文件规定WS63算子板测的完整代码准备和固件接入流程。固件编译交给
`hs-dev-build`，烧录交给 `hs-dev-flash`；执行这两个阶段前，必须先完成本文规定的
Micro模型、adaptor、Sample、CMake/Kconfig和target接线步骤。

## 目录

- [1. 必填输入和授权边界](#1-必填输入和授权边界)
- [2. SDK 身份只读核对](#2-sdk-身份只读核对)
- [3. 逐项使用与 Host 完全相同的全部用例](#3-逐项使用与-host-完全相同的全部用例)
- [4. converter_lite 生成 RISC-V Micro C 工程](#4-converter_lite-生成-risc-v-micro-c-工程)
- [5. 交叉编译模型静态库](#5-交叉编译模型静态库)
- [6. 安装或核对 OH_AI CPU adaptor](#6-安装或核对-oh_ai-cpu-adaptor)
- [7. 安装当前 case 的模型库](#7-安装当前-case-的模型库)
- [8. 生成板端验证 Sample](#8-生成板端验证-sample)
- [9. 接入 CMake、Kconfig 和 target](#9-接入-cmakekconfig-和-target)
- [10. 构建前接线门禁](#10-构建前接线门禁)
- [11. 委托构建、烧录和精度验证](#11-委托构建烧录和精度验证)

## 1. 必填输入和授权边界

进入任何 SDK 写入动作前，必须由用户在本次会话中明确提供：

```text
FIRMWARE_SDK_ROOT=<固件SDK仓库绝对路径>
```

示例（ROOT 必须由使用者本次明确提供；SRC 由 agent 在该 ROOT 内只读核对）：

```text
FIRMWARE_SDK_ROOT=<用户提供的固件SDK仓库绝对路径>
FIRMWARE_SDK_SRC=<从已授权 FIRMWARE_SDK_ROOT 只读解析出的源码绝对路径>
```

不能仅根据当前目录、当前会话之外的记录、`FBB_SDK_DIR`、搜索到的第一个
SDK目录名或 `fbb describe` 结果自行选择可写 SDK。环境变量和 fbb 输出只用于
核对用户给出的路径，不替代用户授权。

同时读取Host生成的`board_expected_matrix.json`，并为当前矩阵行冻结：

```text
chip=ws63
target=<fbb describe返回的真实target>
framework=<onnx|tflite>
case_id=<Host PASS case>
mode=<fp32|int8>
model=<绝对路径>
input_dir=<绝对路径>
gt_dir=<绝对路径>
host_summary=<绝对路径>
board_expected_matrix=<绝对路径>
```

只有用户明确`BOARD_POLICY=HOST_ONLY`时不询问SDK路径。默认完整workflow会进入全矩阵板测。

## 2. SDK 身份只读核对

对用户给出的路径执行只读检查：

1. 路径必须为绝对路径且真实存在。
2. `FIRMWARE_SDK_SRC` 下应存在 WS63 的 `application/`、`middleware/`、
   `build/config/target_config/ws63/` 和构建输出约定。
3. 设置 `FBB_SDK_DIR=<FIRMWARE_SDK_SRC>` 后执行 `fbb --version`、
   `fbb describe --json` 或 `fbb list-targets --json`。
4. 从 JSON 选择真实 target；不得把任意 `.config` 文件名当成可调用 target。
5. 记录 SDK Git HEAD 和 dirty fingerprint。SDK 中已有改动属于用户，不得覆盖。

任一身份检查失败时，输出 `BOARD_SDK_GATE=FAIL` 并停在板端阶段；Host PASS保持有效。

## 3. 逐项使用与 Host 完全相同的全部用例

`board_expected_matrix.json`是唯一分母。必须按`framework/case_id/mode`固定顺序逐行执行，
不得选择一个代表case。当前行以下文件必须来自同一Host case：

```text
model/model.onnx 或 model/model.tflite
input/input*.bin
gt/output*.npy
verify_summary.txt 中该case的PASS记录
```

禁止跨轮、跨 case 或跨量化模式拼装。记录模型、输入和GT的绝对路径及哈希。

每行独立追踪并完成第4节至后续交接，并写`board_result.json`；第11节中的构建、烧录、串口和
精度由上层 Board/`hs-dev-build`/`hs-dev-flash` handoff 完成，不在本 reference 内绕过 owner
另起一轮。一行PASS不能替代其他行；只有矩阵汇总得到`expected=executed=pass`且
`fail=not_run=0`才算完整板测通过。
其中`executed=pass+fail`，NOT_RUN结果记录只计入`recorded`，不能计入`executed`。

从 Host case 的 `model/` 旁边寻找 `input/`，并在执行前显式核对；不允许找不到输入时
自动填零。

## 4. converter_lite 生成 RISC-V Micro C 工程

本节及第5节在Linux/WSL执行，因为当前MSLite包和交叉工具链是Linux x64程序。即使WS63
SDK将在Windows编译，也不能改用Windows Python直接启动Linux版converter。跨环境时以
`micro_build_receipt.json`中的模型和静态库SHA-256作为交接身份。

为选定模型调用唯一确定性入口，不得手工重写命令：

```bash
python3 <hs-verify-op-board>/chips/ws63/scripts/build_micro.py \
  --model <absolute model.onnx|model.tflite> \
  --framework <onnx|tflite> --mode <fp32|int8> \
  --calib-dir <absolute same-case input directory; int8 only> \
  --mslite-pkg <absolute MSLITE_PKG> \
  --toolchain-bin <absolute directory containing riscv32-linux-musl-gcc> \
  --output-dir <absolute empty board case directory>
```

该脚本为选定模型单独运行一次 `converter_lite`。FP32和INT8使用Skill内冻结的各自
配置；INT8逐模型输入绑定同一case的`calib_0..N`，数量不一致就失败。
脚本在同一 `LD_LIBRARY_PATH` 下先执行 `converter_lite --help`：仅当当前包明确支持
`--encryption`时附加`--encryption=false`，2.8等未声明该参数的包保持省略；help本身
非零、超时或无法启动时输出`MICRO_BUILD_GATE=FAIL`，不继续猜测版本参数。

预期产物至少包含：

```text
<board_case>/micro/
├─ CMakeLists.txt
├─ benchmark/
├─ include/model_handle.h
└─ src/
   ├─ model.c
   ├─ tensor.c
   ├─ context.c
   ├─ allocator.c
   └─ model0/
      ├─ model0.c
      ├─ net0.c
      └─ weight0.c
```

检查 `net0.c`：

- `Execute0()`确实存在；
- 包含目标算子应走的FP32或INT8 Kernel符号；
- INT8用例不能静默回退到FP32；
- 模型输入/输出数量、dtype和shape与Host case一致。

## 5. 交叉编译模型静态库

仍由上节 `build_micro.py` 使用 WS63 SDK 自带或用户明确提供的 RISC-V 工具链，
按照生成工程的CMake构建。脚本保留converter/CMake/build日志，并冻结
`archives/`与`micro_build_receipt.json`；不得复制陈旧构建目录里的库。
不得将 Host x86 benchmark 产物当作板端库。

如果固件SDK属于另一环境，把`archives/`复制到该环境的本轮handoff目录并逐文件复核
receipt哈希；后续`integrate_sdk.py`在固件构建环境中运行，不能复用Micro环境的路径字符串。

必须产生：

```text
libmicro_runtime.a
libnet.a
```

含义：

- `libmicro_runtime.a`：生成模型的 `MSModel*`接口、model0、Tensor、Context、Allocator
  和模型执行外壳；
- `libnet.a`：当前模型实际依赖并被裁剪选中的NNACL Kernel对象。

使用归档查看工具或链接 map 核对：

- `libmicro_runtime.a`含 `MSModelPredict0`、`Execute0`对应对象；
- `libnet.a`含目标Kernel对象；
- 两份库属于当前 case 和当前模式，不是陈旧模型残留。

## 6. 安装或核对 OH_AI CPU adaptor

adaptor固定来源是：

```text
<hispark_ai>/src/adaptor/adaptor
<hispark_ai>/src/adaptor/include/ai.h
```

WS63典型目标位置是：

```text
<FIRMWARE_SDK_SRC>/middleware/utils/ai_mcu/adaptor
<FIRMWARE_SDK_SRC>/include/middleware/utils/ai.h
```

Sample生成完成后统一调用：

```bash
python3 <hs-verify-op-board>/chips/ws63/scripts/integrate_sdk.py \
  --sdk-root <user-provided absolute FIRMWARE_SDK_ROOT> \
  --hispark-root <absolute hispark_ai root> \
  --sample-dir <absolute generated sample> \
  --model-lib-dir <absolute build_micro.py archives> \
  --operator <operator> --case <case> --mode <fp32|int8> \
  --target <real fbb target> \
  --receipt <absolute handoff/integration.json>
```

处理规则：

1. 若SDK已有adaptor，先逐文件比较来源、接口和本地修改，不整目录覆盖。
2. 若缺失，才按仓库现有目录结构接入HiSpark.AI提供的adaptor。
3. `OH_AI_ModelPredict()`的CPU实现必须转发到生成模型的 `MSModelPredict()`。
4. CPU/NPU选择沿用SDK现有构建配置，不临时以同名函数覆盖另一后端。
5. 对SDK做的兼容性修改必须最小化，并在交付中单独列出。
6. 已有adaptor或`ai.h`与HiSpark来源不同会硬失败；逐文件审阅后才能显式加
   `--replace-adaptor`，不得自动覆盖。

不得把整个 `middleware/utils` 当作算子生成物；本阶段只处理 `ai_mcu`接入相关文件。

## 7. 安装当前 case 的模型库

不要删除SDK中其他模型或用户文件。为当前测试 case 使用可追踪目录，例如：

```text
<FIRMWARE_SDK_SRC>/middleware/utils/ai_mcu/lib/
└─ <operator>_<case>_<mode>/
   ├─ libmicro_runtime.a
   └─ libnet.a
```

`integrate_sdk.py`机械创建该目录并生成环境文件。构建配置必须通过
`AI_MCU_MODEL_VARIANT`显式选择这一对库。不得把多个同名 `libnet.a`一起链接，也不得使用
不带case身份的陈旧库冒充当前产物。

脚本还生成 `invoke_hs_dev_build.ps1|sh`。必须使用该wrapper，或在调用
`hs-dev-build/fbb build`的同一进程先导入 `ws63_board_env.ps1|sh`并回显核对：

```text
AI_CUSTOM_SAMPLE_DIR=<当前Sample绝对路径>
AI_MCU_MODEL_VARIANT=<operator>_<case>_<mode>
```

只保存、查看或在另一个已经退出的shell中source环境文件不算完成接线。

## 8. 生成板端验证 Sample

板端Sample以仓库中经过验证的OH_AI Sample/API结构为模板，例如：

```text
<hispark_ai>/src/samples/oh/lenet5/src/ai_main.c
```

实际生成必须使用以下确定性入口填入模型元数据和Host输入：

```bash
python3 <hs-verify-op-board>/chips/ws63/scripts/prepare_sample.py \
  --model <absolute model.onnx|model.tflite> \
  --framework <onnx|tflite> \
  --input-dir <absolute Host case/input> \
  --micro-model-source <absolute generated micro/src/model0/model0.c> \
  --output-dir <absolute independent sample dir> \
  --case <case-id> \
  --mode <fp32|int8>
```

只有 `SAMPLE_PREP_GATE=PASS`才能继续。该脚本同时读取源ONNX/TFLite规格和converter
生成的 `model0.c` 公共Micro API Tensor元数据，以后者作为板端真实dtype/shape并要求
二者一致，再逐字节嵌入Host `input*.bin`。这对INT8尤其重要：内部Kernel量化不等于
公开输入一定变成int8；不能靠模式名猜。源模型与Micro API不一致、缺输入、字节数
不符、动态shape或不支持dtype时硬失败。禁止“找不到输入填零”“按目录名猜dtype”或
原地覆盖示例Sample。

脚本依赖Python环境中的 `onnx`（ONNX模型）或 `tflite_runtime/tensorflow`（TFLite
模型）；应在完成Host验证的同一WSL/Python环境运行，因为该环境已经能构造和检查对应
模型。缺依赖时返回环境FAIL，按 `hs-workflow-mslite-env-setup`补依赖，不得改成猜dtype。

必须复用仓库中已验证的 OH_AI Sample/API风格；不得从空白自由设计另一套运行接口。

每个算子case可以有独立目录，例如：

```text
<hispark_ai>/src/samples/oh/<operator>/
├─ CMakeLists.txt
└─ src/ai_main.c
```

Sample必须具备以下固定职责：

1. 通过项目现有启动机制注册入口并创建一次性任务。
2. 调用 `OH_AI_Init`、`OH_AI_ModelCreate`、`OH_AI_ContextCreate`和
   `OH_AI_ModelBuild`。
3. 核对输入/输出Tensor数量、shape、dtype和数据大小。
4. 将同一Host case的完整输入逐字节写入输入Tensor；多输入逐个写入。
5. 只调用一次 `OH_AI_ModelPredict()`。
6. 打印case身份、每个输出的序号、dtype、完整shape、元素数和完整Data。
7. 多输出必须逐个打印，不能只打印第一个。
8. 释放模型、Context和运行资源，任务退出，不无限循环。

推荐机器可读串口协议：

```text
[AI_MCU] CASE: framework=onnx case=TC-003 mode=fp32
[AI_MCU] OUTPUT: index=0
[AI_MCU] DType: 43
[AI_MCU] Shape: [1,3,1]
[AI_MCU] Elements: 3
[AI_MCU] Data: [51.53875][36.05293][51.53875]
[AI_MCU] Inference finished; task exits after one run.
```

板端Sample可以打印API调用是否成功，但不能自行用硬编码预期值给出最终精度PASS；
最终 `ACCURACY_VERDICT`只能由主机读取串口并与GT比较得到。

## 9. 接入 CMake、Kconfig 和 target

以下动作由 `integrate_sdk.py`固定执行，随后必须逐项验证：

1. Sample的 `CMakeLists.txt`列出新增 `.c`源文件和所需头文件、组件依赖。
2. SDK Sample总入口通过现有Kconfig/组件机制纳入该Sample。
3. `middleware/utils/CMakeLists.txt`纳入CPU adaptor（若SDK尚未接入）。
4. target的组件列表包含CPU adaptor和Sample所需组件。
5. 模型库选择指向第7节冻结的case目录。

优先使用 `fbb config set CONFIG_...=y --target <target>`；手改配置时必须处理Kconfig
`choice`互斥项。任何配置变化后都执行clean build。

禁止只写源文件却不接构建；`fbb build`可能仍返回0但静默漏编该文件。

## 10. 构建前接线门禁

进入 `hs-dev-build`前必须运行：

```bash
python3 <hs-verify-op-board>/chips/ws63/scripts/verify_wiring.py \
  --sdk-root <absolute FIRMWARE_SDK_ROOT> \
  --sample-dir <absolute generated sample> \
  --model-lib-dir <absolute current case libs> \
  --adaptor-dir <absolute CPU adaptor> \
  --ai-header <absolute ai.h> \
  --consumer <absolute CMake/Kconfig/target file>::<required token> \
  --net-source <absolute net0.c> \
  --nm <absolute archive-aware nm executable> \
  --runtime-symbol MSModelPredict0 \
  --runtime-symbol Execute0 \
  --kernel-symbol <expected symbol>
```

每个实际CMake/Kconfig/target消费点都要用重复的 `--consumer`列出；INT8和有独立Kernel
符号的FP32 case必须列出 `--net-source/--kernel-symbol`。`--nm`必须能读取本轮RISC-V
归档；Windows交叉工具因运行库缺失不可执行时，在WSL中使用 `/usr/bin/nm`，不能降级
成只检查文件非空。脚本会同时检查 `net0.c`调用符号、`libmicro_runtime.a`中的
`MSModelPredict0/Execute0`和 `libnet.a`中的目标Kernel。只有脚本输出下列门禁后才能
交给顶层workflow构建：

```text
BOARD_WIRING_GATE=PASS
sdk_root=<用户提供的绝对路径>
sdk_src=<绝对路径>
target=<真实target>
sample_source=<绝对路径>
model_lib_dir=<绝对路径>
host_case=<framework/case/mode>
```

并完成以下检查：

- SDK改动仅限本次明确接线文件，没有覆盖用户无关改动；
- Sample使用的是同一Host输入；
- 模型库哈希与本轮交叉编译产物一致；
- CMake/Kconfig/target每条接线均有定义点和消费点；
- 不存在多个模型库候选导致链接不确定。

## 11. 委托构建、烧录和精度验证

接线通过后按顺序执行：

```text
hs-dev-build
    ↓ fresh *_all.fwpkg
hs-dev-flash
    ↓ FLASH_VERDICT=PASS
串口采集
    ↓ 本次烧录后的完整Tensor文本
hs-verify-op-board/scripts/board_accuracy.py
    ↓ 同一case gt/output*.npy
ACCURACY_VERDICT
```

其中 `hs-dev-build` 必须继承第7节的环境。生成的
`invoke_hs_dev_build.ps1|sh`是确定性默认入口；顶层workflow若直接编排build Skill，
也必须保证同一进程环境等价并保存变量回显证据。

构建后还要核对：

- Sample对应 `.c.obj`存在；
- 最终map/符号中存在模型Predict/Execute和目标Kernel；
- `_all.fwpkg`时间戳晚于本轮配置与源码修改。

这三项必须通过构建后机械门禁，不得只人工浏览：

```bash
python3 <hs-verify-op-board>/chips/ws63/scripts/verify_firmware.py \
  --sample-object <absolute current sample ai_main.c.obj> \
  --map <absolute target map> \
  --firmware <absolute fresh *_all.fwpkg> \
  --map-symbol MSModelPredict0 \
  --map-symbol Execute0 \
  --map-symbol <expected kernel symbol> \
  --newer-than <absolute current sample ai_main.c> \
  --newer-than <absolute current libmicro_runtime.a> \
  --newer-than <absolute current libnet.a> \
  --newer-than <absolute changed target config>
```

只有 `FIRMWARE_CONTENT_GATE=PASS`才说明本轮Sample、模型外壳和Kernel真实进入最终固件。

烧录成功不等于精度成功；只看到启动日志、标签或Sample自报PASS均不能签收。

