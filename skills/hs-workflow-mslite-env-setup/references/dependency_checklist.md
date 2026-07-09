# 环境依赖检查清单

## 一键检查命令

```bash
echo "=== OS ===" && cat /etc/os-release | grep -E "^(NAME|VERSION)="
echo "=== GCC ===" && gcc --version | head -1
echo "=== CMake ===" && cmake --version | head -1
echo "=== Python ===" && python --version
echo "=== pip ===" && python -m pip --version 2>&1
echo "=== PyYAML ===" && python -c "import yaml; print('PyYAML', yaml.__version__)" 2>&1
echo "=== NumPy ===" && python -c "import numpy; print('NumPy', numpy.__version__)" 2>&1
echo "=== 毕昇编译器 ===" && file $HISPARK_RISCV_TOOLCHAIN_PATH/bin/clang-15 2>&1
echo "=== mindspore-lite ===" && ls src/mindspore-lite/build.sh 2>&1
echo "=== adaptor ===" && ls src/adaptor/ 2>&1
```

## 版本要求

| 依赖 | 要求 | 检查命令 |
|------|------|---------|
| Ubuntu | 22.04 | `cat /etc/os-release` |
| GCC | 11.3.0 ~ 12.3.0 | `gcc --version` |
| CMake | 3.22.2+ | `cmake --version` |
| Python | 3.11 | `python --version` |
| PyYAML | 6.0+ | `python -c "import yaml; print(yaml.__version__)"` |
| NumPy | 1.19.3+ | `python -c "import numpy; print(numpy.__version__)"` |
| 毕昇编译器 | 15.0.4 x86_64 | `file <bisheng>/bin/clang-15` |
| mindspore-lite | 子模块 | `ls src/mindspore-lite/build.sh` |
| adaptor | 源码目录 | `ls src/adaptor/` |

## 环境变量要求

```bash
export MSLITE_ENABLE_MICRO=ON
export MSLITE_ENABLE_INT8=ON
export MSLITE_ENABLE_TRAIN=OFF
export MSLITE_ENABLE_TESTCASES=OFF
export MSLITE_TARGET_RISCV=ON
export HISPARK_RISCV_TOOLCHAIN_PATH=<bisheng_root>
```
