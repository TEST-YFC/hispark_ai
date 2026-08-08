---
name: hs-workflow-op-development
description: >-
  End-to-end workflow for adapting, adding, porting, or supporting a MindSpore Lite Micro operator on HiSpark.AI, from specification and implementation through host tests, documentation, firmware build, optional flash, and board accuracy. This is the default top-level skill for generic requests such as “适配一个算子”, “新增/支持 xxx 算子”, “port/add/implement an operator”, or any request combining operator implementation with verification, build, flash, documentation, or board testing. Do not use it when the user explicitly asks to use a named leaf skill or clearly requests only implementation, only host tests, only documentation, only build, only flash, or only board accuracy.
---

# 算子适配端到端工作流

本 skill 只负责编排和跨阶段状态，不重复实现各 leaf skill 的专业逻辑。

```text
hs-dev-op-implement
        ↓ IMPLEMENT_GATE
MindSpore Lite 工具包构建
        ↓ MSLITE_PKG
hs-verify-op-host
        ↓ HOST_VERIFY_GATE
hs-design-op-manual
        ↓ OP_MANUAL_SYNC
（用户要求且板卡可用）模型接入 → hs-dev-build → hs-dev-flash → hs-verify-op-board
```

## 路由优先级

1. 用户明确点名 skill，或明确说“只做某阶段”时，优先使用对应 leaf，不启动本 workflow。
2. 用户泛化地说“适配/新增/支持/移植一个算子”时，默认启动本 workflow。
3. 用户同时要求实现与测试、文档、构建、烧录或板测时，必须使用本 workflow。
4. `hs-verify-op-host` 与 `hs-verify-op-board` 不合并：前者在 PC/WSL 中做完整规格矩阵和数值正确性；后者在真实板上验证交叉编译、固件接入、运行通路和硬件输出。两者复用同一 host 用例的模型、输入和 GT，但执行环境、失败归属和成本不同。

## 用户可见阶段

```markdown
状态: stage<n> 进行中
待办:
- [ ] stage0 冻结范围、模式和环境
- [ ] stage1 实现算子源码
- [ ] stage2 构建 MindSpore Lite 工具包
- [ ] stage3 生成并运行 Host 测试
- [ ] stage4 生成终版算子文档
- [ ] stage5 可选：接入并构建 WS63 固件
- [ ] stage6 可选：烧录并做板端精度验证
```

未连接板卡或用户未要求板测时，stage5-stage6 标记“未请求/板卡不可用，Host 验证已完成”，不把它们伪装成 PASS，也不阻塞 Host 侧算子交付。

## stage0：冻结范围和环境

记录 source entry、implementation unit 候选、代码根、`MSLITE_OP_OUTPUT`、是否要求文档、是否要求板测、板卡是否连接，以及 leaf skill 可用性。

在修改算子源码前建立环境控制基线：记录 MindSpore Lite 主仓/子模块 HEAD、dirty fingerprint、当前 `MSLITE_PKG` 及 converter 路径；若已有一条与目标算子无关且 `verify_summary.txt` 明确 PASS 的稳定 Host case，先读取其 `output/<path>/_driver.sh` 中冻结的 `MSLITE_PKG`，用 `realpath` 与当前记录的包逐字核对。路径一致时才可执行 `_run.sh`，确认重新转换、编译、运行和 judge 仍 PASS；路径不一致时必须用当前环境变量和该控制 spec 重新调用 Host harness（至少 x86 路径），不能让旧 wrapper/旧 converter 产生 `ENV_BASELINE=PASS`。这一步的作用是把 converter/工具链/子模块故障与后续算子缺陷分开。

没有可复用稳定 case 时记录 `ENV_BASELINE=UNKNOWN reason=no-known-pass-case`，不得伪称环境已验证；后续若多个无关用例在 converter 启动阶段成片失败，先补跑未改动控制用例或重建工具包，不允许直接修改目标算子源码。基线本身失败时记录 `ENV_BASELINE=FAIL` 并停在环境分支，源码保持未修改。

优先保证 PC/WSL 单元/Host 验证可运行。即使没有开发板，也继续 stage1-stage4；不要因烧录不可用而跳过 Host 测试。

检查 `hs-dev-build` 和 `hs-dev-flash` 是否已安装：

- 已安装：stage5/6 分别调用它们。
- 未安装：先告知用户可从 `https://gitcode.com/HiSpark/hibot-skills/tree/master/skills` 安装。
- 用户未安装或当前环境不能加载：workflow 可按两者公开契约直接使用 CLI 回退，构建用 `fbb list-targets --json` / `fbb describe --json` 选 target 后执行 `fbb build --clean <target>`；烧录用 `fbb flash <target> --json-summary`，只按最后一行 JSON 的 `success` 和 `error.code` 判定。回退不降低 clean build、target 解析或 JSON 判定要求。

缺少 leaf skill 且没有可验证的 CLI 回退时，只阻塞对应阶段，不伪造结果。

若用户要求 stage5/6，除检查 leaf 是否安装外还要执行 `fbb --version` 和 `fbb describe --json`（使用真实 target 时传入 target）。任一命令不可用或 SDK 描述失败时，stage5/6 标为环境阻塞，并提示从同一公开 GitCode 源安装/运行 `hs-dev-env-prep`；不能因为 build/flash skill 文件存在就假定其隐含环境已准备好。

## stage1：实现源码

调用 `hs-dev-op-implement`，传递明确的“只实现/修复源码”范围。只有收到每个 implementation unit 的 `IMPLEMENT_GATE=PASS` 才进入 stage2。

实现阶段若发现测试合同信息不足，补的是 capability checklist 和 implementation contract，不越权代写 Host 结果或正式文档。

## stage2：构建 MindSpore Lite 工具包

这一步构建的是 `converter_lite` 和通用算子库，不是 WS63 fwpkg。它与 stage5 的 `hs-dev-build` 不同，不能互相替代。

使用本 workflow 自有的受控构建资源：

```bash
OP_BUILD_RUN_ID="op-$(date +%Y%m%d%H%M%S)-$$"
nohup bash <hs-workflow-op-development>/scripts/build_mslite.sh \
  --run-id "$OP_BUILD_RUN_ID" <build_root> >/dev/null 2>&1 &
bash <hs-workflow-op-development>/scripts/build_mslite.sh --wait 540 "$OP_BUILD_RUN_ID"
python3 <hs-workflow-op-development>/scripts/check_build_freshness.py \
  --code-root <code_root> --mslite-pkg "$MSLITE_PKG"
```

workflow 必须把 `OP_BUILD_RUN_ID` 写入本轮状态并在后续每次 `--wait`/`--status` 原样传回。`NO_CURRENT_BUILD`、`STALE_BUILD_RECORD` 或 `INCOMPLETE_BUILD_RECORD` 都表示没有可用于本轮的构建结论：重新启动新 run，不读取旧日志作 FAIL。用户手工修复环境或源码后继续时，旧源码指纹自动失效，必须生成新 RUN_ID 重建。

构建前由 workflow 重跑 `hs-dev-op-implement/references/code-quality-gate.md`，防止 stage1 之后的修改绕过门禁。构建失败按首个真实错误归属：

- parser/kernel/opcoder/注册或本次源码错误 → 回流 `hs-dev-op-implement`；
- 工具链、包新鲜度、子模块漂移或非本次文件错误 → 保留证据并阻塞，不让 implement 盲改源码；
- 修复后重新执行质量门禁和构建，不复用旧包。

成功证据是新鲜的 `MSLITE_PKG=<absolute path>`。

## stage3：Host 测试优先

调用 `hs-verify-op-host`，让其依据 capability checklist 编写/对账 `op_spec.py`。在其启动固定 harness 前，检查它已对每个 framework 执行 `gate_artifacts.py --stage pre-verify` 和 `validate_op_spec.py`；只有 `ARTIFACT_GATE=PASS` 且 validator 退出 0 才能运行长测试。Host 是默认和必做验收，即使没有板卡也必须完成。

失败分流：

| 证据指向 | 回流所有者 |
|---|---|
| 用例模型、输入、GT、属性、覆盖映射设计错误 | `hs-verify-op-host` |
| parser/infer/kernel/opcoder/quantizer 数值或可达性错误 | `hs-dev-op-implement`，之后重跑 stage2-stage3 |
| MSLITE_PKG 陈旧、工具链或子模块异常 | stage2 环境分支 |

不要把所有 FAIL 都扔给验证 skill，也不要让 implement 修改固定测试执行器来凑绿。只有 VERDICT 全绿、`HARNESS_EXIT=0` 且 capability 覆盖 N=M，才得到 `HOST_VERIFY_GATE=PASS`。

## stage4：生成文档

Host 全绿后调用 `hs-design-op-manual mode=integrated-final terminal_state=completed`，由文档 skill 从冻结事实生成正式 `operator-desc/{op}.md`。阻塞或硬停时调用同一模式但传 `terminal_state=blocked|hard-stop`，只生成/刷新草稿。

文档失败回流文档 skill 或缺失事实的原 owner；不得在 workflow 中另写一套四章节模板。正式交付要求 facts/content/case audit 与 `OP_MANUAL_SYNC` 均 PASS。

## stage5：可选固件接入与构建

只在用户要求板测且板卡/SDK条件可用时执行。选择 stage3 中已 PASS 的代表性用例，复用同一模型、输入和 GT，完成模型静态库、adaptor 和 sample 接线。

随后调用 `hs-dev-build` 生成 fwpkg；它只负责 fbb target 构建。若使用 CLI 回退，先从 `fbb list-targets --json` 或 `fbb describe --json` 获取真实 target，配置变更后强制 clean build。成功证据是新鲜 `*_all.fwpkg`。

构建错误分流：模型/算子生成代码错误回 stage1；sample/adaptor/Kconfig 接线错误留在 stage5；工具链错误按 build skill 处理。

## stage6：可选烧录与板端精度

调用 `hs-dev-flash` 烧录 stage5 的固件，只按 fbb 最后一行 JSON 判断烧录。需要板端精度时可让该 skill 使用其公开的 `fbb flash <target> --then-monitor --until <keyword> --timeout <seconds> --json-summary` 链路保存串口文本；缺 skill 时用相同 CLI 契约回退，不直接调用 BurnTool。

烧录成功不等于板端精度成功。随后调用 `hs-verify-op-board`，传入同轮 Host 用例的 GT、测试输入、串口完整输出和 fp32/INT8 模式，由它输出 `ACCURACY_VERDICT`。

没有连接板卡、串口不可用或用户不在板边时，保留 Host 完成状态并将 stage6 标为未执行；不要反复烧录或用旧串口日志冒充本轮板测。

## 完成判据

Host 交付完成必须满足：

- 每个 implementation unit 的 `IMPLEMENT_GATE=PASS`；
- 新鲜 `MSLITE_PKG` 构建成功；
- `HOST_VERIFY_GATE=PASS`；
- `OP_MANUAL_SYNC=PASS publication=final`。

用户明确要求板测时，另需：

- `hs-dev-build`/CLI 构建成功；
- `hs-dev-flash`/CLI JSON `success=true`；
- `ACCURACY_VERDICT=PASS`。

任一必需门禁 FAIL 时首行写 `状态: 未完成`，列出失败阶段、原始证据和回流 owner。未请求的板测不是 FAIL；已请求但因无板卡未执行则是“Host 完成，板端子任务未执行”，不能写成完整板测完成。

## 统一结案报告

```text
OP_WORKFLOW=<PASS|FAIL|HOST_PASS_BOARD_NOT_RUN>
IMPLEMENT_GATE=<PASS|FAIL>
MSLITE_BUILD=<PASS|FAIL>
HOST_VERIFY_GATE=<PASS|FAIL>
OP_MANUAL_SYNC=<PASS|FAIL>
FIRMWARE_BUILD=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
FLASH_VERDICT=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
ACCURACY_VERDICT=<PASS|FAIL|NOT_REQUESTED|NOT_RUN>
```

报告同时给出源码 diff、`MSLITE_PKG`、Host summary/Excel、正式文档、fwpkg 和板端日志的绝对路径。只报告真实存在且属于本轮的产物。

## 资源索引

| 资源 | 所有者与用途 |
|---|---|
| `scripts/build_mslite.sh` | workflow stage2 的算子源码后工具包重建、RUN_ID 与子模块/注册断言 |
| `scripts/check_build_freshness.py` | workflow stage2 在进入 Host 前核对源码与解压包新鲜度 |
| `references/build-and-toolchain.md` | stage2 工具链、产物和构建失败分诊 |
| `tests/test_build_state.sh` | RUN_ID、源码指纹、陈旧状态和子模块漂移回归 |

这些资源由本 workflow 持有，避免 `hs-dev-op-implement` 托管自己不执行的构建流程。`hs-workflow-mslite-env-setup` 的同名脚本负责通用环境搭建；这里的脚本只服务算子源码修改后的受控重建，调用时必须使用完整 skill 路径区分。
