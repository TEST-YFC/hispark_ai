# 烧录与串口交接

目录：

- [step5：委托烧录并采集完整串口Tensor](#step5委托烧录并采集完整串口tensor)
- [端口重插后的重试顺序](#端口重插后的重试顺序)

进入对应阶段时读取本文件；flash JSON、端口探测、重插重试和串口完整性要求保持不变。

## step5：委托烧录并采集完整串口Tensor

完整workflow中，当前矩阵行step4验收通过后输出烧录handoff并暂停；顶层调用
`hs-dev-flash`/串口采集后，必须以同一receipt、固件哈希和case/mode恢复step5-6。

若由顶层workflow编排，把step4的新鲜 `_all.fwpkg`交回workflow调用 `hs-dev-flash`；
若单独调用本 Skill，则输出烧录handoff并等待返回。只接受flash Skill/fbb最后一行JSON
形成的结论。随后采集本次烧录后的串口文本。本skill也可接受workflow或用户提供的既有证据：

```text
FIRMWARE_BUILD=PASS
FLASH_VERDICT=PASS
firmware=<absolute fwpkg path>
target=<fbb target>
port=<serial port>
```

烧录交接必须保留以下执行规则，不能缩写成“运行 fbb flash”：

1. 设置并回显用户授权SDK对应的 `FBB_SDK_DIR=<FIRMWARE_SDK_SRC>`；target必须来自
   `fbb describe --json`或`fbb list-targets --json`，固件必须是 step4 确认的 `_all.fwpkg`；
2. 烧录前必须先运行本 skill 的 `scripts/probe_serial_ports.py`，保存本轮
   `serial_probe.json`。Windows 不能只调用 `Win32_SerialPort`/WMI：至少交叉查询
   `.NET SerialPort.GetPortNames()` 与 `HKLM:\\HARDWARE\\DEVICEMAP\\SERIALCOMM`；
   `pnputil /enum-devices /class Ports /connected` 作为第三来源，但必须有超时，不能因
   PnP/WMI 卡住整个工作流。WSL/Linux 要记录 `/dev/serial/by-id`、`/dev/serial/by-path`
   和 `ttyUSB/ttyACM`。探测回执必须列出每个来源、错误、端口、设备描述/VID/PID（如可得）
   和探测时间；单一来源没有发现端口时不得结论为“无板”。USB 刚重插或上一次返回
   `PORT_NOT_FOUND` 时，必须使用新的输出文件执行有界重探，例如：
   `python3 <skill_root>/scripts/probe_serial_ports.py --output <serial_probe.json> --attempts 3 --interval 2`；
   不得沿用旧回执或旧端口候选。
3. 解析 `serial_probe.json` 后，排除 Intel AMT SOL、Bluetooth 等内部/虚拟端口，优先
   标记 CH340/CH341、CP210x、FTDI、USB-SERIAL 等 USB-UART 候选。设备名只是候选依据，
   不是板卡身份；仍须让 `hs-dev-flash`/`fbb flash --json-summary` 完成真实设备和目标核验。
   只有唯一候选且 flash 返回 `success=true` 才能继续；候选为零或多个时输出候选清单和
   各来源证据，状态为 `NOT_RUN`/端口歧义并请求用户选择或重新接线。
4. 默认执行 `fbb flash <target> --json-summary`。只有端口自动检测歧义时才让用户选择
   或显式传 `--port COM<N>`，不得凭设备名猜控制口/烧录口；
5. 只解析stdout最后一行JSON：`success=true`才是 `FLASH_VERDICT=PASS`；失败必须按
   `error.code`分流，不能按自然语言或进度日志猜成功；
6. `DEVICE_NOT_RESPONDING`时先确认用户就在板边并能按RESET，再启动一次
   `--manual-reset`重试，并明确告知只按一下RESET；不得在用户未确认在场时消耗复位窗口；
7. `PORT_NOT_FOUND`先释放可能占用端口并重新运行本条第2项的探测；如果用户已重插
   USB，等待系统枚举后使用新的探测回执再烧录。重探仍无候选或存在多个候选时记录
   `NOT_RUN`并请求用户选择/重新接线，不能猜测端口。`PORT_BUSY`先释放占用，
   `FWPKG_NOT_FOUND`回构建阶段，其他硬错误保留完整JSON并停止盲目重试；
8. 若使用`--then-monitor`，monitor必须在本次烧录成功后开始并保存完整原文；否则由
   串口能力使用同一端口和Sample规定波特率采集。烧录波特率不能当作启动日志波特率。

这些规则由 `hs-dev-flash`拥有；本skill负责在handoff和返回证据中逐项核对，不复制或
绕过烧录实现。缺少端口、最终 JSON、烧录时间或本次 monitor 时间任一证据时，不能确认精度。

### 端口重插后的重试顺序

端口重插属于设备枚举变化，按一次新的 step5 尝试处理：

1. 停止占用旧端口的 monitor/串口进程，并保留旧日志作为历史背景；
2. 等待系统完成 USB 枚举，使用 `--attempts`/`--interval` 运行新的交叉探测，
   将每次尝试和最终候选写入新的 `serial_probe.json`；
3. 只从最新回执中的唯一 `usb_uart_candidate` 选择端口，再调用
   `hs-dev-flash`；烧录成功后重新采集串口并重新生成精度证据；
4. 将新的探测回执、flash JSON、monitor 和精度路径写入同一 case 的
   `board_result.json`。旧回执只能用于解释失败原因，不能作为本轮 PASS 证据。

固件构建和设备I/O环境可以不同。SDK在WSL构建但串口只在Windows可见时，复制并核对fwpkg
哈希后在Windows烧录；CLI回退可使用
`fbb flash --file <Windows本地fwpkg> --chip ws63 --json-summary`。

同时确认固件确实接入step1的模型和输入，sample会打印完整输出Tensor，而不只是启动
日志、argmax、标签或Sample自行输出的PASS。

没有连接开发板、没有烧录成功证据、用户不在板边或串口不可用时，将当前行及尚未执行行
记录为`NOT_RUN`并返回workflow。Host PASS保持有效，但不能宣称板测完成。设备探测得到唯一
兼容板卡/端口时直接自动继续，不询问“是否上板”；只有无板卡、端口歧义或人工RESET等异常才交互。

接受 workflow 通过 `hs-dev-flash` 的可选 `fbb flash ... --then-monitor` 链路、串口 skill 或其他已验证串口工具保存的本轮文本。文件必须包含本次烧录后的启动与推理输出，并能追溯端口和采集时间。不得使用早于本轮烧录的 monitor、截断后的十个元素、手抄 Tensor 或只有分类标签的日志。解析不到完整 Tensor 或机器可读 shape 时，本步骤 FAIL。
