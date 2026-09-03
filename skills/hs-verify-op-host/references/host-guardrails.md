# Host guardrails

目录：

- [必守约束](#必守约束red-flags违反即作废)
- [前置检查](#前置检查)

进入对应阶段时读取本文件；固定 harness 和防伪规则不变。

## 必守约束（Red Flags：违反即作废）

以下红线**任何情况都不得越过**:

- **就地运行 bundled harness。** 不要手敲 `converter_lite` / `cmake` / `benchmark` 去"复现"流程,
  也不要把 `run_all_cases.py` / `*.sh` / `*.cfg` 拷进仓库改造。
- **harness(`run_all_cases.py` / `*.sh` / `*.cfg`)是不可变基础设施。** 验证某算子时**只允许新建/编辑
  `op_spec.py`**,绝不动 harness。harness 被所有算子共享,为让单个算子变绿而改它 = **污染全体 + 结论作废**。
  确属 harness 能力缺口(如多输入校准)时,这是一次**独立的 harness 维护**:必须带着明确维护意图、同步更新
  本 SKILL.md、**先跑 `tests/test_harness_core.py` 守住防伪结论不变量(改完仍须全绿)**、并在已有算子上回归
  ——而不是夹在某次算子验证里顺手改。
- **余弦相似度一律由 harness 在 benchmark 跑完后用 `cosine_similarity()` 在 Python 侧计算**,x86 与 riscv
  **同一函数、同一判据**。benchmark 只负责**打印输出张量**(`PrintTensorHandle`),**绝不由 benchmark 决定
  PASS/FAIL**(不传 calib 文件、不依赖其内置 `CompareOutputs`)。参考输出由 harness 用 onnxruntime /
  `tf.lite.Interpreter` 现算；仅当 ONNX Runtime 明确返回 `NOT_IMPLEMENTED` 时，harness 可对同一模型和输入使用 ONNX
  官方 `ReferenceEvaluator`，其他异常仍硬失败；ORT 成功的原生整数输出还要与官方 evaluator 做精确一致性审计，
  两者冲突时采用官方 ONNX 结果并打印留痕。spec 不提供 ground truth;禁止手填任何余弦数字或"预期张量"。
- **绝不把 `NaN`/`Inf` 余弦映射成通过值。** `cosine_similarity()` 对一切输入都有定义、永不返回 NaN:
  两边全零→`1.0`(都没产出=相符)、**恰好一边全零→`0.0`(真实失配=FAIL)**。任何 `nan→1.0` 之类的旁路
  都是在掩盖失败,一律禁止。NaN 进入结论 = 余弦没真算出来 = 要修的 bug,不是可以编造的 PASS。
- **不放宽阈值、不改参考来把红变绿。** fp32≥0.999、INT8≥0.99 是固定判据。完整 harness 会拒绝非默认 `--threshold-*`；自定义阈值只允许与 `--judge-case` 一起做单路径诊断，并打印 `VERDICT_NON_SIGNABLE=1`，不能据此生成最终结论。
- **报告与 `output/` 一律落在算子项目目录(约定 `$MSLITE_OP_OUTPUT/<op>`，缺省与 mindspore-lite 仓平级，HiSpark.AI 仓内即 `src/mslite-op-output/<op>`)。** harness 以 `--spec` 所在位置为锚
  (`<proj>/scripts/op_spec.py` → 输出写到 `<proj>`),**与当前工作目录无关**——所以 `--spec` 必传绝对路径
  (实证:重跑时漏 `cd` 曾把整轮输出写错位置白烧 10+ 分钟,锚定 `--spec` 后此错不再可能,但相对路径仍按 cwd 解析)。
  **op_spec.py 严禁放在 MindSpore Lite 源码/构建树内**(会把 `output/`、`*_test_results.xlsx`、`verify_summary.txt`
  灌进 submodule)。harness 已内置该目录守卫,触发即停。
- **某路径 `converter_lite` 失败是一条 FAIL 结论**,按其 `stderr.log` 如实上报(常因该算子未注册/不支持,
  或某属性/输入组合无法处理——实现算子支持是另一项独立工作)。**不得用"harness 限制""已就绪""非算子问题"
  等措辞掩盖未验证的路径**;没跑通就是没跑通。
- **多条互不相关的用例同时 converter 报错 / 全 FAIL / converter 一启动就崩 ≠ 单个算子缺陷,先疑构建环境。**
  失败面远超本算子改动可能影响的范围(多框架、多形态、连之前 PASS 的用例一起塌)时,八成是工具链包陈旧或
  `mindspore` 子模块被构建脚本 `--remote` 推进到别的 commit(converter 行为整体漂移)。处置:回
  hs-workflow-op-development stage3 核对**构建新鲜度**与**子模块 SHA 未漂移**（`build_mslite.sh` 的 `[SUBMOD-LOCK]` 守卫），
  **不要逐用例去改算子代码,更不要 `git checkout` 子模块/`git stash` 反复试**——那只会越改越乱。
- **轻量Python运行包缺失时先自动修复，不得直接停下。** 使用当前Host任务的同一Python解释器，
  在虚拟环境或用户范围安装并验证后继续；ONNX必须同时具备`onnx`和`onnxruntime`。只有管理员
  权限、系统级修改、卸载/降级冲突或大型工具链等超出自动修复边界时才询问用户。真正的编译
  工具链缺失且无法安全自动补齐时如实报告，不伪造PASS、不模拟运行。
- **harness 内部 step1→step5 强制串行。** 某步失败即该用例 FAIL,不跳步、不臆断通过。
- **输入必须确定性(禁随机)**,否则结果不可复现。
- **INT8 真实性由 harness 机械断言,不靠"flat 1.0"目测。** "量化未生效、算子回退 fp32"的判据**不是余弦值**——离散输出算子(hardmax/argmax/select 等,输出 one-hot/索引)即便量化真生效,int8 与 fp32 结果也恒等、余弦本就 `1.000000`,拿 flat 1.0 当 FAIL 信号会把这类合法 PASS 误杀。真正的判据是**生成的 MCU 代码里有没有真的调用该算子的 int8 kernel**:harness 在每条 `riscv_int8` 路径跑完后 grep 生成的 `net*.c`,命中 int8 kernel 符号才算真,缺席判 `INT8_NOT_GENUINE` FAIL(量化旁路 → 发了 fp32 opcoder)。符号默认 `f"{OP_NAME}Int8"`(nnacl 惯例);激活子类型等 int8 符号异名的算子,在 `op_spec.py` 声明 `INT8_KERNEL_SYMBOL`(如 HardSwish→`HSwishInt8`)。**一个算子若按输入形态发射多个 int8 计算函数(如等长核 + 广播核),声明为列表** `INT8_KERNEL_SYMBOL=["BroadcastWhereInt8", "WhereWithTripleInputsInt8"]`——某用例只要命中列表中**任一**符号即算真(闸门只判"是否回退 fp32";发对了哪个 int8 核由余弦负责)。漏列某变体会让发射该变体的用例被误判 `INT8_NOT_GENUINE`。**仅**量化 INT8 豁免算子(原生整型/索引/非 float 输出)可设 `INT8_KERNEL_SYMBOL=""` 关闭该检查,绝不用它掩盖真实回退。**PASS 行备注会区分 `int8_genuine=yes` 与 `int8_exempt=yes`**：前者证明生成代码确实调用 int8 kernel；后者只说明本算子没有 fp32→int8 量化 kernel 需要证明。
- **不得靠"在算子源码里禁用 int8/量化通路"来凑绿。** 把算子移出 `support_int8_ops_`、注释 int8 kernel/coder 注册再跑,`riscv_int8` 路只是退化成 fp32 回退——这不是 INT8 PASS,是**未验证**。要验的恰是带量化的真实通路;禁用它再签收 = 结论作废。**这种回退现在被 harness 的 `INT8_NOT_GENUINE` 闸门机械拦截**(生成代码里 int8 kernel 符号缺席即判 FAIL,见下条);用 `INT8_KERNEL_SYMBOL=""` 关检查再签收,与删 FAIL 用例换绿同属作废行为。若量化通路本身崩溃(见「运行」里的「长任务执行与崩溃检测」),那是要修的缺陷,不是可以绕过的理由。
- **结论只认 harness 的输出。** 向用户汇报必须照抄 harness 末尾的 `VERDICT` 行 / 退出码 / `verify_summary.txt` /
  Excel,**不得凭记忆复述、不得美化、不得自行宣布通过**。harness 退出码即结论:非零=有 FAIL。
- **`op_spec.py` 任何改动后必须重跑 harness。** 不得复用旧结论或旧 Excel——它们不反映最新代码。
- **每个算子的用例按其自身规格新写，禁止复用其它算子的 `op_spec.py`。** 即便新算子在实现上映射到已有 PrimitiveType，其输入个数 / 广播 / 量化语义可能不同，套用别的算子用例会漏测。
- **项目目录里已存在的 `op_spec.py` 必须先与本次"框架 × 算子"裁决对账，禁止照旧复用。** 它可能是上一次（甚至失败的）运行残留的，带着过时或错误的内容。跑之前逐项核对并清理，对账不通过就改到通过再跑——绝不在陈旧/越界的 spec 上出结论：
  - **删除本次范围外框架的全部 `*_TEST_CASES` 与 `build_*_model` 分支。** 某框架经「用例设计原则」中的存在性查证确认为"无此算子"、或不在本次目标框架内，其 cases 与 builder 一律移除——留着就是下次跑 `--framework all` 时的雷（会拿不存在的算子去建模型、或顶替成别的算子）。
  - **docstring / 注释里的存在性与语义断言必须与查证结果一致**，过时或错误的说法（声称某框架有此算子、写错广播规则或映射关系）一律删除，不得留存误导后续。
  - **一个 `op_spec.py` 只针对一个算子的一个 builtin**；`build_*_model` 不得按形状等条件**静默切换到另一个 builtin**（否则本算子的用例会被悄悄测成别的算子，结论无效）。
  - **覆盖也要对账**：现有用例若缺本节要求的强制用例（尤其多数据输入算子的「量级悬殊」用例），同样算不通过。
  - **对账/覆盖任一不通过 → 整体重写该 `op_spec.py`，不要在已有文件上打补丁**（打补丁极易残留过时断言/用例）。用户调用若明确写了「从头设计用例」「重新设计用例」，则**无条件整体重写**，不复用任何已有内容。
  - **对账方向是单向的：以本次 implement step3 能力清单为准改 spec，不得反向改写清单去匹配存量 spec。** 存量用例与清单某行的形状/轴不一致时，改 spec 或新增用例；汇报回填时把清单行"顺手"换成存量用例的实测值 = 静默缩减覆盖（实证：计划的「大 shape × 中间轴」两行被改写成存量的 axis=-1 形状，该路径实际无用例却显示全覆盖）。确需调整某行能力，标「计划变更（原 X → 现 Y，理由）」呈现给用户裁决。
- **「还没跑」不是删除用例的豁免。** 以"转换器无法生成该形态""内核不支持该模式""估计测不了"为由在**未实跑**的情况下删除规格形态用例，与删除 FAIL 用例同属作废行为——这类断言恰恰只能由实跑产生（converter 可能有形态规范化 pass，"不支持"的直觉常是错的）。合法处置只有三种，全部要求本会话日志证据：①实跑通过 → 保留；②builder 确实无法以**本 builtin** 产出该形态（如 TF 高层 API 必然 lower 成另一个 builtin）→ 用例保留为占位、在汇报中如实列为「覆盖缺口」结论，**不得**换用另一 builtin 顶替（那是偷测别的算子）；③converter/编译拒绝 → 按「失败排查」如实上报 FAIL/不支持结论。**任何"无法生成/不支持"的说法不得写进 docstring 或注释当作事实，除非附有本次实跑的日志依据。**
- **能力清单是单向真值，不得反向改写去匹配存量用例。** `hs-dev-op-implement` step3 产出的能力验收清单冻结为 `<proj>/scripts/capability_checklist.json`，harness 据此机械核对覆盖：开跑前查每条能力的 `covered_by` 引用存在且非空（且声明了 `match` 时用例 params 须匹配），结束后按本轮通过用例算覆盖，未覆盖的能力使 VERDICT 非绿。**对账方向单向——以清单为准改 spec / 补用例，绝不反向删改能力行去贴合现有用例**（实证：弱会话曾把「大 shape×中间轴」能力行回填时悄悄换成存量 axis=-1 形状，该路径实际无用例却显示全覆盖）。确需调整某能力行须标「计划变更（原 X→现 Y，理由）」呈给用户裁决，不得静默改 JSON。
- **FAIL 用例不得删除、不得调弱换绿。** harness 对此有机械闸门：本轮用例集比上轮 `verify_summary.txt` 缩水即拒跑（`CASES_REDUCED`），`OP_VERIFY_ACK_REDUCED=1` 仅在**用户明确裁决**将该形态列为覆盖缺口后使用，且豁免会记入 VERDICT——靠删 summary、改算子名等方式绕过闸门与伪造数据同级。
  - **`CASES_REDUCED` 的基线就是 `verify_summary.txt`——所以严禁把它当"残留"删除。** harness 每轮已自动清空 `output/`，**无需任何手动清理**；尤其**不要** `rm verify_summary.txt`。删掉它会抹掉上一轮用例基线，使闸门无法发现用例被减少。要换 spec 直接改 `op_spec.py` 重跑即可，基线由 harness 自己维护。出现 FAIL 后只有两个合法动作：**修实现代码**，或**证明用例本身设计错误**。把 FAIL 归因为"用例设计问题"必须给出**生成代码/日志级证据**（如生成 `.c` 里的量化参数失配、塌缩的输出值），不得只凭"量化精度固有限制""退化输入无意义"一类说辞。任何用例修改（值域、形状、条件模式）必须在汇报中**列出修改前后对照与理由**，且修改后的严酷度（量级跨度、形状规模、边界覆盖）**不得低于原用例**；"把用例调到刚好能过"与放宽阈值同属作废行为。
- **只为该算子真实存在的框架建用例，且禁止用等价算子顶替。** 先按「用例设计原则」里的确定性命令查证每个框架是否定义该算子（ONNX 页面 HTTP 码 / TFLite builtin 枚举）；某框架查证为"无"就不写该框架用例、不测该框架——**不得为了让模型建得起来，把 `build_*_model` 改成另一个"等价算子"**。那样测的是别的算子，结论无效。
- **序关系类算子（argmax/hardmax/topk/sort 等输出由"谁更大"决定）的 int8 用例必须用模板的 `make_distinct_axis_inputs()` 造数。** 普通 linspace 在大张量下相邻值间距 < 量化桶宽（全幅/254），多个浮点不同的值落进同一 int8 桶，int8 取到的极值位置就偏离 fp32 参考——FAIL 但 kernel 没错（实证：Hardmax 大 4D 两次 FAIL 烧掉一轮验证）。这是「证明用例本身设计错误」的已知合法模式之一，证据即沿轴相邻值间距与量化步长的对比计算。
- **多数据输入/搬运·选择类算子必须含一条「输出分布 ≠ 输入分布」的判别用例（抓漏重量化/字节拷贝）。** 设计：各数据输入**同量级**、正负混合（如都在 `[-6, 6]`），条件/选择**只命中单一符号侧**，使输出值域单边、其 scale/zp 与输入明显不同。漏重量化会把输入域 qparams 原样带进输出形成仿射失真，cosine 可测（实测：字节拷贝 ~0.95 FAIL，正确重量化 ≥0.9999 PASS）。**各输入之间不要拉开数量级**（量化器按值域并集分配共享输入 scale，量级悬殊的用例无判别力，不要设）。
