# 训练串口采集与比较

两个脚本使用同一个 `training_protocol.py`，支持现有 training schema_version=1；不改变 inference 的 CLI、格式或精度规则。collector 只判采集/协议，compare 独立重放原文后判单 case 数值，不是训练矩阵汇总器。

## 当前边界与未来命令链

当前检出的 Micro 生成器没有训练 observer。对带 `--config` 的训练调用，`build_micro.py` 会在转换前返回 `training_observer_unavailable_for_micro_generator`；因此不能继续执行 sample 生成、SDK 接入、固件构建、烧录或串口采集。训练板结果必须记录为 `NOT_RUN`，并保留 Host 通过与 observer 缺失的证据。

```text
build_micro.py --config <Host micro_train.cfg>
→ TRAIN_BOARD_VERIFY=NOT_RUN
  reason=training_observer_unavailable_for_micro_generator
```

只有未来生成器和运行时真正提供 observer，并且 receipt、sample 与 wiring 前置检查通过后，才可进入以下完整链路。`verify_firmware.py` 是烧录前的固件内容门禁；串口采集与比较结果用于判定板端回归，不是执行链路的前置条件：

```text
build_micro.py
→ prepare_training_sample.py
→ integrate_sdk.py --verification-kind training
→ verify_wiring.py --verification-kind training
→ hs-dev-build
→ verify_firmware.py
→ hs-dev-flash
→ collect_training_serial.py
→ compare_training_board.py
```

未来链路执行要点：

- 所有 case 使用新的独立 run/case 输出目录；`build_micro.py`、sample 和 receipt 必须绑定相同身份。
- `integrate_sdk.py` 使用 sample 目录和 receipt 中的 `model_lib_dir`，不要把原始 archives 路径当作已安装库路径。
- `verify_wiring.py` 只能从当前生成 receipt 中读取真实 observer 符号，不能手写 `GetTrainWeight*`。
- 只有 `verify_firmware.py` 检查通过的 `*_all.fwpkg` 才交给 `hs-dev-flash`；不得用 fbb flash 绕过该 owner。
- Host/WSL/Windows 混合执行时，每条命令记录自己路径空间中的等价路径；不要把 `/mnt/...` 和 `C:\...` 混在同一路径值里。`integrate_sdk.py` 生成的 `.sh` 使用 WSL 路径，生成的 `.ps1` 会把 `/mnt/<drive>/...` 转为 `<DRIVE>:/...`。

### 逐 case 命令模板

下面的模板在 Windows PowerShell 中发起；`build_micro.py`、`prepare_training_sample.py`、`integrate_sdk.py` 和 `verify_wiring.py` 在 WSL 中执行，固件构建、烧录和串口工具在 Windows 中执行。Windows 侧运行 `compare_training_board.py` 需要 Python 和 NumPy；选择 pyserial 采集时还需要 pyserial，fbb monitor 后端不需要。所有尖括号占位都须替换为当前任务的实际值；不要把示例值当作默认值。

当前 WS63 训练准备链路只支持 `ModelIndex=0`。支持其他索引前，必须先扩展 build、sample 和 receipt 检查，不能只改模板中的编号。

```powershell
$ErrorActionPreference = 'Stop'
$RunId = '<run_id>'
$CaseId = '<case_id>'
$Operator = '<operator>'
$Target = '<ws63-target>'
$Port = '<detected-serial-port>'
$ModelIndex = 0
# 从锁定 case 的 graph_expectations.targets[*].backward_symbols 中选择符号；
# verify_wiring/nm 会继续核对该符号来自当前 net0.c 和 libnet.a。
$BackwardKernelSymbol = '<target_backward_kernel_symbol>'

$BoardSkillW = '<board-skill-windows-root>'
$BoardSkillU = '<board-skill-wsl-root>'
$OpdirW = '<absolute-opdir-windows>'
$OpdirU = '<absolute-opdir-wsl>'
$HisparkU = '<hispark-root-wsl>'
$SdkW = '<ws63-sdk-windows-root>'
$SdkU = '<ws63-sdk-wsl-root>'
$SdkSrcW = Join-Path $SdkW 'src'
$PkgU = '<current-mslite-linux-package>'
$ToolchainU = '<riscv-toolchain-bin-wsl>'

$RunW = Join-Path $OpdirW "runs\$RunId"
$RunU = "$OpdirU/runs/$RunId"
$CaseW = Join-Path $RunW "board\$CaseId"
$CaseU = "$RunU/board/$CaseId"
$MicroU = "$CaseU/micro"
$SampleU = "$CaseU/sample"
$MicroReceiptU = "$MicroU/micro_build_receipt.json"
$TrainingSampleReceiptU = "$SampleU/training_sample_receipt.json"
$ModelSha256 = (Get-FileHash -LiteralPath (Join-Path $OpdirW "cases\$CaseId\model.onnx") -Algorithm SHA256).Hash.ToLowerInvariant()
# 当前脚本会在 build_micro.py 的 observer 能力门禁停止，以下模板仅用于未来支持版本。
```

未来 observer 已验证可用时，生成 Micro 静态库、训练 Sample 并接入 SDK；当前源码不得执行本节命令：

```powershell
wsl.exe -e python3 -B "$BoardSkillU/chips/ws63/scripts/build_micro.py" `
  --model "$OpdirU/cases/$CaseId/model.onnx" `
  --framework onnx --mode fp32 `
  --config "$RunU/$CaseId/micro_train.cfg" `
  --run-id $RunId --case-id $CaseId `
  --mslite-pkg $PkgU --toolchain-bin $ToolchainU `
  --output-dir $MicroU

$micro = Get-Content -LiteralPath (Join-Path $CaseW 'micro\micro_build_receipt.json') -Raw | ConvertFrom-Json
$microProject = [string]$micro.micro_project
$microModelSource = "$microProject/src/model$ModelIndex/model$ModelIndex.c"
$netSource = "$microProject/src/model$ModelIndex/net$ModelIndex.c"

wsl.exe -e python3 -B "$BoardSkillU/chips/ws63/scripts/prepare_training_sample.py" `
  --opdir $OpdirU --run-id $RunId --case-id $CaseId `
  --micro-model-source $microModelSource `
  --micro-build-receipt $MicroReceiptU `
  --output-dir $SampleU

wsl.exe -e python3 -B "$BoardSkillU/chips/ws63/scripts/integrate_sdk.py" `
  --sdk-root $SdkU --hispark-root $HisparkU `
  --sample-dir $SampleU --model-lib-dir "$MicroU/archives" `
  --operator $Operator --case $CaseId --mode fp32 `
  --verification-kind training --run-id $RunId `
  --model-sha256 $ModelSha256 `
  --training-sample-receipt $TrainingSampleReceiptU `
  --target $Target --receipt "$CaseU/integration.json"

$adaptor = "$SdkU/src/middleware/utils/ai_mcu/adaptor/cpu"
$integration = Get-Content -LiteralPath (Join-Path $CaseW 'integration.json') -Raw | ConvertFrom-Json
$installedModelLib = [string]$integration.model_lib_dir

wsl.exe -e python3 -B "$BoardSkillU/chips/ws63/scripts/verify_wiring.py" `
  --sdk-root $SdkU --sample-dir $SampleU `
  --model-lib-dir $installedModelLib `
  --adaptor-dir $adaptor `
  --ai-header "$SdkU/src/include/middleware/utils/ai.h" `
  --consumer "$SdkU/src/application/samples/CMakeLists.txt::AI_CUSTOM_SAMPLE_DIR" `
  --consumer "$SdkU/src/middleware/utils/CMakeLists.txt::ai_mcu/adaptor/cpu" `
  --consumer "$adaptor/CMakeLists.txt::AI_MCU_MODEL_VARIANT" `
  --verification-kind training --net-source $netSource --nm /usr/bin/nm `
  --runtime-symbol "MSModelPredict$ModelIndex" `
  --runtime-symbol "Execute$ModelIndex" `
  --kernel-symbol $BackwardKernelSymbol `
  # --generated-symbol 必须来自未来生成器 receipt；当前源码没有该参数可用的符号。
  --micro-build-receipt $MicroReceiptU `
  --training-sample-receipt $TrainingSampleReceiptU `
  --integration-receipt "$CaseU/integration.json"
```

构建、核验并烧录 Windows 固件。不要默认指定并发；确需指定时由调用方显式传入并记录：

```powershell
$variant = [string]$integration.variant
$sampleSourceW = Join-Path $CaseW 'sample\src\ai_main.c'
$modelLibW = Join-Path $SdkSrcW "middleware\utils\ai_mcu\lib\$variant"

& (Join-Path $CaseW 'invoke_hs_dev_build.ps1')
if ($LASTEXITCODE -ne 0) {
  throw "WS63 firmware build failed with exit code $LASTEXITCODE"
}

$acoreOutput = Join-Path $SdkSrcW "output\ws63\acore\$Target"
$sampleObjectW = Get-ChildItem -LiteralPath (Join-Path $acoreOutput 'application\samples') -Recurse -Filter 'ai_main.c.obj' |
  Where-Object { $_.FullName -like "*$RunId*" -and $_.FullName -like '*board*' -and $_.FullName -like "*$CaseId*" } |
  Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1 -ExpandProperty FullName
$firmwareW = Join-Path $SdkSrcW "output\ws63\fwpkg\$Target\${Target}_all.fwpkg"

python -B (Join-Path $BoardSkillW 'chips\ws63\scripts\verify_firmware.py') `
  --sample-object $sampleObjectW `
  --map (Join-Path $acoreOutput "$Target.map") `
  --firmware $firmwareW `
  --map-symbol "MSModelPredict$ModelIndex" `
  --map-symbol "Execute$ModelIndex" `
  --map-symbol $BackwardKernelSymbol `
  --newer-than $sampleSourceW `
  --newer-than (Join-Path $modelLibW 'libmicro_runtime.a') `
  --newer-than (Join-Path $modelLibW 'libnet.a')

fbb flash $Target --port $Port --json-summary
```

最后使用新的 raw、observed 和 report 路径采集并比较。`<expected>` 是 Host 聚合导出的当前 case expected JSON：

```powershell
$expectedW = Join-Path $RunW "board_expected\$CaseId.json"
$rawW = Join-Path $CaseW "serial\<new-attempt>.raw.log"
$observedW = Join-Path $CaseW "serial\<new-attempt>.observed.json"
$reportW = Join-Path $CaseW '<new-attempt>.report.json'
$env:FBB_SDK_DIR = $SdkSrcW

python -B (Join-Path $BoardSkillW 'scripts\training\collect_training_serial.py') `
  --port $Port --baudrate 115200 --fbb-monitor --reset --seconds 60 `
  --expected $expectedW --output $rawW --protocol-output $observedW

python -B (Join-Path $BoardSkillW 'scripts\training\compare_training_board.py') `
  --expected $expectedW --observed $observedW --evidence-root $OpdirW --output $reportW
```

多 case 逐个替换 `<case_id>` 并使用独立输出目录；不要把一个 case 的 firmware、attempt 或 report 复用为另一个 case 的证据。

## 当前协议与身份

一条完整 JSON 记录占一行，以 LF 或 CRLF 结尾。日志可以包含启动噪声；解析以第一条严格合法的 `TRAIN_BEGIN` 作为会话起点，起点之前的 `TRAIN_TENSOR`、`TRAIN_DONE` 复位残帧按启动噪声处理，不计入结果。起点之后必须只有一个完整会话：

```text
TRAIN_BEGIN {"run_id":"run_001","case_id":"case_A","model_sha256":"<64位小写SHA256>"}
TRAIN_TENSOR {"run_id":"run_001","case_id":"case_A","model_sha256":"<同一SHA256>","key":"step_3/weight/parameter_A","data":[0.1,0.2]}
TRAIN_DONE {"run_id":"run_001","case_id":"case_A","model_sha256":"<同一SHA256>"}
```

示例中的 hash 占位符必须换成真实 hash。run_id/case_id/model_sha256 非空，BEGIN/TENSOR/DONE 逐帧一致，并与 `--expected` 核对。collector 从设备 BEGIN 提取身份到顶层，不从 expected 回填设备未报告的字段。TRAIN_* 明确表示 training；记录如果自带 verification_kind，必须等于 training。

framework、dtype、数据/GT/配置 hash 等额外身份如果实际打印，必须检查冲突；BEGIN 的额外身份须在后续帧保持一致（仅 tensor 自带 dtype、BEGIN 未带 dtype 时允许作为 tensor 元数据）。expected 中设备未打印的身份列入 `external_identity_fields`，不声称完成设备侧核验；这些字段仍由工作流核对 Host 清单及文件指纹。

残缺 `TRAIN_BEGIN`、重复/缺失 BEGIN/DONE、有效 BEGIN 后的区间外 TENSOR、混合 run、坏 JSON、重复 JSON 成员、重复 tensor key、非有限或非法数值都会失败，不取最后一条覆盖。缺失身份的旧裸 DONE 格式不能给 PASS；现有三字段身份、key/data 格式仍可严格重放，无需强制 v2。

## expected 与数值

expected 是本轮锁定的 Host JSON，根包含 `verification_kind=training`、上述三个身份字段及非空 `tensors` 列表，每项包含唯一 key 和显式 data。

- expected/observed 两侧均检查唯一性与数据类型，tensor 集合必须完全相等。
- data 只接受有限 int/float 且转换到 FP32 后仍有限；不接受 bool、数字字符串、null 或嵌套数组。
- 可选 dtype/shape/elements/phase/step/role/name 必须合法；expected 声明的元数据必须由 observed 匹配。未提供完整 dtype/shape/elements 时报告 `metadata_verified=false`，不伪造 shape 证明。
- 标量 shape=[] 是 1 元素；空 data 需要显式含零维度的 shape。读取层支持半行拼接，不支持协议级 tensor chunk，出现 chunk/offset 字段直接拒绝。
- 逐元素 `abs(actual-reference) <= atol + rtol*abs(reference)`，默认均为 1e-5。容差须有限且非负；expected 可用 `tolerances: {"atol":1e-5,"rtol":1e-5}` 冻结，CLI 不一致时失败。不得为消除失败临时放宽容差。
- 串口原文按物理换行分块解析。仅在等待 `TRAIN_BEGIN` 时允许任意启动噪声字节；有效 `TRAIN_BEGIN` 之前的协议残帧不计入证据。有效 `TRAIN_BEGIN` 之后（包括 `TRAIN_DONE` 之后）每一行都必须是完整、严格的 UTF-8 JSON 协议帧；普通文本、空行、二进制和未知 `TRAIN_*` 行均失败，不能截断或降级替换解码。
- 声明 `dtype: "int32"` 的训练权重逐元素整数精确相等；浮点容差不适用于 int32。输出仍必须是 float32。
- 参数集合可用 `required_parameters` 显式列出 **expected tensor key**；否则沿用 `role=parameter`、`weight/`、`/weight/` 的既有命名约定。一个自报 `parameters_observed=true` 不会替代预期集合核验。没有参数预期且无已知错误时，完整训练结论 NOT_RUN；错误优先 FAIL。
- 可选 `parameter_checks` 是列表，每项 `{"kind":"equal|must_change","left":"<key>","right":"<key>"}`。参考和实测都核验 exact equal / 至少一元素变化，可表达 before/after 对应、冻结不变及上游非零更新。键名/step 无硬编码；工作流从 Host case 锁定规则，不从 observed 自报状态猜测。未声明规则就不声称已检验上游更新。快照是否来自运行时地址仍需 Sample/库接线证据。

## 离线重放（不接触设备）

以下离线重放和实时采集命令均在本技能的 `scripts/training/` 目录执行；脚本仍保留在该目录。

```powershell
python -B collect_training_serial.py --input-log <saved-raw.log> --expected <expected.json> --protocol-output <new-observed.json>
python -B compare_training_board.py --expected <expected.json> --raw-log <saved-raw.log> --evidence-root <opdir> --output <new-report.json>
```

collector 仅用于离线解析和归档 observed；数值复核直接读取 raw。compare 每次重验身份/BEGIN/DONE/tensor。离线数值复核没有传输回执，不能当作真实板端训练通过。

## 实时采集（仅设备拥有者执行）

先由工作流确认端口归属、停止旧 monitor；不要并行抢口。使用新 attempt 输出路径，不覆盖旧证据。

```powershell
$env:FBB_SDK_DIR='<已确认的fbb SDK目录>'
python -B collect_training_serial.py --port <detected-serial-port> --baudrate 115200 --fbb-monitor --reset --seconds 60 --expected <expected.json> --output <new-raw.log> --protocol-output <new-observed.json>
python -B compare_training_board.py --expected <expected.json> --observed <new-observed.json> --evidence-root <opdir> --output <new-report.json>
```

`--reset` 仅支持 live fbb，直接传给 `fbb monitor --reset`。SDK 使用继承的 `FBB_SDK_DIR`；兼容 collector 的 `--sdk-dir` 时也只是设置子进程环境，不给 fbb 追加该选项。运行前用本地 `fbb --help`、已设置 SDK 环境下的 `fbb monitor --help` 确认可用参数。

fbb 固定传入 `--until '(?m)^TRAIN_DONE \{[^\r\n]*\}\r?\n'`，只匹配完整 DONE 行；该正则仅控制后端停止，协议是否有效仍由共享解析器判断。fbb 的 --log 文件是串口原文，由 fbb 创建；collector 只做启动前的新路径和祖先路径检查，不承诺代替 fbb 以 exclusive 方式打开该文件。stdout/stderr 单独保留，不混作串口输入。

也可不使用 --fbb-monitor，走 pyserial（不支持 --reset）；读取超时返回的半行会拼接。原文与 parsed JSON 必须是不同路径，已有输出拒绝复用。

## 结果与退出码

collector 保存实际身份、capture_attempt_id、采集时间、raw 路径/hash、backend_command/stdout/stderr/returncode、transport_status、parse_status 和错误。退出 0 仅表示采集后端成功且协议完整，或离线解析成功；后端非零保留原码到 JSON，collector 自身返回 2。异常也尽量保留部分原文。

compare 的 0 只表示本 case 所声明检查 PASS，且传入 observed 时采集传输必须为 PASS、采集后端返回码必须为 0；缺少文件等前置条件为 NOT_RUN，协议/身份/集合/数值/采集回执错误为 FAIL，均非零。直接 raw replay 没有传输回执时状态为 UNKNOWN，只能作为离线数值复核，finalizer 不把它当作真实板端训练通过。

`tensor_count` 是单 case 检查项数，不是 case 数。固定固件 run_id 不会因采集而变化，本次采集以 attempt/time/hash 区分；工作流仍逐 case 核对固件、烧录和运行时快照来源证据。

## 板端结果索引

只有一个 Host 数值用例时，直接把该 case 的 comparator report 作为 `facts.board_evidence`。

多个 Host 数值用例时，工作流生成一个 `board_matrix.json`。这个文件只做 case 到 report 的索引，不承载构建、烧录、设备、端口或采集过程；这些信息留在各自日志和 `facts.sources` 中。

生成规则固定：`report.path` 是相对 `<opdir>` 的路径；`report.sha256` 是 report 文件字节的 64 位小写 SHA256；case 集合必须等于 Host expected 数值 case 集合；每行 report 自身必须 PASS，且 report 中的 `case_id` 与索引行一致。失败或未执行不生成通过索引，保留真实阶段状态和已生成的 report。

```json
{
  "schema_version": 1,
  "verification_kind": "training",
  "run_id": "run_001",
  "status": "PASS",
  "cases": [
    {
      "case_id": "tc_basic",
      "status": "PASS",
      "report": {
        "path": "runs/run_001/board/tc_basic/report.json",
        "sha256": "<64位小写SHA256>"
      }
    },
    {
      "case_id": "tc_boundary",
      "status": "PASS",
      "report": {
        "path": "runs/run_001/board/tc_boundary/report.json",
        "sha256": "<64位小写SHA256>"
      }
    }
  ]
}
```

业务通过时，顶层和每一行的 `status` 都必须是 `PASS`，case 集合必须等于 Host expected 数值用例集合。失败或未执行时不生成通过索引；保留真实阶段状态、原始日志和已生成的 report，由 finalizer 按证据判定。
