# Stage5/Stage6 板端编排细则

## 目录

- [Stage5 固件矩阵](#stage5默认全矩阵固件接入与构建)
- [Stage6 烧录与精度](#stage6默认全矩阵烧录与板端精度)

> 仅在完整 AUTO_ALL 工作流进入板端阶段时读取。WS63 的具体接线步骤由
> `hs-verify-op-board` 内的 `chips/ws63/references/sdk-integration.md` 负责；本文件记录顶层任务、文件交接和状态机衔接。

## Stage5：默认全矩阵固件接入与构建

自动启动 `stage5.firmware_matrix`，并按 `board_expected_matrix.json` 逐行记录构建结果。
不得人工挑选代表用例，也不得每完成一行就等待用户确认下一行。SDK 或工具链不可用时，记录
`NOT_RUN`/`BLOCKED` 和恢复条件，然后让状态机进入终态收尾。若阻断发生在 Stage0 执行确认前，
状态机会将 `stage7.final_docs` 标为 `BLOCKED`，只由 `terminal.report` 记录阻断状态，不调用文档 Skill。
确认后发生的阻断，按对应规则生成记录性终态文档。当前阶段可明确写为 `BLOCKED`，后续阶段由状态脚本继承阻断标记。

除非用户在 Stage0 明确选择`BOARD_POLICY=HOST_ONLY`，否则执行本阶段。若此时发现
`FIRMWARE_SDK_ROOT`缺失、身份变化或环境结论失效，将本阶段写为`BLOCKED`或`NOT_RUN`，
并保存首个错误和恢复命令。不要在 Host 完成后补发第二次 SDK/执行确认。只有用户主动改变范围或
更换 SDK 时，才新建一轮并重新执行 Stage0。不能等到Host完成后才首次询问SDK；开始前必须显示：

```text
BOARD_SDK_GATE=PASS
FIRMWARE_SDK_ROOT=<用户明确提供的绝对路径>
FIRMWARE_SDK_SRC=<已核对的绝对路径>
chip=<chip>
target=<fbb真实target>
```

本阶段完整读取并逐节执行 `hs-verify-op-board` 内的 `chips/ws63/references/sdk-integration.md`
和 `references/ws63-build-handoff.md`。下表只映射顶层编排与具体步骤，不删减任何步骤；
每一项仍须按对应 reference 执行并回传证据。

对于 WS63，先调用 `hs-verify-op-board` step0-3 准备模型并完成 SDK 接线。收到构建 handoff 后，
再调用 `hs-dev-build`。构建结果返回同一轮 Board Skill，由 step4 验收；烧录后不重新从 step0 启动。
下表列出各项的权威步骤和必要交接：

| 编排项 | 具体步骤归属 | 必须回传的交接 |
|---|---|---|
| step0/0a | Board Skill step0/0a、SDK reference §1-2 | 用户授权 SDK、Git/dirty 基线、target、依赖和 `BOARD_SDK_GATE`/`PY_DEPS_GATE` |
| step1 | Board Skill step1、SDK reference §3 | 同轮 `board_expected_matrix.json` 的全部 Host PASS 行及模型、输入、GT |
| step2 | Board Skill step2、SDK reference §4-5、`ws63-build-handoff.md` | 每行 converter/Micro 工程、真实 RISC-V 编译、`libmicro_runtime.a`/`libnet.a` 及 receipt |
| step3 | Board Skill step3、SDK reference §6-10、`ws63-build-handoff.md` | adaptor、带 case 身份的模型库、Sample、CMake/Kconfig/target、`BOARD_WIRING_GATE=PASS` |
| step4 | Board Skill step4、SDK reference §11、`ws63-build-handoff.md` | `hs-dev-build` 返回的新鲜 fwpkg 和 `FIRMWARE_CONTENT_GATE=PASS` |

九项接线动作、模型库组成、Sample 输入/输出协议和构建前检查由 SDK reference 统一定义，均为强制步骤。
上表只说明步骤归属和交接，不重复这些细节。

按固定顺序`framework → case_id → mode(fp32,int8)`逐行执行矩阵。每行都要完成 step2-4，并生成
独立 fwpkg。一张最小模型对应一组 Micro 库和一次固件构建；不能复用其他行的固件或日志。
单个 case 失败时，记录结果，并继续其余可安全执行的行。环境、工具链或设备级失败会阻塞后续行；
所有未执行行必须明确记为`NOT_RUN`。

在自动探测得到的 `HISPARK_RUN_ENV` 中执行 SDK §4-5 的 Micro 生成/交叉编译和 SDK §8 的
`prepare_sample.py`；这些步骤与 Host 共用可导入模型的 Python。在 `FIRMWARE_BUILD_ENV` 中执行
SDK §6-7、§9-10 的 adaptor、模型库、`integrate_sdk.py` 和 wiring。两个环境不同时，按
`micro_build_receipt.json` 核对静态库哈希。保存 `prepare_sample.py` 的 PASS stdout，并为 Sample
输出目录生成本轮文件清单和 SHA-256，然后在固件构建环境运行 `integrate_sdk.py`。

必须在调用 `hs-dev-build` 的同一进程中导入该脚本生成的 `ws63_board_env.ps1|sh`。优先使用同目录的
`invoke_hs_dev_build.ps1|sh`；否则先 source 并回显 `AI_CUSTOM_SAMPLE_DIR` 和 `AI_MCU_MODEL_VARIANT`，
再在同一进程调用 build Skill/fbb CLI。仅生成或查看文件，或在已经退出的 shell 中 source，都不算完成接线。
SDK §8 的 `prepare_sample.py` 和 §10 的 `verify_wiring.py` 是必须执行的脚本检查，不能以人工阅读或临时生成代码替代。
非 WS63 芯片必须先提供对应的 `<chip>-sdk-integration.md` 和确定性脚本。

不得以仅新建一个可编译的 `ai_main.c` 替代上述流程，也不得在找不到输入时填零、只打印
ArgMax/标签、让任务无限循环，或让 Sample 用硬编码答案自报最终精度 PASS。

随后调用 `hs-dev-build` 生成 fwpkg；它只负责通过 fbb CLI 构建指定 target。若使用 CLI 回退，先从
`fbb list-targets --json` 或 `fbb describe --json` 获取真实 target，配置变更后强制 clean build。
必须按 SDK reference §11 和 `hs-verify-op-board` 内的 `references/ws63-build-handoff.md` 运行
该 Skill 内的 `chips/ws63/scripts/verify_firmware.py`，核对 Sample 对应
`.c.obj`、模型 Predict/Execute、目标 Kernel 和本轮新鲜度；只有 `FIRMWARE_CONTENT_GATE=PASS`
才能继续。`fbb build` 退出 0 但缺少这些证据时，Stage5 仍为 FAIL。

构建错误分流：模型/算子生成代码错误回 Stage2，再重跑 Stage3-Stage4；sample/adaptor/Kconfig 接线错误留在 Stage5；工具链错误按 build skill 处理。

## Stage6：默认全矩阵烧录与板端精度

自动启动 `stage6.board_matrix`。逐行完成烧录、串口采集和精度判定，并立即保存结果。
flash、端口交叉探测、重插/RESET、monitor 时间和 JSON 解析规则见 `hs-verify-op-board` 内的
`references/flash-serial-handoff.md`；Tensor、阈值和矩阵规则见同一 Skill 内的
`references/board-accuracy-contract.md` 和 `references/board-guardrails.md`。

对 `board_expected_matrix.json` 的每一行，调用 `hs-dev-flash` 烧录该行在 Stage5 生成的新鲜固件。
只接受本轮 flash 最后一行的 `success=true` JSON；然后采集串口并运行精度判定。不能绕过统一 flash 入口直接调用 BurnTool。
进入本阶段以及每次 `PORT_NOT_FOUND` 重试前，按 `hs-verify-op-board` 内的
`references/flash-serial-handoff.md` 运行 `probe_serial_ports.py`，并保存本轮回执。.NET/注册表交叉探测、
PnP 超时和 USB-UART 候选排除规则都是强制门禁，不能简化为只判断端口名称。

烧录前，核对 `FBB_SDK_DIR`、真实 target，以及通过 Stage5 内容门禁的新鲜 `_all.fwpkg`。
端口有歧义时，按 `hs-verify-op-board` 内的 `references/flash-serial-handoff.md` 输出候选、错误和恢复命令，
请求用户选择具体端口或重新接线。只读取 stdout 最后一行 JSON，并按 `success` 和 `error.code` 分流。
若返回 `DEVICE_NOT_RESPONDING`，将该行标为 `NOT_RUN`，并记录一次人工 RESET 动作；后续阶段不再索取总确认。
烧录后的采集时间、端口和日志波特率必须可追溯；缺少任一证据时，不能确认精度结果。
具体执行规则由 `hs-dev-flash` 和 `hs-verify-op-board` step5 定义；workflow 只核对执行状态和证据。

烧录成功不代表板端精度通过。将烧录和串口证据返回同一轮 `hs-verify-op-board` step5-6，
并传入本轮已冻结的 Host GT、测试输入、串口完整输出和 fp32/INT8 模式，由它输出`ACCURACY_VERDICT`。
这是继续同一轮 Board Skill，不重跑 step0-4 的写入与构建动作。

固件构建与设备 I/O 环境可以不同。若 SDK 在 WSL 构建而串口只在 Windows 可见，将通过内容检查的 fwpkg
复制到 Windows 并核对哈希，再调用 flash/serial 能力；CLI 回退可使用
`fbb flash --file <本地fwpkg> --chip <chip> --json-summary`。

`hs-verify-op-board`必须完整执行板端验证：核对前置产物、确认固件身份、
采集本次烧录后的完整串口Tensor、逐Tensor核对数量/shape/元素数并与同轮GT计算余弦。
不得把“烧录成功”“出现启动日志”或Sample自报PASS当作精度PASS。

每行完成后写 `<board-results>/<framework>/tc<case_id>/<mode>/board_result.json`。所有可执行行到达
`PASS|FAIL|NOT_RUN` 后运行 `hs-verify-op-board` 内的 `scripts/board_matrix_report.py`，生成
`board_case_results.json` 和 `board_verify_summary.txt`；若阶段级工具/设备故障使部分行只能标为
`BLOCKED`，先为每个未执行行写入带原因的 `NOT_RUN` 记录，再运行报告并把阶段本身保留为 `BLOCKED`。
只有 `expected=executed=pass`、`fail=not_run=0` 且 `BOARD_MATRIX_GATE=PASS`，才允许整个板测输出
`ACCURACY_VERDICT=PASS`。`executed=pass+fail` 只统计真实进入板端执行的行；未执行行的
`board_result.json` 只算 `recorded`，不算 `executed`。

没有连接板卡、串口不可用或用户不在板边时，保留 Host 完成状态并将 Stage6 标为未执行；不要反复烧录或用其他轮次串口日志冒充本轮板测。
