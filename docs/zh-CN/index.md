---
html_theme.sidebar_secondary.remove: true
---

# HiSpark.AI 文档

HiSpark.AI 是海思嵌入式 AI 应用开发解决方案，功能覆盖模型压缩、转换、端侧推理与训练，
并提供统一 AI 开发接口、IDE 插件工具，以及 modelzoo 模型方案库等生态资源。

## 方案组成

| 序号 | 组件 | 说明 |
|---|---|---|
| ① | 统一 API & 适配层（adaptor） | 提供统一面向 CPU 与 NPU 平台的 AI 接口，及对应适配层源码 |
| ② | Samples | 基于统一 AI 接口（ai.h）的应用示例，覆盖 CPU / NPU 平台 |
| ③ | HiSpark Studio AI for VS Code | IDE 插件，图形化覆盖模型编译、量化转换、烧录等操作 |
| ④ | MindSpore-Lite | 面向 CPU 平台，支持推理与端侧训练 |
| ⑤ | CANN | 面向 NPU 平台，昇腾 AI 异构计算架构（ATC、AMCT、ACL） |
| ⑥ | modelzoo | 生态组件，汇聚多类别的 AI 模型样例与开发参考方案 |

## 从哪开始

完整的开发指南按主题组织在 [软件资料](./software/index.md) 中，建议按以下路径阅读：

- **初次使用**：从「快速入门指南」开始，完成环境准备与第一个 AI 应用
- **接口开发**：查阅「API 开发指南」与「CPU 算子规格清单」
- **模型部署**：按平台选择「转换工具使用指南」（CPU）或「ATC / AMCT」（NPU）
- **问题排查**：参考「精度调试工具用户指南」与「驱动日志说明文档」
