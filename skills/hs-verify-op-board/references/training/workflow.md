# WS63 训练板端验证

本分支复现 Host 已通过的 Micro 训练用例。复用 SDK 核对、交叉编译、构建、烧录和串口采集能力；训练 Sample、训练快照和训练数值判定按本文执行。推理 Sample 的 `OH_AI_ModelPredict` 和余弦结果不能替代训练验证。

## 1. 前置检查与用例矩阵

输入：`verification_kind=training`、本轮 Host 汇总及其 hash、`runs/<run_id>/board_expected/training_board_expected_matrix.json` 及逐 case expected、原始 case/golden、训练配置、生成模型、输入/label、初值、参考 checkpoint、用户指定的 `FIRMWARE_SDK_ROOT`、`chip=ws63` 和 `BOARD_POLICY`。expected 矩阵由 Host aggregate 的 `--export-board-expected` 生成；本阶段不得手工改写、删减或另行拼装。

先读取 [WS63 SDK 接入规范](../../chips/ws63/references/sdk-integration.md) 和 [设备说明](../../chips/ws63/references/device.md)，复用 SDK 身份、adaptor、库安装、Kconfig/CMake/target 接线要求。其中 ONNX/TFLite 推理矩阵、推理 Sample 生成和精度判定不适用于本分支；训练用例、Sample 与观测要求以本文为准。

执行端口探测并保存结果。Host 运行在 WSL 而 fbb、SDK、串口在 Windows 时，使用 `--target auto` 会同时探测 WSL 本地 `/dev` 和 Windows COM；只要探测 Windows 端口时也可显式加 `--target windows`。若 interop 不可用，必须回到 Windows 执行同一命令，不能把 WSL 的 `/dev` 为空解释为没有板卡：

```bash
python <hs-verify-op-board>/scripts/probe_serial_ports.py --target auto --output <run-dir>/serial_probe.json --attempts 3
```

- 用户明确 Host-only：`TRAIN_BOARD_VERIFY=NOT_REQUESTED`。
- 无设备、SDK 缺失或身份不符：`NOT_RUN`，记录检测结果和恢复步骤；不写入猜测的 SDK。
- 多设备无法唯一确定目标：询问端口，不擅自烧录。
- Host 用例未通过：保留预期矩阵行但不执行，说明上游条件不满足。

读取 Host 导出的 `training_board_expected_matrix.json`，逐行核对 run_id、case_id、framework、dtype、测试点、模型/数据/GT hash、steps、checkpoint、optimizer 参数和必测张量/参数集合。负向转换用例属于 Host 边界检查，不进入板端训练执行分母；Host 数值通过用例必须全覆盖，不能挑选或省略。矩阵缺失、状态不是 PASS 或内部 hash 不一致时，板端记 `NOT_RUN` 并说明上游阻断。

## 2. Micro 模型与交叉编译

逐行复用 Host 已通过的同一源模型、训练配置和初始状态，生成独立 RISCV 训练工程。记录 framework、converter、配置和生成工程 hash，不手写网络/反向公式替代 converter 产物。

Host 的 `MSLITE_TRAIN_BENCHMARK=ON` 是 native 文件导出模式，板端不能照搬。板端用 WS63 对应的 RISC-V 工具链、ABI、NNACL/wrapper 库及 `MSLITE_TRAIN_BENCHMARK=OFF` 构建，交叉编译与推理分支使用相同的 SDK 身份检查。构建前查看当前生成 CMake 和工具链参数，不能把 Host 的 cpu 静态库安装到板端。

`build_micro.py` 在本轮 Micro 工程内生成 observer adapter；调用时必须传入当前锁定的 `case.json`：

```text
build_micro.py --config <Host micro_train.cfg> --case-json <locked case.json> --run-id <run_id> --case-id <case_id>
→ observer_adapter=true, nm_verified=true
```

只有生成 C 的 mutable 参数表、case metadata、adapter、`libnet.a` 定义符号和 receipt 身份链全部通过后，才能调用 sample、SDK 接入和 `hs-dev-build`。任一前置失败记为 `NOT_RUN`/失败，不能以 Host 文件导出或 Sample 自报替代真实板端参数地址；固件构建仍必须使用 `hs-dev-build`，烧录仍必须由 `hs-dev-flash` 负责，不能直接绕过 owner 调用 fbb。

检查产物的架构、ABI、模型/运行时符号、重复库和训练源码收集。安装库、adaptor 和 Sample 到已授权 SDK 时保留原有文件及配置变更记录。固件构建交给 `hs-dev-build`，不绕过其 clean build 和 target 检查。

## 3. 训练 Sample

优先核对当前 `src/adaptor/include/ai.h`、CPU adaptor 和生成模型接口，确认以下调用实际存在且能链接：

```text
OH_AI_ModelGetInputs / OH_AI_ModelGetLabels / OH_AI_ModelGetOutputs
OH_AI_ModelSetTrainMode
OH_AI_ModelRunStep
OH_AI_ModelLoadWeight（按实际接口加载默认或外部初值）
```

Sample 每个用例独立创建模型并恢复相同初始权重/optimizer state，不继承前一用例的更新结果。输入、label 的 dtype、shape 和字节数必须逐项检查；数据写入运行时 tensor，不能只打印编译进 Sample 的参考数组。

执行顺序：

1. 更新前 Predict，输入使用 Host 相同的第一个训练样本。
2. Eval 模式加载固定 Eval input+label，RunStep，采集 checkpoint 0 的输出/loss 和参数快照。
3. Train 模式逐步加载固定训练序列，每个样本调用 RunStep；无 warmup 更新。
4. 到 checkpoint 1 和 final 时切 Eval，加载同一 Eval 数据，RunStep 并采集；之后恢复 Train，下一步重新加载训练样本。
5. 每步检查 API 返回码；失败停止当前 case，保留原始状态和错误，不继续打印成功。

只打印 loss 或“训练结束”不足以验证参数更新。内存不足、接口缺失或线程栈不足应报告具体资源/接口需求，不静默减少 shape、训练步数或用例数。

## 4. 完整训练数据采集

采集与比较共用 `scripts/training/training_protocol.py`，当前支持已有 schema_version=1 的单行 JSON 训练协议，详细字段及命令见 [训练采集与比较说明](commands.md)。不强制固件升级为 v2，不改变推理格式。

板端训练的数据来源、采集和比较分别负责以下工作：

- 生成端 observer：当前源码没有训练模型运行时权重 accessor，具体边界见 [生成端 observer 说明](generated-observer.md)。因此当前训练板路径在 `build_micro.py` 能力门禁处停止；不能生成会引用不存在 `GetTrainWeight*` 的 sample，也不能把 Host 文件导出当成板端参数快照。
- `collect_training_serial.py`：采集并保存原始串口，使用共享 `training_protocol.py` 解析，保留实际身份和解析状态。
- `compare_training_board.py`：独立重放原文，核对完整 tensor 集合、checkpoint、参数规则和数值结果。

仅出现 `TRAIN_DONE`、仅有单个输出，或仅有烧录/进程退出成功，都不能作为 `TRAIN_BOARD_VERIFY=PASS`；缺少必需数据记 `NOT_RUN`/未完成，已发生的解析、采集或数值错误保留 `FAIL`。

原文必须有同一 run_id/case_id/model_sha256 的 TRAIN_BEGIN、唯一 TRAIN_TENSOR 集合和 TRAIN_DONE；逐帧核对身份及顺序，collector 将实收身份提升到顶层。TRAIN_* 表示 training；显式 verification_kind 必须为 training。framework、数据/GT/配置指纹未由设备打印时，保留外部清单证据并标为 external_identity_fields，不从 expected 补造设备字段。

兼容现有 key/data；dtype、shape、元素数、阶段、step、名称等已声明元数据须检查，未打印的元数据不得宣称板端已核验。浮点文本须保留 FP32 精度。两侧数据拒绝重复 key、bool/字符串、NaN/Inf 和 FP32 溢出；tensor 集合与长度精确匹配。读取层支持串口半行拼接，目前不支持协议级 tensor 分块或二进制编码；不能忽略 chunk 字段后判通过。

参数快照必须来自正在训练的运行时地址，名称/布局映射与 Host 一致。当前 Host `MSModelExportWeight` 依赖 `MSLITE_TRAIN_BENCHMARK` 和文件系统；不能假设 MCU 上有相同文件导出能力。先核对是否已有只读的参数访问/串口导出接口：

- 有接口：只有在生成器 receipt、链接符号和运行时快照都证明读取的是实际权重地址时，才可继续完整板测。
- 无接口：当前路径直接在 Micro 准备阶段 `NOT_RUN`；不生成输出-only 的“部分通过”，不硬编码内存偏移，也不通过修改公式规避 observer 缺失。补观测必须同时设计生成器、CMake、receipt、sample、wiring、SDK 构建和板测证据。

冻结用例还需冻结参数前后快照及可训练上游参数更新。导出缺项不是冻结成功。设备没有文件系统时也不能把 Host 的冻结结果直接作为板端结果。

## 5. 构建、烧录、比较

先调用 `hs-dev-build`，完成以下构建身份检查后再调用 `hs-dev-flash`。构建仍须遵守第 2 节的 clean build 和 target 检查要求。

1. **切换 case 后重新配置。** 每次切换 Host case 对应的 Sample 或模型库，都必须触发 CMake 重新配置，并核对配置及生成记录中的源码和库选择属于本 case。仅修改环境变量不能代替重新配置。
2. **核对实际编译与链接输入。** 编译后检查 `compile_commands.json` 中的 Sample 源文件、包含路径和相关编译定义；再检查实际链接命令或链接记录中的模型库路径及库 hash，确认与本 case 的生成产物一致。不能只检查预期配置或环境变量。
3. **核对待烧录固件身份。** 将本轮 `run_id`、`case_id`、模型 hash、Sample 源码及模型库 hash、构建和链接记录、待烧录固件包 hash 对应归档，确保该包可追溯到本 case 的实际构建输入。包名、时间戳或 fbb 构建退出码为 0，都不足以确认 case 切换已经生效。
4. **检查通过才允许烧录。** 发现旧 case 接线或模型库不符时，记录构建身份核验 `FAIL`，禁止烧录该包；证据缺失或身份无法确认时记录未完成，同样不放行。修复并重新核验通过后，才可调用 `hs-dev-flash`，不能将已发现的错误降为未执行。

保留固件包 hash、build 日志、flash JSON、设备身份和端口。按 [烧录与串口交接](../flash-serial-handoff.md) 的设备重探和有界重试规则采集本轮串口，训练行身份及数据解析按上一节执行。

构建、烧录和串口的超时、退出码、日志和端口释放规则分别由 `hs-dev-build`、`hs-dev-flash`、collector 和烧录串口交接文档约束。烧录命令超时或退出码非 0 时，即使 stdout 中出现过 success JSON，也不能按烧录成功继续串口采集。若旧进程仍占用串口，只允许停止能追溯到本轮命令的进程，然后重探端口；仍无法打开时记录真实端口错误，不得改判为通过。

默认先走自动复位烧录。自动复位烧录无响应时，才按 `hs-dev-flash` 的规则改用 `--flash-manual-reset` 重跑。该模式仍由脚本调用 fbb 完成端口打开、握手、烧写和 JSON 判定；用户只做物理 RESET。发命令前必须确认用户在板边，脚本真正进入烧录阶段时提示按一次 RESET，不反复按。

比较使用 Host 同一参考数据和逐元素 atol/rtol 规则，检查 Predict、checkpoint 0/1/final 的 Eval logits/loss 和参数集合，并检查上游非零更新。可复用 Host 训练 runner 中的纯数据比较函数；推理 `board_accuracy.py` / `board_matrix_report.py` 不认识训练 step/权重集合，不能直接用于完整训练 PASS。

使用 `scripts/training/collect_training_serial.py --input-log` 可离线解析已有原文；实时采集由唯一设备拥有者执行，禁止并行抢口。fbb 分支以 --log 原文为准，使用 FBB_SDK_DIR 环境变量、完整行 DONE 正则和可选 --reset，实际参数先查本地 help。保留后端退出码与解析状态；超时但原文完整可单独离线比较，不能把工具失败改记为成功。非协议行可包含任意启动噪声字节；解析器只把第一条严格合法的 `TRAIN_BEGIN` 之后的协议行计入会话，复位残帧不计入证据，计入会话后的协议行必须是完整、严格的 UTF-8 JSON。

`compare_training_board.py` 从 --raw-log 或 collector JSON 引用的原文独立重放，核验 hash、BEGIN/DONE、身份、重复、完整 tensor 集合与数值。传入 observed 时还要求 `transport_status=PASS` 且 backend 返回码为 0；直接 raw replay 只保留 UNKNOWN 传输回执，供离线复核，不等价于真实板端训练通过。参数集合来自 expected.required_parameters 或既有 weight key/role 约定，不信任 parameters_observed 自报值；无参数预期且没有其他错误时返回 NOT_RUN，已知错误保持 FAIL。before/after、上游变化或冻结不变规则由 Host case 写入 expected.parameter_checks，不能硬编码参数名、步数或直接信任 observed 的更新结论。

该脚本生成单 case `training_board_report.json`，包含必需身份、证据 hash、逐 tensor 数值及参数规则结果；`tensor_count` 不是 case 数。

- **比较输入**：只接受同一 case 的期望数据、原始串口日志或 collector 输出。
- **PASS 判定**：必须完成所有必测 tensor 与参数规则的真实数值比较。
- **finalizer**：从逐 case 结果派生 `expected`、`recorded`、`executed`、`pass`、`fail`、`not_run`、`not_requested` 统计。
- **文档同步**：将可追溯的阶段状态与明确排除原因写入验证文档，不得事后补造统计。

训练矩阵身份仍须包含验证类型和 checkpoint，不能和同名推理 case 合并。

交给 facts 的板端证据保持最小：

- 只有一个 Host 数值用例时，`board_evidence` 直接指向该 case 的 `training_board_report.json`。
- 多个 Host 数值用例时，调用工作流生成 `board_matrix.json`，只记录 `schema_version`、`verification_kind`、`run_id`、顶层 `status`、每行 `case_id/status/report.path/report.sha256`。格式见 [训练采集与比较说明](commands.md#板端结果索引)。
- 构建、烧录、端口、设备、固件 hash 和采集过程不属于该索引；它们分别保存在构建/烧录/采集证据和 facts 的 `sources` 中。

finalizer 会重放每个 report，并核对 Host expected 数值用例集合；缺 case、多 case、hash 不一致或任一 report 非 PASS 都不能通过。失败或未执行时不拼装完整通过矩阵，保留真实阶段状态、原始日志和已生成的 report。

只有所有必测行及每行必测数据都实际比较通过，才写 `TRAIN_BOARD_VERIFY=PASS`。部分输出通过但参数未观测，记录该检查的 `NOT_RUN` 和整体未完成；已经发生的构建/烧录/执行/数值错误保留 `FAIL`。烧录成功不等于运行成功，运行成功不等于数值通过。

## 6. 交回工作流

交回模型/库/固件路径、SDK 变更、端口探测、flash JSON、完整串口、数值比较、逐行矩阵和重跑步骤。工作流更新独立验证文档。对尚未具备的板端参数观测接口如实记录，不宣称本分支已有未经实测的全自动板端训练能力。
