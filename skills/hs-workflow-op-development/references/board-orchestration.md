# Stage6/7 板端编排细则

## 目录

- [Stage6 固件矩阵](#stage6默认全矩阵固件接入与构建)
- [Stage7 烧录与精度](#stage7默认全矩阵烧录与板端精度)

> 仅在完整 AUTO_ALL 工作流进入板端阶段时读取。WS63 的具体接线步骤由
> `hs-verify-op-board/chips/ws63/references/sdk-integration.md` 负责；本文件记录顶层任务、文件交接和状态机衔接。

## stage6：默认全矩阵固件接入与构建

自动启动 `stage6.firmware_matrix`，按 `board_expected_matrix.json` 逐行记录构建结果；不允许
人工挑选代表用例或在完成一行后等待用户确认下一行。SDK/工具链确实不可用时写
`NOT_RUN`/`BLOCKED` 和恢复条件，并让状态机进入终态收尾；若阻断发生在 Stage0 执行确认前，
状态机会将 `stage5.final_docs` 自动标为 `BLOCKED`，只由 `terminal.report` 记录阻断状态，不调用文档 Skill。
确认后的后续阶段阻断才按其规则生成记录性
终态文档。状态脚本允许将当前阶段明确写为 `BLOCKED`，后续阶段会自动继承阻断标记。

除非用户在stage0明确`BOARD_POLICY=HOST_ONLY`，否则默认执行。本阶段若发现
`FIRMWARE_SDK_ROOT`缺失、身份变化或环境结论失效，自动将本阶段写为`BLOCKED`或`NOT_RUN`，
保存首个错误和恢复命令；不要在Host完成后补发第二次 SDK/执行确认。只有用户主动开始新的
范围或更换 SDK 时才新建一轮并重新执行Stage0。不能等到Host完成后才首次询问SDK；开始前必须显示：

```text
BOARD_SDK_GATE=PASS
FIRMWARE_SDK_ROOT=<用户明确提供的绝对路径>
FIRMWARE_SDK_SRC=<已核对的绝对路径>
chip=<chip>
target=<fbb真实target>
```

本阶段必须完整读取并逐节执行 [`hs-verify-op-board/chips/ws63/references/sdk-integration.md`](../../hs-verify-op-board/chips/ws63/references/sdk-integration.md)
及 Board Skill 的 [`references/ws63-build-handoff.md`](../../hs-verify-op-board/references/ws63-build-handoff.md)。下表是编排映射，不是删减步骤；每个映射项
仍须按被链接 reference 的原步骤执行并回传证据：

对于 WS63，顶层先调用 `hs-verify-op-board` step0-3 准备模型与 SDK 接线，在它输出构建 handoff
后才调用 `hs-dev-build`；构建结果返回同一轮 Board Skill step4 验收，不在烧录后重新从 step0
启动另一轮。下表列出每项的权威步骤和必须回传的交接：

| 编排项 | 具体步骤归属 | 必须回传的交接 |
|---|---|---|
| step0/0a | Board Skill step0/0a、SDK reference §1-2 | 用户授权 SDK、Git/dirty 基线、target、依赖和 `BOARD_SDK_GATE`/`PY_DEPS_GATE` |
| step1 | Board Skill step1、SDK reference §3 | 同轮 `board_expected_matrix.json` 的全部 Host PASS 行及模型、输入、GT |
| step2 | Board Skill step2、SDK reference §4-5、`ws63-build-handoff.md` | 每行 converter/Micro 工程、真实 RISC-V 编译、`libmicro_runtime.a`/`libnet.a` 及 receipt |
| step3 | Board Skill step3、SDK reference §6-10、`ws63-build-handoff.md` | adaptor、带 case 身份的模型库、Sample、CMake/Kconfig/target、`BOARD_WIRING_GATE=PASS` |
| step4 | Board Skill step4、SDK reference §11、`ws63-build-handoff.md` | `hs-dev-build` 返回的新鲜 fwpkg 和 `FIRMWARE_CONTENT_GATE=PASS` |

SDK reference 中的九项接线动作、模型库组成、Sample 输入/输出协议和构建前检查仍然是强制步骤，
由该 reference 维护；上表只负责步骤归属和交接，避免 workflow 同时展开两份细节。

矩阵按固定顺序`framework → case_id → mode(fp32,int8)`逐行执行。每行都要完成step2-4并生成
独立fwpkg；一张最小模型对应一组Micro库和一次固件构建，不能把某行的固件/日志复用于另一行。
case局部失败时记录后继续其余安全可执行行；环境、工具链或设备级失败会阻塞后续行，但所有
未执行行必须明确记为`NOT_RUN`。

SDK §4-5 的 Micro 生成/交叉编译以及 SDK §8 的 `prepare_sample.py` 在自动探测后的
`HISPARK_RUN_ENV` 执行（与 Host 共用可导入模型的 Python）；SDK §6-7、§9-10 的 adaptor、模型库、
`integrate_sdk.py` 和 wiring 在 `FIRMWARE_BUILD_ENV` 执行。两者不同时，按
`micro_build_receipt.json` 核对静态库哈希；保存 `prepare_sample.py` 的 PASS stdout，并为 Sample
输出目录生成本轮文件清单和 SHA-256 后再在固件构建环境运行
`integrate_sdk.py`。该脚本生成的
`ws63_board_env.ps1|sh` 必须在调用 `hs-dev-build` 的同一进程中导入；优先使用同目录
`invoke_hs_dev_build.ps1|sh`，否则先 source、回显 `AI_CUSTOM_SAMPLE_DIR` 与
`AI_MCU_MODEL_VARIANT`，再在同一进程调用 build Skill/fbb CLI。只生成、查看或在已退出的 shell
中 source 不算接线完成。SDK §8 的 `prepare_sample.py` 和 §10 的 `verify_wiring.py` 两个机械门禁不可由人工阅读
或临场生成代码替代；非 WS63 芯片必须先提供对应 `<chip>-sdk-integration.md` 及确定性脚本。

不得以新建一个能编译的 `ai_main.c`代替上述流程，也不得在找不到输入时填零、只打印
ArgMax/标签、让任务无限循环，或让Sample用硬编码答案自报最终精度PASS。

随后调用 `hs-dev-build` 生成 fwpkg；它只负责通过 fbb CLI 构建指定 target。若使用 CLI 回退，先从
`fbb list-targets --json` 或 `fbb describe --json` 获取真实 target，配置变更后强制 clean build。
必须按 SDK reference §11 和 [`hs-verify-op-board/references/ws63-build-handoff.md`](../../hs-verify-op-board/references/ws63-build-handoff.md) 运行
`hs-verify-op-board/chips/ws63/scripts/verify_firmware.py`，核对 Sample 对应
`.c.obj`、模型 Predict/Execute、目标 Kernel 和本轮新鲜度；只有 `FIRMWARE_CONTENT_GATE=PASS`
才能继续。`fbb build` 退出 0 但缺少这些证据时，stage6 仍为 FAIL。

构建错误分流：模型/算子生成代码错误回 stage2，再重跑 stage3-stage4；sample/adaptor/Kconfig 接线错误留在 stage6；工具链错误按 build skill 处理。

## stage7：默认全矩阵烧录与板端精度

自动启动 `stage7.board_matrix`，逐行完成烧录、串口采集和精度判定并立即保存。详细的 flash、
端口交叉探测、重插/RESET、monitor 时间和 JSON 解析规则必须读取
[`hs-verify-op-board/references/flash-serial-handoff.md`](../../hs-verify-op-board/references/flash-serial-handoff.md)；Tensor、阈值和矩阵规则必须读取
[`hs-verify-op-board/references/board-accuracy-contract.md`](../../hs-verify-op-board/references/board-accuracy-contract.md) 及
[`hs-verify-op-board/references/board-guardrails.md`](../../hs-verify-op-board/references/board-guardrails.md)。

对 `board_expected_matrix.json` 的每一行调用 `hs-dev-flash` 烧录该行 stage6 生成的新鲜固件，
只接受本轮 flash 的最后一行 `success=true` JSON，随后采集串口并运行精度判定；不能直接绕过统一
flash 入口调用 BurnTool。
进入本阶段以及每次 `PORT_NOT_FOUND` 重试前，必须按 [`hs-verify-op-board/references/flash-serial-handoff.md`](../../hs-verify-op-board/references/flash-serial-handoff.md) 运行
`probe_serial_ports.py` 并保存本轮回执；其中的 .NET/注册表交叉探测、PnP 超时和 USB-UART
候选排除规则是强制门禁，不能被简化为端口名称判断。

进入烧录前核对 `FBB_SDK_DIR`、真实 target 和 stage6 内容门禁的新鲜 `_all.fwpkg`。
端口歧义时按 [`hs-verify-op-board/references/flash-serial-handoff.md`](../../hs-verify-op-board/references/flash-serial-handoff.md) 输出候选、错误和恢复命令，请求具体端口选择或重新接线；
只读 stdout 最后一行 JSON 并按 `success` 与 `error.code` 分流。若返回 `DEVICE_NOT_RESPONDING`，
将该行标为 `NOT_RUN` 并记录一次人工 RESET 动作；不在后续阶段再次索取总确认。烧录后采集时间、端口和日志波特率必须可追溯；
缺任一证据都不能进入精度签收。详细执行规则由 `hs-dev-flash` 与 `hs-verify-op-board` step5
持有，workflow 仅核对执行完成和证据。

烧录成功不等于板端精度成功。将烧录和串口证据返回同一轮
`hs-verify-op-board` step5-6，传入已冻结的同轮 Host GT、测试输入、串口完整输出和
fp32/INT8模式，由它输出`ACCURACY_VERDICT`。这是恢复同一轮Board Skill，
不重跑step0-4的写入与构建动作。

固件构建与设备I/O环境可以不同。若SDK在WSL构建而串口只在Windows可见，把签收后的fwpkg
复制到Windows并核对哈希，再调用flash/serial能力；CLI回退可使用
`fbb flash --file <本地fwpkg> --chip <chip> --json-summary`。

`hs-verify-op-board`必须完整执行板端验证：核对前置产物、确认固件身份、
采集本次烧录后的完整串口Tensor、逐Tensor核对数量/shape/元素数并与同轮GT计算余弦。
不得把“烧录成功”“出现启动日志”或Sample自报PASS当作精度PASS。

每行完成后写 `<board-results>/<framework>/tc<case_id>/<mode>/board_result.json`。所有可执行行到达
`PASS|FAIL|NOT_RUN` 后运行 `hs-verify-op-board/scripts/board_matrix_report.py`，生成
`board_case_results.json` 和 `board_verify_summary.txt`；若阶段级工具/设备故障使部分行只能标为
`BLOCKED`，先为每个未执行行写入带原因的 `NOT_RUN` 记录，再运行报告并把阶段本身保留为 `BLOCKED`。
只有 `expected=executed=pass`、`fail=not_run=0` 且 `BOARD_MATRIX_GATE=PASS`，才允许整个板测输出
`ACCURACY_VERDICT=PASS`。`executed=pass+fail` 只统计真实进入板端执行的行；未执行行的
`board_result.json` 只算 `recorded`，不算 `executed`。

没有连接板卡、串口不可用或用户不在板边时，保留 Host 完成状态并将 stage7 标为未执行；不要反复烧录或用其他轮次串口日志冒充本轮板测。
