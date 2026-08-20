---
name: hs-dev-op-implement
description: >-
  Prepare or apply MindSpore Lite Micro operator source changes for HiSpark.AI, including source-entry analysis, PrimitiveType reuse decisions, frozen implementation contracts, parser/populate/infer/kernel/opcoder/quantizer changes, INT8 paths, and implementation quality gates. The top-level workflow calls this skill first with mode=prepare (analysis and contracts only, no source writes), then with mode=apply only after the initial manual draft passes its pre-source gate. Use this stage-specific skill directly only when the user explicitly names hs-dev-op-implement or explicitly requests source-only work with no testing/build/final documentation. Generic requests such as “适配一个算子”, “新增算子”, “支持算子”, “port an operator”, or requests that also include testing, documentation, build, flash, or board verification belong to hs-workflow-op-development instead.
---

# MindSpore Lite 算子实现

本 skill 只负责两件事：准备算子实现合同，以及在前置文档通过后生成或修复 MindSpore Lite
算子源码。它不生成正式设计文档，不拥有 Host 用例的执行和判定，不构建 WS63 固件，
不烧录开发板，也不调用其他 skill。完整适配由 `hs-workflow-op-development` 编排。

## 调用模式

| 模式 | 执行范围 | 允许修改算子源码 | 终态 |
|---|---|---|---|
| `mode=prepare` | step0-step3：扫描、复用裁决、合同、能力清单和计划版`op_spec.py` | **禁止** | `OP_PLAN_GATE=PASS`并返回顶层workflow |
| `mode=apply` | 先验证`PRE_SOURCE_GATE=PASS`，再执行step4-step6 | 允许 | `IMPLEMENT_GATE=PASS`或结构化FAIL |
| `mode=all` | 仅用于显式单独调用：先prepare并暂停；由调用者取得初版文档和`PRE_SOURCE_GATE`后，再恢复apply | prepare阶段禁止，apply阶段允许 | 两段终态均有证据 |

顶层workflow必须分两次调用`prepare`和`apply`，中间由workflow调用
`hs-design-op-manual mode=integrated-initial`。本skill不得自行调用文档Skill。`apply`收到的合同、
能力清单、计划用例或初版文档哈希变化时，返回prepare重新冻结，不能一边改源码一边补文档。

算子最多涉及七类代码能力，但不是每个算子都要新建七层：

```text
① Schema  ② Parser  ③ Populate  ④ Infer  ⑤ Kernel  ⑥ OpCoder  ⑦ Quantizer
```

本 skill 的默认触发范围是“只分析/只实现算子源码”。用户只说“实现算子 X”时，若没有
明确“只实现、不验证/不构建/不写文档”，应回到 `hs-workflow-op-development`；若用户明确
只实现源码，则在开始前说明不会自动生成测试、构建、烧录或最终文档。带有“在 WS63 上运行”、
“编译并测试”、“完整流程”、“生成文档”或“烧录/板测”的请求一律交给 workflow，不在本
skill 内截断流程。

路径以 MindSpore Lite 代码根为基准，即包含 `schema/`、`tools/` 和 `src/litert/` 的目录。HiSpark.AI 仓库中的常见位置是 `src/mindspore-lite/mindspore-lite/`。`<skill_root>` 表示本 skill 目录。

## 职责边界

| 本 skill 负责 | 本 skill 不负责 | 交给谁 |
|---|---|---|
| 查证 source entry、扫描七层链路，并按能力合同生成编码前计划版`op_spec.py` | 执行精度用例、数值判定和Host产物 | `hs-verify-op-host` |
| source grouping、复用/新建裁决 | 生成算子设计文档 | `hs-design-op-manual` |
| 编写和修复算子源码 | 构建 WS63 固件 | `hs-dev-build`，由 workflow 调用 |
| 实现阶段 code style 与安全门禁 | 烧录固件 | `hs-dev-flash`，由 workflow 调用 |
| 输出能力清单和实现交接单 | 板端精度判定 | `hs-verify-op-board` |

如果收到超出边界的任务，只完成被明确指定的专项阶段，并输出交接信息；不要自行串联其他 Skill。

## 用户可见进度

`prepare`执行step0-step3，`apply`执行step4-step6。阶段完成前先展示门控证据，再勾选todo。

```markdown
待办[<implementation_unit>]:
- [ ] step0 确定范围和 source entry
- [ ] step1 扫描规格与仓内现状
- [ ] step2 完成 grouping、复用/新建和层集裁决
- [ ] step3 冻结链路分析与能力清单
- [ ] step4 编写或修复算子源码
- [ ] step5 完成编码后交叉代码审查
- [ ] step6 通过实现质量门禁
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
│   ├── source-freeze.json           # prepare开始前的源码状态receipt
│   ├── code-style-audit.md          # 规范身份与逐规则审计证据
│   ├── operator-manual-facts.json  # 编码前由文档skill冻结
│   ├── operator-development-report-{op}.md # 唯一人读主文档；先填设计，终态回填验证
│   ├── reference-impl.md          # 实际路径为 <opdir>/docs/reference-impl.md；运行时产物，不是 Skill 包内文件
│   └── builtin-probe.md           # 同族多 builtin 时
├── scripts/
│   ├── capability_checklist.json
│   └── op_spec.py                  # 编码前冻结的计划版用例
└── logs/
    └── scan_op_<Op>.log
```

上述目录树描述的是 `<opdir>` 的运行时交付目录，不是本 Skill 包的固定资源清单；其中 `docs/`
和 `<opdir>/scripts/capability_checklist.json` 等文件由当前算子流程生成。`op_spec.py` 的语义和执行属于 Host 验证 skill，但编码前必须按能力清单生成计划版并通过
机械校验；本skill必须触发并核对该交接产物，不能等源码写完后才设计
用例。算子手册facts/Markdown仍由文档skill生成；本skill的prepare只输出文档输入，
由workflow调用`integrated-initial`冻结facts和草稿。本skill的apply只核对这些输入已经通过
`PRE_SOURCE_GATE`，不得越权调用文档skill。构建包、固件和烧录结果属于workflow及对应leaf。

## 安全红线

违反任一项即返工：

1. 标准 ONNX/TFLite 算子不得使用 `ops::Custom`、`PrimType_Inner_*` 或 `REG_BUILIN_CUSTOM_CODER` 走捷径。
2. 存在性、语义、注册可达性只认可本次查证；文件存在不等于已注册或可达。
3. 不通过 `git checkout`、`git stash`、`git submodule update` 改写受管子模块状态，不删除整个 build 目录碰运气。
4. 不为编译通过删除功能分支，不把已有 kernel 当作天然正确；复用即接管该实现单元的存量质量。
5. 浮点输入算子默认实现真实 INT8 通路；原生整数算子按规格逐 dtype 覆盖，不能把“量化豁免”解释成跳过原生 `int8/uint8/int32/...`。
6. 不删除校验、边界保护或错误传播来压住失败；不以未运行的猜测宣称“不支持某形态”。
7. 不在源码、日志或文档中写入密钥、令牌、私有地址、用户数据或内部单号；外部输入用于路径、长度、索引、格式串或进程参数前必须校验。

## 总流程

| Step | 目标 | 必做动作 | 门控产物 |
|---|---|---|---|
| step0 | 冻结范围 | 列出 framework × operator source entry；解析语义名；确定 `<opdir>` | 范围声明 |
| step1 | 查证事实 | 每个 source entry 运行并完整阅读 `scan_op.sh`；归档完整日志 | FOUND/NOT_FOUND/UNREACHABLE 与七层扫描证据 |
| step2 | 冻结实现决策 | source grouping；decision2 复用/新建；decision3 层集开关 | `docs/decision.md` 与逐层做/跳表 |
| step3 | 冻结编码前全部输入 | 生成spec、链路分析、能力清单和implementation contract；review已有/复用能力；生成计划版`op_spec.py`并校验 | `OP_PLAN_GATE=PASS`，随后交给workflow生成初版文档 |
| step4 | 实现源码 | 先通过`PRE_SOURCE_GATE`，必要时对比参考实现，再按七层模板最小修改 | 源码diff与能力落点 |
| step5 | 编码后交叉审查 | 审核注册键、分支可达性、量化归属、折叠/重写和死代码 | `docs/code-review.md` |
| step6 | 实现质量门禁 | 运行快速预检、code style、安全和 diff 审计 | `IMPLEMENT_GATE=PASS` 或结构化 FAIL |

## step0：冻结范围

推荐输入是“只实现 ONNX 的 X”或“用 hs-dev-op-implement 分析 X”。不要在扫描前断言某框架不存在该算子。多个入口先分组再实现；多个 implementation unit 分别维护工作区和 todo。

确定`<opdir>`和`<code_root>`后、执行任何扫描或源码动作前运行：

```bash
OP_PLAN_RUN_ID="op-plan-<本轮唯一ID>"
python3 <skill_root>/scripts/gate_artifacts.py \
  --opdir <opdir> --op <Op> --stage source-freeze --code-root <code_root> \
  --plan-run-id "$OP_PLAN_RUN_ID" --framework <framework>
```

只有`SOURCE_FREEZE_GATE=PASS`才进入step1。receipt允许源树开始时已经dirty；它冻结的是本轮
prepare开始时的真实状态，而不是强迫清理用户改动。prepare和pre-source会复算同一指纹，
从而区分“原本已有改动”和“文档生成前偷跑的源码改动”。

`source-freeze.json`绑定本轮`OP_PLAN_RUN_ID`、算子、框架范围和code root；同一轮禁止覆盖。
只有上一轮stage1已经结构化终止、workflow明确宣布开始新规划轮次时，才可换新ID并显式传
`--rotate-source-freeze`，脚本会先把旧receipt归档到`docs/source-freeze-history/`。不得通过
重新freeze来掩盖本轮prepare期间的源码变化。每个framework都要在首次freeze时列入scope。

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
- `code_findings`：边界检查、rank、内存、返回值、code style、安全红线和已知缺陷模式；
- `disposition`：每层只能是 `REUSE_REVIEWED`、`FIX_REQUIRED` 或 `N/A`，并映射 capability ID。

任何已有层存在 `FIX_REQUIRED` 都进入 step4 修复范围。禁止因为“这不是本次新增代码”而延期；Host 测试前才首次阅读存量实现，说明 step3 review 没完成。

能力清单从 `hs-verify-op-host/scripts/capability_checklist.template.json` 复制结构，但内容由本 skill 根据规格与实现裁决填写。每条能力保留稳定 ID、可读描述和可机械匹配的 `match`；本 skill 不填写虚假的 PASS，也不为现有测试反向弱化能力。

同族多 builtin 场景把实际“输入形态 → builtin”解包证据写入 `builtin-probe.md`。缺实际命令输出时不能用“无归一化”代替证据。

在prepare阶段继续冻结`implementation-contract.md`，至少包含source entries、primitive、
输入/可选输入、属性、layout、dtype、输出、验证方式和暂不支持范围。计算路径新增、修改、
启用或接管时，同时生成`<opdir>/docs/reference-impl.md`，记录上游实现与仓内相似实现的算法、
边界和采纳理由；该文件是算子项目运行时产物，不是Skill包内置模板。

仍在prepare阶段、尚未修改任何①-⑦源码时，使用
`hs-verify-op-host/scripts/operator_spec_template.py`作为唯一模板，把能力清单逐项落实到
`<opdir>/scripts/op_spec.py`。每条`covered_by`必须指向计划版中的真实case ID，非平凡能力
保留可机械核对的`match`，然后运行：

```bash
python3 <hs-verify-op-host>/scripts/validate_op_spec.py <opdir>
```

能力清单是单向真值：修正或补充op_spec，禁止为迁就现有case反向删除、改弱能力行。只有
`OP_SPEC_GATE=PASS`才能执行prepare终态门禁。

所有prepare产物落盘后，按冻结的每个framework运行机械门禁：

```bash
python3 <skill_root>/scripts/gate_artifacts.py \
  --opdir <opdir> --op <Op> --stage prepare --code-root <code_root> \
  --plan-run-id "$OP_PLAN_RUN_ID" --framework <framework>
```

只有每个framework都输出`OP_PLAN_GATE=PASS`，且prepare开始前后由workflow记录的算子源码
指纹一致，才能把规划产物交给workflow。`mode=prepare`必须在这里停止；不能进入step4，不能
调用文档Skill，也不能生成任何算子源码。门禁失败时补规划产物，不用对话里的表格代替文件。

## step4：编写或修复源码

本步骤只允许`mode=apply`进入。workflow必须已经调用
`hs-design-op-manual mode=integrated-initial`，生成并审计：

```text
<opdir>/docs/operator-manual-facts.json
<opdir>/docs/operator-development-report-{op}.md
```

写任何①-⑦源码前，运行pre-source门禁：

```bash
python3 <skill_root>/scripts/gate_artifacts.py \
  --opdir <opdir> --op <Op> --stage pre-source --code-root <code_root> \
  --plan-run-id "$OP_PLAN_RUN_ID" --framework <framework>
```

只有每个framework都输出`PRE_SOURCE_GATE=PASS`才允许动源码。该门禁会机械复算
`source-freeze.json`中的Git可见源码指纹，检查计划版op_spec、初版facts/draft及facts记录的
四个主源哈希，并重新运行文档Skill的facts/content/case三项audit；仅在对话中声称
“文档已生成”不算证据。

能力清单、contract、op_spec或初版文档后续发生变化时，立即停止apply并回到workflow
stage1：重新执行prepare、`integrated-initial`和pre-source门禁。不能先改源码后补文档。

`code-style.md` 是随本 Skill 分发的团队统一 C/C++、CMake 和注册接线编程规范，不是用户需要提前
安装的工具或环境。在本轮首次修改任何①-⑦源码前，必须完整读取
`references/code-style.md` 和 `references/code-quality-gate.md`，并记录：

```text
CODE_STYLE_SOURCE=<本 Skill 安装目录>/references/code-style.md（运行时必须展开为绝对路径）
CODE_STYLE_SOURCE_SHA256=<sha256>
```

该规范由 Skill 自带，使用者无需提供或创建任何额外的 `code-style.md`。格式冲突由代码根
`.clang-format` 决定；安全和可维护性规则由 Skill 内置规范决定。
如果实际选中的规范源在实现期间发生变化，必须重新读取并重新执行 step6 审计。

随后，每一层动笔前打开 `references/implementation-guide.md` 的对应小节，以仓内同族实现和模板为底稿。INT8 另读 `references/int8-coder-conventions.md`；fusion 另读 `references/optimizer-fusion-template.md`。

写Parser前必须把规格中的属性、输入顺序和可选输入逐项审计并展示，不能只写“Parser
已实现”：

| 项目 | 必须记录的结论 |
|---|---|
| 每个属性 | 支持并转发到哪个字段 / 明确暂不支持并在Parser注释留痕 |
| 每个opset版本变化 | 仅默认值变化 / 计算语义变化，分别列出，不可合并描述 |
| 输入顺序 | source entry顺序 → Primitive/Parameter顺序的逐项映射 |
| optional input | initializer还是dynamic input；缺省时由哪层补默认值 |
| dtype/layout | Parser是否只搬运，还是需要显式转换/重排；与contract逐字一致 |

项目策略是：默认值与语义按最新opset实现，不临时发明opset分支；扫描发现
版本差异时Parser加入 `Project policy: parse per opset <N> semantics regardless of model
opset.` 注释，语义差异另写事实注释。属性审计必须落到 `decision.md`或
`implementation-contract.md`，并由`gate_artifacts.py --stage pre-source`机械验收。

组合算子还必须完成构造型fusion审计；任何算子都要完成消除/重写型pass审计。命中
消除型pass时，必须记录触发/存活条件，并在能力清单设计“一条pass不触发且真到Kernel”
和“一条pass触发且模型整体正确”的两类case；后者不得冒充Kernel覆盖。

实现中持续回填能力落点。复用分支只补缺失或有缺陷的部分，不重建已经证明等价且可达的层；但验证反馈定位到存量代码时，该缺陷仍属于本 implementation unit。

新增代码完成后，再对“新增/修改代码 + 已复用代码的接口边界”做一次交叉review：逐条沿
capability从parser输入走到生成代码调用，确认修改侧与复用侧的字段、dtype、shape、默认属性
和量化参数没有断层。把新增发现更新到`existing-capability-review.md`；如果发现改变了冻结语义、
能力或计划用例，必须回到stage1重新生成初版文档，不能在apply阶段重跑pre-source后继续。

## step5：编码后交叉代码审查（强制）

这不是“看一眼 diff”的可选步骤，而是 `IMPLEMENT_GATE` 的组成部分。审查人或 agent 必须
从注册表、派发键、分支条件和生成调用四个方向独立核对，不能只依据编译成功或单个 PASS 用例：

1. **注册键与分支可达性**：列出每个 `REG_KERNEL*`、`REG_OPERATOR_CODER`、parser、populate、
   infer 和 quantizer 注册的完整键（primitive、target、首输入 dtype、其他选择字段），逐键
   对照运行时/coder 内的 dtype 分支。每个已注册 dtype 必须有可达且被 case 覆盖的处理；
   分支条件使用的 dtype 必须是实际数据输入，而不是 condition/index 的派发键。发现永不成立
   的分支、重复键、被更高优先级注册遮蔽的路径或“注册了但 `Collect()` 不会生成调用”的
   路径时，标 `FIX_REQUIRED`，不能以 dead code 留在交付中。
2. **量化注册归属**：逐项核对量化器支持列表、通用白名单、算子专用白名单和 parser 返回
   primitive 的查找路径。支持项必须落在与其语义对应的最窄注册点；不能仅把算子塞进通用
   白名单来绕过专用策略。审查记录实际 lookup 符号、命中的列表和生成模型的量化属性，
   并至少用一个真正进入量化 coder 的 case 验证，而不是只看 fp32 通过。
3. **优化/折叠后的语义**：确认 converter 可能执行的常量折叠、节点消除、重写和 fusion。
   对每个可能替换目标算子的 pass，设计两类 case：一类阻止该 pass 使节点真实到达
   Kernel/OpCoder，另一类允许 pass 触发并验证替换后的整图语义。若算子输入全为 initializer，
   必须明确这是“算子执行覆盖”还是“折叠结果覆盖”，不能把折叠后的 Broadcast/Reshape/
   常量节点误报成原算子 Kernel 已执行。模型图、转换日志或生成 C 中必须有可核验的证据。
4. **整数与混合 dtype**：按规格逐 dtype 检查注册、参数解析、Kernel、OpCoder 和测试输入；
   `int8`、`uint8` 混用时逐输入核对 scale/zero-point、累加和饱和，不能因类型名相近而共享
   未审计的分支。对支持列表中未实现或不可达的 dtype，必须明确写入暂不支持范围并让门禁失败，
   不能保留永不执行的注册作为“已支持”证据。
5. **死代码与失败路径**：启用编译器 warning（至少 unreachable/dead branch、未使用变量、
   switch 覆盖和隐式 fall-through 的等价检查）并结合静态搜索；所有错误返回、边界守卫和
   `Collect()` 依赖必须可追踪。修复编译错误时禁止删除能力分支；若确需删除，必须同步更新
   decision、contract、capability checklist 和测试覆盖。

审查结果写入 `<opdir>/docs/code-review.md`。除说明文字外，文件必须包含一个 fenced JSON
对象（或整个文件为 JSON），顶层至少有 `reviewed_files`、`registration_matrix`、
`branch_reachability`、`quantizer_ownership`、`folding_and_rewrite_cases`、`findings` 和
`disposition`。四个矩阵必须是非空对象列表：注册矩阵逐项记录
`key/dtype/condition/callee/case_id/evidence_location/status`；分支矩阵记录 `branch/case_id/evidence_location/status`；量化归属记录
`capability/expected_owner/actual_owner/lookup_evidence/model_evidence/evidence_location/status`；折叠矩阵记录
`mode(blocked|allowed|N/A)/case_id/expected_node/evidence/evidence_location/status`。每个注册 dtype 和分支都必须
指向真实 case 或明确的 N/A 证据；`UNREACHABLE`、`DEAD_CODE`、`FIX_REQUIRED`、`FAIL` 均不得
留在最终审查中。折叠/重写的 blocked case 必须证明目标 Kernel/OpCoder 真执行，allowed case
必须证明重写后的整图语义正确，不能把后者冒充目标算子覆盖。缺少该文件、JSON 结构不完整、
身份/分支/折叠证据无法追踪时，`IMPLEMENT_GATE` 必须为 FAIL。证据字段必须给出
实际源码、生成 `net*.c`、转换日志的路径与行号或可复现命令；只写“已检查”“应当可达”
等无定位说明不算证据。对于允许重写的 case，必须同时记录目标节点被替换后的节点身份和
整图输出证据；对于 blocked case，必须记录生成代码中目标 Kernel/OpCoder 符号的命中位置。

若本轮新增了 `.c/.cc`源文件而非只修改已有文件，进入构建前必须触发对应CMake重新
configure：先确认该目录的 `CMakeLists.txt`通过GLOB或显式列表消费新文件，再由workflow
构建前 `touch`该 `CMakeLists.txt`。否则增量构建可能不收新对象，却链接旧库产生假结论。

## step6：实现质量门禁

完整执行 `references/code-quality-gate.md`。门禁同时放在本专项 Skill 和顶层 workflow：这里在交付实现前执行，workflow 在构建前复核，避免本 Skill 单独调用时漏检，也避免跨阶段修改绕过门禁。编码后交叉审查必须先通过，才可执行本 step6。

最低证据：

```bash
bash <skill_root>/scripts/quick_check.sh <code_root>
git -C <code_root> diff --check
```

再对本次修改的 C/C++ 文件运行仓内 `.clang-format` 检查、逐条审计本轮
`CODE_STYLE_SOURCE` 中的适用规则以及安全红线。审计结果必须按规范规则编号（例如
`CMT.04`、`FUD.05`、`INT.06`、`FUU.15`）给出适用性、证据和 PASS/FAIL，不能只写
“已符合代码规范”。结果固定写入`<opdir>/docs/code-style-audit.md`，文件头记录
`CODE_STYLE_SOURCE`和`CODE_STYLE_SOURCE_SHA256`，表格逐行记录
`rule_id/applicability/evidence/status`。任何FAIL或缺失规则行都回step4；不要用格式化掩盖
语义改动。

只有以下条件同时满足才输出：

```text
IMPLEMENT_GATE=PASS unit=<implementation_unit>
```

- decision、spec、link analysis、contract 和 capability checklist 存在且互相一致；
- 计划版 `op_spec.py`已经通过validator，且每条能力均映射到计划case；
- `integrated-initial` facts/content/case audit均PASS，编码前草稿存在；
- 本次源码 diff 的每个文件都能映射到某条能力或必要注册点；
- `quick_check.sh` 没有真实 FAIL，rank advisory 已逐项处置；
- code style 与安全检查没有未解决项；
- `CODE_STYLE_SOURCE`和SHA-256已记录，逐规则审计为`CODE_STYLE_AUDIT=PASS`；
- `<opdir>/docs/code-style-audit.md`覆盖规范源中的全部规则ID，适用项均有证据且无FAIL；
- 没有构建、host、文档、flash 或 board 的虚假完成声明。

在输出 `IMPLEMENT_GATE=PASS`前逐项执行以下结案检查；任一项不适用要写N/A及证据，
不能静默删除：

- decision2新建/复用裁决有候选排查和逐项等价/不等价证据；属性审计、构造型fusion
  审计、消除/重写pass审计均已呈现。
- Parser注册名/builtin与规格逐字一致；激活子类型返回 `ops::Activation`；复用路线的
  Parser返回冻结的复用Primitive。
- 新PrimType的schema、`REG_MINDSPORE_OPERATOR`、独立Parameter（`OpParameter`首字段）、
  Populate、Infer注册和⑤/⑥使用的PrimitiveType全部一致。
- 浮点输入且需量化的算子有真实float与INT8 Kernel/Coder及量化器；原生整数算子按规格
  分别覆盖int8/uint8/int32/int64/bool，不用“量化豁免”跳过原生dtype。
- INT8签名携带真实scale/zero-point；逐输入重量化、累加位宽、饱和、per-tensor/
  per-channel与 `Collect()`依赖经过审计；生成代码确实调用目标INT8符号。
- 首输入为condition/index时⑤/⑥只有一组首输入派发键，内部再按数据Tensor dtype分支；
  不存在同键第二注册抢占。
- infer/runtime/coder固定shape数组使用同一rank上界；infer显式拒绝超界，每个写定长数组
  的循环前有守卫；Init/Resize/Prepare返回值均传播。
- 广播实现使用真实stride/tile设施，快路条件逐输入成立，不以 `i % num`近似一般广播。
- OpCoder `Collect()`列全所需 `.h/.c`，serializer结构与底层函数签名一致，无模板残留、
  魔数、错误arity或过期版权年。
- `capability_checklist.json`原行内容未被静默改弱，每行均有实现落点和计划case；若验证
  已回流，则只有真实PASS case可填covered_by，最终必须 `capabilities=N/M`且N=M，除非
  用户裁决并由VERDICT记录 `ACK_REDUCED`。
- `git diff`终审将每个修改文件映射到能力/注册点；失败方案的伴生include、dead pass、
  半拆守卫全部清理；被放开的路径有PASS用例，否则连守卫一起还原。
- `docs/code-review.md` 已完成并且每个注册键、dtype 分支、量化列表、优化/折叠 case 和
  生成调用均有证据；死代码、重复注册和错误白名单归属均为 0 个未处置项。
- 所有修改C/C++按代码根 `.clang-format`检查，`git diff --check`无错误；新增源文件的
  CMake消费点与重新configure要求已交给workflow。

## 失败修复与交接

workflow回流实现缺陷时，必须持续执行以下根因修复循环：

```text
保存并展示首个真实失败
    ↓
按parser/infer/kernel/opcoder/quantizer/构建接线分类
    ↓
查references/troubleshooting.md与lessons.md
    ↓
从失败case反推数学语义、shape、dtype、地址和量化参数
    ↓
定位最小根因并修复源码
    ↓
重跑质量门禁、workflow stage3重建、stage4同case及回归矩阵
```

每次循环必须保存本轮 `RUN_ID`、首个真实 `stderr` 和归属阶段；创建新的 `RUN_ID`
后才允许重跑，禁止用历史日志或旧产物替代当前结论。每个根因最多重试 **2 次**；第二次仍失败时
必须输出 `FAILED` 和两轮证据并暂停，等待用户明确选择继续攻坚或列为覆盖缺口，不能继续盲试。
实现、模型/spec、工具链和固件接线必须分别回流到对应 owner，不能用删除能力或放宽测试掩盖失败。

FP32数值错误不能靠更换输入、删除case、放宽余弦或归咎环境处理；先用小Tensor逐元素
对比参考公式和Kernel中间值。INT8错误先核对scale/zero-point、累加位宽、乘法顺序、
饱和、per-tensor/per-channel和生成代码是否确实调用INT8 Kernel。

出现单次FAIL后不要询问用户“是否继续修复”。完整实现/工作流请求已经授权在既定算子
范围内完成根因分析、最小修复和重跑；只有需要扩展framework/dtype/芯片范围、破坏性
操作或缺少外部授权时才询问。

**同一能力连续2个有证据的方案失败时必须强制停下**：向用户呈报两个方案各自的
根因假设、修改、首错和对算证据，并提供“继续攻坚”或“经裁决列为覆盖缺口”两个
选项，等待用户决定。未经用户裁决不得盲试第三个方案、删除FAIL用例或缩小能力清单；
用户选择缩范围时，Host VERDICT必须保留 `ACK_REDUCED`，并在最终能力清单和文档中
明确该覆盖缺口。

任何“环境问题”“存量局限”“非本次引入”“不支持某形态”“覆盖缺口”等收缩范围的
措辞，必须在同一条消息中先给本轮命令、首错、控制用例或源码证据。没有证据时继续按
算子缺陷处理，不能用措辞提前结案。

结束时输出：

```text
IMPLEMENT_GATE=<PASS|FAIL>
implementation_unit=<name>
source_entries=<list>
changed_files=<list>
CODE_STYLE_SOURCE=<本 Skill 安装目录>/references/code-style.md（运行时必须展开为绝对路径）
CODE_STYLE_SOURCE_SHA256=<sha256>
CODE_STYLE_AUDIT=<PASS|FAIL>
capability_checklist=<absolute path>
opdir=<absolute path>
next_owner=hs-workflow-op-development
```

`IMPLEMENT_GATE=PASS` 只表示源码实现与静态质量门禁通过，不表示构建、host 精度、文档、烧录或板测已经通过。

完成措辞锁：只有真实门禁满足时才能写PASS/完成；缺少任一计划用例、编码前audit、
质量证据或修改文件映射时只能写FAIL/未完成，不能写“基本完成”“代码已就绪”等模糊
完成语义。leaf不因任务耗时、后台运行或用户暂时离开而提前提交最终答复。

## 资源索引

| 资源 | 何时读取 |
|---|---|
| `scripts/scan_op.sh` | step1 规格与七层扫描 |
| `scripts/gate_artifacts.py` | 记录编码前源码指纹，并在prepare/pre-source/pre-verify检查规划、初版文档、代码审查和验证前产物完整性 |
| `scripts/quick_check.sh` | step6 快速编译与结构预检 |
| `../hs-verify-op-host/scripts/operator_spec_template.py` | step3 prepare阶段计划版op_spec唯一模板（由workflow保证该跨Skill资源可用） |
| `../hs-verify-op-host/scripts/validate_op_spec.py` | step3 prepare阶段能力清单与计划case机械校验（由workflow保证该跨Skill资源可用） |
| `scripts/fetch_ref_impl.py` | 计算路径变化时获取上游参考 |
| `references/worked-example.md` | step2 前理解复用/新建范例 |
| `references/decision2-reuse-decision.md` | 复用裁决和 builtin 探针 |
| `references/implementation-guide.md` | step4 七层模板唯一权威 |
| `references/int8-coder-conventions.md` | INT8 kernel/opcoder |
| `references/code-quality-gate.md` | step5/step6 代码审查、code style 与安全门禁 |
| `references/code-style.md` | 随 Skill 分发的 65 个规则ID团队统一规范 |
| `references/spec-sources.md` | 规格来源和不可达回退 |
| `references/troubleshooting.md` | workflow 回流失败时 |
| `references/lessons.md` | 出现已知故障症状或想走捷径时 |

MindSpore Lite 工具包重建、构建新鲜度与工具链分诊资源归 `hs-workflow-op-development` stage3；本专项 Skill 不托管也不执行构建流程。
