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

## 源码编译
### 环境依赖
| 软件名称   | 版本 | 作用                                                             |
| ------ | ------  | ------------------------------------------------------------     |
| Ubuntu |   22.04  |编译和运行MindSpore的操作系统                                      |
| GCC    | 11.3.0-12.3.0 |用于编译MindSpore的C++编译器                                  |
| CMake  | 3.22.2及以上	 |编译构建MindSpore的工具                                       |
| Python | 3.11 | MindSpore的使用依赖Python环境                                         |
| PyYAML | 6.0及以上 | MindSpore里的算子编译功能依赖PyYAML模块                           |
| Numpy  | 1.19.3及以上 | MindSpore里的Numpy相关功能依赖Numpy模块                        |

### 从代码仓下载源码
```
git clone https://gitee.com/HiSpark/mindspore-lite.git
```
### 获取毕昇编译器
- 点击[毕昇编译器官方下载链接](https://developers.hisilicon.com/cn/developerTool)并登录华为开发者账号。
- 在资源下载页面，选择 Toolchain 分类下的 Linux 系统版本。
- 查找并下载适用于 RISC-V 架构 的编译器软件包，其名称为：BiSheng-llvm-15.0.4-riscv-aarch64-linux（或最新版本）。
- 下载完成后，使用以下命令解压（请确保命令实际文件名与下载文件一致）。
```
tar -xzvf BiSheng-llvm-15.0.4-riscv-aarch64-linux-25.09.1.tar.gz
```

### 编译MindSpore
进入mindspore-lite目录
```
cd mindspore-lite
```
设置环境变量，/path替换为毕昇编译器解压后对应的目录
```
export MSLITE_ENABLE_MICRO=ON
export MSLITE_ENABLE_INT8=ON
export MSLITE_ENABLE_TRAIN=OFF
export MSLITE_ENABLE_TESTCASES=OFF
export MSLITE_TARGET_RISCV=ON
export HISPARK_RISCV_TOOLCHAIN_PATH=/path/BiSheng-llvm-binary-release-musl/
```
执行编译脚本，可在执行中修改-j{线程数}来修改线程数量
```
bash build.sh -I x86_64 -j32
```

## Sample案例说明
HiSpark.AI提供了一下Sample供开发参考：
| 平台 | 应用 | AI功能 |
| ---- | ---- | ---- |
| ws63 | LeNet-5手写数字图像识别 | MindSpore Lite Micro工具链量化，转换，编译，SDK集成 |
| ws63 | Gru-S音频固定词识别 | MindSpore Lite Micro工具链量化，转换，编译，SDK集成 |

### **HiSpark.AI CPU系列平台介绍**
超轻量的模型部署平台，支持KB级RAM嵌入式设备；使用说明参考XX和XX使用文档。

### **HiSpark.AI NPU系列平台介绍**
待发布。

### **HiSpark.AI 平台Samples使用说明**
- 从官网分别下载SDK源码放置到某一个路径

- 将Hispark_ai开源仓的Adaptor目录拷贝到${SDK_PATH}/middleware/utils下

- CPU平台将对应的静态链接库拷贝到对应的${SDK_PATH}/middleware/utils/ai_mcu/lib目录下，NPU平台将对应的exeom文件传输到对应的/user路径下。
```
cd ${sample_dir}
export SDK_PATH=${sdk_dir}
./build.sh
```
可烧录固件将自动保存到${SDK_PATH}/output/fwpkg目录下。

## 参与贡献

- 参考[社区参与贡献指南](https://gitee.com/HiSpark/docs/blob/master/contribute/%E7%A4%BE%E5%8C%BA%E5%8F%82%E4%B8%8E%E8%B4%A1%E7%8C%AE%E6%8C%87%E5%8D%97.md)