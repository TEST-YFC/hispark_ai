# 本轮状态与恢复契约

## 目录

- [初始化与一次确认](#本轮待办检查点和自动续跑)
- [固定任务顺序](#固定任务顺序和逐步门禁)
- [人工确认边界](#人工确认边界)

> 本文件由 `hs-workflow-op-development` 按需读取。入口 Skill 只保留最小调用契约；本文件保留完整的状态、证据和恢复规则。

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
| `stage5.final_docs` | 确认后的终版成对文档及 facts/content/case audit；确认前阻断时仅作状态收尾记录 |
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
级联任务明确记 `NOT_RUN`）。若 Stage0 尚未通过执行确认，状态机会同时将
`stage5.final_docs` 标为 `BLOCKED`，只允许 `terminal.report` 做状态收尾；此时不调用文档 Skill
或修改正式文档。确认后的后续失败才按 `integrated-final` 生成记录性文档。
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
