---
name: hs-dev-train-op-implement
description: >-
  Implement or repair FP32 backward operator support in the MindSpore Lite Micro TrainingGraph pipeline for HiSpark.AI, including forward-prerequisite checks, backward contracts, GradRule registration, TrainNodeCoder lowering, NNACL fp32_grad kernels, generated training C inspection, branch gradient accumulation boundaries, and implementation quality gates. Use this leaf skill only when the user explicitly names hs-dev-train-op-implement, asks only to implement/debug training or backward operator code, or hs-workflow-train-op-development routes a training implementation defect here. Generic inference operator requests belong to hs-workflow-op-development or hs-dev-op-implement.
---

# MindSpore Lite Micro 训练算子实现

本 skill 只负责 FP32 训练反向算子的源码实现和实现质量门禁。普通 forward/parser/kernel/opcoder 缺口回流 `hs-dev-op-implement`；完整训练算子交付由 `hs-workflow-train-op-development` 编排。

训练反向支持通常涉及三层：

```text
① GradRule  ② TrainNodeCoder  ③ NNACL fp32_grad kernel
```

路径以 MindSpore Lite 代码根为基准，即包含 `tools/converter/micro/coder/train/` 和 `src/litert/kernel/cpu/nnacl_c/` 的目录。HiSpark.AI 仓库中的常见位置是 `src/mindspore-lite/mindspore-lite/`。

## 职责边界

| 本 skill 负责 | 本 skill 不负责 | 交给谁 |
|---|---|---|
| 确认 forward primitive 和 Micro forward codegen 已可用 | 新增普通推理 parser/kernel/opcoder | `hs-dev-op-implement` |
| 冻结 backward contract | 训练 Host 数值矩阵签收 | `hs-workflow-train-op-development` |
| 实现 GradRule、TrainNodeCoder、NNACL fp32_grad | 正式算子文档发布 | `hs-design-op-manual` 或训练文档阶段 |
| 检查 generated training C 所需源码收集 | WS63 固件构建、烧录、板测 | 父 workflow 及对应 build/flash/board skill |
| 输出实现交接单和质量门禁结论 | 修改 TrainingGraph、scheduler、memory planning 框架 | 先停止并向用户说明框架级需求 |

普通单输出 backward 算子不得修改 `TrainingGraph`、调度器或内存规划。若能力需要多 loss、多 forward output 保活、动态 shape/rank、新 workspace lifetime、算子特有 alias 或影响推理分配/codegen 的框架改动，先停止并把需求升级给用户确认。

## 用户可见进度

```markdown
待办[<training_unit>]:
- [ ] step0 确定训练范围和 forward 前置
- [ ] step1 冻结 backward contract
- [ ] step2 实现或修复 GradRule
- [ ] step3 实现或修复 TrainNodeCoder
- [ ] step4 新增或复用 NNACL fp32_grad kernel
- [ ] step5 通过训练实现质量门禁
```

阶段完成前先展示门控证据，再勾选 todo。

## 工作区和交接产物

每个 training unit 使用 `$MSLITE_OP_OUTPUT/train_<unit>/` 作为 `<opdir>`。缺省位置与 mindspore-lite 仓平级；不要放进源码树或构建树。

```text
<opdir>/
├── docs/
│   ├── forward-prerequisite.md
│   ├── backward-contract.md
│   ├── train-link-analysis.md
│   ├── implementation-contract.md
│   └── generated-code-inspection.md
├── scripts/
│   └── train_capability_checklist.json
└── logs/
```

父 workflow 或训练验证 skill 可以在同一 `<opdir>` 下补充 `training_graph.dot`、`training_memory.json`、generated project、数值对齐日志和 summary；本 skill 不伪造验证 PASS。

## step0：确定范围和 forward 前置

先确认仓库根和 `git status --short`。保留无关 staged、unstaged、untracked 工作。

不要假设 ONNX 名称会保留到 `CoderGraph`。Squeeze、Unsqueeze 等 converter 优化后可能变成 Reshape；必须追踪 parser 和优化后的真实 forward primitive。

只有以下 forward 前置均有证据时，才能实现 backward：

- parser、primitive、populate、infer-shape、Micro forward coder 已支持；
- 生成 forward C 可编译运行；
- forward tensor shape、dtype、layout 和可选属性与训练合同一致。

forward 不通时，输出 `TRAIN_IMPLEMENT_GATE=FAIL reason=forward-prerequisite`，回流 `hs-dev-op-implement`；不要在训练实现里顺手补普通推理链路。

## step1：冻结 backward contract

写入 `<opdir>/docs/backward-contract.md` 后才能改源码。必须覆盖：

- differentiable input indices；
- trainable input indices；
- retained forward input values；
- required forward outputs；
- `dy -> dx/dw/db` 的 shape 和 dtype；
- optional inputs、fused attributes、axes、permutation、mode；
- 支持的静态 rank、dimension、broadcasting；
- kernel 输入输出地址是否允许 alias；
- branch fan-out 与梯度累加行为。

结构张量不得标为可微，包括 shape、axes、pads、begin/end、permutation。刻意不支持的组合在转换期返回 `RET_NOT_SUPPORT`，不能生成目标端才失败的 C。

详细分类先读 [references/operator-patterns.md](references/operator-patterns.md)。

## step2：实现 GradRule

修改 `tools/converter/micro/coder/train/` 下 FP32 GradRule registry。

- 元数据足以表达导数时使用 `IndexedGradRule`。
- 只有属性或拓扑影响梯度构造时才新增专用 rule。
- rule 必须确定性、无副作用；builder 可能先在没有 output gradient IDs 的情况下调用一次。
- `differentiable_input_indices` 只表示 upstream activation gradients。
- `trainable_input_indices` 表示 optimizer parameter gradients。
- `retained_input_indices` 表示 backward 需要保活的 forward 输入。

如果 backward 需要 forward output，必须确认 builder 会加入 `required_forward_tensor_ids`。当前通用 rule result 没有 retained-output 字段，不要仅调用 `ForwardAddr(output)` 并假设内存仍然有效。

只有存在可执行 TrainNodeCoder 的能力才能注册 GradRule。

## step3：实现 TrainNodeCoder

在 `tools/converter/micro/coder/train/opcoders/` 下实现，并用 `kBackward + PrimitiveType` 注册。

`Prepare()` 必须：

- 校验 forward input/output 数量和位置匹配的 gradient IDs；
- 使用通用 FP32、static shape、非空 tensor 检查；
- 校验 rank、shape、attributes、constants、optional inputs；
- 匹配 gradient bytes 与对应 forward tensor；
- 错误信息包含 node name，并在转换期清晰失败。

`DoCode()` 必须：

- forward value 只通过 `ForwardAddr()` 解析；
- gradient 只通过 `GradAddr()` 解析；
- 用 `OutputGradForTensor()` 找到目标 tensor 的 output grad；
- 收集精确 kernel header 和 source；
- 通过 `Serializer` 输出一个 tagged code block；
- 只对有有效 status return 的 kernel 使用 `CodeFunctionWithCheck()`。

不要分配 runtime buffer，不要硬编码 `m0_buffer` offset，不要在 generated C 里重复数值循环，不要在算子 coder 内手写 branch gradient accumulation。

## step4：实现 NNACL FP32 gradient kernel

新增或复用 `src/litert/kernel/cpu/nnacl_c/fp32_grad/` 下纯 C kernel。

- 优先使用小型无状态接口。
- 静态合法性检查放在 TrainNodeCoder `Prepare()`。
- 文档化可选 `NULL` 参数和 alias 行为。
- 不使用 heap allocation 或持久状态。
- 数值公式要能脱离 TrainingGraph 独立测试。

新增 TrainNodeCoder 源码要加入 Micro 显式 CMake 列表。确认 generated project 在源码树外编译时能收集到 header/source。

## step5：训练实现质量门禁

最低证据顺序：

```bash
git diff --check
bash incremental_build.sh
```

只能使用仓库的 `incremental_build.sh` 构建框架，不自定义 full build。随后至少检查正反转换用例、`training_graph.dot`、`training_memory.json`、generated `net0.c`/`net.cmake`、generated host-native build。数值证明由训练验证阶段完成；转换成功不能声明为数值 PASS。

只有以下条件同时满足才输出：

```text
TRAIN_IMPLEMENT_GATE=PASS unit=<training_unit>
```

- forward 前置产物存在且一致；
- backward contract、train link analysis、implementation contract、train capability checklist 互相一致；
- GradRule、TrainNodeCoder、NNACL kernel 和 CMake 收集均可映射到能力；
- `git diff --check` 和仓库增量构建没有真实 FAIL；
- 没有 common TrainingGraph 或 memory code 的普通算子越权改动；
- 没有构建、Host 数值、文档、flash 或 board 的虚假完成声明。

## 失败修复与交接

父 workflow 回流训练实现缺陷时，先贴首个失败原文并归类到 GradRule、TrainNodeCoder、NNACL kernel、generated source collection、training memory 或 forward prerequisite。呈现根因和最小修复后才改代码。

结束时输出：

```text
TRAIN_IMPLEMENT_GATE=<PASS|FAIL>
training_unit=<name>
forward_primitive=<PrimitiveType>
changed_files=<list>
train_capability_checklist=<absolute path>
opdir=<absolute path>
next_owner=hs-workflow-train-op-development
```

## 资源索引

| 资源 | 何时读取 |
|---|---|
| `references/operator-patterns.md` | step1 前分类 backward 模式、branch 和不支持边界 |
| `references/training-implementation-guide.md` | step2-step4 实现细节和常见落点 |
