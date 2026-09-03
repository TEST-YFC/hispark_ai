# 文档事实规则与生成文件分级

目录：

- [调用规则与路径授权](#调用规则与路径授权)
- [文件同步模式的数据来源](#文件同步模式的数据来源)
- [预检与文件分级](#预检与文件分级)

进入对应阶段时读取本文件；步骤和检查点保持不变。

## 调用规则与路径授权

### 独立模式

`standalone-generate` 和 `standalone-update` 在开始时一次性确认
`mindspore-lite` 代码根、算子工作目录 `<opdir>`、`{op}`、`{Op}`、框架范围以及两份绝对目标路径：
`<opdir>/docs/{op}-operator-design-doc.md` 和
`<opdir>/docs/{op}-operator-verify-doc.md`。确认后由 agent 自动查证、生成、审计和成对发布，
不在写入前再次询问。不得把文档写到代码根的公共文档目录。

独立模式继续查证框架公开规格和仓内支持链路：parser/source entry 缺失写“不支持转换”；schema/infer/计算规格不覆盖某属性、shape、layout 或方向写“不支持该规格”；coder/目标类型未注册写“不支持该类型”。阶段更新用 Markdown todo 展示当前 step 和已得到的证据，不提前勾选未完成门控。建议使用以下通用探查命令，并把完整输出保存到 `<opdir>/docs/logs/`，不得只贴截断片段：

```bash
rg -n "Onnx.*Parser|Parser.*<Op>|Parse\\(" <code_root>
rg -n "Populate.*<Op>|<Op>Parameter|InferShape" <code_root>
rg -n "REG_KERNEL|REG_OPERATOR_CODER|OpCoder|Quantizer" <code_root>
rg -n "PrimitiveType.*<Op>|<Op>Fusion" <code_root>
```

将 `<Op>` 替换为本次目标算子；命令只用于 standalone 查证，不能带入产物集成模式。

`template-analysis` 只确认分析范围，不要求保存路径，不写文件。

### 文件同步模式（artifact-sync）

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
Stage0 尚未完成执行确认时的阻断只允许由父 workflow 做状态收尾，不属于可发布的
`integrated-final` 场景；此时不得调用本 Skill 或修改两份正式文档。

## 文件同步模式的数据来源

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

每个 `sources` 项记录相对 `path` 和当前文件 `sha256`。每个 `chapter_facts` 项记录 `chapter`、核心源中的逐字 `quote` 和公开 `manual_text`。每个 capability 保留原始 `id`、`description`、规范化 `covered_by`，可另加不改变语义的公开 `manual_text`。`scenario_groups` 只负责把 capability 归并为读者能理解的使用场景，不能删除、重复或改写源 capability；`coverage_principles` 负责验证文档 `1.1 测试覆盖原则` 的白话说明。每个 case 固定记录原始 ID、`test_point`、framework/source entry、模型 dtype、input shape、value domain、属性、逐 case PASS 验证路径、结构化预期输出、公开预期输出文本和预期输出证据。`test_point` 必须逐字来自 `op_spec.py`，用于说明该用例验证什么，不能由文档阶段另行发挥。case 顺序必须等于 `op_spec.py`。

capability 的公开改写不得扩大用例实际覆盖：case 只把属性写成默认值时，必须写“默认值配置”，不能写“省略属性后的默认解析”；只有模型构造确实省略该属性时才能宣称覆盖默认解析。同理，spec/contract 的 opset 策略不能写成另一个 opset 测试覆盖，除非对应验证模型真实使用该 opset。

case 字段名和形状固定如下；算子特有属性只放在 `attributes`：

```json
{
  "id": "TC-001",
  "test_point": "验证最后一维 TopK 的 Values/Indices 语义与排序",
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

## 预检与文件分级

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
