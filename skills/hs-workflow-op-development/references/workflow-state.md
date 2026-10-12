# 本轮状态与恢复规则

## 目录

- [初始化与一次确认](#本轮待办检查点和自动续跑)
- [固定任务顺序](#固定任务顺序和逐步检查)
- [人工确认边界](#人工确认边界)

> 本文件由 `hs-workflow-op-development` 按需读取。入口 Skill 只保留最小调用约定；本文件保留完整的状态、证据和恢复规则。

当前状态 schema 为 3，任务 ID 直接对应 `stage0` 到 `stage7`。schema=1/2 的状态编号不同，不能直接恢复；保留原记录并新建 `RUN_ID`，不要手工替换状态文件中的编号。

## 本轮待办、检查点和自动续跑

每次开始“生成/实现/适配算子”时，先创建本轮待办和临时状态文件，再调用会生成文档、写源码、
生成测试或构建的下游 Skill。待办模板是 `references/workflow-todo.template.md`，状态只能通过
`scripts/workflow_state.py` 写入。不要凭对话记忆维护进度，也不要手工编辑生成的待办。
状态目录放在本轮算子输出目录的临时子目录中，例如 `<opdir>/.workflow-state/<RUN_ID>/`；
不要放在 skill 源目录或其他算子的目录中。

初始化只创建控制文件，不代表算子产物已经生成，也不改变 Stage0 的只读限制。基于已确定的
算子输出根目录生成本轮唯一 ID，不复用历史 ID，然后立即执行：

```text
python <hs-workflow-op-development>/scripts/workflow_state.py init \
  --state-dir <opdir>/.workflow-state/<RUN_ID> \
  --operator <算子名> --run-id <RUN_ID> --mode AUTO_ALL \
  --sdk-root <用户明确提供的固件SDK绝对路径>
```

如果用户尚未提供 SDK 路径，仍先用 `init` 生成待办，但不要猜测路径。在 Stage0 的唯一一次人工交互中，
同时索取 SDK 绝对路径和执行范围确认。收到回复后，agent 用该路径完成其余只读探测并 `finish` Stage0，
再立即把同一条回复写入 `confirm`，不得再次询问。AUTO_ALL 缺少用户 SDK 路径时，状态机拒绝确认，
流程不能继续。

若用户在最初请求中已明确选择仅电脑端，直接以 `--mode HOST_ONLY` 初始化。若用户在默认 AUTO_ALL 预览的
唯一回复中改选仅电脑端，则废弃尚未确认的 run，使用新 `RUN_ID` 和 `HOST_ONLY` 重新 `init`，完成并
`finish` Stage0，再用同一条回复执行 `confirm --confirmed-mode HOST_ONLY`。不得再次询问，也不得在
AUTO_ALL run 上直接切换模式。没有板卡并不等于用户选择了该模式。

`init` 必须同时生成 `workflow_state.json`、`workflow_todo.md` 和 `workflow_events.jsonl`，并将 Stage0
只读探测标为 `RUNNING`。脚本在同一目录中先写临时文件，再原子替换这三个文件。状态文件损坏、模板占位符
未展开、锁超时或 run ID 不一致时，必须 fail-closed，停止流程并报告原因，不能用其他文件推测进度。
`init` 同时输出 Stage0 探测的 `ATTEMPT_TOKEN`；完成探测时必须原样传回，不能使用其他运行的 token。
SDK 未在 `init` 时提供时，收到用户唯一一次回复后使用同一轮 ID，严格按下面顺序执行：

```text
<使用回复中的 SDK 路径自动完成 fbb/SDK/目标/端口等剩余只读探测>
python <skill>/scripts/workflow_state.py finish \
  --state-dir <STATE_DIR> --run-id <RUN_ID> --task stage0.scope_environment \
  --attempt-token <INIT输出的ATTEMPT_TOKEN> --status PASS --evidence <本轮Stage0探测回执绝对路径>
python <skill>/scripts/workflow_state.py confirm \
  --state-dir <STATE_DIR> --run-id <RUN_ID> \
  --phrase "确认执行" --confirmed-mode AUTO_ALL \
  --sdk-root <用户提供的固件SDK绝对路径>
```

这条命令是本轮唯一的执行确认。`--confirmed-mode` 必须与初始化时的 `--mode` 完全一致，
否则状态机拒绝写入。`--phrase` 仅保存用户确认原文，供审计使用；执行范围以结构化字段为准，
不通过自然语言子串推测。确认成功后，不再逐阶段询问是否继续。

### 固定任务顺序和逐步检查

状态机只允许按下表中的任务 ID 前进。`stage0.scope_environment` 由 `init` 隐式启动；
`stage0.confirm` 使用 `confirm`，`terminal.report` 使用 `finalize`。其余每项任务都必须先调用 `start`，
再执行对应的专项 Skill 或确定性脚本，最后用
`finish --status PASS|FAIL|BLOCKED|NOT_RUN|NOT_REQUESTED` 写回至少一条本轮证据。每完成一项就立即保存，
不能在多个阶段结束后批量补记。`stage7.final_docs` 在 Stage5、Stage6 到达终态后执行，以便终版文档记录真实的板端结果。

| 对外阶段 | 任务 ID | 主要检查和最小证据 |
|---|---|---|
| Stage0 | `stage0.scope_environment`、`stage0.confirm` | 范围和环境只读探测回执；一次总确认和 `EXECUTION_CONFIRM_GATE=PASS` |
| Stage1 | `stage1.plan`、`stage1.initial_docs`、`stage1.pre_source_gate` | 实现约定、能力清单、计划 `op_spec.py`、初版文档、facts 和 `PRE_SOURCE_GATE=PASS` |
| Stage2 | `stage2.implementation`、`stage2.code_review` | 源码 diff、`code-review.md`、质量/安全检查均 PASS |
| Stage3 | `stage3.mslite_build` | 本轮 `MSLITE_PKG`、构建日志和新鲜度回执 |
| Stage4 | `stage4.host_verify` | 全量 Host summary、`board_expected_matrix.json`、`HOST_VERIFY_GATE=PASS` |
| Stage5 | `stage5.firmware_matrix` | 每个 framework/case/mode 独立 fwpkg、接线和固件内容检查 |
| Stage6 | `stage6.board_matrix` | 每行 flash JSON、串口 Tensor、accuracy 结果和矩阵报告 |
| Stage7 | `stage7.final_docs`、`terminal.report` | 终版成对文档、facts/content/case audit、逐任务状态和最终报告 |

建议按以下固定格式调用（每次调用都必须携带同一个 `RUN_ID`）：

```text
python <skill>/scripts/workflow_state.py start  --state-dir <STATE_DIR> --run-id <RUN_ID> --task <TASK_ID>
# 记录上一条命令输出的 ATTEMPT_TOKEN
<调用对应专项 Skill 或脚本；文档、源码、Host/板端验证均由 agent 自动完成>
python <skill>/scripts/workflow_state.py finish --state-dir <STATE_DIR> --run-id <RUN_ID> \
  --task <TASK_ID> --attempt-token <ATTEMPT_TOKEN> --status PASS --evidence <本轮绝对路径>
```

`finish` 不接受空证据；证据可以是本轮产物的绝对路径或明确的单行回执标识。`finalize` 同样
必须带终态报告证据。状态脚本会拒绝损坏、空白或多行证据，避免无产物的 PASS。

`finish` 会推进到下一个未完成任务。失败时，后续执行任务冻结为 `BLOCKED`；板端不可用导致的
后续任务明确记为 `NOT_RUN`。若 Stage0 尚未通过执行确认，状态机会同时将 `stage7.final_docs` 标为
`BLOCKED`，只允许 `terminal.report` 收尾，不调用文档 Skill，也不修改正式文档。确认后的后续失败
才按 `integrated-final` 生成记录性文档。

每次 `start` 都生成新的 `ATTEMPT_TOKEN`。`finish`/`heartbeat` 必须携带同一 token；`retry` 或
`resume` 会使旧 token 失效，防止先前的 worker 覆盖新尝试。不要把短命令行进程登记为长任务 owner。
若能取得实际 worker PID，可在 `start` 或 `heartbeat` 时传入 `--owner-pid <PID>`；否则保留未知 owner。
只有心跳超过 `--stale-after`，或明确使用 `--force` 时，`resume` 才回收任务，避免重复启动仍在写代码、
构建或板测的下游任务。

修复问题后，用 `retry --task <TASK_ID>` 清理被阻断的后继状态，再从该任务重跑；禁止直接把状态改成 PASS。
上游任务重试会使后续执行结果、终版文档和 `terminal.report` 全部失效。状态中的旧证据会被清除，
并保存在 retry 事件历史中；后续阶段必须重新执行并再次 `finalize`，不能沿用之前的 PASS 证据。
重启或会话中断后，先执行 `resume --run-id <RUN_ID>`。未受失败影响且已 PASS 的任务不重跑；
`RUNNING` 任务只有在心跳过期、拥有者已退出或明确 `--force` 恢复时，才回到 PENDING。中间文件不会因此获得 PASS。
最终先把 `terminal.report` 保存到文件，再根据脚本计算的 `OP_WORKFLOW` 收尾；状态仍为
`RUNNING/PENDING/NOT_RUN` 时，不得结束当前任务。

### 人工确认边界

人工交互只发生在 Stage0，用于确认算子范围、运行环境、用户提供的固件 SDK 绝对路径，以及执行范围
（完整流程或明确 Host-only）。完整规则和命令顺序见 [`stage0-environment.md`](stage0-environment.md)。
本文件只补充状态机约束：调用 `confirm` 时显式传入与本轮 `mode` 相同的 `--confirmed-mode`；
`confirmation_count` 固定为 1，再次确认会直接报错。确认后，agent 按待办自动推进，不逐阶段询问。

需要暂停时，记录 `BLOCKED/NOT_RUN`、原因和恢复条件。恢复同一轮任务时继续使用原状态文件和 RUN_ID，
不得读取历史日志作为本轮证据。用户明确要求 Host-only 时，Stage5/Stage6 标记 `NOT_REQUESTED`；
默认完整工作流因板卡、SDK 或设备 I/O 条件不足而未执行时，标记 `NOT_RUN`。

完成措辞和整体状态以 [`final-report.md`](final-report.md) 为准。后台任务遵守以下收尾规则：

只要本轮任一后台任务仍为 `RUNNING`，workflow 就不能结束当前任务或向用户提交最终答复。`--wait` 返回 10 时，必须携带同一 `RUN_ID` 继续等待，直至得到 `SUCCESS` 或 `FAILED`，随后立即向用户通知终态。

所有后台任务都要登记 `RUN_ID`、启动时间、日志路径、状态查询命令和终态通知点。保持前台等待，
或按状态命令查询；不能关闭承载任务的窗口后再假定结果。任务失败时，在当前会话报告首个真实错误、
所属阶段、可复现命令和下一步；任务成功时，报告终态和本轮产物路径。历史日志、其他运行的 RC
和串口输出只能作为背景，不能作为本轮 PASS/FAIL 证据。
