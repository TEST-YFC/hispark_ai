# 固件环境准备与专项 Skill 分流

## 目录

- [环境准备分流](#环境准备分流不修改外部环境-skill)
- [安装地址与回退](#专项-skill-安装地址)
- [可用性门禁](#环境准备-skill-的可用性门禁)

> 只有用户请求固件编译、烧录或板测时读取。算子源码、MindSpore Lite 构建和 Host-only 请求不加载本文件。
> 本文件保留环境准备的完整步骤；入口只负责选择是否进入该分支。

### 环境准备分流（不修改外部环境 Skill）

`hs-dev-env-prep` 是外部维护的环境准备专项 Skill；它的默认行为可能同时安装
`fbb CLI`、构建工具链并下载芯片 SDK。算子工作流不得仅因为它存在就直接调用，必须先按
用户意图和已提供路径分流：

**优先级约定：** 默认 `AUTO_ALL` 必须先由用户在 Stage0 提供
`FIRMWARE_SDK_ROOT` 绝对路径；没有路径时停在 Stage0，不自动下载或从磁盘挑选 SDK。
获取一份新的 SDK 属于独立的环境准备请求，不在本次算子工作流内隐式执行；完成后以得到的
具体路径重新初始化本工作流。一次总确认通过后，agent 可自动为这份已提供的 SDK 补齐工具链，
不再发起额外确认。

| 用户情况 | 工作流动作 | 是否允许调用 `hs-dev-env-prep` |
|---|---|---|
| 只想安装或检查 `fbb CLI` | 只执行 `uv`/`fbb CLI` 安装与 `fbb --version` 检查，然后结束环境准备 | 不调用 |
| 已明确提供 SDK 源码路径，且要编译/上板 | 设置 `FBB_SDK_DIR=<用户路径>`，核对 `src/build.py`、`CMakeLists.txt`、芯片描述和 `fbb describe --json`；确认后只补齐构建环境和工具链 | 自动调用时必须传入已有 SDK，禁止下载另一份 SDK |
| 没有 SDK，且明确要求编译/上板 | 停在 Stage0，要求用户提供 SDK 绝对路径；需要下载时先单独完成环境准备请求，再以实际路径开始新 run | 不在本算子 run 内调用 |
| 只做算子源码、MindSpore Lite 构建或 Host 验证 | 不检查或下载固件 SDK；只使用对应阶段自己的依赖 | 不调用 |

一次总确认同时覆盖对已提供 SDK 补齐工具链的授权；Stage6 只读取该确认和冻结的状态，
不再发起工具链安装询问。若环境准备 Skill 或工具链不可用，直接记录 `BLOCKED` 及恢复命令，
等待用户补齐外部条件后用同一 `RUN_ID` 恢复。

任何环境准备调用前，都必须在状态中记录：用户意图、用户提供的
`FIRMWARE_SDK_ROOT`、SDK 来源为 `USER_PROVIDED`、以及调用返回的 `fbb describe --json`。
不得把 `fbb sdk install <chip>` 当作默认补救动作；若没有 SDK 路径，就把板端阶段写为
`BLOCKED` 和恢复条件，不在后续阶段再次请求确认。

### 专项 Skill 安装地址

`hs-dev-env-prep`、`hs-dev-build` 和 `hs-dev-flash` 使用同一个 Skill 发布目录。当前使用者
缺少其中任意一个时，提示从以下地址安装对应的完整子目录：

```text
https://gitcode.com/HiSpark/hibot-skills/tree/master/skills
```

期望的文件分别是：

```text
<skill-root>/hs-dev-env-prep/SKILL.md
<skill-root>/hs-dev-build/SKILL.md
<skill-root>/hs-dev-flash/SKILL.md
```

安装后必须重新检查当前使用者的 `<skill-root>`，并保留各 Skill 的 `references/`、
`scripts/` 等配套资源；不能只下载一个 `SKILL.md` 作为已安装判据。

### 环境准备 Skill 的可用性门禁

该门禁针对每一位使用者自己的 Codex/Skill 环境在 stage0 执行。通知发生在该使用者
发起本次算子工作流的当前对话中，而不是串口、WSL 后台任务或开发板上。分发本 workflow
不会自动分发外部 `hs-dev-env-prep`；每位使用者需要在自己的 Skill 集合中安装它，或在
已有 `fbb CLI` 环境满足检查时直接使用 CLI/构建专项 Skill。

1. 若用户只要求 CLI、算子源码、MindSpore Lite 工具包构建或 Host 验证，输出
   `ENV_PREP_SKILL=NOT_REQUIRED`，不检查也不要求加载 `hs-dev-env-prep`。
2. 若用户要求固件编译/烧录，先执行 `fbb --version` 和 `fbb describe --json`，并核对用户给出的
   `FIRMWARE_SDK_ROOT`以及SDK全局/目标芯片的`min_cli_version`。命令成功且CLI版本满足要求时，输出 `ENV_PREP_SKILL=NOT_REQUIRED`，直接进入
   `hs-dev-build`/`hs-dev-flash`；“已安装并可用的 fbb CLI 环境”已经满足其前置条件。
3. 若固件阶段需要补环境，尝试加载用户提供或已安装的
   `hs-dev-env-prep/SKILL.md`。加载不到时，必须立即在该使用者当前会话报告：

   ```text
   ENV_PREP_SKILL=UNAVAILABLE
   BOARD_STAGE=BLOCKED
   请先安装 hs-dev-env-prep：
   https://gitcode.com/HiSpark/hibot-skills/tree/master/skills
   期望文件：<skill-root>/hs-dev-env-prep/SKILL.md
   ```

   此时不得假装环境已准备好、不得启动后台 `fbb build`/`fbb flash`，也不得自行下载一份
   外部 Skill；将安装路径和恢复命令写入状态。用户安装或提供该 Skill 后，从 stage0 重新检查；
   不需要重做已通过的 Host 阶段。
4. 若 `hs-dev-env-prep` 可加载且用户已经给出 SDK 路径，确认通过后自动调用，并明确“只补环境和
   工具链，使用该 SDK，禁止执行 `fbb sdk install`”。如果该 Skill 不能遵守已有 SDK 约束，
   记录 `BOARD_STAGE=BLOCKED`，等待外部条件修复，不在 Stage1 之后发起新确认。

检查 `hs-dev-build` 和 `hs-dev-flash` 是否已安装：

- 已安装：stage6、stage7 分别调用它们。
- 未安装：先告知用户从与 `hs-dev-env-prep` 相同的地址安装：
  `https://gitcode.com/HiSpark/hibot-skills/tree/master/skills`。
  该目录包含 `hs-dev-env-prep`、`hs-dev-build` 和 `hs-dev-flash`；安装后应重新检查
  当前使用者自己的 `<skill-root>`，不得只复制 `SKILL.md`；必须保留该 Skill 目录下对应的
  `references/` 和 `scripts/` 子目录及其中脚本。
- 用户未安装或当前环境不能加载：workflow 可按两者公开契约直接使用 CLI 回退，构建用
  `fbb --version`、`fbb describe --json` 或 `fbb list-targets --json` 取得真实 target，
  再执行 `fbb build --clean <target>`；烧录用 `fbb flash <target> --json-summary`，只按最后一行
  JSON 的 `success` 和 `error.code` 判定。回退不降低 clean build、target 解析或 JSON 判定要求。
  `fbb describe`/target 查询失败时阻塞固件阶段，不能猜 target；`fbb build` 非零时保留首个真实
  stderr，并按工具链、接线或生成代码分流；`fbb flash` 返回 `success=false` 时不得宣称烧录成功。

缺少对应专项 Skill 且没有可验证的 CLI 回退时，只阻塞对应阶段，不伪造结果。

默认`BOARD_POLICY=AUTO_ALL`在Stage0必须检查用户本次请求或当前会话是否已经明确提供
`FIRMWARE_SDK_ROOT=<固件SDK仓库绝对路径>`。没有时必须向用户询问并停在Stage0，不能通过
`EXECUTION_CONFIRM_GATE`或进入stage1；禁止通过搜索磁盘、其他任务记录、环境变量或fbb自动
选择一个可写SDK。只有用户明确切换为`BOARD_POLICY=HOST_ONLY`时，才可不提供SDK并继续
stage1-stage5，同时将板端阶段记为`NOT_REQUESTED`。用户提供后，记录对应 `FIRMWARE_SDK_SRC`，再检查
对应专项 Skill 是否安装，并执行 `fbb --version` 和 `fbb describe --json`（使用真实 target 时传入
target）。任一命令不可用、路径身份不符或SDK描述失败时，stage6、stage7标为环境阻塞，
并提示用户安装/运行 `hs-dev-env-prep`；不能因为build/flash skill文件存在就假定其隐含
环境已经准备好。
