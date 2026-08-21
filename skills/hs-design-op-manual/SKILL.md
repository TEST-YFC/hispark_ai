---
name: hs-design-op-manual
description: >-
  Generate two human-readable documents for a MindSpore Lite Micro operator: a design document containing specification, scope, reuse decisions, and software call chains, and a verification document containing test design, Host, firmware, flash, serial, and board accuracy results. Use when the user explicitly asks for operator documentation or hs-workflow-op-development routes a documentation stage here. This skill never modifies operator source or runs build/test/flash.
---

# 单算子设计文档生成器

## 概述

为 MindSpore Lite Micro 单算子维护两份主文档。设计文档只记录框架规格、支持范围、七类能力复用裁决、关键场景和软件调用链；验证文档只记录测试设计、用例矩阵、Host/固件/烧录/串口/板端结果和证据索引。独立模式负责查证事实；产物集成模式只整理父流程已经冻结的产物，不重新运行开发或验证。

始终遵守三条原则：

1. 只写可公开、已核对或由父流程冻结的事实，不编造缺失字段；验证文档不得把未执行阶段写成 PASS。
2. 明确写出“不支持转换”“不支持该规格”或“不支持该类型”，不得把缺失链路包装成支持。
3. 一次调用只有一个模式和一组固定的设计/验证文档目标。所有写入型模式都必须使用算子工作目录
   `<opdir>`。产物集成模式创建或刷新 `<opdir>/docs/operator-manual-facts.json`；facts、日志和
   机器结果是内部证据，不替代两份主文档。
   人读文档固定且仅有 `<opdir>/docs/{op}-operator-design-doc.md` 与
   `<opdir>/docs/{op}-operator-verify-doc.md` 两份；除 facts 和发布门控临时候选外，不生成第三份
   人读文档或旁路说明文档。

## 六种模式

| 模式 | 触发场景 | 事实获取 | 输出 |
|---|---|---|---|
| `standalone-generate` | 独立生成算子文档 | 用户材料、仓内证据、已有公开文档和必要的官方规格查证 | 在 `<opdir>/docs/` 成对生成设计文档和验证文档 |
| `standalone-update` | 独立更新已有设计/验证文档 | 同上，并读取现有目标文档 | 在 `<opdir>/docs/` 成对更新设计文档和验证文档 |
| `template-analysis` | 只分析设计/验证模板 | 本 skill 的模板规则 | 不写文件 |
| `integrated-initial` | 新算子编码前，父流程已冻结计划产物 | 仅 `<opdir>`冻结产物 | 刷新 facts；创建 `<opdir>/docs/{op}-operator-design-doc.md` 与 `<opdir>/docs/{op}-operator-verify-doc.md` 初版 |
| `integrated-final` | 新算子终态同步 | 仅最新 `<opdir>` 冻结产物和父流程终态 | 刷新 facts；分别更新设计文档和验证文档 |
| `artifact-sync` | 从已有算子开发产物同步文档 | 仅已有 `<opdir>` 产物和最后记录的 summary | 分别更新两份文档并明确证据等级；D 不写文件 |

先确定模式，再执行对应分支。不得把独立模式的路径确认、仓库扫描或外部查询带入产物集成模式。

## 调用契约与路径授权

### 独立模式

`standalone-generate` 和 `standalone-update` 保留交互确认：

1. 工作前确认 `mindspore-lite` 代码根、算子工作目录 `<opdir>`、`{op}`、`{Op}` 和框架范围。
2. 写入前再次确认两份绝对目标路径：`<opdir>/docs/{op}-operator-design-doc.md` 和
   `<opdir>/docs/{op}-operator-verify-doc.md`。不得把文档写到代码根的公共文档目录。

独立模式继续查证框架公开规格和仓内支持链路：parser/source entry 缺失写“不支持转换”；schema/infer/计算规格不覆盖某属性、shape、layout 或方向写“不支持该规格”；coder/目标类型未注册写“不支持该类型”。阶段更新用 Markdown todo 展示当前 step 和已得到的证据，不提前勾选未完成门控。建议使用以下通用探查命令，并把完整输出保存到 `<opdir>/docs/logs/`，不得只贴截断片段：

```bash
rg -n "Onnx.*Parser|Parser.*<Op>|Parse\\(" <code_root>
rg -n "Populate.*<Op>|<Op>Parameter|InferShape" <code_root>
rg -n "REG_KERNEL|REG_OPERATOR_CODER|OpCoder|Quantizer" <code_root>
rg -n "PrimitiveType.*<Op>|<Op>Fusion" <code_root>
```

将 `<Op>` 替换为本次目标算子；命令只用于 standalone 查证，不能带入产物集成模式。

`template-analysis` 只确认分析范围，不要求保存路径，不写文件。

### 产物集成模式

父流程必须提供：

| 参数 | 要求 |
|---|---|
| `mode` | `integrated-initial`、`integrated-final` 或 `artifact-sync` |
| `code_root` | 绝对代码根路径 |
| `opdir` | 该 implementation unit 的绝对工作目录 |
| `op` / `Op` | 小写发布名 / 公开算子或 unit 名 |
| `implementation_unit` | 父流程冻结的 implementation unit 标识 |
| `framework_scope` | 父流程冻结的 source entry / 框架范围 |
| `terminal_state` | `integrated-final` 必填：`completed`、`blocked` 或 `hard-stop` |

这些父流程提供的路径和目标已经获得授权，不再询问目录或保存路径。仅做只读合法性检查：路径必须为绝对路径，核心产物必须位于给定 `opdir`，输出必须精确落到本模式规定的位置。参数缺失、路径冲突或框架范围冲突时返回父流程修正，不自行猜测。

`integrated-initial`只能在父流程已经完成`hs-dev-op-implement mode=prepare`并取得
`OP_PLAN_GATE=PASS`后调用。它不负责生成spec、implementation contract、capability checklist
或计划版op_spec；全新/空opdir缺少任一核心源时必须失败返回，不能为了“文档先行”而自行扫描
代码或发明输入。父流程在本skill输出draft后还必须通过`PRE_SOURCE_GATE`，才可调用实现Skill的
`mode=apply`写源码。

`integrated-final` 必须接收父流程终态和同轮验证摘要；它只整理已有证据，不重跑实现、构建、Host
或板测。设计文档不得写测试结果，验证文档不得重复完整软件设计；未执行阶段必须在验证文档写
`NOT_RUN` 及原因。只有父流程给出完整终态时验证文档才写“完整流程通过”。
`integrated-initial`只表示编码前事实和计划用例已经冻结并通过文档审计，绝不表示源码、构建或验证完成。

## 产物集成模式的事实源

| 文档内容 | 唯一主源 | 允许的辅助证据 |
|---|---|---|
| 设计文档规格/软件设计 | `<opdir>/docs/spec.md`、`implementation-contract.md` | `builtin-probe.md`、`reference-impl.md`、`link-analysis.md`、`decision.md` |
| 设计文档场景 | `<opdir>/scripts/capability_checklist.json` | `decision.md` |
| 验证文档用例 | `<opdir>/scripts/op_spec.py` | capability checklist、builtin probe |
| 验证文档结果 | 最新可信 `verify_summary.txt` 及板端矩阵 | 各阶段日志和产物哈希 |

上述四个主源与最后记录的 `verify_summary.txt` 先规范化为统一渲染输入：

```text
<opdir>/docs/operator-manual-facts.json
```

该文件是本 skill 明确要求生成的中间产物，不是某个模型或工具的可选输出。`integrated-initial`在编码前首次生成；`integrated-final`在终态文档前从最新产物整份重建；`artifact-sync`从已有产物生成，不要求已有 `op_spec.py`改成当前schema，也不重跑开发流程。两份 Markdown 只读取该 facts 文件；audit 独立读取原始产物、facts、设计候选和验证候选四方比对，不能用候选反向改写 facts。

facts 顶层固定包含：

```json
{
  "schema_version": 1,
  "operator": "TopK",
  "mode": "integrated-final",
  "provenance": "production",
  "production_eligible": true,
  "sources": {},
  "chapter_facts": [],
  "capabilities": [],
  "scenario_groups": [],
  "coverage_principles": [],
  "cases": []
}
```

每个 `sources` 项记录相对 `path` 和当前文件 `sha256`。每个 `chapter_facts` 项记录 `chapter`、核心源中的逐字 `quote` 和公开 `manual_text`。每个 capability 保留原始 `id`、`description`、规范化 `covered_by`，可另加不改变语义的公开 `manual_text`。`scenario_groups` 只负责把 capability 归并为读者能理解的使用场景，不能删除、重复或改写源 capability；`coverage_principles` 负责验证文档 `1.1 测试覆盖原则` 的白话说明。每个 case 固定记录原始 ID、framework/source entry、模型 dtype、input shape、value domain、属性、逐 case PASS 验证路径、结构化预期输出、公开预期输出文本和预期输出证据。case 顺序必须等于 `op_spec.py`。

capability 的公开改写不得扩大用例实际覆盖：case 只把属性写成默认值时，必须写“默认值配置”，不能写“省略属性后的默认解析”；只有模型构造确实省略该属性时才能宣称覆盖默认解析。同理，spec/contract 的 opset 策略不能写成另一个 opset 测试覆盖，除非对应验证模型真实使用该 opset。

case 字段名和形状固定如下；算子特有属性只放在 `attributes`：

```json
{
  "id": "TC-001",
  "framework_source_entry": "ONNX TopK",
  "framework": "onnx",
  "model_dtype": "float32",
  "input_shape": [2, 8],
  "value_domain": "mixed",
  "attributes": {
    "axis": -1,
    "k": 3,
    "largest": true,
    "sorted": true
  },
  "verification_paths": ["x86_fp32", "riscv_fp32", "riscv_int8"],
  "expected_outputs": [
    {"name": "Values", "shape": [2, 3], "dtype_rule": "same_as_input"},
    {"name": "Indices", "shape": [2, 3], "dtype": "int32"}
  ],
  "expected_outputs_text": "Values/Indices shape=[2, 3]; Values 与输入同 dtype；Indices=int32",
  "expected_output_evidence": {
    "source": "docs/implementation-contract.md",
    "quote": "Both output shapes equal the input shape with the selected axis replaced by K.",
    "shape_rule": "replace_axis_with_k"
  }
}
```

`shape_rule` 只允许 audit 已实现且原始源逐字陈述的规则（当前为 `replace_axis_with_k`），或 op_spec case 已显式给出完整输出时使用 `op_spec_explicit`。不能为了通过 audit 自造规则名。

辅助证据只能在以下边界内使用：

- `decision.md`：确认 source entry 的归并、场景分类和七类能力复用裁决；可引用仓库相对路径、PrimitiveType 和公开符号，不得引用本机工作区或内部流转信息。
- `link-analysis.md`：投影转换支持状态和已查证接线；可引用仓库相对文件及公开注册符号，不得引用本机绝对路径或内部缺陷动作。
- `reference-impl.md`：只补充可观察语义和边界，不公开拉取命令、临时路径或工程取舍。
- `builtin-probe.md`：只补充 source entry 与 builtin 的已验证映射。
- capability checklist 作为验证文档用例表的辅助证据时只检查 `covered_by` 关联；它和 builtin probe 都不得提供或改写 case 字段。

在 `integrated-initial`、`integrated-final` 和 `artifact-sync` 中：

- 禁止重新扫描代码仓，禁止查询外部或框架规格，禁止运行 scan、build、`hs-verify-op-host` 或板端流程。
- 主源之间、主源与父参数之间有冲突，或公开事实缺失时，返回上游修正并输出 FAIL。不得选择“看起来更合理”的版本，不得发明补全。

## 预检与产物分级

对产物集成模式，在生成前运行：

```bash
python3 <manual_skill_root>/scripts/audit_manual_inputs.py --opdir <absolute_opdir>
```

记录 `OP_MANUAL_INPUT_TIER`。集成模式用它检查核心资产是否可读；`artifact-sync` 必须严格按以下 A/B/C/D 分级：

| 等级 | 条件 | 行为 |
|---|---|---|
| A：可直接同步 | 四个核心源完整、当前 capability schema 可读、最后完整 summary 全绿且能力全覆盖 | facts 内容完整且三项同步 PASS 时生成正式文档；否则只生成证据不足草稿 |
| B：可兼容读取 | 语义和用例核心源完整，但使用兼容 capability schema、缺少非语义元数据或没有可信全绿 summary | 更新两份文档并在验证文档标注证据不足；不得写成完整通过 |
| C：已有验证未通过 | 最新完整 summary 含非零 FAIL/ERR、`HARNESS_EXIT!=0` 或能力未覆盖 | 更新验证文档并保留 FAIL/NOT_RUN 原因；设计文档只保留支持限制 |
| D：事实源不足 | 缺少或无法读取 spec、contract、capability 或 op_spec | 列出缺失/冲突后停止，不写文件 |

兼容 schema 只允许无损读取：

- capability 缺少 `match` 时按空匹配读取，不得从 `desc` 猜结构化参数。
- `framework_scope` 由 capability、op_spec 的非空框架用例和 spec 的 FOUND/NOT_FOUND 交叉确认；冲突即 FAIL。
- 条件产物缺失仅在其触发条件不存在时放行。
- 不重写已有 capability、op_spec、summary 或其他产物。

已有 summary 只取最后一组完整 `VERDICT` + 紧随其后的 `HARNESS_EXIT`，只用于发布资格和已记录能力/验证路径的状态过滤；它不是框架语义、功能规格、shape、dtype 或属性的来源。

验证路径只读取 summary 中逐 case 的明确 `PASS` 行。聚合 `paths=[...]`、全局目标列表或 dtype 名称都不能展开成逐 case 支持结论。已有 summary 没有逐 case 记录时，对应 facts 的 `verification_paths` 为空并降为证据不足草稿；不得为了发布补写路径。

对 C 级：

- summary 明确标记失败或未覆盖的 variant/target/path，不得写成已支持，不得在测试表中标成正向通过路径。
- 验证文档仍逐 case 投影 op_spec 以保持 ID 完整，但行只表示冻结的用例设计；失败路径从“已支持验证路径”中移除或明确写“不支持该规格”。
- summary 只有聚合失败而没有可靠映射时，不猜失败 case；整份文档保持证据不足草稿状态，不宣称未证实路径已支持。

## 设计文档与验证文档结构

产物集成模式必须按以下两个模板分别维护两份主文档：

- [`references/operator-design-doc-template.md`](references/operator-design-doc-template.md)：
  `<opdir>/docs/{op}-operator-design-doc.md`，只记录规格范围、支持限制、七类能力复用裁决、关键场景和软件调用链。
- [`references/operator-verify-doc-template.md`](references/operator-verify-doc-template.md)：
  `<opdir>/docs/{op}-operator-verify-doc.md`，只记录测试设计、用例矩阵、Host/固件/烧录/串口/板端结果和证据索引。

设计文档禁止出现测试设计、运行结果、烧录结果、板端精度结论；验证文档禁止重复完整的软件设计和七类能力实现说明。不能把固件构建写成板测通过。
`operator-manual-facts.json`、`code-review.md`、summary、日志和二进制产物仍是机器/审计证据，不替代这两份人读文档。

独立写入模式也始终成对生成或更新两份文档：设计内容使用设计模板，测试设计和已有验证结果
使用验证模板；尚未执行的验证阶段在验证文档中明确写 `NOT_RUN`。不得省略验证文档，也不得把
验证章节重新塞回设计文档。

### 独立模式的设计/验证文档构建

`standalone-generate` 和 `standalone-update` 要求存在明确的 `<opdir>` 作为文档归属目录，但不要求
冻结产物，也不套用产物集成模式的逐产物投影规则：

| 文档位置 | 独立模式事实来源与构建规则 |
|---|---|
| 设计文档 | 从用户材料、已有公开文档、仓内材料和必要的官方规格中交叉查证框架语义、属性、输入、输出、软件设计和限制 |
| 验证文档 | 单独记录测试设计、用例矩阵、运行结果和证据；没有运行证据的阶段明确写 `NOT_RUN`，不复制完整软件设计 |
| 验证文档第 1 章 | 为已验证支持范围构造具体测试设计；每行给出 framework、模型 dtype、input_shape、输入数据特征、属性和预期输出，不为不支持规格生成正向用例 |

独立模式使用两个模板的标题和公开表格形状，但把冻结产物来源替换为本表的已查证来源。验证用例从 `TC-001` 顺序编号，并覆盖已验证的典型值与边界值；更新模式可保留仍被当前证据支持的已有用例，但必须删除过时或无法验证的内容。

### 产物集成模式的设计文档投影

以下来源绑定、`covered_by`检查和op_spec精确case规则只适用于 `integrated-initial`、`integrated-final`和 `artifact-sync`。这三个模式不得回退到独立模式取材。

设计文档头部

```markdown
# {Op} 算子设计文档

{来自 spec.md 的公开、已验证语义简述}
```

产物集成模式只有 `spec.md` 明确给出英文全名、类别或公式时才写对应内容。独立模式使用其已查证来源。所选来源缺少全名/类别时使用不增加新事实的中性已验证描述；缺少公式时省略公式块，不使用通用名称或经验公式补造。

### 第 1 章：算子概述

严格使用模板中的 `1.1 功能和数学定义` 与 `1.2 最小示例`。产物集成模式只有 `spec.md`
明确给出公式时才写公式；独立模式使用已交叉查证的规格。最小示例必须给出输入 dtype、shape、
关键属性和预期输出，但不写运行结果。缺少可靠公式时省略公式，不使用经验公式补造。

### 第 2 章：框架算子规格

```markdown
## 2. 框架算子规格

### 2.1 {framework/source entry}

| 属性 | 类型 | 默认值 | 是否必需 | 说明 |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

| 输入 | 模型数据类型 | 参数含义 | 规格限制 |
|---|---|---|---|
| ... | ... | ... | ... |

| 输出 | 模型数据类型 | 参数含义 | 规格限制 |
|---|---|---|---|
| ... | ... | ... | ... |

### 2.2 支持范围与限制
```

产物集成模式按父流程的 `framework_scope`，独立模式按用户确认且已查证的框架范围，为每个
source entry 重复 `2.1` 小节。无属性时写 `| — | — | — | — | 无属性 |`。spec 或独立模式
证据明确 NOT_FOUND/无转换入口时写“不支持转换”，不编造属性、类型或布局。

产物集成模式完全投影 implementation contract 的输入、dtype、属性、输出、shape/layout、
量化语义和功能限制；独立模式从已查证支持链路构建。模型 dtype 与验证路径是两个概念，不能
把 full-quant int8 验证路径改写成原生 int8 模型支持。本章不写用例数量、运行结果、烧录状态
或验证任务名；这些内容全部放入验证文档。

### 第 3 章：MindSpore Lite Micro 软件设计

`3.1 七类能力与复用裁决` 必须覆盖 Schema、Parser、Populate/Parameter、Infer、Kernel、
OpCoder 和 Quantizer，并写明复用/修改/新建/N/A、仓库相对文件或注册点、依据和限制。

`3.2 关键场景与软件行为` 先完整保留 capability checklist，再通过 `scenario_groups` 组织公开
章节。当 capability 多于 7 项时，必须归并为 3～7 个面向读者的场景；每个场景回答“什么时候
会遇到”“软件支持什么”“有什么限制”。每个 capability 必须恰好属于一个 group，group 的
`covered_by` 等于成员 capability 用例号的有序并集，但不把用例号写入设计文档。找不到、重复
或遗漏即 FAIL，禁止为补齐覆盖而新造用例。独立模式不要求 capability checklist，但仍按相同
读者场景结构组织。

`3.3 转换与运行调用链` 必须把模板的通用链替换为当前算子的真实 Parser、Primitive/Schema、
Parameter、Infer、OpCoder、生成入口、Kernel 和应用模型 API；不适用环节写 N/A 及原因。
使用仓库相对路径和公开符号，不写本机绝对路径。必须说明转换期与运行期边界，不能把七类能力
误写成每次推理依次执行。

### 验证文档的固定结构

验证文档使用 [`references/operator-verify-doc-template.md`](references/operator-verify-doc-template.md)，固定包含以下章节：

```markdown
## 1. 测试设计

### 1.1 测试覆盖原则

**输入是否覆盖常见规模？** 用读者能理解的语言说明 shape、rank、axis 和 batch 覆盖。

**不同选择方式是否正确？** 说明属性、方向、排序或其他主要行为。

**边界和数据内容是否覆盖？** 说明边界值和输入数据特征。

**量化/非量化通路是否覆盖？** 根据逐用例 PASS 记录、模型数据类型和生成代码证据，分别说明非量化、全量化 int8 与原生整数通路覆盖。

### 1.2 用例总表

| 用例编号 | 框架/source entry | 模型 dtype | 已覆盖运行通路 | input_shape | 输入数据特征（value_domain） | 算子属性 | 预期输出 |
|---|---|---|---|---|---|---|---|
| TC-... | ... | ... | ... | ... | ... | ... | ... |
```

上述四个问题的文字和顺序固定，问答来自 facts 的 `coverage_principles`，每项包含 `question` 和 `answer`。答案必须先解释用户能理解的覆盖含义，再让验证文档的用例表给出精确数据；不要使用“逐用例投影”“冻结产物”“正向用例”等流程术语。

第四个问题不能只罗列内部验证任务名。先按实际语义分类，再报告覆盖：

- 非量化通路：依据无全量化配置的主机/RISC-V PASS 记录，说明覆盖的框架、用例数和模型数据类型。
- 全量化 int8 通路：只统计 float32 模型经 FULL_QUANT 后确实生成 int8 张量/量化内核的 PASS 用例；必须有 `int8_genuine`、生成内核或等价产物证据。
- 原生整数通路：单独说明 int32 等原生整数模型。即使它执行了名为 `riscv_int8` 的任务，只要张量和内核仍为原生整数，就不能计入 int8 量化覆盖。

验证结论中的数量必须从 facts 的 cases、逐 case `verification_paths` 和实现/生成证据计算，不能从聚合路径列表或路径名称推断。`verification_paths` 保留机器任务名用于审计，但公开验证文档必须转换为“x86 主机非量化”“RISC-V 非量化”“RISC-V 全量化 int8”“RISC-V 原生整数”等实际含义；全文不得出现 `x86_fp32`、`riscv_fp32`、`riscv_int8`。

以下验证文档用例表规则只适用于产物集成模式：

1. ONNX_TEST_CASES 和 TFLITE_TEST_CASES 中每个 case 恰好一行；不遗漏、不合并、不增加 op_spec 中不存在的 case。
2. 保留原始 case ID。数字 `1` 显示为 `TC-001`，`101` 显示为 `TC-101`；不得按表格位置重新编号。
3. framework、shape、K/属性、模型 dtype 和 `value_domain` 从 op_spec case 规范化进 facts；Markdown 逐字段按 facts 的规范格式渲染，不能把 `value_domain` 丢进泛化描述。
4. “模型 dtype”和“已覆盖运行通路”分列。模型 dtype 只来自 op_spec case；内部验证记录只来自最后可信 summary 的同 case 明确 PASS 行，再结合模型 dtype 和生成代码证据转换为读者语言。不得从聚合路径、dtype 名称或经验规则推导覆盖。
5. 预期输出必须有结构化 `expected_outputs`、公开 `expected_outputs_text` 和逐字证据。输出名称/dtype 来自 op_spec 模型构造或 implementation contract；shape 只有在上述来源明确写出 shape 规则时才可把规则应用到 case 参数。final 不允许任何必需字段写“未记录”“待确认”或“尚未执行验证”。
6. `integrated-initial`尚未产生验证证据时，验证路径单元格固定写“尚未执行验证”，且facts的 `production_eligible=false`；该措辞只允许draft。
7. `integrated-final`和`artifact-sync` A不增量修补已有表，而是从最新facts重建整表，删除已移除case并加入新增case。
8. 不支持的framework/type/spec不生成额外正向case；C级失败路径不得标成PASS或supported。

## 敏感信息与公开边界

违反任一项即返工：

- 禁止写需求号、任务号、缺陷号、工号、员工号、审批/评审单号、内部编号，或 `AR/MR/CR` 等内部流转编号。
- 禁止写 `REQ-123`、`TASK-123`、`BUG-123`、`JIRA-123`、`MS-1234`、`PRJ-1234`、`AR-123`、`MR-123`、`CR-123`、带标签的六位以上数字串，以及此类占位符。
- 禁止写“Bug号”“问题单号”“xxx编号”“请补编号”“待补编号”“内部单号”或“补 AR/MR/CR 单号”等字段/占位描述。
- 禁止私有系统链接和含 `ar_id=`、`mr_id=`、`cr_id=`、`taskId=`、`issueId=` 的参数。
- 设计文档为说明七类能力和真实调用链，可以写仓库相对源码路径、PrimitiveType、公开注册符号、
  Kernel/OpCoder 分支和量化设计事实；验证文档不重复这些完整设计。
- 禁止写本机绝对路径、个人工作区、临时目录、账号/密钥、私有系统链接、内部缺陷动作或与算子
  设计无关的内部实现细节。
- 公开测试用例号 `TC-*` 是必要文档标识，不属于敏感编号，必须按 op_spec 保留。
- 全文不得出现“待确认”。证据不足时停止并返回上游，而不是把不确定性发布出去。

支持状态固定用语：

| 情况 | 写法 |
|---|---|
| source entry/parser 无转换入口 | `不支持转换` |
| 模型 dtype/目标类型无支持记录 | `不支持该类型` |
| 属性、shape、layout、方向、variant 或验证 target 不支持 | `不支持该规格` |

## 执行顺序

| Step | 动作 | 门控 |
|---|---|---|
| step0 | 选择模式；独立模式完成两次确认要求，产物集成模式校验父参数和绝对路径 | 模式、范围、设计/验证目标明确 |
| step1 | 产物集成模式运行输入 audit；`artifact-sync` 按 A/B/C/D 分级 | D 或核心冲突立即 FAIL |
| step2 | 产物集成模式从原始主源创建/整份刷新 `operator-manual-facts.json`；独立模式整理已查证事实但不生成 facts 文件 | 集成模式 facts schema 完整；所有模式遇到缺失和冲突都停止，不发明 |
| step3 | 产物集成模式从 facts、独立模式从已查证事实，在内存中分别生成设计和验证候选；终态重建验证用例表和结果章节 | 两份文档职责完整；验证 case 顺序和逐字段值一一对应 |
| step4 | 对候选做格式、来源、支持措辞、敏感信息和 placeholder 自检 | 全部 PASS 才能进入发布门控 |
| step5 | 将两份候选分别写入 `<opdir>/docs/` 的临时文件；产物集成模式对 facts 和两份候选运行完整 audit，独立模式运行格式、事实来源和职责边界自检 | 集成模式三项 audit 均 PASS；独立模式自检全部 PASS |
| step6 | 对应门禁 PASS 后执行带备份回滚的成对发布；重新读取两份目标并打印 `OP_MANUAL_SYNC` | 两份目标同时更新并复核 PASS，或两份都恢复发布前状态并 FAIL |

现有两份文档在发布门控通过前不得直接修改。候选优先保留在内存；执行发布门控时，才在目标文档
同目录创建可精确识别的临时候选。下面命令用于
产物集成模式：

```bash
design_candidate="$(mktemp "${design_path}.candidate.XXXXXX")"
verify_candidate="$(mktemp "${verify_path}.candidate.XXXXXX")"
# 将内存候选分别写入两个候选文件，不要直接写正式目标
python3 <manual_skill_root>/scripts/audit_manual_inputs.py \
  --opdir <absolute_opdir> \
  --facts <absolute_opdir>/docs/operator-manual-facts.json \
  --design "$design_candidate" \
  --verify "$verify_candidate" \
  --publication <draft|evidence-draft|final>
```

只有 `OP_MANUAL_FACTS_SYNC=PASS`、`OP_MANUAL_CONTENT_SYNC=PASS` 和 `OP_MANUAL_CASE_SYNC=PASS`
同时成立，才成对发布两份候选。发布必须按以下事务式顺序执行：

1. 在 `<opdir>/docs/` 中分别为当前设计、验证目标创建可精确识别的临时备份；目标原先不存在时
   记录 `ABSENT`，不得伪造空备份。
2. 依次以同目录 rename/move 替换设计目标和验证目标；单个替换可以利用同一文件系统的原子
   rename，但不得声称两个替换天然构成一个原子事务。
3. 任一替换失败，立即从备份恢复已经替换的目标；发布前为 `ABSENT` 的目标必须删除。重新读取
   两个目标，确认都回到发布前状态，然后输出 `OP_MANUAL_SYNC=FAIL`。
4. 两个替换都成功后，重新读取两份目标并复跑内容/职责边界检查；全部 PASS 后才能删除备份并
   输出 `OP_MANUAL_SYNC=PASS`。复核失败也执行步骤 3 的回滚。

门禁 FAIL 或命令异常时丢弃两个候选，不改正式目标。候选和备份都不是持久输出，成功或回滚后
不得残留。不得为取得 PASS 修改 op_spec、capability 或 summary。独立模式不执行 facts audit，
但也必须先完成 step4 自检，再按同一成对发布与回滚规则更新 `<opdir>/docs/` 中的两个目标。

产物集成模式的正式发布必须同时满足：父终态允许发布、产物等级允许发布、facts `provenance=production`、`production_eligible=true`，以及 facts/content/case 三项同步 PASS。

## 输出决策

产物集成模式的 `{op}` 使用父流程冻结的小写发布名。每个算子固定生成两份文档：
`{op}-operator-design-doc.md` 和 `{op}-operator-verify-doc.md`。两份文件名都包含算子名，保证文档复制或脱离 `opdir` 后仍可识别；模板源文件按设计/验证各自维护，不按算子复制或改名。

| 模式/状态 | publication | 目标 |
|---|---|---|
| `standalone-generate` / `standalone-update` | `final` | `<opdir>/docs/{op}-operator-design-doc.md` + `<opdir>/docs/{op}-operator-verify-doc.md` |
| `template-analysis` | `none` | `NONE` |
| `integrated-initial` | `record` | `<opdir>/docs/{op}-operator-design-doc.md` + `<opdir>/docs/{op}-operator-verify-doc.md` |
| `integrated-final terminal_state=completed` | `record` | 同上，同时回填验证结果 |
| `integrated-final terminal_state=blocked\|hard-stop` | `record` | 同上，验证文档记录 NOT_RUN/FAIL 原因 |
| `artifact-sync` A 且 facts 内容完整 | `record` | 同上 |
| `artifact-sync` A 但 facts 内容不完整 | `record` | 同上并标注证据不足 |
| `artifact-sync` B/C | `record` | 同上并保留 FAIL/NOT_RUN |
| `artifact-sync` D | `none` | `NONE` |

一次调用不得同时刷新 draft 和 final；除 mandatory facts 中间产物外，必须成对提升设计文档和验证文档。完成或失败时，最后一行使用：

说明：`record` 是工作流对“两份主文档”的发布标识；底层 `audit_manual_inputs.py` 仍使用
`--publication=draft|final` 表示审计严格程度。

```text
OP_MANUAL_SYNC=PASS mode=<mode> publication=<final|record|none> design_path=<absolute-path|NONE> verify_path=<absolute-path|NONE>
OP_MANUAL_SYNC=FAIL mode=<mode> publication=none design_path=NONE verify_path=NONE
```

失败详情在终态行之前简要列出并返回父流程。`integrated-initial`失败会阻塞进入编码；`integrated-final`失败会阻塞完成声明。两份文档只能由冻结facts和同轮终态证据渲染，不能成为另一套手工维护的事实源。

## 自检与最终复核

候选提升前逐项检查：

- [ ] 模式、授权和设计/验证输出与决策表一致；只生成规定的两份人读文档。
- [ ] 产物集成模式已从本次最新原始源刷新 `operator-manual-facts.json`；source path/hash、quote、case 顺序和 provenance 均正确。
- [ ] 设计文档和验证文档各只有规定的三个一级编号章节；独立模式使用已查证事实构建，产物集成模式每章来自规定主源。
- [ ] capability 多于 7 项时，第 3 章已归并为 3～7 个读者场景；每个 capability 恰好出现一次，group 用例号是成员 `covered_by` 的准确并集。
- [ ] 验证文档 `1.1 测试覆盖原则` 的四个问题和答案来自 `coverage_principles`，使用用户语言解释覆盖范围，没有流程术语堆叠。
- [ ] 产物集成模式没有仓库重扫、外部查询、build、verify 或 board 重跑。
- [ ] 现有设计/验证文档没有覆盖冻结事实；终态的验证文档用例表和结果章节已经整表重建并回填结果。
- [ ] formula/full name/category 未被发明；缺公式时已省略。
- [ ] 不支持项使用固定措辞，C 级失败 variant/target/path 未写成支持。
- [ ] 模型 dtype、已覆盖运行通路、value_domain/输入数据特征各自保留且没有混淆；机器验证标识只保留在 facts，公开设计文档已转换为实际运行含义。
- [ ] 文档标题和正文定位为算子设计文档；全文没有出现内部验证任务名。
- [ ] 产物集成模式中 op_spec 每个 case 恰好一行，原始 `TC-*` ID 未重排；每个 `covered_by` 都存在。
- [ ] 全文没有本机绝对路径、内部流转信息、私有链接或“待确认”；设计所需的仓库相对路径和公开符号已保留。
- [ ] facts/content/case 任一 audit 尚未通过时，既有两份文档仍未被覆盖；失败临时候选会被丢弃。
- [ ] 成对发布任一步失败时，两份目标都恢复发布前状态；两份目标版本一致，且没有候选或备份残留。

提升后重新读取目标并确认：

1. 写入模式实际只持久写入决策表中的两份人读文档，零写入模式没有文档；没有第三份人读文档或残留临时候选。
2. 两份文档各自的三个一级编号章节、表头和支持措辞完整，已移除 case 不残留，新增 case 不遗漏。
3. 产物集成模式的输出得到 `OP_MANUAL_FACTS_SYNC=PASS`、`OP_MANUAL_CONTENT_SYNC=PASS` 和 `OP_MANUAL_CASE_SYNC=PASS`；否则不得更新任一文档或报告同步成功。
4. terminal_state 和产物等级没有被文档内容反向改写。

## 变量与参考

| 变量 | 含义 |
|---|---|
| `<manual_skill_root>` | `hs-design-op-manual` skill 的绝对目录 |
| `<code_root>` | MindSpore Lite 代码根绝对路径 |
| `<opdir>` | 单个 implementation unit 的绝对工作目录 |
| `design_path` / `verify_path` | 按输出决策表解析出的两份持久文档目标绝对路径 |
| `{op}` / `{Op}` | 小写发布文件名 / 公开算子或 unit 名 |
| `framework_scope` | 父流程冻结的 source entry / 框架集合 |
| `terminal_state` | `integrated-final` 的 `completed`、`blocked` 或 `hard-stop` |
| `model dtype` | 模型输入本身的数据类型 |
| `verification path` | fp32、full-quant int8 等独立验证路径，不等于模型 dtype |
| `value_domain` | 输入值域/输入数据特征，如 mixed、positive、negative、ties |

所有模式都使用本 Skill 自带的设计/验证模板；不得以公共目录中的其它算子文档作为模板或事实源。
