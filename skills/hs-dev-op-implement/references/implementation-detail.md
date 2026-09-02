# 实现规划与源码细则

## 目录

- [安全红线](#安全红线)
- [step0-step3 规划](#step0冻结范围)
- [step4 源码](#step4编写或修复源码)

> 在 `hs-dev-op-implement` 执行对应模式时按需读取。入口保留模式、门禁和交接；本文件保留完整的规划与源码规则。

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

复用审查还必须单独核对**规格覆盖矩阵**：把 contract/checklist 中的每个输入形态组合
（dynamic、initializer、optional）、广播形态、索引/边界语义、折叠/重写路径和支持的
dtype 逐项映射到独立 case，以及生成模型中的真实节点/输入。不能用一个“代表用例”、
只填写 builder 参数或“以后补测试”推断其它形态；缺少映射就记为 `FIX_REQUIRED`。
若某形态不适用，必须写出 N/A 和可定位证据。数据生成器也必须能表达规格允许的标量、
单元素和边界值，不能隐含最小元素数。

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
<opdir>/docs/{op}-operator-design-doc.md
<opdir>/docs/{op}-operator-verify-doc.md
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
