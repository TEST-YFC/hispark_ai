# Board accuracy contract

目录：

- [step6：计算精度并分流](#step6计算精度并分流)

以下内容从入口按需下沉；逐 Tensor、逐 case 和矩阵统计规则保持不变。

## step6：计算精度并分流

唯一精度入口是已存在的 `board_accuracy.py`：

```bash
python3 <skill_root>/scripts/board_accuracy.py \
  --gt-dir <same-run case gt directory> \
  --monitor <current-run serial text file> \
  [--quantized]
```

每行还必须写入：

```text
<board-results>/<framework>/tc<case_id>/<mode>/board_result.json
```

字段至少包含`run_id/operator/framework/case_id/mode/status/reason`以及同轮
`model/input_dir/gt_dir/firmware/flash_log/monitor/accuracy_log/serial_probe`绝对路径。
`serial_probe`必须指向本轮 `probe_serial_ports.py` 回执；PASS行缺任一证据无效。

脚本解析 benchmark `PrintTensorHandle` 的 `Elements`/`Shape`/`Data`，或项目连续输出的 `[AI_MCU] Shape: [d1,d2,...]` 与 `[AI_MCU] Data: [v1]...`。它先精确核对 Tensor 数量、元素数和 shape，再使用与 Host 相同的余弦语义和签收门槛逐 Tensor 比较：fp32 `cos >= 0.999`，INT8 `cos >= 0.99`。只有 `[AI_MCU] Data` 而没有 shape 时输出 `SHAPE_UNVERIFIED` 并拒绝签收。未带 `OUTPUT: index=N` 的连续 Shape/Data 协议只支持单输出、单轮推理；出现多个没有 round/output 标识的 Data 行时按协议歧义 FAIL，不静默取第一条。Host 与 Board 复用同一 GT，Board 不得另设更松阈值把 Host 不合格精度判绿。

所有行到达`PASS|FAIL|NOT_RUN`终态后运行：

```bash
python3 <skill_root>/scripts/board_matrix_report.py \
  --expected <same-run board_expected_matrix.json> \
  --results-dir <board-results> \
  --output-dir <board-report-dir>
```

脚本机械拒绝缺行、重复行、跨run/operator、Host非PASS、额外case以及PASS证据缺失，输出
`board_case_results.json`和`board_verify_summary.txt`。每行的“测试点”只能读取 Host manifest 冻结的
`test_point`，不得在板端另写或改写。后者必须逐行列出
`framework tc<case_id> mode status test_point=<测试点>`，并分别统计
`expected/recorded/executed/pass/fail/not_run`：`recorded`只表示已有一条结果或未执行原因记录；
`executed=pass+fail`只统计真正进入板端执行并得到PASS/FAIL终态的行；`NOT_RUN`绝不能计入
`executed`。因此“24条NOT_RUN记录”的正确结果是`recorded=24 executed=0 not_run=24`，不能输出
`executed=24 not_run=24`。

只有 `expected=recorded=executed=pass` 且 `fail=not_run=0` 时才能输出
`BOARD_MATRIX_GATE=PASS` 和 `ACCURACY_VERDICT=PASS`。单条或部分用例 PASS 只能作为逐行结果，不能写成
“板端验证通过”。

失败分流：

| 证据 | owner |
|---|---|
| 串口无输出、启动失败、模型/输入未接入 | workflow stage6 的 sample/adaptor/固件接线 |
| 固件未烧录或烧录 JSON 失败 | `hs-dev-flash` |
| Host 同 case PASS、板端 Tensor 可解析但精度 FAIL | 本 skill 输出对比证据，由 workflow 回流实现或板端接入 |
| GT、模型、输入跨轮或 case 不一致 | 回 step0 重新选择，不运行比较 |
| Tensor 数量/shape 不匹配 | 先核对固件模型和串口格式，再决定是接入还是算子缺陷 |

不要在本 skill 修改 kernel/opcoder、降低阈值或重写 GT。把首个失败原文、逐 Tensor 余弦、固件/case 身份和建议 owner 返回 workflow。
