---
name: hs-workflow-train-op-development
description: >-
  编排 HiSpark.AI MindSpore Lite Micro FP32 训练算子的完整开发流程：检查前向能力，先写设计文档，按 GradRule、TrainNodeCoder 和 NNACL fp32_grad 步骤实现，构建训练工具包，生成最小训练模型，运行生成 C 的 Host 多步训练验证，按设备条件执行 WS63 板测，并更新独立验证文档。用于训练算子、反向算子、backward op、梯度支持，以及训练实现与测试、文档或上板组合的请求。明确只做某个阶段时，改用对应专项技能。
---

# 训练算子开发工作流

本技能负责阶段顺序、证据检查和失败处理。源码实现交给 `hs-dev-train-op-implement`，阶段调度脚本 `scripts/run_training_workflow.py` 按计划调用各阶段命令；Host 与板端验证分别交给 `hs-verify-op-host`、`hs-verify-op-board` 的训练分支，两份文档交给 `hs-design-op-manual`。

调度脚本的 `COMMANDS_COMPLETED` 只表示要求执行的命令已完成，不是训练验证通过。计划、命令和证据审计仍由本工作流准备和检查，具体见 [调度脚本说明](references/commands.md)。`design` 命令包含 prepare 和初版文档，`implementation` 命令只执行 apply；前序失败后仍执行 `final` 更新失败报告。

## 入口和范围

- 训练、反向传播、GradRule、TrainNodeCoder 或参数更新的完整开发请求使用本工作流。
- 明确只做源码、Host、板端或文档时使用对应专项技能。
- 没有训练语义的普通算子请求使用 `hs-workflow-op-development`。
- 默认范围为已有训练框架支持的 FP32、静态形状；默认新建最小训练模型，不等待用户提供模型。其他类型和框架扩展先核查源码及证据，不能根据文档中的支持表直接认定支持。
- WS63 是板端目标。默认 `BOARD_POLICY=AUTO_ALL`；用户明确只做 Host 时使用 `HOST_ONLY`。没有设备时记录未执行，不把 Host 通过写成 WS63 通过。

## 固定顺序

开始时建立本轮清单和唯一 `run_id`，逐阶段记录状态、日志和产物路径：

| 阶段 | 动作 | 进入下一阶段的条件 |
|---|---|---|
| train-stage0 | 范围、前向能力和环境检查 | 代码/工具包身份清楚，前向缺口已处理 |
| train-stage1 prepare | 实现技能 step0、step1；制定训练用例计划；生成设计文档和验证文档初稿 | 反向传播说明和初版文档检查通过，尚未修改正式源码 |
| train-stage1 apply | 实现技能 step2、step3、step4、step5；先完成源码门禁 | `TRAIN_SOURCE_GATE=PASS`，`TRAIN_IMPLEMENT_GATE=NOT_RUN` |
| train-stage2 | 仓库增量构建、确认训练工具包 | `MSLITE_TRAIN_BUILD=PASS`，包与源码版本一致 |
| train-stage3 | Host 生成模型、转换、图/内存/生成代码检查 | 正向和预期拒绝用例均有真实转换结果 |
| train-stage4 | Host 编译并运行生成 C 的多步训练，完整数值比较 | 预期用例全部完成，结构和数值检查通过 |
| train-stage5 | 检测设备；按条件准备 WS63 固件、烧录、训练板测；由生成端 observer 提供运行时参数，sample 输出训练记录，collector 采集，compare 比较 | 板端逐项结果，或明确的未执行记录 |
| train-stage6 | 用本轮结果更新两份文档，输出最终报告；调度器的 `final` 阶段在成功或失败时均同步真实结果 | 两份文档通过审计，状态与真实证据一致 |

stage6 放在板端结果之后收尾；初版文档在 stage1 编码前生成。失败、设备缺失或用户排除板端时也要更新验证文档，不能只为成功结果写报告。

`scripts/run_training_workflow.py` 的命令与上述阶段对应如下：

| 执行位置或命令 | 对应阶段与职责 |
|---|---|
| 启动调度前 | train-stage0：完成范围、前向能力和环境检查 |
| `design` | train-stage1 prepare：实现分析、Host 用例计划及初版文档 |
| `implementation` | train-stage1 apply：按审核后的设计执行源码实现 |
| `build` | train-stage2：构建并确认训练工具包 |
| `model` | train-stage3：模型生成与转换 |
| `host` | train-stage3/4：图、内存及生成代码检查，编译执行和数值比较 |
| `aggregate` | 汇总 Host 用例结果，并导出冻结的板端预期矩阵；通过后进入 train-stage5 |
| `board` | train-stage5：板测或明确记录未执行原因 |
| `final` | train-stage6 的文档收尾：成功或失败均同步 facts、两份文档并审计 |
| 调度结束后 | 独立 finalizer：读取终态证据，给出业务 verdict |

调度器结束后必须独立运行 `scripts/finalize_training_workflow.py`，完整命令见 [终态 finalizer](references/commands.md#终态-finalizer调度结束后单独调用)。该命令读取本轮 summary、Host/board 汇总和 facts，形成业务 verdict；不能放入调度器的 `final` 阶段，也不能以 `COMMANDS_COMPLETED` 代替训练验证通过。

## train-stage0：范围与环境

1. 记录代码根、主仓/子模块 HEAD、已有修改、converter 和工具包路径、`MSLITE_OP_OUTPUT`。产物放在独立 `<opdir>=<MSLITE_OP_OUTPUT>/train_<unit>`，不进入源码或构建树。
2. 记录 source entry、优化后的 forward primitive、训练单元、类型/形状/属性范围、optimizer、loss、是否需要冻结参数及板端策略。
3. 检查前向 parser、primitive/schema、populate/parameter、infer-shape/type、runtime kernel、Micro coder 和注册/构建/转换接入。已有能力可以复用，但要有证据；不要求为训练重复新增七层代码。
4. 前向缺失时交回 `hs-dev-op-implement` 或前向完整工作流，补齐并验证后再继续反向实现。
5. 核对可用的训练控制用例。没有已知通过用例时记录 `TRAIN_ENV_BASELINE=UNKNOWN`。多个不相关用例在 converter 启动时同时失败，先检查环境或工具包，不盲改被测算子。
6. 板端 SDK 必须来自用户给出的路径并经只读身份检查。路径不是 SDK 时，不向其中写入文件；先完成可执行的 Host 阶段，在报告说明板端前置缺失。
7. Host 与板端可以在不同环境执行。常见情况是 Host 在 WSL，而 fbb、SDK 和串口在 Windows。WSL 探测不到 `/dev/ttyUSB*` 不能写成整机没有板卡；须在设备所在环境执行 `hs-verify-op-board/scripts/probe_serial_ports.py`（WSL 下可用 `--target auto` 通过 PowerShell interop 探测 Windows 串口），保存 `serial_probe.json`，并记录 fbb、SDK、串口各自的执行环境。若 PowerShell interop、fbb、SDK 路径或唯一串口任一缺失，板端记 `NOT_RUN` 并写清恢复步骤，不得继续烧录。

范围或环境已明确时自动推进，不逐步要求用户确认。需要新增框架能力、扩大源码/SDK 修改范围或执行用户未授权的硬件操作时，说明原因、影响文件和替代方案后再询问。

## train-stage1：先设计，再实现

1. 调用 `hs-dev-train-op-implement mode=prepare`，按原顺序执行 step0、step1。形成前向前置说明、反向传播说明、调用关系、实现约束和 `train_capability_checklist.json`。
2. 调用 `hs-verify-op-host verification_kind=training stage=plan` 制定用例：测试点、预期结果、支持/拒绝边界、梯度经过目标算子的可观测路径、冻结适用性。此时只准备生成器和计划，不声称验证完成。
3. 调用 `hs-design-op-manual verification_kind=training mode=integrated-initial`。设计文档写规格、反向映射、保活张量、复用决定和实现路径；独立验证文档写测试计划，各未执行项为 `NOT_RUN`。两份文档经训练审计后才能改正式源码。
4. 调用 `hs-dev-train-op-implement mode=apply`，保持原步骤：step2 GradRule → step3 TrainNodeCoder → step4 NNACL fp32_grad 与 CMake → step5 实现检查和增量构建。apply 阶段完成源码检查后输出 `TRAIN_SOURCE_GATE=PASS`、`TRAIN_IMPLEMENT_GATE=NOT_RUN`；构建、转换和生成代码证据在 stage2～stage4 完成后，再回到 step5 收尾并决定最终实现门禁。已有实现满足需求时记录复用证据，不为了产生 diff 重写代码。
5. 数值失败导致规格、用例或实现范围变化时，先更新设计和计划再修复。普通实现修复保留原参考结果，重新构建并重跑受影响用例。

权重冻结的开发边界读取实现技能中的冻结说明。配置解析、梯度选择、内存规划或可选梯度接口不存在时，不能假设 coder 单独支持冻结；需要该能力的任务记录阻塞并说明框架改动范围。未要求冻结的普通任务可以继续，但报告必须写出未验证的能力。

## train-stage2：构建训练工具包

目标：用当前源码生成训练工具包，并确认后续转换使用的 converter 来自本轮构建。

1. 使用 `hs-workflow-op-development/scripts/build_mslite.sh` 构建。先保留增量构建；只有在构建配置无效或增量构建无法可靠复现时，才通过同一入口使用 `--full`。
2. 训练构建默认按 CPU 和可用内存估算并发；若显式设置 `JOBS`，记录实际值和原因；出现资源压力时降低并发并保留日志。
3. 保存以下证据：完整构建命令、退出码、构建日志、训练工具包路径、源码指纹，以及构建时间和当前 `run_id`。
4. 构建成功后重新检查 converter 的实际路径、版本或源码指纹，确认它属于本轮构建；禁止用旧工具包或旧 converter 代替当前源码。
5. 构建失败时将 `MSLITE_TRAIN_BUILD` 记为 `FAIL`，保留日志和恢复条件；后续依赖构建的阶段记为 `NOT_RUN`，不得把失败改写成未执行。

通过条件：构建命令退出码为 0，训练工具包真实存在，工具包与源码指纹一致，且 converter 复核通过。
## train-stage3/4：Host 训练验证

调用 `hs-verify-op-host verification_kind=training stage=run`，读取其训练步骤。Host 技能负责模型生成、转换、训练图/内存/生成代码检查、native 构建、训练执行和数值比较；工作流只检查结果、处理跨阶段失败，不另外维护一套训练执行命令。

默认每个测试点新建确定性最小模型。若目标算子没有参数，仍需安排可训练上游，让其权重更新依赖目标算子的反向传播；只在目标后添加可训练层不足以验证目标 dX。输入和初值应让参考上游梯度非零。

默认验证 Predict 输出、Eval 输出和 loss，以及第 0、1、最后一步的参数值。至少两步才能区分一步与最终状态。原始梯度只有在确实导出并比较时才记为已测；不能把参数更新比较称为梯度逐元素比较。

保留四类证据：模型生成、转换、编译执行、数值比较。转换和编译通过不等于训练数值通过。检查 `training_graph.dot`、`training_memory.json`、生成的 `net0.c`/`net.cmake` 及无训练配置时的生成物，确认反向路径、保活/内存、源码收集和无训练符号泄漏。

## train-stage5：WS63 训练板测

Host 通过后调用 `hs-verify-op-board verification_kind=training`。输入必须是 `runs/<run_id>/board_expected/training_board_expected_matrix.json` 及其中逐 case expected 文件；该矩阵由 aggregate 阶段从 Host 汇总和 golden 自动导出，不能由板端阶段手工挑选用例。

按 [生成端 observer 说明](../hs-verify-op-board/references/training/generated-observer.md) 核对运行时参数访问接口，由 sample 读取参数并输出训练记录；已有 accessor 不代表 sample 接线或板测已完成。`collect_training_serial.py` 采集并保存原始串口，使用 `training_protocol.py` 解析协议，再由 `compare_training_board.py` 对原始日志或 collector 结果独立复核。采集与比较的命令见 [板端训练脚本说明](../hs-verify-op-board/references/training/commands.md)。

仅收到 `TRAIN_DONE`，或仅看到某个输出张量，不能写 `TRAIN_BOARD_VERIFY=PASS`；必须同时核对 run/case/model 身份、完整 `TRAIN_BEGIN`/`TRAIN_TENSOR`/`TRAIN_DONE` 序列、必测张量集合、checkpoint、参数快照及逐元素数值比较。解析、采集或比较失败要保留为 `FAIL`；缺少必要观测时只能记录 `NOT_RUN` 或未完成状态。

默认检测 SDK、端口和设备；没有板卡或缺少 SDK 时记 `NOT_RUN`，保留检测证据、原因、缺少的前置和重跑步骤。用户明确排除才记 `NOT_REQUESTED`。

板端复用 Host 已通过的全部适用用例、模型、初值、输入/label、训练步数、optimizer 和参考结果。不能用一个代表用例代替矩阵，也不能用 `ModelPredict` 的结果代替训练执行。

若开始执行后构建、烧录、串口或数值检查失败，该阶段为 `FAIL`；尚未执行的后续行仍为 `NOT_RUN`，失败行不能改成未执行。完整张量或参数观测不足时说明缺失项，不能声称完整训练通过。

## train-stage6：文档与最终报告

调用 `hs-design-op-manual verification_kind=training mode=integrated-final`，失败或阻塞时也同步真实结果。设计与验证文档分开保存；实际运行结果只写验证文档。报告列出：

```text
FORWARD_PREREQUISITE=<PASS|FAIL|NOT_RUN>
TRAIN_SOURCE_GATE=<PASS|FAIL|NOT_RUN>
TRAIN_IMPLEMENT_GATE=<PASS|FAIL|NOT_RUN|BLOCKED>
MSLITE_TRAIN_BUILD=<PASS|FAIL|NOT_RUN>
TRAIN_MODEL_GENERATE=<PASS|FAIL|NOT_RUN>
TRAIN_CONVERT_GATE=<PASS|FAIL|NOT_RUN>
TRAIN_GENERATED_ARTIFACTS=<PASS|FAIL|NOT_RUN>
TRAIN_HOST_VERIFY_GATE=<PASS|FAIL|NOT_RUN>
TRAIN_BOARD_VERIFY=<PASS|FAIL|NOT_RUN|NOT_REQUESTED>
TRAIN_OP_MANUAL_SYNC=<PASS|FAIL>
TRAIN_CASE_EXPECTED=<n>
TRAIN_CASE_EXECUTED=<n>
TRAIN_CASE_PASS=<n>
BOARD_CASE_EXPECTED=<n>
BOARD_CASE_EXECUTED=<n>
BOARD_CASE_PASS=<n>
```

`PREPARED` 只表示 prepare 材料完成，不是实现终态；最终报告仍需记录实现和构建是否实际完成。预期拒绝的转换用例单列，不能计为训练数值通过。

最终报告分别列出以下状态，不混用字段：

- 业务结论：读取独立 finalizer 的 `train_final_verdict.json` 中的 `verdict`。其他必需检查通过且板测合法跳过时，默认 `AUTO_ALL` 为 `NOT_VERIFIED`，显式 `HOST_ONLY` 可为 `PASS`；两者均保留 `board_verified=false`。已执行板测失败不能改为跳过，也不能给出业务 PASS。
- 交付状态：原样引用 finalizer 的 `delivery_status`。`HOST_PASS_BOARD_NOT_RUN` 表示已确认 Host 交付、板端未执行，不替代业务 verdict，也不表示板测通过；不要将 `NOT_REQUESTED` 自行改写成该交付标签。
- 阶段状态：阶段失败写 `FAIL`；前置缺失导致无法继续写 `BLOCKED` 并列出恢复条件。板端未执行与用户明确排除分别保留 `NOT_RUN`、`NOT_REQUESTED`。

给出本轮设计/验证文档、用例、工具包、源码 diff、图/内存/生成工程、数值 summary 和板端记录的实际路径。只列真实存在的文件。未支持的框架、冻结功能或未执行的梯度观测必须明确写出，不能隐藏在整体 PASS 中。
