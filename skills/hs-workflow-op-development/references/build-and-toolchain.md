# 编译与工具链

> 当前职责：本文由 `hs-workflow-op-development` 的 MindSpore Lite 工具包构建阶段读取。
> `hs-dev-op-implement` 算子实现专项 Skill 只生成或修复源码并执行实现门禁，不直接启动构建。这里的
> MindSpore Lite 工具包构建也不同于 `hs-dev-build` 的 fbb 固件构建，二者不能互相替代。

实现完成后，workflow stage3 调用 `scripts/build_mslite.sh` 编译 MindSpore Lite。本文只
解释脚本背后的工具链、受控构建、产物校验和故障分诊。

## 构建身份与源码冻结

构建新鲜度指纹覆盖构建根仓和直接依赖子模块的 HEAD、Git 状态、变更内容与未跟踪源码。
更深层的测试或模型仓库只通过父仓 gitlink/dirty 元数据体现，避免递归读取无关大仓导致
构建启动长时间阻塞。

workflow 设置 `HISPARK_SKIP_SUBMODULE_UPDATE=1`，并在构建前后锁定已检出的子模块 SHA。
受控构建期间不得执行远程 submodule 更新，也不得编辑源码。源码或环境修复后必须使用
新的 `RUN_ID` 启动新构建。

## 何时全量、何时增量

编译较慢，开始前应告知用户。日常使用增量 `-i`；`build.sh` 会重跑 CMake，使用
`file(GLOB)` 的目录能够重新发现新增 `.c/.cc`。若链接报告新增符号 undefined，先读取失败
target 的 CMakeLists，确认是否使用显式源列表；显式列表必须加入新文件，不能靠反复全量
构建碰运气。

仅在工具链或环境变量变化、`build/` 损坏、CMake缓存疑似污染时去掉 `-i` 做全量构建。
RISC-V 交叉库由独立 `ExternalProject` 构建，增量不会重新扫描它；新增 `nnacl_c` 文件未进入
`build/riscv/build/nnacl/libnnacl.a` 时，只删除 `build/riscv` 后重配，不删除整个构建目录。

| 编译类型 | 命令 | 典型耗时 |
|---|---|---|
| 增量（日常开发） | `bash build.sh -I x86_64 -j12 -i` | 约10分钟 |
| 全量（环境或CMake结构变化） | `bash build.sh -I x86_64 -j12` | 约30分钟 |

构建根目录是代码根目录（含 `schema/`、`tools/`、`src/litert/`）的上一级，必须含有
`build.sh` 和 `output/`。HiSpark.AI 集成仓库中的典型构建根是 `src/mindspore-lite/`。

## 必需环境变量

```bash
export MSLITE_ENABLE_MICRO=ON
export MSLITE_ENABLE_INT8=ON
export MSLITE_ENABLE_TRAIN=OFF
export MSLITE_ENABLE_TESTCASES=OFF
export MSLITE_TARGET_RISCV=ON
export HISPARK_RISCV_TOOLCHAIN_PATH=<BiSheng RISC-V工具链根目录>
```

`MSLITE_TARGET_RISCV=ON`通过当前 MindSpore Lite 的 `nnacl_riscv` ExternalProject 生成
`build/riscv/build/nnacl/libnnacl.a`，并把它安装到工具包的 `tools/codegen/lib/riscv/`。
当前源码没有 `nnacl_arm/build/arm` ExternalProject，因此不能把不适用的 ARM 路径设为
成功门禁。找不到RISC-V工具链时必须停止并要求补齐环境，禁止关闭RISC-V构建后用
x86-only产物宣布完成。

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

`--wait`返回10表示同一轮构建仍在运行，必须携带同一 `RUN_ID`继续等待；返回0或1后立即
向用户通知SUCCESS或FAILED。`--status "$RUN_ID"`只用于即时查看，不能代替终态等待。
禁止在后台任务仍为RUNNING时结束当前任务、关闭监控窗口或提交最终答复。也不要使用
`wait $BUILD_PID`，因为每次工具调用位于新的shell，构建进程不是其子进程。

`STALE_BUILD_RECORD`、`NO_CURRENT_BUILD`和`INCOMPLETE_BUILD_RECORD`表示当前没有可签收的
本轮结论，不代表源码构建失败。应按输出提示恢复环境并使用新 `RUN_ID`，不能读取其他运行
的日志或RC作为本轮结论。

## 成功产物与验证入口

脚本构建成功后必须同时确认：

- `build/riscv/build/nnacl/libnnacl.a`存在；
- 最新 `output/mindspore-lite-*-linux-x64.tar.gz`存在；
- 工具包已解压到对应 `output/mindspore-lite-*-linux-x64/`；
- 解压目录中的 `converter_lite`和RISC-V codegen库可读；
- 本次修改涉及的parser注册符号已经进入产物。

`hs-verify-op-host`的 `MSLITE_PKG`必须指向解压目录，而不是原始 `build/`或tar.gz。解压包
提供就位的头文件、共享库、converter和codegen资源，直接使用 `build/`会造成头文件或共享库
缺失。

完成后运行：

```bash
python3 <skill>/scripts/check_build_freshness.py \
  --code-root <MindSpore-Lite代码根> \
  --mslite-pkg "$MSLITE_PKG"
```

只有构建终态SUCCESS、交叉库与工具包门禁通过、`BUILD_FRESHNESS=PASS`时，才把新鲜
`MSLITE_PKG`交回workflow进入 `hs-verify-op-host`。

## 失败分诊

- parser、kernel、opcoder、注册或本次源码编译错误：回流 `hs-dev-op-implement`。
- RISC-V ExternalProject失败：检查 `build/riscv/src/*-stamp/*-build-*.log`及工具链身份。
- 新文件符号undefined：检查失败target的显式源列表或GLOB范围。
- 子模块SHA漂移：恢复到构建前记录的SHA，禁止用漂移后的产物签收。
- tar.gz存在但解压包陈旧：重新执行受控构建和解压，不放宽新鲜度门禁。

修复后必须重新执行质量门禁并启动新构建；本reference不越过workflow宣布Host验证完成。
