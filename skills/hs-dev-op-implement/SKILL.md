---
name: hs-dev-op-implement
description: >-
  Implement or repair MindSpore Lite Micro operator source code for HiSpark.AI, including source-entry analysis, PrimitiveType reuse decisions, parser/populate/infer/kernel/opcoder/quantizer changes, INT8 paths, and implementation quality gates. Use this leaf skill only when the user explicitly names hs-dev-op-implement, asks to only analyze or implement operator code, or an operator workflow routes an implementation defect back here. Generic requests such as “适配一个算子”, “新增算子”, “支持算子”, “port an operator”, or requests that also include testing, documentation, build, flash, or board verification belong to hs-workflow-op-development instead.
---

# MindSpore Lite 算子实现

本 skill 只负责两件事：分析算子实现缺口，以及生成或修复 MindSpore Lite 算子源码。它不生成正式设计文档，不拥有测试用例，不构建 WS63 固件，不烧录开发板，也不调用其他 skill。完整适配由 `hs-workflow-op-development` 编排。

算子最多涉及七类代码能力，但不是每个算子都要新建七层：

```text
① Schema  ② Parser  ③ Populate  ④ Infer  ⑤ Kernel  ⑥ OpCoder  ⑦ Quantizer
```

路径以 MindSpore Lite 代码根为基准，即包含 `schema/`、`tools/` 和 `src/litert/` 的目录。HiSpark.AI 仓库中的常见位置是 `src/mindspore-lite/mindspore-lite/`。`<skill_root>` 表示本 skill 目录。

## 职责边界

| 本 skill 负责 | 本 skill 不负责 | 交给谁 |
|---|---|---|
| 查证 source entry、扫描七层链路 | 编写或运行精度用例 | `hs-verify-op-host` |
| source grouping、复用/新建裁决 | 生成算子设计文档 | `hs-design-op-manual` |
| 编写和修复算子源码 | 构建 WS63 固件 | `hs-dev-build`，由 workflow 调用 |
| 实现阶段 code style 与安全门禁 | 烧录固件 | `hs-dev-flash`，由 workflow 调用 |
| 输出能力清单和实现交接单 | 板端精度判定 | `hs-verify-op-board` |

如果收到超出边界的任务，只完成被明确指定的 leaf 阶段，并输出交接信息；不要自行串联其他 skill。

## 用户可见进度

仅分析模式执行 step0-step3；实现模式执行 step0-step5。阶段完成前先展示门控证据，再勾选 todo。

```markdown
待办[<implementation_unit>]:
- [ ] step0 确定范围和 source entry
- [ ] step1 扫描规格与仓内现状
- [ ] step2 完成 grouping、复用/新建和层集裁决
- [ ] step3 冻结链路分析与能力清单
- [ ] step4 编写或修复算子源码
- [ ] step5 通过实现质量门禁
```

## 两层任务对象

用户给出的 `ONNX ConvTranspose`、`TFLite TransposeConv` 是 source entry；真正新增或复用的 Primitive、kernel 和 opcoder 是 implementation unit。不要把 source entry 数量直接当成实现任务数量。

多个 source entry 只有在以下事实均有证据时才能合并：计算和输出语义一致；dtype 与 shape/infer 语义一致；属性可无损映射到同一 schema；输入顺序差异可由 parser 重排；同一能力清单能覆盖全部差异。广播版与非广播版、属性语义不同、可选输入改变输出语义、或规格不可达时，默认拆分。

用户只给通用语义名时，默认查证 ONNX 和 TFLite 两个前端的真实入口，但不凭记忆静默扩展范围。FOUND 的入口进入 grouping；NOT_FOUND 不生成 parser 或用例承诺；UNREACHABLE 与 NOT_FOUND 不等价，全部不可达时停止并请求可靠规格来源。

## 工作区和交接产物

每个 implementation unit 使用 `$MSLITE_OP_OUTPUT/<unit>/` 作为 `<opdir>`。缺省位置与 mindspore-lite 仓平级；不要放进源码树或构建树。

```text
<opdir>/
├── docs/
│   ├── spec.md
│   ├── decision.md
│   ├── link-analysis.md
│   ├── existing-capability-review.md
│   ├── implementation-contract.md
│   ├── reference-impl.md          # 计算路径变化时
│   └── builtin-probe.md           # 同族多 builtin 时
├── scripts/
│   └── capability_checklist.json
└── logs/
    └── scan_op_<Op>.log
```

`op_spec.py` 属于 host 验证 skill；算子手册 facts/Markdown 属于文档 skill；构建包、固件和烧录结果属于 workflow 及其对应 leaf skill。本 skill 不预先代写这些产物。

## 安全红线

违反任一项即返工：

1. 标准 ONNX/TFLite 算子不得使用 `ops::Custom`、`PrimType_Inner_*` 或 `REG_BUILIN_CUSTOM_CODER` 走捷径。
2. 存在性、语义、注册可达性只认可本次查证；文件存在不等于已注册或可达。
3. 不通过 `git checkout`、`git stash`、`git submodule update` 改写受管子模块状态，不删除整个 build 目录碰运气。
4. 不为编译通过删除功能分支，不把旧 kernel 当作天然正确；复用即接管该实现单元的存量质量。
5. 浮点输入算子默认实现真实 INT8 通路；原生整数算子按规格逐 dtype 覆盖，不能把“量化豁免”解释成跳过原生 `int8/uint8/int32/...`。
6. 不删除校验、边界保护或错误传播来压住失败；不以未运行的猜测宣称“不支持某形态”。
7. 不在源码、日志或文档中写入密钥、令牌、私有地址、用户数据或内部单号；外部输入用于路径、长度、索引、格式串或进程参数前必须校验。

## 总流程

| Step | 目标 | 必做动作 | 门控产物 |
|---|---|---|---|
| step0 | 冻结范围 | 列出 framework × operator source entry；解析语义名；确定 `<opdir>` | 范围声明 |
| step1 | 查证事实 | 每个 source entry 运行并完整阅读 `scan_op.sh`；归档完整日志 | FOUND/NOT_FOUND/UNREACHABLE 与七层扫描证据 |
| step2 | 冻结实现决策 | source grouping；decision2 复用/新建；decision3 层集开关 | `docs/decision.md` 与逐层做/跳表 |
| step3 | 冻结能力合同 | 生成 spec、链路分析和能力清单；review 所有已有/复用能力；必要时做 builtin 探针 | spec、link analysis、existing capability review、capability checklist |
| step4 | 实现源码 | 冻结 implementation contract；必要时对比参考实现；按七层模板最小修改 | 源码 diff 与能力落点 |
| step5 | 实现质量门禁 | 运行快速预检、code style、安全和 diff 审计 | `IMPLEMENT_GATE=PASS` 或结构化 FAIL |

## step0：冻结范围

推荐输入是“只实现 ONNX 的 X”或“用 hs-dev-op-implement 分析 X”。不要在扫描前断言某框架不存在该算子。多个入口先分组再实现；多个 implementation unit 分别维护工作区和 todo。

## step1：扫描规格和现状

```bash
bash <skill_root>/scripts/scan_op.sh <Op> <code_root>
```

每个 source entry 单独运行。完整阅读输出，不用 `head`/`tail` 截断；将 `/tmp/scan_op_<Op>.log` 复制到 `<opdir>/logs/`。规格来源与不可达回退链见 `references/spec-sources.md`。

## step2：裁决复用、新建和层集

先读 `references/worked-example.md` 和 `references/decision2-reuse-decision.md`。

非激活算子的复用必须逐项证明输入个数/顺序/语义、输出语义、属性集和广播规则完全一致；超集不等价。单数据输入、输出保形、逐元素非线性的激活优先走 `PrimitiveType_Activation` 子类型，不套非激活的四项等价测试。

逐项裁决以下开关并写入 `decision.md`：激活子类型；量化 INT8 豁免；构造型 fusion pass；消除/重写 pass；首输入是否为 condition/index。TFLite 同族多 builtin 或疑似 converter 归一化时，先做可达性探针。

向用户展示每层“做/补/复用/不适用”结论，不只写“复用”或“新建”。细化矩阵保留在 `references/decision2-reuse-decision.md` 和 `references/implementation-guide.md`。

## step3：冻结链路和能力合同

链路表固定覆盖 Schema、Parser、Populate/Parameter、Infer、Kernel float/量化 int8/原生 dtype、OpCoder、Quantizer 和 fusion。标“已有”必须同时给定义点与注册/可达点；未注册到目标路径按缺失处理。

**复用不等于跳过 code review。** 对链路表中每个“已有/复用”项，完整阅读定义文件、注册点及其到下一层的调用/数据合同，不能只 grep 文件名或注册宏。把结果写入 `<opdir>/docs/existing-capability-review.md`，至少包含：

- `reviewed_layers`：逐层列出已有能力和实际文件/符号；
- `definition_evidence`：核心实现、dtype/shape/属性/可选输入/量化参数和错误传播是否符合本次合同；
- `registration_evidence`：目标 parser、runtime、Micro codegen 和量化路径是否真实可达，有无重复注册或死代码；
- `code_findings`：边界检查、rank、内存、返回值、code style、安全红线和历史缺陷模式；
- `disposition`：每层只能是 `REUSE_REVIEWED`、`FIX_REQUIRED` 或 `N/A`，并映射 capability ID。

任何已有层存在 `FIX_REQUIRED` 都进入 step4 修复范围。禁止因为“这不是本次新增代码”而延期；Host 测试前才首次阅读存量实现，说明 step3 review 没完成。

能力清单从 `hs-verify-op-host/scripts/capability_checklist.template.json` 复制结构，但内容由本 skill 根据规格与实现裁决填写。每条能力保留稳定 ID、可读描述和可机械匹配的 `match`；本 skill 不填写虚假的 PASS，也不为现有测试反向弱化能力。

同族多 builtin 场景把实际“输入形态 → builtin”解包证据写入 `builtin-probe.md`。缺实际命令输出时不能用“无归一化”代替证据。

所有产物和 existing capability review 落盘后，按冻结的每个 framework 运行机械门禁：

```bash
python3 <skill_root>/scripts/gate_artifacts.py \
  --opdir <opdir> --op <Op> --stage step3 --framework <framework>
```

只有每个 framework 都输出 `ARTIFACT_GATE=PASS` 才能进入 step4。门禁失败时补产物，不用对话里的表格代替文件。

## step4：编写或修复源码

先冻结 `implementation-contract.md`，至少包含 source entries、primitive、输入/可选输入、属性、layout、dtype、输出、验证方式和暂不支持范围。计算路径新增、修改、启用或接管时，再生成 `reference-impl.md`，记录上游实现与仓内相似实现的算法、边界和采纳理由。

写任何 ①-⑦ 源码前，运行 pre-code 门禁：

```bash
python3 <skill_root>/scripts/gate_artifacts.py \
  --opdir <opdir> --op <Op> --stage pre-code --framework <framework>
```

只有每个 framework 都输出 `ARTIFACT_GATE=PASS` 才能动源码。能力清单或 contract 后续变化时，先重跑本门禁再继续。

每一层动笔前打开 `references/implementation-guide.md` 的对应小节，以仓内同族实现和模板为底稿。INT8 另读 `references/int8-coder-conventions.md`；fusion 另读 `references/optimizer-fusion-template.md`。

实现中持续回填能力落点。复用分支只补缺失或有缺陷的部分，不重建已经证明等价且可达的层；但验证反馈定位到存量代码时，该缺陷仍属于本 implementation unit。

新增代码完成后，再对“新增/修改代码 + 已复用代码的接口边界”做一次交叉 review：逐条沿 capability 从 parser 输入走到生成代码调用，确认新旧字段、dtype、shape、默认属性和量化参数没有断层。把新增发现更新到 `existing-capability-review.md`，重跑 pre-code artifact gate 后再进入 step5。

## step5：实现质量门禁

完整执行 `references/code-quality-gate.md`。门禁同时放在本 leaf 和顶层 workflow：这里在交付实现前执行，workflow 在构建前复核，避免 leaf 单独调用时漏检，也避免跨阶段修改绕过门禁。

最低证据：

```bash
bash <skill_root>/scripts/quick_check.sh <code_root>
git -C <code_root> diff --check
```

再对本次修改的 C/C++ 文件运行仓内 `.clang-format` 检查、逐条审计 `code-style.md` 的适用规则以及安全红线。任何 FAIL 都回 step4；不要用格式化掩盖语义改动。

只有以下条件同时满足才输出：

```text
IMPLEMENT_GATE=PASS unit=<implementation_unit>
```

- decision、spec、link analysis、contract 和 capability checklist 存在且互相一致；
- 本次源码 diff 的每个文件都能映射到某条能力或必要注册点；
- `quick_check.sh` 没有真实 FAIL，rank advisory 已逐项处置；
- code style 与安全检查没有未解决项；
- 没有构建、host、文档、flash 或 board 的虚假完成声明。

## 失败修复与交接

workflow 回流实现缺陷时，先贴首个失败原文并归类到 parser、infer、kernel、opcoder、quantizer 或构建接线，再查 `references/troubleshooting.md` 和 `references/lessons.md`。呈现根因和最小修复后才改代码；连续两个有证据的方案都失败时，返回结构化阻塞，不盲试第三个方案。

结束时输出：

```text
IMPLEMENT_GATE=<PASS|FAIL>
implementation_unit=<name>
source_entries=<list>
changed_files=<list>
capability_checklist=<absolute path>
opdir=<absolute path>
next_owner=hs-workflow-op-development
```

`IMPLEMENT_GATE=PASS` 只表示源码实现与静态质量门禁通过，不表示构建、host 精度、文档、烧录或板测已经通过。

## 资源索引

| 资源 | 何时读取 |
|---|---|
| `scripts/scan_op.sh` | step1 规格与七层扫描 |
| `scripts/gate_artifacts.py` | step3/step4 检查实现产物完整性 |
| `scripts/quick_check.sh` | step5 快速编译与结构预检 |
| `scripts/fetch_ref_impl.py` | 计算路径变化时获取上游参考 |
| `references/worked-example.md` | step2 前理解复用/新建范例 |
| `references/decision2-reuse-decision.md` | 复用裁决和 builtin 探针 |
| `references/implementation-guide.md` | step4 七层模板唯一权威 |
| `references/int8-coder-conventions.md` | INT8 kernel/opcoder |
| `references/code-quality-gate.md` | step5 code style 与安全门禁 |
| `references/spec-sources.md` | 规格来源和不可达回退 |
| `references/troubleshooting.md` | workflow 回流失败时 |
| `references/lessons.md` | 出现历史症状或想走捷径时 |

MindSpore Lite 工具包重建、构建新鲜度与工具链分诊资源归 `hs-workflow-op-development` stage2；本 leaf 不托管也不执行构建流程。
