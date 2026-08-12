---
name: hs-verify-op-board
description: >-
  Prepare WS63 MindSpore Lite Micro operator board integration and verify real-board accuracy: require the user-provided firmware SDK source location, reuse a Host-PASS model/input/GT, generate and cross-compile the Micro model, deterministically generate the OH_AI sample, verify adaptor/CMake/Kconfig wiring, hand firmware build and flashing back to the top-level workflow, collect complete serial tensors, and produce board accuracy. Use when the user explicitly names hs-verify-op-board, asks only for WS63 operator board preparation/accuracy, or hs-workflow-op-development routes its board stages here. Other chips require their own chip-specific integration reference and must not reuse WS63 paths by analogy.
---

# 算子真板精度验证

本 skill 负责“同一条Host用例如何被确定性接入固件SDK，以及它在真实WS63
上是否可达并输出正确”。它不重新设计测试规格、不修改MindSpore Lite算子源码；固件
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
| 覆盖策略 | 完整规格矩阵 | 从 Host PASS 中选代表性用例或按要求跑矩阵 |
| 主要发现 | parser/infer/kernel/opcoder/量化和生成代码问题 | 交叉编译、固件接入、真实 RISC-V 执行和板端输出问题 |
| 是否需要板卡 | 否 | 是 |
| 共同事实 | 同一模型、同一输入、同一轮 GT | 同一模型、同一输入、同一轮 GT |

两者功能不同但共享语义用例，因此分别由Host验证专项 Skill和板端验证专项 Skill负责，再由 `hs-workflow-op-development` 串联。

## 职责边界

| 任务 | 所有者 |
|---|---|
| `op_spec.py`、最小模型、输入和 GT | `hs-verify-op-host` |
| 算子源码缺陷 | `hs-dev-op-implement` |
| 固件SDK位置授权、Micro模型、adaptor、Sample和构建接线 | 本 skill；完整workflow下由顶层stage6共同持有 |
| fwpkg 构建 | 顶层workflow调用 `hs-dev-build`；本skill输出构建handoff并验收返回证据 |
| fwpkg 烧录 | 顶层workflow调用 `hs-dev-flash`；本skill输出烧录handoff并验收返回证据 |
| 串口完整 Tensor 与 GT 比对 | 本 skill |

如果用户只说“烧录”，使用 `hs-dev-flash`；如果用户泛化地要求“适配算子并上板验证”，使用顶层 workflow。

## 用户可见进度

```markdown
待办:
- [ ] step0 要求并核对用户提供的固件SDK源码位置
- [ ] step1 选择本轮Host PASS用例并冻结模型、输入和GT
- [ ] step2 生成Micro工程并交叉编译模型静态库
- [ ] step3 安装/核对adaptor，生成Sample并完成CMake/Kconfig/target接线
- [ ] step4 委托构建并核对fwpkg确实包含本轮Sample和模型
- [ ] step5 委托烧录并采集完整串口Tensor
- [ ] step6 运行板端精度比对并分流失败
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

## step1：选择 Host PASS 用例

从本轮 `hs-verify-op-host` 产物中选择 case。必须同时存在：

- `verify_summary.txt` 中该 case 的明确 PASS；
- 该 case 的模型文件；
- 与固件一致的输入 `.bin`；
- 同轮 `gt/output*.npy`；
- fp32 或 full-quant INT8 模式记录。

记录 model、input、gt、framework、case ID、模式和 Host summary 的绝对路径。不能跨轮拼接模型、输入和 GT；不能拿一个 case 的 GT 验另一个固件。

如果要求完整板端矩阵，按 case 与 fp32/INT8 配置逐项执行。不要假设多张最小模型已合并进一个 `libnet.a` 或一个 fwpkg。

## step2：生成Micro工程并交叉编译模型库

完整执行 `chips/ws63/references/sdk-integration.md` 第3-5节，并且必须调用确定性入口
`chips/ws63/scripts/build_micro.py`，不能临场拼converter/CMake命令：

- 对step1的具体模型运行converter_lite；
- 检查生成的 `model0.c`、`net0.c/Execute0()`和目标Kernel符号；
- 使用真实RISC-V工具链构建 `libmicro_runtime.a`和 `libnet.a`；
- 核对归档对象、模型身份、dtype和当前case，禁止使用陈旧库冒充。

任何失败先保留converter/编译原文，再根据证据回流算子实现、工具链或模型配置。

## step3：adaptor、Sample与SDK接线

完整执行 `chips/ws63/references/sdk-integration.md` 第6-10节，包括以下确定性动作：

1. 以HiSpark.AI的 `src/adaptor`为来源安装或逐文件核对CPU adaptor和 `ai.h`；
2. 把本轮两份模型库安装到带operator/case/mode身份的目录；
3. 以仓库中经过验证的OH_AI Sample/API结构作为代码模板；
4. 运行 `chips/ws63/scripts/prepare_sample.py`，使用同一Host输入生成多输入/多输出安全的
   独立板端Sample；缺输入、dtype或大小不符必须硬失败；
5. Sample调用一次 `OH_AI_ModelPredict()`并打印每个完整Tensor和shape；
6. 调用 `chips/ws63/scripts/integrate_sdk.py`按固定规则安装adaptor、`ai.h`、带
   operator/case/mode身份的模型库，并接入CMake、Kconfig、target和模型库选择；
7. 读取脚本receipt，并在调用 `hs-dev-build`/`fbb build`的同一进程导入
   `ws63_board_env.ps1|sh`；必须使用脚本生成的 `invoke_hs_dev_build.ps1|sh`或
   等价地先source再build，确认 `SDK_INTEGRATION_GATE=PASS`；只“读取”环境文件不算执行；
8. 运行 `chips/ws63/scripts/verify_wiring.py`检查每条定义点/消费点，输出
   `BOARD_WIRING_GATE=PASS`。

不能凭经验自由写另一套API路线，也不能只写一句“完成接线”。

## step4：委托构建并核对固件身份

若由顶层workflow编排，本skill把step3产物和target交回workflow，由workflow调用
`hs-dev-build`执行真实target的clean build；若用户只调用本leaf，则输出同样的结构化
handoff，等待顶层/调用者返回构建证据，不自行加载或改写build Skill规则。本skill负责
确认构建输入就是step3冻结的Sample和模型库。必须同时得到：

```text
FIRMWARE_BUILD=PASS
firmware=<fresh absolute *_all.fwpkg>
target=<fbb target>
```

构建进程还必须回显并核对 `AI_CUSTOM_SAMPLE_DIR`和`AI_MCU_MODEL_VARIANT`与receipt一致；
缺任一变量时，即使`fbb build`退出0也判定接线FAIL。

随后必须运行 `chips/ws63/scripts/verify_firmware.py`，机械检查Sample `.c.obj`、map中的模型
Predict/Execute/目标Kernel及 `_all.fwpkg`相对本轮Sample、两份库和配置的新鲜度。只有
`FIRMWARE_CONTENT_GATE=PASS`才能进入烧录；`fbb build`退出0但缺该门禁仍是FAIL。
退出码0但Sample未编入固件仍是FAIL。

`verify-prepared-firmware`模式可以跳过step2-4的写入和构建动作，但必须从已有证据恢复
同样的SDK、case、模型库、Sample对象、符号和fwpkg身份；缺一项都不能猜测。

## step5：委托烧录并采集完整串口Tensor

若由顶层workflow编排，把step4的新鲜 `_all.fwpkg`交回workflow调用 `hs-dev-flash`；
若单独调用本leaf，则输出烧录handoff并等待返回。只接受flash Skill/fbb最后一行JSON
形成的结论。随后采集本次烧录后的串口文本。本skill也可接受workflow或用户提供的既有证据：

```text
FIRMWARE_BUILD=PASS
FLASH_VERDICT=PASS
firmware=<absolute fwpkg path>
target=<fbb target>
port=<serial port>
```

烧录交接必须保留以下执行规则，不能缩写成“运行 fbb flash”：

1. 设置并回显用户授权SDK对应的 `FBB_SDK_DIR=<FIRMWARE_SDK_SRC>`；target必须来自
   `fbb describe --json`或`fbb list-targets --json`，固件必须是step4签收的 `_all.fwpkg`；
2. 默认执行 `fbb flash <target> --json-summary`。只有端口自动检测歧义时才让用户选择
   或显式传 `--port COM<N>`，不得凭设备名猜控制口/烧录口；
3. 只解析stdout最后一行JSON：`success=true`才是 `FLASH_VERDICT=PASS`；失败必须按
   `error.code`分流，不能按自然语言或进度日志猜成功；
4. `DEVICE_NOT_RESPONDING`时先确认用户就在板边并能按RESET，再启动一次
   `--manual-reset`重试，并明确告知只按一下RESET；不得在用户未确认在场时消耗复位窗口；
5. `PORT_NOT_FOUND`重新检测并询问端口，`PORT_BUSY`先释放占用，`FWPKG_NOT_FOUND`
   回构建阶段，其他硬错误保留完整JSON并停止盲目重试；
6. 若使用`--then-monitor`，monitor必须在本次烧录成功后开始并保存完整原文；否则由
   串口能力使用同一端口和Sample规定波特率采集。烧录波特率不能当作启动日志波特率。

这些规则由 `hs-dev-flash`拥有；本skill负责在handoff和返回证据中逐项核对，不复制或
绕过烧录实现。缺少端口、最终JSON、烧录时间或本轮monitor时间任一证据时，不进入精度签收。

同时确认固件确实接入step1的模型和输入，sample会打印完整输出Tensor，而不只是启动
日志、argmax、标签或Sample自行输出的PASS。

没有连接开发板、没有烧录成功证据、用户不在板边或串口不可用时，输出 `ACCURACY_VERDICT=NOT_RUN` 并返回 workflow。Host PASS 保持有效，但不能宣称板测完成。

接受 workflow 通过 `hs-dev-flash` 的可选 `fbb flash ... --then-monitor` 链路、串口 skill 或其他已验证串口工具保存的本轮文本。文件必须包含本次烧录后的启动与推理输出，并能追溯端口和采集时间。不得使用早于本轮烧录的 monitor、截断后的十个元素、手抄 Tensor 或只有分类标签的日志。解析不到完整 Tensor 或机器可读 shape 时，本步骤 FAIL。

## step6：计算精度并分流

唯一精度入口是已存在的 `board_accuracy.py`：

```bash
python3 <skill_root>/scripts/board_accuracy.py \
  --gt-dir <same-run case gt directory> \
  --monitor <current-run serial text file> \
  [--quantized]
```

脚本解析 benchmark `PrintTensorHandle` 的 `Elements`/`Shape`/`Data`，或项目连续输出的 `[AI_MCU] Shape: [d1,d2,...]` 与 `[AI_MCU] Data: [v1]...`。它先精确核对 Tensor 数量、元素数和 shape，再使用与 Host 相同的余弦语义和签收门槛逐 Tensor 比较：fp32 `cos >= 0.999`，INT8 `cos >= 0.99`。只有 `[AI_MCU] Data` 而没有 shape 时输出 `SHAPE_UNVERIFIED` 并拒绝签收。未带 `OUTPUT: index=N` 的连续 Shape/Data 协议只支持单输出、单轮推理；出现多个没有 round/output 标识的 Data 行时按协议歧义 FAIL，不静默取第一条。Host 与 Board 复用同一 GT，Board 不得另设更松阈值把 Host 不合格精度判绿。

失败分流：

| 证据 | owner |
|---|---|
| 串口无输出、启动失败、模型/输入未接入 | workflow stage6 的 sample/adaptor/固件接线 |
| 固件未烧录或烧录 JSON 失败 | `hs-dev-flash` |
| Host 同 case PASS、板端 Tensor 可解析但精度 FAIL | 本 skill 输出对比证据，由 workflow 回流实现或板端接入 |
| GT、模型、输入跨轮或 case 不一致 | 回 step0 重新选择，不运行比较 |
| Tensor 数量/shape 不匹配 | 先核对固件模型和串口格式，再决定是接入还是算子缺陷 |

不要在本 skill 修改 kernel/opcoder、降低阈值或重写 GT。把首个失败原文、逐 Tensor 余弦、固件/case 身份和建议 owner 返回 workflow。

## 红线

1. 完整模式下用户未明确提供固件SDK源码位置，不得开始SDK写入、构建或烧录。
2. 没有当轮 Host PASS 和同一 case GT 不做板端精度签收。
3. 烧录成功不等于精度成功；只有完整 Tensor 比对可产生 `ACCURACY_VERDICT=PASS`。
4. 不直接调用 BurnTool 或任何绕过统一入口的烧录脚本；烧录统一交给 `hs-dev-flash`/`fbb flash`。
5. 不自己实现另一套固件构建器；构建统一委托 `hs-dev-build`/`fbb build`，但不能省略构建前接线。
6. 不手填预期张量、余弦值，不复用跨轮GT/monitor，不调低阈值。
7. 不因“硬件公差”“串口噪声”放行精度失败；先用原始输出证明根因。
8. 不以只有平铺数值、缺少shape元数据的串口输出签收；相同元素数不代表输出shape正确。
9. 不修改Host用例、能力清单或算子源码来让板测变绿。

## 完成判据

只有以下条件同时成立，才输出：

```text
ACCURACY_VERDICT=PASS
```

- step1 的 case 在本轮 Host summary 中明确 PASS；
- 完整模式的 `BOARD_SDK_GATE`、`SAMPLE_PREP_GATE`、`BOARD_WIRING_GATE`与
  `FIRMWARE_CONTENT_GATE`均PASS；
- 固件身份与该 case 的模型、输入、模式一致；
- `FLASH_VERDICT=PASS`；
- 本轮串口完整 Tensor 已保存；
- `board_accuracy.py` 对每个 Tensor 均达到固定阈值。

否则输出 `ACCURACY_VERDICT=FAIL` 或 `ACCURACY_VERDICT=NOT_RUN`，并列出缺失证据或失败 owner。FAIL/NOT_RUN 时不得使用“板测完成”“端到端通过”或 ✅ 等完成语义。

## 资源索引

| 资源 | 用途 |
|---|---|
| `scripts/board_accuracy.py` | 当前唯一板端 Tensor 精度判定入口 |
| `chips/ws63/scripts/prepare_sample.py` | 从模型元数据和Host二进制输入确定性生成一次性、多dtype、多输入/输出Sample |
| `chips/ws63/scripts/build_micro.py` | 固定生成FP32/INT8配置，运行converter和Micro CMake，冻结两份模型库与receipt |
| `chips/ws63/scripts/integrate_sdk.py` | 固定安装adaptor、模型库并接入WS63 CMake/target；拒绝静默覆盖差异文件 |
| `chips/ws63/scripts/verify_wiring.py` | 构建前机械核对Sample、两份库、adaptor和CMake/Kconfig消费点 |
| `chips/ws63/scripts/verify_firmware.py` | 构建后机械核对Sample对象、最终map符号和完整fwpkg新鲜度 |
| `chips/ws63/references/device.md` | 核对 WS63 串口和设备信息；非WS63不得套用本接入规范 |
| `chips/ws63/references/troubleshooting.md` | 读取串口和板端结果异常时 |
| `chips/ws63/references/sdk-integration.md` | 必须完整读取；规定Micro模型、adaptor、Sample、CMake/Kconfig和固件接入细节 |
