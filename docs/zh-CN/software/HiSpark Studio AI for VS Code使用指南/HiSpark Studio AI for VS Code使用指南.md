# 前言<a name="ZH-CN_TOPIC_0000002518029848"></a>

**概述<a name="section4537382116410"></a>**

本文介绍HiSpark Studio AI 插件工具，如何通过该工具进行模型量化、模型转换、模型评估，以及后续应用开发等功能。

**读者对象<a name="section4378592816410"></a>**

本文档主要适用于以下工程师：

-   技术支持工程师
-   AI开发工程师

**符号约定<a name="section133020216410"></a>**

在本文中可能出现下列标志，它们所代表的含义如下。

<a name="table2622507016410"></a>
<table><thead align="left"><tr id="row1530720816410"><th class="cellrowborder" valign="top" width="20.580000000000002%" id="mcps1.1.3.1.1"><p id="p6450074116410"><a name="p6450074116410"></a><a name="p6450074116410"></a><strong id="b2136615816410"><a name="b2136615816410"></a><a name="b2136615816410"></a>符号</strong></p>
</th>
<th class="cellrowborder" valign="top" width="79.42%" id="mcps1.1.3.1.2"><p id="p5435366816410"><a name="p5435366816410"></a><a name="p5435366816410"></a><strong id="b5941558116410"><a name="b5941558116410"></a><a name="b5941558116410"></a>说明</strong></p>
</th>
</tr>
</thead>
<tbody><tr id="row1372280416410"><td class="cellrowborder" valign="top" width="20.580000000000002%" headers="mcps1.1.3.1.1 "><p id="p3734547016410"><a name="p3734547016410"></a><a name="p3734547016410"></a><a name="image2670064316410"></a><a name="image2670064316410"></a><span><img class="" id="image2670064316410" height="25.270000000000003" width="67.83" src="figures/zh-cn_image_0000002549429697.png"></span></p>
</td>
<td class="cellrowborder" valign="top" width="79.42%" headers="mcps1.1.3.1.2 "><p id="p1757432116410"><a name="p1757432116410"></a><a name="p1757432116410"></a>表示如不避免则将会导致死亡或严重伤害的具有高等级风险的危害。</p>
</td>
</tr>
<tr id="row466863216410"><td class="cellrowborder" valign="top" width="20.580000000000002%" headers="mcps1.1.3.1.1 "><p id="p1432579516410"><a name="p1432579516410"></a><a name="p1432579516410"></a><a name="image4895582316410"></a><a name="image4895582316410"></a><span><img class="" id="image4895582316410" height="25.270000000000003" width="67.83" src="figures/zh-cn_image_0000002517869920.png"></span></p>
</td>
<td class="cellrowborder" valign="top" width="79.42%" headers="mcps1.1.3.1.2 "><p id="p959197916410"><a name="p959197916410"></a><a name="p959197916410"></a>表示如不避免则可能导致死亡或严重伤害的具有中等级风险的危害。</p>
</td>
</tr>
<tr id="row123863216410"><td class="cellrowborder" valign="top" width="20.580000000000002%" headers="mcps1.1.3.1.1 "><p id="p1232579516410"><a name="p1232579516410"></a><a name="p1232579516410"></a><a name="image1235582316410"></a><a name="image1235582316410"></a><span><img class="" id="image1235582316410" height="25.270000000000003" width="67.83" src="figures/zh-cn_image_0000002549549695.png"></span></p>
</td>
<td class="cellrowborder" valign="top" width="79.42%" headers="mcps1.1.3.1.2 "><p id="p123197916410"><a name="p123197916410"></a><a name="p123197916410"></a>表示如不避免则可能导致轻微或中度伤害的具有低等级风险的危害。</p>
</td>
</tr>
<tr id="row5786682116410"><td class="cellrowborder" valign="top" width="20.580000000000002%" headers="mcps1.1.3.1.1 "><p id="p2204984716410"><a name="p2204984716410"></a><a name="p2204984716410"></a><a name="image4504446716410"></a><a name="image4504446716410"></a><span><img class="" id="image4504446716410" height="25.270000000000003" width="67.83" src="figures/zh-cn_image_0000002518029850.png"></span></p>
</td>
<td class="cellrowborder" valign="top" width="79.42%" headers="mcps1.1.3.1.2 "><p id="p4388861916410"><a name="p4388861916410"></a><a name="p4388861916410"></a>用于传递设备或环境安全警示信息。如不避免则可能会导致设备损坏、数据丢失、设备性能降低或其它不可预知的结果。</p>
<p id="p1238861916410"><a name="p1238861916410"></a><a name="p1238861916410"></a>“须知”不涉及人身伤害。</p>
</td>
</tr>
<tr id="row2856923116410"><td class="cellrowborder" valign="top" width="20.580000000000002%" headers="mcps1.1.3.1.1 "><p id="p5555360116410"><a name="p5555360116410"></a><a name="p5555360116410"></a><a name="image799324016410"></a><a name="image799324016410"></a><span><img class="" id="image799324016410" height="25.270000000000003" width="67.83" src="figures/zh-cn_image_0000002549429701.png"></span></p>
</td>
<td class="cellrowborder" valign="top" width="79.42%" headers="mcps1.1.3.1.2 "><p id="p4612588116410"><a name="p4612588116410"></a><a name="p4612588116410"></a>对正文中重点信息的补充说明。</p>
<p id="p1232588116410"><a name="p1232588116410"></a><a name="p1232588116410"></a>“说明”不是安全警示信息，不涉及人身、设备及环境伤害信息。</p>
</td>
</tr>
</tbody>
</table>

**修改记录<a name="section2467512116410"></a>**

<a name="table1557726816410"></a>
<table><thead align="left"><tr id="row2942532716410"><th class="cellrowborder" valign="top" width="20.72%" id="mcps1.1.4.1.1"><p id="p3778275416410"><a name="p3778275416410"></a><a name="p3778275416410"></a><strong id="b5687322716410"><a name="b5687322716410"></a><a name="b5687322716410"></a>文档版本</strong></p>
</th>
<th class="cellrowborder" valign="top" width="26.119999999999997%" id="mcps1.1.4.1.2"><p id="p5627845516410"><a name="p5627845516410"></a><a name="p5627845516410"></a><strong id="b5800814916410"><a name="b5800814916410"></a><a name="b5800814916410"></a>发布日期</strong></p>
</th>
<th class="cellrowborder" valign="top" width="53.16%" id="mcps1.1.4.1.3"><p id="p2382284816410"><a name="p2382284816410"></a><a name="p2382284816410"></a><strong id="b3316380216410"><a name="b3316380216410"></a><a name="b3316380216410"></a>修改说明</strong></p>
</th>
</tr>
</thead>
<tbody><tr id="row6889538125617"><td class="cellrowborder" valign="top" width="20.72%" headers="mcps1.1.4.1.1 "><p id="p489043819564"><a name="p489043819564"></a><a name="p489043819564"></a>02</p>
</td>
<td class="cellrowborder" valign="top" width="26.119999999999997%" headers="mcps1.1.4.1.2 "><p id="p28901738175615"><a name="p28901738175615"></a><a name="p28901738175615"></a>2026-04-28</p>
</td>
<td class="cellrowborder" valign="top" width="53.16%" headers="mcps1.1.4.1.3 "><p id="p128901738135612"><a name="p128901738135612"></a><a name="p128901738135612"></a>修改Hi3322的“ <a href="#ZH-CN_TOPIC_0000002515955566">压缩历史显示界面</a> 中”Accuracy字段详细说明。</p>
</td>
</tr>
<tr id="row5947359616410"><td class="cellrowborder" valign="top" width="20.72%" headers="mcps1.1.4.1.1 "><p id="p2149706016410"><a name="p2149706016410"></a><a name="p2149706016410"></a>01</p>
</td>
<td class="cellrowborder" valign="top" width="26.119999999999997%" headers="mcps1.1.4.1.2 "><p id="p648803616410"><a name="p648803616410"></a><a name="p648803616410"></a>2026-03-27</p>
</td>
<td class="cellrowborder" valign="top" width="53.16%" headers="mcps1.1.4.1.3 "><p id="p1946537916410"><a name="p1946537916410"></a><a name="p1946537916410"></a>第一次正式版本发布。</p>
</td>
</tr>
</tbody>
</table>

# HiSpark Studio AI简介<a name="ZH-CN_TOPIC_0000002509724284"></a>

-   **[关于HiSpark Studio AI](#ZH-CN_TOPIC_0000002541284287)**  

-   **[安装方案介绍](#ZH-CN_TOPIC_0000002509764298)**  

-   **[窗口介绍](#ZH-CN_TOPIC_0000002542085605)**  

-   **[关键概念](#ZH-CN_TOPIC_0000002517388100)**  

## 关于HiSpark Studio AI<a name="ZH-CN_TOPIC_0000002541284287"></a>

HiSpark Studio AI是面向开发者提供的超轻量级AI应用开发平台，具备高集成、高专业、高易用等特征，聚焦嵌入式AI应用场景，提供模型压缩、模型转换、应用开发、端侧部署、性能调优的全流程开发平台。

-   高集成
    -   一站式开发平台，支持模型压缩/转换/推理/部署/调试等功能。
    -   统一的IDE界面和API接口，支持CPU/NPU等芯片AI应用开发和部署。

-   高专业
    -   高效的模型压缩，支持ONNX/TFLITE等AI模型。
    -   超轻量的模型部署，支持KB级RAM嵌入式设备。

-   高易用
    -   提供VS Code插件，方便安装和使用。
    -   支持性能/精度可视化分析，方便调试。

-   功能介绍

    HiSpark Studio AI功能架构如[图1](#fig1357355818812)所示。具备核心功能有：

    -   导入ONNX/TFLITE等格式的AI模型，初始化开发环境。
    -   通过集成的NPU/CPU工具链可以进行模型压缩和转换。
    -   导入SDK并参考Sample进行用户AI应用开发。
    -   编译用户AI应用，烧录到嵌入式设备进行部署。
    -   根据串口日志检测性能精度是否达成目标。

    **图 1**  HiSpark Studio AI 功能架构<a name="fig1357355818812"></a>  
    
    ![](figures/zh-cn_image_0000002563755579.png)

## 安装方案介绍<a name="ZH-CN_TOPIC_0000002509764298"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>若之前已经安装过DevEco相关的插件，请手动禁用或者卸载所有与DevEco相关的插件，否则会与HiSpark Studio插件功能冲突。

1.  打开VS Code插件市场。

    ![](figures/33.png)

2.  搜索并安装HiSpark Studio AI。

    ![](figures/zh-cn_image_0000002517339616.png)

    为保证功能正常运行，还需安装HiSpark Studio插件，需安装v26.4.1版本。

    ![](figures/zh-cn_image_0000002548938777.png)

## 窗口介绍<a name="ZH-CN_TOPIC_0000002542085605"></a>

-   **[整体窗口介绍](#ZH-CN_TOPIC_0000002510367162)**  

-   **[侧边栏](#ZH-CN_TOPIC_0000002542087149)**  

-   **[工作区](#ZH-CN_TOPIC_0000002542007157)**  

### 整体窗口介绍<a name="ZH-CN_TOPIC_0000002510367162"></a>

HiSpark Studio AI整体窗口如[图1](#fig141565497718)所示，主要包含两个部分：

1.  侧边栏：HiSpark Studio AI功能导航栏。
2.  工作区：HiSpark Studio AI工作区。

**图 1**  HiSpark Studio AI整体窗口<a name="fig141565497718"></a>  
![](figures/HiSpark-Studio-AI整体窗口.png "HiSpark-Studio-AI整体窗口")

### 侧边栏<a name="ZH-CN_TOPIC_0000002542087149"></a>

侧边栏为功能导航栏，展示了HiSpark Studio AI插件提供的五个主要功能，分别为：

1. Home（主页）：单击进入新建/导入工程，或在已打开工程的情况下进入HiSpark Studio AI模型选择主界面。

2. User Guide（用户指南）：单击在工作区打开用户指南，提供快速入门指南。

3. Connect to Server（连接服务器）：单击连接至服务器。

4. Command Line（命令行工具）：单击在命令行中运行HiSpark Studio AI的量化、转换等功能。

5. Download Toolchain（下载工具链）：单击下载运行HiSpark Studio AI插件所需要的工具链，并自动配置环境。

### 工作区<a name="ZH-CN_TOPIC_0000002542007157"></a>

工作区为插件核心功能展示区域，详细交互逻辑请参见后续章节。

**图 1**  HiSpark Studio AI核心工作区示意图<a name="fig2478146179"></a>  
![](figures/HiSpark-Studio-AI核心工作区示意图.png "HiSpark-Studio-AI核心工作区示意图")

## 关键概念<a name="ZH-CN_TOPIC_0000002517388100"></a>

本文档中涉及如下概念，在此处做统一说明。

-   **[AMCT](#ZH-CN_TOPIC_0000002548827971)**  

-   **[ATC](#ZH-CN_TOPIC_0000002548707983)**  

### AMCT<a name="ZH-CN_TOPIC_0000002548827971"></a>

AMCT（Ascend Model Compression Toolkit，简称AMCT）是一个针对昇腾芯片的深度学习模型压缩工具包，提供量化、张量分解等多种模型压缩特性，压缩后的模型体积变小，部署到NPU IP加速器上后可使能低比特运算，提高计算效率，从而实现性能提升。有关AMCT具体操作请参考《AMCT模型压缩工具用户指南》。

### ATC<a name="ZH-CN_TOPIC_0000002548707983"></a>

昇腾张量编译器（Ascend Tensor Compiler，简称ATC）是CANN异构计算架构体系下的模型转换工具，它可以将开源框架的网络模型转换为NPU IP加速器支持的离线模型。有关ATC具体操作请参考《ATC离线模型编译工具用户指南》。

# 数据准备与环境搭建<a name="ZH-CN_TOPIC_0000002548828403"></a>

-   **[数据准备](#ZH-CN_TOPIC_0000002517501304)**  

-   **[环境搭建](#ZH-CN_TOPIC_0000002517341386)**  

## 数据准备<a name="ZH-CN_TOPIC_0000002517501304"></a>

模型的训练后量化校准、量化感知训练、量化精度评估以及上板精度评估等操作需要对应数据，请按照如下格式准备数据：

-   数据存储为npy格式，每个文件对应一个与网络输出张量匹配的样本。
-   若模型有多个输出，则不同的输出必须存储在不同的目录中。同一个样本不同的输出名称需要保持一致。
-   分类任务真值存储为csv格式。包含两列sample和label，其中sample表示样本的名称，和npy文件名保持一致。label表示标签值。csv文件示例见[表1](#table55542586239)。

    **表 1**  分类真值标签csv表格示例

    <a name="table55542586239"></a>
    <table><thead align="left"><tr id="row655475820236"><th class="cellrowborder" valign="top" width="50%" id="mcps1.2.3.1.1"><p id="p1830154175715"><a name="p1830154175715"></a><a name="p1830154175715"></a><strong id="b1849143165818"><a name="b1849143165818"></a><a name="b1849143165818"></a>sample</strong></p>
    </th>
    <th class="cellrowborder" valign="top" width="50%" id="mcps1.2.3.1.2"><p id="p1830134125710"><a name="p1830134125710"></a><a name="p1830134125710"></a><strong id="b4591931105810"><a name="b4591931105810"></a><a name="b4591931105810"></a>label</strong></p>
    </th>
    </tr>
    </thead>
    <tbody><tr id="row1555205811235"><td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.1 "><p id="p13301174175713"><a name="p13301174175713"></a><a name="p13301174175713"></a>sample_00000_7.npy</p>
    </td>
    <td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.2 "><p id="p1630174165713"><a name="p1630174165713"></a><a name="p1630174165713"></a>7</p>
    </td>
    </tr>
    <tr id="row1726132522419"><td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.1 "><p id="p113011947579"><a name="p113011947579"></a><a name="p113011947579"></a>sample_00001_2.npy</p>
    </td>
    <td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.2 "><p id="p930114416571"><a name="p930114416571"></a><a name="p930114416571"></a>2</p>
    </td>
    </tr>
    </tbody>
    </table>

## 环境搭建<a name="ZH-CN_TOPIC_0000002517341386"></a>

环境配置请参考《HiSpark.AI 快速入门指南》。

# Hi3863操作指南<a name="ZH-CN_TOPIC_0000002509766614"></a>

-   **[工程创建](#ZH-CN_TOPIC_0000002509726608)**  

-   **[模型导入](#ZH-CN_TOPIC_0000002541326603)**  

-   **[模型量化](#ZH-CN_TOPIC_0000002541286615)**  

-   **[模型转换](#ZH-CN_TOPIC_0000002509766616)**  

-   **[部署](#ZH-CN_TOPIC_0000002541345339)**  

-   **[模型调优](#ZH-CN_TOPIC_0000002509726610)**  

-   **[应用开发](#ZH-CN_TOPIC_0000002541326605)**  

## 工程创建<a name="ZH-CN_TOPIC_0000002509726608"></a>

-   **[约束说明](#ZH-CN_TOPIC_0000002516863308)**  

-   **[界面介绍](#ZH-CN_TOPIC_0000002548503199)**  

### 约束说明<a name="ZH-CN_TOPIC_0000002516863308"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>新建工程需要满足以下条件：
>1.  用户使用WS63 SDK版本需要社区版本（[WS63社区链接](https://gitcode.com/HiSpark/fbb_ws63)） 或海思发布的商用版本。商用客户优先使用商用版本。
>2.  SDK存放路径必须为英文路径。

### 界面介绍<a name="ZH-CN_TOPIC_0000002548503199"></a>

-   **[首页](#ZH-CN_TOPIC_0000002548691489)**  

-   **[新建工程配置界面](#ZH-CN_TOPIC_0000002517211612)**  

#### 首页<a name="ZH-CN_TOPIC_0000002548691489"></a>

单击HiSpark Studio AI插件中的“Home”按钮，进入首页如[图1](#fig43390675013)所示。

**图 1**  HiSpark Studio AI首页<a name="fig43390675013"></a>  
![](figures/HiSpark-Studio-AI首页.png "HiSpark-Studio-AI首页")

若用户首次使用HiSpark Studio AI，单击“New Project”即可创建新项目。若用户需要项目迁移，也可以选择“Import Project”导入已有项目。

#### 新建工程配置界面<a name="ZH-CN_TOPIC_0000002517211612"></a>

选择芯片为WS63，选择已准备好的SDK目录，工程项目目录选择SDK相同路径即可。

**图 1**  HiSpark Studio AI新建工程配置界面<a name="fig19934131663619"></a>  
![](figures/HiSpark-Studio-AI新建工程配置界面.png "HiSpark-Studio-AI新建工程配置界面")

新建工程导入页面的具体逻辑如下，参数详细配置如[表1](#table1769074411309)所示。

1.  选择芯片“SOC”为WS63，“Board”为WS63，“Project Type”为Common Project通用项目。
2.  填写“Project Name”为项目名称。
3.  配置“Project Path”以及“SDK”，一般情况下，配置为下载的SDK路径。

**表 1**  新建工程参数配置

<a name="table1769074411309"></a>
<table><thead align="left"><tr id="row1769018444306"><th class="cellrowborder" valign="top" width="26.229999999999997%" id="mcps1.2.3.1.1"><p id="p769074418306"><a name="p769074418306"></a><a name="p769074418306"></a>参数</p>
</th>
<th class="cellrowborder" valign="top" width="73.77%" id="mcps1.2.3.1.2"><p id="p669044423018"><a name="p669044423018"></a><a name="p669044423018"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row13690144417303"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p869054419309"><a name="p869054419309"></a><a name="p869054419309"></a>SOC</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p0212053152519"><a name="p0212053152519"></a><a name="p0212053152519"></a>AI部署工程SOC类型。</p>
</td>
</tr>
<tr id="row15497102073518"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p1449712083518"><a name="p1449712083518"></a><a name="p1449712083518"></a>Board</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p161971592468"><a name="p161971592468"></a><a name="p161971592468"></a>AI部署工程所用具体单板型号。</p>
</td>
</tr>
<tr id="row176419249441"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p10852456174819"><a name="p10852456174819"></a><a name="p10852456174819"></a>Project Name</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p266374119478"><a name="p266374119478"></a><a name="p266374119478"></a>项目名称。</p>
</td>
</tr>
<tr id="row9587204511914"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p135887451899"><a name="p135887451899"></a><a name="p135887451899"></a>Project Path</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p19670175816474"><a name="p19670175816474"></a><a name="p19670175816474"></a>工程配置相关文件存放路径。</p>
</td>
</tr>
<tr id="row0675448181017"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p1067614871016"><a name="p1067614871016"></a><a name="p1067614871016"></a>SDK</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p1221716261486"><a name="p1221716261486"></a><a name="p1221716261486"></a>SDK文件存放路径。</p>
</td>
</tr>
<tr id="row11454192012481"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p2045416206486"><a name="p2045416206486"></a><a name="p2045416206486"></a>Finished</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p8454182044811"><a name="p8454182044811"></a><a name="p8454182044811"></a>完成新建文件。</p>
</td>
</tr>
<tr id="row866720531356"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p18229318368"><a name="p18229318368"></a><a name="p18229318368"></a>Cancel</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p71121238491"><a name="p71121238491"></a><a name="p71121238491"></a>取消新建文件。</p>
</td>
</tr>
</tbody>
</table>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>1.  用户需要提前准备WS63 SDK解压到指定目录，一级目录包含application、tools等文件夹。
>2.  通常情况下，用户将“SDK”和“Project Path”设置为相同路径即可。如果用户有将“.hiproj”等项目文件与SDK文件夹分开放置的需求，可以创建一个新的文件夹，专门用于放置项目文件，并单独配置到“Project Path”中。

## 模型导入<a name="ZH-CN_TOPIC_0000002541326603"></a>

模型导入主要帮助用户将本地已经训练好的ONNX模型或者TFLITE模型加载到HiSpark Studio AI中，并且记录之前的导入记录。

-   **[约束说明](#ZH-CN_TOPIC_0000002516764686)**  

-   **[界面介绍](#ZH-CN_TOPIC_0000002548164589)**  

### 约束说明<a name="ZH-CN_TOPIC_0000002516764686"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>用户导入的模型有以下约束：
>1.  ONNX模型满足Opset版本小于等于18。
>2.  TFLITE推荐版本为Tensorflow 2.13。
>3.  ONNX以及TFLITE模型中的算子必须位于列表中，具体清单请参考《HiSpark. AI 转换工具 使用指南》。
>4.  目前仅支持浮点ONNX以及TFLITE模型，量化后的模型暂时不支持。

### 界面介绍<a name="ZH-CN_TOPIC_0000002548164589"></a>

-   **[整体界面](#ZH-CN_TOPIC_0000002516604782)**  

-   **[Linux导入配置界面（仅Linux端用户需要关注）](#ZH-CN_TOPIC_0000002548244585)**  

#### 整体界面<a name="ZH-CN_TOPIC_0000002516604782"></a>

**图 1**  模型导入整体页面<a name="fig15594115103619"></a>  
![](figures/模型导入整体页面.png "模型导入整体页面")

模型导入的界面如[图1](#fig15594115103619)所示。主要包含以下部分：

1.  跳转标签（Select Model -\> Quantize -\> Convert -\> Deploy -\> Benchmark），当存在历史操作记录时，完成界面的切换。
2.  模型选择页面，用于选择部署目标模型。
3.  历史模型选择记录页面，显示所有的选择过模型的大小、修改时间，并提供回溯历史步骤以及删除功能。

模型导入步骤如下：

1.  进入模型选择页面，单击“Import Model”按钮，选择对应的Mnist ONNX模型，测试模型请参考[Mnist-12.onnx](https://gitcode.com/HiSpark/hispark_ai/blob/master/src/samples/oh/lenet5/model/mnist-12.onnx)。
2.  模型导入结束，进入量化页面。

#### Linux导入配置界面（仅Linux端用户需要关注）<a name="ZH-CN_TOPIC_0000002548244585"></a>

1.  首次单击“Import Model”按钮，需要用户填写服务器相关配置，用于连接远端服务器（需要先按照快速入门指南环境准备章节配置环境）。
2.  单击“仅命令传输 & 待定文件下载连接”按钮。

**图 1**  Linux服务器连接选项页面<a name="fig143981083427"></a>  
![](figures/Linux服务器连接选项页面.png "Linux服务器连接选项页面")

## 模型量化<a name="ZH-CN_TOPIC_0000002541286615"></a>

-   **[约束说明](#ZH-CN_TOPIC_0000002548383197)**  

-   **[量化前提](#ZH-CN_TOPIC_0000002516703394)**  

-   **[界面介绍](#ZH-CN_TOPIC_0000002516863310)**  

### 约束说明<a name="ZH-CN_TOPIC_0000002548383197"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>在进行模型压缩前，有以下约束：
>1.  模型压缩仅针对ONNX以及TFLITE两种格式的模型。
>2.  模型压缩仅支持未进行过量化的模型，已量化完成的ONNX以及TFLITE不支持。
>3.  任何网络都会被处理为分类网络，带标签的量化精度准确率评估仅针对网络输入为\[N, D\]格式。

### 量化前提<a name="ZH-CN_TOPIC_0000002516703394"></a>

用户需要准备模型量化的输入数据（Linux用户需要提前将数据放置到Docker环境所在的服务器上），可参考《快速入门指南》的“样例运行”章节准备。

### 界面介绍<a name="ZH-CN_TOPIC_0000002516863310"></a>

-   **[整体界面](#ZH-CN_TOPIC_0000002548503201)**  

-   **[量化参数配置页面](#ZH-CN_TOPIC_0000002548383199)**  

-   **[量化历史配置界面](#ZH-CN_TOPIC_0000002516703396)**  

-   **[验证集精度分布直方图显示界面](#ZH-CN_TOPIC_0000002516863312)**  

#### 整体界面<a name="ZH-CN_TOPIC_0000002548503201"></a>

**图 1**  模型量化示意图<a name="fig156191537102517"></a>  
![](figures/模型量化示意图.png "模型量化示意图")

模型压缩界面如[图1](#fig156191537102517)所示，整体界面主要包含四个部分：

1. 跳转标签页面，能否跳转到该量化记录关联的前后步骤。

2. 量化参数配置界面。

3. 压缩历史显示界面，显示所有的量化网络余弦相似度、MSE、准确率等指标。

4. 样本精度分布直方图显示界面，显示验证集量化输出与浮点标杆相似度的直方图界面。

量化步骤如下：

1.  进入量化页面，配置量化参数，参数详情请参见“[量化参数配置页面](#ZH-CN_TOPIC_0000002548383199)”。

    >![](public_sys-resources/icon-note.gif) **说明：** 
    >量化输入数据以及验证输入数据需要输入文件夹路径，文件夹内数据保持为npy格式。
    >多输入模型不同输入文件夹内每个npy文件名称代表样本名，样本名称需要保持一致。

1.  单击“Quantize”按钮，输出量化余弦相似度、准确率以及MSE等结果；单击“Next Without Quantization”按钮，直接跳过[3](#li475115341204)和[4](#li434033051115)进入转换步骤。
2.  <a name="li475115341204"></a>在量化历史配置界面与验证集精度直方图分布界面，查看量化结果。
3.  <a name="li434033051115"></a>单击“Next”进入下一步。

#### 量化参数配置页面<a name="ZH-CN_TOPIC_0000002548383199"></a>

**图 1**  模型量化参数配置界面<a name="fig66893348297"></a>  
![](figures/模型量化参数配置界面.png "模型量化参数配置界面")

参数解释如[表1](#table1769074411309)所示。

**表 1**  量化参数配置

<a name="table1769074411309"></a>
<table><thead align="left"><tr id="row1769018444306"><th class="cellrowborder" valign="top" width="26.229999999999997%" id="mcps1.2.3.1.1"><p id="p769074418306"><a name="p769074418306"></a><a name="p769074418306"></a>参数</p>
</th>
<th class="cellrowborder" valign="top" width="73.77%" id="mcps1.2.3.1.2"><p id="p669044423018"><a name="p669044423018"></a><a name="p669044423018"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row13690144417303"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p869054419309"><a name="p869054419309"></a><a name="p869054419309"></a>Quantized Data Type</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p18690204412306"><a name="p18690204412306"></a><a name="p18690204412306"></a>数据量化的数据位数。目前仅支持8bit量化，权重或激活值会转换成int8类型来参与计算。</p>
</td>
</tr>
<tr id="row15497102073518"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p1449712083518"><a name="p1449712083518"></a><a name="p1449712083518"></a>Quant Type</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p4498182013516"><a name="p4498182013516"></a><a name="p4498182013516"></a>数量量化类型。目前仅支持全量化。</p>
<a name="ul8922547415"></a><a name="ul8922547415"></a><ul id="ul8922547415"><li>FULL_QUANT：支持量化的算子权重以及中间层张量会被同时量化为低精度。</li></ul>
</td>
</tr>
<tr id="row176419249441"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p10852456174819"><a name="p10852456174819"></a><a name="p10852456174819"></a>Calibration Inputs</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p36512474420"><a name="p36512474420"></a><a name="p36512474420"></a>用户在该表格中输入量化的校准数据。表格中各列的含义如下所示：</p>
<a name="ul1749181515018"></a><a name="ul1749181515018"></a><ul id="ul1749181515018"><li>Input Node：网络输入节点的名称。</li><li>Path：校准数据的目录。目录中存放和模型输入匹配的npy文件数据。若模型有多个输入，同一个校准样本的多个输入npy文件文件名必须保持一致。</li><li>Shape（不可配置）：网络输入张量的形状。</li></ul>
</td>
</tr>
<tr id="row9587204511914"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p135887451899"><a name="p135887451899"></a><a name="p135887451899"></a>Validation</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p11588184515918"><a name="p11588184515918"></a><a name="p11588184515918"></a>使能验证开关。当开关打开时，验证数据集输入界面展开，如<a href="#fig125691159182914">图3</a>所示。</p>
</td>
</tr>
<tr id="row0675448181017"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p1067614871016"><a name="p1067614871016"></a><a name="p1067614871016"></a>Validation Inputs</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p16676134871019"><a name="p16676134871019"></a><a name="p16676134871019"></a>用户在该表格中输入量化评估网络的验证数据集。表格中各列的含义如<a href="#fig125691159182914">图3</a>所示：</p>
<a name="ul11478439133512"></a><a name="ul11478439133512"></a><ul id="ul11478439133512"><li>Input Node：网络输入节点的名称。</li><li>Path：验证数据的目录。目录中存放和模型输入匹配的npy文件数据。若模型有多个输入，同一个验证样本的多个输入npy文件文件名必须保持一致。</li></ul>
</td>
</tr>
<tr id="row7221131203619"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p18229318368"><a name="p18229318368"></a><a name="p18229318368"></a>Validation Labels</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p4519123583915"><a name="p4519123583915"></a><a name="p4519123583915"></a>使能开关打开后，输入含分类真值标签的csv表格文件。文件中的表格格式如<a href="#table112929412576">表2</a>所示。各列的含义如下所示：</p>
<a name="ul24531748114210"></a><a name="ul24531748114210"></a><ul id="ul24531748114210"><li>sample：验证样本的名称。</li><li>label：验证样本的标签值。</li></ul>
</td>
</tr>
<tr id="row11454192012481"><td class="cellrowborder" valign="top" width="26.229999999999997%" headers="mcps1.2.3.1.1 "><p id="p2045416206486"><a name="p2045416206486"></a><a name="p2045416206486"></a>Quantize</p>
</td>
<td class="cellrowborder" valign="top" width="73.77%" headers="mcps1.2.3.1.2 "><p id="p8454182044811"><a name="p8454182044811"></a><a name="p8454182044811"></a>开始量化按钮。</p>
</td>
</tr>
</tbody>
</table>

**图 2**  跳过量化按钮<a name="fig132176591794"></a>  
![](figures/跳过量化按钮.png "跳过量化按钮")

单击“Next Without Quantization”按钮，即可跳过量化步骤，直接转换成浮点模型。

**图 3**  验证数据输入页面<a name="fig125691159182914"></a>  
![](figures/验证数据输入页面.png "验证数据输入页面")

Validation Labels输入csv格式如[表2](#table112929412576)所示。

**表 2**  label.csv文件内容

<a name="table112929412576"></a>
<table><thead align="left"><tr id="row73010420575"><th class="cellrowborder" valign="top" width="50.12%" id="mcps1.2.3.1.1"><p id="p1830154175715"><a name="p1830154175715"></a><a name="p1830154175715"></a>sample</p>
</th>
<th class="cellrowborder" valign="top" width="49.88%" id="mcps1.2.3.1.2"><p id="p1830134125710"><a name="p1830134125710"></a><a name="p1830134125710"></a>label</p>
</th>
</tr>
</thead>
<tbody><tr id="row0301184195719"><td class="cellrowborder" valign="top" width="50.12%" headers="mcps1.2.3.1.1 "><p id="p13301174175713"><a name="p13301174175713"></a><a name="p13301174175713"></a>sample_00000_7.npy</p>
</td>
<td class="cellrowborder" valign="top" width="49.88%" headers="mcps1.2.3.1.2 "><p id="p1630174165713"><a name="p1630174165713"></a><a name="p1630174165713"></a>7</p>
</td>
</tr>
<tr id="row930164135710"><td class="cellrowborder" valign="top" width="50.12%" headers="mcps1.2.3.1.1 "><p id="p113011947579"><a name="p113011947579"></a><a name="p113011947579"></a>sample_00001_2.npy</p>
</td>
<td class="cellrowborder" valign="top" width="49.88%" headers="mcps1.2.3.1.2 "><p id="p930114416571"><a name="p930114416571"></a><a name="p930114416571"></a>2</p>
</td>
</tr>
</tbody>
</table>

>![](public_sys-resources/icon-note.gif) **说明：** 
>label.csv中为样本分类的真值标签。文件中的表格格式如[表2](#table112929412576)所示。其中sample列表示样本的名称，label列表示样本对应的真值标签。

#### 量化历史配置界面<a name="ZH-CN_TOPIC_0000002516703396"></a>

量化历史显示窗口如[图1](#fig16878619143716)所示。

**图 1**  量化历史配置页面<a name="fig16878619143716"></a>  
![](figures/量化历史配置页面.png "量化历史配置页面")

该窗口以表格的方式显示历史量化的结果。表头解释如[表1](#table17914154610556)所示。

**表 1**  历史压缩结果表头说明

<a name="table17914154610556"></a>
<table><thead align="left"><tr id="row691494685515"><th class="cellrowborder" valign="top" width="25.929999999999996%" id="mcps1.2.3.1.1"><p id="p189148465551"><a name="p189148465551"></a><a name="p189148465551"></a>项目</p>
</th>
<th class="cellrowborder" valign="top" width="74.07000000000001%" id="mcps1.2.3.1.2"><p id="p1391434685514"><a name="p1391434685514"></a><a name="p1391434685514"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row09141746195518"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p191416466557"><a name="p191416466557"></a><a name="p191416466557"></a>Trail ID</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p03571347185611"><a name="p03571347185611"></a><a name="p03571347185611"></a>网络量化结果的序号。</p>
</td>
</tr>
<tr id="row926611014579"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p52661011575"><a name="p52661011575"></a><a name="p52661011575"></a>Model Name</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p8266709578"><a name="p8266709578"></a><a name="p8266709578"></a>网络的名称，以及模型大小和修改时间。</p>
</td>
</tr>
<tr id="row499271165719"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p39921311125712"><a name="p39921311125712"></a><a name="p39921311125712"></a>Accuracy</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p16992191195715"><a name="p16992191195715"></a><a name="p16992191195715"></a>表示分类结果准确率，使用标签真值计算。</p>
</td>
</tr>
<tr id="row844131695717"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p184471665720"><a name="p184471665720"></a><a name="p184471665720"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p8151115911493"><a name="p8151115911493"></a><a name="p8151115911493"></a>余弦相似度，使用量化评估网络的输出和原始浮点网络的输出计算。</p>
</td>
</tr>
<tr id="row1676132014572"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p19676520145712"><a name="p19676520145712"></a><a name="p19676520145712"></a>MSE</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p189491228195019"><a name="p189491228195019"></a><a name="p189491228195019"></a>均方误差，使用量化评估网络的输出和原始浮点网络的输出计算。</p>
</td>
</tr>
<tr id="row199509591380"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p179501959884"><a name="p179501959884"></a><a name="p179501959884"></a>RAM(KB)</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p199509592818"><a name="p199509592818"></a><a name="p199509592818"></a>上板AI相关RAM内存估计。</p>
</td>
</tr>
<tr id="row2384771999"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p0385271894"><a name="p0385271894"></a><a name="p0385271894"></a>FLASH(KB)</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p1031018559917"><a name="p1031018559917"></a><a name="p1031018559917"></a>上板AI相关FLASH内存估计。</p>
</td>
</tr>
<tr id="row14206152325711"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p19206152355710"><a name="p19206152355710"></a><a name="p19206152355710"></a>Operation</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p1220642335713"><a name="p1220642335713"></a><a name="p1220642335713"></a>操作按钮：</p>
<a name="ul52775178594"></a><a name="ul52775178594"></a><ul id="ul52775178594"><li><a name="image14822121019112"></a><a name="image14822121019112"></a><span><img id="image14822121019112" src="figures/zh-cn_image_0000002562133105.png"></span>：下载压缩结果。下载的压缩包中包含：<a name="ul1285118481118"></a><a name="ul1285118481118"></a><ul id="ul1285118481118"><li>{模型名称}.ms：量化后模型IR。</li><li>{模型名称}.cfg：<span>量化配置。</span></li><li>quant_plot.json：量化评估结果文件。</li></ul>
</li><li><a name="image1746324617"></a><a name="image1746324617"></a><span><img id="image1746324617" src="figures/zh-cn_image_0000002562013105.png"></span>：删除当前记录。</li><li><a name="image1559016359114"></a><a name="image1559016359114"></a><span><img id="image1559016359114" src="figures/zh-cn_image_0000002531173136.png"></span>：跳转到模型转换页面，在模型转换页面对当前行对应的压缩网络进行模型转换。</li></ul>
</td>
</tr>
</tbody>
</table>

#### 验证集精度分布直方图显示界面<a name="ZH-CN_TOPIC_0000002516863312"></a>

验证集精度分布直方图显示窗口如[图1](#fig125132017185218)所示，该窗口显示验证集的余弦相似度的分布图。横轴为余弦相似度，纵轴为验证集样本的百分比。

**图 1**  验证集精度分布直方图显示界面<a name="fig125132017185218"></a>  
![](figures/验证集精度分布直方图显示界面.png "验证集精度分布直方图显示界面")

## 模型转换<a name="ZH-CN_TOPIC_0000002509766616"></a>

-   **[约束说明](#ZH-CN_TOPIC_0000002516898190)**  

-   **[转换前提](#ZH-CN_TOPIC_0000002517058108)**  

-   **[界面介绍](#ZH-CN_TOPIC_0000002548417995)**  

### 约束说明<a name="ZH-CN_TOPIC_0000002516898190"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>WS63模型转换需要满足以下条件：
>1.  用户转换的模型格式、版本以及算子需要满足条件详见“[约束说明](#ZH-CN_TOPIC_0000002516764686)”以及“[约束说明](#ZH-CN_TOPIC_0000002548383197)”。
>2.  用户需要确保Docker容器中MSLite工具链配套环境的完备性（Windows侧用户保证toolchain文件中tools下存在“mindspore-xxx-lite-xxx.x.x-win-x64”文件夹；Linux侧用户保证Docker容器内“/usr/src/mindspore”存在对应的“mindspore-xxx-lite-xxx.x.x-linux-x64”文件夹）。

### 转换前提<a name="ZH-CN_TOPIC_0000002517058108"></a>

用户已成功完成量化或跳过量化，且量化所用的校准数据位置不改变。

### 界面介绍<a name="ZH-CN_TOPIC_0000002548417995"></a>

-   **[整体界面](#ZH-CN_TOPIC_0000002548538003)**  

-   **[转换参数配置页面](#ZH-CN_TOPIC_0000002516898192)**  

-   **[转换历史配置界面](#ZH-CN_TOPIC_0000002517058110)**  

-   **[内存占用分布条形图显示界面](#ZH-CN_TOPIC_0000002548417997)**  

#### 整体界面<a name="ZH-CN_TOPIC_0000002548538003"></a>

**图 1**  模型转换整体界面<a name="fig57907974019"></a>  
![](figures/模型转换整体界面.png "模型转换整体界面")

模型转换整体界面如[图1](#fig57907974019)所示，主要包含四个部分：

1. 跳转标签页面，能否跳转到该量化记录关联的前后步骤。

2. 转换参数配置界面。

3. 历史转换记录配置界面，显示所有的转换网络余弦相似度、MSE、准确率、RAM、FLASH等指标。

4. 转换结果RAM/FLASH对比界面，显示模型转换预估上板的各项RAM/FLASH估计。

转换步骤：

1.  进入转换页面，配置转换参数，参数详情详见“[转换参数配置页面](#ZH-CN_TOPIC_0000002516898192)”。

1.  单击“Convert”按钮，输出转换RAM/FLASH等结果。
2.  单击“Next”进入下一步。

#### 转换参数配置页面<a name="ZH-CN_TOPIC_0000002516898192"></a>

**图 1**  转换参数配置页面<a name="fig487341125020"></a>  
![](figures/转换参数配置页面.png "转换参数配置页面")

参数说明如[表1](#table1769074411309)所示。

**表 1**  转换参数配置

<a name="table1769074411309"></a>
<table><thead align="left"><tr id="row1769018444306"><th class="cellrowborder" valign="top" width="25.019999999999996%" id="mcps1.2.3.1.1"><p id="p769074418306"><a name="p769074418306"></a><a name="p769074418306"></a>参数</p>
</th>
<th class="cellrowborder" valign="top" width="74.98%" id="mcps1.2.3.1.2"><p id="p669044423018"><a name="p669044423018"></a><a name="p669044423018"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row13690144417303"><td class="cellrowborder" valign="top" width="25.019999999999996%" headers="mcps1.2.3.1.1 "><p id="p869054419309"><a name="p869054419309"></a><a name="p869054419309"></a>Input Node（不可配置）</p>
</td>
<td class="cellrowborder" valign="top" width="74.98%" headers="mcps1.2.3.1.2 "><p id="p7320104755012"><a name="p7320104755012"></a><a name="p7320104755012"></a>输入变量名称。</p>
</td>
</tr>
<tr id="row15497102073518"><td class="cellrowborder" valign="top" width="25.019999999999996%" headers="mcps1.2.3.1.1 "><p id="p1449712083518"><a name="p1449712083518"></a><a name="p1449712083518"></a>Shape（不可配置）</p>
</td>
<td class="cellrowborder" valign="top" width="74.98%" headers="mcps1.2.3.1.2 "><p id="p1410744221013"><a name="p1410744221013"></a><a name="p1410744221013"></a>输入变量形状。</p>
</td>
</tr>
<tr id="row176419249441"><td class="cellrowborder" valign="top" width="25.019999999999996%" headers="mcps1.2.3.1.1 "><p id="p10852456174819"><a name="p10852456174819"></a><a name="p10852456174819"></a>Data Type（不可配置）</p>
</td>
<td class="cellrowborder" valign="top" width="74.98%" headers="mcps1.2.3.1.2 "><p id="p154251141201214"><a name="p154251141201214"></a><a name="p154251141201214"></a>输入变量的数据类型。</p>
</td>
</tr>
<tr id="row11454192012481"><td class="cellrowborder" valign="top" width="25.019999999999996%" headers="mcps1.2.3.1.1 "><p id="p2045416206486"><a name="p2045416206486"></a><a name="p2045416206486"></a>Convert</p>
</td>
<td class="cellrowborder" valign="top" width="74.98%" headers="mcps1.2.3.1.2 "><p id="p8454182044811"><a name="p8454182044811"></a><a name="p8454182044811"></a>开始转换按钮。</p>
</td>
</tr>
</tbody>
</table>

#### 转换历史配置界面<a name="ZH-CN_TOPIC_0000002517058110"></a>

**图 1**  历史转换结果配置界面<a name="fig172891046191311"></a>  
![](figures/历史转换结果配置界面.png "历史转换结果配置界面")

该窗口以表格的方式显示历史转换的结果。表头说明如[表1](#table17914154610556)所示。

**表 1**  历史转换结果表头说明

<a name="table17914154610556"></a>
<table><thead align="left"><tr id="row691494685515"><th class="cellrowborder" valign="top" width="25.929999999999996%" id="mcps1.2.3.1.1"><p id="p189148465551"><a name="p189148465551"></a><a name="p189148465551"></a>项目</p>
</th>
<th class="cellrowborder" valign="top" width="74.07000000000001%" id="mcps1.2.3.1.2"><p id="p1391434685514"><a name="p1391434685514"></a><a name="p1391434685514"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row09141746195518"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p191416466557"><a name="p191416466557"></a><a name="p191416466557"></a>Trail ID</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p03571347185611"><a name="p03571347185611"></a><a name="p03571347185611"></a>网络转换结果的序号。</p>
</td>
</tr>
<tr id="row926611014579"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p52661011575"><a name="p52661011575"></a><a name="p52661011575"></a>Model Name</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p8266709578"><a name="p8266709578"></a><a name="p8266709578"></a>网络的名称，以及模型大小和修改时间。</p>
</td>
</tr>
<tr id="row499271165719"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p39921311125712"><a name="p39921311125712"></a><a name="p39921311125712"></a>Accuracy</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p16992191195715"><a name="p16992191195715"></a><a name="p16992191195715"></a>表示分类结果准确率，使用标签真值计算。</p>
<p id="p16175262198"><a name="p16175262198"></a><a name="p16175262198"></a>准确率表示的格式：{量化模型准确率}({量化模型与原始浮点模型准确率对比})</p>
<a name="ul614475942616"></a><a name="ul614475942616"></a><ul id="ul614475942616"><li><a name="image10256111862719"></a><a name="image10256111862719"></a><span><img id="image10256111862719" src="figures/zh-cn_image_0000002561045444.png"></span>：表示量化后模型的准确率为0.99，与原始浮点网络模型相比上升0.01。</li><li><a name="image122892229115"></a><a name="image122892229115"></a><span><img id="image122892229115" src="figures/zh-cn_image_0000002591685199.png" width="97.75500000000001" height="35.0322"></span>：表示量化后模型的准确率为0.95，与原始浮点网络模型相比下降0.01。</li></ul>
</td>
</tr>
<tr id="row844131695717"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p872513454221"><a name="p872513454221"></a><a name="p872513454221"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p8151115911493"><a name="p8151115911493"></a><a name="p8151115911493"></a>余弦相似度，使用量化评估网络的输出和原始浮点网络的输出计算。</p>
</td>
</tr>
<tr id="row1676132014572"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p19676520145712"><a name="p19676520145712"></a><a name="p19676520145712"></a>MSE</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p189491228195019"><a name="p189491228195019"></a><a name="p189491228195019"></a>均方误差，使用量化评估网络的输出和原始浮点网络的输出计算。</p>
</td>
</tr>
<tr id="row199509591380"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p179501959884"><a name="p179501959884"></a><a name="p179501959884"></a>RAM(KB)</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p199509592818"><a name="p199509592818"></a><a name="p199509592818"></a>上板AI相关RAM内存估计。</p>
</td>
</tr>
<tr id="row2384771999"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p0385271894"><a name="p0385271894"></a><a name="p0385271894"></a>FLASH(KB)</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p1031018559917"><a name="p1031018559917"></a><a name="p1031018559917"></a>上板AI相关FLASH内存估计。</p>
</td>
</tr>
<tr id="row14206152325711"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p19206152355710"><a name="p19206152355710"></a><a name="p19206152355710"></a>Operation</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p1220642335713"><a name="p1220642335713"></a><a name="p1220642335713"></a>操作按钮：</p>
<a name="ul1211118337216"></a><a name="ul1211118337216"></a><ul id="ul1211118337216"><li><a name="image14822121019112"></a><a name="image14822121019112"></a><span><img id="image14822121019112" src="figures/zh-cn_image_0000002562133137.png"></span>：下载转换结果。下载的压缩包中包含：<a name="ul1285118481118"></a><a name="ul1285118481118"></a><ul id="ul1285118481118"><li>micro_gen文件夹：转换后的工程文件。</li><li>converter.cfg：转换配置<span>。</span></li><li>convert_plot.json：转换评估结果文件。</li></ul>
</li></ul>
<a name="ul52775178594"></a><a name="ul52775178594"></a><ul id="ul52775178594"><li><a name="image1746324617"></a><a name="image1746324617"></a><span><img id="image1746324617" src="figures/zh-cn_image_0000002562013141.png"></span>：删除当前记录。</li><li><a name="image1559016359114"></a><a name="image1559016359114"></a><span><img id="image1559016359114" src="figures/zh-cn_image_0000002562133139.png" width="63.84" height="41.040076"></span>：跳转到部署页面，对模型进行进一步的部署与调优。</li></ul>
</td>
</tr>
</tbody>
</table>

#### 内存占用分布条形图显示界面<a name="ZH-CN_TOPIC_0000002548417997"></a>

**图 1**  AI上板各存储占用分布<a name="fig205537152214"></a>  
![](figures/AI上板各存储占用分布.png "AI上板各存储占用分布")

AI上板存储占比如[图1](#fig205537152214)所示，蓝色显示为RAM占用，绿色显示为FLASH占用，各参数显示具体含义如[表1](#table17914154610556)所示。

**表 1**  内存占用分布条形图各项含义

<a name="table17914154610556"></a>
<table><thead align="left"><tr id="row691494685515"><th class="cellrowborder" valign="top" width="19.43%" id="mcps1.2.4.1.1"><p id="p189148465551"><a name="p189148465551"></a><a name="p189148465551"></a>项目</p>
</th>
<th class="cellrowborder" valign="top" width="12.07%" id="mcps1.2.4.1.2"><p id="p163542074279"><a name="p163542074279"></a><a name="p163542074279"></a>所属类型</p>
</th>
<th class="cellrowborder" valign="top" width="68.5%" id="mcps1.2.4.1.3"><p id="p1391434685514"><a name="p1391434685514"></a><a name="p1391434685514"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row09141746195518"><td class="cellrowborder" valign="top" width="19.43%" headers="mcps1.2.4.1.1 "><p id="p191416466557"><a name="p191416466557"></a><a name="p191416466557"></a>workspace</p>
</td>
<td class="cellrowborder" valign="top" width="12.07%" headers="mcps1.2.4.1.2 "><p id="p1835420711277"><a name="p1835420711277"></a><a name="p1835420711277"></a>RAM</p>
</td>
<td class="cellrowborder" valign="top" width="68.5%" headers="mcps1.2.4.1.3 "><p id="p18478163182516"><a name="p18478163182516"></a><a name="p18478163182516"></a>存储输入输出中间数据所需的工作空间RAM大小。</p>
</td>
</tr>
<tr id="row926611014579"><td class="cellrowborder" valign="top" width="19.43%" headers="mcps1.2.4.1.1 "><p id="p52661011575"><a name="p52661011575"></a><a name="p52661011575"></a>stack</p>
</td>
<td class="cellrowborder" valign="top" width="12.07%" headers="mcps1.2.4.1.2 "><p id="p8354207162718"><a name="p8354207162718"></a><a name="p8354207162718"></a>RAM</p>
</td>
<td class="cellrowborder" valign="top" width="68.5%" headers="mcps1.2.4.1.3 "><p id="p368433282510"><a name="p368433282510"></a><a name="p368433282510"></a>AI推理栈空间所占用大小。</p>
</td>
</tr>
<tr id="row499271165719"><td class="cellrowborder" valign="top" width="19.43%" headers="mcps1.2.4.1.1 "><p id="p39921311125712"><a name="p39921311125712"></a><a name="p39921311125712"></a>pack_weight</p>
</td>
<td class="cellrowborder" valign="top" width="12.07%" headers="mcps1.2.4.1.2 "><p id="p4354772275"><a name="p4354772275"></a><a name="p4354772275"></a>RAM</p>
</td>
<td class="cellrowborder" valign="top" width="68.5%" headers="mcps1.2.4.1.3 "><p id="p16992191195715"><a name="p16992191195715"></a><a name="p16992191195715"></a>AI推理针对权重额外辅助空间占用大小。</p>
</td>
</tr>
<tr id="row844131695717"><td class="cellrowborder" valign="top" width="19.43%" headers="mcps1.2.4.1.1 "><p id="p184471665720"><a name="p184471665720"></a><a name="p184471665720"></a>other</p>
</td>
<td class="cellrowborder" valign="top" width="12.07%" headers="mcps1.2.4.1.2 "><p id="p20354575273"><a name="p20354575273"></a><a name="p20354575273"></a>RAM</p>
</td>
<td class="cellrowborder" valign="top" width="68.5%" headers="mcps1.2.4.1.3 "><p id="p8151115911493"><a name="p8151115911493"></a><a name="p8151115911493"></a>其他对输入输出张量元信息存储占用等大小（输入输出张量名称，张量shape等）。</p>
</td>
</tr>
<tr id="row1676132014572"><td class="cellrowborder" valign="top" width="19.43%" headers="mcps1.2.4.1.1 "><p id="p4668163032710"><a name="p4668163032710"></a><a name="p4668163032710"></a>code</p>
</td>
<td class="cellrowborder" valign="top" width="12.07%" headers="mcps1.2.4.1.2 "><p id="p23541274274"><a name="p23541274274"></a><a name="p23541274274"></a>FLASH</p>
</td>
<td class="cellrowborder" valign="top" width="68.5%" headers="mcps1.2.4.1.3 "><p id="p162941446102714"><a name="p162941446102714"></a><a name="p162941446102714"></a>AI推理相关算子，Runtime代码段占用。</p>
</td>
</tr>
<tr id="row199509591380"><td class="cellrowborder" valign="top" width="19.43%" headers="mcps1.2.4.1.1 "><p id="p451483410273"><a name="p451483410273"></a><a name="p451483410273"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="12.07%" headers="mcps1.2.4.1.2 "><p id="p6354773276"><a name="p6354773276"></a><a name="p6354773276"></a>FLASH</p>
</td>
<td class="cellrowborder" valign="top" width="68.5%" headers="mcps1.2.4.1.3 "><p id="p199509592818"><a name="p199509592818"></a><a name="p199509592818"></a>AI推理过程中数据段占用。</p>
</td>
</tr>
<tr id="row2384771999"><td class="cellrowborder" valign="top" width="19.43%" headers="mcps1.2.4.1.1 "><p id="p0385271894"><a name="p0385271894"></a><a name="p0385271894"></a>weight</p>
</td>
<td class="cellrowborder" valign="top" width="12.07%" headers="mcps1.2.4.1.2 "><p id="p123541271274"><a name="p123541271274"></a><a name="p123541271274"></a>FLASH</p>
</td>
<td class="cellrowborder" valign="top" width="68.5%" headers="mcps1.2.4.1.3 "><p id="p1031018559917"><a name="p1031018559917"></a><a name="p1031018559917"></a>AI推理参数FLASH存储代码段占用（非数据段）。</p>
</td>
</tr>
</tbody>
</table>

## 部署<a name="ZH-CN_TOPIC_0000002541345339"></a>

-   **[约束说明](#ZH-CN_TOPIC_0000002548538005)**  

-   **[界面介绍](#ZH-CN_TOPIC_0000002516898194)**  

### 约束说明<a name="ZH-CN_TOPIC_0000002548538005"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>WS63模型部署需要满足以下条件：
>用户必须已成功完成模型转换。

### 界面介绍<a name="ZH-CN_TOPIC_0000002516898194"></a>

**图 1**  模型部署页面<a name="fig5293115453112"></a>  
![](figures/模型部署页面.png "模型部署页面")

模型部署整体界面如[图1](#fig5293115453112)所示，主要包含四个部分：

1. 跳转标签页面，能否跳转到该量化记录关联的前后步骤。

2. 模型选择页面，展示已选中的模型。

3. SDK编译以及烧录页面。

4. 转换产物下载页面。

转换步骤如下：

1.  单击界面上SDK Compile右侧的“Build”按钮，进行SDK的编译。
2.  选择对应的Port以及Baud Rate，单击界面上的“Burn”按钮，完成固件烧录。

1.  单击“Next”按钮，进行下一步性能 & 精度验证。

## 模型调优<a name="ZH-CN_TOPIC_0000002509726610"></a>

-   **[约束说明](#ZH-CN_TOPIC_0000002517058112)**  

-   **[调优前提](#ZH-CN_TOPIC_0000002548417999)**  

-   **[界面介绍](#ZH-CN_TOPIC_0000002548538007)**  

### 约束说明<a name="ZH-CN_TOPIC_0000002517058112"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>WS63模型调优需要满足以下约束条件：
>-   用户需要保证SDK的完整性，确保AI组件（Adaptor 以及 AI\_AT组件）包含在SDK中。
>-   用户需要保证单个样本的输入数据量总和小于4K。
>-   用户需要准备一块WS63单板，并且使用USB串口线与本地PC连接。

### 调优前提<a name="ZH-CN_TOPIC_0000002548417999"></a>

用户已完成模型转换步骤。

### 界面介绍<a name="ZH-CN_TOPIC_0000002548538007"></a>

-   **[整体界面](#ZH-CN_TOPIC_0000002516898196)**  

-   **[性能验证参数配置页面](#ZH-CN_TOPIC_0000002517058114)**  

-   **[性能验证结果配置页面](#ZH-CN_TOPIC_0000002548418001)**  

-   **[精度验证参数配置页面](#ZH-CN_TOPIC_0000002548538009)**  

-   **[精度验证结果配置页面](#ZH-CN_TOPIC_0000002516898198)**  

-   **[评估结果汇总页面](#ZH-CN_TOPIC_0000002562010663)**  

#### 整体界面<a name="ZH-CN_TOPIC_0000002516898196"></a>

**图 1**  WS63模型调优整体页面<a name="fig89471319155115"></a>  
![](figures/WS63模型调优整体页面.png "WS63模型调优整体页面")

模型调优界面如[图1](#fig89471319155115)所示，主要包含五个部分：

1. 跳转标签页面，能否跳转到该量化记录关联的前后步骤。

2. 性能验证参数配置页面，配置相关的串口连接相关选项。

3. 性能验证结果评估页面，显示AI上板推理时间、RAM内存消耗、FLASH内存消耗等信息。

4. 精度验证参数配置页面，配置相关的精度验证输入数据输入等信息。

5. 精度验证结果评估页面，显示上板精度评估余弦相似度分布直方图 & 准确率等信息。

模型调优步骤如下：

1.  进入模型调优页面，选择单板连接的串口以及波特率。

1.  单击“Performance Evaluation”按钮，输出上板推理时间、RAM内存消耗、FLASH内存消耗等信息。
2.  选择Windows本地相应的验证数据输入文件夹等精度验证相关的选项。

    >![](public_sys-resources/icon-note.gif) **说明：** 
    >上板精度验证输入数据以及验证输入数据需要输入文件夹路径，文件夹内上板精度验证数据保持为npy格式。

3.  单击“Accuracy Evaluation”按钮，输出相关的准确率、余弦相似度分布以及上板推理的时间、精度等信息。

#### 性能验证参数配置页面<a name="ZH-CN_TOPIC_0000002517058114"></a>

**图 1**  性能验证选项配置<a name="fig995816154011"></a>  
![](figures/性能验证选项配置.png "性能验证选项配置")

参数解释如[表1](#table1769074411309)所示。

**表 1**  转换参数配置

<a name="table1769074411309"></a>
<table><thead align="left"><tr id="row1769018444306"><th class="cellrowborder" valign="top" width="26.3%" id="mcps1.2.3.1.1"><p id="p769074418306"><a name="p769074418306"></a><a name="p769074418306"></a>参数</p>
</th>
<th class="cellrowborder" valign="top" width="73.7%" id="mcps1.2.3.1.2"><p id="p669044423018"><a name="p669044423018"></a><a name="p669044423018"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row13690144417303"><td class="cellrowborder" valign="top" width="26.3%" headers="mcps1.2.3.1.1 "><p id="p1430713542016"><a name="p1430713542016"></a><a name="p1430713542016"></a>Port</p>
</td>
<td class="cellrowborder" valign="top" width="73.7%" headers="mcps1.2.3.1.2 "><p id="p1969021118"><a name="p1969021118"></a><a name="p1969021118"></a>单板连接的串口号。</p>
</td>
</tr>
<tr id="row15497102073518"><td class="cellrowborder" valign="top" width="26.3%" headers="mcps1.2.3.1.1 "><p id="p3934181817110"><a name="p3934181817110"></a><a name="p3934181817110"></a>Baud Rate</p>
</td>
<td class="cellrowborder" valign="top" width="73.7%" headers="mcps1.2.3.1.2 "><p id="p1410744221013"><a name="p1410744221013"></a><a name="p1410744221013"></a>单板连接的波特率。</p>
</td>
</tr>
</tbody>
</table>

#### 性能验证结果配置页面<a name="ZH-CN_TOPIC_0000002548418001"></a>

**图 1**  性能验证结果页面<a name="fig079215513611"></a>  
![](figures/性能验证结果页面.png "性能验证结果页面")

具体每个参数含义如[表1](#table1769074411309)所示。

**表 1**  性能验证结果

<a name="table1769074411309"></a>
<table><thead align="left"><tr id="row1769018444306"><th class="cellrowborder" valign="top" width="24.990000000000002%" id="mcps1.2.3.1.1"><p id="p769074418306"><a name="p769074418306"></a><a name="p769074418306"></a>参数</p>
</th>
<th class="cellrowborder" valign="top" width="75.01%" id="mcps1.2.3.1.2"><p id="p669044423018"><a name="p669044423018"></a><a name="p669044423018"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row13690144417303"><td class="cellrowborder" valign="top" width="24.990000000000002%" headers="mcps1.2.3.1.1 "><p id="p1430713542016"><a name="p1430713542016"></a><a name="p1430713542016"></a>INFERENCE TIME</p>
</td>
<td class="cellrowborder" valign="top" width="75.01%" headers="mcps1.2.3.1.2 "><p id="p1969021118"><a name="p1969021118"></a><a name="p1969021118"></a>上板AI推理时间。</p>
</td>
</tr>
<tr id="row15497102073518"><td class="cellrowborder" valign="top" width="24.990000000000002%" headers="mcps1.2.3.1.1 "><p id="p3934181817110"><a name="p3934181817110"></a><a name="p3934181817110"></a>RAM</p>
</td>
<td class="cellrowborder" valign="top" width="75.01%" headers="mcps1.2.3.1.2 "><p id="p1410744221013"><a name="p1410744221013"></a><a name="p1410744221013"></a>上板性能验证的RAM内存消耗。</p>
</td>
</tr>
<tr id="row142072442117"><td class="cellrowborder" valign="top" width="24.990000000000002%" headers="mcps1.2.3.1.1 "><p id="p15207944141111"><a name="p15207944141111"></a><a name="p15207944141111"></a>FLASH</p>
</td>
<td class="cellrowborder" valign="top" width="75.01%" headers="mcps1.2.3.1.2 "><p id="p1120724471113"><a name="p1120724471113"></a><a name="p1120724471113"></a>上板性能验证的FLASH内存消耗。</p>
</td>
</tr>
<tr id="row16051831165115"><td class="cellrowborder" valign="top" width="24.990000000000002%" headers="mcps1.2.3.1.1 "><p id="p36051531125119"><a name="p36051531125119"></a><a name="p36051531125119"></a>Performance Evaluation</p>
</td>
<td class="cellrowborder" valign="top" width="75.01%" headers="mcps1.2.3.1.2 "><p id="p13605183165111"><a name="p13605183165111"></a><a name="p13605183165111"></a>性能验证按钮。</p>
</td>
</tr>
</tbody>
</table>

#### 精度验证参数配置页面<a name="ZH-CN_TOPIC_0000002548538009"></a>

**图 1**  上板精度验证配置页面<a name="fig19579133791213"></a>  
![](figures/上板精度验证配置页面.png "上板精度验证配置页面")

参数解释如[表1](#table1769074411309)所示。

**表 1**  转换参数配置

<a name="table1769074411309"></a>
<table><thead align="left"><tr id="row1769018444306"><th class="cellrowborder" valign="top" width="32.1%" id="mcps1.2.3.1.1"><p id="p769074418306"><a name="p769074418306"></a><a name="p769074418306"></a>参数</p>
</th>
<th class="cellrowborder" valign="top" width="67.9%" id="mcps1.2.3.1.2"><p id="p669044423018"><a name="p669044423018"></a><a name="p669044423018"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row138985316508"><td class="cellrowborder" valign="top" width="32.1%" headers="mcps1.2.3.1.1 "><p id="p73891534502"><a name="p73891534502"></a><a name="p73891534502"></a>Input Node</p>
</td>
<td class="cellrowborder" valign="top" width="67.9%" headers="mcps1.2.3.1.2 "><p id="p8389145315012"><a name="p8389145315012"></a><a name="p8389145315012"></a>上板精度验证输入名称。</p>
</td>
</tr>
<tr id="row13690144417303"><td class="cellrowborder" valign="top" width="32.1%" headers="mcps1.2.3.1.1 "><p id="p105589115518"><a name="p105589115518"></a><a name="p105589115518"></a>Path</p>
</td>
<td class="cellrowborder" valign="top" width="67.9%" headers="mcps1.2.3.1.2 "><p id="p1969021118"><a name="p1969021118"></a><a name="p1969021118"></a>上板精度验证输入数据文件夹路径。</p>
</td>
</tr>
<tr id="row15497102073518"><td class="cellrowborder" valign="top" width="32.1%" headers="mcps1.2.3.1.1 "><p id="p3934181817110"><a name="p3934181817110"></a><a name="p3934181817110"></a>Validation Labels</p>
</td>
<td class="cellrowborder" valign="top" width="67.9%" headers="mcps1.2.3.1.2 "><p id="p365025421314"><a name="p365025421314"></a><a name="p365025421314"></a>上板精度验证的labels标签。</p>
</td>
</tr>
<tr id="row1147919919148"><td class="cellrowborder" valign="top" width="32.1%" headers="mcps1.2.3.1.1 "><p id="p18479139101418"><a name="p18479139101418"></a><a name="p18479139101418"></a>Accuracy Validation</p>
</td>
<td class="cellrowborder" valign="top" width="67.9%" headers="mcps1.2.3.1.2 "><p id="p14479179171415"><a name="p14479179171415"></a><a name="p14479179171415"></a>精度验证按钮。</p>
</td>
</tr>
</tbody>
</table>

#### 精度验证结果配置页面<a name="ZH-CN_TOPIC_0000002516898198"></a>

上板精度验证结果页面主要分为以下三部分：

-   准确率信息
-   逐项结果展示
-   余弦相似度分布直方图

各参数如[表1](#table1769074411309)所示。

**表 1**  上板精度验证结果说明

<a name="table1769074411309"></a>
<table><thead align="left"><tr id="row1769018444306"><th class="cellrowborder" valign="top" width="28.68%" id="mcps1.2.4.1.1"><p id="p769074418306"><a name="p769074418306"></a><a name="p769074418306"></a>参数</p>
</th>
<th class="cellrowborder" valign="top" width="32.07%" id="mcps1.2.4.1.2"><p id="p10796142512011"><a name="p10796142512011"></a><a name="p10796142512011"></a>所属部分</p>
</th>
<th class="cellrowborder" valign="top" width="39.25%" id="mcps1.2.4.1.3"><p id="p669044423018"><a name="p669044423018"></a><a name="p669044423018"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row13690144417303"><td class="cellrowborder" valign="top" width="28.68%" headers="mcps1.2.4.1.1 "><p id="p1430713542016"><a name="p1430713542016"></a><a name="p1430713542016"></a>ACCURACY</p>
</td>
<td class="cellrowborder" valign="top" width="32.07%" headers="mcps1.2.4.1.2 "><p id="p20796192512201"><a name="p20796192512201"></a><a name="p20796192512201"></a>准确率信息</p>
</td>
<td class="cellrowborder" valign="top" width="39.25%" headers="mcps1.2.4.1.3 "><p id="p971775751913"><a name="p971775751913"></a><a name="p971775751913"></a>上板精度验证准确率</p>
</td>
</tr>
<tr id="row15497102073518"><td class="cellrowborder" valign="top" width="28.68%" headers="mcps1.2.4.1.1 "><p id="p07691614142018"><a name="p07691614142018"></a><a name="p07691614142018"></a>Sample Name</p>
</td>
<td class="cellrowborder" valign="top" width="32.07%" headers="mcps1.2.4.1.2 "><p id="p9796102582018"><a name="p9796102582018"></a><a name="p9796102582018"></a>逐项结果展示</p>
</td>
<td class="cellrowborder" valign="top" width="39.25%" headers="mcps1.2.4.1.3 "><p id="p17715835202112"><a name="p17715835202112"></a><a name="p17715835202112"></a>样本名称</p>
</td>
</tr>
<tr id="row19578139540"><td class="cellrowborder" valign="top" width="28.68%" headers="mcps1.2.4.1.1 "><p id="p795712132540"><a name="p795712132540"></a><a name="p795712132540"></a>Output Name</p>
</td>
<td class="cellrowborder" valign="top" width="32.07%" headers="mcps1.2.4.1.2 "><p id="p101152023135419"><a name="p101152023135419"></a><a name="p101152023135419"></a>逐项结果展示</p>
</td>
<td class="cellrowborder" valign="top" width="39.25%" headers="mcps1.2.4.1.3 "><p id="p695712133547"><a name="p695712133547"></a><a name="p695712133547"></a>指标所对应的输出名称</p>
</td>
</tr>
<tr id="row63547222115"><td class="cellrowborder" valign="top" width="28.68%" headers="mcps1.2.4.1.1 "><p id="p18355629215"><a name="p18355629215"></a><a name="p18355629215"></a>Predict</p>
</td>
<td class="cellrowborder" valign="top" width="32.07%" headers="mcps1.2.4.1.2 "><p id="p143550215217"><a name="p143550215217"></a><a name="p143550215217"></a>逐项结果展示</p>
</td>
<td class="cellrowborder" valign="top" width="39.25%" headers="mcps1.2.4.1.3 "><p id="p2558611102211"><a name="p2558611102211"></a><a name="p2558611102211"></a>上板推理结果</p>
</td>
</tr>
<tr id="row144111758212"><td class="cellrowborder" valign="top" width="28.68%" headers="mcps1.2.4.1.1 "><p id="p1041125202111"><a name="p1041125202111"></a><a name="p1041125202111"></a>Golden</p>
</td>
<td class="cellrowborder" valign="top" width="32.07%" headers="mcps1.2.4.1.2 "><p id="p441113516212"><a name="p441113516212"></a><a name="p441113516212"></a>逐项结果展示</p>
</td>
<td class="cellrowborder" valign="top" width="39.25%" headers="mcps1.2.4.1.3 "><p id="p7411459214"><a name="p7411459214"></a><a name="p7411459214"></a>标杆推理结果</p>
</td>
</tr>
<tr id="row162581712115"><td class="cellrowborder" valign="top" width="28.68%" headers="mcps1.2.4.1.1 "><p id="p9625141719219"><a name="p9625141719219"></a><a name="p9625141719219"></a>Accuracy</p>
</td>
<td class="cellrowborder" valign="top" width="32.07%" headers="mcps1.2.4.1.2 "><p id="p662531719217"><a name="p662531719217"></a><a name="p662531719217"></a>逐项结果展示</p>
</td>
<td class="cellrowborder" valign="top" width="39.25%" headers="mcps1.2.4.1.3 "><p id="p17625017162114"><a name="p17625017162114"></a><a name="p17625017162114"></a>样本所对应的准确率信息</p>
</td>
</tr>
<tr id="row68591621152116"><td class="cellrowborder" valign="top" width="28.68%" headers="mcps1.2.4.1.1 "><p id="p9859821192116"><a name="p9859821192116"></a><a name="p9859821192116"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" width="32.07%" headers="mcps1.2.4.1.2 "><p id="p1286010218215"><a name="p1286010218215"></a><a name="p1286010218215"></a>逐项结果展示</p>
</td>
<td class="cellrowborder" valign="top" width="39.25%" headers="mcps1.2.4.1.3 "><p id="p6860721202114"><a name="p6860721202114"></a><a name="p6860721202114"></a>余弦相似度</p>
</td>
</tr>
<tr id="row1147919919148"><td class="cellrowborder" valign="top" width="28.68%" headers="mcps1.2.4.1.1 "><p id="p18479139101418"><a name="p18479139101418"></a><a name="p18479139101418"></a>Probability Density Histogram</p>
</td>
<td class="cellrowborder" valign="top" width="32.07%" headers="mcps1.2.4.1.2 "><p id="p16796142502011"><a name="p16796142502011"></a><a name="p16796142502011"></a>余弦相似度分布直方图</p>
</td>
<td class="cellrowborder" valign="top" width="39.25%" headers="mcps1.2.4.1.3 "><p id="p138301428132218"><a name="p138301428132218"></a><a name="p138301428132218"></a>余弦相似度分布图</p>
</td>
</tr>
</tbody>
</table>

**图 1**  上板精度验证准确率信息<a name="fig1940433918178"></a>  
![](figures/上板精度验证准确率信息.png "上板精度验证准确率信息")

**图 2**  上板精度验证逐项结果展示<a name="fig131353914188"></a>  
![](figures/上板精度验证逐项结果展示.png "上板精度验证逐项结果展示")

**图 3**  上板精度验证余弦相似度分布直方图<a name="fig12558337151812"></a>  
![](figures/上板精度验证余弦相似度分布直方图.png "上板精度验证余弦相似度分布直方图")

#### 评估结果汇总页面<a name="ZH-CN_TOPIC_0000002562010663"></a>

单击“Summary of Results”按钮之后弹出评估结果汇总界面，该界面汇总每次评估的结果。如[图1](#fig495923816254)所示。

**图 1**  评估结果汇总界面<a name="fig495923816254"></a>  
![](figures/评估结果汇总界面.png "评估结果汇总界面")

评估结果汇总界面元素说明如[表1](#table126871262713)所示。

**表 1**  评估结果界面元素说明

<a name="table126871262713"></a>
<table><thead align="left"><tr id="row26821219274"><th class="cellrowborder" valign="top" width="13.08%" id="mcps1.2.4.1.1"><p id="p1968191282719"><a name="p1968191282719"></a><a name="p1968191282719"></a>指标</p>
</th>
<th class="cellrowborder" valign="top" width="16.32%" id="mcps1.2.4.1.2"><p id="p74741310154113"><a name="p74741310154113"></a><a name="p74741310154113"></a>指标所属部分</p>
</th>
<th class="cellrowborder" valign="top" width="70.6%" id="mcps1.2.4.1.3"><p id="p2069151252713"><a name="p2069151252713"></a><a name="p2069151252713"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row920295822719"><td class="cellrowborder" valign="top" width="13.08%" headers="mcps1.2.4.1.1 "><p id="p17202155862714"><a name="p17202155862714"></a><a name="p17202155862714"></a>Trail ID</p>
</td>
<td class="cellrowborder" valign="top" width="16.32%" headers="mcps1.2.4.1.2 "><p id="p134751910174111"><a name="p134751910174111"></a><a name="p134751910174111"></a>----</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p1420235818272"><a name="p1420235818272"></a><a name="p1420235818272"></a>评估结果序号。</p>
</td>
</tr>
<tr id="row131301128142814"><td class="cellrowborder" valign="top" width="13.08%" headers="mcps1.2.4.1.1 "><p id="p151301928202820"><a name="p151301928202820"></a><a name="p151301928202820"></a>Model Name</p>
</td>
<td class="cellrowborder" valign="top" width="16.32%" headers="mcps1.2.4.1.2 "><p id="p1547512105418"><a name="p1547512105418"></a><a name="p1547512105418"></a>Benchmark</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p1513012282281"><a name="p1513012282281"></a><a name="p1513012282281"></a>网络的名称，以及模型大小和修改时间。</p>
</td>
</tr>
<tr id="row4391171693915"><td class="cellrowborder" valign="top" width="13.08%" headers="mcps1.2.4.1.1 "><p id="p1039251643910"><a name="p1039251643910"></a><a name="p1039251643910"></a>Accuracy</p>
</td>
<td class="cellrowborder" valign="top" width="16.32%" headers="mcps1.2.4.1.2 "><p id="p747551054117"><a name="p747551054117"></a><a name="p747551054117"></a>Benchmark</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p939221615399"><a name="p939221615399"></a><a name="p939221615399"></a>模型上板精度评估的准确率。</p>
</td>
</tr>
<tr id="row87249382281"><td class="cellrowborder" valign="top" width="13.08%" headers="mcps1.2.4.1.1 "><p id="p272463882818"><a name="p272463882818"></a><a name="p272463882818"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" width="16.32%" headers="mcps1.2.4.1.2 "><p id="p447501064112"><a name="p447501064112"></a><a name="p447501064112"></a>Benchmark</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p54531149131416"><a name="p54531149131416"></a><a name="p54531149131416"></a>模型上板精度评估的平均余弦相似度，计算公式如下，其中<a name="image15484124391614"></a><a name="image15484124391614"></a><span><img class="mathml" id="image15484124391614" src="figures/zh-cn_formulaimage_0000002531170700.png" width="18.837056" height="34.398189"></span>表示模型上板推理的输出，<a name="image634019531710"></a><a name="image634019531710"></a><span><img class="mathml" id="image634019531710" src="figures/zh-cn_formulaimage_0000002562010667.png" width="19.427443000000004" height="30.408189"></span>表示原始浮点网络在Windows的输出，<a name="image8788135318194"></a><a name="image8788135318194"></a><span><img class="mathml" id="image8788135318194" src="figures/zh-cn_formulaimage_0000002531170702.png" width="20.937126000000003" height="31.405689"></span>表示验证集样本的数量。</p>
<p id="p8151115911493"><a name="p8151115911493"></a><a name="p8151115911493"></a><a name="image196582429196"></a><a name="image196582429196"></a><span><img class="mathml" id="image196582429196" src="figures/zh-cn_formulaimage_0000002562010669.png" width="250.3725" height="75.380942"></span></p>
</td>
</tr>
<tr id="row9187175792810"><td class="cellrowborder" valign="top" width="13.08%" headers="mcps1.2.4.1.1 "><p id="p918765714288"><a name="p918765714288"></a><a name="p918765714288"></a>Inference Time</p>
</td>
<td class="cellrowborder" valign="top" width="16.32%" headers="mcps1.2.4.1.2 "><p id="p1347513106415"><a name="p1347513106415"></a><a name="p1347513106415"></a>Benchmark</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p0187195702812"><a name="p0187195702812"></a><a name="p0187195702812"></a>模型性能评估上板推理的时间。</p>
</td>
</tr>
<tr id="row71421715292"><td class="cellrowborder" valign="top" width="13.08%" headers="mcps1.2.4.1.1 "><p id="p4149171298"><a name="p4149171298"></a><a name="p4149171298"></a>RAM</p>
</td>
<td class="cellrowborder" valign="top" width="16.32%" headers="mcps1.2.4.1.2 "><p id="p1147519109413"><a name="p1147519109413"></a><a name="p1147519109413"></a>Benchmark</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p101413173299"><a name="p101413173299"></a><a name="p101413173299"></a>模型上板推理所占用的RAM开销。</p>
</td>
</tr>
<tr id="row15753193722918"><td class="cellrowborder" valign="top" width="13.08%" headers="mcps1.2.4.1.1 "><p id="p1819518406296"><a name="p1819518406296"></a><a name="p1819518406296"></a>Flash</p>
</td>
<td class="cellrowborder" valign="top" width="16.32%" headers="mcps1.2.4.1.2 "><p id="p1475201015414"><a name="p1475201015414"></a><a name="p1475201015414"></a>Benchmark</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p14753153782919"><a name="p14753153782919"></a><a name="p14753153782919"></a>模型上板推理所占用的FLASH开销。</p>
</td>
</tr>
<tr id="row627412105305"><td class="cellrowborder" valign="top" width="13.08%" headers="mcps1.2.4.1.1 "><p id="p142741510193011"><a name="p142741510193011"></a><a name="p142741510193011"></a>Accuracy</p>
</td>
<td class="cellrowborder" valign="top" width="16.32%" headers="mcps1.2.4.1.2 "><p id="p9475141014415"><a name="p9475141014415"></a><a name="p9475141014415"></a>Quantize</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p827451083012"><a name="p827451083012"></a><a name="p827451083012"></a>模型量化准确率。</p>
</td>
</tr>
<tr id="row28969270300"><td class="cellrowborder" valign="top" width="13.08%" headers="mcps1.2.4.1.1 "><p id="p16681185724210"><a name="p16681185724210"></a><a name="p16681185724210"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" width="16.32%" headers="mcps1.2.4.1.2 "><p id="p3475111015416"><a name="p3475111015416"></a><a name="p3475111015416"></a>Quantize</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p138966274309"><a name="p138966274309"></a><a name="p138966274309"></a>模型量化平均余弦相似度，计算公式如上</p>
</td>
</tr>
<tr id="row17854435134312"><td class="cellrowborder" valign="top" width="13.08%" headers="mcps1.2.4.1.1 "><p id="p208541335184313"><a name="p208541335184313"></a><a name="p208541335184313"></a>MSE</p>
</td>
<td class="cellrowborder" valign="top" width="16.32%" headers="mcps1.2.4.1.2 "><p id="p285493511434"><a name="p285493511434"></a><a name="p285493511434"></a>Quantize</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p485403524318"><a name="p485403524318"></a><a name="p485403524318"></a>模型量化的均方误差，计算公式如下，其中<a name="image624053817501"></a><a name="image624053817501"></a><span><img class="mathml" id="image624053817501" src="figures/zh-cn_formulaimage_0000002562132507.png" width="18.837056" height="34.398189"></span>表示模型上板推理的输出，<a name="image224063816505"></a><a name="image224063816505"></a><span><img class="mathml" id="image224063816505" src="figures/zh-cn_formulaimage_0000002531172536.png" width="19.427443000000004" height="30.408189"></span>表示原始浮点网络在Windows的输出，<a name="image14240538125016"></a><a name="image14240538125016"></a><span><img class="mathml" id="image14240538125016" src="figures/zh-cn_formulaimage_0000002562132511.png" width="20.937126000000003" height="31.405689"></span>表示验证集样本的数量。</p>
<p id="p13519152134318"><a name="p13519152134318"></a><a name="p13519152134318"></a><a name="image1315481514500"></a><a name="image1315481514500"></a><span><img class="mathml" id="image1315481514500" src="figures/zh-cn_formulaimage_0000002531052504.png" width="244.38750000000002" height="85.442259"></span></p>
</td>
</tr>
</tbody>
</table>

## 应用开发<a name="ZH-CN_TOPIC_0000002541326605"></a>

在HiSpark Studio AI中完成模型量化、转换之后，将模型导出并使用HiSpark.AI API完成应用开发。具体步骤如下。

1.  在“Deploy”页面下载转换好的Micro工程文件。

    **图 1**  下载micro工程文件<a name="fig6785143417386"></a>  
    ![](figures/下载micro工程文件.png "下载micro工程文件")

2.  具体API的用法请参考文档《HiSpark.AI API开发指南》

# Hi3322操作指南<a name="ZH-CN_TOPIC_0000002541286617"></a>

-   **[工程创建](#ZH-CN_TOPIC_0000002509766618)**  

-   **[模型导入](#ZH-CN_TOPIC_0000002509726612)**  

-   **[模型量化](#ZH-CN_TOPIC_0000002541326607)**  

-   **[模型转换](#ZH-CN_TOPIC_0000002541286619)**  

-   **[部署](#ZH-CN_TOPIC_0000002541425345)**  

-   **[模型调优](#ZH-CN_TOPIC_0000002509766620)**  

-   **[应用开发](#ZH-CN_TOPIC_0000002509726614)**  

## 工程创建<a name="ZH-CN_TOPIC_0000002509766618"></a>

-   **[前提条件](#ZH-CN_TOPIC_0000002517226682)**  

-   **[界面介绍](#ZH-CN_TOPIC_0000002517386758)**  

### 前提条件<a name="ZH-CN_TOPIC_0000002517226682"></a>

在工程创建前，请先获取Hi3322 SDK，并存放于本地Windows环境。SDK存放路径请勿带空格。

### 界面介绍<a name="ZH-CN_TOPIC_0000002517386758"></a>

进入HiSpark Studio AI单击“New Project”按钮进入新建工程页面。工程创建整体界面如[图1](#fig56341651183719)所示。

**图 1**  工程创建整体界面<a name="fig56341651183719"></a>  
![](figures/工程创建整体界面.png "工程创建整体界面")

工程创建的步骤如下所示：

1.  选择3322 SOC。
2.  输入工程创建配置参数。
3.  单击“Finished”按钮。

工程创建界面元素说明如[表1](#table10967339113911)所示。

**表 1**  工程创建元素说明

<a name="table10967339113911"></a>
<table><thead align="left"><tr id="row12968939143915"><th class="cellrowborder" valign="top" width="25.929999999999996%" id="mcps1.2.3.1.1"><p id="p11968123910394"><a name="p11968123910394"></a><a name="p11968123910394"></a>元素</p>
</th>
<th class="cellrowborder" valign="top" width="74.07000000000001%" id="mcps1.2.3.1.2"><p id="p189681039193916"><a name="p189681039193916"></a><a name="p189681039193916"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row996815390394"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p2096843973911"><a name="p2096843973911"></a><a name="p2096843973911"></a>SOC</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p896813918391"><a name="p896813918391"></a><a name="p896813918391"></a>SOC，请选择3322。</p>
</td>
</tr>
<tr id="row531311139408"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p13131613144016"><a name="p13131613144016"></a><a name="p13131613144016"></a>Board</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p1431391334019"><a name="p1431391334019"></a><a name="p1431391334019"></a>单板型号。默认选择3322。</p>
</td>
</tr>
<tr id="row1156834134020"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p105653419401"><a name="p105653419401"></a><a name="p105653419401"></a>Project Type</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p1745325154015"><a name="p1745325154015"></a><a name="p1745325154015"></a>工程类型，请选择Common Project。</p>
</td>
</tr>
<tr id="row879032710415"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p479042715413"><a name="p479042715413"></a><a name="p479042715413"></a>Project Name</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p579012714110"><a name="p579012714110"></a><a name="p579012714110"></a>用户自定义的工程名称。</p>
</td>
</tr>
<tr id="row842194124114"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p184211419412"><a name="p184211419412"></a><a name="p184211419412"></a>Project Path</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p17421441184118"><a name="p17421441184118"></a><a name="p17421441184118"></a>用户自定义的工程文件存放路径。</p>
</td>
</tr>
<tr id="row740213585413"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p154021058144117"><a name="p154021058144117"></a><a name="p154021058144117"></a>SDK</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p12402185814119"><a name="p12402185814119"></a><a name="p12402185814119"></a>Hi3322 SDK存放路径。</p>
</td>
</tr>
<tr id="row163064339427"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p230720336422"><a name="p230720336422"></a><a name="p230720336422"></a>Finished</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p15307033144219"><a name="p15307033144219"></a><a name="p15307033144219"></a>完成创建工程按钮。</p>
</td>
</tr>
<tr id="row154521348134217"><td class="cellrowborder" valign="top" width="25.929999999999996%" headers="mcps1.2.3.1.1 "><p id="p1845264854214"><a name="p1845264854214"></a><a name="p1845264854214"></a>Cancel</p>
</td>
<td class="cellrowborder" valign="top" width="74.07000000000001%" headers="mcps1.2.3.1.2 "><p id="p1345224813423"><a name="p1345224813423"></a><a name="p1345224813423"></a>取消创建工程按钮。</p>
</td>
</tr>
</tbody>
</table>

## 模型导入<a name="ZH-CN_TOPIC_0000002509726612"></a>

-   **[约束说明](#ZH-CN_TOPIC_0000002548827023)**  

-   **[前提条件](#ZH-CN_TOPIC_0000002517387150)**  

-   **[界面介绍](#ZH-CN_TOPIC_0000002517227232)**  

### 约束说明<a name="ZH-CN_TOPIC_0000002548827023"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>在进行模型导入前，请务必查看如下约束要求：
>Hi3322平台只支持导入ONNX以及pt、pth模型。ONNX模型支持训练后量化。pt、pth模型支持量化感知训练。

### 前提条件<a name="ZH-CN_TOPIC_0000002517387150"></a>

-   完成Linux服务器环境配置或者WSL环境配置。
-   连接Linux服务器或者WSL环境，若未完成连接，在单击“Import Model”按钮时会弹出Linux服务器或者WSL连接窗口。
-   若使用Linux服务器，将待处理的网络模型上传至Linux服务器。

### 界面介绍<a name="ZH-CN_TOPIC_0000002517227232"></a>

模型导入界面整体界面如[图1](#fig634318418485)所示。

**图 1**  模型导入界面<a name="fig634318418485"></a>  

![](figures/zh-cn_image_0000002532171656.png)

模型导入界面主要元素说明如[表1](#table31132274497)。

**表 1**  模型导入主要元素说明

<a name="table31132274497"></a>
<table><thead align="left"><tr id="row1511315272499"><th class="cellrowborder" valign="top" width="27.11%" id="mcps1.2.3.1.1"><p id="p81136270498"><a name="p81136270498"></a><a name="p81136270498"></a>元素</p>
</th>
<th class="cellrowborder" valign="top" width="72.89%" id="mcps1.2.3.1.2"><p id="p1211392719495"><a name="p1211392719495"></a><a name="p1211392719495"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row111372754913"><td class="cellrowborder" valign="top" width="27.11%" headers="mcps1.2.3.1.1 "><p id="p5114182711495"><a name="p5114182711495"></a><a name="p5114182711495"></a>Import Model</p>
</td>
<td class="cellrowborder" valign="top" width="72.89%" headers="mcps1.2.3.1.2 "><p id="p91141827124920"><a name="p91141827124920"></a><a name="p91141827124920"></a>模型导入按钮。完成导入后自动进入模型压缩界面。</p>
</td>
</tr>
<tr id="row19902119503"><td class="cellrowborder" valign="top" width="27.11%" headers="mcps1.2.3.1.1 "><p id="p1099114135019"><a name="p1099114135019"></a><a name="p1099114135019"></a>History Files</p>
</td>
<td class="cellrowborder" valign="top" width="72.89%" headers="mcps1.2.3.1.2 "><p id="p1799119185019"><a name="p1799119185019"></a><a name="p1799119185019"></a>模型导入历史列表。单击“Next”按钮进入对应历史模型的模型压缩界面。</p>
</td>
</tr>
</tbody>
</table>

## 模型量化<a name="ZH-CN_TOPIC_0000002541326607"></a>

-   **[约束说明](#ZH-CN_TOPIC_0000002547595389)**  

-   **[量化前提](#ZH-CN_TOPIC_0000002516115476)**  

-   **[界面介绍](#ZH-CN_TOPIC_0000002547515393)**  

### 约束说明<a name="ZH-CN_TOPIC_0000002547595389"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>在进行模型压缩前，请务必查看如下约束要求：
>-   支持原始框架类型为ONNX的模型训练后量化PTQ。
>-   支持原始框架类型为PyTorch（参数后缀pt或pth）的模型量化感知训练QAT。
>-   只支持单输出分类网络计算量化评估网络的准确率。
>-   量化感知训练只支持单输入单输出分类网络。

### 量化前提<a name="ZH-CN_TOPIC_0000002516115476"></a>

-   若使用Linux服务器，将待量化的模型、数据上传到服务器。数据格式见“[数据准备与环境搭建](#ZH-CN_TOPIC_0000002548828403)”。
-   若使用Linux服务器，并需要通过量化后仿真模型验证量化精度，请准备待量化数据；上传到服务器。数据格式见“[数据准备与环境搭建](#ZH-CN_TOPIC_0000002548828403)”。

### 界面介绍<a name="ZH-CN_TOPIC_0000002547515393"></a>

-   **[整体界面](#ZH-CN_TOPIC_0000002515955564)**  

-   **[量化参数配置界面](#ZH-CN_TOPIC_0000002547595391)**  

-   **[压缩历史显示界面](#ZH-CN_TOPIC_0000002515955566)**  

-   **[验证集精度分布直方图显示界面](#ZH-CN_TOPIC_0000002547595393)**  

#### 整体界面<a name="ZH-CN_TOPIC_0000002515955564"></a>

量化的整体界面如[图 量化整体界面](#fig16918198146)所示。

**图 1**  量化整体界面<a name="fig16918198146"></a>  

![](figures/zh-cn_image_0000002562049207.png)

模型量化整体界面如[图1](#fig16918198146)所示，主要包含三个部分：

1.  量化参数配置界面。
2.  压缩历史显示界面，显示所有压缩的网络及其精度指标。
3.  样本精度分布直方图显示界面，显示验证集的精度分布。

执行量化步骤如下：

1.  在量化参数界面配置量化参数。
2.  单击“Quantize”按钮。
3.  压缩历史显示界面查看压缩的结果。如果使能了量化精度验证，在该表格中显示量化精度验证评估结果。
4.  如果使能了量化精度验证，在样本精度分布直方图显示界面中查看验证集精度分布直方图。
5.  压缩历史显示界面中选择待转换的量化模型，单击“Next”按钮进入模型转换界面。

#### 量化参数配置界面<a name="ZH-CN_TOPIC_0000002547595391"></a>

-   **[训练后量化](#ZH-CN_TOPIC_0000002516115478)**  

-   **[量化感知训练](#ZH-CN_TOPIC_0000002547515395)**  

##### 训练后量化<a name="ZH-CN_TOPIC_0000002516115478"></a>

训练后量化量化参数配置窗口如[图 量化参数配置界面](#fig157591121132916)所示。

**图 1**  训练后量化参数配置界面<a name="fig157591121132916"></a>  

![](figures/zh-cn_image_0000002531848386.png)

参数解释如[表1](#table1769074411309)所示。

**表 1**  训练后量化参数配置界面参数

<a name="table1769074411309"></a>
<table><thead align="left"><tr id="row1769018444306"><th class="cellrowborder" valign="top" width="23.27%" id="mcps1.2.3.1.1"><p id="p769074418306"><a name="p769074418306"></a><a name="p769074418306"></a>参数</p>
</th>
<th class="cellrowborder" valign="top" width="76.73%" id="mcps1.2.3.1.2"><p id="p669044423018"><a name="p669044423018"></a><a name="p669044423018"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row13690144417303"><td class="cellrowborder" valign="top" width="23.27%" headers="mcps1.2.3.1.1 "><p id="p869054419309"><a name="p869054419309"></a><a name="p869054419309"></a>Quantized Data Type</p>
</td>
<td class="cellrowborder" valign="top" width="76.73%" headers="mcps1.2.3.1.2 "><p id="p18690204412306"><a name="p18690204412306"></a><a name="p18690204412306"></a>模型量化类型。当配置为int8时，转换后模型占用空间相对较小，推理速度相对较快，精度损失相对更大。当配置为int16时，转换后模型占用空间相对较大，推理速度相对较慢，精度损失相对小。</p>
</td>
</tr>
<tr id="row15497102073518"><td class="cellrowborder" valign="top" width="23.27%" headers="mcps1.2.3.1.1 "><p id="p1449712083518"><a name="p1449712083518"></a><a name="p1449712083518"></a>Layerwise Config</p>
</td>
<td class="cellrowborder" valign="top" width="76.73%" headers="mcps1.2.3.1.2 "><p id="p4498182013516"><a name="p4498182013516"></a><a name="p4498182013516"></a>打开逐层量化配置窗口。逐层量化类型配置窗口如<a href="#fig9513147163811">图2</a>所示。表格中各列的含义如下所示：</p>
<a name="ul8922547415"></a><a name="ul8922547415"></a><ul id="ul8922547415"><li>layer_name：层的名称。</li><li>layer_type：层的算子类型。</li><li>bit_num：用户在此列配置数据量化到的类型。</li></ul>
</td>
</tr>
<tr id="row176419249441"><td class="cellrowborder" valign="top" width="23.27%" headers="mcps1.2.3.1.1 "><p id="p10852456174819"><a name="p10852456174819"></a><a name="p10852456174819"></a>Calibration Inputs</p>
</td>
<td class="cellrowborder" valign="top" width="76.73%" headers="mcps1.2.3.1.2 "><p id="p36512474420"><a name="p36512474420"></a><a name="p36512474420"></a>用户在该表格中输入量化的校准数据。表格中各列的含义如下所示：</p>
<a name="ul1749181515018"></a><a name="ul1749181515018"></a><ul id="ul1749181515018"><li>Input Node：网络输入节点的名称。</li><li>Path：校准数据的目录。校准数据为npy格式。</li><li>Shape：网络输入张量的形状。</li><li>DataType：网络输入张量的类型。</li></ul>
</td>
</tr>
<tr id="row9587204511914"><td class="cellrowborder" valign="top" width="23.27%" headers="mcps1.2.3.1.1 "><p id="p135887451899"><a name="p135887451899"></a><a name="p135887451899"></a>validation</p>
</td>
<td class="cellrowborder" valign="top" width="76.73%" headers="mcps1.2.3.1.2 "><p id="p11588184515918"><a name="p11588184515918"></a><a name="p11588184515918"></a>使能验证开关。当开关打开时，验证数据集输入界面展开，如<a href="#fig11646193615123">图3</a>所示。</p>
</td>
</tr>
<tr id="row0675448181017"><td class="cellrowborder" valign="top" width="23.27%" headers="mcps1.2.3.1.1 "><p id="p1067614871016"><a name="p1067614871016"></a><a name="p1067614871016"></a>Validation Inputs</p>
</td>
<td class="cellrowborder" valign="top" width="76.73%" headers="mcps1.2.3.1.2 "><p id="p16676134871019"><a name="p16676134871019"></a><a name="p16676134871019"></a>用户在该表格中输入量化评估网络的验证数据集。表格中各列的含义如下所示：</p>
<a name="ul11478439133512"></a><a name="ul11478439133512"></a><ul id="ul11478439133512"><li>Input Node：网络输入节点的名称。</li><li>Path：验证数据的目录。验证数据为npy格式。</li></ul>
</td>
</tr>
<tr id="row7221131203619"><td class="cellrowborder" valign="top" width="23.27%" headers="mcps1.2.3.1.1 "><p id="p18229318368"><a name="p18229318368"></a><a name="p18229318368"></a>Validation Labels</p>
</td>
<td class="cellrowborder" valign="top" width="76.73%" headers="mcps1.2.3.1.2 "><p id="p4519123583915"><a name="p4519123583915"></a><a name="p4519123583915"></a>使能开关打开后，输入含分类真值标签的csv表格文件。</p>
</td>
</tr>
<tr id="row13146175924311"><td class="cellrowborder" valign="top" width="23.27%" headers="mcps1.2.3.1.1 "><p id="p51461759124316"><a name="p51461759124316"></a><a name="p51461759124316"></a>Advanced</p>
</td>
<td class="cellrowborder" valign="top" width="76.73%" headers="mcps1.2.3.1.2 "><p id="p15146159154312"><a name="p15146159154312"></a><a name="p15146159154312"></a>高级模式使能开关。当开关打开时，高级模式界面展开，如<a href="#fig232314275455">图4</a>所示。</p>
</td>
</tr>
<tr id="row5926956114512"><td class="cellrowborder" valign="top" width="23.27%" headers="mcps1.2.3.1.1 "><p id="p12926256184512"><a name="p12926256184512"></a><a name="p12926256184512"></a>Ascend Config</p>
</td>
<td class="cellrowborder" valign="top" width="76.73%" headers="mcps1.2.3.1.2 "><p id="p183943473491"><a name="p183943473491"></a><a name="p183943473491"></a>高级模式量化配置文件输入控件。在该输入控件中输入昇腾量化配置cfg文件。昇腾量化配置文件编写格式参见文档《AMCT模型压缩工具用户指南》。单击<a name="image194511735485"></a><a name="image194511735485"></a><span><img id="image194511735485" src="figures/zh-cn_image_0000002547595463.png"></span>可下载配置cfg文件模板。</p>
<p id="p1926175615456"><a name="p1926175615456"></a><a name="p1926175615456"></a>在使能Ascend Config时，BitNum和Layerwise Config配置不生效。</p>
</td>
</tr>
<tr id="row11454192012481"><td class="cellrowborder" valign="top" width="23.27%" headers="mcps1.2.3.1.1 "><p id="p2045416206486"><a name="p2045416206486"></a><a name="p2045416206486"></a>Quantize</p>
</td>
<td class="cellrowborder" valign="top" width="76.73%" headers="mcps1.2.3.1.2 "><p id="p8454182044811"><a name="p8454182044811"></a><a name="p8454182044811"></a>开始量化按钮。</p>
</td>
</tr>
</tbody>
</table>

**图 2**  逐层量化类型配置界面<a name="fig9513147163811"></a>  
![](figures/逐层量化类型配置界面.png "逐层量化类型配置界面")

**图 3**  验证集输入界面<a name="fig11646193615123"></a>  
![](figures/验证集输入界面.png "验证集输入界面")

**图 4**  高级模式界面<a name="fig232314275455"></a>  
![](figures/高级模式界面.png "高级模式界面")

##### 量化感知训练<a name="ZH-CN_TOPIC_0000002547515395"></a>

量化感知训练参数配置窗口如[图1](#fig189812612211)所示。

**图 1**  量化感知训练参数配置界面<a name="fig189812612211"></a>  
![](figures/量化感知训练参数配置界面.png "量化感知训练参数配置界面")

参数解释如[表1](#table1769074411309)所示。

**表 1**  量化感知训练参数配置界面参数

<a name="table1769074411309"></a>
<table><thead align="left"><tr id="row1769018444306"><th class="cellrowborder" valign="top" width="22.45%" id="mcps1.2.3.1.1"><p id="p769074418306"><a name="p769074418306"></a><a name="p769074418306"></a>参数</p>
</th>
<th class="cellrowborder" valign="top" width="77.55%" id="mcps1.2.3.1.2"><p id="p669044423018"><a name="p669044423018"></a><a name="p669044423018"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row13690144417303"><td class="cellrowborder" valign="top" width="22.45%" headers="mcps1.2.3.1.1 "><p id="p869054419309"><a name="p869054419309"></a><a name="p869054419309"></a>Network Struction</p>
</td>
<td class="cellrowborder" valign="top" width="77.55%" headers="mcps1.2.3.1.2 "><p id="p18690204412306"><a name="p18690204412306"></a><a name="p18690204412306"></a>网络结构输入路径。网络结构文件为一个python文件，里面含有网络结构的定义。在定义网络结构时，请满足如下约束：</p>
<a name="ul15198342105114"></a><a name="ul15198342105114"></a><ul id="ul15198342105114"><li>网络结构类的名称固定为NNModel</li><li>当前只支持单输入和单输出网络，因此forward函数的输入输出类型为torch.Tensor</li><li>构造函数不包含除self外的其他入参，如果有其他入参请配置默认值</li></ul>
<p id="p492711845215"><a name="p492711845215"></a><a name="p492711845215"></a>以下为LeNet5网络结构的参考实现：</p>
<pre class="screen" id="screen167021785119"><a name="screen167021785119"></a><a name="screen167021785119"></a>class NNModel(nn.Module):
    def __init__(self) -&gt; None:
        """Initialize network layers and components."""
        super(NNModel, self).__init__()

        self.conv1 = nn.Conv2d(1, 8, kernel_size=(5, 5), padding=2)
        self.relu1 = nn.ReLU()
        self.maxpool1 = nn.MaxPool2d(kernel_size=(2, 2), stride=(2, 2), padding=(0, 0), dilation=1, ceil_mode=False)

        self.conv2 = nn.Conv2d(8, 16, kernel_size=(5, 5), padding=2)
        self.relu2 = nn.ReLU()
        self.maxpool2 = nn.MaxPool2d(kernel_size=(3, 3), stride=(3, 3), padding=(0, 0), dilation=1, ceil_mode=False)

        self.fc = torch.nn.Linear(256, 10, bias=True)

    def forward(self, img):
        """
        Forward pass of the network.

        Args:
            x (torch.Tensor): Input tensor with shape (batch_size, 1, 28, 28)

        Returns:
            torch.Tensor: Output logits with shape (batch_size, 10)
        """
        out = self.conv1(img)
        out = self.relu1(out)
        out = self.maxpool1(out)
        out = self.conv2(out)

        out = self.relu2(out)
        out = self.maxpool2(out)
        out = out.reshape(-1, 256)
        out = self.fc(out)
        return out</pre>
</td>
</tr>
<tr id="row15497102073518"><td class="cellrowborder" valign="top" width="22.45%" headers="mcps1.2.3.1.1 "><p id="p1449712083518"><a name="p1449712083518"></a><a name="p1449712083518"></a>Input</p>
</td>
<td class="cellrowborder" valign="top" width="77.55%" headers="mcps1.2.3.1.2 "><p id="p1839513816304"><a name="p1839513816304"></a><a name="p1839513816304"></a>Training Dataset：训练集输入数据目录。训练集输入数据为npy格式。</p>
<p id="p854993813565"><a name="p854993813565"></a><a name="p854993813565"></a>Validation Dataset：验证集输入数据目录。目录中存放和模型输入匹配的npy文件数据。若模型有多个输入，同一个训练样本的多个输入npy文件文件名必须保持一致。</p>
</td>
</tr>
<tr id="row2058969135718"><td class="cellrowborder" valign="top" width="22.45%" headers="mcps1.2.3.1.1 "><p id="p758917910579"><a name="p758917910579"></a><a name="p758917910579"></a>Label</p>
</td>
<td class="cellrowborder" valign="top" width="77.55%" headers="mcps1.2.3.1.2 "><p id="p165894995715"><a name="p165894995715"></a><a name="p165894995715"></a>Training Dataset：训练集真值csv文件。</p>
<p id="p168861134125719"><a name="p168861134125719"></a><a name="p168861134125719"></a>Validation Dataset：验证集真值csv文件。</p>
</td>
</tr>
<tr id="row8596131613118"><td class="cellrowborder" valign="top" width="22.45%" headers="mcps1.2.3.1.1 "><p id="p137301940583"><a name="p137301940583"></a><a name="p137301940583"></a>Epoch Num</p>
</td>
<td class="cellrowborder" valign="top" width="77.55%" headers="mcps1.2.3.1.2 "><p id="p1973016401183"><a name="p1973016401183"></a><a name="p1973016401183"></a>量化感知训练的Epoch数量。</p>
</td>
</tr>
<tr id="row1753471018329"><td class="cellrowborder" valign="top" width="22.45%" headers="mcps1.2.3.1.1 "><p id="p0729240782"><a name="p0729240782"></a><a name="p0729240782"></a>Batch Size</p>
</td>
<td class="cellrowborder" valign="top" width="77.55%" headers="mcps1.2.3.1.2 "><p id="p117285401688"><a name="p117285401688"></a><a name="p117285401688"></a>量化感知训练的Batch Size</p>
</td>
</tr>
<tr id="row4866618133218"><td class="cellrowborder" valign="top" width="22.45%" headers="mcps1.2.3.1.1 "><p id="p67281140986"><a name="p67281140986"></a><a name="p67281140986"></a>Learning Rate</p>
</td>
<td class="cellrowborder" valign="top" width="77.55%" headers="mcps1.2.3.1.2 "><p id="p1172744018818"><a name="p1172744018818"></a><a name="p1172744018818"></a>量化感知训练时的学习率。</p>
</td>
</tr>
<tr id="row769312712328"><td class="cellrowborder" valign="top" width="22.45%" headers="mcps1.2.3.1.1 "><p id="p1838914591598"><a name="p1838914591598"></a><a name="p1838914591598"></a>Layerwise Config</p>
</td>
<td class="cellrowborder" valign="top" width="77.55%" headers="mcps1.2.3.1.2 "><p id="p4498182013516"><a name="p4498182013516"></a><a name="p4498182013516"></a>打开逐层量化配置窗口。逐层量化类型配置窗口如<a href="#fig89361036161014">图2</a>所示。表格中各列的含义如下所示：</p>
<a name="ul8922547415"></a><a name="ul8922547415"></a><ul id="ul8922547415"><li>layer_name：层的名称。</li><li>layer_type：层的算子类型。</li><li>bit_num：用户在此列配置数据量化到的类型。</li></ul>
</td>
</tr>
<tr id="row19016324323"><td class="cellrowborder" valign="top" width="22.45%" headers="mcps1.2.3.1.1 "><p id="p51461759124316"><a name="p51461759124316"></a><a name="p51461759124316"></a>Advanced Settings</p>
</td>
<td class="cellrowborder" valign="top" width="77.55%" headers="mcps1.2.3.1.2 "><p id="p15146159154312"><a name="p15146159154312"></a><a name="p15146159154312"></a>高级模式使能开关。当开关打开时，高级模式界面展开，如<a href="#fig57442431416">图3</a>所示。</p>
</td>
</tr>
<tr id="row121991245201317"><td class="cellrowborder" valign="top" width="22.45%" headers="mcps1.2.3.1.1 "><p id="p12926256184512"><a name="p12926256184512"></a><a name="p12926256184512"></a>Ascend Config</p>
</td>
<td class="cellrowborder" valign="top" width="77.55%" headers="mcps1.2.3.1.2 "><p id="p183943473491"><a name="p183943473491"></a><a name="p183943473491"></a>高级模式量化配置文件输入控件。在该输入控件中输入昇腾量化配置cfg文件。昇腾量化配置文件编写格式参见文档《AMCT模型压缩工具用户指南》。单击<a name="image194511735485"></a><a name="image194511735485"></a><span><img id="image194511735485" src="figures/zh-cn_image_0000002562055691.png"></span>可下载配置cfg文件模板。</p>
<p id="p1926175615456"><a name="p1926175615456"></a><a name="p1926175615456"></a>在使能Ascend Config时，Layerwise Config配置不生效。</p>
</td>
</tr>
<tr id="row592812546498"><td class="cellrowborder" valign="top" width="22.45%" headers="mcps1.2.3.1.1 "><p id="p2045416206486"><a name="p2045416206486"></a><a name="p2045416206486"></a>Quantize</p>
</td>
<td class="cellrowborder" valign="top" width="77.55%" headers="mcps1.2.3.1.2 "><p id="p8454182044811"><a name="p8454182044811"></a><a name="p8454182044811"></a>开始量化按钮。</p>
</td>
</tr>
</tbody>
</table>

**图 2**  量化感知训练逐层量化类型配置界面<a name="fig89361036161014"></a>  
![](figures/量化感知训练逐层量化类型配置界面.png "量化感知训练逐层量化类型配置界面")

**图 3**  高级模式界面<a name="fig57442431416"></a>  
![](figures/高级模式界面-0.png "高级模式界面-0")

#### 压缩历史显示界面<a name="ZH-CN_TOPIC_0000002515955566"></a>

压缩历史显示窗口如[图1](#fig17766212211)所示。

**图 1**  压缩历史显示界面<a name="fig17766212211"></a>  
![](figures/压缩历史显示界面.png "压缩历史显示界面")

该界面以表格的方式显示历史压缩的结果。表头解释如[表1](#table17914154610556)所示。

**表 1**  压缩历史

<a name="table17914154610556"></a>
<table><thead align="left"><tr id="row691494685515"><th class="cellrowborder" valign="top" width="20.91%" id="mcps1.2.3.1.1"><p id="p189148465551"><a name="p189148465551"></a><a name="p189148465551"></a>项目</p>
</th>
<th class="cellrowborder" valign="top" width="79.09%" id="mcps1.2.3.1.2"><p id="p1391434685514"><a name="p1391434685514"></a><a name="p1391434685514"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row09141746195518"><td class="cellrowborder" valign="top" width="20.91%" headers="mcps1.2.3.1.1 "><p id="p191416466557"><a name="p191416466557"></a><a name="p191416466557"></a>Trail ID</p>
</td>
<td class="cellrowborder" valign="top" width="79.09%" headers="mcps1.2.3.1.2 "><p id="p03571347185611"><a name="p03571347185611"></a><a name="p03571347185611"></a>网络压缩结果的序号。</p>
</td>
</tr>
<tr id="row926611014579"><td class="cellrowborder" valign="top" width="20.91%" headers="mcps1.2.3.1.1 "><p id="p52661011575"><a name="p52661011575"></a><a name="p52661011575"></a>Model Name</p>
</td>
<td class="cellrowborder" valign="top" width="79.09%" headers="mcps1.2.3.1.2 "><p id="p8266709578"><a name="p8266709578"></a><a name="p8266709578"></a>网络的名称，以及修改时间。</p>
</td>
</tr>
<tr id="row499271165719"><td class="cellrowborder" valign="top" width="20.91%" headers="mcps1.2.3.1.1 "><p id="p39921311125712"><a name="p39921311125712"></a><a name="p39921311125712"></a>Accuracy</p>
</td>
<td class="cellrowborder" valign="top" width="79.09%" headers="mcps1.2.3.1.2 "><p id="p16992191195715"><a name="p16992191195715"></a><a name="p16992191195715"></a>表示分类结果准确率，使用标签真值计算。计算公式如下，其中<a name="image642362211326"></a><a name="image642362211326"></a><span><img class="mathml" id="image642362211326" src="figures/zh-cn_formulaimage_0000002549112889.png" width="28.927500000000002" height="16.902305000000002"></span>表示分类正确的样本数量，<a name="image1097645123220"></a><a name="image1097645123220"></a><span><img class="mathml" id="image1097645123220" src="figures/zh-cn_formulaimage_0000002549153223.png" width="28.927500000000002" height="21.130508000000003"></span>表示样本的总数量。</p>
<p id="p17330110153017"><a name="p17330110153017"></a><a name="p17330110153017"></a><a name="image9860115919319"></a><a name="image9860115919319"></a><span><img class="mathml" id="image9860115919319" src="figures/zh-cn_formulaimage_0000002517553012.png" width="200.4975" height="54.333293000000005"></span></p>
<p id="p128001110182411"><a name="p128001110182411"></a><a name="p128001110182411"></a>准确率表示格式：</p>
<pre class="screen" id="screen4381153942419"><a name="screen4381153942419"></a><a name="screen4381153942419"></a>{量化模型准确率}({量化模型与原始浮点模型准确率对比})</pre>
<a name="ul614475942616"></a><a name="ul614475942616"></a><ul id="ul614475942616"><li><a name="image10256111862719"></a><a name="image10256111862719"></a><span><img id="image10256111862719" src="figures/zh-cn_image_0000002560885588.png"></span>：表示量化后模型的准确率为0.99，与原始浮点网络模型相比上升0.01。</li><li><a name="image122892229115"></a><a name="image122892229115"></a><span><img id="image122892229115" src="figures/zh-cn_image_0000002591683695.png" width="91.77000000000001" height="30.270800000000005"></span>：表示量化后模型的准确率为0.95，与原始浮点网络模型相比下降0.01。</li></ul>
</td>
</tr>
<tr id="row844131695717"><td class="cellrowborder" valign="top" width="20.91%" headers="mcps1.2.3.1.1 "><p id="p184471665720"><a name="p184471665720"></a><a name="p184471665720"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" width="79.09%" headers="mcps1.2.3.1.2 "><p id="p54531149131416"><a name="p54531149131416"></a><a name="p54531149131416"></a>平均余弦相似度，计算公式如下，其中<a name="image15484124391614"></a><a name="image15484124391614"></a><span><img class="mathml" id="image15484124391614" src="figures/zh-cn_formulaimage_0000002549142017.png" width="19.042009" height="34.772318000000006"></span>表示量化评估网络的输出，<a name="image634019531710"></a><a name="image634019531710"></a><span><img class="mathml" id="image634019531710" src="figures/zh-cn_formulaimage_0000002517542344.png" width="19.666444000000002" height="30.782318000000004"></span>表示原始浮点网络的输出，<a name="image8788135318194"></a><a name="image8788135318194"></a><span><img class="mathml" id="image8788135318194" src="figures/zh-cn_formulaimage_0000002549102503.png" width="19.191501000000002" height="28.787318000000003"></span>表示验证集样本的数量。</p>
<p id="p8151115911493"><a name="p8151115911493"></a><a name="p8151115911493"></a><a name="image196582429196"></a><a name="image196582429196"></a><span><img class="mathml" id="image196582429196" src="figures/zh-cn_formulaimage_0000002517701808.png" width="192.5175" height="57.95501600000001"></span></p>
</td>
</tr>
<tr id="row1676132014572"><td class="cellrowborder" valign="top" width="20.91%" headers="mcps1.2.3.1.1 "><p id="p19676520145712"><a name="p19676520145712"></a><a name="p19676520145712"></a>MSE</p>
</td>
<td class="cellrowborder" valign="top" width="79.09%" headers="mcps1.2.3.1.2 "><p id="p189491228195019"><a name="p189491228195019"></a><a name="p189491228195019"></a>均方误差，计算公式如下，其中<a name="image116392033152317"></a><a name="image116392033152317"></a><span><img class="mathml" id="image116392033152317" src="figures/zh-cn_formulaimage_0000002549148179.png" width="18.495645" height="33.774818"></span>表示量化评估网络的输出，<a name="image16391333182311"></a><a name="image16391333182311"></a><span><img class="mathml" id="image16391333182311" src="figures/zh-cn_formulaimage_0000002549108183.png" width="18.391772" height="28.787318000000003"></span>表示原始浮点网络的输出，<a name="image1563903322316"></a><a name="image1563903322316"></a><span><img class="mathml" id="image1563903322316" src="figures/zh-cn_formulaimage_0000002549148183.png" width="19.191501000000002" height="28.787318000000003"></span>表示验证集样本的数量。</p>
<p id="p182633519237"><a name="p182633519237"></a><a name="p182633519237"></a><a name="image196434716242"></a><a name="image196434716242"></a><span><img class="mathml" id="image196434716242" src="figures/zh-cn_formulaimage_0000002517548816.png" width="126.6825" height="48.913277"></span></p>
</td>
</tr>
<tr id="row14206152325711"><td class="cellrowborder" valign="top" width="20.91%" headers="mcps1.2.3.1.1 "><p id="p19206152355710"><a name="p19206152355710"></a><a name="p19206152355710"></a>Operation</p>
</td>
<td class="cellrowborder" valign="top" width="79.09%" headers="mcps1.2.3.1.2 "><p id="p1220642335713"><a name="p1220642335713"></a><a name="p1220642335713"></a>操作按钮：</p>
<a name="ul52775178594"></a><a name="ul52775178594"></a><ul id="ul52775178594"><li><a name="image14822121019112"></a><a name="image14822121019112"></a><span><img id="image14822121019112" src="figures/zh-cn_image_0000002562133181.png"></span>：下载压缩结果。下载的压缩包中包含：<a name="ul1285118481118"></a><a name="ul1285118481118"></a><ul id="ul1285118481118"><li>{模型名称}_deploy_model.onnx：量化部署模型，即量化后的可在昇腾 AI 处理器部署的模型文件。</li><li>{模型名称}_fake_quant_model.onnx：量化仿真模型，即量化后的可在 ONNX执行框架ONNX Runtime进行精度仿真的模型文件。</li><li>{模型名称}_quant.json：<span>融合信息文件。</span></li><li>precision_output.csv：验证集各个样本的精度信息。</li></ul>
</li><li><a name="image1746324617"></a><a name="image1746324617"></a><span><img id="image1746324617" src="figures/zh-cn_image_0000002531053268.png"></span>：删除当前记录。</li><li><a name="image1559016359114"></a><a name="image1559016359114"></a><span><img id="image1559016359114" src="figures/zh-cn_image_0000002531173168.png"></span>：跳转到模型转换页面，在模型转换页面对当前行对应的压缩网络进行模型转换。</li></ul>
</td>
</tr>
</tbody>
</table>

#### 验证集精度分布直方图显示界面<a name="ZH-CN_TOPIC_0000002547595393"></a>

验证集精度分布直方图显示界面如[图 验证集精度分布直方图显示界面](#fig125132017185218)所示。该窗口显示验证集的余弦相似度的分布图，横轴为余弦相似度，纵轴为验证集样本的百分比。

**图 1**  验证集精度分布直方图显示界面<a name="fig125132017185218"></a>  
![](figures/验证集精度分布直方图显示界面-1.png "验证集精度分布直方图显示界面-1")

## 模型转换<a name="ZH-CN_TOPIC_0000002541286619"></a>

-   **[整体界面](#ZH-CN_TOPIC_0000002548567951)**  

-   **[模型转换参数配置界面](#ZH-CN_TOPIC_0000002517088070)**  

-   **[转换历史显示界面](#ZH-CN_TOPIC_0000002548458355)**  

-   **[转换结果显示界面](#ZH-CN_TOPIC_0000002517098478)**  

### 整体界面<a name="ZH-CN_TOPIC_0000002548567951"></a>

**图 1**  模型转换整体界面<a name="fig191831926161420"></a>  
![](figures/模型转换整体界面-2.png "模型转换整体界面-2")

用户在模型转换界面将模型转换成昇腾NPU执行的离线模型。模型转换整体界面如[图1](#fig191831926161420)所示。主要包含三个部分：

1.  模型转换参数配置界面。
2.  转换历史显示界面，显示所有转换的网络及其相关信息。
3.  转换结果显示界面，显示转换后模型的大小。

模型转换步骤如下：

1.  在模型转换参数配置界面配置转换参数。
2.  单击“Convert”按钮。
3.  转换历史显示界面查看转换的结果。
4.  转换结果显示界面查看转换后模型的大小。
5.  转换历史显示界面选择待评估的模型，单击“Next”按钮进入部署界面。

### 模型转换参数配置界面<a name="ZH-CN_TOPIC_0000002517088070"></a>

模型转换参数配置界面如[图1](#fig03721841143618)所示。

**图 1**  模型转换参数配置界面<a name="fig03721841143618"></a>  
![](figures/模型转换参数配置界面.png "模型转换参数配置界面")

参数解释如[表1](#table82721173715)所示。

**表 1**  模型转换参数配置界面参数

<a name="table82721173715"></a>
<table><thead align="left"><tr id="row17271611113720"><th class="cellrowborder" valign="top" width="20.05%" id="mcps1.2.3.1.1"><p id="p17271411203716"><a name="p17271411203716"></a><a name="p17271411203716"></a>参数</p>
</th>
<th class="cellrowborder" valign="top" width="79.95%" id="mcps1.2.3.1.2"><p id="p12273117378"><a name="p12273117378"></a><a name="p12273117378"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row327311203719"><td class="cellrowborder" valign="top" width="20.05%" headers="mcps1.2.3.1.1 "><p id="p1827311123718"><a name="p1827311123718"></a><a name="p1827311123718"></a>Input</p>
</td>
<td class="cellrowborder" valign="top" width="79.95%" headers="mcps1.2.3.1.2 "><p id="p1427161118372"><a name="p1427161118372"></a><a name="p1427161118372"></a>该标签显示为模型的输入节点名称。包含两个控件：</p>
<a name="ol960313528382"></a><a name="ol960313528382"></a><ol id="ol960313528382"><li>输入节点张量形状。</li><li>输入节点数据类型。转换后的网络接收该数据类型的数据。</li></ol>
</td>
</tr>
<tr id="row873460174210"><td class="cellrowborder" valign="top" width="20.05%" headers="mcps1.2.3.1.1 "><p id="p673414044211"><a name="p673414044211"></a><a name="p673414044211"></a>Output Type</p>
</td>
<td class="cellrowborder" valign="top" width="79.95%" headers="mcps1.2.3.1.2 "><p id="p127359044211"><a name="p127359044211"></a><a name="p127359044211"></a>输出节点数据类型。转换后的网络输出该数据类型的输出。</p>
</td>
</tr>
<tr id="row2310111181"><td class="cellrowborder" valign="top" width="20.05%" headers="mcps1.2.3.1.1 "><p id="p1631019117814"><a name="p1631019117814"></a><a name="p1631019117814"></a>Advanced Options</p>
</td>
<td class="cellrowborder" valign="top" width="79.95%" headers="mcps1.2.3.1.2 "><p id="p15146159154312"><a name="p15146159154312"></a><a name="p15146159154312"></a>高级模式使能开关。当开关打开时，高级模式界面展开。</p>
</td>
</tr>
<tr id="row163268581816"><td class="cellrowborder" valign="top" width="20.05%" headers="mcps1.2.3.1.1 "><p id="p183261589815"><a name="p183261589815"></a><a name="p183261589815"></a>Additional Arguments</p>
</td>
<td class="cellrowborder" valign="top" width="79.95%" headers="mcps1.2.3.1.2 "><p id="p1232625818817"><a name="p1232625818817"></a><a name="p1232625818817"></a>扩展参数输入框。模型转换界面不支持配置，但是ATC工具支持的参数均可通过此选项进行扩展。在该输入框中用户根据实际情况输入ATC工具可用的参数。多个参数使用空格分隔。详细参数请参见《ATC离线模型编译工具用户指南》。</p>
</td>
</tr>
<tr id="row651411425113"><td class="cellrowborder" valign="top" width="20.05%" headers="mcps1.2.3.1.1 "><p id="p051581495112"><a name="p051581495112"></a><a name="p051581495112"></a>Convert</p>
</td>
<td class="cellrowborder" valign="top" width="79.95%" headers="mcps1.2.3.1.2 "><p id="p1251501445113"><a name="p1251501445113"></a><a name="p1251501445113"></a>开始转换按钮。</p>
</td>
</tr>
</tbody>
</table>

### 转换历史显示界面<a name="ZH-CN_TOPIC_0000002548458355"></a>

转换历史显示界面如[图1](#fig26931136531)所示。

**图 1**  转换历史显示界面<a name="fig26931136531"></a>  
![](figures/转换历史显示界面.png "转换历史显示界面")

该界面以表格的方式显示历史转换的结果。表头说明如[表1](#table14941640115315)所示。

**表 1**  转换历史

<a name="table14941640115315"></a>
<table><thead align="left"><tr id="row34941040165314"><th class="cellrowborder" valign="top" width="23.23%" id="mcps1.2.3.1.1"><p id="p11494164055310"><a name="p11494164055310"></a><a name="p11494164055310"></a>项目</p>
</th>
<th class="cellrowborder" valign="top" width="76.77000000000001%" id="mcps1.2.3.1.2"><p id="p18494194015310"><a name="p18494194015310"></a><a name="p18494194015310"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row749464085313"><td class="cellrowborder" valign="top" width="23.23%" headers="mcps1.2.3.1.1 "><p id="p191416466557"><a name="p191416466557"></a><a name="p191416466557"></a>Trail ID</p>
</td>
<td class="cellrowborder" valign="top" width="76.77000000000001%" headers="mcps1.2.3.1.2 "><p id="p03571347185611"><a name="p03571347185611"></a><a name="p03571347185611"></a>网络转换结果的序号。</p>
</td>
</tr>
<tr id="row11343161545419"><td class="cellrowborder" valign="top" width="23.23%" headers="mcps1.2.3.1.1 "><p id="p52661011575"><a name="p52661011575"></a><a name="p52661011575"></a>Model Name</p>
</td>
<td class="cellrowborder" valign="top" width="76.77000000000001%" headers="mcps1.2.3.1.2 "><p id="p8266709578"><a name="p8266709578"></a><a name="p8266709578"></a>网络的名称，以及修改时间。</p>
</td>
</tr>
<tr id="row149818163543"><td class="cellrowborder" valign="top" width="23.23%" headers="mcps1.2.3.1.1 "><p id="p39921311125712"><a name="p39921311125712"></a><a name="p39921311125712"></a>Accuracy</p>
</td>
<td class="cellrowborder" valign="top" width="76.77000000000001%" headers="mcps1.2.3.1.2 "><p id="p16992191195715"><a name="p16992191195715"></a><a name="p16992191195715"></a>表示分类结果准确率，使用标签真值计算。计算公式如下，其中<a name="image642362211326"></a><a name="image642362211326"></a><span><img class="mathml" id="image642362211326" src="figures/zh-cn_formulaimage_0000002517553946.png" width="50.734313" height="29.660064"></span>表示分类正确的样本数量，<a name="image1097645123220"></a><a name="image1097645123220"></a><span><img class="mathml" id="image1097645123220" src="figures/zh-cn_formulaimage_0000002549113729.png" width="40.56367" height="29.660064"></span>表示样本的总数量。</p>
<p id="p17330110153017"><a name="p17330110153017"></a><a name="p17330110153017"></a><a name="image9860115919319"></a><a name="image9860115919319"></a><span><img class="mathml" id="image9860115919319" src="figures/zh-cn_formulaimage_0000002517553950.png" width="242.3925" height="65.68643900000001"></span></p>
</td>
</tr>
<tr id="row191011317145410"><td class="cellrowborder" valign="top" width="23.23%" headers="mcps1.2.3.1.1 "><p id="p184471665720"><a name="p184471665720"></a><a name="p184471665720"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" width="76.77000000000001%" headers="mcps1.2.3.1.2 "><p id="p54531149131416"><a name="p54531149131416"></a><a name="p54531149131416"></a>平均余弦相似度，计算公式如下，其中<a name="image15484124391614"></a><a name="image15484124391614"></a><span><img class="mathml" id="image15484124391614" src="figures/zh-cn_formulaimage_0000002549113735.png" width="17.881185000000002" height="32.652564"></span>表示量化评估网络的输出，<a name="image634019531710"></a><a name="image634019531710"></a><span><img class="mathml" id="image634019531710" src="figures/zh-cn_formulaimage_0000002517553958.png" width="18.312238" height="28.662564"></span>表示原始浮点网络的输出，<a name="image8788135318194"></a><a name="image8788135318194"></a><span><img class="mathml" id="image8788135318194" src="figures/zh-cn_formulaimage_0000002549113739.png" width="21.103243000000003" height="31.655064"></span>表示验证集样本的数量。</p>
<p id="p8151115911493"><a name="p8151115911493"></a><a name="p8151115911493"></a><a name="image196582429196"></a><a name="image196582429196"></a><span><img class="mathml" id="image196582429196" src="figures/zh-cn_formulaimage_0000002517553960.png" width="243.39000000000001" height="73.278744"></span></p>
</td>
</tr>
<tr id="row11552161735412"><td class="cellrowborder" valign="top" width="23.23%" headers="mcps1.2.3.1.1 "><p id="p19676520145712"><a name="p19676520145712"></a><a name="p19676520145712"></a>MSE</p>
</td>
<td class="cellrowborder" valign="top" width="76.77000000000001%" headers="mcps1.2.3.1.2 "><p id="p189491228195019"><a name="p189491228195019"></a><a name="p189491228195019"></a>均方误差，计算公式如下，其中<a name="image116392033152317"></a><a name="image116392033152317"></a><span><img class="mathml" id="image116392033152317" src="figures/zh-cn_formulaimage_0000002549113741.png" width="20.066109" height="36.642564"></span>表示量化评估网络的输出，<a name="image16391333182311"></a><a name="image16391333182311"></a><span><img class="mathml" id="image16391333182311" src="figures/zh-cn_formulaimage_0000002517553964.png" width="18.312238" height="28.662564"></span>表示原始浮点网络的输出，<a name="image1563903322316"></a><a name="image1563903322316"></a><span><img class="mathml" id="image1563903322316" src="figures/zh-cn_formulaimage_0000002549113745.png" width="20.438376" height="30.657564"></span>表示验证集样本的数量。</p>
<p id="p182633519237"><a name="p182633519237"></a><a name="p182633519237"></a><a name="image196434716242"></a><a name="image196434716242"></a><span><img class="mathml" id="image196434716242" src="figures/zh-cn_formulaimage_0000002517553966.png" width="192.5175" height="74.338488"></span></p>
</td>
</tr>
<tr id="row7716154415234"><td class="cellrowborder" valign="top" width="23.23%" headers="mcps1.2.3.1.1 "><p id="p107169444233"><a name="p107169444233"></a><a name="p107169444233"></a>Model Size(KB)</p>
</td>
<td class="cellrowborder" valign="top" width="76.77000000000001%" headers="mcps1.2.3.1.2 "><p id="p12716744142315"><a name="p12716744142315"></a><a name="p12716744142315"></a>转换后在昇腾AI处理器运行的离线模型文件大小。</p>
</td>
</tr>
<tr id="row1644874782313"><td class="cellrowborder" valign="top" width="23.23%" headers="mcps1.2.3.1.1 "><p id="p10448194716236"><a name="p10448194716236"></a><a name="p10448194716236"></a>Dbg Size(KB)</p>
</td>
<td class="cellrowborder" valign="top" width="76.77000000000001%" headers="mcps1.2.3.1.2 "><p id="p1744820473237"><a name="p1744820473237"></a><a name="p1744820473237"></a>图调试信息文件大小。</p>
</td>
</tr>
<tr id="row073913020562"><td class="cellrowborder" valign="top" width="23.23%" headers="mcps1.2.3.1.1 "><p id="p127392030185611"><a name="p127392030185611"></a><a name="p127392030185611"></a>Operation</p>
</td>
<td class="cellrowborder" valign="top" width="76.77000000000001%" headers="mcps1.2.3.1.2 "><p id="p1220642335713"><a name="p1220642335713"></a><a name="p1220642335713"></a>操作按钮：</p>
<a name="ul52775178594"></a><a name="ul52775178594"></a><ul id="ul52775178594"><li><a name="image14822121019112"></a><a name="image14822121019112"></a><span><img id="image14822121019112" src="figures/zh-cn_image_0000002531053258.png"></span>：下载模型转换结果。下载的压缩包中包含：<a name="ul1285118481118"></a><a name="ul1285118481118"></a><ul id="ul1285118481118"><li>convert.exeom：转换后在昇腾AI处理器运行的离线模型。</li><li>convert.dbg：图调试信息文件。</li></ul>
</li><li><a name="image1746324617"></a><a name="image1746324617"></a><span><img id="image1746324617" src="figures/zh-cn_image_0000002562013199.png"></span>：删除当前记录。</li><li><a name="image1559016359114"></a><a name="image1559016359114"></a><span><img id="image1559016359114" src="figures/zh-cn_image_0000002531053216.png"></span>：跳转到部署页面。</li></ul>
</td>
</tr>
</tbody>
</table>

### 转换结果显示界面<a name="ZH-CN_TOPIC_0000002517098478"></a>

转换结果显示界面如[图1](#fig1526210123512)所示。该界面以柱状图的形式显示转换后模型以及图调试信息文件的大小。

**图 1**  转换结果显示界面<a name="fig1526210123512"></a>  
![](figures/转换结果显示界面.png "转换结果显示界面")

## 部署<a name="ZH-CN_TOPIC_0000002541425345"></a>

部署界面如[图1](#fig789910546818)所示。

**图 1**  部署界面<a name="fig789910546818"></a>  
![](figures/部署界面.png "部署界面")

该界面主要包含Model currently selected、Build and Burn、Download Results三个部分。Build and Burn中的主要控件如[表1 Build and Burn主要控件说明](#table105181481495)所示。

**表 1**  Build and Burn主要控件说明

<a name="table105181481495"></a>
<table><thead align="left"><tr id="row185184483918"><th class="cellrowborder" valign="top" width="38.37%" id="mcps1.2.3.1.1"><p id="p951814813919"><a name="p951814813919"></a><a name="p951814813919"></a>项目</p>
</th>
<th class="cellrowborder" valign="top" width="61.629999999999995%" id="mcps1.2.3.1.2"><p id="p1851824815918"><a name="p1851824815918"></a><a name="p1851824815918"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row5518134815917"><td class="cellrowborder" valign="top" width="38.37%" headers="mcps1.2.3.1.1 "><p id="p1251915481893"><a name="p1251915481893"></a><a name="p1251915481893"></a>Burn Port</p>
</td>
<td class="cellrowborder" valign="top" width="61.629999999999995%" headers="mcps1.2.3.1.2 "><p id="p751911484918"><a name="p751911484918"></a><a name="p751911484918"></a>镜像烧录串口号。</p>
</td>
</tr>
<tr id="row12594141775218"><td class="cellrowborder" valign="top" width="38.37%" headers="mcps1.2.3.1.1 "><p id="p559451715215"><a name="p559451715215"></a><a name="p559451715215"></a>Baud Rate</p>
</td>
<td class="cellrowborder" valign="top" width="61.629999999999995%" headers="mcps1.2.3.1.2 "><p id="p1059415179529"><a name="p1059415179529"></a><a name="p1059415179529"></a>镜像烧录波特率。</p>
</td>
</tr>
<tr id="row1938352817578"><td class="cellrowborder" valign="top" width="38.37%" headers="mcps1.2.3.1.1 "><p id="p2384628125715"><a name="p2384628125715"></a><a name="p2384628125715"></a>Build SDK</p>
</td>
<td class="cellrowborder" valign="top" width="61.629999999999995%" headers="mcps1.2.3.1.2 "><p id="p11384112811576"><a name="p11384112811576"></a><a name="p11384112811576"></a>开始编译SDK。</p>
</td>
</tr>
<tr id="row74301255175711"><td class="cellrowborder" valign="top" width="38.37%" headers="mcps1.2.3.1.1 "><p id="p1543125520573"><a name="p1543125520573"></a><a name="p1543125520573"></a>Flash</p>
</td>
<td class="cellrowborder" valign="top" width="61.629999999999995%" headers="mcps1.2.3.1.2 "><p id="p9431155512572"><a name="p9431155512572"></a><a name="p9431155512572"></a>开始镜像烧录。</p>
</td>
</tr>
<tr id="row1750681211586"><td class="cellrowborder" valign="top" width="38.37%" headers="mcps1.2.3.1.1 "><p id="p250651210584"><a name="p250651210584"></a><a name="p250651210584"></a>Next</p>
</td>
<td class="cellrowborder" valign="top" width="61.629999999999995%" headers="mcps1.2.3.1.2 "><p id="p95061812115814"><a name="p95061812115814"></a><a name="p95061812115814"></a>进入Benchmark界面。</p>
</td>
</tr>
</tbody>
</table>

**表 2**  Download Results主要控件说明

<a name="table16936471009"></a>
<table><thead align="left"><tr id="row09372710014"><th class="cellrowborder" valign="top" width="30.48%" id="mcps1.2.3.1.1"><p id="p12937976019"><a name="p12937976019"></a><a name="p12937976019"></a>项目</p>
</th>
<th class="cellrowborder" valign="top" width="69.52000000000001%" id="mcps1.2.3.1.2"><p id="p1293797704"><a name="p1293797704"></a><a name="p1293797704"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row1293710712011"><td class="cellrowborder" valign="top" width="30.48%" headers="mcps1.2.3.1.1 "><p id="p11937137305"><a name="p11937137305"></a><a name="p11937137305"></a>Download OM Model</p>
</td>
<td class="cellrowborder" valign="top" width="69.52000000000001%" headers="mcps1.2.3.1.2 "><p id="p15937171003"><a name="p15937171003"></a><a name="p15937171003"></a>单击下载按钮下载模型量化、转换结果。</p>
</td>
</tr>
</tbody>
</table>

## 模型调优<a name="ZH-CN_TOPIC_0000002509766620"></a>

-   **[约束说明](#ZH-CN_TOPIC_0000002516954544)**  

-   **[调优前提](#ZH-CN_TOPIC_0000002548594339)**  

-   **[界面介绍](#ZH-CN_TOPIC_0000002517114452)**  

### 约束说明<a name="ZH-CN_TOPIC_0000002516954544"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>在进行模型调优前，请务必查看如下约束要求：
>只支持单输出分类网络计算量化评估网络的准确率。

### 调优前提<a name="ZH-CN_TOPIC_0000002548594339"></a>

-   准备精度验证数据，并保存于本地Windows环境。具体数据格式见“[数据准备与环境搭建](#ZH-CN_TOPIC_0000002548828403)”。
-   准备并连接Hi3322单板。

### 界面介绍<a name="ZH-CN_TOPIC_0000002517114452"></a>

-   **[整体界面](#ZH-CN_TOPIC_0000002548474327)**  

-   **[串口配置界面](#ZH-CN_TOPIC_0000002516954546)**  

-   **[性能评估界面](#ZH-CN_TOPIC_0000002517218672)**  

-   **[精度评估界面](#ZH-CN_TOPIC_0000002548818475)**  

-   **[评估结果汇总界面](#ZH-CN_TOPIC_0000002517378582)**  

#### 整体界面<a name="ZH-CN_TOPIC_0000002548474327"></a>

**图 1**  模型调优整体界面<a name="fig825954753619"></a>  
![](figures/模型调优整体界面.png "模型调优整体界面")

模型调优整体界面如[图1](#fig825954753619)所示，主要包含四个部分：

1.  串口配置界面。在该界面配置数据传输、烧录、命令串口和波特率。
2.  性能评估界面。
3.  精度评估界面。
4.  评估结果汇总按钮。

执行模型调优的步骤如下：

1.  配置数据传输、烧录、命令串口和波特率。
2.  可选。如需烧录镜像，单击“Flash”按钮，执行镜像烧录。
3.  可选。单击“Performance Validation”按钮，执行上板性能评估。查看性能评估结果。
4.  可选。配置精度验证数据集路径，单击“Accuracy Validation”按钮，执行上板精度评估。查看精度评估结果。
5.  单击“Summary of Results”按钮，在弹窗中查看历史评估结果。

#### 串口配置界面<a name="ZH-CN_TOPIC_0000002516954546"></a>

用户在串口配置界面配置数据传输、命令发送串口和波特率。串口配置界面如[图1](#fig1637415227426)所示。

**图 1**  串口配置界面<a name="fig1637415227426"></a>  
![](figures/串口配置界面.png "串口配置界面")

元素说明如[表1](#table1315143434513)所示。

**表 1**  串口配置界面元素说明

<a name="table1315143434513"></a>
<table><thead align="left"><tr id="row18151934164510"><th class="cellrowborder" valign="top" width="31.1%" id="mcps1.2.3.1.1"><p id="p20154347459"><a name="p20154347459"></a><a name="p20154347459"></a>元素</p>
</th>
<th class="cellrowborder" valign="top" width="68.89999999999999%" id="mcps1.2.3.1.2"><p id="p17159346453"><a name="p17159346453"></a><a name="p17159346453"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row111553410459"><td class="cellrowborder" valign="top" width="31.1%" headers="mcps1.2.3.1.1 "><p id="p6157341450"><a name="p6157341450"></a><a name="p6157341450"></a>Data Port</p>
</td>
<td class="cellrowborder" valign="top" width="68.89999999999999%" headers="mcps1.2.3.1.2 "><p id="p1915143474519"><a name="p1915143474519"></a><a name="p1915143474519"></a>数据传输串口号。数据传输口用于将待评估的网络模型和验证数据传送到单板。</p>
</td>
</tr>
<tr id="row12755194814613"><td class="cellrowborder" valign="top" width="31.1%" headers="mcps1.2.3.1.1 "><p id="p6755154810464"><a name="p6755154810464"></a><a name="p6755154810464"></a>Data Port-&gt;Baudr Rate</p>
</td>
<td class="cellrowborder" valign="top" width="68.89999999999999%" headers="mcps1.2.3.1.2 "><p id="p375574814468"><a name="p375574814468"></a><a name="p375574814468"></a>数据传输串口波特率。</p>
</td>
</tr>
<tr id="row6371155084717"><td class="cellrowborder" valign="top" width="31.1%" headers="mcps1.2.3.1.1 "><p id="p19371050144710"><a name="p19371050144710"></a><a name="p19371050144710"></a>Command Port</p>
</td>
<td class="cellrowborder" valign="top" width="68.89999999999999%" headers="mcps1.2.3.1.2 "><p id="p1437113504478"><a name="p1437113504478"></a><a name="p1437113504478"></a>命令发送串口号。命令发送串口用于向单板发送模型推理命令。</p>
</td>
</tr>
<tr id="row1157026154811"><td class="cellrowborder" valign="top" width="31.1%" headers="mcps1.2.3.1.1 "><p id="p45701963486"><a name="p45701963486"></a><a name="p45701963486"></a>Command Port-&gt;Baud Rate</p>
</td>
<td class="cellrowborder" valign="top" width="68.89999999999999%" headers="mcps1.2.3.1.2 "><p id="p15118125104811"><a name="p15118125104811"></a><a name="p15118125104811"></a>命令发送串口波特率。</p>
</td>
</tr>
</tbody>
</table>

#### 性能评估界面<a name="ZH-CN_TOPIC_0000002517218672"></a>

用户在性能评估界面触发上板性能评估，并查看性能评估结果。性能评估界面的如[图1](#fig168883129411)所示。

**图 1**  性能评估界面<a name="fig168883129411"></a>  
![](figures/性能评估界面.png "性能评估界面")

性能评估界面元素说明如[表1](#table8147195912415)所示。

**表 1**  性能评估界面元素说明

<a name="table8147195912415"></a>
<table><thead align="left"><tr id="row1414712591549"><th class="cellrowborder" valign="top" width="31.209999999999997%" id="mcps1.2.3.1.1"><p id="p7147359146"><a name="p7147359146"></a><a name="p7147359146"></a>元素</p>
</th>
<th class="cellrowborder" valign="top" width="68.78999999999999%" id="mcps1.2.3.1.2"><p id="p614711591548"><a name="p614711591548"></a><a name="p614711591548"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row81479591842"><td class="cellrowborder" valign="top" width="31.209999999999997%" headers="mcps1.2.3.1.1 "><p id="p10147359643"><a name="p10147359643"></a><a name="p10147359643"></a>Performance Evaluation</p>
</td>
<td class="cellrowborder" valign="top" width="68.78999999999999%" headers="mcps1.2.3.1.2 "><p id="p1114711590411"><a name="p1114711590411"></a><a name="p1114711590411"></a>开始上板精度评估按钮。</p>
</td>
</tr>
<tr id="row139595984011"><td class="cellrowborder" valign="top" width="31.209999999999997%" headers="mcps1.2.3.1.1 "><p id="p3165145818614"><a name="p3165145818614"></a><a name="p3165145818614"></a>INFERENCE TIME</p>
</td>
<td class="cellrowborder" valign="top" width="68.78999999999999%" headers="mcps1.2.3.1.2 "><p id="p13165165813615"><a name="p13165165813615"></a><a name="p13165165813615"></a>上板推理时间。该时间只包括模型推理时间，不包括输入输出数据的拷贝。</p>
</td>
</tr>
<tr id="row1734698174118"><td class="cellrowborder" valign="top" width="31.209999999999997%" headers="mcps1.2.3.1.1 "><p id="p2014210306610"><a name="p2014210306610"></a><a name="p2014210306610"></a>MODEL SIZE</p>
</td>
<td class="cellrowborder" valign="top" width="68.78999999999999%" headers="mcps1.2.3.1.2 "><p id="p18142630763"><a name="p18142630763"></a><a name="p18142630763"></a>模型文件大小。</p>
</td>
</tr>
<tr id="row66401736953"><td class="cellrowborder" valign="top" width="31.209999999999997%" headers="mcps1.2.3.1.1 "><p id="p1664063615519"><a name="p1664063615519"></a><a name="p1664063615519"></a>DBG SIZE</p>
</td>
<td class="cellrowborder" valign="top" width="68.78999999999999%" headers="mcps1.2.3.1.2 "><p id="p10640153611510"><a name="p10640153611510"></a><a name="p10640153611510"></a>图调试信息文件大小。</p>
</td>
</tr>
</tbody>
</table>

#### 精度评估界面<a name="ZH-CN_TOPIC_0000002548818475"></a>

用户在精度评估界面配置精度评估验证数据、触发上板精度验证以及查看精度验证结果。精度评估界面如[图1](#fig29194371693)所示。

**图 1**  精度评估界面<a name="fig29194371693"></a>  
![](figures/精度评估界面.png "精度评估界面")

精度评估界面元素说明如[表1](#table14641101316114)所示。

**表 1**  精度评估界面元素说明

<a name="table14641101316114"></a>
<table><thead align="left"><tr id="row66411013101118"><th class="cellrowborder" valign="top" width="29.98%" id="mcps1.2.3.1.1"><p id="p19641113131111"><a name="p19641113131111"></a><a name="p19641113131111"></a>元素</p>
</th>
<th class="cellrowborder" valign="top" width="70.02000000000001%" id="mcps1.2.3.1.2"><p id="p6641181314118"><a name="p6641181314118"></a><a name="p6641181314118"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row12641121317116"><td class="cellrowborder" valign="top" width="29.98%" headers="mcps1.2.3.1.1 "><p id="p16641191318118"><a name="p16641191318118"></a><a name="p16641191318118"></a>Input Node</p>
</td>
<td class="cellrowborder" valign="top" width="70.02000000000001%" headers="mcps1.2.3.1.2 "><p id="p93861311181213"><a name="p93861311181213"></a><a name="p93861311181213"></a>Path：验证集输入数据目录。输入文件夹路径，文件夹中包含和模型输入数据匹配的npy文件。</p>
</td>
</tr>
<tr id="row1728540121412"><td class="cellrowborder" valign="top" width="29.98%" headers="mcps1.2.3.1.1 "><p id="p13286008142"><a name="p13286008142"></a><a name="p13286008142"></a>Validation Labels</p>
</td>
<td class="cellrowborder" valign="top" width="70.02000000000001%" headers="mcps1.2.3.1.2 "><p id="p192866031410"><a name="p192866031410"></a><a name="p192866031410"></a>包含两个元素：</p>
<a name="ul439724081410"></a><a name="ul439724081410"></a><ul id="ul439724081410"><li>下拉框：<a name="ul1815795731419"></a><a name="ul1815795731419"></a><ul id="ul1815795731419"><li>None：不输入分类真值标签文件。不进行准确率评估。</li><li>输出结点名称：从文件系统选择包含该节点分类真值标签的csv文件。并使用csv文件中包含的标签进行准确率计算。在选择该选项时，使能分类真值文件输入框。</li></ul>
</li><li>分类真值文件输入框：输入包含分类真值的csv文件路径。</li></ul>
</td>
</tr>
<tr id="row331245414144"><td class="cellrowborder" valign="top" width="29.98%" headers="mcps1.2.3.1.1 "><p id="p1831295419141"><a name="p1831295419141"></a><a name="p1831295419141"></a>Accuracy Evaluation</p>
</td>
<td class="cellrowborder" valign="top" width="70.02000000000001%" headers="mcps1.2.3.1.2 "><p id="p1550765515172"><a name="p1550765515172"></a><a name="p1550765515172"></a>开始上板精度验证按钮。</p>
</td>
</tr>
<tr id="row8623171198"><td class="cellrowborder" valign="top" width="29.98%" headers="mcps1.2.3.1.1 "><p id="p39921311125712"><a name="p39921311125712"></a><a name="p39921311125712"></a>ACCURACY</p>
</td>
<td class="cellrowborder" valign="top" width="70.02000000000001%" headers="mcps1.2.3.1.2 "><p id="p16992191195715"><a name="p16992191195715"></a><a name="p16992191195715"></a>表示分类结果准确率，使用标签真值计算。计算公式如下，其中<a name="image642362211326"></a><a name="image642362211326"></a><span><img class="mathml" id="image642362211326" src="figures/zh-cn_formulaimage_0000002517714152.png" width="56.279482" height="32.901939"></span>表示分类正确的样本数量，<a name="image1097645123220"></a><a name="image1097645123220"></a><span><img class="mathml" id="image1097645123220" src="figures/zh-cn_formulaimage_0000002549154021.png" width="45.023692000000004" height="32.901939"></span>表示样本的总数量。</p>
<p id="p17330110153017"><a name="p17330110153017"></a><a name="p17330110153017"></a><a name="image9860115919319"></a><a name="image9860115919319"></a><span><img class="mathml" id="image9860115919319" src="figures/zh-cn_formulaimage_0000002517714156.png" width="233.41500000000002" height="63.253735999999996"></span></p>
</td>
</tr>
<tr id="row19814192411435"><td class="cellrowborder" valign="top" width="29.98%" headers="mcps1.2.3.1.1 "><p id="p184471665720"><a name="p184471665720"></a><a name="p184471665720"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" width="70.02000000000001%" headers="mcps1.2.3.1.2 "><p id="p289204614436"><a name="p289204614436"></a><a name="p289204614436"></a>平均余弦相似度，计算公式如下，其中<a name="image9892046174320"></a><a name="image9892046174320"></a><span><img class="mathml" id="image9892046174320" src="figures/zh-cn_formulaimage_0000002562062097.png" width="17.881185000000002" height="32.652564"></span>表示量化评估网络的输出，<a name="image389204620436"></a><a name="image389204620436"></a><span><img class="mathml" id="image389204620436" src="figures/zh-cn_formulaimage_0000002531182176.png" width="18.312238" height="28.662564"></span>表示原始浮点网络的输出，<a name="image38934624313"></a><a name="image38934624313"></a><span><img class="mathml" id="image38934624313" src="figures/zh-cn_formulaimage_0000002562062103.png" width="21.103243000000003" height="31.655064"></span>表示验证集样本的数量。</p>
<p id="p208904614317"><a name="p208904614317"></a><a name="p208904614317"></a><a name="image189646154311"></a><a name="image189646154311"></a><span><img class="mathml" id="image189646154311" src="figures/zh-cn_formulaimage_0000002531182178.png" width="243.39000000000001" height="73.278744"></span></p>
</td>
</tr>
<tr id="row856725711199"><td class="cellrowborder" valign="top" width="29.98%" headers="mcps1.2.3.1.1 "><p id="p1456715715192"><a name="p1456715715192"></a><a name="p1456715715192"></a>Evaluation Data</p>
</td>
<td class="cellrowborder" valign="top" width="70.02000000000001%" headers="mcps1.2.3.1.2 "><p id="p956715576197"><a name="p956715576197"></a><a name="p956715576197"></a>各验证样本验证结果。表格中各项说明如<a href="#table8115238122018">表2</a>所示。</p>
</td>
</tr>
<tr id="row32007219214"><td class="cellrowborder" valign="top" width="29.98%" headers="mcps1.2.3.1.1 "><p id="p92003217218"><a name="p92003217218"></a><a name="p92003217218"></a>Probability Density Histogram</p>
</td>
<td class="cellrowborder" valign="top" width="70.02000000000001%" headers="mcps1.2.3.1.2 "><p id="p6404133513619"><a name="p6404133513619"></a><a name="p6404133513619"></a>验证集的余弦相似度的分布图。横轴为余弦相似度，纵轴为验证集样本的百分比。</p>
</td>
</tr>
</tbody>
</table>

**表 2**  验证样本结果说明

<a name="table8115238122018"></a>
<table><thead align="left"><tr id="row151151438192018"><th class="cellrowborder" valign="top" width="29.42%" id="mcps1.2.3.1.1"><p id="p11115133862016"><a name="p11115133862016"></a><a name="p11115133862016"></a>元素</p>
</th>
<th class="cellrowborder" valign="top" width="70.58%" id="mcps1.2.3.1.2"><p id="p10115173814204"><a name="p10115173814204"></a><a name="p10115173814204"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row31155385204"><td class="cellrowborder" valign="top" width="29.42%" headers="mcps1.2.3.1.1 "><p id="p911523802015"><a name="p911523802015"></a><a name="p911523802015"></a>Sample Name</p>
</td>
<td class="cellrowborder" valign="top" width="70.58%" headers="mcps1.2.3.1.2 "><p id="p171151038182010"><a name="p171151038182010"></a><a name="p171151038182010"></a>样本名称。</p>
</td>
</tr>
<tr id="row15643194115225"><td class="cellrowborder" valign="top" width="29.42%" headers="mcps1.2.3.1.1 "><p id="p4644134114225"><a name="p4644134114225"></a><a name="p4644134114225"></a>Output Name</p>
</td>
<td class="cellrowborder" valign="top" width="70.58%" headers="mcps1.2.3.1.2 "><p id="p5644184142214"><a name="p5644184142214"></a><a name="p5644184142214"></a>输出节点名称。</p>
</td>
</tr>
<tr id="row928511578221"><td class="cellrowborder" valign="top" width="29.42%" headers="mcps1.2.3.1.1 "><p id="p628617573223"><a name="p628617573223"></a><a name="p628617573223"></a>Predict</p>
</td>
<td class="cellrowborder" valign="top" width="70.58%" headers="mcps1.2.3.1.2 "><p id="p7286155720222"><a name="p7286155720222"></a><a name="p7286155720222"></a>模型上板推理的输出。</p>
</td>
</tr>
<tr id="row5812918239"><td class="cellrowborder" valign="top" width="29.42%" headers="mcps1.2.3.1.1 "><p id="p11812912315"><a name="p11812912315"></a><a name="p11812912315"></a>Golden</p>
</td>
<td class="cellrowborder" valign="top" width="70.58%" headers="mcps1.2.3.1.2 "><p id="p178189102315"><a name="p178189102315"></a><a name="p178189102315"></a>原始浮点网络在Windows主机推理的输出。</p>
</td>
</tr>
<tr id="row61391237122311"><td class="cellrowborder" valign="top" width="29.42%" headers="mcps1.2.3.1.1 "><p id="p1991151310449"><a name="p1991151310449"></a><a name="p1991151310449"></a>Accuracy</p>
</td>
<td class="cellrowborder" valign="top" width="70.58%" headers="mcps1.2.3.1.2 "><p id="p7140143718238"><a name="p7140143718238"></a><a name="p7140143718238"></a>本样本的分类正确率。</p>
</td>
</tr>
<tr id="row107321547172315"><td class="cellrowborder" valign="top" width="29.42%" headers="mcps1.2.3.1.1 "><p id="p1573224718232"><a name="p1573224718232"></a><a name="p1573224718232"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" width="70.58%" headers="mcps1.2.3.1.2 "><p id="p54531149131416"><a name="p54531149131416"></a><a name="p54531149131416"></a>余弦相似度，计算公式如下，其中<a name="image15484124391614"></a><a name="image15484124391614"></a><span><img class="mathml" id="image15484124391614" src="figures/zh-cn_formulaimage_0000002517554446.png" width="19.110238000000003" height="34.896939"></span>表示模型上板推理的输出，<a name="image634019531710"></a><a name="image634019531710"></a><span><img class="mathml" id="image634019531710" src="figures/zh-cn_formulaimage_0000002549114235.png" width="19.108775" height="29.909439"></span>表示原始浮点网络在Windows的输出。</p>
<p id="p8151115911493"><a name="p8151115911493"></a><a name="p8151115911493"></a><a name="image9372165344419"></a><a name="image9372165344419"></a><span><img class="mathml" id="image9372165344419" src="figures/zh-cn_formulaimage_0000002549114245.png"></span></p>
</td>
</tr>
</tbody>
</table>

#### 评估结果汇总界面<a name="ZH-CN_TOPIC_0000002517378582"></a>

单击“Summary of Results”按钮之后弹出评估结果汇总界面，该界面汇总每次评估的结果。如[图1](#fig15398321925)所示。

**图 1**  评估结果汇总界面<a name="fig15398321925"></a>  
![](figures/评估结果汇总界面-3.png "评估结果汇总界面-3")

评估结果汇总界面元素说明如[表1](#table126871262713)所示。

**表 1**  评估结果界面元素说明

<a name="table126871262713"></a>
<table><thead align="left"><tr id="row26821219274"><th class="cellrowborder" valign="top" width="10.57%" id="mcps1.2.4.1.1"><p id="p67751648104519"><a name="p67751648104519"></a><a name="p67751648104519"></a>一级元素</p>
</th>
<th class="cellrowborder" valign="top" width="18.83%" id="mcps1.2.4.1.2"><p id="p1968191282719"><a name="p1968191282719"></a><a name="p1968191282719"></a>二级元素</p>
</th>
<th class="cellrowborder" valign="top" width="70.6%" id="mcps1.2.4.1.3"><p id="p2069151252713"><a name="p2069151252713"></a><a name="p2069151252713"></a>说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row920295822719"><td class="cellrowborder" valign="top" width="10.57%" headers="mcps1.2.4.1.1 "><p id="p17202155862714"><a name="p17202155862714"></a><a name="p17202155862714"></a>Trail ID</p>
</td>
<td class="cellrowborder" valign="top" width="18.83%" headers="mcps1.2.4.1.2 ">&nbsp;&nbsp;</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p1420235818272"><a name="p1420235818272"></a><a name="p1420235818272"></a>评估结果序号。</p>
</td>
</tr>
<tr id="row131301128142814"><td class="cellrowborder" valign="top" width="10.57%" headers="mcps1.2.4.1.1 "><p id="p151301928202820"><a name="p151301928202820"></a><a name="p151301928202820"></a>Model Name</p>
</td>
<td class="cellrowborder" valign="top" width="18.83%" headers="mcps1.2.4.1.2 ">&nbsp;&nbsp;</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p1513012282281"><a name="p1513012282281"></a><a name="p1513012282281"></a>网络的名称，以及修改时间。</p>
</td>
</tr>
<tr id="row194581042144817"><td class="cellrowborder" rowspan="5" valign="top" width="10.57%" headers="mcps1.2.4.1.1 "><p id="p977514884518"><a name="p977514884518"></a><a name="p977514884518"></a>Benchmark</p>
</td>
<td class="cellrowborder" valign="top" width="18.83%" headers="mcps1.2.4.1.2 "><p id="p39921311125712"><a name="p39921311125712"></a><a name="p39921311125712"></a>Accuracy</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p16992191195715"><a name="p16992191195715"></a><a name="p16992191195715"></a>表示模型上板推理结果分类结果准确率，使用标签真值计算。计算公式如下，其中<a name="image642362211326"></a><a name="image642362211326"></a><span><img class="mathml" id="image642362211326" src="figures/zh-cn_formulaimage_0000002562063161.png" width="50.734313" height="29.660064"></span>表示分类正确的样本数量，<a name="image1097645123220"></a><a name="image1097645123220"></a><span><img class="mathml" id="image1097645123220" src="figures/zh-cn_formulaimage_0000002531183246.png" width="40.56367" height="29.660064"></span>表示样本的总数量。</p>
<p id="p17330110153017"><a name="p17330110153017"></a><a name="p17330110153017"></a><a name="image9860115919319"></a><a name="image9860115919319"></a><span><img class="mathml" id="image9860115919319" src="figures/zh-cn_formulaimage_0000002562063163.png" width="242.3925" height="65.68643900000001"></span></p>
</td>
</tr>
<tr id="row87249382281"><td class="cellrowborder" valign="top" headers="mcps1.2.4.1.1 "><p id="p272463882818"><a name="p272463882818"></a><a name="p272463882818"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" headers="mcps1.2.4.1.2 "><p id="p54531149131416"><a name="p54531149131416"></a><a name="p54531149131416"></a>表示模型上板推理结果平均余弦相似度，计算公式如下，其中<a name="image15484124391614"></a><a name="image15484124391614"></a><span><img class="mathml" id="image15484124391614" src="figures/zh-cn_formulaimage_0000002549116911.png" width="18.837056" height="34.398189"></span>表示模型上板推理的输出，<a name="image634019531710"></a><a name="image634019531710"></a><span><img class="mathml" id="image634019531710" src="figures/zh-cn_formulaimage_0000002517557120.png" width="19.427443000000004" height="30.408189"></span>表示原始浮点网络在Windows的输出，<a name="image8788135318194"></a><a name="image8788135318194"></a><span><img class="mathml" id="image8788135318194" src="figures/zh-cn_formulaimage_0000002549116919.png" width="20.937126000000003" height="31.405689"></span>表示验证集样本的数量。</p>
<p id="p8151115911493"><a name="p8151115911493"></a><a name="p8151115911493"></a><a name="image196582429196"></a><a name="image196582429196"></a><span><img class="mathml" id="image196582429196" src="figures/zh-cn_formulaimage_0000002517557128.png" width="250.3725" height="75.380942"></span></p>
</td>
</tr>
<tr id="row1589814107496"><td class="cellrowborder" valign="top" headers="mcps1.2.4.1.1 "><p id="p1819518406296"><a name="p1819518406296"></a><a name="p1819518406296"></a>Inference Time(MS)</p>
</td>
<td class="cellrowborder" valign="top" headers="mcps1.2.4.1.2 "><p id="p14753153782919"><a name="p14753153782919"></a><a name="p14753153782919"></a>上板推理时间。</p>
</td>
</tr>
<tr id="row1538583114498"><td class="cellrowborder" valign="top" headers="mcps1.2.4.1.1 "><p id="p4149171298"><a name="p4149171298"></a><a name="p4149171298"></a>Model Size(KB)</p>
</td>
<td class="cellrowborder" valign="top" headers="mcps1.2.4.1.2 "><p id="p101413173299"><a name="p101413173299"></a><a name="p101413173299"></a>模型文件大小。</p>
</td>
</tr>
<tr id="row9187175792810"><td class="cellrowborder" valign="top" headers="mcps1.2.4.1.1 "><p id="p918765714288"><a name="p918765714288"></a><a name="p918765714288"></a>Dbg Size</p>
</td>
<td class="cellrowborder" valign="top" headers="mcps1.2.4.1.2 "><p id="p0187195702812"><a name="p0187195702812"></a><a name="p0187195702812"></a>图调试信息文件大小。</p>
</td>
</tr>
<tr id="row71421715292"><td class="cellrowborder" rowspan="2" valign="top" width="10.57%" headers="mcps1.2.4.1.1 "><p id="p67751648134518"><a name="p67751648134518"></a><a name="p67751648134518"></a>Quantize</p>
</td>
<td class="cellrowborder" valign="top" width="18.83%" headers="mcps1.2.4.1.2 "><p id="p1886352124915"><a name="p1886352124915"></a><a name="p1886352124915"></a>Cosine Similarity</p>
</td>
<td class="cellrowborder" valign="top" width="70.6%" headers="mcps1.2.4.1.3 "><p id="p128675234911"><a name="p128675234911"></a><a name="p128675234911"></a>表示量化评估模型推理结果的平均余弦相似度，计算公式如下，其中<a name="image686175215490"></a><a name="image686175215490"></a><span><img class="mathml" id="image686175215490" src="figures/zh-cn_formulaimage_0000002562063065.png" width="18.837056" height="34.398189"></span>表示模型上板推理的输出，<a name="image1986155214916"></a><a name="image1986155214916"></a><span><img class="mathml" id="image1986155214916" src="figures/zh-cn_formulaimage_0000002531183142.png" width="19.427443000000004" height="30.408189"></span>表示原始浮点网络在Windows的输出，<a name="image1986185211496"></a><a name="image1986185211496"></a><span><img class="mathml" id="image1986185211496" src="figures/zh-cn_formulaimage_0000002562063067.png" width="20.937126000000003" height="31.405689"></span>表示验证集样本的数量。</p>
<p id="p1786352204920"><a name="p1786352204920"></a><a name="p1786352204920"></a><a name="image178695274917"></a><a name="image178695274917"></a><span><img class="mathml" id="image178695274917" src="figures/zh-cn_formulaimage_0000002531183144.png" width="250.3725" height="75.380942"></span></p>
</td>
</tr>
<tr id="row15753193722918"><td class="cellrowborder" valign="top" headers="mcps1.2.4.1.1 "><p id="p19676520145712"><a name="p19676520145712"></a><a name="p19676520145712"></a>MSE</p>
</td>
<td class="cellrowborder" valign="top" headers="mcps1.2.4.1.2 "><p id="p189491228195019"><a name="p189491228195019"></a><a name="p189491228195019"></a>表示量化评估模型推理结果的均方误差，计算公式如下，其中<a name="image116392033152317"></a><a name="image116392033152317"></a><span><img class="mathml" id="image116392033152317" src="figures/zh-cn_formulaimage_0000002562063145.png" width="20.066109" height="36.642564"></span>表示量化评估网络的输出，<a name="image16391333182311"></a><a name="image16391333182311"></a><span><img class="mathml" id="image16391333182311" src="figures/zh-cn_formulaimage_0000002531263150.png" width="18.312238" height="28.662564"></span>表示原始浮点网络的输出，<a name="image1563903322316"></a><a name="image1563903322316"></a><span><img class="mathml" id="image1563903322316" src="figures/zh-cn_formulaimage_0000002562063147.png" width="20.438376" height="30.657564"></span>表示验证集样本的数量。</p>
<p id="p182633519237"><a name="p182633519237"></a><a name="p182633519237"></a><a name="image196434716242"></a><a name="image196434716242"></a><span><img class="mathml" id="image196434716242" src="figures/zh-cn_formulaimage_0000002531263152.png" width="192.5175" height="74.338488"></span></p>
</td>
</tr>
</tbody>
</table>

## 应用开发<a name="ZH-CN_TOPIC_0000002509726614"></a>

在HiSpark Studio AI中完成模型量化、转换之后，将模型导出并使用HiSpark.AI API完成应用开发。具体步骤如下：

1.  在Deploy页面下载转换好的exeom模型。

    **图 1**  下载exeom模型<a name="fig126011912721"></a>  
    ![](figures/下载exeom模型.png "下载exeom模型")

2.  具体API的用法请参考文档《HiSpark.AI API开发指南》。

# 常见问题<a name="ZH-CN_TOPIC_0000002565416179"></a>

-   **[服务器断连](#ZH-CN_TOPIC_0000002565416789)**  

## 服务器断连<a name="ZH-CN_TOPIC_0000002565416789"></a>

对于Linux通路，若远程服务器在使用过程中断连，插件右下角会弹窗提示 "Lost connection to remote server" 。当远程服务器重新启动，连接恢复后，需手动在选择模型界面通过导入模型或选择已有模型的方式，重新连接一次服务器。

