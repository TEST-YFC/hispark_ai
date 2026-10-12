# Host guardrails

目录：

- [必守约束](#必守约束red-flags违反即作废)
- [前置检查](host-contract.md#前置检查)

进入对应阶段时读取本文件；固定 harness 和防伪规则不变。

## 必守约束（Red Flags：违反即作废）

以下红线**任何情况都不得越过**:

- **就地运行 bundled harness。** 不要手敲 `converter_lite` / `cmake` / `benchmark` 去"复现"流程,
  也不要把 `run_all_cases.py` / `*.sh` / `*.cfg` 拷进仓库改造。
- **harness（`run_all_cases.py` / `*.sh` / `*.cfg`）是不可变基础设施。** 独立 Host 任务只能新建或编辑
  `op_spec.py`，不得修改 harness。harness 被所有算子共享；为单个算子修改它会影响共享验证基础设施，并使本次结论失效。
  完整 workflow 中，`op_spec.py` 已在 Stage1 冻结，Host 阶段只能只读对账；如需调整用例、模型、GT 或覆盖映射，
  必须返回 workflow Stage1 重新生成初版文档并通过 pre-source gate。确有 harness 能力缺口（如多输入校准）时，
  这是独立的 harness 维护：必须明确维护意图、同步更新本 SKILL.md、先运行 `tests/test_harness_core.py` 守住防伪
  结论不变量，并在已有算子上回归，不能混入某次算子验证。
- **余弦相似度一律由 harness 在 benchmark 跑完后用 `cosine_similarity()` 在 Python 侧计算**,x86 与 riscv
  **同一函数、同一判据**。benchmark 只负责**打印输出张量**(`PrintTensorHandle`),**绝不由 benchmark 决定
  PASS/FAIL**(不传 calib 文件、不依赖其内置 `CompareOutputs`)。参考输出由 harness 用 onnxruntime /
  `tf.lite.Interpreter` 现算；仅当 ONNX Runtime 明确返回 `NOT_IMPLEMENTED` 时，harness 可对同一模型和输入使用 ONNX
  官方 `ReferenceEvaluator`，其他异常仍硬失败；ORT 成功的原生整数输出还要与官方 evaluator 做精确一致性审计，
  两者冲突时采用官方 ONNX 结果并打印留痕。spec 不提供 ground truth;禁止手填任何余弦数字或"预期张量"。
- **绝不把 `NaN`/`Inf` 余弦映射成通过值。** `cosine_similarity()` 对一切输入都有定义、永不返回 NaN:
  两边全零→`1.0`(都没产出=相符)、**恰好一边全零→`0.0`(真实失配=FAIL)**。任何 `nan→1.0` 之类的旁路
  都是在掩盖失败,一律禁止。NaN 进入结论 = 余弦没真算出来 = 要修的 bug,不是可以编造的 PASS。
- **不得通过放宽阈值或修改参考结果消除失败。** fp32≥0.999、INT8≥0.99 是固定判据。完整 harness 会拒绝非默认 `--threshold-*`；自定义阈值只允许与 `--judge-case` 一起做单路径诊断，并打印 `VERDICT_NON_SIGNABLE=1`，不能据此生成最终结论。
- **报告与 `output/` 一律落在算子项目目录(约定 `$MSLITE_OP_OUTPUT/<op>`，缺省与 mindspore-lite 仓平级，HiSpark.AI 仓内即 `src/mslite-op-output/<op>`)。** harness 以 `--spec` 所在位置为锚
  (`<proj>/scripts/op_spec.py` → 输出写到 `<proj>`),**与当前工作目录无关**——所以 `--spec` 必传绝对路径
  (实证:重跑时漏 `cd` 曾把整轮输出写错位置白烧 10+ 分钟,锚定 `--spec` 后此错不再可能,但相对路径仍按 cwd 解析)。
  **op_spec.py 严禁放在 MindSpore Lite 源码/构建树内**(会把 `output/`、`*_test_results.xlsx`、`verify_summary.txt`
  灌进 submodule)。harness 已内置该目录守卫,触发即停。
- **某路径 `converter_lite` 失败是一条 FAIL 结论**,按其 `stderr.log` 如实上报(常因该算子未注册/不支持,
  或某属性/输入组合无法处理——实现算子支持是另一项独立工作)。**不得用"harness 限制""已就绪""非算子问题"
  等措辞掩盖未验证的路径**;没跑通就是没跑通。
- **多条互不相关的用例同时出现 converter 错误、全部失败或启动即崩溃时，先排查构建环境。**
  当失败范围明显超过本算子改动可能影响的范围（多框架、多形态，且既有 PASS 用例也失败）时，优先检查工具包
  新鲜度和 `mindspore` 子模块是否被构建脚本 `--remote` 推进到其他 commit，避免 converter 行为整体漂移。处置：返回
  `hs-workflow-op-development` Stage3，核对构建新鲜度和子模块 SHA 未漂移（`build_mslite.sh` 的 `[SUBMOD-LOCK]` 守卫）。
  不得在缺少证据时逐用例修改算子代码，也不要反复 `git checkout` 子模块或 `git stash` 试错。
- **轻量Python运行包缺失时先自动修复，不得直接停下。** 使用当前Host任务的同一Python解释器，
  在虚拟环境或用户范围安装并验证后继续；ONNX必须同时具备`onnx`和`onnxruntime`。只有管理员
  权限、系统级修改、卸载/降级冲突或大型工具链等超出自动修复边界时才询问用户。真正的编译
  工具链缺失且无法安全自动补齐时如实报告，不伪造PASS、不模拟运行。
- **harness 内部 step1→step5 强制串行。** 某步失败即该用例 FAIL,不跳步、不臆断通过。
- **输入必须确定性(禁随机)**,否则结果不可复现。
- **INT8 真实性由 harness 机械断言,不靠"flat 1.0"目测。** "量化未生效、算子回退 fp32"的判据**不是余弦值**——离散输出算子(hardmax/argmax/select 等,输出 one-hot/索引)即便量化真生效,int8 与 fp32 结果也恒等、余弦本就 `1.000000`,拿 flat 1.0 当 FAIL 信号会把这类合法 PASS 误杀。真正的判据是**生成的 MCU 代码里有没有真的调用该算子的 int8 kernel**:harness 在每条 `riscv_int8` 路径跑完后 grep 生成的 `net*.c`,命中 int8 kernel 符号才算真,缺席判 `INT8_NOT_GENUINE` FAIL(量化旁路 → 发了 fp32 opcoder)。符号默认 `f"{OP_NAME}Int8"`(nnacl 惯例);激活子类型等 int8 符号异名的算子,在 `op_spec.py` 声明 `INT8_KERNEL_SYMBOL`(如 HardSwish→`HSwishInt8`)。**一个算子若按输入形态发射多个 int8 计算函数(如等长核 + 广播核),声明为列表** `INT8_KERNEL_SYMBOL=["BroadcastWhereInt8", "WhereWithTripleInputsInt8"]`——某用例只要命中列表中**任一**符号即算真(闸门只判"是否回退 fp32";发对了哪个 int8 核由余弦负责)。漏列某变体会让发射该变体的用例被误判 `INT8_NOT_GENUINE`。**仅**量化 INT8 豁免算子(原生整型/索引/非 float 输出)可设 `INT8_KERNEL_SYMBOL=""` 关闭该检查,绝不用它掩盖真实回退。**PASS 行备注会区分 `int8_genuine=yes` 与 `int8_exempt=yes`**：前者证明生成代码确实调用 int8 kernel；后者只说明本算子没有 fp32→int8 量化 kernel 需要证明。
- **不得靠"在算子源码里禁用 int8/量化通路"来凑绿。** 把算子移出 `support_int8_ops_`、注释 int8 kernel/coder 注册再跑,`riscv_int8` 路只是退化成 fp32 回退——这不是 INT8 PASS,是**未验证**。要验的恰是带量化的真实通路;禁用它后再宣布验证通过，结论无效。**harness 的 `INT8_NOT_GENUINE` 闸门会自动拦截这种回退**(生成代码里 int8 kernel 符号缺席即判 FAIL,见下条);用 `INT8_KERNEL_SYMBOL=""` 关闭检查后再宣布验证通过,与删 FAIL 用例换绿同属作废行为。若量化通路本身崩溃(见「运行」里的「长任务执行与崩溃检测」),那是要修的缺陷,不是可以绕过的理由。
- **结论只认 harness 的输出。** 向用户汇报必须照抄 harness 末尾的 `VERDICT` 行 / 退出码 / `verify_summary.txt` /
  Excel,**不得凭记忆复述、不得美化、不得自行宣布通过**。harness 退出码即结论:非零=有 FAIL。
- **`op_spec.py` 任何改动后必须重跑 harness。** 不得复用旧结论或旧 Excel——它们不反映最新代码。
- **每个算子的用例按其自身规格新写，禁止复用其它算子的 `op_spec.py`。** 即便新算子在实现上映射到已有 PrimitiveType，其输入个数 / 广播 / 量化语义可能不同，套用别的算子用例会漏测。
- **已存在的 `op_spec.py` 必须先与本次“框架 × 算子”范围核对，不得直接复用。** 它可能来自上一次运行，内容已过时或不适用于本次范围。
  - **独立 Host 任务**：对账不通过时，按当前能力清单整体重建 `op_spec.py`，不要在旧文件上零散补丁；用户明确要求从头设计用例时，同样整体重建。
  - **完整 workflow**：`op_spec.py` 已在 Stage1 冻结。若模型构造、输入/GT、case、覆盖映射或能力清单必须变化，停止 Host 阶段并返回 Stage1；重新 prepare、生成初版文档、通过 pre-source gate 后再继续。不得在 Host 阶段改写冻结 spec 或 facts。
  - 只保留本次范围且经存在性查证的框架 cases 与 `build_*_model` 分支；注释、docstring 和语义说明必须与查证结果一致。
  - 一个 `op_spec.py` 只描述一个算子的一个 builtin；`build_*_model` 不得因形状等条件静默切换到其他 builtin。
  - 用例覆盖必须满足能力清单要求。能力清单是单向依据：独立任务可据此更新 spec 或新增用例；完整 workflow 则应返回 Stage1 更新计划。不得为了适配存量用例而反向缩减能力清单。
- **“尚未执行”不是删除用例的理由。** 结论必须按本轮日志确定：builder 无法以当前 builtin 产出该形态时，保留占位并报告覆盖缺口；builder 已生成用例但 converter 或编译明确拒绝时，记录 `FAIL` 或不支持。两种情况都不得改用其他 builtin 替代目标算子。任何“无法生成”或“不支持”的说明均须附本轮实跑日志依据。
- **能力清单是单向依据，不得反向改写以适配存量用例。** `hs-dev-op-implement` step3 产出的能力验收清单冻结在 `<proj>/scripts/capability_checklist.json`。harness 在运行前检查每条能力的 `covered_by` 引用及可选 `match` 参数，运行后按本轮通过用例计算覆盖；未覆盖能力会使 VERDICT 失败。独立任务确需调整能力项时，标注“计划变更（原 X → 现 Y，理由）”并交由用户决定；完整 workflow 必须返回 Stage1，不得在 Host 阶段静默修改 JSON。
- **FAIL 用例不得删除、不得调弱换绿。** harness 对此有机械闸门：本轮用例集比上轮 `verify_summary.txt` 缩水即拒跑（`CASES_REDUCED`），`OP_VERIFY_ACK_REDUCED=1` 仅在**用户明确决定**将该形态列为覆盖缺口后使用，且豁免会记入 VERDICT——靠删 summary、改算子名等方式绕过闸门与伪造数据同级。
  - **`CASES_REDUCED` 的基线就是 `verify_summary.txt`——所以严禁把它当"残留"删除。** harness 每轮已自动清空 `output/`，**无需任何手动清理**；尤其**不要** `rm verify_summary.txt`。删掉它会抹掉上一轮用例基线，使闸门无法发现用例被减少。要换 spec 直接改 `op_spec.py` 重跑即可，基线由 harness 自己维护。出现 FAIL 后只有两个合法动作：**修实现代码**，或**证明用例本身设计错误**。把 FAIL 归因为"用例设计问题"必须给出**生成代码/日志级证据**（如生成 `.c` 里的量化参数失配、塌缩的输出值），不得只凭"量化精度固有限制""退化输入无意义"一类说辞。任何用例修改（值域、形状、条件模式）必须在汇报中**列出修改前后对照与理由**，且修改后的严酷度（量级跨度、形状规模、边界覆盖）**不得低于原用例**；"把用例调到刚好能过"与放宽阈值同属作废行为。
- **只为该算子真实存在的框架建用例，且禁止用等价算子顶替。** 先按「用例设计原则」里的确定性命令查证每个框架是否定义该算子（ONNX 页面 HTTP 码 / TFLite builtin 枚举）；某框架查证为"无"就不写该框架用例、不测该框架——**不得为了让模型建得起来，把 `build_*_model` 改成另一个"等价算子"**。那样测的是别的算子，结论无效。
- **序关系类算子（argmax/hardmax/topk/sort 等输出由"谁更大"决定）的 int8 用例必须用模板的 `make_distinct_axis_inputs()` 造数。** 普通 linspace 在大张量下相邻值间距 < 量化桶宽（全幅/254），多个浮点不同的值落进同一 int8 桶，int8 取到的极值位置就偏离 fp32 参考——FAIL 但 kernel 没错（实证：Hardmax 大 4D 两次 FAIL 烧掉一轮验证）。这是「证明用例本身设计错误」的已知合法模式之一，证据即沿轴相邻值间距与量化步长的对比计算。
- **多数据输入/搬运·选择类算子必须含一条「输出分布 ≠ 输入分布」的判别用例（抓漏重量化/字节拷贝）。** 设计：各数据输入**同量级**、正负混合（如都在 `[-6, 6]`），条件/选择**只命中单一符号侧**，使输出值域单边、其 scale/zp 与输入明显不同。漏重量化会把输入域 qparams 原样带进输出形成仿射失真，cosine 可测（实测：字节拷贝 ~0.95 FAIL，正确重量化 ≥0.9999 PASS）。**各输入之间不要拉开数量级**（量化器按值域并集分配共享输入 scale，量级悬殊的用例无判别力，不要设）。
