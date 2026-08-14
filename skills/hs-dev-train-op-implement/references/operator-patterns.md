# 训练算子 backward 模式

本文件用于在编码前判断 backward 支持边界。先分类，再写 `backward-contract.md`。

## shape-only / view 类

例如 Reshape、Squeeze、Unsqueeze。通常只需要把 `dy` reshape 回 forward 输入形状，不对 shape、axes 等结构 tensor 求导。

注意 converter 优化后 forward primitive 可能已经归一化为 Reshape。以 `CoderGraph` 中真实 primitive 为准。

拒绝边界：

- dynamic rank；
- runtime shape tensor；
- backward 需要未保活的 forward output。

## slicing / scattering 类

例如 Slice、StridedSlice、Gather。Backward 通常是把 `dy` scatter 回 input gradient。

必须冻结：

- begin/end/stride/axis 是否为常量；
- 重复 index 的累加语义；
- out-of-bound 和 negative index 规则；
- output gradient 与 input gradient 是否可能 alias。

结构 tensor 不可微。重复 index 需要明确是否由 kernel 内累加，还是由 TrainingGraph 的 GradAccum 节点承担。

## concat / split 类

Concat backward 是按 axis 切分 `dy`。Split backward 是 concat 多路 `dy`。

必须冻结：

- axis 是否常量；
- 每个输入 shape 是否静态；
- 多分支 output gradient 的存在性；
- 缺失分支 gradient 是否允许 zero-fill。

当前框架若不能表达多 forward output 在 active loss path 上的保活，不要绕过内存规划。

## permutation 类

Transpose backward 是反 permutation。Permutation tensor 是结构输入，不可微。

必须冻结：

- permutation 是否编译期常量；
- rank 上限；
- repeated 或非法 permutation 的转换期拒绝。

## trainable linear 类

例如 Conv、MatMul、Dense。Backward 通常产生 activation grad 与 weight/bias grad。

必须冻结：

- differentiable input 和 trainable input 的区别；
- weight layout；
- bias optional；
- group、stride、dilation、pad、transpose 等属性；
- branch fan-out 时 parameter gradient 的累加归属。

如果需要 workspace、大型 im2col 缓冲或特殊 lifetime，不要在 TrainNodeCoder 临时分配 runtime buffer；应先升级框架需求。

## elementwise 类

例如 Add、Mul、Relu、Sigmoid。Backward 可能需要 forward input 或 forward output。

必须冻结：

- broadcasting 反向 reduce 规则；
- 是否需要 forward input；
- 是否需要 forward output；
- activation mask 或 derivative 是否可从 input 直接计算。

当前通用 GradRule 只能声明 retained forward inputs。需要 retained forward outputs 时，确认框架已有支持，否则停止。

## branch fan-out

算子 coder 不负责手写分支梯度累加。多 consumer 的同一 tensor gradient 应由 TrainingGraph 的 GradAccum 节点合并。

实现时只产生本 backward node 的局部贡献，并通过框架提供的 gradient 地址访问接口读取/写入。

## 常见失败签名

| 现象 | 优先归因 |
|---|---|
| generated C 中出现 forward output 地址但运行时数据无效 | forward output 未被 required/retained |
| 同一 tensor 多分支梯度少一路 | GradAccum connectivity 或 GradRule output mapping |
| generated project 缺少 fp32_grad 源文件 | TrainNodeCoder source collection 或 CMake 列表 |
| 转换期成功，host-native 链接失败 | kernel header/source 收集不完整 |
| 训练一步 loss 对齐但 weight 不变 | trainable input indices 或 optimizer gradient mapping |
| inference-only 生成物含 grad symbol | backward coder/source collection 泄漏到推理路径 |

