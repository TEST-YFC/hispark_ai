# HiSpark.AI 文档导航

HiSpark.AI 的文档按「**一个统一接口 → 两条工具链 → 两个芯片平台**」组织。选对平台，再按任务找对应工具链的文档即可。

## 架构速览

```
            应用层 —— ai.h 统一接口（OH_AI_*）
                        │
              adaptor 适配层（屏蔽平台差异）
                        │
        ┌───────────────┴───────────────┐
     CPU / WS63                     NPU / 3322（HiDiTing）
     MindSpore Lite                  CANN
     converter_lite + libnnacl       ATC + AMCT + acl
```

- **CPU 平台（WS63）**：MindSpore Lite 工具链，负责模型转换（converter_lite）、RISC-V 算子库、端侧推理/训练。
- **NPU 平台（3322 / HiDiTing）**：CANN 工具链，负责模型编译（ATC）、压缩量化（AMCT）、推理（acl）。
- **统一接口**：上层应用只面向 `ai.h`（`OH_AI_*`）编程，平台差异由 adaptor 适配层屏蔽。

## 文档总览

| 分组 | 文档 | 平台 | 说明 |
|------|------|------|------|
| 入口 / 总览 | [HiSpark.AI 快速入门指南](<zh-CN/software/HiSpark.AI 快速入门指南/HiSpark.AI 快速入门指南.md>) | 双 | 一条龙跑通（WS63 + 3322 各一遍） |
| | [HiSpark Studio AI for VS Code使用指南](<zh-CN/software/HiSpark Studio AI for VS Code使用指南/HiSpark Studio AI for VS Code使用指南.md>) | 双 | IDE 插件界面详解 |
| 统一接口 | [HiSpark.AI API开发指南](<zh-CN/software/HiSpark.AI API开发指南/HiSpark.AI API开发指南.md>) | 双 | `ai.h` / `OH_AI_*` 统一接口 |
| CPU 工具链 | [HiSpark.AI 转换工具使用指南](<zh-CN/software/HiSpark.AI 转换工具使用指南/HiSpark.AI 转换工具 使用指南.md>) | WS63 | converter_lite 模型转换 |
| | [HiSpark.AI CPU算子规格清单](<zh-CN/software/HiSpark.AI CPU算子规格清单/HiSpark.AI CPU算子规格清单.md>) | WS63 | CPU 算子支持列表 |
| NPU 工具链 | [ATC 离线模型编译工具用户指南](<zh-CN/software/ATC离线模型编译工具用户指南/ATC 离线模型编译工具用户指南.md>) | 3322 | 模型编译 → .om |
| | [AMCT 模型压缩工具用户指南](<zh-CN/software/AMCT模型压缩工具用户指南/AMCT 模型压缩工具用户指南.md>) | 3322 | 量化 / 压缩 / 蒸馏 |
| | [Nano AI应用开发指导书](<zh-CN/software/Nano AI应用开发指导书/Nano AI应用开发指导书.md>) | 3322 | 量化（命令行 / 端侧） |
| | [应用开发指南（C&C++）](<zh-CN/software/应用开发指南/应用开发指南（C&C++）.md>) | 3322 | acl 应用开发 + acl API 参考 |
| | [精度调试工具用户指南](<zh-CN/software/精度调试工具用户指南/精度调试工具用户指南.md>) | 3322 | GPU/NPU、NPU/NPU 精度比对 |
| | [模型评估脚本使用指南](<zh-CN/software/模型评估脚本使用指南/模型评估脚本使用指南.md>) | 3322 | onnx 模型评估脚本 |
| 环境 / 部署 | [开发环境安装指南](<zh-CN/software/开发环境安装指南/开发环境安装指南.md>) | 双 | 软件包（.run）安装 / 升级 / 卸载 |
| | [linux环境docker镜像制作参考](<zh-CN/software/linux环境docker镜像制作参考/linux环境docker镜像制作参考.md>) | 双 | Docker 镜像制作（MSLite + CANN 各一套） |
| 支撑 | [术语和缩略语](<zh-CN/software/术语和缩略语/术语和缩略语.md>) | 双 | 术语 / 缩略语表 |
| | [驱动日志说明文档](<zh-CN/software/驱动日志说明文档/驱动日志说明文档.md>) | 双 | 驱动日志分类与排查 |

## 按任务找文档

| 我想…… | 看这篇 |
|--------|--------|
| 快速跑通一个例子 | [快速入门指南](<zh-CN/software/HiSpark.AI 快速入门指南/HiSpark.AI 快速入门指南.md>) |
| 用 IDE 图形界面操作 | [HiSpark Studio AI for VS Code使用指南](<zh-CN/software/HiSpark Studio AI for VS Code使用指南/HiSpark Studio AI for VS Code使用指南.md>) |
| 写代码调统一接口 | [HiSpark.AI API开发指南](<zh-CN/software/HiSpark.AI API开发指南/HiSpark.AI API开发指南.md>) |
| CPU/WS63 转换模型 | [HiSpark.AI 转换工具使用指南](<zh-CN/software/HiSpark.AI 转换工具使用指南/HiSpark.AI 转换工具 使用指南.md>) |
| CPU/WS63 查算子是否支持 | [HiSpark.AI CPU算子规格清单](<zh-CN/software/HiSpark.AI CPU算子规格清单/HiSpark.AI CPU算子规格清单.md>) |
| NPU/3322 量化 / 压缩模型 | [AMCT 模型压缩工具用户指南](<zh-CN/software/AMCT模型压缩工具用户指南/AMCT 模型压缩工具用户指南.md>) / [Nano AI应用开发指导书](<zh-CN/software/Nano AI应用开发指导书/Nano AI应用开发指导书.md>) |
| NPU/3322 编译模型（.om） | [ATC 离线模型编译工具用户指南](<zh-CN/software/ATC离线模型编译工具用户指南/ATC 离线模型编译工具用户指南.md>) |
| NPU/3322 用 acl 开发应用 | [应用开发指南（C&C++）](<zh-CN/software/应用开发指南/应用开发指南（C&C++）.md>) |
| NPU/3322 比对精度 | [精度调试工具用户指南](<zh-CN/software/精度调试工具用户指南/精度调试工具用户指南.md>) |
| NPU/3322 评估模型 | [模型评估脚本使用指南](<zh-CN/software/模型评估脚本使用指南/模型评估脚本使用指南.md>) |
| 装环境（软件包） | [开发环境安装指南](<zh-CN/software/开发环境安装指南/开发环境安装指南.md>) |
| 装环境（Docker 镜像） | [linux环境docker镜像制作参考](<zh-CN/software/linux环境docker镜像制作参考/linux环境docker镜像制作参考.md>) |
| 排查驱动日志 | [驱动日志说明文档](<zh-CN/software/驱动日志说明文档/驱动日志说明文档.md>) |
| 查术语 / 缩略语 | [术语和缩略语](<zh-CN/software/术语和缩略语/术语和缩略语.md>) |

## 推荐阅读路径

- **新用户上手**：快速入门指南 →（按平台）转换工具 / ATC → API开发指南。
- **CPU（WS63）开发**：快速入门指南（WS63 样例运行）→ 转换工具使用指南 → CPU 算子规格清单 → API开发指南。
- **NPU（3322）开发**：快速入门指南（3322 样例运行）→ AMCT 模型压缩 → ATC 模型编译 → 应用开发指南（acl）。
- **NPU 量化专项**：AMCT 模型压缩工具 → Nano AI应用开发指导书 → 精度调试工具用户指南。
