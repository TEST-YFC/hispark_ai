# 实现失败修复与交接

## 目录

- [根因修复循环](#失败修复与交接)
- [输出要求](#结束时输出)

> 只有发生失败、需要交接或重试时读取；不改变实现阶段的失败归属。

## 失败修复与交接

workflow 返回实现缺陷时，必须持续执行以下根因修复循环：

```text
保存并展示首个真实失败
    ↓
按parser/infer/kernel/opcoder/quantizer/构建接线分类
    ↓
查references/troubleshooting.md与lessons.md
    ↓
从失败case反推数学语义、shape、dtype、地址和量化参数
    ↓
定位最小根因并修复源码
    ↓
重跑质量门禁、workflow stage3重建、stage4同case及回归矩阵
```

每次循环必须保存本轮 `RUN_ID`、首个真实 `stderr` 和归属阶段；创建新的 `RUN_ID`
后才允许重跑，禁止用历史日志或旧产物替代当前结论。每个根因最多重试 **2 次**；第二次仍失败时
必须输出 `FAILED` 和两轮证据并暂停，等待用户明确选择继续攻坚或列为覆盖缺口，不能继续盲试。
实现、模型/spec、工具链和固件接线必须分别交给对应负责人，不能用删除能力或放宽测试掩盖失败。

FP32数值错误不能靠更换输入、删除case、放宽余弦或归咎环境处理；先用小Tensor逐元素
对比参考公式和Kernel中间值。INT8错误先核对scale/zero-point、累加位宽、乘法顺序、
饱和、per-tensor/per-channel和生成代码是否确实调用INT8 Kernel。

出现单次FAIL后不要询问用户“是否继续修复”。完整实现/工作流请求已经授权在既定算子
范围内完成根因分析、最小修复和重跑；只有需要扩展framework/dtype/芯片范围、破坏性
操作或缺少外部授权时才询问。

**同一能力连续2个有证据的方案失败时必须强制停下**：向用户呈报两个方案各自的
根因假设、修改、首错和对算证据，并提供“继续攻坚”或“经裁决列为覆盖缺口”两个
选项，等待用户决定。未经用户裁决不得盲试第三个方案、删除FAIL用例或缩小能力清单；
用户选择缩范围时，Host VERDICT必须保留 `ACK_REDUCED`，并在最终能力清单和文档中
明确该覆盖缺口。

任何“环境问题”“存量局限”“非本次引入”“不支持某形态”“覆盖缺口”等收缩范围的
措辞，必须在同一条消息中先给本轮命令、首错、控制用例或源码证据。没有证据时继续按
算子缺陷处理，不能用措辞提前宣称完成。

结束时输出：

```text
IMPLEMENT_GATE=<PASS|FAIL>
implementation_unit=<name>
source_entries=<list>
changed_files=<list>
CODE_STYLE_SOURCE=<本 Skill 安装目录>/references/code-style.md（运行时必须展开为绝对路径）
CODE_STYLE_SOURCE_SHA256=<sha256>
CODE_STYLE_AUDIT=<PASS|FAIL>
capability_checklist=<absolute path>
opdir=<absolute path>
next_owner=hs-workflow-op-development
```

`IMPLEMENT_GATE=PASS` 只表示源码实现与静态质量门禁通过，不表示构建、host 精度、文档、烧录或板测已经通过。

完成措辞锁：只有真实门禁满足时才能写PASS/完成；缺少任一计划用例、编码前audit、
质量证据或修改文件映射时只能写FAIL/未完成，不能写“基本完成”“代码已就绪”等模糊
完成语义。本 Skill 不因任务耗时、后台运行或用户暂时离开而提前提交最终答复。
