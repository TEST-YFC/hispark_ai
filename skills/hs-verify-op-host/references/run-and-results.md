# Host run and results

目录：

- [运行](#运行)
- [读取结果](#读取结果汇报只认这些)

以下内容从入口按需下沉，harness 的执行、等待和结果来源不变。

## 运行

**填好三个变量后整块复制执行**（`--spec` 传绝对路径——harness 以 spec 所在项目目录为锚写报告与 `output/`，与当前目录无关）:

```bash
PROJ=$MSLITE_OP_OUTPUT/<op>                         # 算子目录；MSLITE_OP_OUTPUT 缺省与 mindspore-lite 仓平级(HiSpark.AI 仓内即 src/mslite-op-output)
export MSLITE_PKG=<构建产物解压目录>         # .../output/mindspore-lite-<ver>-linux-x64（不是 build/）
SKILL=<hs-verify-op-host 的绝对 skill 根路径>

test -x "$MSLITE_PKG/tools/converter/converter/converter_lite" \
  && python "$SKILL/scripts/run_all_cases.py" --spec "$PROJ/scripts/op_spec.py"
```

- `--framework {onnx,tflite,all}`(默认 all):每个框架用自己的 `*_TEST_CASES` 跑一轮、单独出一份 Excel。
- `--target {x86,riscv,all}`(默认 all):每框架内选目标路径,决定表里出现哪些余弦列。
- harness按所选框架惰性安装依赖：ONNX路径安装`onnx`和`onnxruntime`，TFLite路径安装
  `tensorflow`，报告安装`openpyxl`，基础数值处理安装`numpy`。优先清华源、失败后尝试默认源；
  安装到当前虚拟环境或当前用户范围，并在同一解释器中重新import验证。Agent看到缺包日志后
  必须等待自动修复结果并继续，不能把第一次`ModuleNotFoundError`直接当成最终结论。

### 长任务执行与崩溃检测(harness 单轮 10+ 分钟)

harness 串行跑「生成→转换→编译→推理」,单轮 10+ 分钟。**后台启动 + `wait_verify.sh` 阻塞等待**——
禁止自拼 `sleep N && tail` 盲等（sleep >110s 会被 Bash 工具默认 120s 超时杀掉,exit 143 是 sleep
被杀不是验证结果;实证多次算错）:

```bash
RUN_ID="host-$(date +%Y%m%d%H%M%S)-$$"
nohup python "$SKILL/scripts/run_all_cases.py" --run-id "$RUN_ID" --spec "$PROJ/scripts/op_spec.py" \
    > "/tmp/op_verify_${RUN_ID}.log" 2>&1 & echo $! > "/tmp/op_verify_${RUN_ID}.pid"
# 一条命令内部轮询到结束或到时（Bash 工具 timeout 设 (max_secs+60)*1000 毫秒,如 540 配 600000）:
bash "$SKILL/scripts/wait_verify.sh" "/tmp/op_verify_${RUN_ID}.log" 540 \
    "$(cat /tmp/op_verify_${RUN_ID}.pid)" "$RUN_ID"
# 退出码: 0=已出 VERDICT(贴出末尾,照抄) / 1=进程退出无 VERDICT(闸门拦截或崩溃,读贴出的日志)
#        / 10=还在跑(再跑一次 wait_verify.sh 接着等)
```

- **崩溃/卡死由 harness 自己兜底,无需人肉盯进程。** 每条路径有超时上限(默认 1200s,环境变量 `OP_VERIFY_PATH_TIMEOUT` 秒可调),超时即**连同 `converter_lite` 子进程整组 kill**,不再无限等。converter 因堆损坏 abort(SIGABRT)、段错误、或日志出现 `malloc/sysmalloc/encounter an unknown error` 时,harness 把该路径判 FAIL 并在结论里写明原因(如 `converter crashed: SIGABRT — abort / heap corruption`、`TIMEOUT — converter hung`)。
- 这类 crash 几乎都是**算子量化通路的空指针/越界（implement 实现侧 bug）**,不是验证流程问题——照结论给的路径去查 `stderr.log` 与生成代码，并交 workflow 回流算子实现专项 Skill。
- 某路径**确实只是慢**(大 4D + 量化)被超时误杀时,调高 `OP_VERIFY_PATH_TIMEOUT` 重跑,而不是降覆盖或放宽阈值。

## 读取结果(汇报只认这些)

- **VERDICT**:harness 末尾打印 `VERDICT: op=... N/M variant-cases PASS, K FAIL ...` 一行,并写入项目根
  `verify_summary.txt`。**这是唯一可信的结论来源,向用户汇报时照抄它与退出码**。
- **退出码只认 VERDICT 后紧跟的 `HARNESS_EXIT=N` 行**(0=全 PASS,非 0=有 FAIL;同步写入日志与
  summary)——nohup 后台模式下进程退出码不可观测,这一行就是为此而设。**禁止自行 `grep -c FAIL`
  之类计数判定**:VERDICT 的 "0 FAIL" 字样也会被计入,全绿会被误判成失败(实证踩过)。
- **整体通过分母**：计划 variant 数 = 全部激活 framework 的 case 数 × 全部激活 path 数。
  只有 `expected=executed=passed>0`、能力清单无未覆盖项且 `HARNESS_EXIT=0` 才是 Host 通过；单条、
  抽样或部分用例 PASS 只能报告为局部结果。
- **报告**(每框架一份):`<op>_<framework>_test_results.xlsx`(写在你运行 harness 的项目目录下)。
  一行一个用例;列 = 用例编号 / 描述 / 测试点 / `PARAM_COLUMNS` / 各 active 路径余弦 / 结果 / 备注。
  “测试点”原样读取 case 的 `test_point`，必须明确该行验证的行为、边界或缺陷类型。
  所有已运行路径达各自阈值才整行 PASS(绿),否则 FAIL(红);末尾汇总行给总计/通过/失败与判据。
- **板端期望分母**:`board_expected_matrix.json`。harness从本轮实际执行的
  `riscv_fp32/riscv_int8`行自动生成，每行冻结`framework/case_id/mode/test_point/model/input_dir/gt_dir`
  和Host状态。完整workflow必须使用`--target all`；Board不得手工重写该文件或只挑代表case。
- **现场**(`output/<framework>/tc<id>/`，按类型分类，类型下再分三路径):
  ```
  tc<id>/
  ├── model/                 # 共享: ONNX/TFLite 模型 (build 一次, 三路径复用)
  ├── input/                 # 共享: input*.bin + riscv_int8 的 calib_<i>/ 副本
  ├── gt/                    # 共享: onnxruntime/tf.lite 参考输出 (.npy, 供审计)
  ├── convert/               # 三路径的转换+构建树并排
  │   ├── x86_fp32/          #   *_micro (driver CWD, 含 net*.c)
  │   ├── riscv_fp32/
  │   └── riscv_int8/        #   (+ micro_riscv_quant.cfg)
  └── output/                # 三路径的运行产物并排
      ├── x86_fp32/          #   _run.sh / _driver.sh / stdout.log / stderr.log / output.npy / judge.txt
      ├── riscv_fp32/
      └── riscv_int8/
  ```
  `output/<framework>/` 在每轮开跑时被 harness 清空——现场只属于本轮,不存在上轮残留,无需(也不要)手动 `rm -rf` 后再跑。每个 `output/<path>/_run.sh` 都是可从任意 cwd 执行的单路径复现入口:它会在对应 `convert/<path>` 下重跑转换/编译/benchmark,覆盖写回本路径的 `stdout.log`/`stderr.log`,再调用同一 Python 判定入口刷新 `output*.npy` 与 `judge.txt`。`gt/output*.npy` 是稳定参考,不会被 `_run.sh` 改写。`INT8_NOT_GENUINE` 闸门 grep 的是 `convert/riscv_int8/**/net*.c`。
- 入口在任一路径未达阈值或无法运行时**非零退出**。

判定:x86/riscv fp32 余弦 ≥ 0.999;riscv INT8 ≥ 0.99(量化有损,故更宽)。
