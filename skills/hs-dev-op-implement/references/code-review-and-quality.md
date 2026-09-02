# 编码后审查与质量门禁

## 目录

- [编码后交叉审查](#step5编码后交叉代码审查强制)
- [实现质量门禁](#step6实现质量门禁)

> `mode=apply` 在源码修改后读取；审查和质量门禁不可合并跳过。

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
6. **规格覆盖与测试数据**：逐条对照 contract/checklist 的输入形态、广播、索引/边界、
   折叠/重写和 dtype 行，确认每行都指向独立且可运行的 case；确认 `make_inputs()` 或等价
   生成器按模型输入顺序返回全部输入，并能表达规格允许的标量、单元素、负值和边界数据。
   只看到 builder 参数、同形 case 或“以后补测试”的说明，均视为覆盖缺失并置
   `FIX_REQUIRED`。

审查结果写入 `<opdir>/docs/code-review.md`。除说明文字外，文件必须包含一个 fenced JSON
对象（或整个文件为 JSON），顶层至少有 `reviewed_files`、`registration_matrix`、
`branch_reachability`、`quantizer_ownership`、`folding_and_rewrite_cases`、
`semantic_coverage`、`findings` 和 `disposition`。五个矩阵必须是非空对象列表：注册矩阵逐项记录
`key/dtype/condition/callee/case_id/evidence_location/status`；分支矩阵记录 `branch/case_id/evidence_location/status`；量化归属记录
`capability/expected_owner/actual_owner/lookup_evidence/model_evidence/evidence_location/status`；折叠矩阵记录
`mode(blocked|allowed|N/A)/case_id/expected_node/evidence/evidence_location/status`；
`semantic_coverage` 使用 `scenario/case_id/expected_behavior/evidence_location/status`，
逐项列出 dynamic/initializer/optional、广播、索引/边界、折叠/重写和 dtype 场景（不适用时
用 N/A 加证据）。每个注册 dtype 和分支都必须
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
- 计划版 `op_spec.py`已经通过validator，每条 case 都有明确 `test_point`，且每条能力均映射到计划case；
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
