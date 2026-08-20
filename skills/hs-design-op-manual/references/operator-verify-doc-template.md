# {Op} 算子验证文档

> 状态：{PLANNED | INCOMPLETE | FAIL | PASS | HOST_ONLY_PASS}
>
> 本文只记录测试设计、Host/固件/烧录/串口/板端验证结果和证据索引，不重复描述完整规格和软件设计。
>
> 文件位置：`<opdir>/docs/{op}-operator-verify-doc.md`

## 1. 测试设计

### 1.1 测试覆盖原则

{输入规模、属性选择、边界、折叠/重写、量化/原生整数和 GT 判定方法。}

### 1.2 用例总表

| 用例编号 | 框架/source entry | 模型 dtype | 已覆盖运行通路 | input_shape | 输入数据特征（value_domain） | 算子属性 | 预期输出 |
|---|---|---|---|---|---|---|---|
| TC-001 | ... | ... | ... | ... | ... | ... | ... |

### 1.3 预期运行矩阵

| 验证阶段 | 预期覆盖 |
|---|---|
| Host | ... |
| 固件构建 | ... |
| 真实板烧录与串口 | ... |
| 板端精度 | ... |

## 2. 运行验证结果

### 2.1 阶段汇总

| 阶段 | 结果 | 数量 | 原因/证据 |
|---|---|---|---|
| Host 全量验证 | PASS/FAIL/NOT_RUN | passed/expected | ... |
| 固件构建矩阵 | PASS/FAIL/NOT_RUN | built/expected | ... |
| 真实板烧录与串口 | PASS/FAIL/NOT_RUN | executed/expected | ... |
| 板端精度矩阵 | PASS/FAIL/NOT_RUN | passed/expected | ... |

### 2.2 每个用例的阶段状态

| 用例编号 | Host | 固件构建 | 真实板烧录 | 板端精度 |
|---|---|---|---|---|
| TC-001 | ... | ... | ... | ... |

### 2.3 结论

{必须区分 Host、固件构建和真实板测。只要存在 NOT_RUN/PENDING，整体不得写 PASS；失败必须写明原因和下一步。}

## 3. 证据索引

- `docs/operator-manual-facts.json`
- `scripts/op_spec.py`
- `verify_summary.txt`
- 固件构建报告和 `.fwpkg`
- 烧录 JSON、串口日志和板端逐用例结果
