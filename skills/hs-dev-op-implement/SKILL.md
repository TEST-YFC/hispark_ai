---
name: hs-dev-op-implement
description: >-
  Prepare or apply MindSpore Lite Micro operator source changes for HiSpark.AI.
  Use when the user explicitly names this stage-specific skill or explicitly
  requests source-only analysis/implementation with no testing, documentation,
  build, flash, or board verification. It owns source-entry analysis, reuse
  decisions, frozen contracts, seven-layer implementation, INT8 paths, code
  review, and implementation gates. Generic operator requests and combined
  workflows belong to hs-workflow-op-development. 中文触发包括“只实现算子”“仅源码”“使用 hs-dev-op-implement”；
  带测试、文档、编译、烧录或板测的请求不触发本 Skill。
---

# MindSpore Lite 算子实现

本 skill 只负责实现合同和算子源码，不生成正式文档、不执行 Host/板端验证、不构建固件、不烧录，
也不调用其他 Skill。完整适配由 `hs-workflow-op-development` 编排。

## 工作流总览

```text
选择模式
  -> step0 范围/source entry
  -> step1 规格与仓内扫描
  -> step2 grouping、复用/新建和层集裁决
  -> step3 链路、能力清单、contract、计划版 op_spec
     -> mode=prepare: OP_PLAN_GATE=PASS，返回 workflow
  -> workflow integrated-initial + PRE_SOURCE_GATE
     -> mode=apply: step4 源码 -> step5 code review -> step6 quality gate
```

`mode=prepare` 禁止任何源码写入；`mode=apply` 只能在 `PRE_SOURCE_GATE=PASS` 后写入。
`mode=all` 只供用户明确单独调用：prepare 完成后暂停，取得初版文档和门禁证据，再恢复 apply。
顶层 workflow 必须分两次调用 prepare/apply，中间调用 `hs-design-op-manual mode=integrated-initial`；
本 skill 不自行调用文档 Skill。

当顶层 workflow 已在 Stage0 完成唯一环境/SDK/范围确认后，prepare、文档门禁交接、apply、代码审查
和质量检查均由 agent 自动推进，不逐步询问“是否继续”。本 Skill 只有在独立 source-only 调用开始时
确认输入范围；外部权限、缺失 SDK 或无法判定的事实仍按失败回流规则停下并记录原因。

## 调用模式和路由

| 模式 | 范围 | 源码写入 | 终态 |
|---|---|---|---|
| `prepare` | step0-step3 扫描、裁决、合同、能力清单、计划版 `op_spec.py` | 禁止 | `OP_PLAN_GATE=PASS` |
| `apply` | 验证 pre-source 后执行 step4-step6 | 允许 | `IMPLEMENT_GATE=PASS` 或结构化 FAIL |
| `all` | 显式单独调用的 prepare → 外部门禁 → apply | 分段允许 | 两段均有证据 |

用户只说“实现算子 X”但没有明确“只实现、不验证/不构建/不写文档”时，回到
`hs-workflow-op-development`；带有 WS63、测试、编译、文档、烧录或板测的请求一律交给 workflow。
只有明确 source-only 请求才在本 Skill 内停止，并说明不会生成测试、构建、烧录或最终文档。
`explicitly requests source-only work` 是本 Skill 的直接触发边界。

## 职责和任务对象

| 本 skill 负责 | 不负责 | 交给谁 |
|---|---|---|
| source entry、七层链路、grouping、复用/新建裁决 | Host 用例和数值判定 | `hs-verify-op-host` |
| implementation contract、能力清单和计划版 `op_spec.py` | 两份正式算子文档 | `hs-design-op-manual` |
| 七层源码、实现 code style、安全和质量门禁 | 固件构建、烧录、板端精度 | workflow、`hs-dev-build`、`hs-dev-flash`、`hs-verify-op-board` |

source entry 是用户给出的 ONNX/TFLite 前端入口；Primitive、Kernel 和 OpCoder 是
implementation unit。多个入口只有计算/输出语义、dtype/shape、属性映射、输入重排和能力清单
都一致时才能合并；否则分别维护 unit。用户只给通用语义名时默认查证 ONNX 和 TFLite 真实入口，
`FOUND` 才进入 grouping，`NOT_FOUND` 与 `UNREACHABLE` 不混用。

## 工作区和最小交接

每个 unit 使用 `$MSLITE_OP_OUTPUT/<unit>/` 作为 `<opdir>`，不要放进源码树或构建树。运行时核心输出为：

```text
<opdir>/
├── docs/spec.md
├── docs/decision.md
├── docs/link-analysis.md
├── docs/existing-capability-review.md
├── docs/implementation-contract.md
├── docs/source-freeze.json
├── docs/code-style-audit.md
├── docs/reference-impl.md
├── scripts/capability_checklist.json
├── scripts/op_spec.py
└── logs/scan_op_<Op>.log
```

这些是算子运行时产物，不是 Skill 包固定文件。`op_spec.py` 的语义和执行属于 Host Skill；
prepare 必须先按能力清单生成计划版并校验，apply 只核对文档和 `PRE_SOURCE_GATE` 已通过。
代码风格文件是 Skill 自带资源，使用者无需提供或创建同名文件。

## 用户可见任务

阶段完成前先展示证据，再更新 todo；细节参考
[`references/implementation-detail.md`](references/implementation-detail.md)。

```markdown
待办[<implementation_unit>]:
- [ ] step0 确定范围和 source entry
- [ ] step1 扫描规格与仓内现状
- [ ] step2 完成 grouping、复用/新建和层集裁决
- [ ] step3 冻结链路、能力清单、contract 和计划用例
- [ ] step4 编写或修复算子源码
- [ ] step5 完成编码后交叉代码审查
- [ ] step6 通过实现质量门禁
```

## step0：冻结范围

确定 `<opdir>` 和 `<code_root>` 后、任何扫描或源码动作前运行：

```bash
OP_PLAN_RUN_ID="op-plan-<本轮唯一ID>"
python3 <skill_root>/scripts/gate_artifacts.py \
  --opdir <opdir> --op <Op> --stage source-freeze --code-root <code_root> \
  --plan-run-id "$OP_PLAN_RUN_ID" --framework <framework>
```

只有 `SOURCE_FREEZE_GATE=PASS` 才进入 step1。receipt 允许源树起始时已有用户 dirty 状态，
它冻结真实起点；prepare 和 pre-source 会复算同一指纹。每个 framework 首次 freeze 都要列入 scope，
同一 `OP_PLAN_RUN_ID` 不覆盖 receipt；新规划轮次才允许显式 rotate 并归档旧 receipt。

## step1：扫描规格和现状

每个 source entry 单独运行并完整保存输出：

```bash
bash <skill_root>/scripts/scan_op.sh <Op> <code_root>
```

不要用 `head`/`tail` 截断；将日志复制到 `<opdir>/logs/`。规格来源和不可达回退读取
`references/spec-sources.md`。文件存在不等于已注册或可达。

## step2：裁决复用、新建和层集

按需先读 `references/worked-example.md`、`references/decision2-reuse-decision.md` 和
`references/implementation-detail.md`。逐项写 `decision.md`：激活子类型、量化 INT8 豁免、
构造型 fusion、消除/重写 pass、首输入是否为 condition/index，以及每层“做/补/复用/不适用”。
复用必须审查定义点、注册点、调用合同和规格覆盖；不能把一个代表 case 当作全覆盖。

## step3：冻结链路和能力合同

链路固定覆盖 Schema、Parser、Populate/Parameter、Infer、Kernel float/量化 int8/原生 dtype、
OpCoder、Quantizer 和 fusion。每个“已有/复用”项必须有定义与注册/可达证据，并写入
`existing-capability-review.md`。按 `hs-verify-op-host/scripts/operator_spec_template.py` 生成计划版
`<opdir>/scripts/op_spec.py`；每条 case 必须包含明确说明验证目的的非空 `test_point`，每条
`covered_by` 指向真实 case，运行：

```bash
python3 <hs-verify-op-host>/scripts/validate_op_spec.py <opdir>
python3 <skill_root>/scripts/gate_artifacts.py \
  --opdir <opdir> --op <Op> --stage prepare --code-root <code_root> \
  --plan-run-id "$OP_PLAN_RUN_ID" --framework <framework>
```

只有每个 framework 的 `OP_SPEC_GATE=PASS`、`OP_PLAN_GATE=PASS` 且源码指纹未变化，才交给
workflow；`mode=prepare` 必须在此停止，不能调用文档 Skill、step4 或生成源码。

## step4：编写或修复源码

本步骤只允许 `mode=apply`。workflow 必须先调用
`hs-design-op-manual mode=integrated-initial`，生成并审计：

```text
<opdir>/docs/operator-manual-facts.json
<opdir>/docs/{op}-operator-design-doc.md
<opdir>/docs/{op}-operator-verify-doc.md
```

在本轮首次修改任何①-⑦源码前，必须完整读取 Skill 自带的
`references/code-style.md` 和 `references/code-quality-gate.md`，并将规范路径展开为绝对路径，
记录 `CODE_STYLE_SOURCE`、`CODE_STYLE_SOURCE_SHA256`。该规范不是用户需要安装的工具。每一层动笔前完成逐规则审计。之后按
`references/implementation-guide.md` 的对应小节实施；INT8 和 fusion 另读各自 reference。
`PRE_SOURCE_GATE=PASS` 前不能写源码；contract、能力清单、op_spec 或初版文档变化时停止并回到
stage1，不能先改代码再补文档。完整属性审计、七层模板和接口检查见
[`references/implementation-detail.md`](references/implementation-detail.md)。

## step5：编码后交叉代码审查

这是 `IMPLEMENT_GATE` 的组成部分，不是可选的“看一眼 diff”。独立核对注册键、分支可达性、
量化归属、折叠/重写双路径、整数/混合 dtype、死代码和规格覆盖；结果写入
`<opdir>/docs/code-review.md`，并通过 `check_code_review`。完整 JSON 字段和每项证据要求见
[`references/code-review-and-quality.md`](references/code-review-and-quality.md)。没有
`registration_matrix`、`folding_and_rewrite_cases` 或 `semantic_coverage` 的结构化证据不得继续。

## step6：实现质量门禁

按 [`references/code-review-and-quality.md`](references/code-review-and-quality.md) 和
`references/code-quality-gate.md` 完整执行。至少运行：

```bash
bash <skill_root>/scripts/quick_check.sh <code_root>
git -C <code_root> diff --check
```

逐条审计 `CODE_STYLE_SOURCE` 的规则并写入 `<opdir>/docs/code-style-audit.md`；
需要 `CODE_STYLE_AUDIT=PASS`、`CODE_STYLE_GATE=PASS` 和 `SECURITY_GATE=PASS`。本专项的
`IMPLEMENT_GATE=PASS` 只表示源码实现与静态质量门禁通过，不表示构建、Host、文档、烧录或板测通过。

## 失败修复与交接

保存首个真实错误，按 parser/infer/kernel/opcoder/quantizer/工具链分类，查
`references/troubleshooting.md` 和 `references/lessons.md`，定位最小根因后重跑质量门禁。
实现、模型/spec、工具链和固件接线分别回流各自 owner；不删除能力、不降低阈值、不改 GT。
同一能力连续两次有证据的方案失败时暂停并交用户裁决。完整循环和输出格式见
[`references/recovery.md`](references/recovery.md)。

结束时至少输出：

```text
IMPLEMENT_GATE=<PASS|FAIL>
implementation_unit=<name>
source_entries=<list>
changed_files=<list>
CODE_STYLE_SOURCE=<absolute path>
CODE_STYLE_SOURCE_SHA256=<sha256>
CODE_STYLE_AUDIT=<PASS|FAIL>
capability_checklist=<absolute path>
opdir=<absolute path>
next_owner=hs-workflow-op-development
```

## 资源索引

| 资源 | 何时读取 |
|---|---|
| `scripts/scan_op.sh`、`scripts/gate_artifacts.py` | step0/step1/step3 机械门禁 |
| `scripts/fetch_op_spec.py` | step1/step3 规格存在性和属性摘要（由扫描流程调用，也可按需直接复核） |
| `scripts/fetch_ref_impl.py` | step2/step4 上游参考实现的镜像链取材 |
| `scripts/quick_check.sh` | step6 快速预检 |
| `../hs-verify-op-host/scripts/operator_spec_template.py`、`validate_op_spec.py` | step3 计划版 spec |
| [`references/implementation-detail.md`](references/implementation-detail.md) | step2/step4 详细规则 |
| [`references/code-review-and-quality.md`](references/code-review-and-quality.md) | step5/step6 结构化审查和质量门禁 |
| [`references/implementation-guide.md`](references/implementation-guide.md) | step4 七层代码模板 |
| [`references/int8-coder-conventions.md`](references/int8-coder-conventions.md) | INT8 kernel/opcoder |
| [`references/optimizer-fusion-template.md`](references/optimizer-fusion-template.md) | fusion |
| [`references/code-quality-gate.md`](references/code-quality-gate.md)、[`references/code-style.md`](references/code-style.md) | 质量门禁与团队规范 |
| [`references/spec-sources.md`](references/spec-sources.md)、[`references/troubleshooting.md`](references/troubleshooting.md)、[`references/lessons.md`](references/lessons.md) | 规格来源和失败回流 |
| [`references/worked-example.md`](references/worked-example.md)、[`references/decision2-reuse-decision.md`](references/decision2-reuse-decision.md) | 复用裁决示例 |
