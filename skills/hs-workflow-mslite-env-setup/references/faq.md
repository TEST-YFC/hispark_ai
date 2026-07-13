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
