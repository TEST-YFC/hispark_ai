# 编译与工具链

> 当前职责：本文由 `hs-workflow-op-development` 的推理 Stage3 读取。
> `hs-dev-op-implement` 算子实现专项 Skill 只生成或修复源码并执行实现门禁，不直接启动构建。这里的
> MindSpore Lite 工具包构建也不同于 `hs-dev-build` 的 fbb 固件构建，二者不能互相替代。

实现完成后，推理 workflow 在 Stage3 调用 `scripts/build_mslite.sh` 编译 MindSpore Lite。
本文说明推理 profile 的工具链、受控构建、产物校验和故障分诊。训练 workflow 使用同一脚本的
`--profile training`；训练开关和验收条件以 `hs-workflow-train-op-development` 为准。

## 构建身份与源码冻结

构建根仓的新鲜度指纹包括 HEAD、Git 状态、变更内容和未跟踪源码。对直接依赖的子模块，只记录当前
HEAD。上游构建会在子模块中应用受管补丁，Windows 换行转换也可能使整个仓库显示 dirty，因此不把
子模块 worktree 变化直接判为本轮源码漂移。直接子模块的 commit 变化仍会使指纹失效。更深层的测试或
模型仓库只通过父仓的 index/gitlink 身份体现，避免递归读取无关的大型仓库。

wrapper 在构建前后锁定已检出的子模块 SHA。当前上游 `build.sh` 不读取
`HISPARK_SKIP_SUBMODULE_UPDATE`，因此该环境变量不能证明远程更新已禁用。受控构建期间不得编辑
构建根仓源码；子模块 HEAD 漂移时，不得接受该产物。修复源码或环境后，使用新的 `RUN_ID` 启动构建。

## 何时全量、何时增量

编译耗时较长，开始前告知用户。日常使用增量参数 `-i`。`build.sh` 会重新运行 CMake，使用
`file(GLOB)` 的目录能够发现新增的 `.c/.cc` 文件。若链接器报告新增符号 undefined，先读取失败
目标的 CMakeLists，确认是否使用显式源列表。显式列表需要加入新文件；反复全量构建不能解决遗漏。

仅在工具链或环境变量变化、`build/` 损坏、CMake 缓存疑似污染时，去掉 `-i` 做全量构建。
RISC-V 交叉库由独立的 `ExternalProject` 构建，增量构建不会重新扫描它。新增 `nnacl_c` 文件未进入
`build/riscv/build/nnacl/libnnacl.a` 时，只删除 `build/riscv` 后重新配置，不删除整个构建目录。

| 编译类型 | 命令 | 典型耗时 |
|---|---|---|
| 增量（日常开发） | `bash build.sh -I x86_64 -i`（并发由构建脚本按 CPU 和内存估算） | 约10分钟 |
| 全量（环境或CMake结构变化） | `bash build.sh -I x86_64`（并发由构建脚本按 CPU 和内存估算） | 约30分钟 |

构建根目录是代码根目录（含 `schema/`、`tools/`、`src/litert/`）的上一级，必须含有
`build.sh` 和 `output/`。HiSpark.AI 集成仓库中的典型构建根是 `src/mindspore-lite/`。

## 推理 profile 的环境变量

以下配置仅适用于 `--profile inference`；它保留推理流程的 `MSLITE_ENABLE_TRAIN=OFF`，不能用于训练工作流。

```bash
export MSLITE_ENABLE_MICRO=ON
export MSLITE_ENABLE_INT8=ON
export MSLITE_ENABLE_TRAIN=OFF
export MSLITE_ENABLE_TESTCASES=OFF
export MSLITE_TARGET_RISCV=ON
export HISPARK_RISCV_TOOLCHAIN_PATH=<BiSheng RISC-V工具链根目录>
```

`MSLITE_TARGET_RISCV=ON`通过 MindSpore Lite 当前的 `nnacl_riscv` ExternalProject 生成
`build/riscv/build/nnacl/libnnacl.a`，并安装到工具包的 `tools/codegen/lib/riscv/`。
当前源码没有 `nnacl_arm/build/arm` ExternalProject，因此不把不适用的 ARM 路径设为成功门禁。
找不到 RISC-V 工具链时，停止构建并要求补齐环境；不能关闭 RISC-V 构建后用 x86-only 产物宣布完成。

工具链检查以真实二进制为准：

```bash
test -x "$HISPARK_RISCV_TOOLCHAIN_PATH/bin/clang"
"$HISPARK_RISCV_TOOLCHAIN_PATH/bin/clang" --version | grep -qi bisheng
```

## 启动并持续等待构建

标准入口带有并发锁、环境检查、工具链探测、交叉库断言、产物解压和构建身份记录：

```bash
OP_BUILD_RUN_ID="op-$(date +%Y%m%d%H%M%S)-$$"
nohup bash <skill>/scripts/build_mslite.sh \
  --run-id "$OP_BUILD_RUN_ID" <构建根目录> >/dev/null 2>&1 &
bash <skill>/scripts/build_mslite.sh --wait 540 "$OP_BUILD_RUN_ID"
```

`--wait`返回10表示同一轮构建仍在运行。继续使用同一 `RUN_ID` 等待；返回0或1后，立即向用户通知
SUCCESS或FAILED。`--status "$RUN_ID"`只用于即时查看，不能代替终态等待。后台任务仍为RUNNING时，
不能结束当前任务、关闭监控窗口或提交最终答复。不要使用 `wait $BUILD_PID`，因为每次工具调用都在新的 shell 中，
构建进程不是该 shell 的子进程。

`STALE_BUILD_RECORD`、`NO_CURRENT_BUILD` 和 `INCOMPLETE_BUILD_RECORD` 表示当前没有可确认的本轮结论，
不代表源码构建失败。按输出提示恢复环境，并使用新 `RUN_ID`；不能把其他运行的日志或 RC 当作本轮结论。

## 成功产物与验证入口

脚本构建成功后，还要确认以下条件：

- `build/riscv/build/nnacl/libnnacl.a`存在；
- 最新 `output/mindspore-lite-*-linux-x64.tar.gz` 或 `output/mindspore-enterprise-lite-*-linux-x64.tar.gz` 存在；
- 工具包已解压到同名目录，且包含 `tools/converter/converter/converter_lite`；
- 解压目录中的 `converter_lite`和RISC-V codegen库可读；
- 本次修改涉及的parser注册符号已经进入产物。

`hs-verify-op-host`的 `MSLITE_PKG`必须指向解压目录，不能指向原始 `build/`或 tar.gz。
解压包提供所需的头文件、共享库、converter 和 codegen 资源；直接使用 `build/`会缺少头文件或共享库。

完成后运行：

```bash
python3 <skill>/scripts/check_build_freshness.py \
  --code-root <MindSpore-Lite代码根> \
  --mslite-pkg "$MSLITE_PKG"
```

只有构建终态为 SUCCESS、交叉库和工具包门禁通过，且`BUILD_FRESHNESS=PASS`时，才把新鲜的
`MSLITE_PKG`交回 workflow，并进入 `hs-verify-op-host`。`--status` 和 `--wait` 的成功输出还必须包含
`BUILD_PROFILE`、`RESOLVED_MSLITE_ENABLE_TRAIN` 和 `TRAIN_PACKAGE_ARTIFACTS`。对于 training profile，
新鲜解压包必须包含非空的 `libmindspore-lite-train.so` 和 `.a`，才能通过产物检查。

## 失败分诊

- parser、kernel、opcoder、注册或本次源码编译错误：转交 `hs-dev-op-implement`。
- RISC-V ExternalProject 失败：检查 `build/riscv/src/*-stamp/*-build-*.log` 及工具链身份。
- 新文件符号 undefined：检查失败 target 的显式源列表或 GLOB 范围。
- 子模块 SHA 漂移：恢复到构建前记录的 SHA，不得使用漂移后的产物。
- tar.gz存在但解压包陈旧：重新执行受控构建和解压，不放宽新鲜度门禁。

修复后必须重新执行质量门禁并启动新构建；本reference不越过workflow宣布Host验证完成。
