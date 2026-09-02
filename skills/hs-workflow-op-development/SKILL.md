---
name: hs-workflow-op-development
description: >-
  End-to-end workflow for adapting, adding, porting, or supporting a MindSpore Lite Micro operator on HiSpark.AI, from specification and implementation through host tests, documentation, automatic firmware build/flash, and full board-case accuracy. It creates a per-run TODO checklist and persisted, resumable checkpoints so every stage reaches a recorded terminal state. This is the default top-level skill for generic requests such as “适配一个算子”, “新增/支持 xxx 算子”, “port/add/implement an operator”, or any request combining operator implementation with verification, build, flash, documentation, or board testing. Do not use it when the user explicitly asks to use a named stage-specific skill or clearly requests only implementation, only host tests, only documentation, only build, only flash, or only board accuracy.
---

# 算子适配端到端工作流

本 skill 负责编排、跨阶段状态和固件接入准备。必须完整执行模型转换、Micro交叉编译、
adaptor安装、Sample生成、CMake/Kconfig接线、固件构建、烧录和板端精度步骤；各阶段由
明确的专项 Skill（只负责一个确定阶段）或确定性脚本负责，不能压缩成“完成接线”后依靠临场发挥。

```text
stage0 范围/环境冻结
        ↓ EXECUTION_CONFIRM_GATE（一次总确认；确认前只读）
hs-dev-op-implement (mode=prepare；禁止源码写入)
        ↓ OP_PLAN_GATE（规格、合同、能力清单、计划用例已冻结）
hs-design-op-manual (integrated-initial)
        ↓ OP_MANUAL_SYNC publication=record
gate_artifacts.py --stage pre-source
        ↓ PRE_SOURCE_GATE（初版文档和四个主源哈希一致）
hs-dev-op-implement (mode=apply；此后才允许源码写入)
        ↓ IMPLEMENT_GATE
MindSpore Lite 工具包构建
        ↓ MSLITE_PKG
hs-verify-op-host
         ↓ HOST_VERIFY_GATE
（默认自动；明确Host-only时跳过）hs-verify-op-board(step0-3逐case准备)
         ↓ BUILD_HANDOFF
hs-dev-build → hs-verify-op-board(step4验收固件)
         ↓ FLASH_HANDOFF
hs-dev-flash/串口采集 → hs-verify-op-board(step5-6精度签收)
         ↓ 完整流程终态/Host-only终态
hs-design-op-manual (integrated-final：分别更新设计文档和验证文档并回填结果)
         ↓ OP_MANUAL_SYNC publication=record
```

## 路由优先级

1. 用户明确点名 Skill，或明确说“只做某阶段”时，优先使用对应的专项 Skill，不启动本 workflow。
2. 用户泛化地说“生成/实现/适配/新增/支持/移植一个算子”时，默认启动本 workflow，策略为
   `BOARD_POLICY=AUTO_ALL`；不能把“生成算子”理解成仅生成源码或仅 Host。
3. 用户同时要求实现与测试、文档、构建、烧录或板测时，必须使用本 workflow。
4. `hs-verify-op-host` 与 `hs-verify-op-board` 不合并：前者在 PC/WSL 中做完整规格矩阵和数值正确性；后者在真实板上验证交叉编译、固件接入、运行通路和硬件输出。两者复用同一 host 用例的模型、输入和 GT，但执行环境、失败归属和成本不同。

### 触发消歧矩阵

工作流优先级按用户意图判定，不按“是否出现算子名称”猜测：

| 用户请求示例 | 顶层入口 | 处理规则 |
|---|---|---|
| “实现/适配/新增 MatMul 算子” | `hs-workflow-op-development` | 默认完整走文档、实现、构建、Host和全用例板测；只有用户明确Host-only才跳过板端 |
| “生成 BitShift 算子” | `hs-workflow-op-development` | 默认宣布`AUTO_ALL`，继续走实现→MSLite构建→Host全量→固件构建→全部case上板；不能先把“仅Host”当成默认选项 |
| “在 WS63 上实现/运行 X 算子” | `hs-workflow-op-development` | 核对 SDK 路径；总确认通过且检测到单板时不再询问是否上板，自动跑完整矩阵 |
| “实现 X，只改 MindSpore Lite 源码，不测试、不编译、不写文档” | `hs-dev-op-implement` | 明确只做实现，输出交接信息，不启动 workflow 后续阶段 |
| “只用 hs-dev-op-implement 分析/补 X” | `hs-dev-op-implement` | 用户点名专项 Skill，严格停在该 Skill 的边界 |
| “只写 X 的测试/做 Host accuracy” | `hs-verify-op-host` | 不修改正式算子源码，不构建固件 |
| “只生成 X 的文档”或“用本 workflow 新生成 X 文档” | `hs-design-op-manual` | 已有算子产物使用 `artifact-sync`，全新独立文档使用对应 standalone 模式；不实现、不构建、不运行板测 |

若请求同时包含“实现/适配”与任意“测试、编译、文档、WS63、烧录、板测、完整流程”，
不得降级为 `hs-dev-op-implement`；若用户只说“实现算子”且范围不清，先按完整 workflow
处理，并在 stage0 说明将包含哪些阶段，允许用户明确选择“仅源码实现”后再切换专项 Skill。

## 用户可见阶段

```markdown
状态: stage<n> 进行中
待办:
- [ ] stage0 冻结范围、模式和环境
- [ ] stage0-confirm 展示环境、完整流程和影响范围，等待一次执行确认
- [ ] stage1 生成并审计算子文档草稿、实现合同和计划用例
- [ ] stage2 实现/修复算子源码并通过代码审查
- [ ] stage3 构建 MindSpore Lite 工具包
- [ ] stage4 生成并运行 Host 测试
- [ ] stage6 默认：取得用户明确提供的固件SDK位置，按板端期望矩阵逐项接入并构建固件
- [ ] stage7 默认：逐项烧录、采集串口并完成全部板端 case 精度验证
- [ ] stage5（stage6-stage7终态后）生成终版算子文档
```

## 本轮待办、检查点和自动续跑

每次开始“生成/实现/适配算子”时，必须先创建本轮待办和临时状态文件，再调用任何会生成
文档、写源码、生成测试或构建的下游 Skill。待办模板是
`references/workflow-todo.template.md`，状态唯一写入入口是
`scripts/workflow_state.py`；不要凭对话记忆维护进度，也不要手工编辑生成的待办。
状态目录应放在本轮算子输出目录的临时子目录（例如
`<opdir>/.workflow-state/<RUN_ID>/`），不能放在 skill 源目录或其他算子的目录中。

初始化只创建控制性文件，不代表算子产物已经生成，也不绕过 stage0 的只读限制。用确认的
算子输出根目录生成一个本轮唯一 ID（不能复用历史 ID），并立即执行：

```text
python <hs-workflow-op-development>/scripts/workflow_state.py init \
  --state-dir <opdir>/.workflow-state/<RUN_ID> \
  --operator <算子名> --run-id <RUN_ID> --mode AUTO_ALL \
  --sdk-root <用户明确提供的固件SDK绝对路径>
```

如果 SDK 路径尚未在用户请求中给出，仍先用 `init` 生成待办，但不要猜测路径；在 stage0 的
唯一一次人工交互中同时索取 SDK 绝对路径和执行范围确认。收到这一条回复后，agent 先用该路径
自动完成剩余只读探测并 `finish` stage0，再立即把同一条回复写入 `confirm`，不得二次询问。
AUTO_ALL 没有用户 SDK 路径时，状态机拒绝确认，不能以缺失路径继续。若用户在最初请求中已经
明确选择仅电脑端，直接以 `--mode HOST_ONLY` 初始化；若是在默认 AUTO_ALL 预览的唯一回复中
改选仅电脑端，则自动废弃尚未确认的 run，以新 `RUN_ID` 和 `HOST_ONLY` 重新 `init`、完成并
`finish` stage0，再用同一条回复执行 `confirm --confirmed-mode HOST_ONLY`，不得二次询问，也不得
在 AUTO_ALL run 上直接切换模式。不能因为没有板卡就自行切换该模式。`init` 必须同时生成
`workflow_state.json`、`workflow_todo.md` 和
`workflow_events.jsonl`，并把 stage0 只读探测标为 `RUNNING`。这三个文件均由脚本在同一目录
用临时文件写入后原子替换；状态文件损坏、模板占位符未展开、锁超时或 run ID 不一致时必须
fail-closed，停止流程并报告原因，不能用旧文件猜测进度。
`init` 同时输出 stage0 探测的 `ATTEMPT_TOKEN`；完成该探测时必须原样传回，不能从别的运行取值。
SDK 未在 `init` 时提供时，收到用户唯一一次回复后使用同一轮 ID，严格按下面顺序执行：

```text
<使用回复中的 SDK 路径自动完成 fbb/SDK/目标/端口等剩余只读探测>
python <skill>/scripts/workflow_state.py finish \
  --state-dir <STATE_DIR> --run-id <RUN_ID> --task stage0.scope_environment \
  --attempt-token <INIT输出的ATTEMPT_TOKEN> --status PASS --evidence <本轮stage0探测回执绝对路径>
python <skill>/scripts/workflow_state.py confirm \
  --state-dir <STATE_DIR> --run-id <RUN_ID> \
  --phrase "确认执行" --confirmed-mode AUTO_ALL \
  --sdk-root <用户提供的固件SDK绝对路径>
```

这条命令是本轮唯一的执行确认；`--confirmed-mode` 必须与初始化时的 `--mode` 完全一致，
否则状态机拒绝写入。`--phrase` 只作为用户确认原文审计记录，不用自然语言子串猜测执行范围；
确认成功后不再为普通阶段询问继续。

### 固定任务顺序和逐步门禁

状态机只允许按下面的任务 ID 前进。`stage0.scope_environment` 由 `init` 隐式启动；除它、
`stage0.confirm`（使用 `confirm`）和 `terminal.report`（使用 `finalize`）外，每一项都必须先 `start`，执行该项的专项 Skill 或确定性
脚本，再用 `finish --status PASS|FAIL|BLOCKED|NOT_RUN|NOT_REQUESTED` 写回至少一条本轮证据引用；完成一项立即落盘，
不能把多个阶段做完后批量补记。`stage5.final_docs` 虽保留历史编号，但实际在 stage6、stage7
到达终态后执行，确保终版文档能记录真实的板端结果。

| 任务 ID | 主要检查和最小证据 |
|---|---|
| `stage0.scope_environment` | 范围、代码根、MSLite/SDK/设备环境只读探测回执 |
| `stage0.confirm` | 一次总确认；`EXECUTION_CONFIRM_GATE=PASS` |
| `stage1.plan` | 冻结合同、能力清单、计划 `op_spec.py` 及哈希 |
| `stage1.initial_docs` | 成对初版设计/验证文档和 facts |
| `stage1.pre_source_gate` | `PRE_SOURCE_GATE=PASS` |
| `stage2.implementation` | 下游实现 Skill 的源码 diff 和实现回执 |
| `stage2.code_review` | `code-review.md`、质量/安全门禁均 PASS |
| `stage3.mslite_build` | 本轮 `MSLITE_PKG`、构建日志和新鲜度回执 |
| `stage4.host_verify` | 全量 Host summary、`board_expected_matrix.json`、`HOST_VERIFY_GATE=PASS` |
| `stage6.firmware_matrix` | 每个 framework/case/mode 独立 fwpkg、接线和固件内容门禁 |
| `stage7.board_matrix` | 每行 flash JSON、串口 Tensor、accuracy 结果和矩阵报告 |
| `stage5.final_docs` | 终版成对文档、facts/content/case audit |
| `terminal.report` | 逐任务状态、证据路径、失败/未执行原因和恢复条件 |

推荐的机械调用形态如下（每次调用都必须携带同一个 `RUN_ID`）：

```text
python <skill>/scripts/workflow_state.py start  --state-dir <STATE_DIR> --run-id <RUN_ID> --task <TASK_ID>
# 记录上一条命令输出的 ATTEMPT_TOKEN
<调用对应专项 Skill 或脚本；文档、源码、Host/板端验证均由 agent 自动完成>
python <skill>/scripts/workflow_state.py finish --state-dir <STATE_DIR> --run-id <RUN_ID> \
  --task <TASK_ID> --attempt-token <ATTEMPT_TOKEN> --status PASS --evidence <本轮绝对路径>
```

`finish` 不接受空证据；证据可以是本轮产物的绝对路径或明确的单行回执标识。`finalize` 同样
必须带终态报告证据。状态脚本会拒绝损坏、空白或多行证据，避免无产物的 PASS。

`finish` 会自动推进到下一个未完成任务；失败会冻结后续执行任务为 `BLOCKED`（板端不可用的
级联任务明确记 `NOT_RUN`），但仍允许 `stage5.final_docs` 和 `terminal.report` 记录终态。
每次 `start` 都生成新的 `ATTEMPT_TOKEN`；`finish`/`heartbeat` 必须携带同一 token，`retry` 或
`resume` 会使旧 token 失效，防止旧 worker 覆盖新尝试。短命令行进程不要被误认为长任务 owner；若能取得实际 worker PID，可在 `start` 或 `heartbeat` 时
传 `--owner-pid <PID>` 注册，否则保留未知 owner，`resume` 只有在心跳超过 `--stale-after`
或显式 `--force` 时才回收，避免下游仍在写代码/构建/板测时被重复启动。修复责任归属后用
`retry --task <TASK_ID>` 清理被阻断的后继状态，再从该任务重跑；禁止直接
把状态改成 PASS。上游任务重试会使其后的执行结果、终版文档和 `terminal.report` 全部失效，
状态中的旧证据会被清除并保存在 retry 事件历史中；后续阶段必须重新执行并再次 `finalize`，
不能沿用先前 PASS 证据。重启或会话中断后先执行
`resume --run-id <RUN_ID>`：未受回流影响的已 PASS 任务不
重跑；`RUNNING` 任务只有其心跳过期、拥有者已退出或明确 `--force` 恢复时才回到 PENDING，
中间产物不因此获得 PASS。最终必须先让 `terminal.report` 落盘，再根据脚本计算的
`OP_WORKFLOW` 结案；状态仍为 `RUNNING/PENDING/NOT_RUN` 时不得结束当前任务。

### 人工确认边界

人工交互只发生在 stage0：确认算子范围、运行环境、用户提供的固件 SDK 绝对路径以及一次
执行范围（完整流程或明确 Host-only）。调用 `confirm` 时必须显式传入与本轮相同的
`--confirmed-mode`；状态中的
`confirmation_count` 固定为 1；任何再次确认都直接报错。之后 agent 必须自动生成两份文档、
写代码、审查、构建、生成并运行 Host 用例、生成固件、逐项验证并回填文档，不得逐阶段询问
“是否继续/是否写文档/是否运行验证”。
确认命令的 `--confirmed-mode` 必须与本轮 `mode` 一致；AUTO_ALL 缺少用户 SDK 路径时，先用
用户同一条确认回复中的路径完成并落盘 stage0 只读探测，再在 `confirm` 命令补入
`--sdk-root`。状态机不会接受无路径的完整流程确认。用户确认原文保存在状态中供审计，不用
易误判的关键词解析替代结构化范围字段。
若这条唯一回复把默认 AUTO_ALL 改为 HOST_ONLY，自动用新 `RUN_ID` 重新初始化 HOST_ONLY 并完成
stage0，再以同一回复确认；这仍是一次人工交互，不得在旧 run 上调用不匹配的确认模式。

只有安全或外部条件确实无法由 agent 决定时才暂停并记录 `BLOCKED/NOT_RUN`，例如缺少用户
SDK 路径、环境候选无法唯一选择、端口歧义、设备需要人工 RESET、需要管理员权限或用户明确
改变范围；这类暂停不是常规阶段确认，也不能把未执行写成 PASS。自动恢复时继续使用同一个
状态文件和 RUN_ID，不得重新开一轮或读取历史日志冒充证据。

只有用户明确要求Host-only时，stage6-stage7标记`NOT_REQUESTED`。默认完整工作流中没有连接
板卡、缺少SDK或设备I/O不可用时标记`NOT_RUN`并说明原因，不把它们伪装成PASS，也不否定
已经完成的Host交付。只要默认流程存在一个`NOT_RUN/PENDING/RUNNING`阶段，整体状态就是
`INCOMPLETE`，不是PASS；任何必需阶段FAIL时整体状态是FAIL。

**完成措辞硬门禁：** 面向用户的首句必须先给整体状态，后给分阶段结果。只有默认完整流程的
实现、工具包构建、Host全量验证、文档、全量固件构建、逐行烧录、串口采集和板端精度全部PASS，
才允许使用不带范围限定的“完整流程通过”“全部验证通过”或✅。任一阶段未执行、仍在运行或
失败时，禁止用“已完成迁移和验证”“已完成开发和验证”“验证通过”“全部通过”等笼统完成句；
必须分别写明哪些PASS、哪些NOT_RUN/FAIL、未完成原因和下一步。

**后台任务终态硬门禁：只要本轮任一后台任务仍为 `RUNNING`，workflow 就禁止结束当前任务或向用户提交最终答复；`--wait` 返回 10 时必须携带同一 `RUN_ID` 继续等待，直至得到 `SUCCESS` 或 `FAILED`，随后立即向用户通知终态。**

所有后台任务都必须登记 `RUN_ID`、启动时间、日志路径、状态查询命令和终态通知点；前台
必须持续等待或按状态命令轮询，不能关闭承载任务的窗口后继续假设结果。任务失败时必须在
当前会话报告首个真实错误、归属阶段、可复现命令和下一步；任务成功时必须报告终态和本轮
产物路径。历史日志、旧 RC、旧串口输出只能作为背景，不能作为本轮 PASS/FAIL。

## stage0：冻结范围和环境

进入Stage0的第一项动作是运行上面的 `workflow_state.py init`，生成本轮待办和临时检查点；
状态文件本身是控制性记录，不属于算子源码或交付文档写入。随后记录 source entry、
implementation unit 候选、代码根、`MSLITE_OP_OUTPUT`、板测策略、板卡连接状态，以及各专项
Skill 的可用性，并在 `stage0.scope_environment` 完成后立即 `finish`。完整workflow默认
`BOARD_POLICY=AUTO_ALL`；只有用户明确说“只做Host/不上板/不烧录”才记录
`BOARD_POLICY=HOST_ONLY`。Stage0只完成只读探测和计划生成；在`EXECUTION_CONFIRM_GATE=PASS`
前禁止进入stage1，禁止调用下游生成/实现/验证Skill；禁止创建或修改算子文档、源码、测试模型、Micro工程、SDK接线和固件，
禁止安装、下载、构建、烧录或启动后台长任务。
若 `stage0.scope_environment` 以失败或阻断结束且尚未通过确认，状态机允许启动
`stage5.final_docs` 仅写入阻断运行的失败原因、恢复命令和状态证据；此例外不得生成或修改
算子设计/验证交付文档，常规终版文档回填仍须在确认通过且 stage6、stage7 到达终态后执行。

开始前先自动探测代码存储位置和各阶段实际执行环境；可由当前会话、路径存在性和工具实测
唯一确定的信息不得再次询问用户。路径只直接证明“文件存在哪里”，不能单独证明“命令在哪里
执行”：例如 Windows 工作区和其 `/mnt/<drive>/...` 映射表示同一类存储位置，但 Linux ELF版
`converter_lite`仍应在WSL/Linux运行，Windows侧SDK也可能由Windows侧`fbb CLI`驱动构建。必须分别
记录以下字段：

```text
HISPARK_ROOT=<绝对路径>
HISPARK_STORAGE_ENV=<Windows|WSL|Linux>
HISPARK_RUN_ENV=<WSL|Linux>
WSL_DISTRO=<使用WSL时填写>
FIRMWARE_SDK_ROOT=<要求固件/板测时填写>
FIRMWARE_SDK_STORAGE_ENV=<Windows|WSL|Linux>
FIRMWARE_BUILD_ENV=<Windows|WSL|Linux>
DEVICE_IO_ENV=<Windows|WSL|Linux>
TARGET_RUNTIME=<chip/board/OS/fbb-target>
```

`HISPARK_STORAGE_ENV`和`FIRMWARE_SDK_STORAGE_ENV`只描述两个仓库所在的文件系统；
`HISPARK_RUN_ENV`描述MindSpore Lite、converter、Host harness和Micro库构建命令的执行环境；
`FIRMWARE_BUILD_ENV`只描述fbb/SDK固件编译实际运行处；`DEVICE_IO_ENV`只描述烧录和串口可见处。
这些字段允许不同，例如HiSpark.AI存于Windows盘、MSLite命令在WSL执行、SDK在Windows编译、
串口也由Windows访问。

术语必须统一：`fbb CLI`是提供`fbb describe/build/flash/monitor`等命令的命令行工具，命令名
本身仍写作`fbb`；`固件SDK`是用户提供的芯片源码工程；`交叉编译工具链`是由fbb CLI调用的
编译器和构建工具；`固件`是编译后生成、用于烧录的`.fwpkg`文件。不得把fbb CLI称为SDK，
也不得把开发板连接环境或串口称为固件。

### Stage0 自动探测顺序

先执行只读探测并记录每项结论的命令/输出摘要：

1. 从当前工作目录、用户已给路径及路径在当前环境中的实际存在性确定`HISPARK_ROOT`和
   `HISPARK_STORAGE_ENV`；Windows路径与其`/mnt/<drive>/...`映射视为同一存储身份。
2. 检查`converter_lite`或现有`MSLITE_PKG`的二进制类型（如`file converter_lite`），并在候选
   Linux/WSL环境实测`--help`或`--version`。当前工具为Linux ELF时，自动选择唯一可执行的
   Linux/WSL环境作为`HISPARK_RUN_ENV`；使用WSL时一并记录真实发行版。
3. 只有用户已提供`FIRMWARE_SDK_ROOT`时才探测固件环境。分别在可访问该路径的Windows、WSL
   或Linux候选环境执行`fbb --version`和针对该SDK的`fbb describe --json`，不能只检查命令是否
   存在。必须同时比较`fbb_cli.version`与SDK全局及目标芯片声明的`min_cli_version`；版本不足的
   候选环境标记`BLOCKED`，不能因为describe成功就视为可构建。SDK在Windows文件系统且Windows侧检查成功时优先Windows；SDK在WSL/Linux原生文件
   系统且对应环境检查成功时优先该环境；只有一个候选通过时自动选择它。
4. 从SDK身份、芯片参考和`fbb describe --json`记录`TARGET_RUNTIME`；不能把Host或固件编译
   环境误写成MCU实际运行环境。
5. 分别探测候选环境中的兼容设备/串口可见性。Windows 必须运行
   `hs-verify-op-board/scripts/probe_serial_ports.py`，交叉记录 `.NET SerialPort.GetPortNames()`、
   `HKLM:\\HARDWARE\\DEVICEMAP\\SERIALCOMM` 和有界的 `pnputil` 结果；不得只依赖
   `Win32_SerialPort`/WMI。WSL/Linux 记录 `/dev/serial/by-id`、`/dev/serial/by-path` 及
   `ttyUSB/ttyACM`。串口探测必须在 `DEVICE_IO_ENV` 执行：Windows 设备用 Windows Python/PowerShell
   运行脚本并保存 Windows 绝对路径；只有 `DEVICE_IO_ENV=WSL|Linux` 时才在 WSL/Linux 探测 `/dev`。
   `HISPARK_RUN_ENV=WSL` 不代表 Windows COM 会自动出现在 WSL；跨环境交接时必须复制并记录
   `serial_probe.json`、固件的绝对路径和 SHA-256。保存的回执包括每个来源的端口、设备描述、VID/PID、错误和时间。
   只有一个环境能看到唯一 USB-UART 候选且后续 `hs-dev-flash` 返回真实 `success=true` 时，
   才记录 `DEVICE_IO_ENV`和端口；未检测到、多个候选或来源冲突时进入用户交互，不能直接判定“无板”。
6. 两个环境都能成功构建同一SDK且没有更强证据可唯一选择时，不擅自偏好某一边，向用户询问
   一次`FIRMWARE_BUILD_ENV`；设备I/O同理。

自动探测只允许读取状态，不能通过扫描磁盘自行挑选一个未由用户提供的可写SDK。完整workflow
缺少`FIRMWARE_SDK_ROOT`时只询问该绝对路径；收到路径后再自动判断其存储、构建和设备I/O环境，
不能在尚无SDK路径时要求用户同时填写三个环境字段。

### Stage0 完成只读探测后必须发出的执行确认模板

对“生成/实现/适配算子”，工具调用前可以先发简短进度说明；完成上述Stage0只读探测后的
第一条环境状态回复必须集中展示算子范围、四类环境、探测依据、完整阶段、预计写入/产物位置
和仍需人工处理的条件，再等待一次执行确认。`待提供/待确认`部分只列真正无法自动确定的项：

面向用户的正文使用中文含义，不把`BOARD_POLICY`、`DEVICE_IO_ENV`、`TARGET_RUNTIME`、
`EXECUTION_CONFIRM_GATE`等内部字段当成标题或要求用户理解。确需保留机器状态时统一放在末尾
“技术记录”中。尤其要解释：“开发板连接环境”是电脑在哪个系统中通过USB/串口烧录和读取
日志，不是固件；固件是后续构建出的`.fwpkg`文件。

```text
执行方式：完整开发和验证（默认）
将完成算子设计、代码实现、电脑端全部测试、固件编译、烧录和开发板全部测试。

本次算子：<算子名称>
来源模型格式：<ONNX/TFLite/...>
预计涉及：<只读扫描得到的实现单元候选；用普通中文描述>

检测到的环境：
  HiSpark.AI代码位置：<绝对路径；Windows磁盘或Linux文件系统>
  模型转换和电脑端测试：<在Windows/WSL/Linux中的哪个环境运行，并说明原因>
  固件SDK位置：<绝对路径；Windows磁盘或Linux文件系统>
  固件编译：<在哪个环境运行fbb CLI和交叉编译工具链>
  开发板连接：<在哪个环境烧录并读取串口；例如Windows COM5；未检测到则明确说明>
  板上运行目标：<芯片、操作系统、构建target>

判断依据：<路径映射、converter类型、fbb CLI版本/SDK要求和串口探测结果，用一句话解释>

接下来会执行：
  1. 编写算子说明、实现约定和测试计划
  2. 实现或补齐算子代码，并完成代码审查
  3. 编译MindSpore Lite转换工具和通用算子库
  4. 在电脑端生成全部测试模型，逐项转换、编译、运行并检查精度
  5. 根据实际结果更新最终算子文档
  6. 为每个板测用例生成Micro代码和静态库，并编译WS63固件
  7. 逐个烧录全部用例，读取串口输出，与电脑端标准答案比较

预计修改和生成：<算子源码、测试目录、报告目录、SDK中的隔离Sample和固件路径>

当前状态：等待你的确认，尚未生成代码、编译或烧录。
请回复“确认执行”；如果这次不需要开发板验证，请回复“只做电脑端验证”。

技术记录：STAGE0_PREVIEW=READY；BOARD_POLICY=AUTO_ALL；EXECUTION_CONFIRM_GATE=PENDING
```

如果缺少`FIRMWARE_SDK_ROOT`，先只展示已知的HiSpark存储/运行环境和默认AUTO_ALL范围，在同一条
提示中索取SDK绝对路径和执行范围确认，不得猜测或自动挑选路径。收到这一条回复后，agent 无需
再次询问：先用该路径自动完成剩余只读探测，把回执作为
`stage0.scope_environment` 的 evidence 并 `finish`；只有 stage0 已经 PASS 后，才调用
`confirm --confirmed-mode AUTO_ALL --sdk-root <绝对路径>`，把同一条回复作为唯一确认落盘并进入
stage1。若某项仍有歧义，只把该项及候选证据列为`待确认`，待用户修正后在新 RUN_ID 重新展示
最终方案。
用户明确回复“确认/继续/按上述方案执行”等同意语义后记录`EXECUTION_CONFIRM_GATE=PASS`，才可
进入stage1。用户要求调整范围或更换 SDK 时废弃当前轮次并新建 `RUN_ID`，重新执行 stage0 和
唯一一次确认；如果调整来自这条唯一回复，agent 自动重建 run、完成只读探测并复用该回复，
不得要求用户再次确认。尤其不能在 AUTO_ALL run 上直接执行
`confirm --confirmed-mode HOST_ONLY`。不得把最初一句
“生成某算子”或提供SDK路径本身当成已经通过该门禁。

记录用户回答后，在每个阶段用实际命令验证路径和工具是否可用。当前MSLite工具包是
Linux x64程序，因此MSLite构建、Host harness、converter和Micro库构建在Linux/WSL执行；
固件构建与烧录可以位于另一环境。跨Windows/WSL时在命令边界转换路径，并在复制模型库或
fwpkg时核对哈希即可，不为环境组合另建一套状态机。
转入`hs-workflow-mslite-env-setup`时显式传递
`HISPARK_AI_ROOT=$HISPARK_ROOT`；两个名称表示同一个 HiSpark.AI 项目根目录。

### 默认自动化与用户交互边界

- 用户已经给出`FIRMWARE_SDK_ROOT`，表示允许Stage0对该SDK做只读身份和环境探测；只有一次
  总确认通过后才允许在该SDK内完成确定性接线和构建。确认通过后不得再询问“是否要上板”。
- 总确认已通过、固件位置已给出且设备探测得到唯一兼容板卡/端口时，自动执行全用例固件构建、烧录、串口
  采集和精度判定，直至全矩阵终态。
- 标准流程只在Stage0进行一次总确认。确认成功后，文档生成、源码编写、代码审查、构建、Host
  和板端验证均由 agent 按待办自动推进，不再逐阶段询问是否继续。Stage0没有发现、或确认后
  外部条件发生变化时，自动把缺少的 SDK、设备、端口、权限或工具记录为 `BLOCKED/NOT_RUN`，
  保存首个错误和恢复命令后停止受影响分支；本轮不发起第二次常规确认。用户以后补齐条件并
  显式执行同一 RUN_ID 的 `resume` 时再继续，不能把未执行写成验证完成。
- 用户明确`HOST_ONLY`时不探测、不构建、不烧录，报告`NOT_REQUESTED`；默认策略下因外部条件
  不能执行则报告`NOT_RUN`，两者不能混用。

### 缺失依赖自动修复

总确认通过后，运行中出现`ModuleNotFoundError`、`command not found`或等价依赖缺失时，不能只
报告“缺少xxx”就结束。先确认报错发生在哪个执行环境、使用哪个Python/工具，再按以下边界修复：

1. 对`onnx`、`onnxruntime`、`numpy`、`PyYAML`、`openpyxl`等可通过pip安装的轻量Python包，
   优先使用项目已有虚拟环境；没有虚拟环境时使用当前用户范围，禁止`sudo pip`和静默修改系统
   Python。版本优先取仓库requirements/lock、README或工具兼容声明；没有约束时让pip解析兼容版。
2. 自动执行安装时记录`DEPENDENCY_REPAIR`、执行环境、Python绝对路径、安装命令、包版本和日志；
   镜像源失败可再尝试默认源。安装后必须用同一解释器执行真实`import`/`--version`验证，成功后
   自动重新启动失败阶段。构建或长测试环境发生变化时生成新`RUN_ID`，不得读取旧失败状态。
3. 只有安装需要管理员/root权限、全局系统修改、卸载或降级现有包、解决破坏性版本冲突、接受
   许可证/登录、下载大型SDK/专有工具链，或写入Stage0未确认的目录时，才把该项记为
   `BLOCKED`，同时写明“需要安装什么、为什么、将修改哪里、预计大小/影响”。不要在后续阶段
   再索取常规确认；把所需授权和恢复命令写入状态，用户随后主动授权并通过同一 RUN_ID 的
   恢复动作继续。
4. 自动安装和验证均失败时，报告已尝试的命令、两个源的首个真实错误、当前解释器和下一步，
   再将阶段标为`BLOCKED`；不能只复述缺少的包名，也不能伪造后续PASS。

ONNX Host路径开始前必须同时验证`onnx`（建模/读图）和`onnxruntime`（参考推理）；TFLite路径
验证`tensorflow`；报告生成验证`openpyxl`。这些是运行依赖，不是算子实现失败。

在修改算子源码前建立环境控制基线：记录 MindSpore Lite 主仓/子模块 HEAD、dirty fingerprint、当前 `MSLITE_PKG` 及 converter 路径；若已有一条与目标算子无关且 `verify_summary.txt` 明确 PASS 的稳定 Host case，先读取其 `output/<path>/_driver.sh` 中冻结的 `MSLITE_PKG`，用 `realpath` 与当前记录的包逐字核对。路径一致时才可执行 `_run.sh`，确认重新转换、编译、运行和 judge 仍 PASS；路径不一致时必须用当前环境变量和该控制 spec 重新调用 Host harness（至少 x86 路径），不能让陈旧 wrapper/converter 产生 `ENV_BASELINE=PASS`。这一步的作用是把 converter/工具链/子模块故障与后续算子缺陷分开。

没有可复用稳定 case 时记录 `ENV_BASELINE=UNKNOWN reason=no-known-pass-case`，不得伪称环境已验证；后续若多个无关用例在 converter 启动阶段成片失败，先补跑未改动控制用例或重建工具包，不允许直接修改目标算子源码。基线本身失败时记录 `ENV_BASELINE=FAIL` 并停在环境分支，源码保持未修改。

优先保证 PC/WSL 单元/Host 验证可运行。即使没有开发板，也继续 stage1-stage5；不要因烧录不可用而跳过 Host 测试。

## stage1：实现计划和初版文档先行

仅当`EXECUTION_CONFIRM_GATE=PASS`时进入本阶段；`PENDING`或缺少记录都必须停在Stage0。

进入本阶段先将 `stage1.plan` 标为 `RUNNING`，并在计划、初版文档和
`PRE_SOURCE_GATE` 各自完成后立即分别落盘 `PASS`；任一门禁失败要写入首个错误和证据路径，
不得只在对话中口头记账。

本阶段固定按下面顺序执行，不能把三个动作合并或调换：

1. 生成本轮唯一`OP_PLAN_RUN_ID`并调用`hs-dev-op-implement mode=prepare`。它先运行
   `gate_artifacts.py --stage source-freeze --plan-run-id <ID>`生成绑定算子、框架范围和code root的
   `source-freeze.json`，再执行step0-step3，生成并冻结
   `spec.md`、`decision.md`、`link-analysis.md`、`existing-capability-review.md`、
   `implementation-contract.md`、`capability_checklist.json`和计划版`op_spec.py`；运行
   `validate_op_spec.py`及带`--code-root`的`gate_artifacts.py --stage prepare`。prepare期间禁止修改Schema、
   Parser、Populate、Infer、Kernel、OpCoder、Quantizer、注册或构建接线源码。只有
   `OP_SPEC_GATE=PASS`和每个framework的`OP_PLAN_GATE=PASS`才继续。
2. 顶层workflow调用`hs-design-op-manual mode=integrated-initial`。文档Skill只消费第1步
   已冻结的四个主源，不负责扫描或生成实现合同，输出
   `operator-manual-facts.json`、`{op}-operator-design-doc.md`和`{op}-operator-verify-doc.md`。只有
   `OP_MANUAL_SYNC=PASS mode=integrated-initial publication=record`才继续。
3. 对每个framework运行带`--code-root`的`gate_artifacts.py --stage pre-source`，机械复核
   `source-freeze.json`中的源码指纹、计划版`op_spec.py`、facts、两份文档以及facts记录的
   `spec/implementation-contract/capability-checklist/op_spec`哈希，并重新执行facts/content/case
   三项文档audit。
   只有全部输出`PRE_SOURCE_GATE=PASS`才能进入stage2。

`source-freeze.json`记录prepare开始前的Git可见源码指纹，prepare和pre-source使用同一
`OP_PLAN_RUN_ID`机械复核指纹不变；`<opdir>`中的规划和草稿文件变化不算算子源码写入。
任何`code_root`内的①-⑦源码、注册或MindSpore Lite构建接线在`PRE_SOURCE_GATE=PASS`前
发生变化，都使本轮stage1失败，必须查明来源并重新执行prepare，不能用后补文档掩盖顺序错误。

同一`OP_PLAN_RUN_ID`禁止覆盖freeze receipt。上一轮stage1已结构化终止并明确开始新规划轮次时，
才可生成新ID并显式rotate；旧receipt必须归档，不得静默重置基线。固件SDK不属于本门禁范围，
其写入授权、接线receipt和新鲜度由stage6单独门控。

实现过程中若规格、合同、能力清单或计划用例需要变化，停止源码修改并回到stage1完整重跑
prepare→integrated-initial→pre-source；不能先改代码再更新草稿。

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

表中的“用户明确授权”只能在 Stage0 的一次总确认中取得；Stage6 只读取该确认和冻结的
状态，不再发起工具链安装询问。若授权缺失，直接记录 `BLOCKED` 及恢复命令，等待用户主动
授权后用同一 `RUN_ID` 恢复。

任何环境准备调用前，都必须在状态中记录：用户意图、`FIRMWARE_SDK_ROOT`（如已提供）、
是否允许下载 SDK，以及调用返回的 `fbb describe --json`。如果用户只提供了已有 SDK 路径，
不得把 `fbb sdk install <chip>` 当作默认补救动作；若 Stage0 没有记录下载授权，就把 SDK
缺失写为 `BLOCKED` 和恢复条件，不在后续阶段再次请求确认。

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
已有 `fbb CLI` 环境满足检查时直接使用 CLI/构建专项 Skill。

1. 若用户只要求 CLI、算子源码、MindSpore Lite 工具包构建或 Host 验证，输出
   `ENV_PREP_SKILL=NOT_REQUIRED`，不检查也不要求加载 `hs-dev-env-prep`。
2. 若用户要求固件编译/烧录，先执行 `fbb --version` 和 `fbb describe --json`，并核对用户给出的
   `FIRMWARE_SDK_ROOT`以及SDK全局/目标芯片的`min_cli_version`。命令成功且CLI版本满足要求时，输出 `ENV_PREP_SKILL=NOT_REQUIRED`，直接进入
   `hs-dev-build`/`hs-dev-flash`；“已安装并可用的 fbb CLI 环境”已经满足其前置条件。
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
   外部 Skill；将安装路径和恢复命令写入状态。用户安装或提供该 Skill 后，从 stage0 重新检查；
   不需要重做已通过的 Host 阶段。
4. 若 `hs-dev-env-prep` 可加载但用户已经给出 SDK 路径，调用时必须明确“只补环境和工具链，
   使用该 SDK，禁止再次执行 `fbb sdk install`”；若 Stage0 没有下载授权，则记录
   `BOARD_STAGE=BLOCKED`，等待用户主动授权后恢复，不在 Stage1 之后发起新确认。

检查 `hs-dev-build` 和 `hs-dev-flash` 是否已安装：

- 已安装：stage6、stage7 分别调用它们。
- 未安装：先告知用户从与 `hs-dev-env-prep` 相同的地址安装：
  `https://gitcode.com/HiSpark/hibot-skills/tree/master/skills`。
  该目录包含 `hs-dev-env-prep`、`hs-dev-build` 和 `hs-dev-flash`；安装后应重新检查
  当前使用者自己的 `<skill-root>`，不得只复制 `SKILL.md`；必须保留该 Skill 目录下对应的
  `references/` 和 `scripts/` 子目录及其中脚本。
- 用户未安装或当前环境不能加载：workflow 可按两者公开契约直接使用 CLI 回退，构建用
  `fbb --version`、`fbb describe --json` 或 `fbb list-targets --json` 取得真实 target，
  再执行 `fbb build --clean <target>`；烧录用 `fbb flash <target> --json-summary`，只按最后一行
  JSON 的 `success` 和 `error.code` 判定。回退不降低 clean build、target 解析或 JSON 判定要求。
  `fbb describe`/target 查询失败时阻塞固件阶段，不能猜 target；`fbb build` 非零时保留首个真实
  stderr，并按工具链、接线或生成代码分流；`fbb flash` 返回 `success=false` 时不得宣称烧录成功。

缺少对应专项 Skill 且没有可验证的 CLI 回退时，只阻塞对应阶段，不伪造结果。

默认`BOARD_POLICY=AUTO_ALL`在Stage0必须检查用户本次请求或当前会话是否已经明确提供
`FIRMWARE_SDK_ROOT=<固件SDK仓库绝对路径>`。没有时必须向用户询问并停在Stage0，不能通过
`EXECUTION_CONFIRM_GATE`或进入stage1；禁止通过搜索磁盘、其他任务记录、环境变量或fbb自动
选择一个可写SDK。只有用户明确切换为`BOARD_POLICY=HOST_ONLY`时，才可不提供SDK并继续
stage1-stage5，同时将板端阶段记为`NOT_REQUESTED`。用户提供后，记录对应 `FIRMWARE_SDK_SRC`，再检查
对应专项 Skill 是否安装，并执行 `fbb --version` 和 `fbb describe --json`（使用真实 target 时传入
target）。任一命令不可用、路径身份不符或SDK描述失败时，stage6、stage7标为环境阻塞，
并提示用户安装/运行 `hs-dev-env-prep`；不能因为build/flash skill文件存在就假定其隐含
环境已经准备好。

## stage2：实现源码

按待办先启动 `stage2.implementation`，源码和代码审查完成后再启动
`stage2.code_review`；两个任务必须分别写回状态和审查证据。确认门禁通过后，这一阶段以及
后续文档、构建、Host/板端验证由 agent 自动执行，不再向用户索取常规继续确认。

调用`hs-dev-op-implement mode=apply`，传递stage1冻结的implementation unit、全部产物哈希和
`HISPARK_ROOT`。`code-style.md`是随 Skill 分发的团队统一编程规范，不是用户需要安装的工具；apply
在写任何①-⑦源码前必须完整读取 Skill 内置的`references/code-style.md`，并返回该文件展开后的绝对
路径作为`CODE_STYLE_SOURCE`，以及`CODE_STYLE_SOURCE_SHA256`。不能改用用户本地项目中的同名文件，也不能因用户项目
缺少该文件而停止。
apply必须先重新读取`PRE_SOURCE_GATE=PASS`证据；不得重新运行prepare、静默改写合同或自行调用
文档Skill。只有收到每个implementation unit的`IMPLEMENT_GATE=PASS`才进入stage3。

实现阶段若发现capability checklist、implementation contract或计划用例信息不足，立即停止
apply并返回stage1，重新执行prepare、`integrated-initial`和pre-source。不得在apply中直接
修改冻结合同，也不得越权代写Host结果或正式文档。

## stage3：构建 MindSpore Lite 工具包

启动 `stage3.mslite_build` 后才允许运行受控构建脚本；构建成功或失败都要立即把 RUN_ID、
日志和 `MSLITE_PKG`/首个 stderr 写入检查点。不要因为后台命令已启动就把任务标成 PASS。

这一步构建的是 `converter_lite` 和通用算子库，不是 WS63 fwpkg。它与 stage6 的 `hs-dev-build` 不同，不能互相替代。

README中的构建环境在本阶段必须完整覆盖，但由受控脚本按命令作用域设置，不能依赖上一条
shell残留：

| README变量 | workflow处理 |
|---|---|
| `MSLITE_ENABLE_MICRO/INT8=ON`、`MSLITE_ENABLE_TRAIN/TESTCASES=OFF`、`MSLITE_TARGET_RISCV=ON` | `scripts/build_mslite.sh`在构建进程内显式导出 |
| `HISPARK_RISCV_TOOLCHAIN_PATH` | 尊重用户设置，否则定位并实测BiSheng `clang --version`；缺失即停止 |
| `mslite_pkg_path` | 统一命名为`MSLITE_PKG`，只接受本轮解压后的绝对目录 |
| converter的`PATH`、`LD_LIBRARY_PATH` | 不依赖全局PATH；Host/Board使用converter绝对路径，自动从本轮`MSLITE_PKG`定位`libmindspore_converter.so`，并在启动converter的同一子进程内注入动态库路径 |
| `SDK_PATH`、`ADAPTOR_PATH` | 属于README旧Sample固件构建示例；本workflow在stage6改用已核对的`FIRMWARE_SDK_ROOT/SRC`、`FBB_SDK_DIR`和integration receipt，不混入MSLite构建 |

如果这些变量需要从零安装和持久化，使用`hs-workflow-mslite-env-setup`；正常算子重建仍使用
本workflow的受控脚本，以保留RUN_ID、源码指纹、子模块锁和产物新鲜度门禁。

构建前由 workflow 使用stage2记录的同一`CODE_STYLE_SOURCE`重跑
`hs-dev-op-implement/references/code-quality-gate.md`，防止实现阶段之后的修改绕过门禁。先读取
`<opdir>/docs/code-style-audit.md`并核对规范路径、SHA-256、全部规则ID和当前diff；Skill 内置规范
内容发生变化时必须重新完整读取并重做逐规则审计。没有
`CODE_STYLE_AUDIT=PASS`、`CODE_STYLE_GATE=PASS`和`SECURITY_GATE=PASS`不得启动下面的构建命令。

使用本 workflow 自有的受控构建资源：

```bash
OP_BUILD_RUN_ID="op-$(date +%Y%m%d%H%M%S)-$$"
nohup bash <hs-workflow-op-development>/scripts/build_mslite.sh \
  --run-id "$OP_BUILD_RUN_ID" <build_root> >/dev/null 2>&1 &
bash <hs-workflow-op-development>/scripts/build_mslite.sh --wait 540 "$OP_BUILD_RUN_ID"
python3 <hs-workflow-op-development>/scripts/check_build_freshness.py \
  --code-root <code_root> --mslite-pkg "$MSLITE_PKG"
```

workflow 必须把 `OP_BUILD_RUN_ID` 写入本轮状态并在后续每次 `--wait`/`--status` 原样传回。`NO_CURRENT_BUILD`、`STALE_BUILD_RECORD` 或 `INCOMPLETE_BUILD_RECORD` 都表示没有可用于本轮的构建结论：重新启动新 run，不读取其他运行日志作 FAIL。用户手工修复环境或源码后继续时，先前源码指纹自动失效，必须生成新 RUN_ID 重建。构建失败按首个真实错误归属：

- parser/kernel/opcoder/注册或本次源码错误 → 回流 `hs-dev-op-implement`，修复后重跑 stage3-stage4；
- 工具链、包新鲜度、子模块漂移或非本次文件错误 → 保留证据并阻塞，不让 implement 盲改源码；
- 修复后重新执行质量门禁和构建，不复用陈旧包。

基线或工具链失败必须先停在环境分支，不得把它当作算子失败。若用户修复环境后要求
继续，必须创建新的 `RUN_ID` 并重新运行基线/构建；不得仅用 `--status` 读取旧轮次日志，
也不得因为旧失败而跳过新的基线。若 converter 在启动阶段对多个互不相关 case 同时失败，
先报告包版本、help 能力探测、子模块/工具链状态和首个 stderr，再回流环境分支；只有单个
模型在环境基线通过后失败，才归属算子或测试模型。

`error while loading shared libraries: libmindspore_converter.so`属于可自动修复的converter
运行环境问题，不是算子失败。所有调用converter的阶段必须先执行同一顺序：以本轮冻结的
`MSLITE_PKG`为唯一身份，定位包内真实动态库目录，过滤`LD_LIBRARY_PATH`中明显属于其他
MSLite包的目录，在**同一子进程**中注入后运行`converter_lite --help`自检；自检通过就直接
继续原阶段，不能让用户手工`export`后重试；不修改`.bashrc`、`ldconfig`等全局设置，也不能默认修改其他全局环境。
只有本轮包内完全没有该库、converter和库来自不同工具包、需要重新构建/下载包或需要系统级
修改时，才展示已探测路径、建议方案和影响并将阶段记为`BLOCKED`；不在本轮再次请求用户确认。
用户主动授权后通过恢复动作继续；环境身份发生变化后创建新`RUN_ID`，
不得读取旧失败记录冒充本轮结果。

成功证据是新鲜的 `MSLITE_PKG=<absolute path>`。

## stage4：Host 测试优先

启动 `stage4.host_verify` 后自动完成 pre-verify、全量 harness 和矩阵报告，并在同一轮状态中
写入 `HOST_VERIFY_GATE`、`board_expected_matrix.json` 和退出码；没有真实结论时保持 RUNNING 或
FAIL，不能先结束任务再补报告。

调用`hs-verify-op-host`，让其读取并执行stage1冻结的完整`op_spec.py`，依据capability checklist
做只读对账，不把Host阶段当成正常改写计划用例的阶段。发现模型构造、case或覆盖映射必须变化时，
返回stage1重新prepare、生成初版文档并通过pre-source，然后重新apply/build/Host。在启动固定
harness前，检查它已对每个framework执行`gate_artifacts.py --stage pre-verify`和
`validate_op_spec.py`；只有`ARTIFACT_GATE=PASS`且validator退出0才能运行长测试。完整workflow
必须使用`--target all`，使Host harness除summary/Excel外生成本轮`board_expected_matrix.json`；
该文件中的每个`framework/case_id/mode`就是板测分母，不允许后续人工挑代表用例。Host是默认
和必做验收，即使没有板卡也必须完成。

失败分流：

| 证据指向 | 回流所有者 |
|---|---|
| 用例模型、输入、GT、属性、覆盖映射设计错误 | `hs-verify-op-host` |
| parser/infer/kernel/opcoder/quantizer 数值或可达性错误 | `hs-dev-op-implement`，之后重跑 stage3-stage4 |
| MSLITE_PKG 陈旧、工具链或子模块异常 | stage3 环境分支 |

不要把所有 FAIL 都扔给验证 skill，也不要让 implement 修改固定测试执行器来凑绿。只有 VERDICT 全绿、`HARNESS_EXIT=0` 且 capability 覆盖 N=M，才得到 `HOST_VERIFY_GATE=PASS`。

进入 Host 前还必须完成一次规格覆盖对账：`code-review.md` 的 `semantic_coverage` 矩阵要逐项核对 dynamic/initializer/optional
输入组合、广播形态、索引/边界语义、折叠/重写路径和支持 dtype 与独立 case 的映射；单元素或
标量输入若在规格中合法，必须确认数据生成器确实能生成。缺少映射、只有代表 case 或生成器
无法表达最小合法输入时，`pre-verify` 直接 FAIL 并回流设计/实现阶段，不得把“代码编译通过”
或部分 Host PASS 当作覆盖完成。

## stage5：两份文档终态回填（在stage6-stage7之后执行）

`stage5.final_docs` 是终态回填任务：只有 stage6、stage7 已经 PASS、FAIL 或 NOT_RUN（而不是
仍为 RUNNING/PENDING）后才启动。文档生成由 agent 自动完成；文档失败只回流文档 owner，不能
通过再次询问用户来替代 audit。若它因 stage0 阻断而作为例外收尾，只记录状态证据，不生成
算子交付文档。

Host、固件构建和板端阶段都完成或明确终止后，调用
`hs-design-op-manual mode=integrated-final terminal_state=completed|blocked|hard-stop`，由文档
skill 从同一轮冻结事实和验证摘要分别更新
`<opdir>/docs/{op}-operator-design-doc.md`与`<opdir>/docs/{op}-operator-verify-doc.md`。
设计文档只保留规格和软件设计；验证文档回填测试设计、阶段结果和证据索引；不得另写调用链、Host结果或板测说明 Markdown。

文档失败回流文档 skill 或缺失事实的原 owner；两份文档只有 facts/content/case audit 均通过才可
输出 `OP_MANUAL_SYNC=PASS publication=record`。此门禁在完整workflow终态时签收，不能在Host
通过但板端尚未执行时提前写成完整流程通过。

## stage6：默认全矩阵固件接入与构建

自动启动 `stage6.firmware_matrix`，按 `board_expected_matrix.json` 逐行记录构建结果；不允许
人工挑选代表用例或在完成一行后等待用户确认下一行。SDK/工具链确实不可用时写
`NOT_RUN`/`BLOCKED` 和恢复条件，并让状态机继续到终态文档；状态脚本允许将当前阶段
明确写为 `BLOCKED`，后续阶段会自动继承阻断标记。

除非用户在stage0明确`BOARD_POLICY=HOST_ONLY`，否则默认执行。本阶段若发现
`FIRMWARE_SDK_ROOT`缺失、身份变化或环境结论失效，自动将本阶段写为`BLOCKED`或`NOT_RUN`，
保存首个错误和恢复命令；不要在Host完成后补发第二次 SDK/执行确认。只有用户主动开始新的
范围或更换 SDK 时才新建一轮并重新执行Stage0。不能等到Host完成后才首次询问SDK；开始前必须显示：

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

对于WS63，顶层先调用`hs-verify-op-board` step0-3准备模型与SDK接线，
在它输出构建handoff后才调用`hs-dev-build`。构建结果返回同一轮Board Skill
step4验收；不在烧录后重新从step0启动另一轮。该reference规定以下完整板测流程：

1. 冻结用户授权的SDK路径、target和SDK Git/dirty基线；
2. 读取stage4同轮`board_expected_matrix.json`，冻结全部Host PASS的RISC-V
   `framework/case_id/mode`、模型、输入和GT；不得只挑一个代表case；
3. 对矩阵中的每一行调用Board Skill的 `chips/ws63/scripts/build_micro.py`，以固定配置对该模型运行
   converter_lite并生成RISC-V Micro C工程；
4. 由同一脚本使用真实RISC-V工具链交叉编译并冻结 `libmicro_runtime.a`和 `libnet.a`；前者包含
   Micro模型API/运行时以及本轮生成的 `modelN.c`、`netN.c/ExecuteN()`、`weightN.c` 等模型执行外壳，
   后者是从通用NNACL/Wrapper库中按本轮模型实际依赖裁剪出的Kernel对象集合；
   它们按 operator/case/mode 身份分别归档，不能把不同模型或旧轮次混在同一组库中；
5. 从HiSpark.AI既有 `src/adaptor`安装或核对OH_AI CPU adaptor，不整目录覆盖用户代码；
6. 为当前case使用可追踪模型库目录，禁止多个同名陈旧库混链；
7. 以仓库中经过验证的OH_AI Sample/API结构为模板生成板端测试代码，
   写入同一Host输入并打印所有输出的dtype、shape、元素数和完整Data；
8. 调用 `chips/ws63/scripts/integrate_sdk.py`机械接入Sample、adaptor、模型库、CMake、
   Kconfig和target组件，并保存receipt；
9. 构建前执行对象、符号、库哈希和接线消费点检查，得到
   `BOARD_WIRING_GATE=PASS`；每行使用独立的operator/case/mode产物目录和receipt。

矩阵按固定顺序`framework → case_id → mode(fp32,int8)`逐行执行。每行都要完成step2-4并生成
独立fwpkg；一张最小模型对应一组Micro库和一次固件构建，不能把某行的固件/日志复用于另一行。
case局部失败时记录后继续其余安全可执行行；环境、工具链或设备级失败会阻塞后续行，但所有
未执行行必须明确记为`NOT_RUN`。

第3-4项在自动探测或歧义确认后的`HISPARK_RUN_ENV`执行；第5-9项在自动探测或歧义确认后的
`FIRMWARE_BUILD_ENV`执行。两者不同时，
按`micro_build_receipt.json`核对复制后的两份静态库哈希，并在固件构建环境运行
`integrate_sdk.py`，使实际使用的PowerShell或Shell包装器持有该环境可识别的路径。

第7项必须运行 `<hs-verify-op-board>/chips/ws63/scripts/prepare_sample.py`，第9项必须运行
`<hs-verify-op-board>/chips/ws63/scripts/verify_wiring.py`；不能用人工阅读或临场生成代码代替
这两个机械门禁。非WS63芯片必须有对应 `<chip>-sdk-integration.md`及确定性脚本后才能
进入本阶段，禁止照搬WS63路径猜接线。

第8项生成的 `ws63_board_env.ps1|sh` 必须在调用 `hs-dev-build`的同一进程中导入。
优先运行同目录的 `invoke_hs_dev_build.ps1|sh`；若顶层保持build Skill委托边界，则先
source环境文件、回显核对 `AI_CUSTOM_SAMPLE_DIR`与 `AI_MCU_MODEL_VARIANT`，再在该
进程调用build Skill/fbb CLI。只生成、查看或在已经退出的另一个shell中source不算接线完成。

不得以新建一个能编译的 `ai_main.c`代替上述流程，也不得在找不到输入时填零、只打印
ArgMax/标签、让任务无限循环，或让Sample用硬编码答案自报最终精度PASS。

随后调用 `hs-dev-build` 生成 fwpkg；它只负责通过fbb CLI构建指定target。若使用 CLI 回退，先从 `fbb list-targets --json` 或 `fbb describe --json` 获取真实 target，配置变更后强制 clean build。成功证据是新鲜 `*_all.fwpkg`。

构建完成后必须运行
`<hs-verify-op-board>/chips/ws63/scripts/verify_firmware.py`，验证Sample对应 `.c.obj`存在，
最终map包含模型Predict、Execute和目标Kernel，并确认 `_all.fwpkg`晚于本轮源码、配置
和模型库；只有 `FIRMWARE_CONTENT_GATE=PASS`才能继续。`fbb build`退出0但没有这些
证据时，stage6仍为FAIL。

构建错误分流：模型/算子生成代码错误回 stage2，再重跑 stage3-stage4；sample/adaptor/Kconfig 接线错误留在 stage6；工具链错误按 build skill 处理。

## stage7：默认全矩阵烧录与板端精度

自动启动 `stage7.board_matrix`，逐行完成烧录、串口采集和精度判定并立即落盘；端口或人工
RESET 等外部阻塞只记录为 `NOT_RUN`/`FAIL`，不再次询问是否进行普通验证，也不复用上一轮证据。

对`board_expected_matrix.json`的每一行调用`hs-dev-flash`烧录该行stage6生成的固件，只按fbb CLI最后一行JSON判断烧录；随后必须采集串口并运行精度判定。可使用该skill公开的`fbb flash <target> --then-monitor --until <keyword> --timeout <seconds> --json-summary`链路保存串口文本；缺skill时用相同CLI契约回退，不直接调用BurnTool。
进入本阶段以及每次 `PORT_NOT_FOUND` 重试前，必须运行
`hs-verify-op-board/scripts/probe_serial_ports.py --output <serial_probe.json>`，并把该回执
写入本轮状态。Windows 不能只使用 `Win32_SerialPort`/WMI；COM 端口必须至少由 .NET 和注册表
交叉确认，PnP 查询须有超时。探测到 CH340/CH341、CP210x、FTDI 或 USB-SERIAL 等 USB-UART
只表示候选，不能替代 `hs-dev-flash` 的真实 flash JSON 和本轮串口证据。

不得把上述委托压缩成不可核验的一句话。进入烧录前必须确认 `FBB_SDK_DIR`仍指向用户
提供的SDK、target来自fbb真实列表、输入固件是stage6通过内容门禁的新鲜 `_all.fwpkg`。
端口歧义时把候选、错误和恢复命令写入状态并将该行标为`NOT_RUN`，不在本轮主动要求用户选择；
只读stdout最后一行JSON并按 `success`与`error.code`分流。若返回 `DEVICE_NOT_RESPONDING`，
将该行标为`NOT_RUN`并记录需要人工RESET的明确操作；不在后续阶段再次索取确认。烧录成功后采集时间必须晚于本轮烧录，串口
端口和日志波特率必须可追溯；缺任一证据都不能进入板端精度签收。详细执行规则以
`hs-dev-flash`和 `hs-verify-op-board` step5为准，workflow负责确认二者实际执行完毕。

烧录成功不等于板端精度成功。将烧录和串口证据返回同一轮
`hs-verify-op-board` step5-6，传入已冻结的同轮 Host GT、测试输入、串口完整输出和
fp32/INT8模式，由它输出`ACCURACY_VERDICT`。这是恢复同一轮Board Skill，
不重跑step0-4的写入与构建动作。

固件构建与设备I/O环境可以不同。若SDK在WSL构建而串口只在Windows可见，把签收后的fwpkg
复制到Windows并核对哈希，再调用flash/serial能力；CLI回退可使用
`fbb flash --file <本地fwpkg> --chip <chip> --json-summary`。

`hs-verify-op-board`必须完整执行板端验证：核对前置产物、确认固件身份、
采集本次烧录后的完整串口Tensor、逐Tensor核对数量/shape/元素数并与同轮GT计算余弦。
不得把“烧录成功”“出现启动日志”或Sample自报PASS当作精度PASS。

每行完成后写`<board-results>/<framework>/tc<case_id>/<mode>/board_result.json`。全部行到达终态后
必须运行`hs-verify-op-board/scripts/board_matrix_report.py`，生成`board_case_results.json`和
`board_verify_summary.txt`。只有`expected=executed=pass`、`fail=not_run=0`且
`BOARD_MATRIX_GATE=PASS`，才允许整个板测输出`ACCURACY_VERDICT=PASS`。板测脚本中的
`executed=pass+fail`，只统计真实进入板端执行的行；为未执行行生成`board_result.json`只算
`recorded`，不算`executed`。

没有连接板卡、串口不可用或用户不在板边时，保留 Host 完成状态并将 stage7 标为未执行；不要反复烧录或用其他轮次串口日志冒充本轮板测。

## 完成判据

Host 交付完成必须满足：

- 每个 implementation unit 的 `IMPLEMENT_GATE=PASS`；
- 编码后审查产物 `<opdir>/docs/code-review.md` 已生成，且
  `registration_matrix`、`branch_reachability`、`quantizer_ownership`、
  `folding_and_rewrite_cases` 均有证据，不能存在未处置的 `FIX_REQUIRED`；
- 新鲜 `MSLITE_PKG` 构建成功；
- `HOST_VERIFY_GATE=PASS`；
- 设计文档的规格/软件设计已保留；验证文档的测试计划和阶段结果在所有请求范围内的阶段结束后同步。

默认完整workflow的板测完成另需：

- `hs-dev-build`/CLI 构建成功；
- `hs-dev-flash`/CLI JSON `success=true`；
- `BOARD_MATRIX_GATE=PASS`，且`board_expected_matrix.json`中的全部case/mode均有逐行证据；
- `ACCURACY_VERDICT=PASS`。
- `OP_MANUAL_SYNC=PASS publication=record`，且验证文档中的结果汇总与矩阵报告一致、设计文档未混入验证结果。

默认完整流程的用户可见首行只能是以下三种之一：

```text
状态：完整流程通过
状态：未完成（存在NOT_RUN/PENDING/RUNNING阶段）
状态：失败（存在FAIL阶段）
```

显式`HOST_ONLY`且Host范围全绿时首行写：

```text
状态：仅Host范围通过（用户明确未要求板端；不是完整流程通过）
```

任一必需门禁FAIL时列出失败阶段、原始证据和回流owner；任一阶段NOT_RUN时列出未执行阶段、
原因和恢复条件。只有明确`HOST_ONLY`时板测是`NOT_REQUESTED`；默认流程因无板卡未执行时是
“Host验证通过、固件构建验证通过、真实板测未执行”，不能写成“已完成验证”或完整板测完成。

## 统一结案报告

`terminal.report` 只能由 `workflow_state.py finalize` 写入，不能用通用 `start`/`finish` 绕过结案
证据。结案前必须运行 `workflow_state.py finalize --state-dir <STATE_DIR> --run-id <RUN_ID> \
--evidence <本轮终态报告绝对路径>`，让脚本
根据本轮检查点重新计算整体状态；不得手工把 `OP_WORKFLOW` 改成 PASS。结案消息首行、逐阶段
表和状态文件中的结果必须一致，并同时报告 `RUN_ID`、`workflow_state.json`、`workflow_todo.md`
和 `workflow_events.jsonl` 的绝对路径。若仍有 RUNNING/PENDING，先恢复或继续该任务；若有
FAIL/BLOCKED，保留失败证据并说明 retry owner。

```text
OP_WORKFLOW=<PASS|FAIL|INCOMPLETE|HOST_ONLY_PASS>
RUN_ID=<本轮唯一ID>
WORKFLOW_STATE=<workflow_state.json绝对路径>
WORKFLOW_TODO=<workflow_todo.md绝对路径>
EXECUTION_CONFIRM_GATE=<PASS|PENDING>
IMPLEMENT_GATE=<PASS|FAIL>
MSLITE_BUILD=<PASS|FAIL>
HOST_VERIFY_GATE=<PASS|FAIL>
OP_MANUAL_SYNC=<PASS|FAIL>
FIRMWARE_BUILD=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
FIRMWARE_MATRIX=<expected=N built=M pass=P fail=F not_run=R>
FLASH_VERDICT=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
BOARD_RECORDS=<expected=N recorded=M>
BOARD_MATRIX=<expected=N executed=M pass=P fail=F not_run=R>
BOARD_MATRIX_GATE=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
ACCURACY_VERDICT=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
```

`OP_WORKFLOW=PASS`只用于`AUTO_ALL`的全部阶段和板端全矩阵PASS；默认流程有任何
`NOT_RUN/PENDING/RUNNING`时使用`INCOMPLETE`，有任何必需阶段或case失败时使用`FAIL`。用户明确
选择`HOST_ONLY`且stage0-stage5全部PASS、板端字段均为`NOT_REQUESTED`时使用
`HOST_ONLY_PASS`，不能缩写成无范围的PASS。

结案消息在整体状态后必须输出逐阶段表，至少包含：

```text
阶段                         状态          数量/证据                     原因
源码实现                     PASS|FAIL     IMPLEMENT_GATE                ...
MindSpore Lite工具包构建     PASS|FAIL     MSLITE_BUILD                  ...
Host全量验证                 PASS|FAIL     passed/expected               ...
固件构建矩阵                 PASS|FAIL/... built/expected                ...
真实开发板烧录               PASS|FAIL/... flashed/expected              ...
串口Tensor与板端精度         PASS|FAIL/... executed/expected, pass/fail  ...
```

“固件构建矩阵24/24 PASS”和“真实板测0/24 NOT_RUN”必须作为两行展示，不能合并成“WS63验证
通过”。如果板端未执行，即使Host和24份固件全部成功，整体仍是`OP_WORKFLOW=INCOMPLETE`。

报告同时给出源码diff、`MSLITE_PKG`、Host summary/Excel、设计文档、验证文档、
`board_expected_matrix.json`、逐case的fwpkg/烧录JSON/monitor/accuracy日志、
`board_case_results.json`和`board_verify_summary.txt`绝对路径。面向用户的结案消息必须逐行列出
`framework/case_id/mode/status`，不能只写“板测完成”或只展示一个成功case。

## 资源索引

| 资源 | 所有者与用途 |
|---|---|
| `scripts/build_mslite.sh` | workflow stage3 的算子源码后工具包重建、RUN_ID 与子模块/注册断言 |
| `scripts/check_build_freshness.py` | workflow stage3 在进入 Host 前核对源码与解压包新鲜度 |
| `scripts/workflow_state.py` | 初始化待办、原子写入检查点、顺序门禁、恢复、重试和终态计算 |
| `references/workflow-todo.template.md` | 每轮生成的可读待办模板；由状态脚本自动渲染，不手工编辑 |
| `references/workflow-todo.template.json` | 任务 ID、固定顺序和状态值的机器可读契约 |
| `references/build-and-toolchain.md` | stage3 工具链、产物和构建失败分诊 |
| `../hs-verify-op-board/chips/ws63/references/sdk-integration.md` | stage6必须完整读取的WS63模型库、adaptor、Sample与SDK接线规范（跨 Skill 资源） |
| `tests/test_build_state.sh` | RUN_ID、源码指纹、陈旧状态和子模块漂移回归 |
| `tests/test_workflow_state.py` | BitShift 12×2 打桩流程、状态顺序、失败回流、Host-only 和恢复回归 |

这些资源由本 workflow 持有，避免 `hs-dev-op-implement` 托管自己不执行的构建流程。
每个专项 Skill 的 `references/` 与 `scripts/` 子目录也必须随 Skill 一起安装；这里的表格只列本
workflow 自有资源和一个明确的跨 Skill 资源，不存在名为 `references/scripts` 的合并目录。
`hs-workflow-mslite-env-setup` 的同名脚本负责通用环境搭建；这里的脚本只服务算子源码修改后的
受控重建，调用时必须使用完整 skill 路径区分。
