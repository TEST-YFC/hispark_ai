# Optimization Workflow

## 1. 冻结任务

开始前明确 operator、framework、mode、case、target、源码根目录和验证范围，并确认本次修改的是
NNACL，还是当前 case 的生成代码。检查现有改动属于谁；不得清理、覆盖或 stash 用户的改动。

正式实验必须从干净的源码检出状态开始。NNACL 轮次必须列出允许修改的相对路径；生成代码轮次必须保持
MindSpore Lite 源码无改动，并将差异保存在生成代码 snapshot 中。

## 2. 理解代码并采 baseline

阅读目标 kernel、Micro Coder 以及代表性 case 的 `net0.c`，记录实际调用链、shape、dtype、热点、
静态参数、精度风险和允许修改的文件。

在开始任何构建之前，先准备 baseline 运行记录：

```bash
python3 <skill>/scripts/run_optimization.py prepare \
  --repo-root /abs/HiSpark.AI \
  --operator ExampleOp --case example_case \
  --framework onnx --mode int8 --target ws63 \
  --task-type baseline \
  --ticks-per-us 24.0 --window 50 \
  --stable-tolerance 0.05 --timeout-seconds 110
```

命令会输出本轮唯一的 `RUN_MANIFEST` 和 `EXECUTION_ID`。后续构建、metric 采集和证据绑定均使用这
两个值。准备阶段要求源码干净；baseline 已存在时拒绝覆盖。

依次执行：

```text
hs-debug-op-host-accuracy
  → timed firmware build
  → flash + board accuracy
  → target latency
  → bind all evidence
  → record
```

把各阶段原始输出绑定到同一 manifest：

```bash
python3 <skill>/scripts/run_optimization.py bind \
  --manifest <RUN_MANIFEST> --kind host --source /abs/verify_summary.txt
python3 <skill>/scripts/run_optimization.py bind \
  --manifest <RUN_MANIFEST> --kind build --source /abs/firmware_build.log
python3 <skill>/scripts/run_optimization.py bind \
  --manifest <RUN_MANIFEST> --kind flash --source /abs/flash_board.log
python3 <skill>/scripts/run_optimization.py bind \
  --manifest <RUN_MANIFEST> --kind board --source /abs/flash_board.log
python3 <skill>/scripts/run_optimization.py bind \
  --manifest <RUN_MANIFEST> --kind metric --source /abs/onboard_metric.json
python3 <skill>/scripts/run_optimization.py bind \
  --manifest <RUN_MANIFEST> --kind serial --source /abs/serial_raw.log
```

WS63 的 `flash_board.log` 由 target runbook 中负责记录运行身份的包装脚本生成，同时包含 flash 和 accuracy 的最终状态，
因此要分别绑定为两类证据。绑定会把文件复制到本轮目录并冻结 SHA256；绑定后修改文件会使归档
失败。完整归档还必须提供真实 firmware、生成代码、CPU/RISC-V `libnnacl.a` 和 target SDK：

```bash
python3 <skill>/scripts/run_optimization.py record \
  --manifest <RUN_MANIFEST> \
  --firmware /abs/model.fwpkg \
  --codes-dir /abs/generated/micro \
  --cpu-archive /abs/cpu/libnnacl.a \
  --riscv-archive /abs/riscv/libnnacl.a \
  --sdk-root /abs/ws63-sdk
```

当前仓库的归档布局：

```text
<repo>/src/mslite-op-output/{Op}/performance/{target}/{framework}/{case}/
├── runs/{execution_id}/               # 本轮 manifest 和已绑定证据
└── experiments/
    ├── baseline/
    │   ├── result.json
    │   ├── report.md
    │   ├── patch.diff
    │   ├── evidence/
    │   ├── artifacts/
    │   └── snapshot/
    ├── {execution_id}/                # accepted/rejected 优化轮次
    └── {execution_id}_failed/         # 失败轮次
```

## 3. 写计划并等待确认

在算子项目的性能目录中编写 `plan.md`，至少说明对代码的理解、baseline、瓶颈、每个变量的修改方式、
预期效果、风险以及允许修改的文件。不能估计收益时写未知。用户确认前不改源码。

## 4. 逐变量执行

验证每个变量时，都从 baseline 对应 commit 的干净检出状态开始，不叠加上一轮的修改。

NNACL 轮次在修改前准备 manifest：

```bash
python3 <skill>/scripts/run_optimization.py prepare \
  --repo-root /abs/HiSpark.AI \
  --operator ExampleOp --case example_case \
  --framework onnx --mode int8 --target ws63 \
  --task-type optimization --change-kind nnacl \
  --variable candidate-change --note "describe this variable" \
  --allowed-change mindspore-lite/src/litert/kernel/cpu/nnacl_c/int8/example.c \
  --ticks-per-us 24.0 --window 50 \
  --stable-tolerance 0.05 --timeout-seconds 110
```

生成代码轮次改用 `--change-kind generated-code`，不传 `--allowed-change`。归档时生成代码
snapshot 必须与 baseline 不同，MindSpore Lite 源码必须仍然干净。

完成单一修改后：

1. NNACL 轮次先刷新实际使用的 CPU package，再运行全部预期的 Host 用例。
2. Host PASS 后刷新 RISC-V package，构建并烧录计时 firmware。
3. 取得 `FLASH_VERDICT=PASS` 和 `ACCURACY_VERDICT=PASS` 后采 latency。
4. 绑定六类必需证据并归档。
5. 确认实验记录已经写入归档后，才能撤销本轮源码修改并重新刷新 package。

任一阶段失败也必须归档：

```bash
python3 <skill>/scripts/run_optimization.py fail \
  --manifest <RUN_MANIFEST> \
  --stage host_accuracy --detail "HARNESS_EXIT=1" \
  --log /abs/failed.log
```

`stage`、变量以及各级目录名都必须使用符合安全要求的标识符，不能包含路径分隔符或 `..`。

## 5. 汇总

```bash
python3 <skill>/scripts/run_optimization.py summarize \
  --repo-root /abs/HiSpark.AI \
  --operator ExampleOp --case example_case \
  --framework onnx --target ws63
```

只有精度全通过且 latency 严格低于 baseline 的轮次标为 `ACCEPTED`；speedup 只在呈现结果时
格式化，判定时必须使用未经四舍五入的值。最终列出全部 execution ID 和各阶段状态。

## 禁止事项

- 未完成 baseline 或计划确认就修改源码；
- 混用来自不同源码 commit、测量协议或 case 的证据；
- 一轮修改多个变量，或删除失败/退化轮次；
- 修改 NNACL 后继续消费旧 package/archive；
- 用 Host 耗时、估算值或手填数字替代 target metric；
- 尚未归档就撤销本轮实验修改；
- 修改其他 Skill 的脚本来适配某个优化轮次；
- 同一错误无限重试；连续两次相同设备错误后停止并报告。
