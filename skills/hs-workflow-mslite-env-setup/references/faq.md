# MindSpore Lite 环境搭建完整 FAQ

> 包含从零搭建环境到静态库编译全过程 12 个问题的解决方案。

## 快速排查清单

1. `python --version` — 是否为 3.11？
2. `python -c "import numpy, yaml"` — NumPy、PyYAML 是否可用？
3. `file <bisheng>/bin/clang-15` — 是否为 x86-64？
4. `echo $HISPARK_RISCV_TOOLCHAIN_PATH` — 环境变量是否已 set？
5. `grep Python3_EXECUTABLE build/CMakeCache.txt` — CMake 是否用了 3.11？
6. `ls <bisheng>/bin/riscv32/riscv32-linux-musl-gcc` — 软链接是否存在？
7. `grep sysroot micro_gen/CMakeLists.txt` — sysroot 是否已配置？
8. `grep stdatomic micro_gen/src/allocator.h` — 头文件补丁是否已打？

## 获取毕昇编译器（BiSheng LLVM RISC-V）

毕昇（BiSheng）LLVM 15.0.4 RISC-V 工具链是 RISC-V 交叉编译的必需依赖，需从华为开发者官网手动下载（外部资源、需登录华为账号，skill 无法自动获取）。来源：项目 README「获取毕昇编译器」。

**下载步骤：**

1. 打开[毕昇编译器官方下载链接](https://developers.hisilicon.com/cn/developerTool)，登录华为开发者账号。
2. 进入资源下载页面，选择 **Toolchain** 分类下的 **Linux** 系统版本。
3. 查找并下载适用于 **RISC-V 架构**的编译器包，名称为 `BiSheng-llvm-15.0.4-riscv-x86-linux`（或最新版本）。
4. 解压（实际文件名以下载为准，日期后缀如 `25.09.1` 会随版本变化）：
   ```bash
   tar -xzvf BiSheng-llvm-15.0.4-riscv-x86-linux-*.tar.gz
   ```

**放置位置（二选一，让 `setup_env.sh` 自动识别）：**

- 解压到项目根 `$HISPARK_AI_ROOT/` 下，目录名以 `BiSheng-llvm-` 开头即可被自动探测（推荐，零配置）。
- 或写入 `~/.hispark_env`：`export BISHENG_ROOT=<解压出的、含 bin/clang 的目录绝对路径>`。

> ⚠️ 务必下载 **x86_64（x86-linux）**版本。误下 aarch64 版本在 x86 主机无法执行（见典型问题速查 #5）。

**验证：** 解压目录下应存在 `bin/clang` 与 `bin/clang-15`；`setup_env.sh` 会实测 `riscv32-linux-musl-gcc` 交叉编译。

## 获取 ARM GCC 工具链（gcc-10.3-arm-musl）

ARM musl GCC 工具链（`arm-v01c01-linux-musleabi` 目标）是 ARM 交叉编译的必需依赖，需从华为开发者官网手动下载（外部资源、需登录华为账号，skill 无法自动获取）。来源：项目 README「获取 GCC 编译器」。

**下载步骤：**

1. 打开[编译器官方下载链接](https://developers.hisilicon.com/cn/developerTool)，登录华为开发者账号。
2. 进入资源下载页面，选择 **Toolchain** 分类下的 **Linux** 系统版本。
3. 查找并下载适用于 **ARM 架构**的 GCC 编译器包，名称为 `gcc-10.3-arm-musl-x86-linux`（或最新版本）。
4. 解压（实际文件名以下载为准，日期后缀如 `26.04.1` 会随版本变化）：
   ```bash
   tar -xzvf gcc-10.3-arm-musl-x86-linux-*.tgz
   ```

> ⚠️ 解压后是**嵌套布局**：`gcc-10.3-arm-musl-x86-linux-<ver>/arm-v01c01-linux-musleabi-gcc/` 才是含 `bin/` 的工具链根。`setup_env.sh` 探测的是这一层（不是最外层目录）。

**放置位置（三选一，让 `setup_env.sh` 自动识别）：**

- **官方安装器（推荐）**：进入解压出的最外层目录，执行 `sudo ./install_gcc_toolchain.sh`，默认装到 `/opt/linux/x86-arm/arm-v01c01-linux-musleabi-gcc/`，并把 `bin/` 写入 `/etc/profile` 的 PATH。
- **项目树内解压**：保留嵌套目录结构放到项目根 `$HISPARK_AI_ROOT/` 下，最外层目录名以 `gcc-10.3-arm-musl-` 开头即可被自动探测（零配置）。
- 或写入 `~/.hispark_env`：`export ARM_TOOLCHAIN_ROOT=<.../arm-v01c01-linux-musleabi-gcc 的绝对路径>`。

> ⚠️ 务必下载 **x86_64（x86-linux）**版本。误下 aarch64 版本在 x86 主机无法执行。

**验证：** 工具链根下应存在 `bin/arm-v01c01-linux-musleabi-gcc` 与 `bin/arm-v01c01-linux-musleabi-g++`；`setup_env.sh` 会实测该 gcc 交叉编译，并导出 `HISPARK_ARM_TOOLCHAIN_PATH`。

## 典型问题速查

| # | 阶段 | 问题 | 解决方案 |
|---|------|------|---------|
| 1 | 依赖 | python 指向 3.10 | 配置 `python`→3.11（可逆，见下文「python 命令配置」） |
| 2 | 依赖 | pip 未安装 | `sudo apt install -y python3-pip` |
| 3 | 依赖 | PyYAML < 6.0 | `python -m pip install --upgrade PyYAML` |
| 4 | 依赖 | NumPy 缺失 | `python -m pip install numpy` |
| 5 | 依赖 | 毕昇 aarch64 无法执行 | 下载 x86_64 版本 |
| 6 | 环境变量 | .bashrc 不生效 | 非交互 Shell 跳过，需每次手动 export |
| 7 | 编译 | CMake 找到 Python 3.10 | `CMAKE_ARGS="-DPython3_EXECUTABLE=/usr/bin/python3.11"` |
| 8 | 编译 | 输出截断退出码 1 | 重定向到日志文件检查 |
| 9 | 静态库 | 缺 gcc/g++ | 软链接 clang → riscv32-linux-musl-gcc |
| 10 | 静态库 | glibc 头文件错误 | CMakeLists 加 --sysroot |
| 11 | 静态库 | atomic_bool 未定义 | allocator.h 加 stdatomic.h |

## python 命令配置（安全做法）

> ⚠️ **切勿**用 `sudo ln -sf /usr/bin/python3.11 /usr/bin/python` 覆盖系统符号链接——Ubuntu 22.04 的 `/usr/bin/python` 可能被系统工具依赖，强制覆盖会破坏系统 Python 环境且难以回滚。

**多数情况无需改系统 `python`**：`setup_env.sh` 已通过 `CMAKE_ARGS="-DPython3_EXECUTABLE=$(command -v python3.11)"` 把 3.11 显式传给 CMake，绕过了对系统 `python` 命令的依赖。

仅当确实需要 `python` 命令指向 3.11 时，二选一（**均可逆**）：

- **系统级（推荐 `update-alternatives`，可管理、可回滚）**：
  ```bash
  sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.11 2
  # 回滚: sudo update-alternatives --remove python /usr/bin/python3.11
  ```

- **用户级（最安全，不碰系统）**：
  ```bash
  mkdir -p ~/.local/bin && ln -sf /usr/bin/python3.11 ~/.local/bin/python
  # 需 ~/.local/bin 位于 PATH 前面（Ubuntu 默认已配置）
  ```
