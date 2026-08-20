---
name: hs-workflow-mslite-env-setup
description: 本 skill 适用于用户请求"编译 MindSpore Lite"、"build mslite"、"转换 ONNX 模型"、"运行模型转换"、"构建静态库"、"编译 micro_gen"、"配置 mslite环境"、"配置HiSpark_ai环境"，或希望执行从源码编译到静态库生成的完整 MindSpore Lite 工作流的场景。
---

# MindSpore Lite 工作流 Skill

本 skill 自动化完成 MindSpore Lite 的完整工作流：源码编译、ONNX 模型转换，以及面向 HiSpark.AI 嵌入式 AI 应用的 RISC-V 静态库生成。

## 前置条件

运行任何工作流步骤前，请确认环境依赖已满足：

- Ubuntu 22.04、GCC 11.3+、CMake 3.22+、Python 3.11
- PyYAML 6.0+、NumPy 1.19.3+
- 毕昇（BiSheng）LLVM 15.0.4 RISC-V 工具链（x86_64 主机）—— 需从[华为开发者官网](https://developers.hisilicon.com/cn/developerTool)手动下载 `BiSheng-llvm-15.0.4-riscv-x86-linux`，详见 `references/faq.md`「获取毕昇编译器」
- ARM musl GCC 工具链 `gcc-10.3-arm-musl-x86-linux`（x86_64 主机）—— 同样需手动下载，详见 `references/faq.md`「获取 ARM GCC 工具链」
- mindspore-lite 子模块已初始化
- `python` 与 `python3` 命令均指向 Python 3.11

完整的依赖清单请见 `references/dependency_checklist.md`，遇到问题时请见 `references/faq.md`。

## 工作流概览

四步流水线：

```
第 1 步：配置环境  →  第 2 步：编译 MSLite  →  第 3 步：转换模型  →  第 4 步：构建静态库
```

每一步在 `scripts/` 下都有对应的脚本。要执行完整流水线，按顺序依次运行各脚本即可。

## 第 1 步：设置环境变量

为 MindSpore Lite 编译设置所有必需的环境变量：

```bash
source scripts/setup_env.sh
```

该脚本导出以下变量：
- `MSLITE_ENABLE_MICRO=ON`、`MSLITE_ENABLE_INT8=ON`、`MSLITE_TARGET_RISCV=ON`
- `MSLITE_ENABLE_TRAIN=OFF`、`MSLITE_ENABLE_TESTCASES=OFF`
- `HISPARK_RISCV_TOOLCHAIN_PATH` —— 毕昇 RISC-V 编译器根路径
- `HISPARK_ARM_TOOLCHAIN_PATH` —— ARM musl GCC 工具链根路径

脚本还会在尚不存在时为毕昇编译器创建符号链接（`clang` → `riscv32-linux-musl-gcc`），并分别实测 RISC-V 与 ARM 两条交叉编译器是否可用。

## 第 2 步：编译 MindSpore Lite

以 RISC-V 为目标编译 MindSpore Lite 框架：

```bash
source scripts/setup_env.sh && bash scripts/build_mslite.sh
```

编译产物为 `src/mindspore-lite/output/` 下的 `mindspore-lite-2.8.0-linux-x64.tar.gz`。脚本通过 `CMAKE_ARGS` 传入 `-DPython3_EXECUTABLE`，解决 Python 3.11 路径问题。

构建参数：
- 目标平台：x86_64 主机，RISC-V 交叉编译
- 并行任务数：按 CPU 核心数自动检测
- 输出日志：`/tmp/mslite_build.log`

## 第 3 步：转换 ONNX 模型

使用 `converter_lite` 将 ONNX 模型转换为 Micro C 代码：

```bash
source scripts/setup_env.sh && bash scripts/convert_model.sh <onnx_模型路径> <输出目录>
```

以 LeNet-5 为例：

```bash
bash scripts/convert_model.sh \
  src/samples/oh/lenet5/model/mnist-12.onnx \
  src/samples/oh/lenet5/output/micro_gen
```

该脚本会：
1. 若 `micro_config.cfg` 不存在则创建
2. 从本轮`MSLITE_PKG`自动定位`libmindspore_converter.so`，过滤其他MSLite包的旧路径，
   并在启动converter的同一进程中设置PATH与LD_LIBRARY_PATH；不依赖前一个shell的export，
   不修改`.bashrc`或系统`ldconfig`
3. 在相同动态库环境中运行`converter_lite --help`；支持`--encryption`时显式传
   `--encryption=false`，不支持时省略，help失败时按环境问题停止
4. 以 NCHW 格式运行 `converter_lite`
5. 通过 `CONVERT RESULT SUCCESS` 校验输出

出现`libmindspore_converter.so: cannot open shared object file`时，脚本会先自动修复当前
命令的动态库环境并继续。只有本轮工具包内确实找不到该库、包身份冲突或需要重建/重新下载
工具包时才把探测证据和建议方案交给用户确认；这不是算子实现失败。

## 第 4 步：构建静态库

将生成的 Micro C 代码编译为 RISC-V 静态库：

```bash
source scripts/setup_env.sh && bash scripts/build_static_lib.sh <micro_gen 目录>
```

示例：

```bash
bash scripts/build_static_lib.sh src/samples/oh/lenet5/output/micro_gen
```

该脚本会：
1. 修改 `CMakeLists.txt`，为 RISC-V 交叉编译添加 `--sysroot`
2. 修改 `allocator.h`，包含 `<stdatomic.h>` 以兼容 Clang
3. 以正确的 RISC-V 工具链与 sysroot 路径运行 cmake
4. 以并行任务数运行 make
5. 校验已产出 `libnet.a` 与 `libmicro_runtime.a`

## 已知问题与修复

以下常见问题由自动化脚本自动处理。如需手动介入，请见 `references/faq.md`：

| 问题 | 脚本中的自动修复 |
|-------|-------------------|
| CMake 找到 Python 3.10 而非 3.11 | 第 2 步：通过 `CMAKE_ARGS` 指定 Python 路径 |
| 缺少 `riscv32-linux-musl-gcc` | 第 1 步：建立 `clang` → `gcc` 符号链接 |
| 交叉编译时误用主机 glibc 头文件 | 第 4 步：为 CMake 添加 `--sysroot` |
| Clang 下 `atomic_bool` 未定义 | 第 4 步：在 allocator.h 中加入 `<stdatomic.h>` |
| 非交互式 shell 未加载 `.bashrc` 环境变量 | 所有脚本显式 `source setup_env.sh` |

## 配置

skill 脚本会从项目根目录自动发现路径。如需覆盖默认值，可在运行前设置以下变量：

| 变量 | 默认值 | 用途 |
|----------|---------|---------|
| `HISPARK_AI_ROOT` | 脚本的父目录 | 项目根目录 |
| `BISHENG_ROOT` | `$HISPARK_AI_ROOT/BiSheng-llvm-binary-release-musl` | 毕昇 RISC-V 编译器 |
| `ARM_TOOLCHAIN_ROOT` | `/opt/linux/x86-arm/arm-v01c01-linux-musleabi-gcc` 或项目树内 `gcc-10.3-arm-musl-*/arm-v01c01-linux-musleabi-gcc` | ARM musl GCC 工具链 |
| `MSLITE_PKG` | `$HISPARK_AI_ROOT/src/mindspore-lite/output/mindspore-lite-2.8.0-linux-x64` | MSLite 发布包 |

## 参考文件

- **`references/faq.md`** —— 完整 FAQ，覆盖环境配置、编译、模型转换与静态库构建过程中遇到的全部 12 个问题
- **`references/dependency_checklist.md`** —— 分步骤的环境依赖校验指南
