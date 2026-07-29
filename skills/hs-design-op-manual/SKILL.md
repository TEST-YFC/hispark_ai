---
name: hs-design-op-manual
description: Use when generating or updating a standalone operator design document, projecting a design document during integrated operator development, synchronizing the final document at terminal state, migrating historical operator artifacts, or analyzing the four-chapter template.
---

# 单算子设计文档生成器

## 概述

为 MindSpore Lite Micro 单算子生成四章节设计文档，内容包括框架语义、Micro 功能设计、关键使用场景和测试设计。独立模式负责查证事实；集成和历史模式只把父流程已经冻结的产物整理为面向设计评审和后续维护的公开文档，不重新解释开发结果。

始终遵守三条原则：

1. 只写可公开、已验证的事实，不编造缺失字段，不在最终文档中保留“待确认”。
2. 明确写出“不支持转换”“不支持该规格”或“不支持该类型”，不得把缺失链路包装成支持。
3. 一次调用只有一个模式和一个文档发布目标。带 `opdir` 的写入型模式还必须创建或刷新 skill 明确规定的中间产物 `<opdir>/docs/operator-manual-facts.json`；它不算第二个文档发布目标。除该 facts 文件、唯一文档目标和发布门控临时候选外，不生成计划文件或旁路报告。

## 六种模式

| 模式 | 触发场景 | 事实获取 | 输出 |
|---|---|---|---|
| `standalone-generate` | 独立生成新文档 | 用户材料、仓内证据、已有公开文档和必要的官方规格查证 | `<code_root>/operator-desc/{op}.md` |
| `standalone-update` | 独立更新已有文档 | 同上，并读取现有目标文档 | 更新 `<code_root>/operator-desc/{op}.md` |
| `template-analysis` | 只分析四章节模板 | 本 skill 的模板规则 | 不写文件 |
| `integrated-initial` | 新算子编码前，父流程已冻结计划产物 | 仅 `<opdir>` 冻结产物 | 刷新 facts；发布 `<opdir>/docs/operator-manual-draft.md` |
| `integrated-final` | 新算子终态同步 | 仅最新 `<opdir>` 冻结产物和父流程终态 | 刷新 facts；完成态发布正式文档，阻塞/硬停态只刷新草稿 |
| `legacy-sync` | 历史算子从旧开发产物迁移文档 | 仅历史 `<opdir>` 产物和最后记录的 summary | A 且事实完整时发布正式文档；否则刷新 facts 并写迁移草稿；D 不写文件 |

先确定模式，再执行对应分支。不得把独立模式的路径确认、仓库扫描或外部查询带入集成/历史模式。

## 调用契约与路径授权

### 独立模式

`standalone-generate` 和 `standalone-update` 保留交互确认：

1. 工作前确认 `mindspore-lite` 代码根、`{op}`、`{Op}` 和框架范围。
2. 写入前再次确认绝对目标路径 `<code_root>/operator-desc/{op}.md`。

独立模式继续查证框架公开规格和仓内支持链路：parser/source entry 缺失写“不支持转换”；schema/infer/计算规格不覆盖某属性、shape、layout 或方向写“不支持该规格”；coder/目标类型未注册写“不支持该类型”。阶段更新用 Markdown todo 展示当前 step 和已得到的证据，不提前勾选未完成门控。

`template-analysis` 只确认分析范围，不要求保存路径，不写文件。

### 集成和历史模式

父流程必须提供：

| 参数 | 要求 |
|---|---|
| `mode` | `integrated-initial`、`integrated-final` 或 `legacy-sync` |
| `code_root` | 绝对代码根路径 |
| `opdir` | 该 implementation unit 的绝对工作目录 |
| `op` / `Op` | 小写发布名 / 公开算子或 unit 名 |
| `implementation_unit` | 父流程冻结的 implementation unit 标识 |
| `framework_scope` | 父流程冻结的 source entry / 框架范围 |
| `terminal_state` | `integrated-final` 必填：`completed`、`blocked` 或 `hard-stop` |

这些父流程提供的路径和目标已经获得授权，不再询问目录或保存路径。仅做只读合法性检查：路径必须为绝对路径，核心产物必须位于给定 `opdir`，输出必须精确落到本模式规定的位置。参数缺失、路径冲突或框架范围冲突时返回父流程修正，不自行猜测。

`integrated-final` 的 `completed` 只能来自父流程已经通过的 build、verify 和 board 等门控。本 skill 不重跑这些门控，也不从 summary 自行推导新算子的完成态。

## 集成/历史模式的单一事实源

| 文档位置 | 唯一主源 | 允许的辅助证据 |
|---|---|---|
| 文档头部、第 1 章 | `<opdir>/docs/spec.md` | `builtin-probe.md`、`reference-impl.md` |
| 第 2 章 | `<opdir>/docs/implementation-contract.md` | `link-analysis.md` |
| 第 3 章 | `<opdir>/scripts/capability_checklist.json` | `decision.md` |
| 第 4 章 | `<opdir>/scripts/op_spec.py` | capability checklist、builtin probe |

上述四个主源与最后记录的 `verify_summary.txt` 先规范化为唯一渲染输入：

```text
<opdir>/docs/operator-manual-facts.json
```

该文件是本 skill 明确要求生成的中间产物，不是某个模型或工具的可选输出。`integrated-initial` 在草稿前首次生成；`integrated-final` 在终态文档前从最新产物整份重建；`legacy-sync` 从历史产物生成，不要求历史 `op_spec.py` 改成新 schema，也不重跑开发流程。Markdown 只读取该 facts 文件；audit 则独立读取原始产物、facts 和候选 Markdown 三方比对，不能用候选反向改写 facts。

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

每个 `sources` 项记录相对 `path` 和当前文件 `sha256`。每个 `chapter_facts` 项记录 `chapter`、核心源中的逐字 `quote` 和公开 `manual_text`。每个 capability 保留原始 `id`、`description`、规范化 `covered_by`，可另加不改变语义的公开 `manual_text`。`scenario_groups` 只负责把 capability 归并为读者能理解的使用场景，不能删除、重复或改写源 capability；`coverage_principles` 负责第 4-1 的白话说明。每个 case 固定记录原始 ID、framework/source entry、模型 dtype、input shape、value domain、属性、逐 case PASS 验证路径、结构化预期输出、公开预期输出文本和预期输出证据。case 顺序必须等于 `op_spec.py`。

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

- `decision.md`：只确认 source entry 的归并和场景分类，不公开 PrimitiveType、源码层级、工作区或内部流程。
- `link-analysis.md`：只投影为“支持转换”“不支持该规格”“不支持该类型”，不公开文件、注册符号或缺陷动作。
- `reference-impl.md`：只补充可观察语义和边界，不公开拉取命令、临时路径或工程取舍。
- `builtin-probe.md`：只补充 source entry 与 builtin 的已验证映射。
- capability checklist 作为第 4 章辅助证据时只检查 `covered_by` 关联；它和 builtin probe 都不得提供或改写 case 字段。

在 `integrated-initial`、`integrated-final` 和 `legacy-sync` 中：

- 禁止重新扫描代码仓，禁止查询外部或框架规格，禁止运行 scan、build、`hs-debug-op-host-accuracy` 或板端流程。
- 现有 `operator-desc/{op}.md` 不是事实源，不得覆盖或“纠正”冻结产物；最终同步必须从最新冻结产物整篇重建。
- 主源之间、主源与父参数之间有冲突，或公开事实缺失时，返回上游修正并输出 FAIL。不得选择“看起来更合理”的版本，不得发明补全。

## 预检与历史分级

对所有带 `opdir` 的模式，在生成前运行：

```bash
python3 <manual_skill_root>/scripts/audit_manual_inputs.py --opdir <absolute_opdir>
```

记录 `OP_MANUAL_INPUT_TIER`。集成模式用它检查核心资产是否可读；`legacy-sync` 必须严格按以下 A/B/C/D 分级：

| 等级 | 条件 | 行为 |
|---|---|---|
| A：可直接同步 | 四个核心源完整、现行 capability schema 可读、最后完整 summary 全绿且能力全覆盖 | facts 内容完整且三项同步 PASS 时生成正式文档；否则只生成迁移草稿 |
| B：可迁移同步 | 语义和用例核心源完整，但使用旧 capability schema、缺少非语义元数据或没有可信全绿 summary | 只读兼容，生成 `<opdir>/docs/operator-manual-draft.md`；不得覆盖正式文档 |
| C：历史验证未通过 | 最新完整 summary 含非零 FAIL/ERR、`HARNESS_EXIT!=0` 或能力未覆盖 | 生成 `<opdir>/docs/operator-manual-draft.md`；不得覆盖正式文档 |
| D：事实源不足 | 缺少或无法读取 spec、contract、capability 或 op_spec | 列出缺失/冲突后停止，不写文件 |

旧 schema 只允许无损读取：

- capability 缺少 `match` 时按空匹配读取，不得从 `desc` 猜结构化参数。
- `framework_scope` 由 capability、op_spec 的非空框架用例和 spec 的 FOUND/NOT_FOUND 交叉确认；冲突即 FAIL。
- 条件产物缺失仅在其触发条件不存在时放行。
- 不重写历史 capability、op_spec、summary 或其他产物。

历史 summary 只取最后一组完整 `VERDICT` + 紧随其后的 `HARNESS_EXIT`，只用于发布资格和已记录能力/验证路径的状态过滤；它不是框架语义、功能规格、shape、dtype 或属性的来源。

验证路径只读取 summary 中逐 case 的明确 `PASS` 行。聚合 `paths=[...]`、全局目标列表或 dtype 名称都不能展开成逐 case 支持结论。历史 summary 没有逐 case 记录时，对应 facts 的 `verification_paths` 为空并降为迁移草稿；不得为了发布补写路径。

对 C 级：

- summary 明确标记失败或未覆盖的 variant/target/path，不得写成已支持，不得在测试表中标成正向通过路径。
- 第 4 章仍逐 case 投影 op_spec 以保持 ID 完整，但行只表示冻结的用例设计；失败路径从“已支持验证路径”中移除或明确写“不支持该规格”。
- summary 只有聚合失败而没有可靠映射时，不猜失败 case；整份文档保持迁移草稿状态，不宣称未证实路径已支持。

## 四章节结构与模式分支

最终文档必须有标题、简述和且仅有以下四个一级编号章节。

### 独立模式的四章节构建

`standalone-generate` 和 `standalone-update` 不要求存在 `opdir` 或冻结产物，也不套用集成/历史模式的逐产物投影规则：

| 文档位置 | 独立模式事实来源与构建规则 |
|---|---|
| 文档头部、第 1 章 | 从用户材料、已有公开文档、仓内材料和必要的官方规格中交叉查证框架语义、属性、输入和输出 |
| 第 2 章 | 扫描并核对 parser/source entry、schema/infer、coder 和实际计算规格，只记录公开支持范围和明确限制 |
| 第 3 章 | 从上述已验证事实归纳关键支持/不支持场景，不写内部实现 |
| 第 4 章 | 为已验证支持范围构造具体测试设计；每行给出 framework、模型 dtype、input_shape、输入数据特征、属性和预期输出，不为不支持规格生成正向用例 |

独立模式使用下方相同的标题、四章节名称和公开表格形状，但把其中的冻结产物来源替换为本表的已查证来源。其测试用例从 `TC-001` 顺序编号，并覆盖已验证的典型值与边界值；它们不需要与不存在的 `op_spec.py` 做 case parity。更新模式可保留仍被当前证据支持的已有用例，但必须删除过时或无法验证的内容。

### 集成/历史模式的四章节投影

以下来源绑定、`covered_by` 检查和 op_spec 精确 case 规则只适用于 `integrated-initial`、`integrated-final` 和 `legacy-sync`。这三个模式不得回退到独立模式取材。

### 文档头部

```markdown
# {Op} 算子设计文档

{来自 spec.md 的公开、已验证语义简述}
```

集成/历史模式只有 `spec.md` 明确给出英文全名、类别或公式时才写对应内容。独立模式使用其已查证来源。所选来源缺少全名/类别时使用不增加新事实的中性已验证描述；缺少公式时省略公式块，不使用通用名称或经验公式补造。

### 第 1 章：ONNX/TFLITE 框架算子描述

```markdown
## 1. ONNX/TFLITE 框架算子描述

### 1.1 {framework/source entry}

**Attributes**

| Name | Type | Default | Required | Description |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

**Inputs**

| Name | Type | Description |
|---|---|---|
| ... | ... | ... |

**Outputs**

| Name | Type | Description |
|---|---|---|
| ... | ... | ... |
```

集成/历史模式按父流程的 `framework_scope`，独立模式按用户确认且已查证的框架范围，为每个 source entry 重复小节。无属性时写 `| — | — | — | — | 无属性 |`。集成/历史模式的 spec 或独立模式证据明确 NOT_FOUND/无转换入口时写“不支持转换”，不编造属性、类型或布局。

### 第 2 章：MindSpore-Lite Micro 功能规格

```markdown
## 2. MindSpore-Lite Micro 功能规格

### 2.1 {framework/source entry} 算子规格

**输入**

| 输入 | 模型数据类型 | 参数含义 | 规格限制 |
|---|---|---|---|
| ... | ... | ... | ... |

**属性**

| 属性 | 数据类型 | 参数含义 | 规格限制 |
|---|---|---|---|
| ... | ... | ... | ... |

**输出**

| 输出 | 模型数据类型 | 参数含义 | 规格限制 |
|---|---|---|---|
| ... | ... | ... | ... |
```

集成/历史模式完全投影 implementation contract 的输入、dtype、属性、输出、shape/layout 和功能限制；独立模式从已查证支持链路构建本章。模型 dtype 与验证路径是两个概念，不能把 full-quant int8 验证路径改写成原生 int8 模型支持。

本章需要说明已验证运行通路时，使用设计语言描述实际覆盖，不公开验证脚本内部任务名：

```markdown
### 2.3 已验证运行通路与限制

| 运行通路 | 已验证的设计范围 |
|---|---|
| x86 主机非量化通路 | 已验证的 float32 和/或原生整数模型 |
| RISC-V 非量化通路 | 已验证的 float32 和/或原生整数模型 |
| RISC-V 全量化 int8 通路 | float32 模型经全量化后实际使用 int8 数据和量化内核 |
| RISC-V 原生整数通路 | 原生整数模型保持其整数数据类型，不计入 int8 量化覆盖 |
```

只保留当前算子真实覆盖的行。表格后直接写设计限制和不支持范围，不写“冻结汇总逐 case 记录了以下通过路径”等流程说明。

### 第 3 章：关键场景分析

```markdown
## 3. 关键场景分析

| 使用场景 | 什么时候会遇到 | 已覆盖行为与限制 | 对应用例 |
|---|---|---|---|
| 常规选择 | 用户在什么情况下使用 | 已验证的行为和必须知道的限制 | TC-... |
```

集成/历史模式先完整保留 capability checklist，再通过 `scenario_groups` 组织公开章节。当 capability 多于 7 项时，必须归并为 3～7 个面向读者的场景；每个场景回答“什么时候会遇到”“已经验证什么”“有什么限制”，不得默认把每个内部 capability 直接公开成一行。每个 capability 必须恰好属于一个 group，group 的 `covered_by` 必须等于成员 capability 用例号的有序并集。找不到、重复或遗漏即 FAIL，禁止为补齐覆盖而新造用例。独立模式改用本节前述已验证场景构建规则，不要求 capability checklist。

### 第 4 章：测试设计

```markdown
## 4. 测试设计

### 4-1 测试用例覆盖原则

**输入是否覆盖常见规模？** 用读者能理解的语言说明 shape、rank、axis 和 batch 覆盖。

**不同选择方式是否正确？** 说明属性、方向、排序或其他主要行为。

**边界和数据内容是否覆盖？** 说明边界值和输入数据特征。

**量化/非量化通路是否覆盖？** 根据逐用例 PASS 记录、模型数据类型和生成代码证据，分别说明非量化、全量化 int8 与原生整数通路覆盖。

### 4-2 用例总表

| 用例编号 | 框架/source entry | 模型 dtype | 已覆盖运行通路 | input_shape | 输入数据特征（value_domain） | 算子属性 | 预期输出 |
|---|---|---|---|---|---|---|---|
| TC-... | ... | ... | ... | ... | ... | ... | ... |
```

上述四个问题的文字和顺序固定，问答来自 facts 的 `coverage_principles`，每项包含 `question` 和 `answer`。答案必须先解释用户能理解的覆盖含义，再让第 4-2 给出精确数据；不要在第 4-1 使用“逐用例投影”“冻结产物”“正向用例”等流程术语。

第四个问题不能只罗列内部验证任务名。先按实际语义分类，再报告覆盖：

- 非量化通路：依据无全量化配置的主机/RISC-V PASS 记录，说明覆盖的框架、用例数和模型数据类型。
- 全量化 int8 通路：只统计 float32 模型经 FULL_QUANT 后确实生成 int8 张量/量化内核的 PASS 用例；必须有 `int8_genuine`、生成内核或等价产物证据。
- 原生整数通路：单独说明 int32 等原生整数模型。即使它执行了名为 `riscv_int8` 的任务，只要张量和内核仍为原生整数，就不能计入 int8 量化覆盖。

结论中的数量必须从 facts 的 cases、逐 case `verification_paths` 和实现/生成证据计算，不能从聚合路径列表或路径名称推断。`verification_paths` 保留机器任务名用于审计，但公开设计文档必须转换为“x86 主机非量化”“RISC-V 非量化”“RISC-V 全量化 int8”“RISC-V 原生整数”等实际含义；全文不得出现 `x86_fp32`、`riscv_fp32`、`riscv_int8`。

以下第 4 章规则只适用于集成/历史模式：

1. ONNX_TEST_CASES 和 TFLITE_TEST_CASES 中每个 case 恰好一行；不遗漏、不合并、不增加 op_spec 中不存在的 case。
2. 保留原始 case ID。数字 `1` 显示为 `TC-001`，`101` 显示为 `TC-101`；不得按表格位置重新编号。
3. framework、shape、K/属性、模型 dtype 和 `value_domain` 从 op_spec case 规范化进 facts；Markdown 逐字段按 facts 的规范格式渲染，不能把 `value_domain` 丢进泛化描述。
4. “模型 dtype”和“已覆盖运行通路”分列。模型 dtype 只来自 op_spec case；内部验证记录只来自最后可信 summary 的同 case 明确 PASS 行，再结合模型 dtype 和生成代码证据转换为读者语言。不得从聚合路径、dtype 名称或经验规则推导覆盖。
5. 预期输出必须有结构化 `expected_outputs`、公开 `expected_outputs_text` 和逐字证据。输出名称/dtype 来自 op_spec 模型构造或 implementation contract；shape 只有在上述来源明确写出 shape 规则时才可把规则应用到 case 参数。final 不允许任何必需字段写“未记录”“待确认”或“尚未执行验证”。
6. `integrated-initial` 尚未产生验证证据时，验证路径单元格固定写“尚未执行验证”，且 facts 的 `production_eligible=false`；该措辞只允许 draft。
7. `integrated-final` 和 legacy A 不增量修补旧表，而是从最新 facts 重建整表，删除已移除 case 并加入新增 case。
8. 不支持的 framework/type/spec 不生成额外正向 case；C 级失败路径不得标成 PASS 或 supported。

## 敏感信息与公开边界

违反任一项即返工：

- 禁止写需求号、任务号、缺陷号、工号、员工号、审批/评审单号、内部编号，或 `AR/MR/CR` 等内部流转编号。
- 禁止写 `REQ-123`、`TASK-123`、`BUG-123`、`JIRA-123`、`MS-1234`、`PRJ-1234`、`AR-123`、`MR-123`、`CR-123`、带标签的六位以上数字串，以及此类占位符。
- 禁止写“Bug号”“问题单号”“xxx编号”“请补编号”“待补编号”“内部单号”或“补 AR/MR/CR 单号”等字段/占位描述。
- 禁止私有系统链接和含 `ar_id=`、`mr_id=`、`cr_id=`、`taskId=`、`issueId=` 的参数。
- 禁止写源码路径、注册符号、LUT、kernel/opcoder 分支、量化实现、工作区和内部缺陷动作。
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
| step0 | 选择模式；独立模式完成两次确认要求，集成/历史模式校验父参数和绝对路径 | 模式、范围、唯一目标明确 |
| step1 | 带 opdir 的模式运行输入 audit；legacy 按 A/B/C/D 分级 | D 或核心冲突立即 FAIL |
| step2 | 从原始主源创建/整份刷新 `operator-manual-facts.json`，逐项保存 source quote/hash | facts schema 完整；缺失和冲突返回上游，不发明 |
| step3 | 只从 facts 在内存中生成完整候选；final 从最新 facts 整表重建第 4 章 | 四章完整；case 顺序和逐字段值一一对应 |
| step4 | 对候选做格式、来源、支持措辞、敏感信息和 placeholder 自检 | 全部 PASS 才能进入发布门控 |
| step5 | 将候选写入目标同目录的临时文件，对 facts 和临时候选运行完整 audit | facts/content/case 三项均 PASS |
| step6 | 三项 audit PASS 后才把临时候选原子提升为唯一文档目标；重新读取并打印 `OP_MANUAL_SYNC` | PASS 或带阻塞原因的 FAIL |

现有正式文档和现有草稿在发布门控通过前都不得修改。候选优先保留在内存；运行 audit 时，才在目标同目录创建可精确识别的临时候选，以保证 PASS 后可在同一文件系统原子提升：

```bash
candidate_path="$(mktemp "${target_path}.candidate.XXXXXX")"
# 将内存候选写入 "$candidate_path"，不要写 "$target_path"
python3 <manual_skill_root>/scripts/audit_manual_inputs.py \
  --opdir <absolute_opdir> \
  --facts <absolute_opdir>/docs/operator-manual-facts.json \
  --manual "$candidate_path" \
  --publication <draft|migration-draft|final>
```

只有 `OP_MANUAL_FACTS_SYNC=PASS`、`OP_MANUAL_CONTENT_SYNC=PASS` 和 `OP_MANUAL_CASE_SYNC=PASS` 同时成立，才以原子 rename/move 将临时候选提升为本模式唯一文档目标。若 FAIL 或命令异常，删除/丢弃该临时候选并保持已有文档 target 原样；先修 facts 或内存候选，再用新的临时候选重跑。临时候选不是持久输出，不得残留。不得为取得 PASS 修改 op_spec、capability 或 summary。独立模式没有 opdir/facts audit，但也必须先完成 step4 自检，再通过同目录临时候选原子提升目标。

带 `opdir` 的正式发布必须同时满足：父终态允许发布、legacy 等级允许发布、facts `provenance=production`、`production_eligible=true`，以及 facts/content/case 三项同步 PASS。

## 输出决策

| 模式/状态 | publication | 唯一目标 |
|---|---|---|
| `standalone-generate` / `standalone-update` | `final` | `<code_root>/operator-desc/{op}.md` |
| `template-analysis` | `none` | `NONE` |
| `integrated-initial` | `draft` | `<opdir>/docs/operator-manual-draft.md` |
| `integrated-final terminal_state=completed` | `final` | `<code_root>/operator-desc/{op}.md` |
| `integrated-final terminal_state=blocked\|hard-stop` | `draft` | `<opdir>/docs/operator-manual-draft.md` |
| `legacy-sync` A 且 facts 内容完整 | `final` | `<code_root>/operator-desc/{op}.md` |
| `legacy-sync` A 但 facts 内容不完整 | `migration-draft` | `<opdir>/docs/operator-manual-draft.md` |
| `legacy-sync` B/C | `migration-draft` | `<opdir>/docs/operator-manual-draft.md` |
| `legacy-sync` D | `none` | `NONE` |

一次调用不得同时刷新 draft 和 final，且除 mandatory facts 中间产物外最多提升一个持久文档目标。完成或失败时，最后一行使用：

```text
OP_MANUAL_SYNC=PASS mode=<mode> publication=<final|draft|migration-draft|none> path=<absolute-path|NONE>
OP_MANUAL_SYNC=FAIL mode=<mode> publication=none path=NONE
```

失败详情在终态行之前简要列出并返回父流程。`integrated-initial` 失败会阻塞进入编码；`integrated-final` 失败会阻塞完成声明。

## 自检与最终复核

候选提升前逐项检查：

- [ ] 模式、授权和唯一输出与决策表一致；不生成 `docs_operator/{op}/plan.md` 或其他文件。
- [ ] 带 opdir 的模式已从本次最新原始源刷新 `operator-manual-facts.json`；source path/hash、quote、case 顺序和 provenance 均正确。
- [ ] 文档只有规定的四个编号章节；独立模式使用已查证事实构建，集成/历史模式每章来自规定主源。
- [ ] capability 多于 7 项时，第 3 章已归并为 3～7 个读者场景；每个 capability 恰好出现一次，group 用例号是成员 `covered_by` 的准确并集。
- [ ] 第 4-1 的四个问题和答案来自 `coverage_principles`，使用用户语言解释覆盖范围，没有流程术语堆叠。
- [ ] 集成/历史模式没有仓库重扫、外部查询、build、verify 或 board 重跑。
- [ ] 现有正式文档没有覆盖冻结事实；final 的第 4 章已经整表重建。
- [ ] formula/full name/category 未被发明；缺公式时已省略。
- [ ] 不支持项使用固定措辞，C 级失败 variant/target/path 未写成支持。
- [ ] 模型 dtype、已覆盖运行通路、value_domain/输入数据特征各自保留且没有混淆；机器验证标识只保留在 facts，公开设计文档已转换为实际运行含义。
- [ ] 文档标题和正文定位为算子设计文档；全文没有出现内部验证任务名。
- [ ] 集成/历史模式中 op_spec 每个 case 恰好一行，原始 `TC-*` ID 未重排；每个 `covered_by` 都存在。
- [ ] 全文没有敏感信息、内部实现、私有链接或“待确认”。
- [ ] facts/content/case 任一 audit 尚未通过时，既有正式文档/草稿仍未被覆盖；失败临时候选会被丢弃。

提升后重新读取目标并确认：

1. 实际只持久写入决策表中的一个文件，或命中允许的零写入分支；没有残留临时候选。
2. 四章、表头和支持措辞完整，旧 case 不残留，新 case 不遗漏。
3. 带 opdir 的输出得到 `OP_MANUAL_FACTS_SYNC=PASS`、`OP_MANUAL_CONTENT_SYNC=PASS` 和 `OP_MANUAL_CASE_SYNC=PASS`；否则不得发布正式文档或报告同步成功。
4. terminal_state 和 legacy 等级没有被文档内容反向改写。

## 变量与参考

| 变量 | 含义 |
|---|---|
| `<manual_skill_root>` | `hs-design-op-manual` skill 的绝对目录 |
| `<code_root>` | MindSpore Lite 代码根绝对路径 |
| `<opdir>` | 单个 implementation unit 的绝对工作目录 |
| `target_path` | 按输出决策表解析出的唯一持久文档目标绝对路径 |
| `{op}` / `{Op}` | 小写发布文件名 / 公开算子或 unit 名 |
| `framework_scope` | 父流程冻结的 source entry / 框架集合 |
| `terminal_state` | `integrated-final` 的 `completed`、`blocked` 或 `hard-stop` |
| `model dtype` | 模型输入本身的数据类型 |
| `verification path` | fp32、full-quant int8 等独立验证路径，不等于模型 dtype |
| `value_domain` | 输入值域/输入数据特征，如 mixed、positive、negative、ties |

独立模式可参考已确认的 `operator-desc/sub.md`、`operator-desc/lstm.md` 的结构和表格风格，但不得复用其算子事实。集成和历史模式不得把这些示例或现有目标文档当作事实源。
