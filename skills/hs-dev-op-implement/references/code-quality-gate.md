# 算子实现 Code Style 与安全门禁

## 适用范围

这里的“代码规范”是用来检查算子源码格式、安全性和可维护性的规则清单，不是编译器、SDK、Python
包或用户必须提前安装的环境。规范已经随本 Skill 一起提供在
`references/code-style.md`，使用者不需要另外下载或创建规范文件。

本门禁检查本次新增或修改的 C/C++、CMake 和注册接线。开始修改源码前必须完整读取 Skill 内置的
`references/code-style.md`，记录该文件的绝对路径和 SHA-256，并以它作为团队统一规范源。

`code-quality-gate.md` 是执行流程和算子专项检查，不是第二份代码规范；它不能替代
`references/code-style.md`。必须逐规则记录适用性、证据和结果。

门禁执行两次：`hs-dev-op-implement` 交付源码前执行一次，`hs-workflow-op-development` 构建前再执行一次。两次必须使用同一个规范文件身份；SHA-256变化时重新完整读取并重做逐规则审计。
不要另建独立门禁 skill，避免只靠触发概率决定质量检查是否发生。

## 执行顺序

1. 列出本次修改文件，并把每个文件映射到 capability、注册点或构建接线。
2. 对修改的 C/C++ 文件使用代码根的 `.clang-format`；先检查 diff，再决定是否 `-i`，避免格式化无关代码。
3. 运行 `git diff --check` 和 `quick_check.sh`。
4. 按下表人工审计无法可靠机械判断的规则；按原规范规则编号记录适用性、证据和结果，不能只写笼统结论。
5. 将全部规则ID及`applicability/evidence/status`写入`<opdir>/docs/code-style-audit.md`；缺少任一规则ID、适用项缺证据或任一FAIL时门禁为FAIL。
6. 输出 PASS/FAIL 表；任何高风险项未确认时门禁为 FAIL。

## 格式与可维护性

- 注释与内容间保留一个空格，注释放在对应代码上方或右侧；新增代码使用项目接受的 `/* ... */` 风格。
- 新文件包含正确版权头；新增代码不得含 TODO、TBD 或 FIXME。
- 函数左大括号独占一行；条件和循环左大括号跟随语句；所有 if/for/while/do-while 使用大括号。
- 一行一条语句，常规行不超过 120 字符；二元操作符、逗号和关键字空格符合规范；不连续堆叠空行。
- 函数不超过 50 个非空非注释行、5 个参数和 4 层嵌套。
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
- 必须处理函数返回值；禁止在库代码调用 `exit`、`abort`、`atexit`、`pthread_exit`、`kill`、`realloc` 或 `alloca`。
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

## 编码后结构审查

在 `IMPLEMENT_GATE` 前必须生成 `docs/code-review.md`，并逐项记录：

- 注册键（primitive/target/首输入 dtype/选择字段）与每个分支的实际可达性；
- `int8`、`uint8` 或其他 dtype 注册是否都有对应 Kernel、OpCoder 和测试，是否存在永不执行的分支；
- 量化器的专用列表、通用白名单和 lookup 路径，确认算子没有被放入错误的通用入口；
- 常量折叠、节点消除、重写和 fusion 的触发/不触发两类模型，区分“原算子 Kernel 执行”与“折叠结果正确”；
- 新增/复用代码之间的字段、shape、dtype、qparam 和生成调用接口。
- 规格覆盖矩阵：输入的 dynamic/initializer/optional 组合、广播形态、索引/边界语义、
  折叠/重写路径和支持的 dtype 是否逐项对应独立 case；测试数据生成器是否能表达规格允许的
  标量、单元素、负值和边界值。只列出 builder 参数而没有实际 case、模型节点和运行证据，
  视为 `FIX_REQUIRED`。

编译通过不能替代这项审查。任一注册键、分支、量化归属或折叠语义没有证据，或存在
未处置的 `FIX_REQUIRED`，门禁必须 FAIL。

`docs/code-review.md` 除说明文字外必须含一个可解析的 JSON 对象。五个矩阵字段必须是
非空列表，并使用固定共性字段：`registration_matrix` 使用
`key,dtype,condition,callee,case_id,evidence_location,status`；`branch_reachability` 使用
`branch,case_id,evidence_location,status`；`quantizer_ownership` 使用
`capability,expected_owner,actual_owner,lookup_evidence,model_evidence,evidence_location,status`；
`folding_and_rewrite_cases` 使用 `mode,case_id,expected_node,evidence,evidence_location,status`。
`evidence_location` 必须指向实际源码、生成 `net*.c` 或转换日志的路径与行号，或给出可复现命令。
`mode` 必须覆盖 `blocked` 和 `allowed`，或以 `N/A` 加证据说明不适用；
`semantic_coverage` 使用 `scenario,case_id,expected_behavior,evidence_location,status`，
逐项记录输入形态、广播、索引/边界、折叠/重写和 dtype 场景（不适用时用 N/A 加证据）。门禁因此能机械拦截
空表、未达分支、量化归属漂移、死代码和把重写结果冒充原算子执行等情况；具体算子名称
不写入规则。

## 建议命令

```bash
git -C <code_root> diff --check
bash <skill_root>/scripts/quick_check.sh <code_root>
clang-format --dry-run --Werror --style=file <changed C/C++ files>
```

当前 clang-format 不支持 `--dry-run --Werror` 时，使用临时副本格式化后比较，禁止为检查而覆盖用户无关修改。

## 输出格式

逐规则证据固定写入`<opdir>/docs/code-style-audit.md`。构建前复核必须读取这份文件，核对其中的
规范路径/SHA-256仍与当前规范源一致，并重新检查本轮diff；不能只复用旧的PASS文本。

```text
CODE_STYLE_SOURCE=<本 Skill 安装目录>/references/code-style.md（运行时必须展开为绝对路径）
CODE_STYLE_SOURCE_SHA256=<sha256>
CODE_STYLE_AUDIT=<PASS|FAIL>
CODE_STYLE_GATE=<PASS|FAIL>
SECURITY_GATE=<PASS|FAIL>
QUICK_CHECK=<PASS|FAIL>
DIFF_AUDIT=<PASS|FAIL>
```

`CODE_STYLE_AUDIT`以及后四项均 PASS，才能由实现 skill 输出 `IMPLEMENT_GATE=PASS`。
