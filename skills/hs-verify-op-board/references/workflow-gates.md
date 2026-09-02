# Board workflow gates

目录：

- [算子真板精度验证](#算子真板精度验证)
- [职责边界](#职责边界)
- [用户可见进度](#用户可见进度)
- [step0：固件SDK位置授权和身份门禁](#step0固件sdk位置授权和身份门禁)
- [step0a：板端 Python 依赖预检](#step0a板端-python-依赖预检在-step1-前执行)
- [step1：冻结完整板端期望矩阵](#step1冻结完整板端期望矩阵)

以下内容从入口按需下沉；SDK授权、矩阵分母和进度步骤保持不变。

# 算子真板精度验证

本 skill 负责“本轮Host板端期望矩阵中的每条用例如何被确定性接入固件SDK，以及它们在真实WS63
上是否全部可达并输出正确”。它不重新设计测试规格、不修改MindSpore Lite算子源码；固件
构建和烧录由顶层workflow分别调用 `hs-dev-build`、`hs-dev-flash`；本skill输出明确
handoff并在它们完成后继续验收，但不会在未读取这两个Skill时自行解释其内部流程。
本skill必须完整执行构建前的Micro模型、adaptor、Sample和SDK接线步骤，不能只验收一个
来源不明的固件。

两种入口模式：

| 模式 | 使用场景 | 起点 |
|---|---|---|
| `prepare-build-flash-verify` | 用户要求上板、构建并验证，或顶层workflow路由完整板端阶段 | step0 |
| `verify-prepared-firmware` | 用户明确已有已构建、已烧录且身份可追踪的固件，只要求精度比较 | step4；仍核对step0事实和固件身份 |

Host 与 Board 不合并为一个 skill：

| 对比项 | Host accuracy | Board accuracy |
|---|---|---|
| 执行位置 | PC/WSL，benchmark 在 x86 运行 | 真实 WS63 |
| 覆盖策略 | 完整规格矩阵 | 完整重放Host产生的全部板端适用`framework/case/mode`，不选代表性用例 |
| 主要发现 | parser/infer/kernel/opcoder/量化和生成代码问题 | 交叉编译、固件接入、真实 RISC-V 执行和板端输出问题 |
| 是否需要板卡 | 否 | 是 |
| 共同事实 | 同一模型、同一输入、同一轮 GT | 同一模型、同一输入、同一轮 GT |

两者功能不同但共享语义用例，因此分别由Host验证专项 Skill和板端验证专项 Skill负责，再由 `hs-workflow-op-development` 串联。

## 职责边界

| 任务 | 所有者 |
|---|---|
| `op_spec.py`、最小模型、输入和 GT | `hs-verify-op-host` |
| 算子源码缺陷 | `hs-dev-op-implement` |
| 固件SDK位置授权、Micro模型、adaptor、Sample和构建接线 | 本 skill step0-3；完整workflow恢复同一轮状态处理handoff |
| fwpkg 构建 | 顶层workflow调用 `hs-dev-build`；本skill输出构建handoff并验收返回证据 |
| fwpkg 烧录 | 顶层workflow调用 `hs-dev-flash`；本skill输出烧录handoff并验收返回证据 |
| 串口完整 Tensor 与 GT 比对 | 本 skill |

如果用户只说“烧录”，使用 `hs-dev-flash`；如果用户泛化地要求“适配算子并上板验证”，使用顶层 workflow。

## 用户可见进度

```markdown
待办:
- [ ] step0 要求并核对用户提供的固件SDK源码位置
- [ ] step0a 检查本轮框架所需的板端 Python 依赖
- [ ] step1 读取本轮board_expected_matrix.json并冻结全部Host PASS用例、模式、模型、输入和GT
- [ ] step2 对矩阵每行生成Micro工程并交叉编译模型静态库
- [ ] step3 对矩阵每行安装/核对adaptor，生成Sample并完成CMake/Kconfig/target接线
- [ ] step4 对矩阵每行委托构建并核对fwpkg确实包含本轮Sample和模型
- [ ] step5 对矩阵每行委托烧录并采集完整串口Tensor
- [ ] step6 对矩阵每行运行精度比对，最终生成全矩阵报告
```

每个 step 只有在证据已展示后才能勾选。

## step0：固件SDK位置授权和身份门禁

进入任何固件SDK写入前，必须让用户在本次请求或当前会话中明确提供：

```text
FIRMWARE_SDK_ROOT=<固件SDK仓库绝对路径>
```

即使能从当前目录、环境变量、磁盘搜索或fbb猜到路径，也不能替用户选择一个可写SDK。
没有路径时暂停板端阶段并询问；不要因此回滚或否定已经完成的Host验证。

用户提供后，必须完整读取并执行：

```text
chips/ws63/references/sdk-integration.md
```

先完成其中第1-2节，输出 `BOARD_SDK_GATE=PASS`和SDK/target绝对路径，才能继续。

若顶层workflow尚未记录环境，先询问并记录`HISPARK_ROOT/HISPARK_RUN_ENV`、
`FIRMWARE_SDK_ROOT/FIRMWARE_BUILD_ENV`、`DEVICE_IO_ENV`及可选`WSL_DISTRO`。不要只根据路径
猜运行环境；后续每条命令使用所在环境可识别的路径。

## step0a：板端 Python 依赖预检（在 step1 前执行）

在任何模型解析或 Sample 生成前执行 WS63 Python 依赖预检。`prepare_sample.py` 需要 `onnx`；
TFLite 用例需要 `tflite_runtime` 或 `tensorflow`；两种路径都需要 `numpy`。运行：

```bash
python3 chips/ws63/scripts/check_python_deps.py --framework <onnx|tflite|all>
```

脚本必须打印可导入模块及版本；任一必需模块缺失、导入失败或版本无法读取时输出
`PY_DEPS_GATE=FAIL` 并阻塞本轮板端阶段，不得跨环境继续解析或手工填充元数据。
本预检只确认可用性，不硬编码某个具体版本；依赖安装由用户选择的环境准备方式负责。

## step1：冻结完整板端期望矩阵

唯一分母是本轮`hs-verify-op-host`生成的`board_expected_matrix.json`。完整workflow的Host阶段
必须使用`--target all`，该manifest会列出每个RISC-V `framework/case_id/mode/test_point`。逐行确认：

- `verify_summary.txt` 中该case/mode的明确PASS；
- 该 case 的模型文件；
- 与固件一致的输入 `.bin`；
- 同轮 `gt/output*.npy`；
- fp32 或 full-quant INT8 模式记录。

记录manifest、model、input、gt、framework、case ID、模式和Host summary的绝对路径。
`expected_count`必须等于cases数组长度且每行`host_status=PASS`；存在重复身份、Host FAIL、空矩阵
或缺失产物立即停止。不能跨轮拼接模型、输入和GT；不能拿一个case的GT验另一个固件。

默认按固定顺序`framework → case_id → mode(fp32,int8)`逐项执行全部矩阵。每行沿用 Host 冻结的
`test_point`，不得在板端改写测试目的。不要假设多张最小
模型已合并进一个`libnet.a`或一个fwpkg；每行都有独立Micro库、Sample、固件和串口证据。
