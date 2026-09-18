# 生成训练 observer 说明

生成训练模型可在 CMake 配置时启用 `MSLITE_TRAIN_OBSERVER=ON`，而不启用
`MSLITE_TRAIN_BENCHMARK`。生成的 `GetTrainWeightCountN()` / `GetTrainWeightN()`
是模型内部 accessor，不改变公共 ABI。

`GetTrainWeightN(index, &metadata, &data)` 当前接受生成 metadata 标记为
`float32` 或 `int32` 的训练权重。bytes 非零且与 dtype 对应、shape 元素数与 bytes
一致；越界 index、NULL 输出指针、未绑定的 runtime weight 指针和 bytes 不匹配都会
被拒绝。`data` 指向 LoadWeight 后的训练 RAM，而不是只读的 `_const` 初始数组。
调用者应遍历 count 和 metadata 的 `raw_name/rank/shape`，不要假设 `m0_weight0`、
参数顺序或元素个数。

`float32` 权重仍按训练容差比较；`int32` 权重按整数精确相等判断。当前不支持其他
训练权重 dtype，也不把这个能力扩大成通用混合精度训练。

本说明只描述生成接口。真实结论仍须使用与当前源码一致的 converter 生成训练模型，
完成 Sample 接线、WS63 构建、烧录和串口采集，并按训练验证流程比较完整数据。
