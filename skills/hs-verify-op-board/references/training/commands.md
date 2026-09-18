# 训练串口采集与比较

两个脚本使用同一个 `training_protocol.py`，支持现有 training schema_version=1；不改变 inference 的 CLI、格式或精度规则。collector 只判采集/协议，compare 独立重放原文后判单 case 数值，不是训练矩阵汇总器。

## 最小逐 case 板端命令链

只处理 Host 聚合中 `PASS` 且 `kind=numerical` 的 case；每个 case 使用新的独立输出目录。构建、烧录继续使用 `hs-dev-build` 和 `hs-dev-flash`，采集与比较使用本目录脚本。多 case 只生成最小 `board_matrix.json` 索引，不新增汇总 runner。

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

执行要点：

- `build_micro.py` 需要当前 case 的模型、`micro_train.cfg`、工具链目录和新的 `--run-id/--case-id/output-dir`；生成 Micro 工程后保存 receipt。
- `prepare_training_sample.py` 使用同一个 run/case 身份、Micro 模型源文件、Micro build receipt 和 Host 导出的 expected；生成的 sample 也有独立 receipt。
- `integrate_sdk.py --verification-kind training` 使用 sample 目录和 receipt 中的 `model_lib_dir`，并传入 training sample receipt；不要把原始 archives 路径当作已安装库路径。
- `verify_wiring.py --verification-kind training` 需要 Micro build、training sample 和 integration 三份 receipt；`--generated-symbol` 从 generated model/receipt 派生，可重复传入多个符号。
- 只有 `verify_firmware.py` 检查通过的 `*_all.fwpkg` 才交给 `hs-dev-flash`。
- Host/WSL/Windows 混合执行时，每条命令记录自己路径空间中的等价路径；不要把 `/mnt/...` 和 `C:\...` 混在同一路径值里。

## 当前协议与身份

一条完整 JSON 记录占一行，以 LF 或 CRLF 结束。日志可以包含启动噪声，但必须只有一个完整会话：

```text
TRAIN_BEGIN {"run_id":"run_001","case_id":"case_A","model_sha256":"<64位小写SHA256>"}
TRAIN_TENSOR {"run_id":"run_001","case_id":"case_A","model_sha256":"<同一SHA256>","key":"step_3/weight/parameter_A","data":[0.1,0.2]}
TRAIN_DONE {"run_id":"run_001","case_id":"case_A","model_sha256":"<同一SHA256>"}
```

示例中的 hash 占位符必须换成真实 hash。run_id/case_id/model_sha256 非空，BEGIN/TENSOR/DONE 逐帧一致，并与 `--expected` 核对。collector 从设备 BEGIN 提取身份到顶层，不从 expected 回填设备未报告的字段。TRAIN_* 明确表示 training；记录如果自带 verification_kind，必须等于 training。

framework、dtype、数据/GT/配置 hash 等额外身份如果实际打印，必须检查冲突；BEGIN 的额外身份须在后续帧保持一致（仅 tensor 自带 dtype、BEGIN 未带 dtype 时允许作为 tensor 元数据）。expected 中设备未打印的身份列入 `external_identity_fields`，不声称完成设备侧核验；这些字段仍由工作流核对 Host 清单及文件指纹。

重复/缺失 BEGIN/DONE、区间外 TENSOR、混合 run、坏 JSON、重复 JSON 成员、重复 tensor key、非有限或非法数值都会失败，不取最后一条覆盖。缺失身份的旧裸 DONE 格式不能给 PASS；现有三字段身份、key/data 格式仍可严格重放，无需强制 v2。

## expected 与数值

expected 是本轮锁定的 Host JSON，根包含 `verification_kind=training`、上述三个身份字段及非空 `tensors` 列表，每项包含唯一 key 和显式 data。

- expected/observed 两侧均检查唯一性与数据类型，tensor 集合必须完全相等。
- data 只接受有限 int/float 且转换到 FP32 后仍有限；不接受 bool、数字字符串、null 或嵌套数组。
- 可选 dtype/shape/elements/phase/step/role/name 必须合法；expected 声明的元数据必须由 observed 匹配。未提供完整 dtype/shape/elements 时报告 `metadata_verified=false`，不伪造 shape 证明。
- 标量 shape=[] 是 1 元素；空 data 需要显式含零维度的 shape。读取层支持半行拼接，不支持协议级 tensor chunk，出现 chunk/offset 字段直接拒绝。
- 逐元素 `abs(actual-reference) <= atol + rtol*abs(reference)`，默认均为 1e-5。容差须有限且非负；expected 可用 `tolerances: {"atol":1e-5,"rtol":1e-5}` 冻结，CLI 不一致时失败。不得为消除失败临时放宽容差。
- 声明 `dtype: "int32"` 的训练权重逐元素整数精确相等；浮点容差不适用于 int32。输出仍必须是 float32。
- 参数集合可用 `required_parameters` 显式列出 **expected tensor key**；否则沿用 `role=parameter`、`weight/`、`/weight/` 的既有命名约定。一个自报 `parameters_observed=true` 不会替代预期集合核验。没有参数预期且无已知错误时，完整训练结论 NOT_RUN；错误优先 FAIL。
- 可选 `parameter_checks` 是列表，每项 `{"kind":"equal|must_change","left":"<key>","right":"<key>"}`。参考和实测都核验 exact equal / 至少一元素变化，可表达 before/after 对应、冻结不变及上游非零更新。键名/step 无硬编码；工作流从 Host case 锁定规则，不从 observed 自报状态猜测。未声明规则就不声称已检验上游更新。快照是否来自运行时地址仍需 Sample/库接线证据。

## 离线重放（不接触设备）

以下离线重放和实时采集命令均在本技能的 `scripts/training/` 目录执行；脚本仍保留在该目录。

```powershell
python -B collect_training_serial.py --input-log <saved-raw.log> --expected <expected.json> --protocol-output <new-observed.json>
python -B compare_training_board.py --expected <expected.json> --observed <new-observed.json> --output <new-report.json>
# 也可以直接重放：
python -B compare_training_board.py --expected <expected.json> --raw-log <saved-raw.log> --output <new-report.json>
```

compare 每次读取 raw，重验身份/BEGIN/DONE/tensor；有 observed 时还核验 raw hash 和记录一致性，不信任单个 capture_complete 布尔值。旧 observed 没有 raw_log 路径时，可额外传 `--raw-log`，但其 raw_log_sha256 必须一致。

## 实时采集（仅设备拥有者执行）

先由工作流确认端口归属、停止旧 monitor；不要并行抢口。使用新 attempt 输出路径，不覆盖旧证据。

```powershell
$env:FBB_SDK_DIR='<已确认的fbb SDK目录>'
python -B collect_training_serial.py --port COM12 --baudrate 115200 --fbb-monitor --reset --seconds 60 --expected <expected.json> --output <new-raw.log> --protocol-output <new-observed.json>
python -B compare_training_board.py --expected <expected.json> --observed <new-observed.json> --output <new-report.json>
```

`--reset` 仅支持 live fbb，直接传给 `fbb monitor --reset`。SDK 使用继承的 `FBB_SDK_DIR`；兼容 collector 的 `--sdk-dir` 时也只是设置子进程环境，不给 fbb 追加该选项。运行前用本地 `fbb --help`、已设置 SDK 环境下的 `fbb monitor --help` 确认可用参数。

fbb 固定传入 `--until '(?m)^TRAIN_DONE \{[^\r\n]*\}\r?\n'`，只匹配完整 DONE 行；该正则仅控制后端停止，协议是否有效仍由共享解析器判断。fbb 的 --log 文件是串口原文；stdout/stderr 单独保留，不混作串口输入。

也可不使用 --fbb-monitor，走 pyserial（不支持 --reset）；读取超时返回的半行会拼接。原文与 parsed JSON 必须是不同路径，已有输出拒绝复用。

## 结果与退出码

collector 保存实际身份、capture_attempt_id、采集时间、raw 路径/hash、backend_command/stdout/stderr/returncode、transport_status、parse_status 和错误。退出 0 仅表示采集后端成功且协议完整，或离线解析成功；后端非零保留原码到 JSON，collector 自身返回 2。异常也尽量保留部分原文。

compare 的 0 只表示本 case 所声明检查 PASS；缺少文件等前置条件为 NOT_RUN，协议/身份/集合/数值错误为 FAIL，均非零。工具超时但原文完整可独立重放数值 PASS，同时保留 `capture_transport_status=FAIL` 与真实 backend_returncode，不把监视器改记为成功。直接 raw replay 没有传输回执时状态为 UNKNOWN。

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
