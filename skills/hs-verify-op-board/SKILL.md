---
name: hs-verify-op-board
description: >-
  Verify an already-built and already-flashed MindSpore Lite Micro operator on a real HiSpark WS63/Hi3863 board by selecting a Host-PASS case, reusing its exact input and ground truth, collecting complete serial tensor output, and producing an on-board accuracy verdict. Use when the user explicitly names hs-verify-op-board, asks only for real-board/operator board accuracy after firmware is ready, or hs-workflow-op-development routes the post-flash verification stage here. Generic operator adaptation belongs to hs-workflow-op-development; firmware build belongs to hs-dev-build and flashing belongs to hs-dev-flash.
---

# 算子真板精度验证

本 skill 验证的是“同一条 Host 用例在真实 WS63/Hi3863 上是否可达并输出正确”。它不重新设计测试规格，不构建 fwpkg，不烧录固件，也不修改算子源码。

Host 与 Board 不合并为一个 skill：

| 对比项 | Host accuracy | Board accuracy |
|---|---|---|
| 执行位置 | PC/WSL，benchmark 在 x86 运行 | 真实 WS63/Hi3863 |
| 覆盖策略 | 完整规格矩阵 | 从 Host PASS 中选代表性用例或按要求跑矩阵 |
| 主要发现 | parser/infer/kernel/opcoder/量化和生成代码问题 | 交叉编译、固件接入、真实 RISC-V 执行和板端输出问题 |
| 是否需要板卡 | 否 | 是 |
| 共同事实 | 同一模型、同一输入、同一轮 GT | 同一模型、同一输入、同一轮 GT |

两者功能不同但共享语义用例，因此保持两个 leaf skill，由 `hs-workflow-op-development` 串联。

## 职责边界

| 任务 | 所有者 |
|---|---|
| `op_spec.py`、最小模型、输入和 GT | `hs-verify-op-host` |
| 算子源码缺陷 | `hs-dev-op-implement` |
| fwpkg 构建 | `hs-dev-build` |
| fwpkg 烧录 | `hs-dev-flash` |
| 串口完整 Tensor 与 GT 比对 | 本 skill |

如果用户只说“烧录”，使用 `hs-dev-flash`；如果用户泛化地要求“适配算子并上板验证”，使用顶层 workflow。

## 用户可见进度

```markdown
待办:
- [ ] step0 选择本轮 Host PASS 用例
- [ ] step1 核对板测前置事实
- [ ] step2 采集完整串口 Tensor
- [ ] step3 运行板端精度比对并分流失败
```

每个 step 只有在证据已展示后才能勾选。

## step0：选择 Host PASS 用例

从本轮 `hs-verify-op-host` 产物中选择 case。必须同时存在：

- `verify_summary.txt` 中该 case 的明确 PASS；
- 该 case 的模型文件；
- 与固件一致的输入 `.bin`；
- 同轮 `gt/output*.npy`；
- fp32 或 full-quant INT8 模式记录。

记录 model、input、gt、framework、case ID、模式和 Host summary 的绝对路径。不能跨轮拼接模型、输入和 GT；不能拿一个 case 的 GT 验另一个固件。

如果要求完整板端矩阵，按 case 与 fp32/INT8 配置逐项执行。不要假设多张最小模型已合并进一个 `libnet.a` 或一个 fwpkg。

## step1：核对板测前置事实

本 skill 只接受 workflow 或用户提供的烧录完成证据：

```text
FIRMWARE_BUILD=PASS
FLASH_VERDICT=PASS
firmware=<absolute fwpkg path>
target=<fbb target>
port=<serial port>
```

同时确认固件确实接入 step0 的模型和输入，sample 会打印完整输出 Tensor，而不只是启动日志、argmax 或标签。

没有连接开发板、没有烧录成功证据、用户不在板边或串口不可用时，输出 `ACCURACY_VERDICT=NOT_RUN` 并返回 workflow。Host PASS 保持有效，但不能宣称板测完成。

## step2：采集完整串口 Tensor

接受 workflow 通过 `hs-dev-flash` 的可选 `fbb flash ... --then-monitor` 链路、串口 skill 或其他已验证串口工具保存的本轮文本。文件必须包含本次烧录后的启动与推理输出，并能追溯端口和采集时间。不得使用旧 monitor、截断后的十个元素、手抄 Tensor 或只有分类标签的日志。解析不到完整 Tensor 或机器可读 shape 时，本步骤 FAIL。

## step3：计算精度并分流

唯一精度入口是已存在的 `board_accuracy.py`：

```bash
python3 <skill_root>/scripts/board_accuracy.py \
  --gt-dir <same-run case gt directory> \
  --monitor <current-run serial text file> \
  [--quantized]
```

脚本解析 benchmark `PrintTensorHandle` 的 `Elements`/`Shape`/`Data`，或项目连续输出的 `[AI_MCU] Shape: [d1,d2,...]` 与 `[AI_MCU] Data: [v1]...`。它先精确核对 Tensor 数量、元素数和 shape，再使用与 Host 相同的余弦语义和签收门槛逐 Tensor 比较：fp32 `cos >= 0.999`，INT8 `cos >= 0.99`。只有 `[AI_MCU] Data` 而没有 shape 时输出 `SHAPE_UNVERIFIED` 并拒绝签收。Host 与 Board 复用同一 GT，Board 不得另设更松阈值把 Host 不合格精度判绿。

失败分流：

| 证据 | owner |
|---|---|
| 串口无输出、启动失败、模型/输入未接入 | workflow stage5 的 sample/adaptor/固件接线 |
| 固件未烧录或烧录 JSON 失败 | `hs-dev-flash` |
| Host 同 case PASS、板端 Tensor 可解析但精度 FAIL | 本 skill 输出对比证据，由 workflow 回流实现或板端接入 |
| GT、模型、输入跨轮或 case 不一致 | 回 step0 重新选择，不运行比较 |
| Tensor 数量/shape 不匹配 | 先核对固件模型和串口格式，再决定是接入还是算子缺陷 |

不要在本 skill 修改 kernel/opcoder、降低阈值或重写 GT。把首个失败原文、逐 Tensor 余弦、固件/case 身份和建议 owner 返回 workflow。

## 红线

1. 没有当轮 Host PASS 和同一 case GT 不做板端精度签收。
2. 烧录成功不等于精度成功；只有完整 Tensor 比对可产生 `ACCURACY_VERDICT=PASS`。
3. 不直接调用 BurnTool 或旧 `flash.sh` 烧录；烧录统一交给 `hs-dev-flash`/`fbb flash`。
4. 不由本 skill 构建 SDK 或 fwpkg；构建统一交给 `hs-dev-build`/`fbb build`。
5. 不手填预期张量、余弦值，不复用跨轮 GT/monitor，不调低阈值。
6. 不因“硬件公差”“串口噪声”放行精度失败；先用原始输出证明根因。
7. 不以只有平铺数值、缺少 shape 元数据的串口输出签收；相同元素数不代表输出 shape 正确。
8. 不修改 Host 用例、能力清单或算子源码来让板测变绿。

## 完成判据

只有以下条件同时成立，才输出：

```text
ACCURACY_VERDICT=PASS
```

- step0 的 case 在本轮 Host summary 中明确 PASS；
- 固件身份与该 case 的模型、输入、模式一致；
- `FLASH_VERDICT=PASS`；
- 本轮串口完整 Tensor 已保存；
- `board_accuracy.py` 对每个 Tensor 均达到固定阈值。

否则输出 `ACCURACY_VERDICT=FAIL` 或 `ACCURACY_VERDICT=NOT_RUN`，并列出缺失证据或失败 owner。FAIL/NOT_RUN 时不得使用“板测完成”“端到端通过”或 ✅ 等完成语义。

## 资源索引

| 资源 | 用途 |
|---|---|
| `scripts/board_accuracy.py` | 当前唯一板端 Tensor 精度判定入口 |
| `references/device-matrix.md` | 核对 WS63/Hi3863 串口和设备信息 |
| `references/troubleshooting.md` | 读取串口和板端结果异常时 |

旧一体化构建、直连 BurnTool、HTTP 烧录服务和 patch 脚本仅保留在本次优化前的备份中，不属于当前 skill。
