# 训练阶段命令调度

`run_training_workflow.py` 按顺序执行工作流已经准备好的命令，保存日志并在失败后运行报告收尾命令。它不会自行生成算子代码、模型或文档，也不审计训练数值和源码身份。不要把这个脚本等同于整套技能的自动化能力。

## 阶段与计划

计划包含 `verification_kind=training`、`run_id` 和 `stages`。`run_id` 必须与运行目录名一致；运行目录须不存在或为空，脚本不覆盖旧结果。阶段顺序固定为：

```text
design → implementation → build → model → host → aggregate → board → final
```

- `design` 命令先调用训练实现的 prepare（step0、step1），制定用例计划，再生成并审计设计文档和验证文档初稿。不能在缺少这些设计输入时先写文档。
- `implementation` 命令执行 apply（step2–step5），不重复或省略 prepare，也不能先于初版文档。
- 其余命令分别由对应技能准备。Host 生成 C 的数值比较、板端比较、文档审计仍使用各自脚本。
- `aggregate` 的正式命令必须给 `aggregate_training_results.py` 增加 `--export-board-expected`。该参数在写入 `train_verify_summary.json` 后，从 Host PASS 的数值用例和原始 golden 导出 `runs/<run_id>/board_expected/training_board_expected_matrix.json`。Host 未全量 PASS 时矩阵状态为 `BLOCKED_HOST_NOT_PASS`，调度器不得进入 board。
- `board` 阶段不提供专用矩阵 runner。工作流按板端训练步骤调用现有准备、构建、烧录、采集和比较命令；每个 case 保留 comparator report。
- 必需阶段不得禁用或缺少命令。命令失败后不执行依赖阶段，但仍尝试执行 `final`。

每个阶段提供参数数组 `command`，可选 `cwd` 和正数 `timeout`（秒，默认 3600）。路径含空格时作为数组中的一个参数，不拼 shell 字符串。正式使用前，工作流必须把全部阶段命令写入计划；空操作只能用于调度器测试，不能作为实现或验证证据。

没有板端执行条件时，加 `--allow-board-not-run`，并在 `board` 中提供具体 `reason`，不提供命令，状态为 `NOT_RUN`。用户明确排除板测时还需 `enabled=false`，状态为 `NOT_REQUESTED`。已执行的板端命令失败不适用跳过规则。

`--allow-board-not-run` 只允许调度器记录合法跳过，不会自动将 finalizer 的 policy 改为 `HOST_ONLY`。跳过原因、board 状态与 facts 必须一致，且不能携带已执行的 board 证据。在其他必需命令和证据检查均通过时：

| finalizer 的 `--board-policy` | 调度器 `status` | finalizer `verdict` | `board_verified` |
|---|---|---|---|
| `AUTO_ALL`（默认），板测合法跳过 | `COMMANDS_COMPLETED` | `NOT_VERIFIED` | `false` |
| `HOST_ONLY`（显式选择），板测合法跳过 | `COMMANDS_COMPLETED` | `PASS` | `false` |

两种情况下，调度器自身的 `workflow_status` 都保留 `NOT_VERIFIED`；表中的业务 verdict 由调度结束后的独立 finalizer 给出。证据缺失或有明确失败时不能套用该表中的通过结果。

```bash
python3 <workflow_skill_root>/scripts/run_training_workflow.py \
  --plan <opdir>/workflow_plan.json \
  --run-dir <opdir>/runs/<run_id> \
  --allow-board-not-run
```

## 失败后生成报告

每个阶段启动前，工作流保存当前 `train_workflow_summary.json`，并传入以下环境变量：

- `TRAIN_WORKFLOW_SUMMARY`：本轮中间摘要的绝对路径；
- `TRAIN_RUN_ID`：本轮身份；
- `TRAIN_PREVIOUS_COMMAND_STATUS`：前序命令是否失败。

`final` 从该摘要读取失败和未执行情况，再同步真实 facts、生成独立验证文档并调用文档审计。它不能把前序失败改成成功。缺少或失败的 `final` 命令也会使调度结果失败。

## 输出与状态

输出 `<run-dir>/train_workflow_summary.json` 和 `<run-dir>/<stage>.log`；摘要记录计划 SHA256、阶段命令、退出码及耗时。超时或启动失败会保留日志和失败原因。

摘要 `schema_version=2`，明确区分命令和验证结果：

- 全部要求执行的命令成功：`status=COMMANDS_COMPLETED`、`command_status=PASS`，退出码 0；
- 必需命令缺失、被禁用或执行失败：`status=FAIL`、`command_status=FAIL`，退出码 2；
- 本脚本不做业务证据审计，因此始终保留 `workflow_status=NOT_VERIFIED`、`evidence_status=NOT_CHECKED`、`board_verified=false`。最后一项表示调度器没有确认板测，不否认独立板端报告的真实结果。

工作流必须继续读取并审计 Host 的 `train_verify_summary.json`、板端报告及两份文档，才能给出技能规定的最终结论。任何单纯退出码为 0 的命令，包括最终报告命令，都不能让本调度器输出训练验证 PASS。

板端证据交给 facts 时保持最小：单 case 直接引用 comparator report；多 case 使用只含 case、状态和 report 路径/hash 的 `board_matrix.json`。构建、烧录、端口和设备信息保留在各自证据及 `facts.sources` 中。finalizer 重放每个 report，并核对 Host expected 数值用例集合。

## 终态 finalizer（调度结束后单独调用）

`run_training_workflow.py` 只负责阶段命令调度。即使调度器输出 `COMMANDS_COMPLETED`，也不代表训练业务验证通过。调度器结束后，必须单独调用：

```bash
python3 <workflow-skill-root>/scripts/finalize_training_workflow.py \
  --opdir <opdir> \
  --run-dir <opdir>/runs/<run_id> \
  --facts <opdir>/<facts.json> \
  --design <opdir>/<design.md> \
  --verify <opdir>/<verify.md> \
  --board-policy AUTO_ALL
```

`--board-policy` 默认为 `AUTO_ALL`；只有明确采用 Host-only 策略时才使用 `HOST_ONLY`。finalizer 读取已经结束的 `train_workflow_summary.json`、现有 `runs/<run_id>/train_verify_summary.json` 和 facts，不新增 facts schema 字段，不重跑训练、Host、构建、烧录或串口验证。

它会逐项调用现有 `aggregate_training_results.aggregate_case(root, run_id, item)` 重新读取当前 case 证据并复核 aggregate，包括 graph gate；随后调用 `audit_manual_inputs.py --publication final`，并检查 `facts.checks.required/observed`、board policy、路径与 hash。结果写入：

```text
<run-dir>/train_final_verdict.json
```

命令返回 0 表示业务 `verdict=PASS`。证据缺失或无法确认输出 `NOT_VERIFIED`；明确失败、aggregate 被手工改写、证据 hash 变化或已执行板测失败输出 `FAIL`。合法 board skip 按前述 policy 表判定：只有显式 `HOST_ONLY` 且其他必需检查通过时才可业务 PASS，仍不声明板测通过。

`delivery_status` 与 `verdict` 分开记录。当前 finalizer 在业务结论非 FAIL、Host 状态及 `host_aggregate`、`checks`、`audit` 均为 PASS、board 状态为 `NOT_RUN` 时，输出 `delivery_status=HOST_PASS_BOARD_NOT_RUN`；其他情况沿用 `verdict`。因此不能把该交付标签当成业务 PASS，也不能把 `NOT_REQUESTED` 改记成 `NOT_RUN`。

finalizer 必须在调度结束后独立运行，不能放入调度器的 `final` 阶段，否则会形成读取终态 summary 的循环依赖。`final` 仍负责在成功或失败时同步真实结果和文档。

## 板端参考与锁定 golden 绑定

finalizer 在每个 case 重放 comparator 前，调用只读 helper `check_board_reference.py` 的 `check_expected_against_golden(case_path, locked, expected, report)`。该检查使用原始 case 目录中的 golden，不把 run 目录内的归档 case 副本当作相对路径基准。

- 先校验 locked golden SHA256，以 `np.load(..., allow_pickle=False)` 读取 NPZ，检查 keys、shape 与有限值。输出和 loss 是 FP32；训练权重按 case 声明为 FP32 或 INT32。
- 仅支持当前标准 Host 格式：Predict 使用 `outputs[:-1]`，Eval 覆盖 `checkpoints=[0,1,steps]` 的全部 outputs 与 weights reference；`before/after` 按明确的 weight name 映射到初末 checkpoint。映射必须唯一且覆盖完整集合，不做任意协议翻译。
- FP32 输出和参考值展平后必须与 golden 精确相等，不用 `allclose` 放行参考偏差；INT32 训练权重逐元素整数精确相等。INT32 输出不支持。report 及 expected 可选的 `tolerances` 必须与 Host 常量 `ATOL=RTOL=1e-5` 一致；comparator CLI 也使用该常量，不从 report 取容差。仍兼容 expected 未写 `tolerances` 字段。
- helper 的 `FileNotFoundError` 表示缺失 golden，不能确认为 PASS；内容矛盾的 `ValueError` 转为完整性 FAIL。任一已确认的 FAIL gate 不会被后续缺证据异常降为 NOT_VERIFIED。通过后的 board gate 记录逐 case `reference_bindings`（golden hash、tensor 数量及容差）。

## verdict 输出不覆盖

默认输出为 `<run-dir>/train_final_verdict.json`；`--output` 可指定新文件路径。输出不得覆盖 facts、两份文档、summary、证据、已有 verdict 或其他任何既有目标；明确的输入路径即使缺失也不能用来写 verdict。相对路径别名、硬链接、符号链接不能绕过保护。

重复执行请使用新的 `--output` 文件名，如 `train_final_verdict-recheck-01.json`（相对输出路径以当前工作目录为基准）。脚本在目标目录写入临时文件，再通过不覆盖的原子链接发布，不使用 `os.replace`。发生碰撞或文件系统不支持该操作时，仅向 stdout 报 FAIL（`output_written=false`，退出码 2），保留既有文件，不回退到其他路径写入。

## 跨平台审计的证据可访问性

manual audit 和 finalizer 所在环境必须能读取本轮 summary 引用的原工具包证据（包括 converter 与静态库），并按原记录校验文件 hash；只有 summary 或工具名称不足以通过审计。

- 明确的绝对 evidence 路径复用 Host aggregate 的 `resolve_evidence_path`，仅对 Windows 盘符与 `/mnt/<drive>/...` 做确定性映射；相对路径仍按 opdir resolve 并检查边界。不放宽越界、符号链接或 hash 门禁。
- 位于 Linux/WSL 用户目录下的绝对路径是 WSL 原生路径，不是 Windows 盘符别名。不得猜测映射、伪称 Windows 已读取，或跳过不可读工具的 hash 检查。若本轮工具证据位于这类路径，应在能访问原工具包的 WSL 环境执行 manual 审计，通过后再按文档流程发布。
- Windows 下的 Host/board 阶段重放可单独留存报告，不替代完整 manual 审计，也不补造 scheduler 历史；缺少该历史时，工作流终态仍为 `NOT_VERIFIED`。
