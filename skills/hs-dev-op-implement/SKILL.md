---
name: hs-dev-op-implement
description: Use when working on MindSpore Lite operator support for HiSpark.AI / RISC-V MCU deployment, including operator analysis, new ONNX/TFLite operator support, INT8 quantization, code generation, MCU deployment, parser/kernel/opcoder work, or requests such as "新增算子", "分析算子", "add operator", "add op", "implement op", "port operator", "支持算子", and "新增op". The "新增算子" path goes end-to-end: implement → compile → verify accuracy → flash to board with cosine similarity check — no handoffs, no asking.
---

# 新增 MindSpore Lite 算子

本 skill 用来把一个 ONNX/TFLite 算子从需求走到 MindSpore Lite MCU 可用：先查证规格和仓内现状，再决定复用已有 `PrimitiveType` 还是新建，随后补齐代码、构建，`hs-verify-op` 做精度验收，最后 `hs-debug-op-board-accuracy` 烧录到板端做精度比对。

算子实现最多贯穿 **7 个代码层**，但**不是每个算子都要做满 7 层**。要做哪些层由 **step2 决策**算出；每层怎么写以 `references/implementation-guide.md` 的模板为底稿改名填空。本文只管流程、决策与门控，代码模板、注册宏、易错点在实现指南里。

```
① Schema  ② Parser  ③ Populate  ④ Infer  ⑤ Kernel(fp32+int8)  ⑥ OpCoder(fp32+int8)  ⑦ Quantizer
```

**路径基准**：本文所有路径相对 **mindspore-lite 代码根目录**（含 `schema/`、`tools/`、`src/litert/` 的那一级；HiSpark.AI 仓库中是 `src/mindspore-lite/mindspore-lite/`）。`<skill>` = 本 skill 安装目录（通常 `~/.claude/skills/hs-dev-op-implement`）。

## 用户能看到什么

执行时向用户展示三类信息：

1. **当前模式**：仅分析，或完整实现。
2. **todo 进度**：每次阶段性汇报都用 Markdown todo，而不是压缩成一行进度条。
3. **门控产物**：每个 step 完成前必须在对话正文给出证据；只落盘不展示给用户不算完成该 step。

阶段性汇报固定格式：

```markdown
状态: step<n> 进行中
待办:
- [x] step0 确定算子和框架
- [x] step1 扫描算子现状
- [ ] step2 决定复用还是新建（进行中）
- [ ] step3 分析链路并列能力清单
- [ ] step4 编写算子代码
- [ ] step5 编译前预检
- [ ] step6 编译构建
- [ ] step7 验证精度
- [ ] step8 烧录板端精度比对
```

仅分析模式只列 step0-step3。多实现单元时每个实现单元各一组 todo，标题写 `待办[Select]:`。某 step 标为 `[x]` 的前提是它的门控产物已经真实出现在对话正文；不得为了进度好看提前勾选。

## 两层对象：source entry vs implementation unit

用户输入里的 `ONNX ConvTranspose`、`TFLite TransposeConv` 这类 **框架 × 算子名/builtin** 叫 **source entry**。真正要新增/复用的 `PrimitiveType`、kernel、opcoder 叫 **implementation unit**。

**不要把 source entry 数量直接等同于实现任务数量。** 多个 source entry 可能只是同一个算子在不同前端的名字/输入顺序/属性编码不同，正确做法是：

1. step0 先列出用户指定的所有 source entry。
2. step1 对每个 source entry 都跑 scan/规格查证，日志分别归档。
3. step2 先做 **source grouping 裁决**：哪些 source entry 可落到同一个 implementation unit，哪些必须拆开。
4. step3-step8 按 implementation unit 执行；同一 unit 内为每个 source entry 补对应 parser/用例，底层 ①③④⑤⑥⑦ 只做一次。

**可合并为一个 implementation unit 的条件**（必须逐条给证据）：计算公式/输出语义相同；dtype 语义相同或可由同一 Primitive 表达；shape/infer 语义相同；属性能无损映射到同一 schema 字段；输入顺序差异仅由 parser 重排解决；能力清单能覆盖所有 source entry 的差异。

**必须拆开的条件**：广播版 vs 非广播版、可选输入导致输出语义不同、属性语义不是无损映射、一个 source entry 需要另一个不支持的行为、或 scan/规格不可达无法证明等价。名字相近不是合并理由；框架不同也不是拆分理由。裁决前不得凭记忆合并或拆分。

**典型合并形态**：用户指定 `ONNX ConvTranspose` + `TFLite TransposeConv` 这类跨框架同语义入口时，step0 仍列两条 source entry，step1 两条都查证；若 step2 证明二者都是转置卷积、输出/shape/属性可无损映射，就合并为一个 ConvTranspose implementation unit：新增/复用一套 Primitive/kernel/coder，分别补 ONNX parser 与 TFLite parser，hs-verify-op 同一项目里覆盖 `onnx` 与 `tflite` 用例。

### 语义名发现（用户只给一个通用算子名时）

用户只说 `ConvTranspose`、`TransposeConv`、`deconvolution` 这类**没有明确框架范围**的名字时，先把它当作 **semantic op name**，不要直接缩成某一个框架的 source entry，也不要凭记忆静默扩成多个框架。正确流程：

1. step0 声明「用户给的是语义名，框架范围待查证」，并默认查证本 skill 支持的 ONNX + TFLite 两个前端。
2. step1 用确切名跑 scan；若某框架 `NOT_FOUND`，再使用 scan 的跨框架映射字典/同义词簇候选（如 `convtranspose|transposeconv|deconv`）对候选名字逐个查证，直到得到 FOUND/NOT_FOUND/UNREACHABLE 的证据。
3. 把 FOUND 的框架入口列为 source entry，UNKNOWN/UNREACHABLE 不自动纳入实现范围；若全部不可达，停下问用户。
4. 对 FOUND 的 source entry 继续走 source grouping。若证明等价，就一个 implementation unit 覆盖多个前端；若不等价，就拆成多个 unit。

对 `实现 ConvTranspose` 这类请求，合理结果可以是「ONNX `ConvTranspose` + TFLite `TransposeConv` 合并为一个 unit」，但前提是本会话查证 `TransposeConv` 是 TFLite 的 FOUND 入口且 step2 证明语义可合并。禁止只因名字相似直接加入 TFLite；也禁止只因用户没写 TFLite 就忽略已查证的同语义前端，除非用户明确限定“只做 ONNX”。

## 产物工作区 `<opdir>`

每个 **implementation unit** 的全部产物落在 `$MSLITE_OP_OUTPUT/<unit>/`（下称 `<opdir>`）。若多个 source entry 合并到同一 unit，用共同 Primitive/语义名作 `<unit>`；在 `docs/spec.md` 里列出全部 source entry，不为同一 unit 建多个重复 opdir。

- `MSLITE_OP_OUTPUT` 缺省**与 mindspore-lite 仓平级**（HiSpark.AI 仓内即 `src/mslite-op-output/`），可由环境变量覆盖。它独立于业务仓、**不在 mslite 源码树内**（满足 hs-verify-op 红线），Claude 与 Codex 共享同一份。
- step0 建目录时从 `$MSLITE_OP_OUTPUT/_template/` 拷骨架。`<opdir>` 结构：
  - `docs/` — `spec.md` / `decision.md` / `link-analysis.md` / `reference-impl.md` / `builtin-probe.md`。**step1-step4 的思考产物逐份落盘，不止留在对话里。**
  - `scripts/` — `op_spec.py`、`capability_checklist.json`、`env_setup.sh`
  - `logs/`、`run.sh`、`output/`（验证现场，gitignore）

## 运行模式

先判断模式，向用户说明后再执行：

| 用户输入 | 模式 | 执行范围 |
|---------|------|---------|
| "分析XX算子" / "算子分析" / "XX算子链路" | **仅分析** | 只走 **step0-step3**，呈现链路分析表 + 能力清单后**停止**，不进实现 |
| "新增XX算子" / "支持XX算子" / "add operator" | **完整实现** | **step0-step8** 全程：决策 → 写码 → 编译 → 精度验证（调 `hs-verify-op`）→ 烧录板端精度比对（调 `hs-debug-op-board-accuracy`） |

**多 source entry 先分组，不直接串行实现。** 用户一次点名多个框架/算子名时，先按上文 source grouping 做裁决：

- 若裁决为 **同一个 implementation unit**：只做一套 ①③④⑤⑥⑦；② Parser 和 hs-verify-op 用例按 source entry 分别补齐；一个 `<opdir>` 内的 `framework_scope` 覆盖所有 source entry。
- 若裁决为 **多个 implementation unit**：每个 unit 串行独立走 step1-step8（先验证+烧录完一个再开下一个）。
- 若是同一框架同族 builtin（如广播/非广播、V2/V3 语义不同）：默认拆开，除非规格证明逐项等价。

## 红线

违反任一条即返工：

1. **不走 Custom 捷径。** 标准 ONNX/TFLite 算子必须落到真正的 `PrimitiveType`；**严禁** `ops::Custom` + `PrimType_Inner_*` + `REG_BUILIN_CUSTOM_CODER`。
2. **存在性与语义只认查证，不认记忆。** 框架有无此算子由 scan 的 `FOUND/NOT_FOUND` 裁决，`NOT_FOUND` 即"无此算子"（**不翻案为"别名/旧名"，不用等价算子顶替**）；广播/形状/量化语义以语义摘要或规格原文为准。全部源不可达 → **停下问用户**（见 `references/spec-sources.md`）。
3. **量化 INT8 默认必做（除 decision3 豁免）；原生整型 dtype 仍按规格全做。** "INT8 豁免"只表示不走 fp32→int8 量化器/INT8 genuine 符号闸门，不表示跳过 `int8/uint8/int32/...` 这类算子原生输入 dtype 的 kernel/coder 注册。完成 = 本会话亲自跑出 hs-verify-op 全绿；历史 PASS、x86-only、其它能出余弦数字的旁路流程都不算完成；精度验证唯一入口是 `hs-verify-op`。
4. **不碰子模块 git 状态，不靠重建试错。** `mindspore` 是受管子模块（CLAUDE.md：不得直接改）。**严禁** `git checkout <commit>` / `git stash` / `git submodule update` 去"修"它，**严禁**手敲 `build.sh`/`tar`/清 `build/` 碰运气。构建唯一入口是 `build_mslite.sh`；它在构建前记录子模块 SHA，若 `build.sh` 把子模块推进到别的 commit 就以 `[SUBMOD-LOCK] exit 7` 硬停。**先立基线再改码**：动任何源码前，确认当前包能让一个已知用例 hs-verify-op 通过；基线本就失败、或出现「之前全绿的用例成片 converter 报错 / `SUBMOD-LOCK` 报警 / 报错文件不是本会话改的」= 环境或子模块漂移，**不是算子缺陷**，停下报告用户，不得改 parser/kernel/infer，也不得反复重建。

## 总流程

| Step | 用户可读目标 | 必做动作 | 门控产物 |
|---|---|---|---|
| **step0** | 确定语义名/source entry | 锁定用户给定的框架 × 算子名；若只给语义名则进入「语义名发现」，查证 ONNX + TFLite 真实入口，**不凭记忆推断** | 范围声明 |
| **step1** | 扫描 source entry 现状 | `bash <skill>/scripts/scan_op.sh <Op> <代码根>`，每个 source entry 各跑一次 | scan 输出已**完整阅读**；全文在 `/tmp/scan_op_<Op>.log`，并 `cp` 归档到 `<opdir>/logs/` |
| **step2** | source grouping + 复用/新建裁决 | source grouping 裁决 + decision2 复用/新建裁决 + decision3 层集开关；先读 `references/worked-example.md` | 分组结论 + 裁决结论 + 逐条证据 + ①-⑦ 各层做/跳总结表；落盘 `<opdir>/docs/decision.md` |
| **step3** | 分析链路并列能力清单 | 呈现 decision4 产物并逐份落盘 `<opdir>/docs/`；能力验收清单落盘 `<opdir>/scripts/capability_checklist.json`；跑 artifact gate | 框架对应表 + 链路分析表 + 能力验收清单；`ARTIFACT_GATE=PASS`；同族多 builtin 时附探针表 |
| **step4** | 编写算子代码 | 先冻结 `docs/implementation-contract.md` 并跑 artifact gate；每层动笔前打开实现指南对应小节，以模板为底稿改名填空；写 ⑤ 前先呈现参考实现对比表 | `ARTIFACT_GATE=PASS`；参考实现对比表；每层完成即回填能力清单落点 |
| **step5** | 编译前预检 | `bash <skill>/scripts/quick_check.sh <代码根>` | 预检 **FAIL=0**（`SCHEMA_PENDING`/`UNVERIFIED` 均可） |
| **step6** | 编译构建 | `build_mslite.sh` 后台构建 + `--wait` 阻塞等结果 | 末尾 `export MSLITE_PKG=...` 行 |
| **step7** | 验证精度 | 先跑 artifact/op_spec/build-freshness 三闸门，再调用 `hs-verify-op` skill 验证精度 | 三闸门 PASS；每个 implementation unit 的 `VERDICT` 全绿，且 `framework_scope` 覆盖 step0 范围内全部 source entry（fp32 ≥ 0.999、INT8 ≥ 0.99） |
| **step8** | 烧录板端精度比对 | 调用 `hs-debug-op-board-accuracy` skill，烧录 fwpkg 到 WS63/Hi3863 板端并比对余弦相似度 | `FLASH_VERDICT=PASS` + `ACCURACY_VERDICT=PASS`（非量化 ≥ 0.999999、量化 ≥ 0.9） |

## 决策词汇

本文和脚本统一使用下面这些名字：

| 名称 | 含义 | 主要产出位置 |
|---|---|---|
| **decision1 规格查证** | 框架存在性裁决 + 语义摘要 + opset/属性事实 | step1 scan 输出、`docs/spec.md` |
| **decision2 复用裁决** | 复用已有 `PrimitiveType`、走激活子类型，还是新建 `PrimitiveType` | step2、`docs/decision.md` |
| **decision3 层集开关** | 激活子类型、int8 豁免、融合 pass、图消除/重写 pass(3′)、condition/index 首输入这五个开关 | step2、`docs/decision.md` |
| **decision4 链路产物** | 框架对应表、链路分析表、能力验收清单、必要的 builtin 探针表 | step3、`docs/` + `scripts/capability_checklist.json` |

## 完成判据

**首行状态由最近一次 VERDICT 机械决定，不由你的叙述口吻决定**：只要存在 `HARNESS_EXIT≠0`、或任一 VERDICT 行含 `FAIL`/`ERR`/`[UNCOVERED]`，或 `ACCURACY_VERDICT=FAIL`，本次就处于「未完成」态，无可商量（见下「完成状态闸门」）。只有同时满足以下条件，首行才允许写 `状态: 完成`：

1. **贴出 step6 的 `MSLITE_PKG` 行。**
2. **step7 前三闸门均 PASS**：`gate_artifacts.py --stage pre-verify`、`validate_op_spec.py`、`check_build_freshness.py`。任一 FAIL 时不得启动/引用 hs-verify-op 结论。
3. **step0 范围内每个 implementation unit 各一行 VERDICT**，且每行都是 `0 FAIL`、日志中 VERDICT 后有 `HARNESS_EXIT=0` 行；合并多个 source entry 的 unit，其 `framework_scope`/用例必须覆盖每个 source entry。
   - 后台模式下进程退出码不可观测，退出码只认 harness 自报的 `HARNESS_EXIT=0` 这一行。
   - **禁止自行 `grep -c FAIL` 之类计数判定**：VERDICT 的 `0 FAIL` 也含 `FAIL` 字样，全绿会被误判为失败。
   - 任一 VERDICT 含 FAIL/ERR，首行只能写 `状态: 未完成`，无论缺陷是谁引入的。
4. **同族多 builtin 场景附「形态→builtin」探针表**（见 step3）。
5. **原样重贴 step3 能力验收清单**：行内容（形状/轴/属性）不得改写，只追加落点与 PASS 用例编号（确需修订某行须明示修订原因）。逐行标注 PASS 用例编号，或「覆盖缺口（用户已裁决，VERDICT 含 `ACK_REDUCED` 留痕）」。
   - 存在既无 PASS 落点又未经用户裁决的行 = 未完成；回填时悄悄改写清单行、删用例换绿，同性质于伪造。
   - 清单已在 step3 落盘 `capability_checklist.json`，**VERDICT 须含 `capabilities=N/M` 且 N=M**；出现 `[UNCOVERED]` 行即未完成。
   - **VERDICT 的分母是能力清单，不是 op_spec 现存用例**：删除/弱化用例后取得的 0 FAIL 不满足本判据（hs-verify-op 的 `CASES_REDUCED` 与能力覆盖闸门会拒跑并留痕，绕过它 = 伪造结论）。
6. **step8 烧录板端精度比对完成**：`FLASH_VERDICT=PASS` + `ACCURACY_VERDICT=PASS`（非量化 cos ≥ 0.999999、量化 cos ≥ 0.9）。调用 `hs-debug-op-board-accuracy` skill，不跳过、不询问。

中途停下向用户求助是合法动作（如实写 `未完成` + 阻塞原因即可）。但用"已知局限/存量缺陷/非本次引入/需后续修复"包装失败后宣布完成，与伪造数据同级。缺陷来历不改变完成判据（decision2 复用 = 接管存量质量）。

### 完成状态闸门（措辞锁）

本判据约束的是**状态语义**，不是某串字面量——换标题、加括号、改 emoji 都不能把「未完成」说成「完成」。`HARNESS_EXIT≠0`（或任一 VERDICT 含 `FAIL`/`ERR`/`[UNCOVERED]`）或 `ACCURACY_VERDICT=FAIL` 时，全文**禁止出现任何收尾/达标语义的措辞**，包括但不限于：

- **变体标题**：`最终状态`、`最终结果`、`本次任务完成`、`收尾汇报`、`大功告成`、以 ✅/🎉/🟢 作结——只要读起来像"交付了"，就在禁止之列。
- **括号 hedge**：`完成（X 已完成、Y 待后续）`、`完成（仅剩 Z）`、`ONNX 完成、TFLite 待修`——**部分完成 = 未完成，一个 FAIL 也是未完成**。
- **把剩余 FAIL 改写成**"已知剩余缺陷 / 建议作为独立任务后续处理"后照常给"最终"汇报。

此态下唯一合法的首行是 `状态: 未完成`，正文如实列 FAIL 与下一步；要停只能走「证据闸门」或「连续 2 方案失败」，不得以"完成"的任何变体收尾。
> 实证：弱会话两次在 `HARNESS_EXIT=1`、某用例仍 FAIL 时写"状态: 完成（…待后续修复）"与"最终状态：✅ 完成"，靠换标题、加括号绕过只认 `状态: 完成` 字面的旧规则，逼用户两次催"继续"。

### 停止/降级措辞的证据闸门

在对话里写下任何会**结束或缩小**本次修复范围的措辞——`环境问题`、`构建环境问题`、`系统性问题`、`子模块漂移`、`存量局限/已知局限`、`不支持<某形态>`、`覆盖缺口`、`根因较深`、`非本次引入`——之前，**同一条消息里必须先贴出对应证据**。证据缺席时该措辞作废，按缺陷继续修；"凭措辞断言而不贴证据"是红线 2（只认查证不认记忆）在收尾阶段的同款违规。

| 措辞 | 必备证据（缺一不可，全是本会话现跑的命令输出） |
|---|---|
| 环境/构建环境/系统性问题、子模块漂移 | `git -C mindspore rev-parse HEAD` 与构建前 SHA 对比 + `build_mslite.sh` 是否报过 `[SUBMOD-LOCK]` + **一个与本算子无关、之前 PASS 的用例本轮也 FAIL** 的证据（成片回归才是环境，单算子单形态 FAIL 不是） |
| 链接符号缺失（如 riscv_int8 `MatMulInt8_*` linker error） | 缺失符号名 + 在 `libmicro_runtime.a` 与生成 `convert/riscv_int8/**/net*.c` 里 `nm`/`grep` 的实际查找结果 + 判断该符号本应由哪一层产出（⑤int8 runtime / ⑥int8 coder 注册 / 库未编入）——很可能是本次要补的 ⑥int8 缺口，不是"环境" |
| 不支持某形态（group>1、output_padding…） | converter/infer 的**实际报错原文**（`stderr.log` 首个错误行）+ 仓内 infer/kernel 中拒绝或漏处理该形态的 `文件:行` |
| 覆盖缺口 / `ACK_REDUCED` | 下文「数值缺陷根因法」①-⑤ 的逐段对算证据（证明已查到发散点却无法在不破坏其它用例前提下修复）+ 用户明确裁决 |

## step0 确定算子和框架

- 推荐调用格式：**`新增 <ONNX|TFLite|两者> 的 <算子名>`**；跨框架名字不同时可写 **`新增 ONNX 的 <OpA> 和 TFLite 的 <OpB>`**。框架与算子名**只能由用户给定**；用户给出的是 source entry 范围，不等于强制拆成多个 implementation unit。
- **向用户提问锁范围时不得断言任一框架是否存在该算子**：存在性是 step1 scan 的裁决，提问先于 scan，此时的"X 框架没有此算子"必然出自记忆（红线 2）。只列框架选项让用户选；用户反问存在性时答"step1 查证后裁决"。用户只给语义名且未限定框架时，按「语义名发现」先查 ONNX + TFLite 的真实入口，不要在 step0 凭记忆缩/扩范围。
  > 实证：step0 凭记忆断言"TFLite 没有 Hardmax"，碰巧对，但若记错，用户的范围裁决就被幻觉引导。
- 只覆盖确认的 source entry。实现/测试中冒出范围外算子的需求 → **停下报告用户裁决**。正在为清单外算子名创建/修改文件 = 越界，停。多个确认 source entry 若经 step2 证明同语义，可合并到同一 implementation unit；这不是扩范围。
- **例外**：decision2 把用户点名的算子映射到**已有 PrimitiveType**（复用分支）不算扩范围；变的是内部映射目标，不是要实现的源算子集合。

## step1 扫描算子现状

```bash
bash <skill>/scripts/scan_op.sh <Op> <代码根>   # 每个 source entry 各跑一次
```

一条命令同时产出：decision1 规格查证 + 语义摘要 + 多 opset 版本审计 + ①-⑦ 链路扫描（decision4）+ decision2 候选段 + ⑧ 融合/图改写审计。

- **scan 输出必须完整阅读，禁 `head`/`tail` 截断。** 全文在 `/tmp/scan_op_<Op>.log`，并 `cp` 归档到 `<opdir>/logs/scan_op_<Op>.log`。
  > 实证：`tail -60` 恰好截掉 decision1 的 ONNX 语义摘要段，模型拿幸存的另一框架同名摘要误判 decision2 候选语义，错走新建分支。

## step2 决定复用还是新建

### decision2 复用已有 PrimType vs 新建

**第 0 步：先过激活闸门。** 若本算子是**单数据输入 + 输出保形 + 逐元素的非线性激活**（Relu/Elu/Gelu/Swish/HSwish/Softplus/Celu… 这一族），它既不"复用某个等价 PrimType"也不"新建顶层 PrimType"，而是第三条路：**激活子类型**（共享 `PrimitiveType_Activation` + 一个 `ActivationType` 枚举值）。此族直接转 decision3 开关1 裁决，跳过下面的四条等价测试。四条测试是给"非激活算子找等价 PrimType"用的，对激活族永远判不出等价（每个激活公式都不同），照搬必然把激活误导向"新建顶层 PrimType"。

**判据 = 四条逐项相等**（仅适用于非激活算子）：① 输入个数/顺序/语义；② 输出语义；③ 属性集；④ **广播规则**。

要点：

- 确切名在链路扫描 **0 命中 ≠ 需要新建**。复用候选来自 scan 输出的「decision2 候选段」+ 人工语义检索（按"做什么"检索 `schema/ops.fbs` 与 parser 目录，留意规格里 "same as X with broadcasting" 类表述）。
- **候选语义的真值在仓内 ④infer + ⑤kernel 源码**（Read 后裁决），不是"与候选同名的其它框架算子"的摘要。同名异义是常态。kernel 可能按输入个数分支承载多形态，等价性逐分支裁决。
- **仓内既有映射（parser/注册/量化器列表）是 decision2 的审查对象，不是裁决依据**。它可能来自历史的、甚至已被判定为缺陷的实现。"既有 parser 已把它映射到 X"不构成复用理由，照样按四条判据独立裁决；裁决与现状冲突时，把冲突写进 decision4 呈现，并改造既有代码以符合裁决。
- **超集也是不等价**：非广播算子映射到全向广播 PrimType 会静默放宽语义。方向口诀：**广播版找广播版，非广播版找非广播版，找不到逐项相等的就新建**。裁决与工期无关，不得为省事把不等价复用列为"备选"。
- **语义不同的同族 builtin（典型：非广播版 vs 广播版）= 两个独立 implementation unit**，各自 parser、各自映射，绝不并入同一 parser；只有逐项语义相同的 source entry/builtin 才共用同一 unit。
- TFLite 算子命中同族多 builtin / 疑似 converter 归一化时，**裁决前做可达性探针**（哪个输入形态实际落到哪个 builtin），流程与命令见 `references/decision2-reuse-decision.md`（该文件还有候选四层来源与同义词簇缓存的维护方法）。

裁决两分支：

- **走新建** → decision4 必须附「已排查候选 + 逐项不等价理由」，每条带 `文件:行` 或规格证据；走 ①-⑦ + ①‴ 全做。
- **走复用** → **只补现存链路缺失环节**（最常缺 ⑥、⑤int8、⑦），**严禁为它重建 ①③④⑤**；复用分支下创建这些层的新文件 = 越界信号，停下复查 decision2。**复用 = 接管被复用的 ①-⑦ 全部存量代码**：从裁决「复用」的那一刻起，这些 kernel/coder/infer 就是**本次实现的代码**，「已有」≠「已验证」，hs-verify-op 在其中测出的任何缺陷（含别人多年前写错的数学）与你亲手写的代码**同等**在本次修复范围内，处置见 step7「存量缺陷修复 playbook」。补 ⑤/⑥/⑦ 任一计算相关缺口前，也必须按 step4 做参考实现对比；“只打开已有 int8 路径”同样是计算正确性变更，不得免对比。
  > 反例（弱会话实测）：decision2 判复用后把结论写成「全链路均已存在，主要任务是 step7 精度验证」，于是把验证当走过场；hs-verify-op 测出 output_padding 精度缺陷（cos=0.77）时以"存量缺陷、根因较深"搁置——这正是把"接管存量质量"读成了"存量缺陷与我无关"。复用分支的正确心智：**验证不是收尾，定位并修好它暴露的缺陷才是本次实现的主体工作。**

两条分支的端到端范例见 `references/worked-example.md`，拿到算子先读它。

### decision3 层集开关

1. **激活子类型？** 正向判据（满足即"是"，不靠举例/邻居推断）：单数据输入 + 输出保形 + 逐元素非线性。满足即为激活子类型，这是激活族的**默认且首选**路径，复用整条 activation 通路。
   - **"是"的后果**：共享 `PrimitiveType_Activation`，schema①/populate③/infer④ **跳过**（infer 复用 `REG_INFER(Activation, …)`），parser 返回带正确 `ActivationType` 的 `ops::Activation`（返回独立 op 类无匹配 `PrimitiveType` → MetaGraph 序列化时**静默丢弃**），OpCoder 加 `case`，⑦ 查 `support_activation_`。schema 改动只是给 `ActivationType` 枚举加一个值，不是建顶层 `PrimitiveType_Xxx`。
   - **三条反踩坑**：
     - 「`ActivationType` 枚举里没有本算子的值」不是排除理由；子类型路径就是去新增这个枚举值，新算子缺席是常态。
     - 「同族邻居有独立 `PrimType_Xxx` 枚举值」不构成本算子走顶层 PrimType 的理由。`PrimType_Elu=51`、`PrimType_LeakyRelu=76` 确实存在，但二者的 ONNX parser 实测返回 `ops::Activation`（子类型）。以 parser 实际返回什么为准。
     - 「decision2 四条等价测试找不到逐项相等的 PrimType」对激活族不适用；见 decision2 第 0 步激活闸门，激活根本不进那个测试。
   - **真正的非子类型（需独立 PrimType，别走子类型）**：**PReLU**（parser 返回 `ops::PReLUFusion`，2 输入 + slope 张量，专属 `PrimType_PReLUFusion` + 专属 infer）。通则：需 >1 数据输入或带权重/slope 张量 → 不是纯激活子类型。（仓内 `Selu`/旧 `Celu` parser 返回独立 op 类是遗留欠佳实现，非范本；新算子按本判据走子类型。）
2. **量化 INT8 豁免？** 先把本算子的 dtype 语义分成两层，禁止混用：
   - **浮点输入算子**：源输入/输出是 float，`riscv_int8` 通过量化器把 float tensor 量化后运行。这类除明确豁免外，必须做 ⑤int8 + ⑥int8 + ⑦量化器列表，并由 hs-verify-op 的 `INT8_NOT_GENUINE` 闸门证明真的发到 int8 kernel。
   - **原生整型/索引/离散 dtype 算子**：规格本身要求 `int8/uint8/int32/int64/bool` 等输入或输出（如 ConvInteger、Cast、ArgMax、Shape、索引类）。这类可判 **量化 INT8 豁免**：不需要加入量化器列表，也可在 op_spec 中关闭 genuine 符号检查；但仍必须按规格列出的每个 dtype 注册 ⑤ kernel 与 ⑥ OpCoder。`int8` 与 `uint8` 是两个不同派发键，能力清单必须各有用例或明确证明某 dtype 不在规格内。
   - **完成表述**：对原生整型算子写「量化 INT8 豁免，原生 dtype 覆盖：int8/uint8/... 做」，不要写成「fp32 做 / int8 跳过」。
3. **组合算子需融合 pass？**（HardSwish/GeLU/Swish 等被源框架拆成子图）→ **融合 pass + 单算子 ①-⑦ 两者都做**（融合只改图形态，从不替代通路），模板见 `references/optimizer-fusion-template.md`。裁决据 scan 的 ⑧ 融合审计段（grep 证据），不凭记忆：命中既有 pass→读懂它；0 命中且源框架是单算子→填「否」；0 命中但源框架拆成子图→缺融合 pass，填「是」须新建。
   - **开关3 只管「构造型」pass（fusion/produce/consume），不管「消除型」pass**——后者是开关3′，必须单独裁决，别让 graph/ 的删除型命中被开关3 的良性解读（「消费=独立通路仍必需」）一笔带过。
3′. **本算子被既有图 pass 消除/重写？**（passthrough/no-op 类：Identity、推理期 Dropout、同 dtype Cast、空 Reshape…）→ 裁决据 scan ⑧「消除/重写型命中」段（grep 证据：命中文件含 `Remove`/`redundant`/`Eliminat`/对本算子 `isa<>` 擦除）。**消除型 pass 是合法优化，不禁用、不据此跳过 ①-⑦**（算子在该 pass 未触发的图里仍可达，仍须全做）；但命中即填「是」，并**额外**完成两件事，否则 ①-⑦ 是不可达死代码、step7 是空图假绿：
   - **读懂触发条件**：打开命中 pass 的 `DefinePattern`/`Process`，写出本算子**何时被删、何时存活**（典型条件：单消费者、非图输出、前后 dtype/shape 一致等）→ 落 `docs/decision.md`。0 命中=填「否」。
   - **step7 双情形用例**：能力清单必须含一条**该 pass 不触发、算子真正到达 kernel** 的用例——这是 ⑤/⑥/⑦ genuine 覆盖与 INT8 genuine 闸门的唯一落点；并对**该 pass 触发、算子被合法删除**的情形给出用例与结果说明（模型输出仍正确，但**不得据此声称 kernel 覆盖**）。
4. **首输入是 condition/index（bool/int 非数据张量）？** → 运行时与 codegen 都按 `inputs[0]->data_type()` 派发：⑤/⑥ 各只有**一个注册键**（首输入固定 dtype），kernel/coder 内部按数据张量 dtype 分支 fp32/int8。此开关必须在创建任何 ⑤/⑥ 文件前定下（目录与模板见实现指南 ⑤″/⑥；定错 = 整组文件删除重建）。

### 决策总结表

**这张表必须在对话正文呈现给用户**（step2 门控产物）：选定本算子所在列后，把该列 ①-⑦ 各层「做/跳」逐项落成结论贴出来。不能只口头说"走新建/复用"，也不能只写进 `decision.md`。本表只决「做/跳」、不贴文件路径；step3 §2 的链路分析表会把这里的合并行按固定映射展开成「可达性 + 文件」落地视图，两表行序一致、逐行可对照。

| | 激活子类型 | 复用已有 PrimType | 新 PrimType（浮点输入，需量化） | 新 PrimType（量化豁免/原生 dtype） | 组合算子 |
|---|---|---|---|---|---|
| ① Schema | 跳过 | 跳过（复用） | **做** | **做** | 跳过 |
| ② Parser | **做**（返 `ops::Activation`） | **做**（返所复用 op 类） | **做** | **做** | 通常跳过 |
| ③ Populate | 跳过 | 跳过（复用） | **做** | **做** | 跳过 |
| ④ Infer | 跳过（复用 `REG_INFER(Activation, ...)`） | 跳过（复用） | **做** | **做** | 跳过 |
| ⑤ Kernel float / 量化int8 / 原生dtype | 查已存在 / 跳过 / N/A | 查已存在 / **按需补** / 按规格补 | **做 / 做** / 按规格补 | **float 仅规格需要才做** / 跳过量化int8 / **按规格补原生dtype** | 跳过 |
| ⑥ OpCoder float / 量化int8 / 原生dtype | 加 `case` | **补缺失 / 按需补** / 按规格补 | **做 / 做** / 按规格补 | **float 仅规格需要才做** / 跳过量化int8 / **按规格补原生dtype** | 跳过 |
| ⑦ 量化器列表 | 查 `support_activation_` | **按需补，但先证明 ⑤/⑥ int8 已正确** | 加 `support_int8_ops_`，但先证明 ⑤/⑥ int8 已正确 | 不适用（仅量化豁免；不影响原生 dtype 注册） | 不适用 |
| 融合 pass（构造型/开关3） | 跳过 | 跳过 | 跳过 | 跳过 | **做** |

> **开关3′「图消除/重写 pass」与本表的列正交**：它不改 ①-⑦ 的「做/跳」（命中后 ①-⑦ 照所在列做），只追加两项义务——读懂触发条件 + step7 双情形用例（见 decision3 开关3′）。任意列的算子只要 scan ⑧「消除/重写型」段非空就触发，与上面的算子分类无关。

## step3 分析链路并列能力清单

step3 产出四样东西，逐份落盘 `<opdir>/docs/`，并把能力清单冻结到 `capability_checklist.json`。

step3 结束前必须跑产物闸门（`--framework` 按 step0 范围逐个传）：

```bash
python3 <skill>/scripts/gate_artifacts.py --opdir <opdir> --op <Op> --stage step3 --framework onnx
```

只有输出 `ARTIFACT_GATE=PASS` 才能把 step3 标 `[x]` 或进入 step4；失败时先补齐/修正落盘产物，不许用对话里的表格代替文件。

### 1. 框架对应关系表 → `docs/spec.md`

证据**照抄 scan 的 fetch_op_spec 裁决**：

| 框架 | 算子名/builtin | 查证证据 | → PrimitiveType |
|---|---|---|---|
| ONNX / TFLite | <名> | FOUND@... / NOT_FOUND（→不建 parser/用例） | <PrimType 或 N/A> |

- step0 已排除的框架在表中写「范围外（未查证）」即可，不必给存在性裁决。
- **`UNREACHABLE` ≠ `NOT_FOUND`**："取不到"不得翻译成"无此算子/不建用例"，范围内框架 UNREACHABLE 仍按 decision1 兜底问用户。

### 2. 链路分析表 → 先呈现对话，再落盘 `docs/link-analysis.md`

**这张表是 step3 门控产物，和 step2 决策总结表一样必须在对话正文贴出**（只落盘不展示不算完成 step3）。它与 step2 决策表是**同一批层的两个视图**——step2 给「做/跳」决策（粗粒度通用矩阵），step3 给「可达性 + `文件:标识`」落地（细粒度、本算子专属）。两表**行序必须一致、逐行可对照**：step3 按下表把 step2 的合并行**固定展开**，不得临时增删行或改顺序（缺失/不适用的层也保留该行，标 ❌/➖）。

| step2 决策行 | step3 链路行（固定展开） |
|---|---|
| ① Schema | ① `ops_def.cc` · ①′ `ops::<Op>` · ①″ `ops_func_declare.h` · ①‴ `ops_utils.cc` |
| ② Parser | ② Parser |
| ③ Populate | ③ Populate · ③′ Parameter(`nnacl_c` 结构体) |
| ④ Infer | ④ Infer |
| ⑤ Kernel float / 量化int8 / 原生dtype | ⑤ Kernel float · ⑤ Kernel 量化int8 · ⑤ Kernel 原生dtype/base |
| ⑥ OpCoder float / 量化int8 / 原生dtype | ⑥ OpCoder float · ⑥ OpCoder 量化int8 · ⑥ OpCoder 原生dtype/base |
| ⑦ 量化器列表 | ⑦ Quantizer |
| 融合 pass | Fusion pass |

每个 step3 链路行标 **✅已有(且可达) / ❌缺失 / ➖N/A** + `文件:标识`，并在表后单列出所有 ❌ 环节。

- **emoji 跟可达性走，不跟文件存在性走**：定义点在、但未注册进本目标路径（pass 只挂 GE 流程、CPU converter 不跑、infer 缺 REG_INFER）= 不可达 = 标 ❌（按缺失计）。
- **标「已有」须给两处证据：定义点 + 注册/可达点**（kernel 在哪个注册表、optimizer pass 在哪条 pipeline 挂载、infer 的 REG_INFER）。文件存在但未注册进本目标路径 = 不可达，按缺失计。
- ⑤ 标「已有」前看 scan 的 ⑤′ 段：kernel 存在但无 int8 处理 → 标「已有(仅fp32)」，int8 分支列入缺失。
- **异常信号**：③ 只命中 `custom_populate.cc` 或 ⑥ 是 `REG_BUILIN_CUSTOM_CODER` → Custom 捷径，按红线 1 改造。
- 复用分支要对被复用的 PrimType **再跑一次 `scan_op.sh`**。

### 3. 能力验收清单 → `scripts/capability_checklist.json`

从 decision1 语义摘要 + decision2 裁决**逐条列出本算子必须支持的形态**（形状模式 × fp32/int8），每条标三个落点：① 承载的 nnacl_c 函数；② infer 是否感知（✅/❌）；③ 对应 hs-verify-op 用例。此后三处回查：每层写完回填落点；**启动编译前清单上不得有标「需新增」却无落点的能力**；写 op_spec 时每条能力 ≥1 用例。

**落盘规则（路径只此一处，落错等于没落）：**

- 冻结落盘 `<opdir>/scripts/capability_checklist.json`（`<opdir>` = `$MSLITE_OP_OUTPUT/<op>`，与后续 hs-verify-op `op_spec.py` 同处一目录）。**严禁落到 mslite 源码树或 vendor/ 等工作区**，落错位置 hs-verify-op 的覆盖闸门读不到。
- **别凭记忆手写 schema**：从 `<hs-verify-op>/scripts/capability_checklist.template.json` 拷贝改写。
  > 实证：手写曾把 `framework`/`framework_scope`、`all_equal`/`value_domain`、空 `covered_by` 写错，连烧 3 轮 hs-verify-op 才对齐。
- 每条 `{id, desc, covered_by:[用例id], match?:{param:value}}`。这是 hs-verify-op 的机械对账依据；step7 验证时 harness 校验每条能力都有 covered_by 通过用例，未覆盖即非绿。
- **非平凡能力必须写 `match`**：凡能力描述里出现 dtype、shape/rank、axis、stride、pads、dilation、group、可选输入、broadcast 形态等可参数化约束，都要在 `match` 写出关键参数（如 `{"dtype":"uint8"}`、`{"stride":2}`、`{"pad":"SAME_UPPER"}`、`{"group":8}`）。空 `{}` 只适合无法由 params 机械表达的总体验收行；不能用空 match 让任意 case id 冒充覆盖。
- **禁止 proxy 覆盖**：`covered_by` 只能指向实际满足该行 `match` 的 PASS 用例；不得用普通 case 代理 depthwise、rank、batch、dtype、stride/pad 等不同能力，也不得把失败/未实现能力改写成「已知缺陷 ACK」后仍填 unrelated case。确需缩范围只能经用户裁决并让 VERDICT 留 `ACK_REDUCED`。
- **原生整型算子能力清单按 dtype 列分**：如果规格支持 `int8` 和 `uint8`，至少分别有能力行和用例；如果还有 `int32/int64/bool`，同理。量化 INT8 豁免不合并这些 dtype。
- **清单是单向真值**：回填/调试时只能以它为准改 op_spec，**绝不反向改 JSON 去贴合存量用例**。
  > 实证：弱会话曾把「大 shape×中间轴」行悄悄换成存量 axis=-1 形状，路径实际无用例却显示全覆盖。
- 确需修订某能力行须标「计划变更（原 X→现 Y，理由）」呈用户裁决。
- **decision3 开关3′ 命中（本算子被消除型图 pass 删除/重写）的算子，能力清单必须显式分两组**：① **「pass 不触发、算子到达 kernel」**至少一行（按 step3 读懂的存活条件构造形态，如「非图输出」「多消费者」），其 `covered_by` 是 ⑤/⑥/⑦ 与 INT8 genuine 的唯一真实落点；② **「pass 触发、算子被合法删除」**一行，desc 注明这是合法 no-op、`covered_by` 用例只验「模型整体输出正确」，并标注 `{"note":"op_removed_by_<pass>"}`——**严禁拿这行去声称 kernel/genuine 覆盖**。两组都缺 = 该算子 step7 等于在被改写的空图上假绿。

### rank 上界一致性（本项目实测上限通常 4D）

本项目 MCU 算子的固定长 shape 数组普遍按 `DIMENSION_4D` 开；新算子无特殊需求就以 4D 为上限，能力清单「最大 rank」一行按真实上限写（一般即 4D，由现有 4D 用例覆盖），**不必硬撑 8D**。要守的不变量与上限取值无关，**两条独立判据**：

- **① 同常量**：infer / runtime kernel / nnacl kernel / OpCoder 各层的 shape 数组维度与 `> DIMENSION_xD` 守卫取同一个 `DIMENSION_*` 常量。
- **② infer 是权威上界闸门**：超过上限的 rank 必须在 infer **显式 `return` 报错**（不得静默截断/越界算错；被吞 = 拿残值算错，比崩溃更糟），**且每个 `[DIMENSION_xD]` 定长数组的填充循环前都有 `> DIMENSION_xD` 守卫**（infer 是第一道闸，每个写数组的 kernel/coder 是第二道）。

**判据 ① 与 ② 互不蕴含**：各层常量都相同（① 满足）仍可能越界，只要 infer 没设闸、且写数组的循环前没守卫（② 违反）。

- **反例 A（常量不一致，违反 ①）**：infer 放行 `DIMENSION_8D` 而 int8 数组只开 `DIMENSION_5D`，4D 全绿、6D 模型 infer 过、kernel 才静默算错。
- **反例 B（常量全 4D 却仍越界，违反 ②）**：infer 用 `SetShapeTensor` 同形传播、无 rank 守卫，nnacl fp32 kernel 的 `input_shape_[DIMENSION_4D]` 数组在 `InitHardmaxParam` 里按 `for i<n_dim` 直写、填充前无守卫；各层常量都是 4D（① 满足），但 5D 模型 infer 放行、fp32 校准期数组越界。

这条不变量靠 `quick_check.sh` 的 rank advisory（非阻塞预检）暴露。hs-verify-op 只能确认上限本身端到端可用，测不到"超界应报错"（用例都 ≤ 上限），故跨层一致性归预检管。advisory 现覆盖三类：(1) 多常量不一致；(2) 数组在、同 stem 单元无守卫（反例 B 的 kernel 侧）；(3) 存在无守卫数组层时 infer 也漏设闸（反例 B 的 infer 侧）。**advisory 命中即按缺陷处理，不得因"用例全 ≤4D 跑绿"放行。**

### 4. 输入形态 → 实际 builtin 探针表 → `docs/builtin-probe.md`

目标算子与同族 builtin 并存（如同一操作的非广播版/广播版）或疑似 converter 按形状归一化时，**每类形状形态各转一个最小模型并解包核对 builtin code**（命令见 `references/decision2-reuse-decision.md`），把映射表列进 decision4。它决定每个 builtin 的真实输入域（不跑会把不可达形态当需求、把真实需求分错家），并且是 step7 完成声明的必备证据。**缺这张表时 decision4 不算呈现完整**。

> **证据硬定义**：表中每行附本会话解包命令的实际输出（形状 → 打印出的 builtin 编号）。"验证方法"列只写方法名、引用文档、或按 raw_op 名推断，都不是证据 = 探针没做。"两 builtin 各自独立可达 / 不存在归一化"恰恰是探针要证明的命题，不得以该断言豁免探针。

## step4 编写算子代码

**动手前确认**：属性审计已填好；上游/业界参考实现已读、算法笔记在手边；decision4 链路分析表已展示给用户。

**先冻结实现契约**：写任何 ①-⑦ 代码前，落盘并展示 `<opdir>/docs/implementation-contract.md`。它至少包含这些小标题：`source_entries`、`primitive_type`、`input_contract`、`optional_inputs`、`attribute_contract`、`layout_contract`、`dtype_contract`、`output_contract`、`verification_mode`、`unsupported_or_deferred`。原生整型/索引/布局敏感算子必须在这里写清外部 layout、内部 layout、输入/权重 dtype 矩阵、optional input 是 initializer 还是 dynamic input、输出 dtype、hs-verify-op 路径含义。然后跑：

```bash
python3 <skill>/scripts/gate_artifacts.py --opdir <opdir> --op <Op> --stage pre-code --framework onnx
```

只有输出 `ARTIFACT_GATE=PASS` 才能写代码。后续 parser/infer/kernel/coder/op_spec 与契约冲突时，先修契约并重跑闸门，再改代码；不得边写边临时发明 layout/dtype 规则。

- **「对照模板」的硬定义：动笔前打开实现指南对应小节，以模板为底稿改名填空（不是写完再纠错）。** 凭印象写的返工是整文件级的（签名/目录/量化接口起笔即错）。INT8 另读 `references/int8-coder-conventions.md`（多输入重量化 §9：**int8 函数签名必须带各输入/输出 scale/zp**，按 ⑤‴ float-ratio 模板，**无量化参数的签名 = 字节拷贝 = bug**）。

- **计算路径变更前呈现参考实现对比表**：凡新增、修改、启用或接管 ⑤ runtime kernel、⑥ OpCoder、⑦ `support_int8_ops_` / `support_activation_` 的计算路径，都先做对比；只改 parser/属性转发且不影响计算可跳过。来源至少含：源框架/业界实现（优先 onnxruntime、tflite-micro、TensorFlow Lite 等与 source entry 对应者）+ 仓内相似算子；逐源记「算法要点 / 边界情况 / 采纳或不采纳理由」，不可达记 UNREACHABLE，仓内行不得为空。上游源无本地克隆时**用 `python3 <skill>/scripts/fetch_ref_impl.py --op <Op>` 取材**（镜像链联网，缓存到 `/tmp/ref_impl/` 供 Read，Bash timeout 设 300000）。**禁止**直接 WebFetch/curl `raw.githubusercontent.com`，**禁止**自写内省脚本或凭记忆补"算法要点"。算法核心可选优；工程骨架（注册宏/目录/量化接口）一律按实现指南，不在选优范围。

- **⑦ 不是一行开关**：`support_int8_ops_` 表示允许 full quant 把该 op 标记为 int8；`per_channel_ops_` 只表示权重量化时采用 per-channel 粒度，不能当作 int8 计算已支持的证据。把 op 加进 `support_int8_ops_` 前，必须在链路分析表中同时给出 ⑤ int8 runtime 注册、⑥ int8 coder 注册、生成代码依赖 `Collect()`、量化参数传递/重排逻辑、以及最小 int8 精度探针的证据。缺任一项时结论写「per-channel 权重量化策略已有，full int8 未开放/未证明」，不得写「唯一缺失 support_int8_ops_」。

- **写 ② 前完成属性审计**：规格全部属性逐条标「支持并转发 / 暂不支持（parser 注释写明）」。对每个 opset 有变化的属性**分列两类，不可混为一谈**：
  - **(a) 仅默认值变化**（如某属性 default 从 1 变 -1，但语义函数不变）——影响小。
  - **(b) 计算语义变化**（同一属性在不同 opset 下结果不同，如 Hardmax 的 axis：opset≤11 是"沿 axis flatten 成 2D 后整行取 max"、opset≥13 是"逐轴取 max"，同输入算出不同结果）——必须在呈现中**单独高亮**，因为按最新 opset 实现意味着旧 opset 模型会被算出与原框架不同的结果。

  **opset 策略（项目裁决）：默认值与语义一律按最新 opset 实现，不做 opset 分支、不拒绝旧 opset 模型。** scan 的「opset 版本史」段报告有差异时，parser 加一行注释留痕：`// Project policy: parse per opset <N> semantics regardless of model opset.`，(b) 类语义差异另在注释写明两版语义差异事实（仅陈述事实）。**注释只许写这条策略事实，禁止编造技术依据。**
  > 实证：弱会话曾在 parser 注释里臆造"旧 opset 模型会序列化显式属性值"来论证写死默认值安全；ONNX 不序列化等于默认值的属性，该断言不成立。证据标准见 `references/spec-sources.md`。

- **只参考** `parser/onnx/`、`parser/tflite/`、标准 `populate/`；**不要**参考 `parser/caffe/`、MindIR（`tools/converter/import/`）、`adapter/dpico/`。
- **参考算子选型**：逐元素二元看 `arithmetic_fp32`，一元/激活看 `activation_fp32`，归约看 `reduce_fp32`，形状操作看 `transpose_fp32`，卷积/池化/矩阵看同名 kernel。落笔前用 scan 结果确认真实文件名。

## step5 编译前预检

```bash
bash <skill>/scripts/quick_check.sh <代码根>
```

- **预检 FAIL 清零才许构建**（语法错误在预检层是秒级，漏进构建一轮 10-30 分钟）。
- `SCHEMA_PENDING`/`UNVERIFIED` **不阻塞**：新建 PrimType 的 schema 生成类型要到构建期才产出，脚本已自动识别。不要试图在预检层修它，也不得借它先例放行真 FAIL。

## step6 编译构建

```bash
nohup bash <skill>/scripts/build_mslite.sh <构建根> >/dev/null 2>&1 &
bash <skill>/scripts/build_mslite.sh --wait 540    # Bash 工具 timeout 设 600000；返回 10=到时仍在构建 → 再跑一次 --wait
```

- 日志由脚本自写 `/tmp/mslite_build.log`，**勿自行重定向**。
- 构建**只经 `build_mslite.sh`**（含并发锁、env、工具链探测、交叉库断言）；判进度只用 `--status`；要改代码先 `--stop`。
- **禁止自拼 `sleep N && --status` 链**（sleep 算术屡次出错）。
- **改码后重建 = 重跑同一条 `build_mslite.sh`**（默认增量 + 构建后自动重解压），**禁手敲 `build.sh`/`tar`**；手动解压会跑出陈旧包致假结论。
- **新增了源文件（不只是改）→ 先 `touch` 对应目录 `CMakeLists.txt` 再构建。** nnacl_c 用 `file(GLOB ...)` 收源，GLOB 只在 configure 期展开；增量 make 不重配会让新 `.c` 静默不编译（链接缺符号或用旧对象出假结论）。复用既有文件名时无此问题，仅新建文件需要。
- 脚本报"未找到工具链" → 唯一动作是**问用户要路径**（x86-only 退化 = 没验证）。失败时报错文件不是本会话改的 → **停下报告用户，不顺手修无关文件**。
- **修编译错误不丢功能**：只许最小改动（补 include/改签名），**禁止删功能分支换编译通过**；重写过的文件立即对照能力清单核对每条能力代码仍在。
- **`build_mslite.sh` 报 `[SUBMOD-LOCK] exit 7`（子模块漂移）= 硬停信号，不是算子缺陷。** 成因是 `build.sh` 的 `update_submodule` 跑了 `git submodule update --init --remote` 把 `mindspore` 推进到上游新 commit（converter 行为随之漂移，之前全绿用例成片报错，甚至报 `gen_lite_ops.h: No such file`）。处置照脚本提示：把子模块 `checkout` 回构建前 SHA、注释 `build.sh` 第一处 `update_submodule` 调用后经本脚本重建。**禁止 `git checkout` 别的 commit / `git stash` 反复试**，仍异常即报告用户。

细则与链接失败分诊见 `references/build-and-toolchain.md`、`references/troubleshooting.md`。

## step7 验证精度

- **hs-verify-op 前先过三闸门**（`--framework` 按 step0 范围逐个传；`MSLITE_PKG` 用 step6 输出）：

```bash
python3 <skill>/scripts/gate_artifacts.py --opdir <opdir> --op <Op> --stage pre-verify --framework onnx
python3 <skill>/scripts/validate_op_spec.py <opdir>
python3 <skill>/scripts/check_build_freshness.py --code-root <代码根> --mslite-pkg "$MSLITE_PKG"
```

任一闸门 FAIL 时，先修闸门指出的问题，不启动 hs-verify-op、不引用旧 `verify_summary.txt`。`check_build_freshness.py` FAIL 表示包比源码旧，必须回 step6 重建；手动解压/裸跑 `build.sh` 的结果视为不可信。
- **编译成功后立即自动调 `hs-verify-op`，不等用户要求。** 完成判据见红线 3 与上文「完成判据」。
- **完成判据按 implementation unit 计，同时按 source entry 查覆盖**：每个 unit 各自一行 VERDICT 全绿；合并了多个 source entry 的 unit，`framework_scope` 与 PASS 用例必须覆盖每个框架入口，一个框架入口全绿不覆盖另一个。**同族多 builtin / converter 会按形状归一化的算子，完成声明须附「输入形态 → 实际 builtin」探针证据**，因为 converter 可能把用例悄悄归一化成别的 builtin。
- **任何 FAIL 都是缺陷**：先 fp32 隔离（无量化噪声）；fp32 过而 INT8 不过 → 回实现指南 ⑤‴ 模板修 int8（不在错误方案上叠特判）。**禁止合理化为"量化固有限制/退化输入无意义/存量代码局限"。**

**系统性失败硬停**：出现以下任一信号，不进入普通“改一处再试”循环，先写诊断摘要：`0 PASS`、`HARNESS_EXIT=1`、`capabilities=0/M`、`EXITED_NO_VERDICT`、`OP_SPEC_GATE=FAIL`、`BUILD_FRESHNESS=FAIL`、reference/build 阶段失败、converter 包旧于源码、**之前全绿/与本算子无关的成片用例同时 converter 报错**。诊断摘要必须列出：首个失败原文、失败层、是否为 op_spec/契约/构建新鲜度问题、下一步最小修复。没有这份摘要就继续改 kernel/infer = 盲试。

**成片回归 = 先查环境，不查算子**：当失败面远超本算子改动可能影响的范围（多个无关用例、之前 PASS 的用例、converter 一启动就崩），第一步是**核对 `mindspore` 子模块未漂移**——`git -C mindspore rev-parse HEAD` 与上一次构建前 SHA 对比，或看 `build_mslite.sh` 是否报过 `[SUBMOD-LOCK]`。子模块被推进 / 包旧于源码 / 报错文件非本会话所改，都属环境问题：停下报告用户，**禁止改 parser/kernel/infer，禁止 `git checkout` 子模块到别的 commit、`git stash`、反复重建试错**（红线 4）。

**FAIL 修复循环**（固定步骤，①-③ 没出现在对话正文就动代码 = 盲试，返工）：

1. 粘贴该用例 `output/<fw>/tc<id>/<path>/stderr.log` **首个错误行原文**，指明故障层（converter/codegen/交叉编译/运行时数值）。
2. 查 `references/lessons.md` 当前阶段症状表，声明命中条目或「未命中」。
3. 呈现根因 + 最小修复方案。
4. 改码 → step5 预检 → step6 构建 → 重跑 hs-verify-op。

**同一能力连续 2 个方案失败 → 强制停下**，向用户呈报根因分析与方案选项（继续攻坚 / 经裁决列为覆盖缺口），等待用户决定。自行删用例缩范围、或换第 3 个未经根因分析的方案，都不合法。

### 存量缺陷修复 playbook（复用分支必读）

decision2 判「复用」**不等于**「任务已完成、step7 只是走过场」。hs-verify-op 暴露的缺陷，定位并修好它就是本次实现的**主体工作**。先把缺陷分两类，分别处置：

| 缺陷类型 | 典型信号 | 处置 |
|---|---|---|
| 结构 / codegen 缺陷 | 生成 `.c` 编译失败、重复定义、`args` 重定义、符号缺失 | 读生成代码定位 → 改 OpCoder/模板（多为机械修；弱会话已能修 batch>1 这类） |
| 数值 / 精度缺陷 | fp32 cos<0.999 但能跑通（如 output_padding cos=0.77） | **走下面的数值缺陷根因法**，不得以"根因较深""存量已知"搁置 |

**数值缺陷根因法（fp32 cos 偏低、无量化噪声）——cos<0.999 时强制执行；①-⑤ 没出现在对话正文就改码 = 盲试：**

1. **缩到最小复现**：留一条触发该缺陷的最小用例（小 shape、单一可疑属性），确认 fp32 路径稳定复现 cos 偏低。
2. **取参考实现**：`python3 <skill>/scripts/fetch_ref_impl.py --op <Op>`（onnxruntime/tflite-micro 对应 kernel）；Read 被复用的仓内 ⑤ runtime kernel 与 ⑥ OpCoder 计算路径。
3. **逐段对算**：把可疑属性（output_padding/dilation/group…）在参考实现与仓内实现里的处理逐段对照，定位**第一处发散的计算**（哪个下标 / 边界 / 累加被算错或被忽略），以 `文件:行 + 两边公式` 写进对话。
4. **最小修复**：只改发散那一处，不旁路、不加特判掩盖、不退化成 fp32。
5. **重验证**：step5 预检 → step6 重建 → 重跑该用例 → 再放开全量用例。

只有走完 ①-⑤ **仍无法定位或无法在不破坏其它用例前提下修复**，才可把该形态作为「候选覆盖缺口」呈用户裁决（VERDICT 留 `ACK_REDUCED`），且必须附第 3 步的对算证据。**"根因较深"本身不是证据，是没做第 3 步的代名词。**

### FAIL 之后禁止征求"是否继续"

hs-verify-op 跑出任一 FAIL，**就是继续进入 FAIL 修复循环的授权**——不要停下来问用户"要不要继续深入修复 / 要继续吗"。那是把本属于本次任务的工作退回给用户，也是本 skill 要消除的主要摩擦。合法的停下只有两种，且各自带强制证据，不能只写一句反问：

- 命中上文「系统性失败硬停」信号 → 先写诊断摘要（含「证据闸门」要求的命令输出）。
- 「同一能力连续 2 个方案失败」→ 呈报根因分析与方案选项。

求许可有两种形态，都禁止：一是直接问"要继续吗"；二是 FAIL 未清零却用「完成/最终状态」的任何变体收尾（见「完成状态闸门」），把活悄悄退回用户等其催"继续"。换标题、加括号 hedge 与直接发问同性质。

> 实证：弱会话修好 batch>1 后，对 output_padding 精度缺陷只写"要继续深入修复吗？"就停了；另一轮则在 `HARNESS_EXIT=1` 时写"最终状态：✅ 完成"。两者都 FAIL 未清零，都逼用户回一句"继续修复"才解锁——正是要消除的来回。

### 红旗：以下念头出现即"正在放弃存量代码"，停，回根因法

| 念头 | 现实 |
|---|---|
| "这段 kernel 不是我写的" | 复用分支下它就是本次实现的代码（decision2 复用 = 接管 ①-⑦ 存量代码）。 |
| "根因较深 / 留待后续" | 没走完数值缺陷根因法 ①-⑤ 不算查过根因；"深"是做下去的理由，不是停下的理由。 |
| "riscv_int8 全 ERR，肯定是环境" | 先过证据闸门：贴 `nm`/`grep` 符号查找结果与子模块 SHA；很可能是要补的 ⑥int8 缺口。 |
| "fp32 都过了，就 output_padding 差一点" | fp32 cos<0.999 是确定的数值 bug，不是"差一点"；按根因法定位发散点。 |
| "group>1 转换器不支持，删了用例" | 未贴 converter 报错原文不得断言不支持；删用例触发 `CASES_REDUCED`，须用户裁决。 |
| "要继续深入修复吗？" | FAIL 即继续的授权；问这句 = 在 FAIL 上停下 = 违规。 |
| "先写个'最终状态'，剩下的标为后续" | `HARNESS_EXIT≠0` 时任何"完成/最终/达标"措辞（含换标题、括号 hedge、✅）都是未完成的形变绕过，见「完成状态闸门」。 |

验证用例归 hs-verify-op 管，按其说明新建项目。

## 结案检查清单

- [ ] decision2 裁决有据：新建分支已呈现候选排查 + 逐项不等价证据。
- [ ] 属性审计、融合审计（grep `tools/optimizer/`）、参考实现对比表均已呈现。
- [ ] Parser 已注册且算子名/builtin 与规格逐字一致；激活子类型返回 `ops::Activation`。
- [ ] （新 PrimType）①‴ `REG_MINDSPORE_OPERATOR` 已注册；独立 `XxxParameter` 结构体且 `OpParameter op_parameter_` 为首字段。
- [ ] ⑤-⑥ 与 parser 用同一 `PrimType_*`；浮点输入/需量化的算子已注册 float kernel（全量化校准必需）；原生整型-only 算子不伪造 fp32 路径，按规格逐 dtype 注册 kernel/coder。
- [ ] 量化 int8 通路：签名带量化参数并逐输入重量化（⑤‴）；运行时 int8 LiteKernel 的 `Prepare()` 以 `return ReSize();` 收尾（shape 派生态不能只放 `ReSize()`，bias_correction 不保证其先于 `Run()`）；参考算子按结构族选、只抄骨架不抄数值（序关系算子勿照搬 softmax 的输入重量化/定点乘数）。
- [ ] 原生 dtype 通路：不臆造 scale/zp/量化器列表；`int8/uint8` 数值计算不放 `fp32/`，跨 dtype coder 放 `opcoders/base/`；condition/index 首输入算子只有单注册键（⑤″），内部按数据张量 dtype 分支。
- [ ] （改造存量 kernel）全执行路径审计：每条输出写入路径（dtype 分支/单元素快路/memcpy 搬运）对 int8 要么重量化要么不可达；无同键第二注册。
- [ ] 防御性代码未因抄模板丢失（rank 上界两条判据都过，详见 step3「rank 上界一致性」）：① 同常量；② infer 显式拒绝超界 rank + 每个 `[DIMENSION_*]` 数组填充循环前都有 `> DIMENSION_*` 守卫；`quick_check.sh` rank advisory 命中 (1)/(2)/(3) 任一即按缺陷处理；`Init*/Resize/Prepare` 返回值全部传播，无被吞的校验。
- [ ] 模板残留清理：抄参考算子（如 softmax）模板带来的字段若本算子未用即删；infer 的输入/输出计数校验按真实 arity 选宏。
- [ ] （广播类）按实现指南 ⑤⁗：优先复用 nnacl 既有广播设施；快路守卫逐输入成立；禁 `i % num` 近似。
- [ ] OpCoder `Collect()` 列全 `.h`/`.c`；新增的每个 serializer `CodeStruct` 重载都对应 nnacl 函数确实接收该结构体指针；⑦ 量化器列表已更新；无魔数；新文件版权年用 `date +%Y`。
- [ ] 能力验收清单逐条闭环（每条有落点 + 有 PASS 用例）；`capability_checklist.json` 已落盘且 VERDICT `capabilities=N/M` 满 N=M（无 `[UNCOVERED]`）。
- [ ] 编译成功 + hs-verify-op 全绿，**每个 implementation unit 各一行 VERDICT**，且 `framework_scope` 覆盖 step0 范围内全部 source entry（2D/小4D/大4D/batch>1 及有意义属性组合全 PASS；多 builtin 场景附「形态→builtin」命中证据）。
- [ ] **`git diff` 终审**：每个改动文件可映射到能力清单或某 PASS 用例；试错废案已还原；放开过的入口守卫，其暴露出的路径要么有 PASS 用例，要么连守卫一起还原。
- [ ] **格式化**：编辑过的 `nnacl_c/**` 与生成的 `net0.c` 用 mindspore-lite 自带的 `.clang-format`（`<代码根>/.clang-format`，LLVM/IndentWidth 4）跑一遍 `clang-format -i --style=file <files>`。

## 索引

| 文件 | 何时用 |
|---|---|
| `scripts/scan_op.sh` | step1 开工第一条命令（存在性 + 语义摘要 + 多 opset 版本审计 + 链路扫描 + decision2 候选 + ⑧ 融合/图改写审计） |
| `scripts/fetch_ref_impl.py` | step4 写 ⑤ 前，联网取 onnxruntime/tflite/tflite-micro 参考 kernel 源（镜像链防墙，缓存 `/tmp/ref_impl/`） |
| `scripts/gate_artifacts.py` | step3 / step4 前 / step7 前的产物闸门：检查 `decision.md`、`spec.md`、`link-analysis.md`、`implementation-contract.md`、`capability_checklist.json`、`op_spec.py` 是否真实落盘且覆盖 op/framework |
| `scripts/validate_op_spec.py` | step7 前验证 `op_spec.py` 机械正确性：用例 id 覆盖、ONNX dynamic input 数量、initializer 声明、`auto_pad`/`pads` 冲突 |
| `scripts/check_build_freshness.py` | step7 前验证 packaged `converter_lite` 不旧于本次 dirty 源码；FAIL 必须回 step6 重建 |
| `scripts/quick_check.sh` / `scripts/build_mslite.sh` | step5 预检（`-fsyntax-only` + nnacl_c 头 extern "C" lint + rank 上界 advisory 三类）/ step6 编译唯一入口（`--wait` 等结果，`--status` 即时查看，`--stop` 终止） |
| `references/worked-example.md` | step2 开始时，复用/新建两分支端到端范例 |
| `references/decision2-reuse-decision.md` | decision2 详细流程：候选四层来源、可达性探针、同义词簇维护 |
| `references/implementation-guide.md` | step4 每层动笔前，①-⑦ 模板唯一权威 |
| `references/int8-coder-conventions.md` | 写 int8 kernel/coder 前（重量化 §9） |
| `references/spec-sources.md` | 规格/参考实现取材路径与回退链 |
| `references/optimizer-fusion-template.md` | decision3 命中融合时 |
| `references/build-and-toolchain.md` / `references/troubleshooting.md` | step6 编译细则 / 报错→根因对照 |
| `references/lessons.md` | **卡住或想走捷径时按症状查**：历史事故的根因与规则 |
