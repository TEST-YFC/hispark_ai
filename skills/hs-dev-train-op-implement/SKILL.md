---
name: hs-dev-train-op-implement
description: >-
  Implement or repair FP32 backward operator support in the MindSpore Lite Micro TrainingGraph pipeline for HiSpark.AI.
  This training implementation skill owns forward-prerequisite and training-framework capability checks, GradRule, TrainNodeCoder,
  NNACL fp32_grad, generated training C inspection, and implementation gates. Use it only when the user explicitly
  names hs-dev-train-op-implement, requests training/backward source work, or hs-workflow-train-op-development routes
  a training implementation defect. Generic inference operator work belongs to hs-dev-op-implement.
---

# MindSpore Lite Micro 训练算子实现

本技能负责训练反向源码和源码集成检查，不执行完整训练数值验证。权重冻结是否可用，须先检查当前框架。
完整训练交付由 `hs-workflow-train-op-development` 编排；训练数值由 `hs-verify-op-host` 的 training 模式负责。
普通推理 parser、primitive、populate、infer-shape、forward kernel 或 forward coder 缺口回流
`hs-dev-op-implement`，不要在本技能内顺手补齐。

## 调用模式

必须显式选择 `mode`：

| 模式 | 执行范围 | 是否允许源码写入 |
|---|---|---|
| `prepare` | step0、step1；建立前置检查、训练链路说明和实现计划 | 否 |
| `apply` | 先检查设计文档和 prepare 产物，再执行 step2、step3、step4、step5 | 是 |

独立源码请求也必须先执行 `mode=prepare`。集成工作流的 `mode=apply` 必须先检查正式设计文档；独立且明确只做源码的请求先完成内部设计材料，不额外发布两份正式文档。
上层工作流 必须在 prepare 之后完成设计文档，再调用 apply。`prepare` 阶段发现阻断时停止，不写源码。

## 职责边界

| 本技能负责 | 本技能不负责 | 交给谁 |
|---|---|---|
| 检查 forward 和训练框架前置能力 | 新增普通推理 parser/kernel/opcoder | `hs-dev-op-implement` |
| 编写 GradRule、TrainNodeCoder、NNACL fp32_grad | Host 训练数值矩阵和参考值确认 | `hs-verify-op-host` training |
| 检查冻结链路的 parser、选择器、可选梯度地址、memory、导出和 kernel 能力 | 修改 TrainingGraph、scheduler、memory planning 等公共框架 | 用户确认后的框架变更方案 |
| 检查 generated training C、源码收集和实现质量 | 固件构建、烧录、串口和板端确认 | 上层工作流及对应 build/flash/board skill |
| 输出实现交接结果 | 正式设计/验证文档发布 | `hs-design-op-manual` 或训练文档阶段 |

普通单输出 backward 算子不得修改公共 TrainingGraph、调度器或内存规划。若需求依赖多 loss、多 forward
output 保活、动态 shape/rank、新 workspace lifetime、算子特有 alias，或影响推理分配/codegen，必须先停止并
请求用户确认框架级变更。

## 用户可见进度

```markdown
待办[<training_unit>][mode=<prepare|apply>]:
- [ ] step0 范围、forward 前置和冻结能力检查
- [ ] step1 反向传播说明、训练链路和实现计划
- [ ] step2 实现或修复 GradRule
- [ ] step3 实现或修复 TrainNodeCoder
- [ ] step4 新增或复用 NNACL fp32_grad kernel
- [ ] step5 通过训练实现质量检查并交接
```

阶段完成前先展示证据，再勾选 todo。

## 工作区和交接产物

每个 training unit 使用 `$MSLITE_OP_OUTPUT/train_<unit>/` 作为 `<opdir>`。缺省位置与 mindspore-lite 仓库平级，
不要放进源码树或构建树。prepare 必须产出或更新以下分析材料；apply 在材料检查通过后才能写源码，集成模式还需检查正式设计文档。`generated-code-inspection.md` 在 prepare 阶段只列检查计划，尚未生成或运行的项目写 `NOT_RUN`，实际结果在转换后补齐。

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

上层工作流或训练验证 skill 可以在同一 `<opdir>` 补充 `training_graph.dot`、`training_memory.json`、generated
project、数值对齐日志和 summary；本技能不伪造数值 PASS。

## step0：范围、forward 前置和冻结能力检查

先确认代码根、目标算子、请求模式、`git status --short` 和当前工作树已有改动。保留无关 staged、unstaged、
untracked 工作，不执行清理或还原。

不要假设框架输入名称会保留到 `CoderGraph`；必须追踪 parser、优化后的真实 forward primitive、forward coder
和 generated C。确认 parser、primitive、populate、infer-shape、Micro forward coder、静态 shape/dtype/layout
和可选属性边界均有证据，且生成的 forward C 可在源码树外编译运行。forward 不通时输出：

```text
TRAIN_IMPLEMENT_GATE=FAIL reason=forward-prerequisite
next_owner=hs-dev-op-implement
```

### 冻结能力是独立的 step0 检查

只要用户任务包含冻结、部分冻结、不可更新权重或 `frozen_node`，必须逐项检查并记录真实文件和行号：

1. **config parser**：是否接受冻结配置、写入训练参数、未知键是否明确拒绝。
2. **node weight selection**：是否按真实 forward node name 选择权重，而不是 coder/kernel 自己解析配置。
3. **TrainingGraphBuilder**：冻结参数是否省略 parameter grad 但保留所需 activation grad/backward node。
4. **OptionalGradAddr/helper**：缺失的 dW/dB 是否能表达为合法 `NULL`，并与地址解析失败的空字符串区分。
5. **TrainNodeCoder**：Prepare 只检查实际存在的可选梯度，DoCode 不把缺失 dW 当成错误。
6. **MemoryAnalyzer**：冻结权重是否没有 optimizer state 和 mutable train-weight update buffer；同时单独记录
   canonical RAM/default weight 是否仍保留。
7. **Kernel**：每个可选输出逐一判空；不能在判空前清零、读取或写入该指针。
8. **ExportWeight**：导出对象、运行时 mutable 地址、manifest 和快照是否能区分“存在但不更新”与“未导出”。

冻结验收不得把“canonical 权重仍有 RAM 段”误报为“权重可更新”，也不得把“导出文件缺席”直接当成
“训练前后不变”。必须有实际训练前/后权重快照，按名称、shape、dtype、元素数对齐；冻结参数的快照缺失时，
不能确认不变。至少应观察：训练图、`training_memory.json`、生成 C、ExportWeight/manifest（如启用）以及
训练前后实际权重数据。

若冻结能力任一关键环节缺失，且用户任务要求冻结，立即输出：

```text
TRAIN_IMPLEMENT_GATE=BLOCKED reason=weight-freezing-framework-capability-missing
requires_user_confirmation=framework-change
next_owner=user
```

不得通过本技能修改公共框架来“顺手支持冻结”。若用户任务不要求冻结，则继续普通非冻结覆盖，但输出中必须
明确 `weight_freezing=NOT_REQUESTED`；能力缺失另记 MISSING，未检查另记 NOT_RUN，不把“未请求”写成“不支持”。详细责任、判空和交接要求见
[references/weight-freezing.md](references/weight-freezing.md)。

step0 还要按输入、输出、属性和既有模式把 backward 归类为 shape-only、elementwise、broadcast/reduction、
index/slice、multi-input/multi-output、parameter-gradient 或 framework-special。优先复用已有能力。

## step1：反向传播说明和实现计划

先写入 `<opdir>/docs/backward-contract.md`，再进入源码修改。必须逐项说明：

- differentiable input indices；
- trainable input indices；
- retained forward input values；
- required forward outputs；
- `dy -> dx/dw/db` 的 shape 和 dtype；
- optional inputs、fused attributes、axes、permutation、mode；
- 支持的静态 rank、dimension、broadcasting；
- kernel 输入输出地址是否允许 alias；
- branch fan-out 与梯度累加行为；
- forward prerequisite 的证据路径。

结构张量不得标为可微，包括 shape、axes、pads、begin/end、permutation。刻意不支持的组合必须在转换期返回
`RET_NOT_SUPPORT`，不能让目标端生成 C 后才失败。

step1 必须形成实现约束、训练调用关系说明和能力清单，保留原有文件名。详细分类读取 [算子模式](references/operator-patterns.md)。`mode=prepare` 到此结束，
不得修改源码；输出 `TRAIN_IMPLEMENT_GATE=PREPARED`。集成模式设计文档缺失、所需冻结能力阻断或 forward 前置失败时，
不得进入 apply。

## step2：实现 GradRule

修改 `tools/converter/micro/coder/train/` 下 FP32 GradRule registry。

- 元数据足以表达导数时使用 `IndexedGradRule`。
- 只有属性或拓扑影响梯度构造时才新增专用 rule。
- rule 必须确定性、无副作用；builder 可能先在没有 output gradient IDs 的情况下调用一次。
- `differentiable_input_indices` 只表示 upstream activation gradients。
- `trainable_input_indices` 表示 optimizer parameter gradients。
- `retained_input_indices` 表示 backward 需要保活的 forward 输入。
- 不得在 GradRule、coder 或 kernel 读取冻结配置；冻结决策只来自已经构造好的 TrainingGraph。

如果 backward 需要 forward output，必须确认 builder 会加入 `required_forward_tensor_ids`。当前通用 rule result 没有 retained-output 字段，不能只调用
`ForwardAddr(output)` 并假设内存仍然有效。只有存在可执行 TrainNodeCoder 的能力才能注册 GradRule。

## step3：实现 TrainNodeCoder

在 `tools/converter/micro/coder/train/opcoders/` 下实现，并用 `kBackward + PrimitiveType` 注册。

`Prepare()` 必须校验 forward 输入输出数量、位置匹配的 gradient IDs、FP32、静态且非空 tensor、rank、shape、属性、常量和 optional input；gradient bytes 必须与对应 forward tensor 匹配，错误信息包含 node name，并在转换期清晰失败。对可能因冻结而不存在的 dW/dB，只在 ID 有效时检查；合法缺失
必须继续生成，不得把 `NULL` 当成地址解析错误。

`DoCode()` 必须：

- forward value 只通过 `ForwardAddr()` 解析；
- 必选梯度通过 `GradAddr()`；dX 是否必需由训练图的上游需求决定，不一律强制存在；
- 可能不存在的 dX/dW/dB 通过 `OptionalGradAddr` 或等价 helper；无效 gradient ID 映射为字符串 `NULL`，地址解析
  失败仍是错误；
- 用 `OutputGradForTensor()` 找到目标 tensor 的 output grad；
- 收集精确 kernel header/source，并通过 `Serializer` 输出一个 tagged code block；
- 只对有有效 status return 的 kernel 使用 `CodeFunctionWithCheck()`；
- 不分配 runtime buffer，不硬编码 `m0_buffer` offset，不在生成 C 中重复数值循环，不在算子 coder 内手写 branch gradient accumulation。

若当前框架没有 `OptionalGradAddr` 或等价能力，冻结任务必须在 step0 BLOCKED；不得在单个算子 coder 内私造
与框架不一致的冻结语义。

## step4：实现 NNACL FP32 gradient kernel

新增或复用 `src/litert/kernel/cpu/nnacl_c/fp32_grad/` 下纯 C kernel。

- 优先使用小型无状态接口；静态合法性检查放在 `Prepare()`。
- 每一个可选输出（例如 dX、dW、dB）独立判空，判空前不得读、写、清零该地址。
- 文档化可选 `NULL` 参数和 alias 行为；不使用 heap allocation 或持久状态。
- 数值公式可脱离 TrainingGraph 独立测试，但本技能不确认训练数值。
- 新增 TrainNodeCoder 源码必须加入 Micro 显式 CMake 列表，并确认 generated project 在源码树外能收集 header/source。

## step5：训练实现质量检查和交接

最低证据顺序：

```bash
git diff --check
bash <mslite-workflow-skill>/scripts/build_mslite.sh --run-id <run_id> <mindspore-lite-root>
```

优先使用增量构建；首次没有可复用的构建配置时，使用同一脚本的全量模式（`--full`）。不得要求仓库中不存在的 `incremental_build.sh`，也不要绕过 `build_mslite.sh` 直接运行 `make` 或 `build.sh`。脚本记录源码身份、工具包打包和解包结果；训练构建并发默认按 CPU 和可用内存估算；资源不足时按真实日志降低并记录原因。随后至少检查正反转换、`training_graph.dot`、
`training_memory.json`、generated `net0.c`/`net.cmake` 和 generated host-native build。转换成功不是数值 PASS。
数值交给 `hs-verify-op-host` 的 training 模式；不要把推理 Host/板端结果当作训练结果。

源码 apply 阶段先输出 `TRAIN_SOURCE_GATE=PASS`；此时 `TRAIN_IMPLEMENT_GATE=NOT_RUN`，因为工具包、转换和生成代码尚未完成。完成后续构建、转换、生成工程和 native build 后，再回到本步骤核对以下条件；全部满足才输出 `TRAIN_IMPLEMENT_GATE=PASS`：

- forward 前置、反向传播说明、训练调用关系、实现约束和能力清单一致；集成模式还需与正式设计文档一致；
- GradRule、TrainNodeCoder、NNACL kernel 和 CMake 收集可映射到能力；
- `git diff --check` 和增量构建均已执行且通过，正反转换、生成图/内存/源码检查与 native 构建证据完整；未执行不能算通过；
- 没有公共 TrainingGraph、scheduler 或 memory code 的普通算子越权修改；
- 没有构建、Host 数值、flash、board 或冻结快照的虚假完成声明。

若任务包含冻结，还必须交接冻结检查结果：`freezing_capability=AVAILABLE|MISSING|NOT_RUN`、实际快照路径、
训练图和内存 dump 路径、ExportWeight/manifest 路径（如启用）以及未解决的框架缺口。没有实际快照不得写
`frozen_weights_unchanged=PASS`。

## 失败修复与交接

先贴首个失败原文并归类到 parser、forward prerequisite、GradRule、TrainNodeCoder、NNACL kernel、generated
source collection、training memory、weight-freezing framework capability 或 verification handoff。呈现根因和
最小修复后才改代码。框架级缺口必须停止并交用户确认，不得降级成普通算子实现后隐瞒冻结未支持。

结束时输出：

```text
TRAIN_SOURCE_GATE=<PASS|FAIL|NOT_RUN>
TRAIN_IMPLEMENT_GATE=<PREPARED|PASS|FAIL|NOT_RUN|BLOCKED>
training_unit=<name>
mode=<prepare|apply>
forward_primitive=<PrimitiveType>
weight_freezing=<AVAILABLE|MISSING|NOT_RUN|NOT_REQUESTED>
changed_files=<list>
train_capability_checklist=<absolute path>
opdir=<absolute path>
next_owner=<hs-verify-op-host training|hs-workflow-train-op-development|user>
```

## 资源索引

| 资源 | 何时读取 |
|---|---|
| `references/operator-patterns.md` | step1 前分类 backward 模式、branch 和不支持边界 |
| `references/training-implementation-guide.md` | step2–step4 实现细节和常见落点 |
| `references/weight-freezing.md` | step0 冻结能力矩阵、判空规则、canonical RAM/可更新性和验收交接 |
