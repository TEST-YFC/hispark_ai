# 生成训练 observer 说明

当前检出的 Micro 生成器不提供训练 observer。源码中不存在 `MSLITE_TRAIN_OBSERVER`、`GetTrainWeightCount<model_index>()` 或 `GetTrainWeight<model_index>()`；因此不能从生成模型运行时地址读取板端训练权重。

当前唯一相关能力是 `MSLITE_TRAIN_BENCHMARK`。它用于 Host/native benchmark 的文件导出（例如 `ExportN` 和 `manifest.json`），不能证明 RISC-V 固件中存在运行时 accessor，也不能作为板端参数快照。`const` 初始数组、Host 文件或 sample 自报的 `parameters_observed` 都不能替代实际 mutable weight 地址。

因此当前训练板验证边界为：

- `build_micro.py --config ...` 在转换前失败，原因是 `training_observer_unavailable_for_micro_generator`；
- `prepare_training_sample.py` 和 `verify_wiring.py` 对该能力同样 fail closed，不生成或要求不存在的 `GetTrainWeight*` 符号；
- 不调用 `hs-dev-build`、`hs-dev-flash` 或 fbb flash，不生成板端 PASS；
- Host 训练仍可独立执行，板端结果记录为 `NOT_RUN`，而不是 `PASS` 或伪造的 output-only 完整训练结论。

未来若要恢复板端训练，必须一次性设计并验证生成器代码、CMake 选项、Micro receipt 能力字段、sample 接线、wiring/nm 检查、SDK 构建、`hs-dev-flash` 烧录和串口比较；不能只添加一个命令行选项或在 sample 中声明外部函数。
