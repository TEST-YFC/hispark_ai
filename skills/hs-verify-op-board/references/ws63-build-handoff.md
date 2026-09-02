# WS63 build handoff

目录：

- [step2：生成Micro工程并交叉编译模型库](#step2生成micro工程并交叉编译模型库)
- [step3：adaptor、Sample与SDK接线](#step3adaptorsample与sdk接线)
- [step4：委托构建并核对固件身份](#step4委托构建并核对固件身份)

以下内容从入口按需下沉；每一行独立模型库、Sample、接线和固件身份规则保持不变。

## step2：生成Micro工程并交叉编译模型库

完整执行 `chips/ws63/references/sdk-integration.md` 第3-5节，并且必须调用确定性入口
`chips/ws63/scripts/build_micro.py`，不能临场拼converter/CMake命令：

- 对step1矩阵当前行的具体模型运行converter_lite；
- `build_micro.py`自动从本轮`MSLITE_PKG`定位`libmindspore_converter.so`，过滤其他MSLite
  包的旧动态库目录，在启动converter的同一子进程中注入；不得要求用户先手工`export`，也
  不得修改系统级`ldconfig`或shell启动文件；包内确实缺库时才以环境门禁停止并请求确认重建/下载；
- 在与真实转换相同的动态库环境中先运行一次 `converter_lite --help`；明确支持
  `--encryption`时传`--encryption=false`，明确不支持时省略，探测失败则以环境门禁FAIL停止；
- 检查生成的 `model0.c`、`net0.c/Execute0()`和目标Kernel符号；
- 使用真实RISC-V工具链构建 `libmicro_runtime.a`和 `libnet.a`；
- 核对归档对象、模型身份、dtype和当前case，禁止使用陈旧库冒充。

任何失败先保留converter/编译原文，再根据证据回流算子实现、工具链或模型配置。case局部失败
时记录该行FAIL并继续其他安全可执行行；环境/工具链公共失败时停止后续动作，并把剩余行逐项
记录为NOT_RUN，不能缩小expected分母。
本步骤只能在Linux/WSL的`HISPARK_RUN_ENV`运行；Windows固件编译不意味着Linux版
`converter_lite`也能在Windows运行。

## step3：adaptor、Sample与SDK接线

完整执行 `chips/ws63/references/sdk-integration.md` 第6-10节，包括以下确定性动作。`prepare_sample.py`
属于 SDK §8，应在与 Host 相同的 `HISPARK_RUN_ENV`/Python 中生成并验证 Sample；随后保存脚本
的 PASS stdout，并为 Sample 输出目录生成本轮文件清单和 SHA-256，再将 Sample 交给
`FIRMWARE_BUILD_ENV`，在那里执行 SDK §6-7、§9-10 的 SDK 接线和
`integrate_sdk.py`/`verify_wiring.py`：

1. 以HiSpark.AI的 `src/adaptor`为来源安装或逐文件核对CPU adaptor和 `ai.h`；
2. 把本轮两份模型库安装到带operator/case/mode身份的目录；
3. 以仓库中经过验证的OH_AI Sample/API结构作为代码模板；
4. 运行 `chips/ws63/scripts/prepare_sample.py`，使用同一Host输入生成多输入/多输出安全的
   独立板端Sample；缺输入、dtype或大小不符必须硬失败；
5. Sample调用一次 `OH_AI_ModelPredict()`并打印每个完整Tensor和shape；
6. 调用 `chips/ws63/scripts/integrate_sdk.py`按固定规则安装adaptor、`ai.h`、带
   operator/case/mode身份的模型库，并接入CMake、Kconfig、target和模型库选择；
7. 读取脚本receipt，并在调用 `hs-dev-build`/`fbb build`的同一进程导入
   `ws63_board_env.ps1|sh`；必须使用脚本生成的 `invoke_hs_dev_build.ps1|sh`或
   等价地先source再build，确认 `SDK_INTEGRATION_GATE=PASS`；只“读取”环境文件不算执行；
8. 运行 `chips/ws63/scripts/verify_wiring.py`检查每条定义点/消费点，输出
   `BOARD_WIRING_GATE=PASS`。

在`FIRMWARE_BUILD_ENV`运行`integrate_sdk.py`并采用对应的PowerShell或Shell包装器。若
Micro库或 Sample 来自另一环境，复制后分别按 `micro_build_receipt.json` 和该文件清单复核
SHA-256 再接入 SDK。

不能凭经验自由写另一套API路线，也不能只写一句“完成接线”。

## step4：委托构建并核对固件身份

完整workflow中，本skill对当前矩阵行在step3结束时输出构建handoff并暂停；顶层调用
`hs-dev-build`后，必须带同一case/mode的receipt和新鲜固件恢复step4。不得把
step0-3在烧录后另起一轮重复执行。

若由顶层workflow编排，本skill把step3产物和target交回workflow，由workflow调用
`hs-dev-build`执行真实target的clean build；若用户只调用本 Skill，则输出同样的结构化
handoff，等待顶层/调用者返回构建证据，不自行加载或改写build Skill规则。本skill负责
确认构建输入就是step3冻结的Sample和模型库。必须同时得到：

```text
FIRMWARE_BUILD=PASS
firmware=<fresh absolute *_all.fwpkg>
target=<fbb target>
```

构建进程还必须回显并核对 `AI_CUSTOM_SAMPLE_DIR`和`AI_MCU_MODEL_VARIANT`与receipt一致；
缺任一变量时，即使`fbb build`退出0也判定接线FAIL。

随后必须运行 `chips/ws63/scripts/verify_firmware.py`，机械检查Sample `.c.obj`、map中的模型
Predict/Execute/目标Kernel及 `_all.fwpkg`相对本轮Sample、两份库和配置的新鲜度。只有
`FIRMWARE_CONTENT_GATE=PASS`才能进入烧录；`fbb build`退出0但缺该门禁仍是FAIL。
退出码0但Sample未编入固件仍是FAIL。

`verify-prepared-firmware`模式可以跳过step2-4的写入和构建动作，但必须从已有证据恢复
同样的SDK、case、模型库、Sample对象、符号和fwpkg身份；缺一项都不能猜测。
