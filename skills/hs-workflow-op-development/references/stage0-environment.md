# Stage0 环境探测与确认细则

## 目录

- [冻结范围和环境](#stage0冻结范围和环境)
- [自动探测顺序](#stage0-自动探测顺序)
- [确认模板](#stage0-完成只读探测后必须发出的执行确认模板)
- [自动化边界与依赖修复](#默认自动化与用户交互边界)

> 仅在 Stage0 需要环境判断、用户确认模板或依赖修复时读取。探测仍必须先由入口状态机初始化并记录。

## stage0：冻结范围和环境

进入Stage0的第一项动作是按 [`workflow-state.md`](workflow-state.md) 中的 `init` 约定运行
`scripts/workflow_state.py init`，生成本轮待办和临时检查点；
状态文件本身是控制性记录，不属于算子源码或交付文档写入。随后记录 source entry、
implementation unit 候选、代码根、`MSLITE_OP_OUTPUT`、板测策略、板卡连接状态，以及各专项
Skill 的可用性，并在 `stage0.scope_environment` 完成后立即 `finish`。完整workflow默认
`BOARD_POLICY=AUTO_ALL`；只有用户明确说“只做Host/不上板/不烧录”才记录
`BOARD_POLICY=HOST_ONLY`。Stage0只完成只读探测和计划生成；在`EXECUTION_CONFIRM_GATE=PASS`
前禁止进入stage1，禁止调用下游生成/实现/验证Skill；禁止创建或修改算子文档、源码、测试模型、Micro工程、SDK接线和固件，
禁止安装、下载、构建、烧录或启动后台长任务。
若 `stage0.scope_environment` 以失败或阻断结束且尚未通过确认，状态机会自动将
`stage5.final_docs` 标为 `BLOCKED`，只允许 `terminal.report` 写入阻断运行的失败原因、恢复命令和状态证据；此例外不得生成或修改
算子设计/验证交付文档，常规终版文档回填仍须在确认通过且 stage6、stage7 到达终态后执行。

开始前先自动探测代码存储位置和各阶段实际执行环境；可由当前会话、路径存在性和工具实测
唯一确定的信息不得再次询问用户。路径只直接证明“文件存在哪里”，不能单独证明“命令在哪里
执行”：例如 Windows 工作区和其 `/mnt/<drive>/...` 映射表示同一类存储位置，但 Linux ELF版
`converter_lite`仍应在WSL/Linux运行，Windows侧SDK也可能由Windows侧`fbb CLI`驱动构建。必须分别
记录以下字段：

```text
HISPARK_ROOT=<绝对路径>
HISPARK_STORAGE_ENV=<Windows|WSL|Linux>
HISPARK_RUN_ENV=<WSL|Linux>
WSL_DISTRO=<使用WSL时填写>
FIRMWARE_SDK_ROOT=<要求固件/板测时填写>
FIRMWARE_SDK_STORAGE_ENV=<Windows|WSL|Linux>
FIRMWARE_BUILD_ENV=<Windows|WSL|Linux>
DEVICE_IO_ENV=<Windows|WSL|Linux>
TARGET_RUNTIME=<chip/board/OS/fbb-target>
```

`HISPARK_STORAGE_ENV`和`FIRMWARE_SDK_STORAGE_ENV`只描述两个仓库所在的文件系统；
`HISPARK_RUN_ENV`描述MindSpore Lite、converter、Host harness和Micro库构建命令的执行环境；
`FIRMWARE_BUILD_ENV`只描述fbb/SDK固件编译实际运行处；`DEVICE_IO_ENV`只描述烧录和串口可见处。
这些字段允许不同，例如HiSpark.AI存于Windows盘、MSLite命令在WSL执行、SDK在Windows编译、
串口也由Windows访问。

术语必须统一：`fbb CLI`是提供`fbb describe/build/flash/monitor`等命令的命令行工具，命令名
本身仍写作`fbb`；`固件SDK`是用户提供的芯片源码工程；`交叉编译工具链`是由fbb CLI调用的
编译器和构建工具；`固件`是编译后生成、用于烧录的`.fwpkg`文件。不得把fbb CLI称为SDK，
也不得把开发板连接环境或串口称为固件。

### Stage0 自动探测顺序

先执行只读探测并记录每项结论的命令/输出摘要：

1. 从当前工作目录、用户已给路径及路径在当前环境中的实际存在性确定`HISPARK_ROOT`和
   `HISPARK_STORAGE_ENV`；Windows路径与其`/mnt/<drive>/...`映射视为同一存储身份。
2. 检查`converter_lite`或现有`MSLITE_PKG`的二进制类型（如`file converter_lite`），并在候选
   Linux/WSL环境实测`--help`或`--version`。当前工具为Linux ELF时，自动选择唯一可执行的
   Linux/WSL环境作为`HISPARK_RUN_ENV`；使用WSL时一并记录真实发行版。
3. 只有用户已提供`FIRMWARE_SDK_ROOT`时才探测固件环境。分别在可访问该路径的Windows、WSL
   或Linux候选环境执行`fbb --version`和针对该SDK的`fbb describe --json`，不能只检查命令是否
   存在。必须同时比较`fbb_cli.version`与SDK全局及目标芯片声明的`min_cli_version`；版本不足的
   候选环境标记`BLOCKED`，不能因为describe成功就视为可构建。SDK在Windows文件系统且Windows侧检查成功时优先Windows；SDK在WSL/Linux原生文件
   系统且对应环境检查成功时优先该环境；只有一个候选通过时自动选择它。
4. 从SDK身份、芯片参考和`fbb describe --json`记录`TARGET_RUNTIME`；不能把Host或固件编译
   环境误写成MCU实际运行环境。
5. 分别探测候选环境中的兼容设备/串口可见性。Windows 必须运行
   `hs-verify-op-board/scripts/probe_serial_ports.py`，交叉记录 `.NET SerialPort.GetPortNames()`、
   `HKLM:\\HARDWARE\\DEVICEMAP\\SERIALCOMM` 和有界的 `pnputil` 结果；不得只依赖
   `Win32_SerialPort`/WMI。WSL/Linux 记录 `/dev/serial/by-id`、`/dev/serial/by-path` 及
   `ttyUSB/ttyACM`。串口探测必须在 `DEVICE_IO_ENV` 执行：Windows 设备用 Windows Python/PowerShell
   运行脚本并保存 Windows 绝对路径；只有 `DEVICE_IO_ENV=WSL|Linux` 时才在 WSL/Linux 探测 `/dev`。
   `HISPARK_RUN_ENV=WSL` 不代表 Windows COM 会自动出现在 WSL；跨环境交接时必须复制并记录
   `serial_probe.json`、固件的绝对路径和 SHA-256。保存的回执包括每个来源的端口、设备描述、VID/PID、错误和时间。
   只有一个环境能看到唯一 USB-UART 候选且后续 `hs-dev-flash` 返回真实 `success=true` 时，
   才记录 `DEVICE_IO_ENV`和端口；未检测到、多个候选或来源冲突时进入用户交互，不能直接判定“无板”。
6. 两个环境都能成功构建同一SDK且没有更强证据可唯一选择时，不擅自偏好某一边，在本次
   Stage0 执行确认预览中向用户询问一次`FIRMWARE_BUILD_ENV`；设备I/O同理。该选择属于
   Stage0 的唯一人工交互，确认后不得在 Stage6/7 或其他普通阶段再次询问。

自动探测只允许读取状态，不能通过扫描磁盘自行挑选一个未由用户提供的可写SDK。完整workflow
缺少`FIRMWARE_SDK_ROOT`时只询问该绝对路径；收到路径后再自动判断其存储、构建和设备I/O环境，
不能在尚无SDK路径时要求用户同时填写三个环境字段。

### Stage0 完成只读探测后必须发出的执行确认模板

对“生成/实现/适配算子”，工具调用前可以先发简短进度说明；完成上述Stage0只读探测后的
第一条环境状态回复必须集中展示算子范围、四类环境、探测依据、完整阶段、预计写入/产物位置
和仍需人工处理的条件，再等待一次执行确认。`待提供/待确认`部分只列真正无法自动确定的项：

面向用户的正文使用中文含义，不把`BOARD_POLICY`、`DEVICE_IO_ENV`、`TARGET_RUNTIME`、
`EXECUTION_CONFIRM_GATE`等内部字段当成标题或要求用户理解。确需保留机器状态时统一放在末尾
“技术记录”中。尤其要解释：“开发板连接环境”是电脑在哪个系统中通过USB/串口烧录和读取
日志，不是固件；固件是后续构建出的`.fwpkg`文件。

```text
执行方式：完整开发和验证（默认）
将完成算子设计、代码实现、电脑端全部测试、固件编译、烧录和开发板全部测试。

本次算子：<算子名称>
来源模型格式：<ONNX/TFLite/...>
预计涉及：<只读扫描得到的实现单元候选；用普通中文描述>

检测到的环境：
  HiSpark.AI代码位置：<绝对路径；Windows磁盘或Linux文件系统>
  模型转换和电脑端测试：<在Windows/WSL/Linux中的哪个环境运行，并说明原因>
  固件SDK位置：<绝对路径；Windows磁盘或Linux文件系统>
  固件编译：<在哪个环境运行fbb CLI和交叉编译工具链>
  开发板连接：<在哪个环境烧录并读取串口；例如Windows COM5；未检测到则明确说明>
  板上运行目标：<芯片、操作系统、构建target>

判断依据：<路径映射、converter类型、fbb CLI版本/SDK要求和串口探测结果，用一句话解释>

接下来会执行：
  1. 编写算子说明、实现约定和测试计划
  2. 实现或补齐算子代码，并完成代码审查
  3. 编译MindSpore Lite转换工具和通用算子库
  4. 在电脑端生成全部测试模型，逐项转换、编译、运行并检查精度
  5. 根据实际结果更新最终算子文档
  6. 为每个板测用例生成Micro代码和静态库，并编译WS63固件
  7. 逐个烧录全部用例，读取串口输出，与电脑端标准答案比较

预计修改和生成：<算子源码、测试目录、报告目录、SDK中的隔离Sample和固件路径>

当前状态：等待你的确认，尚未生成代码、编译或烧录。
请回复“确认执行”；如果这次不需要开发板验证，请回复“只做电脑端验证”。

技术记录：STAGE0_PREVIEW=READY；BOARD_POLICY=AUTO_ALL；EXECUTION_CONFIRM_GATE=PENDING
```

如果缺少`FIRMWARE_SDK_ROOT`，先只展示已知的HiSpark存储/运行环境和默认AUTO_ALL范围，在同一条
Stage0 执行确认预览中索取SDK绝对路径和执行范围确认，不得猜测或自动挑选路径。收到这一条回复后，agent 无需
再次询问：先用该路径自动完成剩余只读探测，把回执作为
`stage0.scope_environment` 的 evidence 并 `finish`；只有 stage0 已经 PASS 后，才调用
`confirm --confirmed-mode AUTO_ALL --sdk-root <绝对路径>`，把同一条回复作为唯一确认落盘并进入
stage1。若某项仍有歧义，只把该项及候选证据列为`待确认`，待用户修正后在新 RUN_ID 重新展示
最终方案；这仍属于 Stage0 初始确认修正，不是后续阶段的二次确认。
用户明确回复“确认/继续/按上述方案执行”等同意语义后记录`EXECUTION_CONFIRM_GATE=PASS`，才可
进入stage1。用户要求调整范围或更换 SDK 时废弃当前轮次并新建 `RUN_ID`，重新执行 stage0 和
唯一一次确认；如果调整来自这条唯一回复，agent 自动重建 run、完成只读探测并复用该回复，
不得要求用户再次确认。尤其不能在 AUTO_ALL run 上直接执行
`confirm --confirmed-mode HOST_ONLY`。不得把最初一句
“生成某算子”或提供SDK路径本身当成已经通过该门禁。

记录用户回答后，在每个阶段用实际命令验证路径和工具是否可用。当前MSLite工具包是
Linux x64程序，因此MSLite构建、Host harness、converter、`prepare_sample.py`和Micro库构建在Linux/WSL执行；
固件构建与烧录可以位于另一环境。跨Windows/WSL时在命令边界转换路径，并在复制模型库或
fwpkg时核对哈希即可，不为环境组合另建一套状态机。
转入`hs-workflow-mslite-env-setup`时显式传递
`HISPARK_AI_ROOT=$HISPARK_ROOT`；两个名称表示同一个 HiSpark.AI 项目根目录。

### 默认自动化与用户交互边界

- 用户已经给出`FIRMWARE_SDK_ROOT`，表示允许Stage0对该SDK做只读身份和环境探测；只有一次
  总确认通过后才允许在该SDK内完成确定性接线和构建。确认通过后不得再询问“是否要上板”。
- 总确认已通过、固件位置已给出且设备探测得到唯一兼容板卡/端口时，自动执行全用例固件构建、烧录、串口
  采集和精度判定，直至全矩阵终态。
- 标准流程只在Stage0进行一次总确认。确认成功后，文档生成、源码编写、代码审查、构建、Host
  和板端验证均由 agent 按待办自动推进，不再逐阶段询问是否继续。Stage0没有发现、或确认后
  外部条件发生变化时，自动把缺少的 SDK、设备、端口、权限或工具记录为 `BLOCKED/NOT_RUN`，
  保存首个错误和恢复命令后停止受影响分支；本轮不发起第二次常规确认。用户以后补齐条件并
  显式执行同一 RUN_ID 的 `resume` 时再继续，不能把未执行写成验证完成。
- 用户明确`HOST_ONLY`时不探测、不构建、不烧录，报告`NOT_REQUESTED`；默认策略下因外部条件
  不能执行则报告`NOT_RUN`，两者不能混用。

### 缺失依赖自动修复

总确认通过后，运行中出现`ModuleNotFoundError`、`command not found`或等价依赖缺失时，不能只
报告“缺少xxx”就结束。先确认报错发生在哪个执行环境、使用哪个Python/工具，再按以下边界修复：

1. 对`onnx`、`onnxruntime`、`numpy`、`PyYAML`、`openpyxl`等可通过pip安装的轻量Python包，
   优先使用项目已有虚拟环境；没有虚拟环境时使用当前用户范围，禁止`sudo pip`和静默修改系统
   Python。版本优先取仓库requirements/lock、README或工具兼容声明；没有约束时让pip解析兼容版。
2. 自动执行安装时记录`DEPENDENCY_REPAIR`、执行环境、Python绝对路径、安装命令、包版本和日志；
   镜像源失败可再尝试默认源。安装后必须用同一解释器执行真实`import`/`--version`验证，成功后
   自动重新启动失败阶段。构建或长测试环境发生变化时生成新`RUN_ID`，不得读取旧失败状态。
3. 只有安装需要管理员/root权限、全局系统修改、卸载或降级现有包、解决破坏性版本冲突、接受
   许可证/登录、下载大型SDK/专有工具链，或写入Stage0未确认的目录时，才把该项记为
   `BLOCKED`，同时写明“需要安装什么、为什么、将修改哪里、预计大小/影响”。不要在后续阶段
   再索取常规确认；把所需授权和恢复命令写入状态，用户随后主动授权并通过同一 RUN_ID 的
   恢复动作继续。
4. 自动安装和验证均失败时，报告已尝试的命令、两个源的首个真实错误、当前解释器和下一步，
   再将阶段标为`BLOCKED`；不能只复述缺少的包名，也不能伪造后续PASS。

ONNX Host路径开始前必须同时验证`onnx`（建模/读图）和`onnxruntime`（参考推理）；TFLite路径
验证`tensorflow`；报告生成验证`openpyxl`。这些是运行依赖，不是算子实现失败。

在修改算子源码前建立环境控制基线：记录 MindSpore Lite 主仓/子模块 HEAD、dirty fingerprint、当前 `MSLITE_PKG` 及 converter 路径；若已有一条与目标算子无关且 `verify_summary.txt` 明确 PASS 的稳定 Host case，先读取其 `output/<path>/_driver.sh` 中冻结的 `MSLITE_PKG`，用 `realpath` 与当前记录的包逐字核对。路径一致时才可执行 `_run.sh`，确认重新转换、编译、运行和 judge 仍 PASS；路径不一致时必须用当前环境变量和该控制 spec 重新调用 Host harness（至少 x86 路径），不能让陈旧 wrapper/converter 产生 `ENV_BASELINE=PASS`。这一步的作用是把 converter/工具链/子模块故障与后续算子缺陷分开。

没有可复用稳定 case 时记录 `ENV_BASELINE=UNKNOWN reason=no-known-pass-case`，不得伪称环境已验证；后续若多个无关用例在 converter 启动阶段成片失败，先补跑未改动控制用例或重建工具包，不允许直接修改目标算子源码。基线本身失败时记录 `ENV_BASELINE=FAIL` 并停在环境分支，源码保持未修改。

优先保证 PC/WSL 单元/Host 验证可运行。即使没有开发板，也继续 stage1-stage5；不要因烧录不可用而跳过 Host 测试。
