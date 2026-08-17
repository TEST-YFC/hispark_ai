---
name: hs-workflow-train-op-development
description: >-
  End-to-end workflow for adding, adapting, or debugging MindSpore Lite Micro FP32 training/backward operator support on HiSpark.AI, from forward-prerequisite validation and backward contract through GradRule, TrainNodeCoder, NNACL fp32_grad implementation, framework build, generated training graph/memory inspection, host-native generated C execution, one-step numerical training comparison, documentation, and optional board verification. This is the default top-level skill for generic requests such as “训练算子”, “反向算子”, “backward op”, “GradRule”, “TrainNodeCoder”, “支持 xxx 梯度”, or requests combining training implementation with verification.
---

# 训练算子端到端工作流

本 skill 负责编排训练算子交付，不重复实现 leaf skill 的专业逻辑。训练 workflow 与推理 workflow 并列：推理 workflow 交付 forward，训练 workflow 交付 backward/training graph。

```text
确认 forward 前置
        ↓ forward 缺失时回流
hs-dev-op-implement / hs-workflow-op-development
        ↓ forward 已支持
hs-dev-train-op-implement
        ↓ TRAIN_IMPLEMENT_GATE
MindSpore Lite 训练工具包构建
        ↓ MSLITE_TRAIN_PKG
训练 Host 验证：graph / memory / generated C / one-step numerical
        ↓ TRAIN_HOST_VERIFY_GATE
文档同步
        ↓ TRAIN_OP_MANUAL_SYNC
（用户要求且板卡可用）固件接入 → 构建 → 烧录 → 板端训练验证
```

## 路由优先级

1. 用户明确点名 skill，或明确说“只做某阶段”时，优先使用对应 leaf，不启动本 workflow。
2. 用户泛化地说“训练算子”、“反向算子”、“backward”、“梯度”、“GradRule”、“TrainNodeCoder”时，默认启动本 workflow。
3. 用户只说“新增/支持/适配算子”且没有训练语义时，使用 `hs-workflow-op-development`。
4. forward 缺失不是训练实现任务；回流推理 workflow 或 `hs-dev-op-implement`。

## 用户可见阶段

```markdown
状态: train-stage<n> 进行中
待办:
- [ ] train-stage0 冻结训练范围、forward 前置和环境
- [ ] train-stage1 实现 backward 源码
- [ ] train-stage2 构建 MindSpore Lite 训练工具包
- [ ] train-stage3 生成并检查训练图、内存和 generated C
- [ ] train-stage4 执行 Host-native 训练数值验证
- [ ] train-stage5 生成或同步文档
- [ ] train-stage6 可选：板端训练验证
```

未连接板卡或用户未要求板测时，train-stage6 标记“未请求/板卡不可用，Host 训练验证已完成”，不伪装成 PASS，也不阻塞 Host 侧训练交付。

## train-stage0：冻结训练范围和环境

记录 source entry、forward primitive、training unit、代码根、`MSLITE_OP_OUTPUT`、是否要求文档、是否要求板测、板卡是否连接，以及 leaf skill 可用性。

建立环境基线：

- 仓库根和 `git status --short`；
- MindSpore Lite 主仓/子模块 HEAD；
- 当前 converter 路径和 `MSLITE_PKG`；
- 是否存在可复用的 forward Host PASS case；
- 是否存在可复用的一步训练 PASS case。

先验证 forward prerequisite。若 parser、primitive、populate、infer、Micro forward coder 或 generated forward C 不通，记录 `FORWARD_PREREQUISITE=FAIL` 并回流推理实现；不要进入 backward 编码。

没有训练控制用例时记录 `TRAIN_ENV_BASELINE=UNKNOWN reason=no-known-pass-case`，不得伪称环境已验证。若多个无关训练用例在 converter 启动阶段成片失败，先补跑控制用例或重建工具包，不允许直接盲改训练算子源码。

## train-stage1：实现 backward 源码

调用 `hs-dev-train-op-implement`，传递明确的 training unit、forward primitive 和能力边界。

只有每个 training unit 返回：

```text
TRAIN_IMPLEMENT_GATE=PASS
```

才进入 train-stage2。

实现阶段若发现 forward 合同信息不足，补的是 forward prerequisite 证据和 backward contract；不要越权代写训练数值 PASS 或正式文档。

## train-stage2：构建 MindSpore Lite 训练工具包

使用仓库已有 `incremental_build.sh`。不要调用自定义 full build。

构建前复核 `hs-dev-train-op-implement` 的实现质量门禁，防止 stage1 之后的修改绕过检查。

成功证据是新鲜的训练可用 converter/package：

```text
MSLITE_TRAIN_BUILD=PASS
MSLITE_TRAIN_PKG=<absolute path>
```

构建失败按首个真实错误归属：

| 证据指向 | 回流所有者 |
|---|---|
| GradRule、TrainNodeCoder、NNACL kernel、CMake 收集错误 | `hs-dev-train-op-implement` |
| forward parser/infer/kernel/opcoder 错误 | `hs-dev-op-implement` |
| 工具链、包新鲜度、子模块漂移或非本次文件错误 | train-stage2 环境分支 |

修复后重新执行训练实现门禁和构建，不复用旧包。

## train-stage3：训练 Host 验证

运行正向和负向转换用例，检查训练 generated artifacts，并构建执行 generated host-native code。本阶段由训练 workflow 自己持有；在仓库出现稳定、可复用的训练 harness 前，不单独拆成验证 leaf。

必须查看并记录：

- `training_graph.dot`：Backward 节点和 GradAccum connectivity；
- `training_memory.json`：bytes、lifetime、retained forward activations；
- generated `net0.c`：实际 fp32_grad kernel call；
- generated `net.cmake`：新增 header/source 是否被收集；
- inference-only conversion：没有 gradient symbol 或 fp32_grad source 泄漏。

转换成功只能说明结构路径可达，不能声明数值正确。结构检查失败先按证据归类，不直接改测试。

## train-stage4：Host-native 训练数值验证签收

构建并执行 generated host-native code，至少跑一个训练 step，并与参考框架对比：

- logits 或 forward output；
- loss；
- activation gradients；
- trainable parameter gradients；
- updated weights。

比较必须绑定同一模型、同一输入、同一初始权重、同一 loss、同一 optimizer 参数和同一随机种子。

只有结构检查和数值比较均 PASS，才能签收：

```text
TRAIN_HOST_VERIFY_GATE=PASS
```

不要把 conversion-only PASS 或 build-only PASS 写成训练数值 PASS。

## train-stage5：文档同步

训练 Host 全绿后同步文档。若现有 `hs-design-op-manual` 不支持训练章节，先输出训练实现和验证摘要，不强行套普通推理四章节模板。

文档至少应包含：

- forward prerequisite；
- backward contract；
- GradRule / TrainNodeCoder / NNACL fp32_grad 落点；
- 支持与拒绝的 shape、rank、attribute、broadcast、alias 边界；
- generated graph/memory/code evidence；
- 一步训练数值对齐结果。

阻塞或硬停时只生成草稿或摘要，不能发布 final。

## train-stage6：可选板端训练验证

只在用户要求且板卡/SDK 条件可用时执行。复用 train-stage4 已 PASS 的代表性 case，保持同一模型、输入、初始权重和 GT。

烧录成功不等于板端训练正确。板端验证至少需要完整串口输出和 host GT 对比；没有板卡、串口不可用或用户不在板边时，保留 Host 完成状态并标记板端子任务未执行。

## 完成判据

Host 训练交付完成必须满足：

- `FORWARD_PREREQUISITE=PASS`；
- 每个 training unit 的 `TRAIN_IMPLEMENT_GATE=PASS`；
- 新鲜训练工具包构建成功；
- generated graph/memory/code 检查通过；
- `TRAIN_HOST_VERIFY_GATE=PASS`；
- 文档同步为 final 或明确记录文档阶段未请求。

用户明确要求板测时，另需板端训练验证 PASS。

## 统一结案报告

```text
TRAIN_OP_WORKFLOW=<PASS|FAIL|HOST_PASS_BOARD_NOT_RUN>
FORWARD_PREREQUISITE=<PASS|FAIL>
TRAIN_IMPLEMENT_GATE=<PASS|FAIL>
MSLITE_TRAIN_BUILD=<PASS|FAIL>
TRAIN_GENERATED_ARTIFACTS=<PASS|FAIL>
TRAIN_HOST_VERIFY_GATE=<PASS|FAIL>
TRAIN_OP_MANUAL_SYNC=<PASS|FAIL|NOT_REQUESTED>
TRAIN_BOARD_VERIFY=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
```

报告同时给出源码 diff、`MSLITE_TRAIN_PKG`、`training_graph.dot`、`training_memory.json`、generated project、数值对齐 summary、文档和板端日志的绝对路径。只报告真实存在且属于本轮的产物。
