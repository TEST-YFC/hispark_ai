# 训练文档事实与审计

`operator-training-manual-facts.json` 保存已经核对的内容摘要、计划和结果引用。它不是验证结果生成器。下面的字段和固定渲染由 `scripts/training/audit_manual_inputs.py` 校验，不复用推理的 `op_spec.py` 或审计脚本。

## 1. 设计主源

以下文件均在 `<opdir>` 内，必须记录相对路径与真实 SHA256：

- `docs/forward-prerequisite.md`
- `docs/backward-contract.md`
- `docs/train-link-analysis.md`
- `docs/implementation-contract.md`
- `docs/generated-code-inspection.md`
- `scripts/train_case_spec.py`
- 每个 `cases/<case_id>/case.json`

初稿可以记录未执行的代码检查计划。尚未生成模型时，case.json 可先确定 case_id、kind、verification_kind、test_point 和计划；运行前须补成 Host 执行器要求的完整输入。缺少上述设计和计划资料时返回上游补齐，不能用空文档通过检查。

终态还必须记录本轮聚合报告和每个单 case summary 的 hash。执行前就被环境阻塞的用例，由调用方写身份完整、`status=NOT_RUN`、`numerical_pass=false` 和原因的单 case 记录，不能假称 runner 已执行。实际执行后失败的 case 保留 FAIL。

## 2. facts 字段

下面是结构示意，文字和 hash 必须从当前任务填写；字段中的状态不能由目录是否存在推断。

```json
{
  "schema_version": 1,
  "verification_kind": "training",
  "publication": "initial",
  "operator": "Op",
  "run_id": "run_001",
  "framework_scope": ["onnx"],
  "requires_freezing": false,
  "capabilities": {
    "parser": "NOT_RUN", "selection": "NOT_RUN", "helper": "NOT_RUN",
    "development_chain": "NOT_REQUESTED", "graph": "NOT_REQUESTED",
    "memory": "NOT_REQUESTED", "export": "NOT_REQUESTED",
    "freeze_snapshot": "NOT_REQUESTED",
    "matmul_kernel_dw_null_check": "NOT_REQUESTED"
  },
  "capability_notes": "说明所检查的源码位置和实际限制；不需要冻结时明确未请求。",
  "design": {
    "scope": "规格、dtype/shape、前向前置和复用依据。",
    "backward": "数学公式、输入梯度映射、保留张量、广播和梯度累加。",
    "implementation": "GradRule、TrainNodeCoder、NNACL 与构建文件的位置和实现决定。",
    "limits": "支持和拒绝范围、可选梯度条件及未实现功能。"
  },
  "test_design": "新最小训练模型的路径、上游可训练参数、初始化、序列、Eval 输入和标签、参考实现、容差、用例覆盖及板端计划。",
  "host_status": "NOT_RUN",
  "host_reason": "实现前仅发布计划。",
  "board_status": "NOT_RUN",
  "board_reason": "Host 尚未执行。",
  "sources": [{"path": "docs/forward-prerequisite.md", "sha256": "实际SHA256"}],
  "expected_cases": [
    {"case_id": "TC_001", "kind": "numerical", "test_point": "反向路径和上游更新",
     "status": "NOT_RUN", "reason": "尚未执行。"}
  ],
  "checks": {
    "required": ["package_source_freshness", "target_backward_path", "training_graph_and_memory", "inference_isolation"],
    "observed": [
      {"name": "package_source_freshness", "status": "NOT_RUN", "reason": "尚未构建。"},
      {"name": "target_backward_path", "status": "NOT_RUN", "reason": "尚未转换。"},
      {"name": "training_graph_and_memory", "status": "NOT_RUN", "reason": "尚未转换。"},
      {"name": "inference_isolation", "status": "NOT_RUN", "reason": "尚未生成对照工程。"}
    ]
  }
}
```

`sources` 示例只展示一行，实际必须包含全部主源和本轮证据。`operator/run_id/case_id` 只用英文字母、数字、下划线和连字符。

`checks.required` 至少保留上述四项，按任务增加必测项；`observed` 每项都要有状态和原因。PASS/FAIL 检查还要有 `evidence` 相对路径，且被 `sources` 记录。未执行项不伪造观察内容。

冻结能力状态使用 `AVAILABLE/MISSING/BLOCKED/NOT_RUN/NOT_REQUESTED/UNSUPPORTED`。当 `requires_freezing=true` 且 Host 为 `PASS` 时，必须同时具备五项通用能力：`development_chain`、`graph`、`memory`、`export`、`freeze_snapshot`，并通过对应的开发链、训练图、训练内存、权重导出和冻结快照检查。MatMul 的 `matmul_kernel_dw_null_check` 仅在该算子适用时要求，不是通用冻结必填项。

case 级的离散梯度边界能力不新增到 facts 顶层 schema，仍由锁定的 `case.json` 表达。
当 `graph_expectations.gradient_barrier=true` 时，测试设计和验证文档必须写明
`parallel_upstream_paths`、`barrier_upstream_paths`、`barrier_weights` 及对应
`barrier_unchanged/<name>`、`upstream_update/<name>` 证据。训练权重 dtype 仅支持
`float32|int32`；`int32` 按整数精确相等记录。该能力按 case 声明，不扩大成通用混合精度训练。

## 3. 终态聚合报告

路径固定为 `runs/<run_id>/train_verify_summary.json`。顶层 status 只表示 Host 聚合状态，不包含板端结论。所有 case 使用 facts 顶层同一个 run_id，不在 expected_cases 中另选历史运行：

```json
{
  "schema_version": 1,
  "verification_kind": "training",
  "run_id": "run_001",
  "status": "NOT_RUN",
  "cases": [
    {"case_id": "TC_001", "kind": "numerical", "test_point": "反向路径和上游更新",
     "status": "NOT_RUN", "reason": "缺少当前源码工具包。",
     "summary": {"path": "runs/run_001/TC_001/train_summary.json", "sha256": "实际SHA256"}}
  ]
}
```

case 顺序与 facts 和计划一致，不得漏项、重复或加入其他运行结果。聚合行和单 case summary 的 run_id、case_id、类型、测试点、状态必须相符。聚合文件和单 case 文件均加入 facts.sources，summary 引用与 sources 中对应记录精确一致。

Host PASS 要求：至少一个数值用例；全部数值用例 `PASS` 且 `numerical_pass=true`；全部预期拒绝用例 `PASS_EXPECTED_ERROR` 且不计数值通过；所有必需结构与来源检查为 PASS。实际用例 FAIL 不能被汇总成 NOT_RUN 或 BLOCKED。

板端未执行写 NOT_RUN 和检测/前置原因。板端已执行时，`board_evidence` 指向 sources 中的本轮训练板测 JSON：单 case 直接指向 comparator report，多 case 指向最小 `board_matrix.json` 索引。该 JSON 至少含 `verification_kind`、`run_id`、`status`；详细用例矩阵和数值由板端验证步骤核实。文档审计不替代板端比较器。

## 4. 候选内容与结果含义

设计正文由 `design` 四个章节及冻结能力说明组成；验证正文由测试设计、本轮结果、全部 case、结构检查和证据索引组成。渲染器使用固定章节，facts 中可写完整段落、公式、源码落点和表格，不应只填一句空泛概述。

候选必须与当前 facts 渲染内容完全一致，防止正文把 NOT_RUN 写成 PASS。源码事实仍由开发步骤核对；文件 hash 只能证明内容未变，不能证明事实本身正确。

默认执行器不导出原始梯度，文档明确保留未测说明；有额外直接梯度测试时，在 test_design 和对应检查证据中单独记录其结果，不能把默认参数比较改称梯度逐元素验证。

PASS 或 PASS_EXPECTED_ERROR 的单 case summary 必须包含固定执行器生成的 commands、stages、evidence、not_evaluated 和 case_sha256。审计核对命令退出码、阶段完整性、日志及运行证据的 hash，数值检查名称与锁定用例的输出/权重/步数对应。审计应在能读取这些原始路径的同一 Host 环境执行；迁移结果时不能只复制一个 summary 并保留已失效路径。
