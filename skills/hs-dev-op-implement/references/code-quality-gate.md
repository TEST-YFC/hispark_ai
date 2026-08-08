# 算子实现 Code Style 与安全门禁

## 适用范围

本门禁检查本次新增或修改的 C/C++、CMake 和注册接线。规范源是 HiSpark.AI 仓库的 `docs/zh-CN/software/code-style.md`；如果调用环境没有该文件，以本页的冻结摘要为最低要求，并报告缺失的规范源。

门禁执行两次：`hs-dev-op-implement` 交付源码前执行一次，`hs-workflow-op-development` 构建前再执行一次。不要另建独立门禁 skill，避免只靠触发概率决定质量检查是否发生。

## 执行顺序

1. 列出本次修改文件，并把每个文件映射到 capability、注册点或构建接线。
2. 对修改的 C/C++ 文件使用代码根的 `.clang-format`；先检查 diff，再决定是否 `-i`，避免格式化无关代码。
3. 运行 `git diff --check` 和 `quick_check.sh`。
4. 按下表人工审计无法可靠机械判断的规则。
5. 输出 PASS/FAIL 表；任何高风险项未确认时门禁为 FAIL。

## 格式与可维护性

- 注释与内容间保留一个空格，注释放在对应代码上方或右侧；新增代码使用项目接受的 `/* ... */` 风格。
- 新文件包含正确版权头；新增代码不得含 TODO、TBD 或 FIXME。
- 函数左大括号独占一行；条件和循环左大括号跟随语句；所有 if/for/while/do-while 使用大括号。
- 一行一条语句，常规行不超过 120 字符；二元操作符、逗号和关键字空格符合规范；不连续堆叠空行。
- 函数尽量不超过 50 个非空非注释行、5 个参数和 4 层嵌套；超过时必须给出不能拆分的工程理由。
- 不修改输入对象的指针参数使用 const；数组参数同时传入长度；外部接口指针在解引用前判空。
- 头文件有 include guard，无循环依赖和无用 include；不要在 `extern "C"` 块内 include 头文件。
- 变量使用前初始化，缩小作用域，不在子作用域复用同名变量；资源释放后句柄立即置为无效值。

## 内存、整数和控制流安全

- 外部索引必须检查 `index >= size`；禁止变长数组。
- 分配前校验大小与乘加溢出，分配后判空；复制长度来自外部时先验证；释放后不得访问。
- 所有除法检查除零；移位量必须非负且小于位宽；避免有符号溢出、无符号回绕、符号转换和截断。
- 对象大小使用 `size_t`；枚举值保持唯一。
- 循环有可证明的退出条件，不用浮点数计数，不在循环体修改控制变量。
- switch 不允许隐式 fall-through；确需下沉时写明确注释并保证 default 分支安全。
- 字符串空间包含终止符，写入后保证 null 结尾。
- 处理所有有意义的返回值；禁止在库代码调用 `exit`、`abort`、`atexit`、`pthread_exit`、`kill`、`realloc` 或 `alloca`。
- 非测试代码不使用 `assert()` 代替错误处理。

## 外部输入与危险 API

- format 参数不能由外部数据控制。
- 外部输入不能未经校验拼接到进程启动、动态库加载、路径或 shell 命令中。
- 使用项目安全函数库的 `memcpy_s`、`memmove_s`、`memset_s`、`strcpy_s`、`snprintf_s` 等。发现 `memcpy`、`memmove`、`memset`、`strcpy`、`sprintf`、`snprintf` 等规范禁止的不安全 API 时，默认 `CODE_STYLE_GATE=FAIL`。确有项目级兼容约束时，只有用户或项目维护者给出显式 waiver 才可继续；waiver 必须单列范围、理由和风险，且不能把该项记为普通 PASS。
- 不把密钥、token、私有 URL、账号、用户数据或内部流转编号写进源码、日志、测试向量和文档。

## 算子专项门禁

- infer、runtime kernel、nnacl 函数和 OpCoder 的 rank 上限使用同一常量；infer 显式拒绝超界，所有定长 shape 数组填充前有边界守卫。
- Parameter 首字段、注册键、PrimitiveType 和 parser 返回类型在七层一致。
- 新增 `KernelBase` 时 Prepare/Resize/Compute/Release vtable 完整，所有 Init/Resize/Prepare 返回值向上传播。
- INT8 路径逐输入传递并使用 scale/zero-point；输出 qparams 不同时不能做字节拷贝。
- OpCoder 只发数据和 nnacl 函数调用，不内联复制算法；`Collect()` 包含生成代码实际引用的全部头和源。
- 防止重复注册或平行 kernel 劫持既有路径；新增源文件已接入正确构建 target。

## 建议命令

```bash
git -C <code_root> diff --check
bash <skill_root>/scripts/quick_check.sh <code_root>
clang-format --dry-run --Werror --style=file <changed C/C++ files>
```

旧版 clang-format 不支持 `--dry-run --Werror` 时，使用临时副本格式化后比较，禁止为检查而覆盖用户无关修改。

## 输出格式

```text
CODE_STYLE_GATE=<PASS|FAIL>
SECURITY_GATE=<PASS|FAIL>
QUICK_CHECK=<PASS|FAIL>
DIFF_AUDIT=<PASS|FAIL>
```

四项均 PASS 才能由实现 skill 输出 `IMPLEMENT_GATE=PASS`。
