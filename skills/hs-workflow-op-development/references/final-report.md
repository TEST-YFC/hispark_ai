# 终态判据与结案报告

## 目录

- [完成判据](#完成判据)
- [统一结案报告](#统一结案报告)
- [资源索引](#资源索引)

> 只有所有阶段进入终态后读取。这里是用户可见状态和证据格式的唯一详细定义；入口只保留摘要和链接。
> Stage0 尚未完成执行确认而阻断时，状态机会将 `stage5.final_docs` 标为 `BLOCKED`，由
> `terminal.report` 写状态收尾证据，`OP_MANUAL_SYNC=NOT_RUN`，且不生成或覆盖正式设计/验证文档；
> 本文件的终态文档条款适用于确认已通过的运行。

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
OP_MANUAL_SYNC=<PASS|FAIL|NOT_RUN>
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

## 资源索引

报告同时给出源码diff、`MSLITE_PKG`、Host summary/Excel、设计文档、验证文档、
`board_expected_matrix.json`、逐case的fwpkg/烧录JSON/monitor/accuracy日志、
`board_case_results.json`和`board_verify_summary.txt`绝对路径。面向用户的结案消息必须逐行列出
`framework/case_id/mode/status`，不能只写“板测完成”或只展示一个成功case。
