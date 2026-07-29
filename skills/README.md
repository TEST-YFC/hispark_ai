# HiSpark.AI Skills

本目录存放 HiSpark.AI 项目专用的 **AI Agent Skills**。每个子目录是一个独立的 skill，遵循 `SKILL.md` 约定（YAML frontmatter `name` / `description` + 正文），可被 Claude Code 等 agent 按语义自动匹配触发，或通过 `/<skill-name>` 显式调用，用于将项目特定的算子开发/验证流程沉淀为可复用、可检视的工作规范。

## Skills 一览

子目录命名遵循 `hs-<阶段/角色>-<对象>` 约定，`hs` 即 HiSpark，前缀同时指示该 skill 在算子交付生命周期中的阶段。

| 目录 | 阶段 | 状态 | 用途 | 典型触发 |
| ---- | ---- | ---- | ---- | ---- |
| `hs-design-op-manual` | 设计 | 已落地 | 按模板生成或更新单算子规格文档 | "生成算子规格"、"编写算子文档"、"更新算子规格" |
| `hs-dev-op-implement` | 开发 | 已落地 | 新增/移植 MindSpore Lite 算子，覆盖规格分析、ONNX/TFLite parser、kernel/opcoder、INT8 量化、编译与端到端验收 | "新增算子"、"add operator"、"implement op"、"port operator" |
| `hs-dev-op-performance` | 开发 | 规划中 | 算子性能评估、基准对比与调优 | "算子性能"、"benchmark"、"性能调优" |
| `hs-debug-op-host-accuracy` | 调试（主机侧） | 已落地 | 搭建算子精度验证工程，覆盖 ONNX/TFLite、x86 与 RISC-V、FP32 与 INT8 端到端对比 | "验证算子"、"test operator"、"算子验证"、"精度调试" |
| `hs-debug-op-board-accuracy` | 调试（板端） | 已落地 | 构建并烧录 WS63/Hi3863 固件，采集板端输出并与宿主机参考结果进行精度校验 | "板端精度验证"、"烧录固件"、"部署到板子"、"burn to board" |
| `hs-workflow-mslite-env-setup` | 工作流 | 已落地 | 配置并执行 MindSpore Lite 源码编译、ONNX 模型转换与 RISC-V 静态库生成工作流 | "编译 MindSpore Lite"、"配置 MSLite 环境"、"转换 ONNX 模型"、"构建静态库" |

> “规划中”表示该目录尚未提供 `SKILL.md`，目前仅作为占位；“已落地”表示已提供可加载的 `SKILL.md` 及相应流程内容。

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
- 目前 `hs-design-op-manual`、`hs-dev-op-implement`、`hs-debug-op-host-accuracy`、`hs-debug-op-board-accuracy`、`hs-workflow-mslite-env-setup` 为已落地 skill；仅 `hs-dev-op-performance` 为规划占位。

## 新增 skill

1. 新建 `hs-<phase>-<topic>/` 目录，按上面的命名约定选取阶段前缀。
2. 编写 `SKILL.md`（frontmatter + 流程正文），建议借助通用 skill `skill-creator` 起草。
3. 按需补充 `scripts/`、`references/`、`tests/`；空目录放 `.gitkeep`。
4. 同步到 `.claude/skills/` 并在本地验证触发与门禁。
