# HiSpark AI 开源项目

## 项目介绍 && 资源
HiSaprk AI是海思嵌入式AI应用开发解决方案，提供模型压缩、转换、推理等功能，可以结合社区已开源的WS63 SDK集成，开发AI应用。Sample目前已支持LeNet-5手写数组识别 及 Gru-S固定词语音识别相关应用。软件文档在线化链接：[https://docs.hisilicon.com/repos/hispark_ai/zh-CN/master](https://docs.hisilicon.com/repos/hispark_ai/zh-CN/master)

## SDK目录介绍

| 目录   | 二级目录 | 介绍                                                             |
| ------ | ------  | ------------------------------------------------------------     |
| docs   |         |存放AI工具链使用指南，以及AI应用开发指南等文档，帮助客户快速熟悉HiSpark.AI解决方案 |
| src    | adaptor |AI平台所配套的适配层源码                                            |
| src    | samples |HiSpark.AI提供的Samples，用于指导用户基于基于HiSpark各平台部署AI应用                                                                   |
| src    | mindspore-lite | 基于RISC-V平台的AI推理框架，用于自动生成AI推理模块代码并 提供对应的RISC-V算子库                  |

## 社区版本介绍（外部链接）

## 生态板介绍链接
- **WS63系列单板**:  ws63系列是2.4GHz Wi-Fi 6 星闪多模解决方案，其中ws63E支持2.4GHz的雷达人体活动检测功能，适用于大小家电、电工照明及对人体出没检测有需求的常电类物联网智能场景，项目介绍如下：[WS63项目介绍](https://gitee.com/HiSpark/fbb_ws63)。 

  购买链接请参考WS63项目介绍的**购买渠道**页面。

## Sample案例说明
HiSpark.AI提供了一下Sample供开发参考：
| 平台 | 应用 | AI功能 |
| ---- | ---- | ---- |
| ws63 | LeNet-5手写数字图像识别 | MindSpore Lite Micro工具链量化，转换，编译，SDK集成 |
| ws63 | Gru-S音频固定词识别 | MindSpore Lite Micro工具链量化，转换，编译，SDK集成 |

### **HiSpark.AI CPU系列平台介绍**
超轻量的模型部署平台，支持KB级RAM嵌入式设备；使用说明参考XX和XX使用文档。

### **HiSpark.AI 平台快速入门指南**

- **准备hispark_ai工具链**

- **准备待部署模型与数据**

- **模型编译**

- **准备SDK与Sample**

- **SDK编译**

- **烧录调试**

## 参与贡献

- 参考[社区参与贡献指南](https://gitee.com/HiSpark/docs/blob/master/contribute/%E7%A4%BE%E5%8C%BA%E5%8F%82%E4%B8%8E%E8%B4%A1%E7%8C%AE%E6%8C%87%E5%8D%97.md)