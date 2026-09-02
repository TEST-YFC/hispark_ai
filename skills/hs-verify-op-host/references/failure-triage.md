# Host failure triage

目录：

- [失败排查](#失败排查按优先级)
- [范围、失败回流与底线](#范围失败回流与底线)

以下内容从入口按需下沉，失败证据和回流 owner 不变。

## 失败排查(按优先级)

### converter CLI 预检与可复现回退

如果固定驱动无法启动，优先直接重跑下面的harness入口。它会在启动converter的同一进程中
自动定位和配置本轮`MSLITE_PKG`的动态库；以下`--help`仅用于读取已生成日志后的诊断，不要求
用户永久设置环境变量：

```bash
CONVERTER="$MSLITE_PKG/tools/converter/converter/converter_lite"
test -x "$CONVERTER" || { echo "CONVERTER_MISSING=$CONVERTER"; exit 1; }
python3 "$SKILL/scripts/run_all_cases.py" --run-id "$RUN_ID" \
  --spec "$PROJ/scripts/op_spec.py" --framework onnx --target x86
```

若包内缺少`libmindspore_converter.so`，harness会明确报告工具包不完整；只有这种需要重建/
重新下载工具包或发现多包身份冲突的情形才请求用户确认。`--help` 失败归因于工具包/环境并
停止当前验证；单个模型转换失败则保留该路径的
`stderr.log`，回流模型/spec 或算子实现 owner，不能手工修改通用 harness 绕过错误。
该回退仍使用 `run_all_cases.py` 的固定驱动、余弦和门禁，不得自行替换 converter 参数或 GT。

- **某路径 `ERR` / 没解析到余弦** → 转换或编译失败。看该路径 `stderr.log`;`[ERR]` 行指明在 converter/cmake/make 哪步挂。
  `converter_lite` 报错常是该算子未注册/不支持,或某属性组合无法处理——这是**需要上报的结论**(实现算子支持是另一项独立工作)。
- **报"算子未注册/不支持"时,先判用例是否发出了正确的算子,再下结论。** 用例可能发成了语义相近但不同的 builtin(如非广播版 vs 广播版)。若是用例发错算子,**改用例**;**绝不**为把红变绿而在转换器里给一个错误或无关的算子名硬注册 parser 别名——那与放宽阈值同属作废行为。
- **fp32 余弦偏低(<0.999)** → 算子内核/代码生成的真实数值 bug。先用 fp32 隔离,再看 INT8。
  例外仅一种:该用例预期输出量级 < `1e-4`(低于 benchmark `%f` 打印分辨率,见「用例设计原则」的
  打印分辨率约束)。判别方法:加载该用例参考 `.npy` 看输出量级,并与 `stdout.log` 里打印的张量对照
  ——若打印值全是同一截断值/零而参考非零,是用例值域设计违反约束,**按约束修正值域并重跑**(修改
  对照照常列入汇报);若输出量级正常,则按真实 bug 排查,不得借打印精度开脱。
- **fp32 过、INT8 偏低** → 量化路径问题。
- **`INT8_NOT_GENUINE`** → 该路径生成代码里没调到 int8 kernel 符号,量化把算子旁路成了 fp32(发了 fp32 opcoder)。两种根因:①算子漏进 `support_int8_ops_` 或 int8 OpCoder 没注册——保留证据并交 workflow 回流 `hs-dev-op-implement`;②算子 int8 codegen 用的符号名与默认 `{OP_NAME}Int8` 不同(如激活子类型)——在 `op_spec.py` 声明正确的 `INT8_KERNEL_SYMBOL`。**不要**为消除它去设 `INT8_KERNEL_SYMBOL=""`；只有原生整型/索引/非 float 输出这类量化 INT8 豁免算子可用它,且 PASS 备注会写 `int8_exempt=yes` 而不是 `int8_genuine=yes`。
- **张量个数/shape 不匹配** → 解析到的张量与参考对不上;确认 spec 产出的输出 shape 符合预期、布局(NCHW vs NHWC)正确。x86 与 riscv 驱动**均**已 `sed` 关掉 benchmark 的 10 元素打印上限(全张量 dump 是 Python 侧统一算余弦的前提),若换了缺这行的脚本需补回。
- **余弦恒为 `0.0` 且一边输出全零** → 设备/生成代码真的产出了全零张量(参考非零),这是真实失配,不是边界噪声。**绝不能**靠把 NaN/全零判成 1.0 来掩盖——按 fp32 bug 排查内核/opcoder。

## 范围、失败回流与底线

本 skill 负责**测试设计与 Host 验证**，不负责实现转换器/内核支持。某路径因算子源码缺陷失败时，输出首个
`stderr.log` 错误、失败层和受影响 case，交给 `hs-workflow-op-development` 回流 `hs-dev-op-implement`；不要在本 skill
中顺手修改 parser/kernel/opcoder。若证据表明是 `op_spec.py`、模型构造、输入值域、GT 或 capability 映射错误，才由本
skill 修复并整轮重跑。绝不改参考输出、放宽阈值或手填余弦把红变绿。

完成时额外输出 `HOST_VERIFY_GATE=PASS`；任一 VERDICT FAIL、`HARNESS_EXIT!=0` 或能力未全覆盖时输出
`HOST_VERIFY_GATE=FAIL`。该门禁不代表真实开发板已验证。
