# 编译与工具链

> 当前职责：本文由 `hs-workflow-op-development` 的 MindSpore Lite 工具包构建阶段读取。
> `hs-dev-op-implement` leaf 只生成/修复源码和执行实现门禁，不直接启动构建。这里的 MSLite 构建也不同于
> `hs-dev-build` 的 fbb 固件构建，二者不能互相替代。

实现完成后由 `hs-workflow-op-development` stage2 调用 `scripts/build_mslite.sh` 编译 mindspore-lite；本文只解释该脚本背后的工具链、产物校验和故障分诊，不是 leaf 实现阶段的额外流程。

## 何时全量、何时增量

编译较慢。开始前告知用户并在后台运行，保持终端可用。**日常一律用增量 `-i`，新增文件通常也不例外**——`build.sh` 每次都重跑 cmake，`file(GLOB)` 收集的目录会重新扫到新 `.c/.cc`。**但若链接报"新文件的符号 undefined"，这不是"该全量了"的信号**：先从日志提取符号名与失败 target（`build_mslite.sh --status` 的链接专项），读该 target 的 CMakeLists 确认源收集方式——显式源列表必须手动把新文件加进去，详见 `<hs-dev-op-implement>/references/troubleshooting.md` 链接条目；逐级删缓存/全量重建碰运气定位不了问题。**仅这些情况去掉 `-i` 全量：** 工具链/环境变量变更、`build/` 损坏、CMake 缓存疑似污染。

> 特例：RISC-V 交叉库由独立 `ExternalProject`（`mindspore-lite/CMakeLists.txt`）构建，增量不重扫它。新加的 `nnacl_c` 文件若没进 `build/riscv/build/nnacl/libnnacl.a`，删 `build/riscv`（不是整个 `build/`）重配。

> 后台编译判断完成：启动时生成并保存唯一 `RUN_ID`，首选 `build_mslite.sh --wait 540 "$RUN_ID"`（Bash 工具 timeout 设 600000；到时返回 10 就带同一 ID 再等），`--status "$RUN_ID"` 仅作即时查看。**禁止 `wait $BUILD_PID`**——每次工具调用是新 shell，构建进程不是其子进程。`STALE_BUILD_RECORD`、`NO_CURRENT_BUILD` 和 `INCOMPLETE_BUILD_RECORD` 都不是构建失败，必须开启新 run，不能读历史日志阻断流程。

| 编译类型 | 命令 | 典型耗时 |
|---|---|---|
| 增量（日常开发） | `bash build.sh -I x86_64 -j12 -i` | ~10 分钟 |
| 全量（环境/CMake 结构变更后） | `bash build.sh -I x86_64 -j12` | ~30 分钟 |

> 构建脚本与产物在**构建根目录**——代码根目录（含 `schema/`、`tools/`、`src/litert/`）的**上一级**，含 `build.sh`、`output/`。下面命令在构建根目录执行。（HiSpark.AI 集成仓库中是 `src/mindspore-lite/`。）

## 环境变量（必须显式设置，开关固定照抄）

```bash
# 在构建根目录执行：启用 Micro / INT8 / RISC-V，关闭训练与测试用例
export MSLITE_ENABLE_MICRO=ON
export MSLITE_ENABLE_INT8=ON
export MSLITE_ENABLE_TRAIN=OFF
export MSLITE_ENABLE_TESTCASES=OFF
export MSLITE_TARGET_RISCV=ON
# 工具链根目录——按本机实际路径填（RISC-V 需 bin/clang/clang++；ARM 需 bin/arm-v01c01-linux-musleabi-gcc/g++）
export HISPARK_RISCV_TOOLCHAIN_PATH=<BiSheng RISC-V 工具链根目录>
export HISPARK_ARM_TOOLCHAIN_PATH=<ARM musl GCC 工具链根目录>
```

**RISC-V 和 ARM 库是必须产物：** hs-verify-op-host 的 `riscv_fp32`/`riscv_quant` 路径依赖 `MSLITE_TARGET_RISCV=ON` 交叉编译出的 `build/riscv/build/nnacl/libnnacl.a` 和 `build/arm/build/nnacl/libnnacl.a`。**找不到工具链必须停下问用户，禁止去掉 `MSLITE_TARGET_RISCV` 退化成 x86-only 后宣布完成**——那等于没验证。

## 工具链定位（两家都需；分别用 `--version | grep` 识别，不依赖版本标志）

```bash
# RISC-V：--version 含 bisheng
if [ -x "$HISPARK_RISCV_TOOLCHAIN_PATH/bin/clang" ] && \
   "$HISPARK_RISCV_TOOLCHAIN_PATH/bin/clang" --version 2>&1 | grep -qi bisheng; then
  echo "RISC-V OK: $HISPARK_RISCV_TOOLCHAIN_PATH"
else
  found=$(find "$HOME" /opt /usr/local /data -maxdepth 6 -name clang 2>/dev/null \
    | while read -r c; do [ -f "$c" ] && "$c" --version 2>&1 | grep -qi bisheng && echo "$c" && break; done)
  if [ -n "$found" ]; then
    export HISPARK_RISCV_TOOLCHAIN_PATH="$(dirname "$(dirname "$found")")"
    echo "located RISC-V: $HISPARK_RISCV_TOOLCHAIN_PATH"
  else
    echo "未找到 BiSheng RISC-V 工具链，请设置 HISPARK_RISCV_TOOLCHAIN_PATH"
    exit 1
  fi
fi

# ARM：--version 含 musl
if [ -x "$HISPARK_ARM_TOOLCHAIN_PATH/bin/arm-v01c01-linux-musleabi-gcc" ] && \
   "$HISPARK_ARM_TOOLCHAIN_PATH/bin/arm-v01c01-linux-musleabi-gcc" --version 2>&1 | grep -qi musl; then
  echo "ARM OK: $HISPARK_ARM_TOOLCHAIN_PATH"
else
  found=$(find "$HOME" /opt /usr/local /data -maxdepth 6 -name "arm-v01c01-linux-musleabi-gcc" 2>/dev/null \
    | while read -r c; do [ -f "$c" ] && "$c" --version 2>&1 | grep -qi musl && echo "$c" && break; done)
  if [ -n "$found" ]; then
    export HISPARK_ARM_TOOLCHAIN_PATH="$(dirname "$(dirname "$found")")"
    echo "located ARM: $HISPARK_ARM_TOOLCHAIN_PATH"
  else
    echo "未找到 ARM musl GCC 工具链，请设置 HISPARK_ARM_TOOLCHAIN_PATH"
    exit 1
  fi
fi
```

## 后台编译并保持终端可用

标准入口（`build_mslite.sh` 自带并发锁、env、工具链探测、交叉库断言与产物解压）：

```bash
OP_BUILD_RUN_ID="op-$(date +%Y%m%d%H%M%S)-$$"
nohup bash <skill>/scripts/build_mslite.sh --run-id "$OP_BUILD_RUN_ID" <构建根目录> >/dev/null 2>&1 &
bash <skill>/scripts/build_mslite.sh --wait 540 "$OP_BUILD_RUN_ID"
```

编译运行期间可草拟端到端测试或 review diff（**不许改源码**）。`--wait` 结束即给出 SUCCESS/FAILED 摘要；交叉库缺失（`build/riscv|arm/build/nnacl/libnnacl.a`）脚本会以 exit 4 报出——那是 ExternalProject 静默失败（多半工具链问题），查 `build/*/src/*-stamp/*-build-*.log`。

## 解压产物（验证用的就是这个解压包，不是 build/）

成功后：converter 在 `output/mindspore-lite-<version>-linux-x64/tools/converter/converter/converter_lite`，交叉库在 `build/riscv/build/nnacl/` 和 `build/arm/build/nnacl/`。解压新产物（在构建根目录）：

```bash
cd output && rm -rf mindspore-lite-2.8.0-linux-x64 && tar xzf mindspore-lite-2.8.0-linux-x64.tar.gz
```

> **hs-verify-op-host 的 `MSLITE_PKG` 必须指向这个解压目录 `output/mindspore-lite-<ver>-linux-x64/`，不是原始 `build/`。** 解压包自带 `include/c_api/`、`runtime/include/` 与就位的共享库；直接用 `build/` 会缺头文件、`.so` 分散，导致 `error while loading shared libraries` / `c_api/model_c.h: No such file`，白白浪费时间手动 `ln`。

编译成功后把新鲜 `MSLITE_PKG` 交回 `hs-workflow-op-development`，由 workflow 调用 `hs-verify-op-host`。本 reference 不直接调用其他 skill，也不越过 workflow 宣布验证完成。
