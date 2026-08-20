# 训练实现指南

## 文件落点

常见训练实现落点：

```text
tools/converter/micro/coder/train/
tools/converter/micro/coder/train/opcoders/
src/litert/kernel/cpu/nnacl_c/fp32_grad/
```

注册必须绑定到 `kBackward + PrimitiveType`。不要只新增源码文件而忘记显式 Micro CMake 列表。

## GradRule 检查表

- 是否误把 shape、axis、perm、pads、begin/end 标为 differentiable。
- 是否把 parameter gradient 放进 `trainable_input_indices`。
- 是否声明 backward 需要的 forward input。
- 是否依赖 forward output；若依赖，builder 是否有可验证的保活机制。
- 同一个 rule 被 builder 调用两次时是否仍确定性。

## TrainNodeCoder 检查表

`Prepare()`：

- forward input/output 数量；
- gradient IDs 与 forward tensor 位置匹配；
- dtype 为 FP32；
- static shape、rank、非空 tensor；
- constant axes/shape/perm 等属性合法；
- gradient bytes 与目标 tensor bytes 对齐；
- 不支持组合返回 `RET_NOT_SUPPORT`。

`DoCode()`：

- `ForwardAddr()` 只用于 forward values；
- `GradAddr()` 只用于 gradients；
- `OutputGradForTensor()` 用于定位 output gradient；
- header/source 收集完整；
- `Serializer` 只输出一个 tagged block；
- 不写 runtime allocation、m0 offset 或数值循环。

## NNACL fp32_grad 检查表

- 函数接口无状态；
- 不 heap allocate；
- NULL 参数含义明确；
- alias 行为明确；
- 对非法 shape/axis 的防护由转换期承担；
- 可用小型 C 单元测试或 generated host-native 测试独立验证公式。

## 生成物检查

训练实现完成后必须实际查看：

- `training_graph.dot` 是否包含预期 Backward 节点和 GradAccum；
- `training_memory.json` 是否保活必要 forward input；
- `net0.c` 是否调用预期 fp32_grad kernel；
- `net.cmake` 是否收集新增 kernel 源文件；
- inference-only conversion 是否没有训练符号和 fp32_grad 源泄漏。

