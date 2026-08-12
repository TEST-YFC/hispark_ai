---
name: hs-workflow-op-development
description: >-
  End-to-end workflow for adapting, adding, porting, or supporting a MindSpore Lite Micro operator on HiSpark.AI, from specification and implementation through host tests, documentation, firmware build, optional flash, and board accuracy. This is the default top-level skill for generic requests such as “适配一个算子”, “新增/支持 xxx 算子”, “port/add/implement an operator”, or any request combining operator implementation with verification, build, flash, documentation, or board testing. Do not use it when the user explicitly asks to use a named stage-specific skill or clearly requests only implementation, only host tests, only documentation, only build, only flash, or only board accuracy.
---

# 算子适配端到端工作流

本 skill 负责编排、跨阶段状态和固件接入准备。必须完整执行模型转换、Micro交叉编译、
adaptor安装、Sample生成、CMake/Kconfig接线、固件构建、烧录和板端精度步骤；各阶段由
明确的专项 Skill（只负责一个确定阶段）或确定性脚本负责，不能压缩成“完成接线”后依靠临场发挥。

```text
stage0 范围/环境冻结
        ↓
hs-design-op-manual (integrated-initial)
        ↓ 文档事实、实现合同、计划用例冻结
hs-dev-op-implement
        ↓ IMPLEMENT_GATE
MindSpore Lite 工具包构建
        ↓ MSLITE_PKG
hs-verify-op-host
        ↓ HOST_VERIFY_GATE
hs-design-op-manual (integrated-final)
        ↓ OP_MANUAL_SYNC
（用户要求且板卡可用）模型接入 → hs-dev-build → hs-dev-flash → hs-verify-op-board
```

## 路由优先级

1. 用户明确点名 Skill，或明确说“只做某阶段”时，优先使用对应的专项 Skill，不启动本 workflow。
2. 用户泛化地说“适配/新增/支持/移植一个算子”时，默认启动本 workflow。
3. 用户同时要求实现与测试、文档、构建、烧录或板测时，必须使用本 workflow。
4. `hs-verify-op-host` 与 `hs-verify-op-board` 不合并：前者在 PC/WSL 中做完整规格矩阵和数值正确性；后者在真实板上验证交叉编译、固件接入、运行通路和硬件输出。两者复用同一 host 用例的模型、输入和 GT，但执行环境、失败归属和成本不同。

### 触发消歧矩阵

工作流优先级按用户意图判定，不按“是否出现算子名称”猜测：

| 用户请求示例 | 顶层入口 | 处理规则 |
|---|---|---|
| “实现/适配/新增 MatMul 算子” | `hs-workflow-op-development` | 默认完整走文档草稿、实现、构建、Host；缺少板测授权时不擅自烧录 |
| “在 WS63 上实现/运行 X 算子” | `hs-workflow-op-development` | 芯片/固件暗示板端接入，先询问或核对 SDK 路径，再走完整流程 |
| “实现 X，只改 MindSpore Lite 源码，不测试、不编译、不写文档” | `hs-dev-op-implement` | 明确只做实现，输出交接信息，不启动 workflow 后续阶段 |
| “只用 hs-dev-op-implement 分析/补 X” | `hs-dev-op-implement` | 用户点名专项 Skill，严格停在该 Skill 的边界 |
| “只写 X 的测试/做 Host accuracy” | `hs-verify-op-host` | 不修改正式算子源码，不构建固件 |
| “只生成 X 的文档” | `hs-design-op-manual` | 不实现、不构建、不运行板测 |

若请求同时包含“实现/适配”与任意“测试、编译、文档、WS63、烧录、板测、完整流程”，
不得降级为 `hs-dev-op-implement`；若用户只说“实现算子”且范围不清，先按完整 workflow
处理，并在 stage0 说明将包含哪些阶段，允许用户明确选择“仅源码实现”后再切换专项 Skill。

## 用户可见阶段

```markdown
状态: stage<n> 进行中
待办:
- [ ] stage0 冻结范围、模式和环境
- [ ] stage1 生成并审计算子文档草稿、实现合同和计划用例
- [ ] stage2 实现/修复算子源码并通过代码审查
- [ ] stage3 构建 MindSpore Lite 工具包
- [ ] stage4 生成并运行 Host 测试
- [ ] stage5 生成终版算子文档
- [ ] stage6 可选：取得用户明确提供的固件SDK位置，接入并构建固件
- [ ] stage7 可选：烧录并做板端精度验证
```

未连接板卡或用户未要求板测时，stage6-stage7 标记“未请求/板卡不可用，Host 验证已完成”，不把它们伪装成 PASS，也不阻塞 Host 侧算子交付。

**后台任务终态硬门禁：只要本轮任一后台任务仍为 `RUNNING`，workflow 就禁止结束当前任务或向用户提交最终答复；`--wait` 返回 10 时必须携带同一 `RUN_ID` 继续等待，直至得到 `SUCCESS` 或 `FAILED`，随后立即向用户通知终态。**

所有后台任务都必须登记 `RUN_ID`、启动时间、日志路径、状态查询命令和终态通知点；前台
必须持续等待或按状态命令轮询，不能关闭承载任务的窗口后继续假设结果。任务失败时必须在
当前会话报告首个真实错误、归属阶段、可复现命令和下一步；任务成功时必须报告终态和本轮
产物路径。历史日志、旧 RC、旧串口输出只能作为背景，不能作为本轮 PASS/FAIL。

## stage0：冻结范围和环境

记录 source entry、implementation unit 候选、代码根、`MSLITE_OP_OUTPUT`、是否要求文档、是否要求板测、板卡是否连接，以及各专项 Skill 的可用性。

在修改算子源码前建立环境控制基线：记录 MindSpore Lite 主仓/子模块 HEAD、dirty fingerprint、当前 `MSLITE_PKG` 及 converter 路径；若已有一条与目标算子无关且 `verify_summary.txt` 明确 PASS 的稳定 Host case，先读取其 `output/<path>/_driver.sh` 中冻结的 `MSLITE_PKG`，用 `realpath` 与当前记录的包逐字核对。路径一致时才可执行 `_run.sh`，确认重新转换、编译、运行和 judge 仍 PASS；路径不一致时必须用当前环境变量和该控制 spec 重新调用 Host harness（至少 x86 路径），不能让陈旧 wrapper/converter 产生 `ENV_BASELINE=PASS`。这一步的作用是把 converter/工具链/子模块故障与后续算子缺陷分开。

没有可复用稳定 case 时记录 `ENV_BASELINE=UNKNOWN reason=no-known-pass-case`，不得伪称环境已验证；后续若多个无关用例在 converter 启动阶段成片失败，先补跑未改动控制用例或重建工具包，不允许直接修改目标算子源码。基线本身失败时记录 `ENV_BASELINE=FAIL` 并停在环境分支，源码保持未修改。

优先保证 PC/WSL 单元/Host 验证可运行。即使没有开发板，也继续 stage1-stage5；不要因烧录不可用而跳过 Host 测试。

## stage1：文档事实和实现合同先行

在任何算子源码修改前，先调用 `hs-design-op-manual mode=integrated-initial`，冻结
`operator-manual-facts.json`、`operator-manual-draft.md`、输入/输出/dtype/属性、暂不支持范围、
复用裁决、能力清单和计划 Host case。草稿必须完成 facts/content/case audit，并由
`hs-dev-op-implement` 的 `gate_artifacts.py --stage step3` 和 `validate_op_spec.py` 复核。
只有 `OP_MANUAL_SYNC=PASS publication=draft`、`ARTIFACT_GATE=PASS` 和 `OP_SPEC_GATE=PASS`
同时成立，才能进入源码实现；实现过程中事实变化必须先更新草稿和合同，再改代码。

### 环境准备分流（不修改外部环境 Skill）

`hs-dev-env-prep` 是外部维护的环境准备专项 Skill；它的默认行为可能同时安装
`fbb CLI`、构建工具链并下载芯片 SDK。算子工作流不得仅因为它存在就直接调用，必须先按
用户意图和已提供路径分流：

| 用户情况 | 工作流动作 | 是否允许调用 `hs-dev-env-prep` |
|---|---|---|
| 只想安装或检查 `fbb CLI` | 只执行 `uv`/`fbb CLI` 安装与 `fbb --version` 检查，然后结束环境准备 | 不调用 |
| 已明确提供 SDK 源码路径，且要编译/上板 | 设置 `FBB_SDK_DIR=<用户路径>`，核对 `src/build.py`、`CMakeLists.txt`、芯片描述和 `fbb describe --json`；只补齐构建环境和工具链 | 仅在用户明确授权“补齐工具链”时调用；必须传入已有 SDK，禁止下载另一份 SDK |
| 没有 SDK，且明确要求编译/上板 | 先说明将下载 SDK、工具链和烧录工具，再调用环境准备专项 Skill 的完整流程 | 允许调用 |
| 只做算子源码、MindSpore Lite 构建或 Host 验证 | 不检查或下载固件 SDK；只使用对应阶段自己的依赖 | 不调用 |

任何环境准备调用前，都必须在状态中记录：用户意图、`FIRMWARE_SDK_ROOT`（如已提供）、
是否允许下载 SDK，以及调用返回的 `fbb describe --json`。如果用户只提供了已有 SDK 路径，
不得把 `fbb sdk install <chip>` 当作默认补救动作；SDK缺失问题应先报告并请求用户授权。

### 专项 Skill 安装地址

`hs-dev-env-prep`、`hs-dev-build` 和 `hs-dev-flash` 使用同一个 Skill 发布目录。当前使用者
缺少其中任意一个时，提示从以下地址安装对应的完整子目录：

```text
https://gitcode.com/HiSpark/hibot-skills/tree/master/skills
```

期望的文件分别是：

```text
<skill-root>/hs-dev-env-prep/SKILL.md
<skill-root>/hs-dev-build/SKILL.md
<skill-root>/hs-dev-flash/SKILL.md
```

安装后必须重新检查当前使用者的 `<skill-root>`，并保留各 Skill 的 `references/`、
`scripts/` 等配套资源；不能只下载一个 `SKILL.md` 作为已安装判据。

### 环境准备 Skill 的可用性门禁

该门禁针对每一位使用者自己的 Codex/Skill 环境在 stage0 执行。通知发生在该使用者
发起本次算子工作流的当前对话中，而不是串口、WSL 后台任务或开发板上。分发本 workflow
不会自动分发外部 `hs-dev-env-prep`；每位使用者需要在自己的 Skill 集合中安装它，或在
已有 `fbb` 环境满足检查时直接使用 CLI/构建专项 Skill。

1. 若用户只要求 CLI、算子源码、MindSpore Lite 工具包构建或 Host 验证，输出
   `ENV_PREP_SKILL=NOT_REQUIRED`，不检查也不要求加载 `hs-dev-env-prep`。
2. 若用户要求固件编译/烧录，先执行 `fbb --version` 和 `fbb describe --json`，并核对用户给出的
   `FIRMWARE_SDK_ROOT`。两者都通过时，输出 `ENV_PREP_SKILL=NOT_REQUIRED`，直接进入
   `hs-dev-build`/`hs-dev-flash`；“已安装并可用的 fbb 环境”已经满足其前置条件。
3. 若固件阶段需要补环境，尝试加载用户提供或已安装的
   `hs-dev-env-prep/SKILL.md`。加载不到时，必须立即在该使用者当前会话报告：

   ```text
   ENV_PREP_SKILL=UNAVAILABLE
   BOARD_STAGE=BLOCKED
   请先安装 hs-dev-env-prep：
   https://gitcode.com/HiSpark/hibot-skills/tree/master/skills
   期望文件：<skill-root>/hs-dev-env-prep/SKILL.md
   ```

   此时不得假装环境已准备好、不得启动后台 `fbb build`/`fbb flash`，也不得自行下载一份
   外部 Skill。用户安装或提供该 Skill 后，从 stage0 重新检查；不需要重做已通过的 Host 阶段。
4. 若 `hs-dev-env-prep` 可加载但用户已经给出 SDK 路径，调用时必须明确“只补环境和工具链，
   使用该 SDK，禁止再次执行 `fbb sdk install`”；若用户没有 SDK，则先取得其下载授权。

检查 `hs-dev-build` 和 `hs-dev-flash` 是否已安装：

- 已安装：stage6、stage7 分别调用它们。
- 未安装：先告知用户从与 `hs-dev-env-prep` 相同的地址安装：
  `https://gitcode.com/HiSpark/hibot-skills/tree/master/skills`。
  该目录包含 `hs-dev-env-prep`、`hs-dev-build` 和 `hs-dev-flash`；安装后应重新检查
  当前使用者自己的 `<skill-root>`，不得只复制 `SKILL.md` 而遗漏 references/scripts。
- 用户未安装或当前环境不能加载：workflow 可按两者公开契约直接使用 CLI 回退，构建用 `fbb list-targets --json` / `fbb describe --json` 选 target 后执行 `fbb build --clean <target>`；烧录用 `fbb flash <target> --json-summary`，只按最后一行 JSON 的 `success` 和 `error.code` 判定。回退不降低 clean build、target 解析或 JSON 判定要求。

缺少对应专项 Skill 且没有可验证的 CLI 回退时，只阻塞对应阶段，不伪造结果。

若用户要求 stage6、stage7，先检查用户本次请求或当前会话是否已经明确提供
`FIRMWARE_SDK_ROOT=<固件SDK仓库绝对路径>`。没有时必须向用户询问并暂停板端阶段；
禁止通过搜索磁盘、其他任务记录、环境变量或 fbb 自动选择一个可写SDK。该门禁只暂停
stage6、stage7，不阻塞stage1-stage5。用户提供后，记录对应 `FIRMWARE_SDK_SRC`，再检查
对应专项 Skill 是否安装，并执行 `fbb --version` 和 `fbb describe --json`（使用真实 target 时传入
target）。任一命令不可用、路径身份不符或SDK描述失败时，stage6、stage7标为环境阻塞，
并提示用户安装/运行 `hs-dev-env-prep`；不能因为build/flash skill文件存在就假定其隐含
环境已经准备好。

## stage2：实现源码

调用 `hs-dev-op-implement`，传递明确的“只实现/修复源码”范围。只有收到每个 implementation unit 的 `IMPLEMENT_GATE=PASS` 才进入 stage3。

实现阶段若发现测试合同信息不足，补的是 capability checklist 和 implementation contract，不越权代写 Host 结果或正式文档。

## stage3：构建 MindSpore Lite 工具包

这一步构建的是 `converter_lite` 和通用算子库，不是 WS63 fwpkg。它与 stage6 的 `hs-dev-build` 不同，不能互相替代。

使用本 workflow 自有的受控构建资源：

```bash
OP_BUILD_RUN_ID="op-$(date +%Y%m%d%H%M%S)-$$"
nohup bash <hs-workflow-op-development>/scripts/build_mslite.sh \
  --run-id "$OP_BUILD_RUN_ID" <build_root> >/dev/null 2>&1 &
bash <hs-workflow-op-development>/scripts/build_mslite.sh --wait 540 "$OP_BUILD_RUN_ID"
python3 <hs-workflow-op-development>/scripts/check_build_freshness.py \
  --code-root <code_root> --mslite-pkg "$MSLITE_PKG"
```

workflow 必须把 `OP_BUILD_RUN_ID` 写入本轮状态并在后续每次 `--wait`/`--status` 原样传回。`NO_CURRENT_BUILD`、`STALE_BUILD_RECORD` 或 `INCOMPLETE_BUILD_RECORD` 都表示没有可用于本轮的构建结论：重新启动新 run，不读取其他运行日志作 FAIL。用户手工修复环境或源码后继续时，先前源码指纹自动失效，必须生成新 RUN_ID 重建。

构建前由 workflow 重跑 `hs-dev-op-implement/references/code-quality-gate.md`，防止实现阶段之后的修改绕过门禁。构建失败按首个真实错误归属：

- parser/kernel/opcoder/注册或本次源码错误 → 回流 `hs-dev-op-implement`，修复后重跑 stage3-stage4；
- 工具链、包新鲜度、子模块漂移或非本次文件错误 → 保留证据并阻塞，不让 implement 盲改源码；
- 修复后重新执行质量门禁和构建，不复用陈旧包。

基线或工具链失败必须先停在环境分支，不得把它当作算子失败。若用户修复环境后要求
继续，必须创建新的 `RUN_ID` 并重新运行基线/构建；不得仅用 `--status` 读取旧轮次日志，
也不得因为旧失败而跳过新的基线。若 converter 在启动阶段对多个互不相关 case 同时失败，
先报告包版本、help 能力探测、子模块/工具链状态和首个 stderr，再回流环境分支；只有单个
模型在环境基线通过后失败，才归属算子或测试模型。

成功证据是新鲜的 `MSLITE_PKG=<absolute path>`。

## stage4：Host 测试优先

调用 `hs-verify-op-host`，让其依据 capability checklist 编写/对账 `op_spec.py`。在其启动固定 harness 前，检查它已对每个 framework 执行 `gate_artifacts.py --stage pre-verify` 和 `validate_op_spec.py`；只有 `ARTIFACT_GATE=PASS` 且 validator 退出 0 才能运行长测试。Host 是默认和必做验收，即使没有板卡也必须完成。

失败分流：

| 证据指向 | 回流所有者 |
|---|---|
| 用例模型、输入、GT、属性、覆盖映射设计错误 | `hs-verify-op-host` |
| parser/infer/kernel/opcoder/quantizer 数值或可达性错误 | `hs-dev-op-implement`，之后重跑 stage3-stage4 |
| MSLITE_PKG 陈旧、工具链或子模块异常 | stage3 环境分支 |

不要把所有 FAIL 都扔给验证 skill，也不要让 implement 修改固定测试执行器来凑绿。只有 VERDICT 全绿、`HARNESS_EXIT=0` 且 capability 覆盖 N=M，才得到 `HOST_VERIFY_GATE=PASS`。

## stage5：生成文档

Host 全绿后调用 `hs-design-op-manual mode=integrated-final terminal_state=completed`，由文档 skill 从冻结事实生成正式 `operator-desc/{op}.md`。阻塞或硬停时调用同一模式但传 `terminal_state=blocked|hard-stop`，只生成/刷新草稿。

文档失败回流文档 skill 或缺失事实的原 owner；不得在 workflow 中另写一套四章节模板。正式交付要求 facts/content/case audit 与 `OP_MANUAL_SYNC` 均 PASS。

## stage6：可选固件接入与构建

只在用户要求板测且板卡/SDK条件可用时执行。开始前必须显示：

```text
BOARD_SDK_GATE=PASS
FIRMWARE_SDK_ROOT=<用户明确提供的绝对路径>
FIRMWARE_SDK_SRC=<已核对的绝对路径>
chip=<chip>
target=<fbb真实target>
```

本阶段必须完整读取并逐节执行：

```text
<hs-verify-op-board>/chips/ws63/references/sdk-integration.md
```

对于WS63，该reference规定以下完整板测流程：

1. 冻结用户授权的SDK路径、target和SDK Git/dirty基线；
2. 从stage4选择同轮Host PASS case，冻结模型、输入和GT；
3. 调用Board Skill的 `chips/ws63/scripts/build_micro.py`，以固定配置对该模型运行
   converter_lite并生成RISC-V Micro C工程；
4. 由同一脚本使用真实RISC-V工具链交叉编译并冻结 `libmicro_runtime.a`和 `libnet.a`；
5. 从HiSpark.AI既有 `src/adaptor`安装或核对OH_AI CPU adaptor，不整目录覆盖用户代码；
6. 为当前case使用可追踪模型库目录，禁止多个同名陈旧库混链；
7. 以仓库中经过验证的OH_AI Sample/API结构为模板生成板端测试代码，
   写入同一Host输入并打印所有输出的dtype、shape、元素数和完整Data；
8. 调用 `chips/ws63/scripts/integrate_sdk.py`机械接入Sample、adaptor、模型库、CMake、
   Kconfig和target组件，并保存receipt；
9. 构建前执行对象、符号、库哈希和接线消费点检查，得到
   `BOARD_WIRING_GATE=PASS`。

第7项必须运行 `<hs-verify-op-board>/chips/ws63/scripts/prepare_sample.py`，第9项必须运行
`<hs-verify-op-board>/chips/ws63/scripts/verify_wiring.py`；不能用人工阅读或临场生成代码代替
这两个机械门禁。非WS63芯片必须有对应 `<chip>-sdk-integration.md`及确定性脚本后才能
进入本阶段，禁止照搬WS63路径猜接线。

第8项生成的 `ws63_board_env.ps1|sh` 必须在调用 `hs-dev-build`的同一进程中导入。
优先运行同目录的 `invoke_hs_dev_build.ps1|sh`；若顶层保持build Skill委托边界，则先
source环境文件、回显核对 `AI_CUSTOM_SAMPLE_DIR`与 `AI_MCU_MODEL_VARIANT`，再在该
进程调用build Skill/fbb。只生成、查看或在已经退出的另一个shell中source不算接线完成。

不得以新建一个能编译的 `ai_main.c`代替上述流程，也不得在找不到输入时填零、只打印
ArgMax/标签、让任务无限循环，或让Sample用硬编码答案自报最终精度PASS。

随后调用 `hs-dev-build` 生成 fwpkg；它只负责 fbb target 构建。若使用 CLI 回退，先从 `fbb list-targets --json` 或 `fbb describe --json` 获取真实 target，配置变更后强制 clean build。成功证据是新鲜 `*_all.fwpkg`。

构建完成后必须运行
`<hs-verify-op-board>/chips/ws63/scripts/verify_firmware.py`，验证Sample对应 `.c.obj`存在，
最终map包含模型Predict、Execute和目标Kernel，并确认 `_all.fwpkg`晚于本轮源码、配置
和模型库；只有 `FIRMWARE_CONTENT_GATE=PASS`才能继续。`fbb build`退出0但没有这些
证据时，stage6仍为FAIL。

构建错误分流：模型/算子生成代码错误回 stage2，再重跑 stage3-stage4；sample/adaptor/Kconfig 接线错误留在 stage6；工具链错误按 build skill 处理。

## stage7：可选烧录与板端精度

调用 `hs-dev-flash` 烧录 stage6 的固件，只按 fbb 最后一行 JSON 判断烧录。需要板端精度时可让该 skill 使用其公开的 `fbb flash <target> --then-monitor --until <keyword> --timeout <seconds> --json-summary` 链路保存串口文本；缺 skill 时用相同 CLI 契约回退，不直接调用 BurnTool。

不得把上述委托压缩成不可核验的一句话。进入烧录前必须确认 `FBB_SDK_DIR`仍指向用户
提供的SDK、target来自fbb真实列表、输入固件是stage6通过内容门禁的新鲜 `_all.fwpkg`。
端口歧义时让用户选择；只读stdout最后一行JSON并按 `success`与`error.code`分流。
若返回 `DEVICE_NOT_RESPONDING`，必须先问用户是否在板边，得到确认后才调用
`--manual-reset`重试并提示只按一下RESET。烧录成功后采集时间必须晚于本轮烧录，串口
端口和日志波特率必须可追溯；缺任一证据都不能进入板端精度签收。详细执行规则以
`hs-dev-flash`和 `hs-verify-op-board` step5为准，workflow负责确认二者实际执行完毕。

烧录成功不等于板端精度成功。随后调用 `hs-verify-op-board`，传入同轮 Host 用例的 GT、测试输入、串口完整输出和 fp32/INT8 模式，由它输出 `ACCURACY_VERDICT`。

`hs-verify-op-board`必须完整执行板端验证：核对前置产物、确认固件身份、
采集本次烧录后的完整串口Tensor、逐Tensor核对数量/shape/元素数并与同轮GT计算余弦。
不得把“烧录成功”“出现启动日志”或Sample自报PASS当作精度PASS。

没有连接板卡、串口不可用或用户不在板边时，保留 Host 完成状态并将 stage7 标为未执行；不要反复烧录或用其他轮次串口日志冒充本轮板测。

## 完成判据

Host 交付完成必须满足：

- 每个 implementation unit 的 `IMPLEMENT_GATE=PASS`；
- 编码后审查产物 `<opdir>/docs/code-review.md` 已生成，且
  `registration_matrix`、`branch_reachability`、`quantizer_ownership`、
  `folding_and_rewrite_cases` 均有证据，不能存在未处置的 `FIX_REQUIRED`；
- 新鲜 `MSLITE_PKG` 构建成功；
- `HOST_VERIFY_GATE=PASS`；
- `OP_MANUAL_SYNC=PASS publication=final`。

用户明确要求板测时，另需：

- `hs-dev-build`/CLI 构建成功；
- `hs-dev-flash`/CLI JSON `success=true`；
- `ACCURACY_VERDICT=PASS`。

任一必需门禁 FAIL 时首行写 `状态: 未完成`，列出失败阶段、原始证据和回流 owner。未请求的板测不是 FAIL；已请求但因无板卡未执行则是“Host 完成，板端子任务未执行”，不能写成完整板测完成。

## 统一结案报告

```text
OP_WORKFLOW=<PASS|FAIL|HOST_PASS_BOARD_NOT_RUN>
IMPLEMENT_GATE=<PASS|FAIL>
MSLITE_BUILD=<PASS|FAIL>
HOST_VERIFY_GATE=<PASS|FAIL>
OP_MANUAL_SYNC=<PASS|FAIL>
FIRMWARE_BUILD=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
FLASH_VERDICT=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
ACCURACY_VERDICT=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
```

报告同时给出源码 diff、`MSLITE_PKG`、Host summary/Excel、正式文档、fwpkg 和板端日志的绝对路径。只报告真实存在且属于本轮的产物。

## 资源索引

| 资源 | 所有者与用途 |
|---|---|
| `scripts/build_mslite.sh` | workflow stage3 的算子源码后工具包重建、RUN_ID 与子模块/注册断言 |
| `scripts/check_build_freshness.py` | workflow stage3 在进入 Host 前核对源码与解压包新鲜度 |
| `references/build-and-toolchain.md` | stage3 工具链、产物和构建失败分诊 |
| `../hs-verify-op-board/chips/ws63/references/sdk-integration.md` | stage6必须完整读取的WS63模型库、adaptor、Sample与SDK接线规范 |
| `tests/test_build_state.sh` | RUN_ID、源码指纹、陈旧状态和子模块漂移回归 |

这些资源由本 workflow 持有，避免 `hs-dev-op-implement` 托管自己不执行的构建流程。`hs-workflow-mslite-env-setup` 的同名脚本负责通用环境搭建；这里的脚本只服务算子源码修改后的受控重建，调用时必须使用完整 skill 路径区分。
