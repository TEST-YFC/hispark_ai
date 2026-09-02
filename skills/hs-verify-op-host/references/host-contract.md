# Host 规格与输入约定

目录：

- [前置检查](#前置检查)
- [资源边界与 Bundled Harness](#资源边界与-bundled-harness就地运行不要改不要拷)
- [唯一要写的文件](#唯一要写的文件op_specpy)
- [能力清单锁定文件](#能力清单锁定文件-projscriptscapability_checklistjson-完整-workflow-必需implement-step3-保存)
- [用例设计原则](#用例设计原则op_specpy-里两套独立设计)

进入对应阶段时读取本文件；`op_spec.py` 唯一写入边界和覆盖要求不变。

## 前置检查

需要一套**已构建**的 MindSpore Lite 工具链(含 `converter_lite` 与 benchmark 源码)。用环境变量
`MSLITE_PKG` 指向它;harness 也会从当前目录向上自动定位作为兜底:

本Host harness及当前`linux-x64` converter必须在Linux/WSL执行，不能直接用Windows Python
启动。HiSpark.AI代码可以位于Windows磁盘，但传给harness、converter和CMake的路径必须先
转换成WSL原生形式（例如某个 Windows 工作区对应 `/mnt/<drive>/<工作区>`）；代码位于 WSL
原生目录时直接使用`/home/...`。`MSLITE_PKG`、`--spec`及输出目录必须全部属于同一个
Linux/WSL路径空间，禁止在一条命令里混用Windows与WSL绝对路径。

```bash
export MSLITE_PKG=<mindspore-lite 构建产物根目录>
test -x "$MSLITE_PKG/tools/converter/converter/converter_lite" && echo OK || echo "toolchain NOT built"
```

**每次 Bash 工具调用都是新 shell，`export` 不跨调用存活**——所有用到 `MSLITE_PKG` 的命令必须与 `export MSLITE_PKG=...` 写在同一条命令里（「运行」里的"整块复制执行"正是为此；拆开执行时上一条的 export 已失效，`test -x "$MSLITE_PKG/..."` 必然 MISSING）。

**`MSLITE_PKG` 必须指向构建产物顶层（`output/mindspore-lite-<ver>-linux-x64/`）——即解压后的 tar.gz 包。禁止指向原始 `build/` 目录。** 后者缺少 `include/c_api/`、`runtime/include/` 等头文件，共享库分散在多处，会导致 `converter_lite` 找不到 `.so` 或 `make` 缺头文件。用错目录时最常见症状是 `error while loading shared libraries` / `c_api/model_c.h: No such file`——遇到此症状先检查 `MSLITE_PKG` 是否为解压包。

**解压包必须不早于最近一次构建——harness 自动校验并拒绝陈旧包。** 重新编译只刷新 tar.gz，不会自动重新解压；若忘记重解压，验证会运行陈旧的 `converter_lite`，结论不能反映当前代码。harness 发现旁边的 tar.gz 比解压包新即报错停止——处置就是重新解压（`build_mslite.sh` 构建成功后自动完成）。`OP_VERIFY_ALLOW_STALE=1` 只允许用于显式兼容性对比，不得用于结论性签收。`verify_summary.txt` 头部记录本轮 `converter_lite` 的构建时间，便于追溯结论对应哪次构建。

未构建时**停止并告知用户先构建工具链**,不要继续、不要伪造结果。

## 资源边界与 Bundled Harness（就地运行，不要改、不要拷）

Skill 包内固定资源包括 `scripts/run_all_cases.py`、`scripts/*.sh`、`scripts/*.cfg`、
`scripts/operator_spec_template.py`、`scripts/validate_op_spec.py`、`scripts/wait_verify.sh`、
`scripts/judge.sh` 和 `tests/`。当前算子项目的运行时产物包括 `<opdir>/scripts/op_spec.py`、
`<opdir>/scripts/capability_checklist.json`、`<opdir>/docs/*.md`、`<opdir>/output/`、
`verify_summary.txt` 以及 `/tmp/op_verify_<RUN_ID>.log` 和对应 `.pid`；这些文件不属于 Skill 包。
静态资源检查不得要求 `skills/hs-verify-op-host/scripts/op_spec.py` 存在。

| 文件 | 作用 |
|---|---|
| `scripts/run_all_cases.py` | **唯一入口**,算子无关。编排每用例内部 step1-step5、解析 benchmark 打印的输出张量、**在 Python 侧统一算余弦**、写 Excel。每次运行携带唯一 `RUN_ID`，旧日志不能冒充本轮结论。另自带防假结论闸门：按 spec 的目标节点校验源模型，并按 `<proj>/scripts/capability_checklist.json` 校验能力 covered_by 引用；清单还必须声明 `folding_and_rewrite` 矩阵，分别覆盖阻止折叠以证明目标 Kernel 真执行、允许重写以证明整图语义，或给出 N/A 证据。转换后必须保留 target/rewrite identity evidence，不能只凭原始模型节点判定 |
| `scripts/validate_op_spec.py` | Host 拥有的长测试前自动检查：检查动态输入、initializer、capability case ID 和 ONNX 属性冲突 |
| `scripts/wait_verify.sh` | 后台启动后的**唯一等待方式**:内部轮询日志到 VERDICT 出现/进程退出/到时,免 sleep 算术 |
| `scripts/judge.sh` | **手动判定辅助**(不改驱动、不复制公式):`judge.sh <case_dir> [path_key]` 转发到 `run_all_cases.py --judge-case`,读取最新 `output/<path>/stdout.log`,刷新 `output/<path>/output*.npy`,再用 harness 的 `cosine_similarity()` + `PATH_META` 对比稳定的 `gt/output*.npy` 打印 PASS/FAIL。`output/<path>/_run.sh` 手动重跑后也走同一入口刷新判定;**权威结论仍以 run_all_cases.py 的 VERDICT 为准** |
| `scripts/onnx_x86.sh` / `tflite_x86.sh` | x86:转换(NCHW/NHWC)+ 编译 + benchmark **仅打印输出张量**(不传 calib、不做内置比对) |
| `scripts/onnx_riscv.sh` / `tflite_riscv.sh` | riscv:转换 + `sed` 把工具链改写为 x86 host 静态库 + 编译运行(无需真板) + benchmark 仅打印输出张量 |
| `scripts/micro_x86.cfg` / `micro_riscv.cfg` / `micro_riscv_quant.cfg` | 三条路径的 cfg 模板(quant 的 `{CALIBRATE_PATH}` 由 harness 运行时按"每输入一个 `tensor:dir`"填,支持多输入) |
| `scripts/operator_spec_template.py` | **复制到当前算子项目并填写的唯一模板**；复制后的 `<opdir>/scripts/op_spec.py` 是项目运行时文件 |
| `tests/test_harness_core.py` | **harness 自检**(防伪结论的不变量保护网):按真实签名对 `cosine_similarity`(全零/一边零/永不 NaN 三个语义)、三道闸门(`assert_int8_genuine` / `check_case_regression` / 能力清单 `validate_checklist_refs`+`report_capability_coverage`)、`parse_benchmark_outputs`、`_err_msg`、`make_cfg` 做单元断言。不依赖 MSLite/硬件,秒级跑完。**任何对 harness 的维护性改动后必须先跑它**(`python3 -m pytest tests/ -v`),绿了才动真验证——它守的正是"改 harness 时别把防红变绿的能力悄悄改没了" |

## 唯一要写的文件:`op_spec.py`

把 `operator_spec_template.py` 拷到你的算子项目目录(约定 `$MSLITE_OP_OUTPUT/<op>/`，缺省与 mindspore-lite 仓平级，HiSpark.AI 仓内即 `src/mslite-op-output/<op>/`)下的
`<proj>/scripts/op_spec.py`,填入用例与模型构建。harness 校验的必需定义:

```python
OP_NAME            : str
ONNX_TEST_CASES    : list[dict]   # 每条 {"id","desc","test_point","params":{...}}，按 ONNX 规格(NCHW)
TFLITE_TEST_CASES  : list[dict]   # 独立按 TFLite 规格(NHWC)设计
build_onnx_model(tc, model_path)     # 用 onnx.helper 建图并保存 .onnx
build_tflite_model(tc, model_path)   # 用 tf.Module + experimental_new_converter=False 保存 .tflite
make_inputs(tc, framework) -> list[np.ndarray]   # 模型输入顺序、确定性
# 可选: PARAM_COLUMNS = [...]   tc["params"] 里要展示到 Excel 的键
# ONNX_TEST_CASES 非空时必填: ONNX_TARGET_OP_TYPE = "<确切 op_type>"
# TFLITE_TEST_CASES 非空时必填: TFLITE_TARGET_BUILTIN = <存在性查证命中的 builtin 编号>
# harness 检查每个生成的源模型；目标节点/builtin 缺席的用例直接 FAIL(OP_MISMATCH)，
# 不会静默测成 API 优化后的其它算子。缺少对应声明时整轮拒跑。
# 可选: INT8_KERNEL_SYMBOL = ""  # 仅量化 INT8 豁免算子使用；PASS 备注写 int8_exempt=yes。
# 可选: INITIALIZER_INPUTS = {"onnx": ["w", "x_zero_point"]}
#   模型 graph input 中由 initializer/常量提供、不由 make_inputs() 返回的输入名。
#   harness 会校验 make_inputs 数组数 == 动态输入数，防 zip 静默丢输入。
```

harness 自动:用 spec 的模型现算参考输出、生成 calib、存 `input.bin`、跑三条路径、解析真实余弦、写表。
spec **只描述"算什么",不碰"结果对不对"**。

每条 case 的 `desc` 是便于定位的短名称；`test_point` 是报告中的“测试点”，必须用非空单行字符串明确说明
该用例要验证的行为、边界或缺陷类型，例如“验证中间维广播的步长与索引”，不能只写“功能测试”或
复制 `desc`，也不能包含 Markdown 表格分隔符 `|`。`test_point` 在 Host 前冻结，并原样传入 Excel、
`verify_summary.txt` 和板端矩阵。

### 能力清单锁定文件 `<proj>/scripts/capability_checklist.json`（完整 workflow 必需，implement step3 保存）

把 `hs-dev-op-implement` step3 的「能力验收清单」逐行落成 JSON，harness 据此机械核对覆盖（详见「必守约束」对应红线）。结构：

```json
{
  "op": "Hardmax",
  "framework_scope": ["onnx"],
  "capabilities": [
    {"id": "c1", "desc": "2D 小张量 axis=0 (fp32+int8)", "covered_by": [2], "match": {"axis": 0}},
    {"id": "c5", "desc": "4D 大张量 axis=-1 (序关系 distinct)", "covered_by": [5]}
  ]
}
```

- `covered_by`：承载该能力的 `*_TEST_CASES` 用例 id 列表，**必须非空且引用存在的用例**（开跑前校验，dangling/空即拒跑）。
- `match`：params 谓词；声明后该能力的 covered_by 用例中至少一条 params 须满足所有键值，防 covered_by 指错用例冒充覆盖。非平凡能力（dtype、shape/rank、axis、stride、pad、dilation、group、可选输入、broadcast 形态）应写出关键 match；空 match 只用于无法机械表达的总体能力。
- 结束后每条能力按本轮**通过**用例核对：covered_by 无一通过 = 未覆盖，VERDICT 标 `[UNCOVERED]` 且非绿。
- 缺该文件时 harness 仅告警、不阻塞（向后兼容），但 VERDICT 不含能力覆盖留痕——完成声明就缺一项机械证据。

### 用例设计原则(`op_spec.py` 里两套独立设计)

1. **先查证算子名与属性(写用例前,别凭记忆)**:
   - **存在性查证——决定哪个框架该写用例、`build_*_model` 用什么名字(确定性命令,别凭记忆):**
     - ONNX:`curl -sL -o /dev/null -w '%{http_code}\n' https://onnx.com.cn/onnx/operators/onnx__<OpName>.html` —— `200`=有、`404`=无。
     - TFLite:`curl -sL https://raw.githubusercontent.com/tensorflow/tensorflow/master/tensorflow/lite/builtin_ops.h | grep -nE 'kTfLiteBuiltin<OpName>\s*='` —— 命中(含 builtin 编号)=有、空=无。
      **只为"有"的框架写 `*_TEST_CASES`;`build_*_model` 里 `helper.make_node` / TFLite op 用的名字必须是查证命中的确切框架名。** 某框架"无" → 该框架 `*_TEST_CASES = []`,对应 `build_*_model` **保留为占位**(函数体直接 `raise NotImplementedError("<框架> has no <Op>")`——harness 校验符号存在,删函数会报错);**绝不改用"等价算子"顶替来让模型建得起来**(那测的是别的算子,结论无效)。
   - **目标算子身份是前置硬门禁**：ONNX 用例声明 `ONNX_TARGET_OP_TYPE`，TFLite 用例声明 `TFLITE_TARGET_BUILTIN`。harness 在参考运行和 converter 之前逐 case 解包源模型；如果 Fill 等节点被模型 API 常量折叠、lower 或规范化为 BroadcastTo 等别的节点，立即 `OP_MISMATCH`，先修 builder/shape/动态输入设计，不进入精度比较。不要把替代节点的 PASS 当成目标算子 PASS。
   - **converter运行环境和参数按当前包探测**：harness 不依赖用户在前一个shell中的`export`。它先在本轮`MSLITE_PKG`内定位`libmindspore_converter.so`，把真实目录置于当前子进程`LD_LIBRARY_PATH`最前，过滤明显属于其他MSLite包的旧目录，再以相同环境运行真实转换。随后对 `$MSLITE_PKG/tools/converter/converter/converter_lite --help` 只探测一次并缓存。只有 help 明确声明 `--encryption` 时才传 `--encryption=false`；help 成功但不支持时省略。自动配置成功就继续，不向用户转交手工设置；包内缺库时输出`CONVERTER_RUNTIME_GATE=FAIL`，help非零、超时或无法启动时输出 `CONVERTER_CAPABILITY_GATE=FAIL` 并停止，不得猜参数或把环境失败归到算子。每条 driver 日志记录 converter 绝对路径、动态库目录、help 返回码和最终选择，所有驱动不得再硬编码版本专属参数。
   - **模型输入要求**：`make_inputs()` 返回的数组数必须等于模型动态输入数。ONNX 权重/zero-point 等若同时作为 graph input 与 initializer 存在,必须在 `INITIALIZER_INPUTS` 显式列名；否则 harness 会在 reference 前拒跑。不要依赖 Python `zip(input_names, inputs)` 静默截断,那会让测试少喂输入却看似通过。
   - **原生整型/索引算子**：可声明 `INT8_KERNEL_SYMBOL=""` 表示量化 INT8 genuine 检查不适用,但仍要按规格覆盖每个原生 dtype（如 int8 与 uint8 分开用例）,并在能力清单用 `match` 锁定 dtype。
   - **属性按规格枚举**:ONNX `https://onnx.com.cn/onnx/operators/onnx__<OpName>.html`;TFLite `https://tensorflow.google.cn/mlir/tfl_ops`、`.../api_docs/python/tf`、`.../lite/performance/quantization_spec`(属性/量化/布局与 ONNX 可能不同,不要照搬;WebFetch 不可达回退 `curl -sL <url> | head -300`)。参考输出由 harness 用真实 runtime 现算,故属性**取值**的正确性自校验——你的风险是**漏掉属性组合**和**用了不存在的属性名**,不是属性数学算错。列全属性,每个有意义组合各一条用例。
   - **目标 builtin 实证(TFLite,builder 写完必做一次)**:转换器会按输入形状对同一上层算子**择优/规范化** builtin(实证:无广播的 `SelectV2` 调用被降成 `SELECT`,真广播形状才发 `SELECT_V2`)——**builder 调了哪个 raw_op 不等于模型里是哪个 builtin**。每类形状形态各构建一个最小模型,解包核对 operator code 恰为目标 builtin(编号用存在性查证命中的值):
     ```bash
     python3 -c "from tensorflow.lite.python import schema_py_generated as s; \
     m=s.Model.GetRootAsModel(open('<model.tflite>','rb').read(),0); \
     print([max(m.OperatorCodes(i).BuiltinCode(),m.OperatorCodes(i).DeprecatedBuiltinCode()) for i in range(m.OperatorCodesLength())])"
     ```
     命中别的 builtin = 该形状的用例在**测别的算子**:处置是**调形状**让目标 builtin 出现(典型:广播版算子的用例必须全部用真广播形状,同形用例会被规范化成非广播版),而不是接受错位、也不是换算子名。核对结果(每形态一行:形状→builtin 编号)写进 docstring 当作证据。**并把查证命中的编号声明为 spec 的 `TFLITE_TARGET_BUILTIN`**——此后 harness 每轮对每个用例自动解包复核,目标 builtin 缺席的用例判 `OP_MISMATCH` FAIL。手工实证负责"设计形状时找到能逼出目标 builtin 的形态",harness 断言负责"以后每一轮都不漂移",两者不可互替。
2. **每个框架各 10–20 条**,覆盖:

| 维度 | 覆盖范围 |
|------|---------|
| 属性(attribute)边界 | 最小/最大/默认/负值 |
| 输入 shape | 1D / 2D / 小 4D(如 `[1,4,8,8]`) / 大 4D(如 `[1,32,64,64]`) / batch>1(如 `[4,8]`) |
| 输入值域(sign domain) | **全正数**(如 `[0.1, 6.0]`) / **全负数**(如 `[-6.0, -0.1]`) / **正负混合**(`[-6.0, 6.0]`，默认) / **全零** / **小量级**(如 `[-1e-3, 1e-3]`，下限见下方「打印分辨率」) |
| 算子敏感区间 | 由算子特性决定：如 HardSwish 的 `[-3, 3]` 非线性段、ReLU 的 `x<0` 截止区、Softmax 的相对大小关系、Tanh/Sigmoid 的饱和区。至少为每个敏感区间各设一条用例，值落在该区间内 |
| 数值形态 | 递增(`linspace`) / 全相同 / 边界极值(`±1e4`) |
| 数据类型 | float32、int32/int64(MSLite 内部 int64→int32,indices 存 `np.int32`) |
| **多输入 / 广播** | 多输入算子每输入独立 shape、独立 dtype(`make_inputs` 返回全部输入;非 float 输入如 bool 掩码/int 索引保持原 dtype、不做量化值域填充);广播算子**按规格**覆盖同形 + 标量(某输入=`[1]`)+ 文档支持的广播形态,不设算子会拒绝的形态。**全向广播算子还必须各设一条「中间维广播」**(如 `[2,1,4]`×`[2,3,4]`——`i%num` 式近似索引只对最外维广播碰巧正确,此形态专抓它)**与「混合形态」**(一个输入标量 + 另一输入非平凡广播同现——"任一输入是标量就走快路"式弱守卫的盲区);只有同形/标量用例全过证明不了这两类实现错误不存在。在 builder 里加 per-input 形参只是脚手架——**不写出对应的广播用例行就等于没覆盖**(模板文件末尾有通用范式)。 |
| **规格列明的输入形态(强制逐条覆盖)** | 把规格文档里描述输入间 shape/rank 关系的**每一句**翻译成至少一条用例——尤其"或"出来的替代形态(如"condition 与数据同形,**或** rank 1 且匹配首维"是两种形态、两条用例)、可选输入缺省、规格点名的特殊 rank。**只测了其中一种形态 = 另一种形态完全未验证**,转换器/infer/kernel 对它的行为(支持、拒绝、还是静默算错)是未知的。某形态实测被转换器拒绝 → 这是一条要如实上报的结论(见「失败排查」),不是删除该用例的理由;未实跑不得删除,builder 产不出该形态时按「必守约束」的「还没跑」条处置。 |
| 特殊语义 | 算子特有行为(负 axis / 多输出 / 原地…) |

无属性算子(Relu、Abs、HardSwish…)只需 shape + 值域 + 敏感区间 + 数值形态。

> **值域下限受打印分辨率约束(设计用例时即遵守,勿等假 FAIL):** 余弦在 Python 侧基于 benchmark
> **文本打印**的输出张量计算(`%f`,六位小数),可分辨的最小量级约 `1e-4`。用例的预期**输出**量级若
> 低于此(如值域 `[-1e-6, 1e-6]`),打印端只剩截断噪声,余弦反映的是打印精度而非内核精度——fp32 也会
> 假 FAIL。"小量级"用例取 `1e-3` 量级即可达到测试目的(远小于默认 `±6` 的 baseline、足以考验量化
> scale 分配),不要再往下压。

### 输入形态覆盖与测试数据生成检查

在启动 harness 前，先把规格中所有输入形态组合逐项列成 case 矩阵：dynamic、initializer、
optional 缺省/显式、广播形态、索引/边界语义、折叠 blocked/allowed，以及每个支持的 dtype
都必须有独立 case 或有证据的 N/A。一个代表 case、只填写 builder 参数、或只覆盖同形输入
不能推断其它形态已经覆盖。若规格允许标量或单元素输入，`make_inputs()`/`gen_dataset.py`
必须能生成 `[1]` 或标量数组；不得隐含“至少两个元素”。索引类用例必须按来源规范决定
负索引和越界的预期行为，不能静默把它们删除、截断或取模。代码 review 与
`capability_checklist.json` 的每一行都要能回指到这些 case，缺少映射时 Host 门禁失败。

### 量化校准与推理输入的数据一致性（INT8 精度关键）

harness 对 `riscv_int8` 路径的校准数据和推理输入使用**同一份 `make_inputs()` 产物**：
- 推理侧：`input_files` = `make_inputs()` → `.bin`
- 校准侧：`calib_dir` = `input_files` 的直接副本（`run_all_cases.py` 的 calib 准备逻辑：校准数据直接复用推理输入）

因此只要 `make_inputs()` 是确定性的，校准范围与推理范围天然一致，不存在 mismatch。

**但这要求 `make_inputs()` 为每条用例产出有意义的数值**——不当的值域选择会导致 INT8 精度问题的假阳性：

| 问题 | 现象 | 正确做法 |
|------|------|---------|
| 用例全是正数或全是负数 | 量化 zp 偏向一侧，另一侧精度不足 | 至少一条全正数、一条全负数、一条正负混合 |
| 遗漏算子敏感区间 | 内核在非线性段/截止区/saturation 区有 bug 但测不到 | 根据算子特性设置跨越敏感阈值的用例（如 HardSwish 的 ±3、ReLU 的 x=0 两侧） |
| 输入全零 | INT8 量化后 scale≈0，输出无意义，cos 偏低 | 至少有一条用例覆盖非零范围 |
| 只覆盖小量级值 | MAX_MIN 量化的 scale 极小，量化误差放大 | 有中等量级（如 ±6）的 baseline 用例 |

**设计 `make_inputs()` 时的默认策略：**
1. 一条 baseline：`linspace(-6.0, 6.0, n)` —— 正负混合，覆盖大多数算子正常工作区间
2. 一条全正数 + 一条全负数 —— 考验 INT8 zp 的偏向
3. 一条全零 —— 退化输入健壮性
4. 针对算子本身特性，每条敏感区间至少一条 —— 见上表「算子敏感区间」列
   > **单元素输出用例只能证明"能跑通"，证明不了数值正确**——任意两个同号标量的余弦恒为 1.0。单元素用例照设（探崩溃/越界），但凡其代码路径与多元素不同（如 kernel 对 scalar 条件走专用快路），**必须另设同路径的多元素用例**承担数值判别；不可见单元素 PASS 就认为该路径数值正确。
5. **多数据输入算子**（条件选择、Concat、逐元素二元等）：至少一条「**输出分布 ≠ 输入分布**」的判别用例——各输入同量级正负混合（如都在 `[-6,6]`），条件/选择只命中**单一符号侧**使输出单边（输出 scale/zp 与输入不同）。各输入之间**不要拉开数量级**（无判别力，不要设）。
