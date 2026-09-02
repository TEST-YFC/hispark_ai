# 文档模板与渲染规则

目录：

- [设计文档与验证文档结构](#设计文档与验证文档结构)
- [独立模式的设计/验证文档构建](#独立模式的设计验证文档构建)
- [产物集成模式的设计文档投影](#产物集成模式的设计文档投影)
- [验证文档的固定结构](#验证文档的固定结构)

以下内容是 `hs-design-op-manual/SKILL.md` 的按需细节，步骤和输出契约保持不变。

## 设计文档与验证文档结构

产物集成模式必须按以下两个模板分别维护两份主文档：

- [`operator-design-doc-template.md`](operator-design-doc-template.md)：
  `<opdir>/docs/{op}-operator-design-doc.md`，只记录规格范围、支持限制、七类能力复用裁决、关键场景和软件调用链。
- [`operator-verify-doc-template.md`](operator-verify-doc-template.md)：
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

验证文档使用 [`operator-verify-doc-template.md`](operator-verify-doc-template.md)，固定包含以下章节：

```markdown
## 1. 测试设计

### 1.1 测试覆盖原则

**输入是否覆盖常见规模？** 用读者能理解的语言说明 shape、rank、axis 和 batch 覆盖。

**不同选择方式是否正确？** 说明属性、方向、排序或其他主要行为。

**边界和数据内容是否覆盖？** 说明边界值和输入数据特征。

**量化/非量化通路是否覆盖？** 根据逐用例 PASS 记录、模型数据类型和生成代码证据，分别说明非量化、全量化 int8 与原生整数通路覆盖。

### 1.2 用例总表

| 用例编号 | 测试点 | 框架/source entry | 模型 dtype | 已覆盖运行通路 | input_shape | 输入数据特征（value_domain） | 算子属性 | 预期输出 |
|---|---|---|---|---|---|---|---|---|
| TC-... | ... | ... | ... | ... | ... | ... | ... | ... |
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
