---
name: hs-verify-op-host
description: >-
  Design, run, and debug PC/WSL host-side precision tests for an existing MindSpore Lite Micro operator. Owns op_spec.py, deterministic minimal models and inputs, reference outputs, fixed-harness execution, capability coverage, x86 execution of x86/RISC-V code-generation paths, and Host VERDICT reporting for ONNX/TFLite FP32 and INT8. Use when the user explicitly names hs-verify-op-host, asks only to write operator tests or verify host accuracy, or hs-workflow-op-development routes a test-spec/harness defect here. Generic “适配/新增/支持算子” requests belong to hs-workflow-op-development; this skill does not implement operator source, build firmware, flash, or perform real-board verification.
---

# 算子 Host 正确性验证

MSLite 算子在 PC/WSL 上的正确性与精度验证。验证由 `scripts/` 下一套**固定测试执行器（下文简称 harness）**（`run_all_cases.py` + 驱动脚本 + cfg）
完成,它把模型生成→转换→编译→推理→比对→Excel 全流程编排为**不可改的代码**。每次运行必须由入口生成唯一
`RUN_ID` 并写入本轮状态和日志首行；后台调用和 `wait_verify.sh` 必须携带该 ID，终态明确记录
`SUCCESS` 或 `FAILED`，没有匹配 RUN_ID 的旧日志不能作为本轮结论。每个算子你**只写一个
`op_spec.py`**(用例集 + 模型构建),其余一律复用 harness。

支持 **ONNX 与 TFLite 两条独立路径**,每条各跑 x86 fp32 / riscv fp32 / riscv INT8 三个代码生成目标；当前 benchmark 最终均在 x86 Host 执行，`riscv` 不表示真板运行。两框架用例
**各自独立设计、各自出一份 Excel**(`<op>_onnx_test_results.xlsx` / `<op>_tflite_test_results.xlsx`)——同一算子
在 ONNX/TFLite 的属性、布局(NCHW vs NHWC)、量化约束可能不同,不可共用用例。

## 使用方式总览

这个 skill 做的是**测试设计与 Host 验证**,不是实现算子。它要求先写/对账 `op_spec.py`,再由固定 harness 生成模型、运行
MindSpore Lite、比对真实输出,最后只按 harness 的 `VERDICT`、`HARNESS_EXIT`、Excel 和 `verify_summary.txt`
汇报结论。

对用户展示当前进度时,使用 todo 样式,不要只说“正在第几步”：

```markdown
- [ ] step0 准备工具链与项目目录
- [ ] step1 standalone编写 / workflow只读对账 `<proj>/scripts/op_spec.py`
- [ ] step2 运行固定 harness
- [ ] step3 读取 `VERDICT` / `HARNESS_EXIT` / Excel / `verify_summary.txt`
- [ ] step4 排查失败或签收结论
```

推进时只更新状态,并附一句当前证据。例如：

```markdown
- [x] step0 准备工具链与项目目录
- [x] step1 standalone编写 / workflow只读对账 `<proj>/scripts/op_spec.py`
- [ ] step2 运行固定 harness - 正在等 `wait_verify.sh` 返回 VERDICT
- [ ] step3 读取 `VERDICT` / `HARNESS_EXIT` / Excel / `verify_summary.txt`
- [ ] step4 排查失败或签收结论
```

## 流程地图

| 阶段 | 做什么 | 成功证据 |
|---|---|---|
| step0 准备工具链与项目目录 | 确认 `MSLITE_PKG` 指向已解压构建产物,算子项目位于 `$MSLITE_OP_OUTPUT/<op>` | `converter_lite` 可执行,`op_spec.py` 不在 MindSpore Lite 源码/构建树内 |
| step1 准备 spec | standalone任务按规格编写`<proj>/scripts/op_spec.py`；完整workflow只读对账stage1冻结文件并运行pre-verify两道机械门禁 | `OP_NAME`、两套`*_TEST_CASES`、builder、`make_inputs()`齐全且门禁PASS |
| step2 运行 harness | 用 `run_all_cases.py --spec <abs path>` 执行 | 日志出现 `VERDICT` 和紧随其后的 `HARNESS_EXIT=N` |
| step3 读取结果 | 只读取 harness 产物,不要自行判定 | `verify_summary.txt`、每框架 Excel、`output/<framework>/tc*/output/<path>/stderr.log` |
| step4 排查或签收 | 非零退出按失败类型排查;全绿才签收 | 向用户照抄 VERDICT/退出码,列出 FAIL 证据或 PASS 报告 |

### Harness 内部 step1-step5

`run_all_cases.py` 对每条用例强制串行执行内部 step1-step5。这里的 step1-step5 是 harness 内部路径,
不要和上面的用户可见 step0-step4 混用：

| 内部步骤 | harness 做什么 |
|---|---|
| step1 | 构建模型、生成确定性输入、用 onnxruntime（CPU provider 明确 `NOT_IMPLEMENTED` 时回退 ONNX 官方 `ReferenceEvaluator`）/ tf.lite 计算参考输出 |
| step2 | 调 `converter_lite` 生成 micro C 工程 |
| step3 | `cmake` + `make` benchmark |
| step4 | 写入输入 `.bin` |
| step5 | 跑 benchmark 打印输出张量,再由 Python 统一计算余弦 |

### workflow 模式的 pre-verify 门禁

当`<proj>`来自完整算子workflow时，读取stage1已冻结的`op_spec.py`并与capability checklist
只读对账；启动harness前必须执行：

```bash
python3 <hs-dev-op-implement skill root>/scripts/gate_artifacts.py \
  --opdir <absolute proj> --op <Op> --stage pre-verify --framework <framework>
python3 <hs-verify-op-host skill root>/scripts/validate_op_spec.py <absolute proj>
```

每个激活 framework 都要得到 `ARTIFACT_GATE=PASS`，且 validator 退出码为 0。前者确认实现合同、已有能力 review、能力清单和测试 spec 没有断链；后者在长转换前拦截动态输入数量、initializer 声明、capability case ID 及 ONNX `auto_pad/pads` 冲突。独立 Host 任务没有实现工作区时不伪造这些产物，但仍执行 harness 内建的 spec、目标算子身份和能力覆盖门禁。

harness 只要求所选 framework 的模型 builder：`--framework onnx` 必须定义
`build_onnx_model`，但不得强制不存在的 TFLite 路径提供 `build_tflite_model`；TFLite 同理。
`--framework all` 才同时要求两套 builder。公共的算子名、两套 case 容器和 `make_inputs()`
仍是固定 spec 契约，范围外框架的 case 容器应为空。

完整workflow的Host阶段不得直接新增、删除或改写case。若对账发现模型构造、输入/GT、case或
覆盖映射必须变化，返回顶层workflow的stage1，重新prepare、生成初版文档、通过pre-source并
重跑apply/build；不能在Host阶段改完`op_spec.py`后继续使用旧facts哈希。

`ARTIFACT_GATE=PASS` 还要求实现工作区存在编码后 `docs/code-review.md`。该审查必须覆盖注册
键与 dtype 分支可达性、量化器列表归属、常量折叠/节点重写双路径和生成代码调用；没有审查
文件或存在未处置 `FIX_REQUIRED` 时，禁止启动长转换。这样可以在 Host 之前拦截“注册了
uint8/int8 但 coder 未分支”“永不执行死代码”“量化项落错白名单”“Fill 被折叠后误报
原算子已执行”等结构性问题。

## 必守约束(Red Flags — 违反即作废)

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
- **不放宽阈值、不改参考来把红变绿。** fp32≥0.999、INT8≥0.99 是固定判据。完整 harness 机械拒绝非默认 `--threshold-*`；自定义阈值只允许与 `--judge-case` 一起做单路径诊断，并打印 `VERDICT_NON_SIGNABLE=1`，绝不生成结论性签收。
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

## 前置检查

需要一套**已构建**的 MindSpore Lite 工具链(含 `converter_lite` 与 benchmark 源码)。用环境变量
`MSLITE_PKG` 指向它;harness 也会从当前目录向上自动定位作为兜底:

本Host harness及当前`linux-x64` converter必须在Linux/WSL执行，不能直接用Windows Python
启动。HiSpark.AI代码可以位于Windows磁盘，但传给harness、converter和CMake的路径必须先
转换成WSL原生形式（例如某个 Windows 工作区对应 `/mnt/<drive>/<工作区>`）；代码位于 WSL
原生目录时直接使用`/home/...`。`MSLITE_PKG`、`--spec`及输出目录必须全部属于同一个
Linux/WSL路径空间，禁止在一条命令里混用Windows与WSL绝对路径。

```bash
export MSLITE_PKG=<mindspore-lite 构建产物根目录>
test -x "$MSLITE_PKG/tools/converter/converter/converter_lite" && echo OK || echo "toolchain NOT built"
```

**每次 Bash 工具调用都是新 shell，`export` 不跨调用存活**——所有用到 `MSLITE_PKG` 的命令必须与 `export MSLITE_PKG=...` 写在同一条命令里（「运行」里的"整块复制执行"正是为此；拆开执行时上一条的 export 已失效，`test -x "$MSLITE_PKG/..."` 必然 MISSING）。

**`MSLITE_PKG` 必须指向构建产物顶层（`output/mindspore-lite-<ver>-linux-x64/`）——即解压后的 tar.gz 包。禁止指向原始 `build/` 目录。** 后者缺少 `include/c_api/`、`runtime/include/` 等头文件，共享库分散在多处，会导致 `converter_lite` 找不到 `.so` 或 `make` 缺头文件。用错目录时最常见症状是 `error while loading shared libraries` / `c_api/model_c.h: No such file`——遇到此症状先检查 `MSLITE_PKG` 是否为解压包。

**解压包必须不早于最近一次构建——harness 自动校验并拒绝陈旧包。** 重新编译只刷新 tar.gz，不会自动重新解压；若忘记重解压，验证会运行陈旧的 `converter_lite`，结论不能反映当前代码。harness 发现旁边的 tar.gz 比解压包新即报错停止——处置就是重新解压（`build_mslite.sh` 构建成功后自动完成）。`OP_VERIFY_ALLOW_STALE=1` 只允许用于显式兼容性对比，不得用于结论性签收。`verify_summary.txt` 头部记录本轮 `converter_lite` 的构建时间，便于追溯结论对应哪次构建。

未构建时**停止并告知用户先构建工具链**,不要继续、不要伪造结果。

## 资源边界与 Bundled Harness（就地运行，不要改、不要拷）

Skill 包内固定资源包括 `scripts/run_all_cases.py`、`scripts/*.sh`、`scripts/*.cfg`、
`scripts/operator_spec_template.py`、`scripts/validate_op_spec.py`、`scripts/wait_verify.sh`、
`scripts/judge.sh` 和 `tests/`。当前算子项目的运行时产物包括 `<opdir>/scripts/op_spec.py`、
`<opdir>/scripts/capability_checklist.json`、`<opdir>/docs/*.md`、`<opdir>/output/`、
`verify_summary.txt` 以及 `/tmp/op_verify_<RUN_ID>.log` 和对应 `.pid`；这些文件不属于 Skill 包。
静态资源检查不得要求 `skills/hs-verify-op-host/scripts/op_spec.py` 存在。

| 文件 | 作用 |
|---|---|
| `scripts/run_all_cases.py` | **唯一入口**,算子无关。编排每用例内部 step1-step5、解析 benchmark 打印的输出张量、**在 Python 侧统一算余弦**、写 Excel。每次运行携带唯一 `RUN_ID`，旧日志不能冒充本轮结论。另自带防假结论闸门：按 spec 的目标节点校验源模型，并按 `<proj>/scripts/capability_checklist.json` 校验能力 covered_by 引用；清单还必须声明 `folding_and_rewrite` 矩阵，分别覆盖阻止折叠以证明目标 Kernel 真执行、允许重写以证明整图语义，或给出 N/A 证据。转换后必须保留 target/rewrite identity evidence，不能只凭原始模型节点判定 |
| `scripts/validate_op_spec.py` | Host 拥有的长测试前机械门禁：检查动态输入、initializer、capability case ID 和 ONNX 属性冲突 |
| `scripts/wait_verify.sh` | 后台启动后的**唯一等待方式**:内部轮询日志到 VERDICT 出现/进程退出/到时,免 sleep 算术 |
| `scripts/judge.sh` | **手动判定辅助**(不改驱动、不复制公式):`judge.sh <case_dir> [path_key]` 转发到 `run_all_cases.py --judge-case`,读取最新 `output/<path>/stdout.log`,刷新 `output/<path>/output*.npy`,再用 harness 的 `cosine_similarity()` + `PATH_META` 对比稳定的 `gt/output*.npy` 打印 PASS/FAIL。`output/<path>/_run.sh` 手动重跑后也走同一入口刷新判定;**权威结论仍以 run_all_cases.py 的 VERDICT 为准** |
| `scripts/onnx_x86.sh` / `tflite_x86.sh` | x86:转换(NCHW/NHWC)+ 编译 + benchmark **仅打印输出张量**(不传 calib、不做内置比对) |
| `scripts/onnx_riscv.sh` / `tflite_riscv.sh` | riscv:转换 + `sed` 把工具链改写为 x86 host 静态库 + 编译运行(无需真板) + benchmark 仅打印输出张量 |
| `scripts/micro_x86.cfg` / `micro_riscv.cfg` / `micro_riscv_quant.cfg` | 三条路径的 cfg 模板(quant 的 `{CALIBRATE_PATH}` 由 harness 运行时按"每输入一个 `tensor:dir`"填,支持多输入) |
| `scripts/operator_spec_template.py` | **复制到当前算子项目并填写的唯一模板**；复制后的 `<opdir>/scripts/op_spec.py` 是项目运行时文件 |
| `tests/test_harness_core.py` | **harness 自检**(防伪结论的不变量保护网):按真实签名对 `cosine_similarity`(全零/一边零/永不 NaN 三个语义)、三道闸门(`assert_int8_genuine` / `check_case_regression` / 能力清单 `validate_checklist_refs`+`report_capability_coverage`)、`parse_benchmark_outputs`、`_err_msg`、`make_cfg` 做单元断言。不依赖 MSLite/硬件,秒级跑完。**任何对 harness 的维护性改动后必须先跑它**(`python3 -m pytest tests/ -v`),绿了才动真验证——它守的正是"改 harness 时别把防红变绿的能力悄悄改没了" |

## 唯一要写的文件:`op_spec.py`

把 `operator_spec_template.py` 拷到你的算子项目目录(约定 `$MSLITE_OP_OUTPUT/<op>/`，缺省与 mindspore-lite 仓平级，HiSpark.AI 仓内即 `src/mslite-op-output/<op>/`)下的
`<proj>/scripts/op_spec.py`,填入用例与模型构建。harness 校验的必需定义:

```python
OP_NAME            : str
ONNX_TEST_CASES    : list[dict]   # 每条 {"id","desc","params":{...}}，按 ONNX 规格(NCHW)
TFLITE_TEST_CASES  : list[dict]   # 独立按 TFLite 规格(NHWC)设计
build_onnx_model(tc, model_path)     # 用 onnx.helper 建图并保存 .onnx
build_tflite_model(tc, model_path)   # 用 tf.Module + experimental_new_converter=False 保存 .tflite
make_inputs(tc, framework) -> list[np.ndarray]   # 模型输入顺序、确定性
# 可选: PARAM_COLUMNS = [...]   tc["params"] 里要展示到 Excel 的键
# ONNX_TEST_CASES 非空时必填: ONNX_TARGET_OP_TYPE = "<确切 op_type>"
# TFLITE_TEST_CASES 非空时必填: TFLITE_TARGET_BUILTIN = <存在性查证命中的 builtin 编号>
# harness 检查每个生成的源模型；目标节点/builtin 缺席的用例直接 FAIL(OP_MISMATCH)，
# 不会静默测成 API 优化后的其它算子。缺少对应声明时整轮拒跑。
# 可选: INT8_KERNEL_SYMBOL = ""  # 仅量化 INT8 豁免算子使用；PASS 备注写 int8_exempt=yes。
# 可选: INITIALIZER_INPUTS = {"onnx": ["w", "x_zero_point"]}
#   模型 graph input 中由 initializer/常量提供、不由 make_inputs() 返回的输入名。
#   harness 会校验 make_inputs 数组数 == 动态输入数，防 zip 静默丢输入。
```

harness 自动:用 spec 的模型现算参考输出、生成 calib、存 `input.bin`、跑三条路径、解析真实余弦、写表。
spec **只描述"算什么",不碰"结果对不对"**。

### 能力清单冻结件 `<proj>/scripts/capability_checklist.json`（完整 workflow 必需，implement step3 落盘）

把 `hs-dev-op-implement` step3 的「能力验收清单」逐行落成 JSON，harness 据此机械核对覆盖（详见「必守约束」对应红线）。结构：

```json
{
  "op": "Hardmax",
  "framework_scope": ["onnx"],
  "capabilities": [
    {"id": "c1", "desc": "2D 小张量 axis=0 (fp32+int8)", "covered_by": [2], "match": {"axis": 0}},
    {"id": "c5", "desc": "4D 大张量 axis=-1 (序关系 distinct)", "covered_by": [5]}
  ]
}
```

- `covered_by`：承载该能力的 `*_TEST_CASES` 用例 id 列表，**必须非空且引用存在的用例**（开跑前校验，dangling/空即拒跑）。
- `match`：params 谓词；声明后该能力的 covered_by 用例中至少一条 params 须满足所有键值，防 covered_by 指错用例冒充覆盖。非平凡能力（dtype、shape/rank、axis、stride、pad、dilation、group、可选输入、broadcast 形态）应写出关键 match；空 match 只用于无法机械表达的总体能力。
- 结束后每条能力按本轮**通过**用例核对：covered_by 无一通过 = 未覆盖，VERDICT 标 `[UNCOVERED]` 且非绿。
- 缺该文件时 harness 仅告警、不阻塞（向后兼容），但 VERDICT 不含能力覆盖留痕——完成声明就缺一项机械证据。

### 用例设计原则(`op_spec.py` 里两套独立设计)

1. **先查证算子名与属性(写用例前,别凭记忆)**:
   - **存在性查证——决定哪个框架该写用例、`build_*_model` 用什么名字(确定性命令,别凭记忆):**
     - ONNX:`curl -sL -o /dev/null -w '%{http_code}\n' https://onnx.com.cn/onnx/operators/onnx__<OpName>.html` —— `200`=有、`404`=无。
     - TFLite:`curl -sL https://raw.githubusercontent.com/tensorflow/tensorflow/master/tensorflow/lite/builtin_ops.h | grep -nE 'kTfLiteBuiltin<OpName>\s*='` —— 命中(含 builtin 编号)=有、空=无。
      **只为"有"的框架写 `*_TEST_CASES`;`build_*_model` 里 `helper.make_node` / TFLite op 用的名字必须是查证命中的确切框架名。** 某框架"无" → 该框架 `*_TEST_CASES = []`,对应 `build_*_model` **保留为占位**(函数体直接 `raise NotImplementedError("<框架> has no <Op>")`——harness 校验符号存在,删函数会报错);**绝不改用"等价算子"顶替来让模型建得起来**(那测的是别的算子,结论无效)。
   - **目标算子身份是前置硬门禁**：ONNX 用例声明 `ONNX_TARGET_OP_TYPE`，TFLite 用例声明 `TFLITE_TARGET_BUILTIN`。harness 在参考运行和 converter 之前逐 case 解包源模型；如果 Fill 等节点被模型 API 常量折叠、lower 或规范化为 BroadcastTo 等别的节点，立即 `OP_MISMATCH`，先修 builder/shape/动态输入设计，不进入精度比较。不要把替代节点的 PASS 当成目标算子 PASS。
   - **converter运行环境和参数按当前包探测**：harness 不依赖用户在前一个shell中的`export`。它先在本轮`MSLITE_PKG`内定位`libmindspore_converter.so`，把真实目录置于当前子进程`LD_LIBRARY_PATH`最前，过滤明显属于其他MSLite包的旧目录，再以相同环境运行真实转换。随后对 `$MSLITE_PKG/tools/converter/converter/converter_lite --help` 只探测一次并缓存。只有 help 明确声明 `--encryption` 时才传 `--encryption=false`；help 成功但不支持时省略。自动配置成功就继续，不向用户转交手工设置；包内缺库时输出`CONVERTER_RUNTIME_GATE=FAIL`，help非零、超时或无法启动时输出 `CONVERTER_CAPABILITY_GATE=FAIL` 并停止，不得猜参数或把环境失败归到算子。每条 driver 日志记录 converter 绝对路径、动态库目录、help 返回码和最终选择，所有驱动不得再硬编码版本专属参数。
   - **模型输入契约**：`make_inputs()` 返回的数组数必须等于模型动态输入数。ONNX 权重/zero-point 等若同时作为 graph input 与 initializer 存在,必须在 `INITIALIZER_INPUTS` 显式列名；否则 harness 会在 reference 前拒跑。不要依赖 Python `zip(input_names, inputs)` 静默截断,那会让测试少喂输入却看似通过。
   - **原生整型/索引算子**：可声明 `INT8_KERNEL_SYMBOL=""` 表示量化 INT8 genuine 检查不适用,但仍要按规格覆盖每个原生 dtype（如 int8 与 uint8 分开用例）,并在能力清单用 `match` 锁定 dtype。
   - **属性按规格枚举**:ONNX `https://onnx.com.cn/onnx/operators/onnx__<OpName>.html`;TFLite `https://tensorflow.google.cn/mlir/tfl_ops`、`.../api_docs/python/tf`、`.../lite/performance/quantization_spec`(属性/量化/布局与 ONNX 可能不同,不要照搬;WebFetch 不可达回退 `curl -sL <url> | head -300`)。参考输出由 harness 用真实 runtime 现算,故属性**取值**的正确性自校验——你的风险是**漏掉属性组合**和**用了不存在的属性名**,不是属性数学算错。列全属性,每个有意义组合各一条用例。
   - **目标 builtin 实证(TFLite,builder 写完必做一次)**:转换器会按输入形状对同一上层算子**择优/规范化** builtin(实证:无广播的 `SelectV2` 调用被降成 `SELECT`,真广播形状才发 `SELECT_V2`)——**builder 调了哪个 raw_op 不等于模型里是哪个 builtin**。每类形状形态各构建一个最小模型,解包核对 operator code 恰为目标 builtin(编号用存在性查证命中的值):
     ```bash
     python3 -c "from tensorflow.lite.python import schema_py_generated as s; \
     m=s.Model.GetRootAsModel(open('<model.tflite>','rb').read(),0); \
     print([max(m.OperatorCodes(i).BuiltinCode(),m.OperatorCodes(i).DeprecatedBuiltinCode()) for i in range(m.OperatorCodesLength())])"
     ```
     命中别的 builtin = 该形状的用例在**测别的算子**:处置是**调形状**让目标 builtin 出现(典型:广播版算子的用例必须全部用真广播形状,同形用例会被规范化成非广播版),而不是接受错位、也不是换算子名。核对结果(每形态一行:形状→builtin 编号)写进 docstring 当作证据。**并把查证命中的编号声明为 spec 的 `TFLITE_TARGET_BUILTIN`**——此后 harness 每轮对每个用例自动解包复核,目标 builtin 缺席的用例判 `OP_MISMATCH` FAIL。手工实证负责"设计形状时找到能逼出目标 builtin 的形态",harness 断言负责"以后每一轮都不漂移",两者不可互替。
2. **每个框架各 10–20 条**,覆盖:

| 维度 | 覆盖范围 |
|------|---------|
| 属性(attribute)边界 | 最小/最大/默认/负值 |
| 输入 shape | 1D / 2D / 小 4D(如 `[1,4,8,8]`) / 大 4D(如 `[1,32,64,64]`) / batch>1(如 `[4,8]`) |
| 输入值域(sign domain) | **全正数**(如 `[0.1, 6.0]`) / **全负数**(如 `[-6.0, -0.1]`) / **正负混合**(`[-6.0, 6.0]`，默认) / **全零** / **小量级**(如 `[-1e-3, 1e-3]`，下限见下方「打印分辨率」) |
| 算子敏感区间 | 由算子特性决定：如 HardSwish 的 `[-3, 3]` 非线性段、ReLU 的 `x<0` 截止区、Softmax 的相对大小关系、Tanh/Sigmoid 的饱和区。至少为每个敏感区间各设一条用例，值落在该区间内 |
| 数值形态 | 递增(`linspace`) / 全相同 / 边界极值(`±1e4`) |
| 数据类型 | float32、int32/int64(MSLite 内部 int64→int32,indices 存 `np.int32`) |
| **多输入 / 广播** | 多输入算子每输入独立 shape、独立 dtype(`make_inputs` 返回全部输入;非 float 输入如 bool 掩码/int 索引保持原 dtype、不做量化值域填充);广播算子**按规格**覆盖同形 + 标量(某输入=`[1]`)+ 文档支持的广播形态,不设算子会拒绝的形态。**全向广播算子还必须各设一条「中间维广播」**(如 `[2,1,4]`×`[2,3,4]`——`i%num` 式近似索引只对最外维广播碰巧正确,此形态专抓它)**与「混合形态」**(一个输入标量 + 另一输入非平凡广播同现——"任一输入是标量就走快路"式弱守卫的盲区);只有同形/标量用例全过证明不了这两类实现错误不存在。在 builder 里加 per-input 形参只是脚手架——**不写出对应的广播用例行就等于没覆盖**(模板文件末尾有通用范式)。 |
| **规格列明的输入形态(强制逐条覆盖)** | 把规格文档里描述输入间 shape/rank 关系的**每一句**翻译成至少一条用例——尤其"或"出来的替代形态(如"condition 与数据同形,**或** rank 1 且匹配首维"是两种形态、两条用例)、可选输入缺省、规格点名的特殊 rank。**只测了其中一种形态 = 另一种形态完全未验证**,转换器/infer/kernel 对它的行为(支持、拒绝、还是静默算错)是未知的。某形态实测被转换器拒绝 → 这是一条要如实上报的结论(见「失败排查」),不是删除该用例的理由;未实跑不得删除,builder 产不出该形态时按「必守约束」的「还没跑」条处置。 |
| 特殊语义 | 算子特有行为(负 axis / 多输出 / 原地…) |

无属性算子(Relu、Abs、HardSwish…)只需 shape + 值域 + 敏感区间 + 数值形态。

> **值域下限受打印分辨率约束(设计用例时即遵守,勿等假 FAIL):** 余弦在 Python 侧基于 benchmark
> **文本打印**的输出张量计算(`%f`,六位小数),可分辨的最小量级约 `1e-4`。用例的预期**输出**量级若
> 低于此(如值域 `[-1e-6, 1e-6]`),打印端只剩截断噪声,余弦反映的是打印精度而非内核精度——fp32 也会
> 假 FAIL。"小量级"用例取 `1e-3` 量级即可达到测试目的(远小于默认 `±6` 的 baseline、足以考验量化
> scale 分配),不要再往下压。

### 输入形态覆盖与测试数据生成门禁

在启动 harness 前，先把规格中所有输入形态组合逐项列成 case 矩阵：dynamic、initializer、
optional 缺省/显式、广播形态、索引/边界语义、折叠 blocked/allowed，以及每个支持的 dtype
都必须有独立 case 或有证据的 N/A。一个代表 case、只填写 builder 参数、或只覆盖同形输入
不能推断其它形态已经覆盖。若规格允许标量或单元素输入，`make_inputs()`/`gen_dataset.py`
必须能生成 `[1]` 或标量数组；不得隐含“至少两个元素”。索引类用例必须按来源规范决定
负索引和越界的预期行为，不能静默把它们删除、截断或取模。代码 review 与
`capability_checklist.json` 的每一行都要能回指到这些 case，缺少映射时 Host 门禁失败。

### 量化校准与推理输入的数据一致性（INT8 精度关键）

harness 对 `riscv_int8` 路径的校准数据和推理输入使用**同一份 `make_inputs()` 产物**：
- 推理侧：`input_files` = `make_inputs()` → `.bin`
- 校准侧：`calib_dir` = `input_files` 的直接副本（`run_all_cases.py` 的 calib 准备逻辑：校准数据直接复用推理输入）

因此只要 `make_inputs()` 是确定性的，校准范围与推理范围天然一致，不存在 mismatch。

**但这要求 `make_inputs()` 为每条用例产出有意义的数值**——不当的值域选择会导致 INT8 精度问题的假阳性：

| 问题 | 现象 | 正确做法 |
|------|------|---------|
| 用例全是正数或全是负数 | 量化 zp 偏向一侧，另一侧精度不足 | 至少一条全正数、一条全负数、一条正负混合 |
| 遗漏算子敏感区间 | 内核在非线性段/截止区/saturation 区有 bug 但测不到 | 根据算子特性设置跨越敏感阈值的用例（如 HardSwish 的 ±3、ReLU 的 x=0 两侧） |
| 输入全零 | INT8 量化后 scale≈0，输出无意义，cos 偏低 | 至少有一条用例覆盖非零范围 |
| 只覆盖小量级值 | MAX_MIN 量化的 scale 极小，量化误差放大 | 有中等量级（如 ±6）的 baseline 用例 |

**设计 `make_inputs()` 时的默认策略：**
1. 一条 baseline：`linspace(-6.0, 6.0, n)` —— 正负混合，覆盖大多数算子正常工作区间
2. 一条全正数 + 一条全负数 —— 考验 INT8 zp 的偏向
3. 一条全零 —— 退化输入健壮性
4. 针对算子本身特性，每条敏感区间至少一条 —— 见上表「算子敏感区间」列
   > **单元素输出用例只能证明"能跑通"，证明不了数值正确**——任意两个同号标量的余弦恒为 1.0。单元素用例照设（探崩溃/越界），但凡其代码路径与多元素不同（如 kernel 对 scalar 条件走专用快路），**必须另设同路径的多元素用例**承担数值判别；不可见单元素 PASS 就认为该路径数值正确。
5. **多数据输入算子**（条件选择、Concat、逐元素二元等）：至少一条「**输出分布 ≠ 输入分布**」的判别用例——各输入同量级正负混合（如都在 `[-6,6]`），条件/选择只命中**单一符号侧**使输出单边（输出 scale/zp 与输入不同）。各输入之间**不要拉开数量级**（无判别力，不要设）。

## 运行

**填好三个变量后整块复制执行**（`--spec` 传绝对路径——harness 以 spec 所在项目目录为锚写报告与 `output/`，与当前目录无关）:

```bash
PROJ=$MSLITE_OP_OUTPUT/<op>                         # 算子目录；MSLITE_OP_OUTPUT 缺省与 mindspore-lite 仓平级(HiSpark.AI 仓内即 src/mslite-op-output)
export MSLITE_PKG=<构建产物解压目录>         # .../output/mindspore-lite-<ver>-linux-x64（不是 build/）
SKILL=<hs-verify-op-host 的绝对 skill 根路径>

test -x "$MSLITE_PKG/tools/converter/converter/converter_lite" \
  && python "$SKILL/scripts/run_all_cases.py" --spec "$PROJ/scripts/op_spec.py"
```

- `--framework {onnx,tflite,all}`(默认 all):每个框架用自己的 `*_TEST_CASES` 跑一轮、单独出一份 Excel。
- `--target {x86,riscv,all}`(默认 all):每框架内选目标路径,决定表里出现哪些余弦列。
- harness按所选框架惰性安装依赖：ONNX路径安装`onnx`和`onnxruntime`，TFLite路径安装
  `tensorflow`，报告安装`openpyxl`，基础数值处理安装`numpy`。优先清华源、失败后尝试默认源；
  安装到当前虚拟环境或当前用户范围，并在同一解释器中重新import验证。Agent看到缺包日志后
  必须等待自动修复结果并继续，不能把第一次`ModuleNotFoundError`直接当成最终结论。

### 长任务执行与崩溃检测(harness 单轮 10+ 分钟)

harness 串行跑「生成→转换→编译→推理」,单轮 10+ 分钟。**后台启动 + `wait_verify.sh` 阻塞等待**——
禁止自拼 `sleep N && tail` 盲等（sleep >110s 会被 Bash 工具默认 120s 超时杀掉,exit 143 是 sleep
被杀不是验证结果;实证多次算错）:

```bash
RUN_ID="host-$(date +%Y%m%d%H%M%S)-$$"
nohup python "$SKILL/scripts/run_all_cases.py" --run-id "$RUN_ID" --spec "$PROJ/scripts/op_spec.py" \
    > "/tmp/op_verify_${RUN_ID}.log" 2>&1 & echo $! > "/tmp/op_verify_${RUN_ID}.pid"
# 一条命令内部轮询到结束或到时（Bash 工具 timeout 设 (max_secs+60)*1000 毫秒,如 540 配 600000）:
bash "$SKILL/scripts/wait_verify.sh" "/tmp/op_verify_${RUN_ID}.log" 540 \
    "$(cat /tmp/op_verify_${RUN_ID}.pid)" "$RUN_ID"
# 退出码: 0=已出 VERDICT(贴出末尾,照抄) / 1=进程退出无 VERDICT(闸门拦截或崩溃,读贴出的日志)
#        / 10=还在跑(再跑一次 wait_verify.sh 接着等)
```

- **崩溃/卡死由 harness 自己兜底,无需人肉盯进程。** 每条路径有超时上限(默认 1200s,环境变量 `OP_VERIFY_PATH_TIMEOUT` 秒可调),超时即**连同 `converter_lite` 子进程整组 kill**,不再无限等。converter 因堆损坏 abort(SIGABRT)、段错误、或日志出现 `malloc/sysmalloc/encounter an unknown error` 时,harness 把该路径判 FAIL 并在结论里写明原因(如 `converter crashed: SIGABRT — abort / heap corruption`、`TIMEOUT — converter hung`)。
- 这类 crash 几乎都是**算子量化通路的空指针/越界（implement 实现侧 bug）**,不是验证流程问题——照结论给的路径去查 `stderr.log` 与生成代码，并交 workflow 回流算子实现专项 Skill。
- 某路径**确实只是慢**(大 4D + 量化)被超时误杀时,调高 `OP_VERIFY_PATH_TIMEOUT` 重跑,而不是降覆盖或放宽阈值。

## 读取结果(汇报只认这些)

- **VERDICT**:harness 末尾打印 `VERDICT: op=... N/M variant-cases PASS, K FAIL ...` 一行,并写入项目根
  `verify_summary.txt`。**这是唯一可信的结论来源,向用户汇报时照抄它与退出码**。
- **退出码只认 VERDICT 后紧跟的 `HARNESS_EXIT=N` 行**(0=全 PASS,非 0=有 FAIL;同步写入日志与
  summary)——nohup 后台模式下进程退出码不可观测,这一行就是为此而设。**禁止自行 `grep -c FAIL`
  之类计数判定**:VERDICT 的 "0 FAIL" 字样也会被计入,全绿会被误判成失败(实证踩过)。
- **报告**(每框架一份):`<op>_<framework>_test_results.xlsx`(写在你运行 harness 的项目目录下)。
  一行一个用例;列 = 用例编号 / 描述 / `PARAM_COLUMNS` / 各 active 路径余弦 / 结果 / 备注。
  所有已运行路径达各自阈值才整行 PASS(绿),否则 FAIL(红);末尾汇总行给总计/通过/失败与判据。
- **板端期望分母**:`board_expected_matrix.json`。harness从本轮实际执行的
  `riscv_fp32/riscv_int8`行自动生成，每行冻结`framework/case_id/mode/model/input_dir/gt_dir`
  和Host状态。完整workflow必须使用`--target all`；Board不得手工重写该文件或只挑代表case。
- **现场**(`output/<framework>/tc<id>/`，按类型分类，类型下再分三路径):
  ```
  tc<id>/
  ├── model/                 # 共享: ONNX/TFLite 模型 (build 一次, 三路径复用)
  ├── input/                 # 共享: input*.bin + riscv_int8 的 calib_<i>/ 副本
  ├── gt/                    # 共享: onnxruntime/tf.lite 参考输出 (.npy, 供审计)
  ├── convert/               # 三路径的转换+构建树并排
  │   ├── x86_fp32/          #   *_micro (driver CWD, 含 net*.c)
  │   ├── riscv_fp32/
  │   └── riscv_int8/        #   (+ micro_riscv_quant.cfg)
  └── output/                # 三路径的运行产物并排
      ├── x86_fp32/          #   _run.sh / _driver.sh / stdout.log / stderr.log / output.npy / judge.txt
      ├── riscv_fp32/
      └── riscv_int8/
  ```
  `output/<framework>/` 在每轮开跑时被 harness 清空——现场只属于本轮,不存在上轮残留,无需(也不要)手动 `rm -rf` 后再跑。每个 `output/<path>/_run.sh` 都是可从任意 cwd 执行的单路径复现入口:它会在对应 `convert/<path>` 下重跑转换/编译/benchmark,覆盖写回本路径的 `stdout.log`/`stderr.log`,再调用同一 Python 判定入口刷新 `output*.npy` 与 `judge.txt`。`gt/output*.npy` 是稳定参考,不会被 `_run.sh` 改写。`INT8_NOT_GENUINE` 闸门 grep 的是 `convert/riscv_int8/**/net*.c`。
- 入口在任一路径未达阈值或无法运行时**非零退出**。

判定:x86/riscv fp32 余弦 ≥ 0.999;riscv INT8 ≥ 0.99(量化有损,故更宽)。

## 失败排查(按优先级)

### converter CLI 预检与可复现回退

如果固定驱动无法启动，优先直接重跑下面的harness入口。它会在启动converter的同一进程中
自动定位和配置本轮`MSLITE_PKG`的动态库；以下`--help`仅用于读取已生成日志后的诊断，不要求
用户永久设置环境变量：

```bash
CONVERTER="$MSLITE_PKG/tools/converter/converter/converter_lite"
test -x "$CONVERTER" || { echo "CONVERTER_MISSING=$CONVERTER"; exit 1; }
python3 "$SKILL/scripts/run_all_cases.py" --run-id "$RUN_ID" \
  --spec "$PROJ/scripts/op_spec.py" --framework onnx --target x86
```

若包内缺少`libmindspore_converter.so`，harness会明确报告工具包不完整；只有这种需要重建/
重新下载工具包或发现多包身份冲突的情形才请求用户确认。`--help` 失败归因于工具包/环境并
停止当前验证；单个模型转换失败则保留该路径的
`stderr.log`，回流模型/spec 或算子实现 owner，不能手工修改通用 harness 绕过错误。
该回退仍使用 `run_all_cases.py` 的固定驱动、余弦和门禁，不得自行替换 converter 参数或 GT。

- **某路径 `ERR` / 没解析到余弦** → 转换或编译失败。看该路径 `stderr.log`;`[ERR]` 行指明在 converter/cmake/make 哪步挂。
  `converter_lite` 报错常是该算子未注册/不支持,或某属性组合无法处理——这是**需要上报的结论**(实现算子支持是另一项独立工作)。
- **报"算子未注册/不支持"时,先判用例是否发出了正确的算子,再下结论。** 用例可能发成了语义相近但不同的 builtin(如非广播版 vs 广播版)。若是用例发错算子,**改用例**;**绝不**为把红变绿而在转换器里给一个错误或无关的算子名硬注册 parser 别名——那与放宽阈值同属作废行为。
- **fp32 余弦偏低(<0.999)** → 算子内核/代码生成的真实数值 bug。先用 fp32 隔离,再看 INT8。
  例外仅一种:该用例预期输出量级 < `1e-4`(低于 benchmark `%f` 打印分辨率,见「用例设计原则」的
  打印分辨率约束)。判别方法:加载该用例参考 `.npy` 看输出量级,并与 `stdout.log` 里打印的张量对照
  ——若打印值全是同一截断值/零而参考非零,是用例值域设计违反约束,**按约束修正值域并重跑**(修改
  对照照常列入汇报);若输出量级正常,则按真实 bug 排查,不得借打印精度开脱。
- **fp32 过、INT8 偏低** → 量化路径问题。
- **`INT8_NOT_GENUINE`** → 该路径生成代码里没调到 int8 kernel 符号,量化把算子旁路成了 fp32(发了 fp32 opcoder)。两种根因:①算子漏进 `support_int8_ops_` 或 int8 OpCoder 没注册——保留证据并交 workflow 回流 `hs-dev-op-implement`;②算子 int8 codegen 用的符号名与默认 `{OP_NAME}Int8` 不同(如激活子类型)——在 `op_spec.py` 声明正确的 `INT8_KERNEL_SYMBOL`。**不要**为消除它去设 `INT8_KERNEL_SYMBOL=""`；只有原生整型/索引/非 float 输出这类量化 INT8 豁免算子可用它,且 PASS 备注会写 `int8_exempt=yes` 而不是 `int8_genuine=yes`。
- **张量个数/shape 不匹配** → 解析到的张量与参考对不上;确认 spec 产出的输出 shape 符合预期、布局(NCHW vs NHWC)正确。x86 与 riscv 驱动**均**已 `sed` 关掉 benchmark 的 10 元素打印上限(全张量 dump 是 Python 侧统一算余弦的前提),若换了缺这行的脚本需补回。
- **余弦恒为 `0.0` 且一边输出全零** → 设备/生成代码真的产出了全零张量(参考非零),这是真实失配,不是边界噪声。**绝不能**靠把 NaN/全零判成 1.0 来掩盖——按 fp32 bug 排查内核/opcoder。

## 范围、失败回流与底线

本 skill 负责**测试设计与 Host 验证**，不负责实现转换器/内核支持。某路径因算子源码缺陷失败时，输出首个
`stderr.log` 错误、失败层和受影响 case，交给 `hs-workflow-op-development` 回流 `hs-dev-op-implement`；不要在本 skill
中顺手修改 parser/kernel/opcoder。若证据表明是 `op_spec.py`、模型构造、输入值域、GT 或 capability 映射错误，才由本
skill 修复并整轮重跑。绝不改参考输出、放宽阈值或手填余弦把红变绿。

完成时额外输出 `HOST_VERIFY_GATE=PASS`；任一 VERDICT FAIL、`HARNESS_EXIT!=0` 或能力未全覆盖时输出
`HOST_VERIFY_GATE=FAIL`。该门禁不代表真实开发板已验证。
