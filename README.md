# HiSpark.AI 开源项目

## 项目介绍 && 资源
HiSaprk.AI项目是HiSpark全系列AI解决方案，目前已支持ws63，3322等型号芯片，适用于用户定制化部署AI工程。该HiSpark.AI代码包包含了Mindspore Lite Micro RISC-V工具链 以及 CANN工具链，芯片定制AI适配组件 以及 相应的AI Sample。Sample目前已支持LeNet-5手写数组识别 及 Gru-S固定词语音识别相关应用。软件文档在线化链接：[https://docs.hisilicon.com/repos/hispark_ai/zh-CN/master](https://docs.hisilicon.com/repos/hispark_ai/zh-CN/master)

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

- **3322系列单板**:  3322系列是OpenHarmony Watch应用和表盘解决方案，项目介绍如下：[3322项目介绍](https://xxx)。 

  购买链接请参考3322项目介绍的**购买渠道**页面。

## Sample案例说明
HiSpark.AI提供了一下Sample供开发参考：
| 平台 | 应用 | AI功能 |
| ---- | ---- | ---- |
| ws63 | LeNet-5手写数字图像识别 | MindSpore Lite Micro工具链量化，转换，编译，SDK集成 |
| 3322 | LeNet-5手写数字图像识别 | CANN工具链量化，转换，编译，SDK集成 |
| ws63 | Gru-S音频固定词识别 | MindSpore Lite Micro工具链量化，转换，编译，SDK集成 |
| 3322 | Gru-S音频固定词识别 | CANN工具链量化，转换，编译，SDK集成 |

### **HiSpark.AI CPU系列平台介绍**

MindSpore Lite Micro工具链支持Linx CPU核加速的RISC-V AI工具链。

### **HiSpark.AI NPU系列平台介绍**
CPU平台支持Nano核加速的CANN AI工具链。

### **HiSpark.AI 平台Samples使用说明**
- 从官网分别下载SDK源码放置到某一个路径

- 将HiSpark.AI项目自带的Adaptor目录拷贝到${SDK_PATH}/middleware/utils下

- CPU平台将对应的静态链接库拷贝到对应的${SDK_PATH}/middleware/utils/ai_mcu/lib目录下，NPU平台将对应的exeom文件传输到对应的/user路径下。
```
cd ${sample_dir}
export SDK_PATH=${sdk_dir}
./build.sh
```
可烧录固件将自动保存到${SDK_PATH}/output/fwpkg目录下。

## 参与贡献

- 参考[社区参与贡献指南](https://gitee.com/HiSpark/docs/blob/master/contribute/%E7%A4%BE%E5%8C%BA%E5%8F%82%E4%B8%8E%E8%B4%A1%E7%8C%AE%E6%8C%87%E5%8D%97.md)