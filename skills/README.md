# HiSpark.AI Skills

本目录存放 HiSpark.AI 项目专用的 **AI Agent Skills**。每个子目录是一个独立的 skill，遵循 `SKILL.md` 约定（YAML frontmatter `name` / `description` + 正文），可被 Claude Code 等 agent 按语义自动匹配触发，或通过 `/<skill-name>` 显式调用，用于将项目特定的算子开发/验证流程沉淀为可复用、可检视的工作规范。

## Skills 一览

子目录命名遵循 `hs-<阶段/角色>-<对象>` 约定，`hs` 即 HiSpark，前缀同时指示该 skill 在算子交付生命周期中的阶段。

| 目录 | 阶段 | 状态 | 用途 | 典型触发 |
| ---- | ---- | ---- | ---- | ---- |
| `hs-design-op-manual` | 设计 | 规划中 | 编写算子设计手册与设计文档 | "设计算子"、"算子设计文档" |
| `hs-dev-op-implement` | 开发 | 已落地 | 新增/移植 MindSpore Lite 算子：分析、ONNX/TFLite 算子支持、INT8 量化、代码生成、MCU 部署、parser/kernel/opcoder | "新增算子"、"add operator"、"implement op"、"port operator" |
| `hs-dev-op-performance` | 开发 | 规划中 | 算子性能评估、基准对比与调优 | "算子性能"、"benchmark"、"性能调优" |
| `hs-verify-op` | 验证 | 已落地 | 算子精度验证工程搭建：ONNX/TFLite、x86 与 RISC-V、fp32 与 INT8 端到端 | "验证算子"、"test operator"、"算子验证"、"精度调试" |
| `hs-debug-op-board-accuracy` | 部署 | 已落地 | 固件自动烧录到 WS63/Hi3863 板端：CH340G 串口检测、Burntool 烧录、启动验证 | "烧录固件"、"flash firmware"、"部署到板子"、"burn to board" |
| `hs-workflow-mslite-env-setup` | 工作流 | 规划中 | MindSpore Lite 工具链与编译环境搭建流程 | "搭建环境"、"环境配置"、"build env" |

> "规划中" 表示该 skill 目录暂为占位（仅含 `.gitkeep`），内容待补充。

## 目录约定

单个 skill 子目录的典型结构：

```
hs-<phase>-<topic>/
├── SKILL.md          # skill 入口：frontmatter（name/description）+ 流程正文
├── scripts/          # 配套脚本（机械门禁、校验、用例生成等，CI 可直接调用）
├── references/       # 参考文档（判定准则、复用决策、编码规范等）
├── tests/            # 脚本测试
└── .gitkeep          # 仅当目录暂无其它文件时用于占位（git 不追踪空目录）
```

约定：

- **入口唯一**：每个 skill 必须有且仅有一个 `SKILL.md`，其 `description` 决定 agent 的触发匹配，应列出中英文关键短语。
- **脚本只做机械判据**：`scripts/` 下的门禁脚本（如 `gate_artifacts.py`、`validate_op_spec.py`）只检查机械不变量，语义判定保留在 `SKILL.md`。
- **`.gitkeep` 占位**：git 只追踪文件、不追踪空目录；保留空目录时用 `.gitkeep` 占位，待放入实质内容后可删除。
- **Python 产物不入库**：`__pycache__/`、`*.pyc`、`.pytest_cache/` 不应提交（见仓库 `.gitignore`）。

## 加载机制

- **运行时加载位置**：agent（Claude Code）从 `.claude/skills/` 加载 skill。本目录（仓库根 `skills/`）是**项目纳管的 skill 源库**，用于评审、版本管理与规划；已落地的 skill 需同步至 `.claude/skills/` 才会被 agent 识别。
- 目前 `hs-dev-op-implement`、`hs-verify-op`、`hs-debug-op-board-accuracy` 为已落地 skill；其余三个为规划占位。

## 新增 skill

1. 新建 `hs-<phase>-<topic>/` 目录，按上面的命名约定选取阶段前缀。
2. 编写 `SKILL.md`（frontmatter + 流程正文），建议借助通用 skill `skill-creator` 起草。
3. 按需补充 `scripts/`、`references/`、`tests/`；空目录放 `.gitkeep`。
4. 同步到 `.claude/skills/` 并在本地验证触发与门禁。
