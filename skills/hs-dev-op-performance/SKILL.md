---
name: hs-dev-op-performance
description: Optimize and benchmark MindSpore Lite Micro operators in HiSpark.AI with reproducible baselines, one-variable changes, Host and WS63 correctness gates, on-device latency measurement, evidence binding, experiment archival, comparison, and reporting. Use for "算子优化", "算子性能", "性能调优", "benchmark an operator", "optimize NNACL", "采 baseline", or comparing generated Micro code and NNACL implementations.
---

# MindSpore Lite Operator Performance

执行 `prepare → baseline → plan approval → one variable → Host gate → board gate → measure → bind → archive → compare`。

## 必读顺序

1. 完整读取 [references/workflow.md](references/workflow.md)。
2. 确定 target；WS63 任务再完整读取 [references/targets/ws63.md](references/targets/ws63.md)。
3. 涉及瓶颈判断、候选优化、cache、数据布局或停止条件时，再读取
   [references/targets/ws63-methodology.md](references/targets/ws63-methodology.md)。
4. 缺少 target runbook 时，只做静态分析和 Host 验证，不宣称 target 性能结果。

## 能力边界

复用当前仓的现有 Skill：

| 阶段 | 使用的 Skill |
|---|---|
| 算子实现、NNACL 修改、package 刷新 | `hs-dev-op-implement` |
| 模型、case、Host 推理与精度 | `hs-debug-op-host-accuracy` |
| MindSpore Lite 环境和构建 | `hs-workflow-mslite-env-setup` |
| firmware、flash、板端精度 | `hs-debug-op-board-accuracy` |
| latency 协议、运行身份、归档和比较 | 本 Skill |

不要复制或修改其他 Skill 的脚本来适配单次实验。

## 脚本入口

- `scripts/run_optimization.py`：准备运行、绑定证据、归档成功/失败轮次及汇总。
- `scripts/build_timed_fwpkg.py`：调用 Board Skill builder，并为本轮固件加入计时 hook。
- `scripts/run_board_flash.py`：调用 Board Skill flash/accuracy，并绑定 execution ID 与 firmware hash。
- `scripts/inject_ws63_timing.py`：给当前仓生成的 `ai_main.c` 注入连续 tick marker。
- `scripts/measure_latency.py`：校验板端精度证明并保存完整稳定样本窗口。

每轮必须从干净、与 baseline 相同的源码 commit 开始。证据通过 run manifest 绑定；CPU/RISC-V
archive、firmware、生成代码和串口原始日志均为必需产物。只从这些产物判定，不手填 PASS、
latency 或 speedup，不删除失败和退化轮次。
