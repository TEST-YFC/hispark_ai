# HiSpark.AI Skills

本目录存放 HiSpark.AI 项目专用的 **AI Agent Skills**。每个子目录是一个独立的 skill，遵循 `SKILL.md` 约定（YAML frontmatter `name` / `description` + 正文），可被支持该约定的 coding agent 按语义匹配触发或显式调用，用于将项目特定的算子开发/验证流程沉淀为可复用、可检视的工作规范。

## Skills 一览

子目录命名遵循 `hs-<阶段/角色>-<对象>` 约定，`hs` 即 HiSpark，前缀同时指示该 skill 在算子交付生命周期中的阶段。

| 目录 | 阶段 | 状态 | 用途 | 典型触发 |
| ---- | ---- | ---- | ---- | ---- |
| `hs-workflow-op-development` | 工作流 | 已落地 | 默认串联算子实现、Host 测试、文档、固件构建、可选烧录与板测 | "适配算子"、"新增算子"、"支持算子"、"port operator" |
| `hs-design-op-manual` | 设计 | 已落地 | 基于冻结事实生成四章节单算子规格限制文档 | "只生成算子文档"、"算子规格文档" |
| `hs-dev-op-implement` | 开发 | 已落地 | 只分析、生成或修复 MindSpore Lite 算子源码并执行实现质量门禁 | "只实现算子"、"使用 hs-dev-op-implement" |
| `hs-dev-op-performance` | 开发 | 规划中 | 算子性能评估、基准对比与调优 | "算子性能"、"benchmark"、"性能调优" |
| `hs-verify-op-host` | 验证 | 已落地 | 设计用例并在 PC/WSL 运行固定测试执行器，验证 ONNX/TFLite、FP32/INT8 与 RISC-V 代码生成路径 | "只写算子测试"、"Host 验证"、"使用 hs-verify-op-host" |
| `hs-verify-op-board` | 验证 | 已落地 | 复用 Host PASS 用例，在已构建和烧录的真实 WS63/Hi3863 上采集 Tensor 并判定板端精度 | "只做板端精度"、"使用 hs-verify-op-board" |
| `hs-workflow-mslite-env-setup` | 工作流 | 已落地 | MindSpore Lite 工具链、模型转换与静态库构建流程 | "搭建环境"、"转换模型"、"构建静态库" |

> "规划中" 表示该 skill 目录暂为占位（仅含 `.gitkeep`），内容待补充。

## 目录约定

单个 skill 子目录的典型结构：

```
hs-<phase>-<topic>/
├── SKILL.md          # skill 入口：frontmatter（name/description）+ 流程正文
├── scripts/          # 配套脚本（机械门禁、校验、用例生成等，CI 可直接调用）
├── references/       # 参考文档（判定准则、复用决策、编码规范等）
├── tests/            # 脚本测试
├── agents/           # 某些 agent 使用的可选 UI 元数据
└── .gitkeep          # 仅当目录暂无其它文件时用于占位（git 不追踪空目录）
```

约定：

- **入口唯一**：每个 skill 必须有且仅有一个 `SKILL.md`，其 `description` 决定 agent 的触发匹配，应列出中英文关键短语。
- **脚本只做机械判据**：`scripts/` 下的门禁脚本（如 `gate_artifacts.py`、`validate_op_spec.py`）只检查机械不变量，语义判定保留在 `SKILL.md`。
- **默认完整工作流、按需使用专项 Skill**：泛化的“适配/新增/支持算子”进入 `hs-workflow-op-development`；用户点名某个专项 Skill 或明确“只做某阶段”时，不启动完整工作流。
- **`.gitkeep` 占位**：git 只追踪文件、不追踪空目录；保留空目录时用 `.gitkeep` 占位，待放入实质内容后可删除。
- **Python 产物不入库**：`__pycache__/`、`*.pyc`、`.pytest_cache/` 不应提交（见仓库 `.gitignore`）。

## 加载机制

- **源库**：仓库根 `skills/` 是项目纳管的 skill 源库，用于评审和版本管理。
- **agent-neutral**：把完整 skill 目录安装到当前 agent 文档规定的 skill 根目录，运行时统一用 `<skill_root>` 表示，不把某个产品的私有目录写进流程。
- 若 agent 支持项目级和个人级两种安装方式，按其公开文档任选一种；仓库内 skill 内容和门禁不得因安装位置而变化。
- 同步必须包含 `scripts/`、`references/`、`tests/` 和 `agents/`，不能只复制 `SKILL.md`。

## 新增 skill

1. 新建 `hs-<phase>-<topic>/` 目录，按上面的命名约定选取阶段前缀。
2. 编写 `SKILL.md`（frontmatter + 流程正文），建议借助通用 skill `skill-creator` 起草。
3. 按需补充 `scripts/`、`references/`、`tests/`；空目录放 `.gitkeep`。
4. 按当前 agent 的公开安装约定同步完整目录，并在本地验证触发与门禁。
