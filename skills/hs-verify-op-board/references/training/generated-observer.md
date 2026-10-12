# 生成训练 observer 说明

训练 observer 属于验证基础设施，不属于算子特性代码。当前 Skill 不修改 `src/mindspore-lite` 生成器，也不向共享 SDK 写 observer；`build_micro.py` 在每个独立 `<opdir>/runs/<run_id>/<case_id>/micro/` 的生成工程内写入 `src/model0/observer_adapter.c/.h`。

adapter 使用本轮生成 `weight0.c` 的 `model_params[]`，通过 `*model_params[i].addr` 读取 mutable RAM 权重；权重名称、dtype、shape 和元素字节数来自 Host 已锁定的 `case.json`，并与生成 C 的参数数量、offset、size 校验。它不复制默认权重、不硬编码运行时地址或偏移，也不写入算子源码、共享模板或 SDK 源码。

训练构建必须同时满足：

- `--case-json` 指向当前 Host 通过的锁定 case；
- adapter 只位于本轮 Micro 工程 `src/model0/`，路径和 SHA256 写入 `micro_build_receipt.json`；
- `libnet.a` 中由 archive-aware `nm` 定义 `GetTrainWeightCount0` 与 `GetTrainWeight0`；
- receipt 标记 `training_observer=true`、`nm_verified=true`，且 sample、integration、wiring 各阶段都核对同一 observer 能力和身份信息。

`MSLITE_TRAIN_BENCHMARK` 仍只用于 Host/native 文件导出（例如 `ExportN` 和 `manifest.json`），不能替代 RISC-V adapter，也不能把 Host 文件当作板端参数快照。

当前 WS63 脚本/fixture 测试覆盖 adapter 生成和 capability receipt；真实板端仍必须经过 SDK 构建、固件内容检查、烧录、串口采集和逐元素比较，脚本通过不等于 `TRAIN_BOARD_VERIFY=PASS`。任何 metadata、ABI、编译符号或 receipt 校验失败都记录 `NOT_RUN`/失败，不能只有 output 通过就宣称整体通过。
