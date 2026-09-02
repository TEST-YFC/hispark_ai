---
name: hs-workflow-op-development
description: >-
  Orchestrate the complete HiSpark.AI MindSpore Lite Micro operator workflow:
  scope and environment, document-first planning, source implementation, MSLite
  build, Host matrix, firmware, board accuracy, and terminal reporting. Use this
  top-level skill for generic requests to adapt, add, port, support, or run an
  operator, and whenever implementation is combined with tests, documentation,
  build, flash, or board verification. Do not use it for an explicitly named
  stage-only skill or a request explicitly limited to source-only, Host-only,
  documentation-only, build-only, flash-only, or board-only work.
  中文触发包括“生成算子”“实现算子”“适配/新增/支持/移植算子”“完整流程”；仅源码、仅 Host、仅文档或仅板测请求应路由到专项 Skill。
---

# 算子适配端到端工作流

本 skill 只负责跨阶段编排、门禁、状态和交接。每个阶段仍由对应专项 Skill 或确定性脚本执行；
步骤不能被一句“完成接线”替代。入口正文只保留必须始终可见的契约，细节按阶段读取直接链接的
`references/`文件。

## 工作流总览

```text
stage0 范围/环境冻结（只读）
  -> 一次 EXECUTION_CONFIRM_GATE
stage1 prepare -> integrated-initial -> PRE_SOURCE_GATE
  -> stage2 apply -> IMPLEMENT_GATE
  -> stage3 MSLITE_PKG -> stage4 HOST_VERIFY_GATE
  -> AUTO_ALL: stage6 firmware -> stage7 flash/serial/accuracy
  -> stage5 integrated-final -> terminal.report/finalize
  -> HOST_ONLY: stage6/7 = NOT_REQUESTED
```

固定顺序不能交换：`hs-dev-op-implement mode=prepare` 必须先于
`hs-design-op-manual mode=integrated-initial`，后者必须先于
`gate_artifacts.py --stage pre-source`，之后才能
`hs-dev-op-implement mode=apply`。工具包构建、Host、固件和板测的详细命令见各阶段 reference。

## 路由优先级

1. 用户明确点名 Skill，或明确说“只做某阶段”时，使用对应专项 Skill，不启动本 workflow。
2. 用户泛化地说“生成/实现/适配/新增/支持/移植一个算子”时，默认启动本 workflow，
   `BOARD_POLICY=AUTO_ALL`；不能把“生成算子”缩成只写源码或只跑 Host。
3. 请求同时包含实现与测试、文档、编译、WS63、烧录、板测或完整流程时，必须使用本 workflow。
4. `hs-verify-op-host` 负责 PC/WSL 规格矩阵和数值正确性；`hs-verify-op-board` 负责真实板的
   交叉编译、固件接入、串口和硬件输出。两者共用同一 Host 模型、输入和 GT，但不互相替代。

| 用户请求 | 顶层入口 | 处理边界 |
|---|---|---|
| “实现/适配/新增 MatMul 算子” | `hs-workflow-op-development` | 默认完整走文档、实现、构建、Host 和全用例板测；只有明确 Host-only 才跳过板端 |
| “生成 BitShift 算子” | `hs-workflow-op-development` | 默认宣布`AUTO_ALL`，走实现、MSLite 构建、Host、固件和全部 case |
| “在 WS63 上实现/运行 X 算子” | `hs-workflow-op-development` | 核对 SDK；总确认通过且设备可用时自动跑完整矩阵，不再询问是否上板 |
| “实现 X，只改 MindSpore Lite 源码，不测试、不编译、不写文档” | `hs-dev-op-implement` | 只做源码实现并输出交接 |
| “只用 hs-dev-op-implement 分析/补 X” | `hs-dev-op-implement` | 用户点名专项 Skill，严格停在该 Skill 边界 |
| “只写 X 的测试/做 Host accuracy” | `hs-verify-op-host` | 不修改正式算子源码，不构建固件 |
| “只生成 X 的文档”或“用本 workflow 新生成 X 文档” | `hs-design-op-manual` | 已有算子产物使用 `artifact-sync`；不实现、不构建、不运行板测 |

若请求同时包含“实现/适配”与任意测试、编译、文档、WS63、烧录或板测，不得降级为
`hs-dev-op-implement`。只说“实现算子”且范围不清时先按完整 workflow 进入 Stage0，用户可在
唯一确认回复中改为明确的专项范围。

## 用户可见阶段

状态由 `workflow_state.py` 生成，不手工维护第二份清单：

```markdown
状态: stage<n> 进行中
待办:
- [ ] stage0 冻结范围、模式和环境
- [ ] stage0-confirm 展示环境和影响范围，等待一次执行确认
- [ ] stage1 prepare、初版文档和 PRE_SOURCE_GATE
- [ ] stage2 源码实现、代码审查和 IMPLEMENT_GATE
- [ ] stage3 MSLITE_PKG；stage4 Host 全量验证
- [ ] stage6 默认固件矩阵；stage7 默认烧录、串口和板端精度
- [ ] stage5 终态文档；terminal.report
```

## 待办、状态和证据

每次开始生成算子，第一项动作必须是 `scripts/workflow_state.py init`，在
`<opdir>/.workflow-state/<RUN_ID>/` 原子生成
`workflow_state.json`、`workflow_todo.md` 和 `workflow_events.jsonl`。待办模板为
`references/workflow-todo.template.md`，状态机为 `scripts/workflow_state.py`；不要用对话记忆或手工编辑
进度。完整恢复、重试、锁、attempt token 和 fail-closed 规则见
[`references/workflow-state.md`](references/workflow-state.md)。
完整 13 项 task ID 的固定顺序和每项最小证据见模板及状态 reference；初始化时必须整份生成，
不得把任务合并、跳过或改成只在结案时补记。

最小机械契约（所有命令使用同一 `RUN_ID`）：

```text
python <skill>/scripts/workflow_state.py init \
  --state-dir <opdir>/.workflow-state/<RUN_ID> \
  --operator <算子名> --run-id <RUN_ID> --mode AUTO_ALL \
  --sdk-root <用户明确提供的固件SDK绝对路径>
# init 输出 stage0.scope_environment 的 ATTEMPT_TOKEN
python <skill>/scripts/workflow_state.py finish \
  --state-dir <STATE_DIR> --run-id <RUN_ID> --task stage0.scope_environment \
  --attempt-token <INIT_TOKEN> --status PASS --evidence <本轮只读探测绝对路径>
python <skill>/scripts/workflow_state.py confirm \
  --state-dir <STATE_DIR> --run-id <RUN_ID> --phrase "确认执行" \
  --confirmed-mode AUTO_ALL --sdk-root <用户提供的绝对路径>
python <skill>/scripts/workflow_state.py start --state-dir <STATE_DIR> --run-id <RUN_ID> --task <TASK_ID>
python <skill>/scripts/workflow_state.py finish --state-dir <STATE_DIR> --run-id <RUN_ID> \
  --task <TASK_ID> --attempt-token <ATTEMPT_TOKEN> --status PASS --evidence <本轮绝对路径>
python <skill>/scripts/workflow_state.py finalize --state-dir <STATE_DIR> --run-id <RUN_ID> \
  --evidence <本轮终态报告绝对路径>
```

状态机拒绝空证据、乱序、损坏文件、模板占位符、锁超时、run ID 不一致和陈旧 token；
失败会冻结后续任务，`retry`/`resume` 会使旧证据失效。只要有 `RUNNING/PENDING/NOT_RUN`，
默认整体不是 PASS；必须先让 `terminal.report` 落盘。`stage0.confirm` 是本轮唯一确认，
确认后不再询问普通阶段。

## stage0：冻结范围、环境和一次确认

Stage0 只读探测，不生成文档、源码、测试模型、Micro 工程或固件，不安装、下载、构建、烧录，
也不启动后台长任务。必须区分代码存储、MSLite 执行、固件编译和设备 I/O 环境；字段包括：

```text
HISPARK_ROOT=<绝对路径>
HISPARK_STORAGE_ENV=<Windows|WSL|Linux>
HISPARK_RUN_ENV=<WSL|Linux>
FIRMWARE_SDK_ROOT=<用户提供的固件SDK绝对路径>
FIRMWARE_SDK_STORAGE_ENV=<Windows|WSL|Linux>
FIRMWARE_BUILD_ENV=<Windows|WSL|Linux>
DEVICE_IO_ENV=<Windows|WSL|Linux>
TARGET_RUNTIME=<chip/board/OS/fbb-target>
```

先自动探测。`file converter_lite`、`fbb describe --json`、SDK 的
`min_cli_version`、端口和路径证据分别归档；路径只直接证明“文件存在哪里”，不能单独证明命令
在哪里执行。版本不足的
候选环境标记`BLOCKED`。Windows 串口要用 `.NET SerialPort.GetPortNames()`、注册表和有界
`pnputil` 交叉检查，不能只依赖 WMI。完整顺序和用户预览模板见
[`references/stage0-environment.md`](references/stage0-environment.md)。

默认完整流程必须由用户提供 `FIRMWARE_SDK_ROOT`；缺少`FIRMWARE_SDK_ROOT`时只询问该绝对路径，
不得搜索磁盘、环境变量或历史记录替用户选择。收到路径后再自动判断其存储、构建和设备 I/O 环境。
只有用户明确说“只做Host/不上板/不烧录”时才用 `HOST_ONLY`。

唯一确认规则：

- 人工只在 Stage0 确认范围、用户 SDK 绝对路径和执行模式；确认前只读。
- AUTO_ALL 缺 SDK 时，同一条用户回复同时给路径和确认；agent 先完成剩余只读探测并用 init token
  `finish stage0.scope_environment`，再调用 `confirm --confirmed-mode AUTO_ALL --sdk-root ...`。
- 初始 AUTO_ALL 回复改选 HOST_ONLY 时，废弃未确认 run，以新 `RUN_ID` 初始化 HOST_ONLY、完成
  stage0，再复用同一回复确认；不得在 AUTO_ALL run 上直接切换模式，也不得二次询问。
- `EXECUTION_CONFIRM_GATE（一次总确认；确认前只读）` 在确认前为 `EXECUTION_CONFIRM_GATE=PENDING`，
  成功后为 `EXECUTION_CONFIRM_GATE=PASS`；`--confirmed-mode` 必须与 `mode` 一致，
  `confirmation_count=1`。不得把“生成某算子”或仅提供 SDK 路径当成确认。
- 确认后文档、代码、审查、构建、Host、固件、烧录、串口和回填全部由 agent 自动完成，不再逐阶段询问。

Stage0 的完整探测、环境准备分流、依赖自动修复和安装/CLI 回退见
[`references/environment-prep.md`](references/environment-prep.md)。若环境或端口仍需要人工决定，只记录
`BLOCKED/NOT_RUN` 和恢复条件，不把未执行写成 PASS。`缺失依赖自动修复`遵循该 reference：
不能只
报告“缺少xxx”就结束；禁止`sudo pip`；记录 `DEPENDENCY_REPAIR`；镜像源失败可再尝试默认源；
自动安装和验证均失败时才阻塞。构建或长测试环境身份变化时生成新`RUN_ID`。ONNX必须同时具备
`onnx`和`onnxruntime`。

执行确认预览必须先用普通中文展示以下内容，再放技术记录；模板完整版本在 Stage0 reference：

```text
执行方式：完整开发和验证（默认）
模型转换和电脑端测试：<Windows/WSL/Linux 及原因>
固件SDK位置：<用户提供的绝对路径>
固件编译：<在哪个环境运行fbb CLI和交叉编译工具链>
开发板连接：<在哪个环境烧录并读取串口>
板上运行目标：<chip/OS/target>
接下来会执行：文档、源码、工具包、Host、固件、烧录和全部板端 case
当前状态：等待你的确认
请回复“确认执行”；如果这次不需要开发板验证，请回复“只做电脑端验证”
技术记录：STAGE0_PREVIEW=READY；BOARD_POLICY=AUTO_ALL；EXECUTION_CONFIRM_GATE=PENDING
```

## stage1：文档先行的规划门禁

只有 `EXECUTION_CONFIRM_GATE=PASS` 才进入。严格执行：

```text
hs-dev-op-implement mode=prepare
  -> OP_PLAN_GATE=PASS
hs-design-op-manual mode=integrated-initial
  -> OP_MANUAL_SYNC publication=record
gate_artifacts.py --stage pre-source
  -> PRE_SOURCE_GATE=PASS
```

prepare 期间禁止源码写入；初版设计/验证文档、facts、implementation contract、能力清单和计划版
`op_spec.py` 必须来自同一冻结输入；每条计划 case 必须包含明确且非空的 `test_point`。`PRE_SOURCE_GATE=PASS` 前不能调用
`hs-dev-op-implement mode=apply`。不能先改代码再更新草稿；规格、合同、能力或计划用例变化时返回
stage1 完整重跑。详细产物和哈希校验见 [`references/stage1-plan.md`](references/stage1-plan.md)。

## stage2：实现源码

进入 `stage2.implementation` 后调用 `hs-dev-op-implement mode=apply`，并传递冻结的
implementation unit、全部产物哈希和 `HISPARK_ROOT`。只有 `PRE_SOURCE_GATE=PASS` 才能写源码；
实现 Skill 必须先完整读取其 `references/code-style.md` 和 `references/code-quality-gate.md`，记录
`CODE_STYLE_SOURCE`、`CODE_STYLE_SOURCE_SHA256`，再按七层能力实现。该规范是 Skill 自带的，不是用户
需要安装的工具；在写任何①-⑦源码前完成逐规则审计。实现和代码审查分别落盘，不能代写 Host 或正式文档。
规范路径必须展开为绝对路径并记录其 SHA-256；它不是用户需要安装的工具。
`apply` 中不得在源码阶段直接
修改冻结合同；若合同、能力清单、计划 `op_spec.py` 或初版文档变化，必须返回 stage1 重新冻结，不能先改代码再更新草稿。

## stage3：构建 MindSpore Lite 工具包

启动 `stage3.mslite_build` 后读取
[`references/build-and-toolchain.md`](references/build-and-toolchain.md)。它负责
`converter_lite`、RISC-V Micro 库、受控构建、后台 `--wait`、构建新鲜度和失败分诊；这一步不同于
`hs-dev-build` 的 fbb 固件构建。构建前 workflow 必须用同一`CODE_STYLE_SOURCE`重跑
`CODE_STYLE_AUDIT=PASS`、`CODE_STYLE_GATE=PASS` 和 `SECURITY_GATE=PASS`，顺序早于下面命令：
这是构建前由 workflow 执行的质量复核，不是可选提示。

```bash
nohup bash <hs-workflow-op-development>/scripts/build_mslite.sh \
  --run-id "$OP_BUILD_RUN_ID" <build_root> >/dev/null 2>&1 &
bash <hs-workflow-op-development>/scripts/build_mslite.sh --wait 540 "$OP_BUILD_RUN_ID"
python3 <hs-workflow-op-development>/scripts/check_build_freshness.py \
  --code-root <code_root> --mslite-pkg "$MSLITE_PKG"
```

`libmindspore_converter.so` 缺失、其他MSLite包路径污染或环境身份变化时，在同一子进程自动修复；
不能让用户手工`export`，不修改`.bashrc`；需要重新构建/下载时使用新`RUN_ID`。

## stage4：Host 全量验证

进入 `stage4.host_verify` 后调用 `hs-verify-op-host`，读取并执行 stage1 冻结的完整
`op_spec.py`；不把Host阶段当成正常改写计划用例的阶段。必须先通过 `pre-verify`/validator，
再用 `--target all` 运行固定 harness，生成含逐 case 测试点的 `verify_summary.txt`、
`board_expected_matrix.json`、两份 Excel 和逐 case 证据。Host 失败按实现、模型/spec 或工具链回流，
不能用部分 PASS 缩小分母。细节按 Host Skill 的 references 按需读取。

## stage6：AUTO_ALL 固件矩阵

仅 `AUTO_ALL` 进入；`HOST_ONLY` 将 stage6-stage7 标记 `NOT_REQUESTED`。读取
[`references/board-orchestration.md`](references/board-orchestration.md) 和
`hs-verify-op-board/chips/ws63/references/sdk-integration.md`，按
`framework -> case_id -> mode(fp32,int8)` 逐行准备 Micro 工程、adaptor、Sample、CMake/Kconfig
和 target，交给 `hs-dev-build`，再由 Board Skill 验收 `FIRMWARE_CONTENT_GATE=PASS`。不得挑代表 case；
`board_expected_matrix.json` 是唯一分母。

## stage7：烧录、串口和板端精度

每个 stage6 新鲜 fwpkg 交给 `hs-dev-flash`，再由 `hs-verify-op-board` 采集完整 Tensor 并运行
`board_accuracy.py`。端口探测、flash JSON、串口时间、shape/元素数、余弦和
`board_matrix_report.py` 的逐行规则由 [`references/board-orchestration.md`](references/board-orchestration.md)
及 Board Skill 持有；不得以启动日志、标签、少数 case 或单一 PASS 代表完整验证。
确认后默认自动执行，不再询问“是否要上板”；只有端口歧义、设备 RESET 或其他外部条件异常时，
才按对应 Skill 记录 `NOT_RUN/BLOCKED` 和恢复动作。

## stage5：终态文档

Stage6/7 以及被阻断的后续阶段都到达 `PASS|FAIL|BLOCKED|NOT_RUN|NOT_REQUESTED` 终态后，进入
`stage5.final_docs`。若 Stage0 在执行确认前阻断，状态机会自动将 `stage5.final_docs` 标为
`BLOCKED`，只让 `terminal.report` 做状态收尾：记录阻断原因、恢复条件和状态证据，不调用
`hs-design-op-manual`，也不生成或覆盖正式交付文档。只有 Stage0 已完成
确认后，才调用 `hs-design-op-manual mode=integrated-final`：所有必需阶段通过（HOST_ONLY 的板端为
`NOT_REQUESTED`）使用 `terminal_state=completed`；任一后续阶段为 `FAIL|BLOCKED|NOT_RUN` 时使用
`terminal_state=blocked|hard-stop`，并在验证文档明确原因。记录性文档不能宣称完整通过。两份文档
的 facts/content/case audit 通过后写 `OP_MANUAL_SYNC=PASS publication=record`。
终态文档固定写入 `<opdir>/docs/{op}-operator-design-doc.md` 和
`<opdir>/docs/{op}-operator-verify-doc.md`。

## 完成和结案

用户可见首句必须先给整体状态。完整报告的唯一详细模板在
[`references/final-report.md`](references/final-report.md)；入口只保留这些语义：

- `AUTO_ALL` 全阶段和全矩阵通过才是 `OP_WORKFLOW=PASS`。
- 默认流程存在 `NOT_RUN/PENDING/RUNNING` 时是 `INCOMPLETE`，存在必需 FAIL 时是 `FAIL`。
- 明确 `HOST_ONLY` 且 Host 全绿、板端 `NOT_REQUESTED` 时是 `HOST_ONLY_PASS`。
- `FIRMWARE_MATRIX=<expected=N built=M pass=P fail=F not_run=R>`、`BOARD_RECORDS=<expected=N recorded=M>`、
  `BOARD_MATRIX_GATE=PASS` 和 `expected=executed=pass` 必须来自真实逐行证据。
- 如果板端未执行，即使Host和24份固件全部成功，整体仍是`OP_WORKFLOW=INCOMPLETE`。
- 禁止把“已完成迁移和验证”“已完成开发和验证”“验证通过”“全部通过”用于未完整通过的范围；
  `executed=pass+fail` 不把 `NOT_RUN` 计入 executed。`全部通过` 只有完整流程全部 PASS 才能用。
- 结案前必须让 `terminal.report` 通过 `finalize` 落盘；不得手工改写 `OP_WORKFLOW`。

## 资源索引和按需读取

| 阶段 | 直接读取 |
|---|---|
| 状态初始化、恢复、重试 | [`references/workflow-state.md`](references/workflow-state.md) |
| 待办模板（Markdown/JSON） | [`references/workflow-todo.template.md`](references/workflow-todo.template.md)、[`references/workflow-todo.template.json`](references/workflow-todo.template.json) |
| Stage0 探测、确认模板 | [`references/stage0-environment.md`](references/stage0-environment.md) |
| 固件环境准备和 CLI 回退 | [`references/environment-prep.md`](references/environment-prep.md) |
| Stage1 prepare、文档和 pre-source | [`references/stage1-plan.md`](references/stage1-plan.md) |
| Stage3 工具链 | [`references/build-and-toolchain.md`](references/build-and-toolchain.md) |
| Stage6/7 顶层交接 | [`references/board-orchestration.md`](references/board-orchestration.md) |
| Board 构建 handoff | [`../hs-verify-op-board/references/ws63-build-handoff.md`](../hs-verify-op-board/references/ws63-build-handoff.md) |
| Board 烧录与串口交接 | [`../hs-verify-op-board/references/flash-serial-handoff.md`](../hs-verify-op-board/references/flash-serial-handoff.md) |
| Board 精度与矩阵契约 | [`../hs-verify-op-board/references/board-accuracy-contract.md`](../hs-verify-op-board/references/board-accuracy-contract.md) |
| Board 红线与失败分流 | [`../hs-verify-op-board/references/board-guardrails.md`](../hs-verify-op-board/references/board-guardrails.md) |
| 终态报告 | [`references/final-report.md`](references/final-report.md) |
| WS63 具体接线 | [`../hs-verify-op-board/chips/ws63/references/sdk-integration.md`](../hs-verify-op-board/chips/ws63/references/sdk-integration.md) |
| 实现/文档/Host/Board 专项 | 对应 Skill 的 `SKILL.md` 和其直接 references |

专项 Skill 缺失时，完整安装地址为：
`https://gitcode.com/HiSpark/hibot-skills/tree/master/skills`。
需要 `hs-dev-env-prep`、`hs-dev-build` 或 `hs-dev-flash` 时，期望保留完整子目录：
`<skill-root>/hs-dev-env-prep/SKILL.md`、`<skill-root>/hs-dev-build/SKILL.md`、
`<skill-root>/hs-dev-flash/SKILL.md`；不能只复制一个 `SKILL.md`。
