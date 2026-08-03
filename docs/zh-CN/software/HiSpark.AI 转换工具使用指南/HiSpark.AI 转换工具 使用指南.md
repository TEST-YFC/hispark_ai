# 前言<a name="ZH-CN_TOPIC_0000002451492226"></a>

**概述<a name="section4537382116410"></a>**

本文档介绍如何在HiSpark系列MCU上，基于MindSpore Lite Enterprise Micro v106版本，实现第三方开源框架（如TFLite、ONNX等）网络模型的轻量化部署与推理任务。Converter\_lite是MindSpore Lite Enterprise Micro的转换工具，基于一系列内存/算子优化技术，生成适配HiSpark MCU上可执行的Micro模块代码。基于Converter\_lite，在服务器端能够将模型转换为可在x86 / RISCV/ARM平台（x86部署可以为板端调试提供精度标杆）上部署的Micro工程代码，从而脱离在线解析模型和图编译，具有运行时内存小、代码轻量化等特点。

通过本文档，您将能够实现以下目标：

-   了解不同开源框架网络模型离线转换Micro工程代码的方法。
-   能够基于本文档的参数配置，转成量化或非量化的Micro工程代码。
-   能够基于Micro工程代码在x86/RISCV/ARM平台侧（x86部署可以为板端调试提供精度标杆）做部署推理。

掌握以下经验和技能可以更好理解本文档：

-   熟悉Linux基本命令。
-   对机器学习、人工智能有一定的了解。
-   有一定的C++工程开发经验。

**读者对象<a name="section4378592816410"></a>**

本文档适用于使用MindSpore Lite Enterprise Micro v106工具进行AI模型端侧部署的人员，本文档适用于以下工程师：

-   技术支持工程师
-   软件工程师
-   硬件工程师

**符号约定<a name="section133020216410"></a>**

在本文中可能出现下列标志，它们所代表的含义如下。

<a name="table2622507016410"></a>
<table><thead align="left"><tr id="row1530720816410"><th class="cellrowborder" valign="top" width="20.580000000000002%" id="mcps1.1.3.1.1"><p id="p6450074116410"><a name="p6450074116410"></a><a name="p6450074116410"></a><strong id="b2136615816410"><a name="b2136615816410"></a><a name="b2136615816410"></a>符号</strong></p>
</th>
<th class="cellrowborder" valign="top" width="79.42%" id="mcps1.1.3.1.2"><p id="p5435366816410"><a name="p5435366816410"></a><a name="p5435366816410"></a><strong id="b5941558116410"><a name="b5941558116410"></a><a name="b5941558116410"></a>说明</strong></p>
</th>
</tr>
</thead>
<tbody><tr id="row1372280416410"><td class="cellrowborder" valign="top" width="20.580000000000002%" headers="mcps1.1.3.1.1 "><p id="p3734547016410"><a name="p3734547016410"></a><a name="p3734547016410"></a><a name="image2670064316410"></a><a name="image2670064316410"></a><span><img class="" id="image2670064316410" height="25.270000000000003" width="67.83" src="figures/zh-cn_image_0000002484572049.png"></span></p>
</td>
<td class="cellrowborder" valign="top" width="79.42%" headers="mcps1.1.3.1.2 "><p id="p1757432116410"><a name="p1757432116410"></a><a name="p1757432116410"></a>表示如不避免则将会导致死亡或严重伤害的具有高等级风险的危害。</p>
</td>
</tr>
<tr id="row466863216410"><td class="cellrowborder" valign="top" width="20.580000000000002%" headers="mcps1.1.3.1.1 "><p id="p1432579516410"><a name="p1432579516410"></a><a name="p1432579516410"></a><a name="image4895582316410"></a><a name="image4895582316410"></a><span><img class="" id="image4895582316410" height="25.270000000000003" width="67.83" src="figures/zh-cn_image_0000002451332614.png"></span></p>
</td>
<td class="cellrowborder" valign="top" width="79.42%" headers="mcps1.1.3.1.2 "><p id="p959197916410"><a name="p959197916410"></a><a name="p959197916410"></a>表示如不避免则可能导致死亡或严重伤害的具有中等级风险的危害。</p>
</td>
</tr>
<tr id="row123863216410"><td class="cellrowborder" valign="top" width="20.580000000000002%" headers="mcps1.1.3.1.1 "><p id="p1232579516410"><a name="p1232579516410"></a><a name="p1232579516410"></a><a name="image1235582316410"></a><a name="image1235582316410"></a><span><img class="" id="image1235582316410" height="25.270000000000003" width="67.83" src="figures/zh-cn_image_0000002484452085.png"></span></p>
</td>
<td class="cellrowborder" valign="top" width="79.42%" headers="mcps1.1.3.1.2 "><p id="p123197916410"><a name="p123197916410"></a><a name="p123197916410"></a>表示如不避免则可能导致轻微或中度伤害的具有低等级风险的危害。</p>
</td>
</tr>
<tr id="row5786682116410"><td class="cellrowborder" valign="top" width="20.580000000000002%" headers="mcps1.1.3.1.1 "><p id="p2204984716410"><a name="p2204984716410"></a><a name="p2204984716410"></a><a name="image4504446716410"></a><a name="image4504446716410"></a><span><img class="" id="image4504446716410" height="25.270000000000003" width="67.83" src="figures/zh-cn_image_0000002451492230.png"></span></p>
</td>
<td class="cellrowborder" valign="top" width="79.42%" headers="mcps1.1.3.1.2 "><p id="p4388861916410"><a name="p4388861916410"></a><a name="p4388861916410"></a>用于传递设备或环境安全警示信息。如不避免则可能会导致设备损坏、数据丢失、设备性能降低或其它不可预知的结果。</p>
<p id="p1238861916410"><a name="p1238861916410"></a><a name="p1238861916410"></a>“须知”不涉及人身伤害。</p>
</td>
</tr>
<tr id="row2856923116410"><td class="cellrowborder" valign="top" width="20.580000000000002%" headers="mcps1.1.3.1.1 "><p id="p5555360116410"><a name="p5555360116410"></a><a name="p5555360116410"></a><a name="image799324016410"></a><a name="image799324016410"></a><span><img class="" id="image799324016410" height="25.270000000000003" width="67.83" src="figures/zh-cn_image_0000002484572053.png"></span></p>
</td>
<td class="cellrowborder" valign="top" width="79.42%" headers="mcps1.1.3.1.2 "><p id="p4612588116410"><a name="p4612588116410"></a><a name="p4612588116410"></a>对正文中重点信息的补充说明。</p>
<p id="p1232588116410"><a name="p1232588116410"></a><a name="p1232588116410"></a>“说明”不是安全警示信息，不涉及人身、设备及环境伤害信息。</p>
</td>
</tr>
</tbody>
</table>

**修改记录<a name="section2467512116410"></a>**

| 文档版本 | 发布日期 | 修改说明 |
| :--- | :--- | :--- |
| 06 | 2026-07-30 | 新增Onnx/TFLite算子规格：<br>新增“[Erf](#ZH-CN_TOPIC_0000002026072801)、[HardSigmoid](#ZH-CN_TOPIC_0000002026072802)、[Celu](#ZH-CN_TOPIC_0000002026072803)”。<br>新增"[Shape](#ZH-CN_TOPIC_0000003030115802)、[Shape](#ZH-CN_TOPIC_0000003030115702)"。<br>新增"[MatMulInteger](#ZH-CN_TOPIC_0000003040115702)"。<br>新增"[TopK](#ZH-CN_TOPIC_0000003050115802)、[TopK](#ZH-CN_TOPIC_0000003050115702)"。<br>新增"[Gelu](#ZH-CN_TOPIC_0000002661401191)、[Gelu](#ZH-CN_TOPIC_0000002661401194)、[Trilu](#ZH-CN_TOPIC_0000002661401195)、[Pack](#ZH-CN_TOPIC_0000002661401192)、[Unpack](#ZH-CN_TOPIC_0000002661401193)"。<br>新增"[Fill](#ZH-CN_TOPIC_0000002800000001)、[Neg](#ZH-CN_TOPIC_0000002900000001)、[Pow](#ZH-CN_TOPIC_0000002476598365)、[Neg](#ZH-CN_TOPIC_0000002900000002)、[Pow](#ZH-CN_TOPIC_0000002476598371)"。<br>新增"[Select](#ZH-CN_TOPIC_0000002600000001)、[SelectV2](#ZH-CN_TOPIC_0000002600000002)、[ReverseV2](#ZH-CN_TOPIC_0000002600000003)、[Mod](#ZH-CN_TOPIC_0000002600000004)、[ReduceL1](#ZH-CN_TOPIC_0000002600000005)、[ReduceL2](#ZH-CN_TOPIC_0000002600000006)"。<br>新增训练特性：<br>在“[开源框架的TFLite/ONNX模型转换为Micro工程](#ZH-CN_TOPIC_0000002353945877)”中更新QAS INT8量化训练配置、FP32训练配置。<br>在“[参数说明](#ZH-CN_TOPIC_0000002319906348)”中更新训练参数，新增MSE loss和Adam优化器参数。<br>新增QAS INT8和FP32训练支持规格。 |
| 05 | 2026-07-03 | 更新“[设置环境变量](#ZH-CN_TOPIC_0000002353775693)、[限制与约束](#ZH-CN_TOPIC_0000002319976756)”。<br>在“[开源框架的TFLite/ONNX模型转换为Micro工程](#ZH-CN_TOPIC_0000002353945877)”中更新[5](#li1849371193511)。<br>新增“[ARM平台编译部署](#ZH-CN_TOPIC_0000002590121500)”小节。<br>在“[输入选项](#ZH-CN_TOPIC_0000002353985081)”中更新[表1](#table3808173922715)。<br>更新“[算子规格参考](#ZH-CN_TOPIC_0000002354161329)”。<br>新增“[专题](#ZH-CN_TOPIC_0000002562713759)”章节。 |
| 04 | 2026-06-01 | 新增Onnx/TFLite算子规格：<br>更新“[PRelu](#ZH-CN_TOPIC_0000002568693026)、[PRelu](#ZH-CN_TOPIC_0000002568693026)、[CumSum](#ZH-CN_TOPIC_0000002599292569)、[ReverseSequence](#ZH-CN_TOPIC_0000002599187919)、[CumSum](#ZH-CN_TOPIC_0000002568533372)、[ReverseSequence](#ZH-CN_TOPIC_0000002599187805)、[Einsum](#ZH-CN_TOPIC_0000002599307751)”。<br>更新“[Relu6](#ZH-CN_TOPIC_0000002574010852)、[LeakyRelu](#ZH-CN_TOPIC_0000002604689955)、[HardSwish](#ZH-CN_TOPIC_0000002574309498)、[LeakyRelu](#ZH-CN_TOPIC_0000002574170496)、[HardSwish](#ZH-CN_TOPIC_0000002574469146)、[Swish](#ZH-CN_TOPIC_0000002605108551)”。<br>更新“[LogicalAnd](#ZH-CN_TOPIC_0000002574976868)、[Equal](#ZH-CN_TOPIC_0000002605336325)、[GreaterEqual](#ZH-CN_TOPIC_0000002574817236)、[Greater](#ZH-CN_TOPIC_0000002605456261)、[LessEqual](#ZH-CN_TOPIC_0000002574976872)、[Less](#ZH-CN_TOPIC_0000002605336331)、[NotEqual](#ZH-CN_TOPIC_0000002574817240)、[LogicalNot](#ZH-CN_TOPIC_0000002605456267)、[LogicalOr](#ZH-CN_TOPIC_0000002574976878)、[And](#ZH-CN_TOPIC_0000002574578826) 、[GreaterOrEqual](#ZH-CN_TOPIC_0000002605377849)、[Greater](#ZH-CN_TOPIC_0000002574738452)、[LessOrEqual](#ZH-CN_TOPIC_0000002574578828)、[Less](#ZH-CN_TOPIC_0000002605257909)、[Not](#ZH-CN_TOPIC_0000002605377851)、[Or](#ZH-CN_TOPIC_0000002574738488)、[Xor](#ZH-CN_TOPIC_0000002574578874)”。<br>更新“[Dropout](#ZH-CN_TOPIC_0000002659215655) [Identity](#ZH-CN_TOPIC_0000002628696446) [GatherElements](#ZH-CN_TOPIC_0000002659095703) [ReduceLogSum](#ZH-CN_TOPIC_0000002628856352) [ReduceLogSumExp](#ZH-CN_TOPIC_0000002659215657) [Expand](#ZH-CN_TOPIC_0000002628696448) [Elu](#ZH-CN_TOPIC_0000002660394575) [Elu](#ZH-CN_TOPIC_0000002660274969)”。<br>更新“[DepthToSpace](#ZH-CN_TOPIC_0000002629955352) [SpaceToDepth](#ZH-CN_TOPIC_0000002660274511) [GRU](#ZH-CN_TOPIC_0000002631448488) [DepthToSpace](#ZH-CN_TOPIC_0000002660395017) [SpaceToDepth](#ZH-CN_TOPIC_0000002630115702)”。 |
| 03 | 2026-03-24 | 新增Onnx/TFLite算子规格：<br>更新“[ArgMax](#ZH-CN_TOPIC_0000002510106182)、[ArgMin](#ZH-CN_TOPIC_0000002541586163)、[ArgMax](#ZH-CN_TOPIC_0000002509946184)、[ArgMin](#ZH-CN_TOPIC_0000002541666173)”。<br>更新“[Div](#ZH-CN_TOPIC_0000002516261490)、[Clip](#ZH-CN_TOPIC_0000002552815891)、[Cast](#ZH-CN_TOPIC_0000002526464964)、[Div](#ZH-CN_TOPIC_0000002516421386)、[Cast](#ZH-CN_TOPIC_0000002557544885)”。<br>更新“[ReduceMax](#ZH-CN_TOPIC_0000002557401349)、[ReduceMin](#ZH-CN_TOPIC_0000002526441430)、[ReduceSum](#ZH-CN_TOPIC_0000002557481311)、[ReduceMean](#ZH-CN_TOPIC_0000002526281478)、[ReduceMax](#ZH-CN_TOPIC_0000002526421590)、[Sum](#ZH-CN_TOPIC_0000002557400507)、[Mean](#ZH-CN_TOPIC_0000002557400907)”。<br>更新“[Quantize](#ZH-CN_TOPIC_0000002557589767)、[Dequantize](#ZH-CN_TOPIC_0000002526509914)”。<br>更新“[Conv优化](#ZH-CN_TOPIC_0000002531633886)”。 |
| 02 | 2025-12-18 | 新增Onnx/TFLite算子规格：<br>更新“[Squeeze](#ZH-CN_TOPIC_0000002482800962)、[Unsqueeze](#ZH-CN_TOPIC_0000002482804754)、[Flatten](#ZH-CN_TOPIC_0000002515124725)、[Squeeze](#ZH-CN_TOPIC_0000002515130287)、[ExpandDims](#ZH-CN_TOPIC_0000002482930280)、[Slice](#ZH-CN_TOPIC_0000002528453623) [Slice](#ZH-CN_TOPIC_0000002528693597)”。<br>更新“[Abs](#ZH-CN_TOPIC_0000002485239888)、[Ceil](#ZH-CN_TOPIC_0000002517399797)、[Cos](#ZH-CN_TOPIC_0000002517479775)、[Exp](#ZH-CN_TOPIC_0000002485399854)、[Floor](#ZH-CN_TOPIC_0000002485239890)、[Log](#ZH-CN_TOPIC_0000002517399799)、[Round](#ZH-CN_TOPIC_0000002517479777)、[Sin](#ZH-CN_TOPIC_0000002485399856)、[Sqrt](#ZH-CN_TOPIC_0000002485239892)、[Abs](#ZH-CN_TOPIC_0000002485399132)、[Ceil](#ZH-CN_TOPIC_0000002517479769)、[Cos](#ZH-CN_TOPIC_0000002485399848)、[Exp](#ZH-CN_TOPIC_0000002485239884)、[Floor](#ZH-CN_TOPIC_0000002517399793)、[Log](#ZH-CN_TOPIC_0000002517479771)、[Round](#ZH-CN_TOPIC_0000002485399850)、[Rsqrt](#ZH-CN_TOPIC_0000002485239886)、[Sin](#ZH-CN_TOPIC_0000002517399795)、[Sqrt](#ZH-CN_TOPIC_0000002517479773)、[Square](#ZH-CN_TOPIC_0000002485399852)”。<br>更新“[BatchNormalization](#ZH-CN_TOPIC_0000002487717084)、[LayerNormalization](#ZH-CN_TOPIC_0000002519876961)、[LpNormalization](#ZH-CN_TOPIC_0000002519796953)、[L2Normalization](#ZH-CN_TOPIC_0000002487557124)”<br>更新“[GlobalMaxPool](#ZH-CN_TOPIC_0000002497018654)、[GlobalAveragePool](#ZH-CN_TOPIC_0000002496698634)”。<br>更新“[DepthwiseConv2D](#ZH-CN_TOPIC_0000002529736261)、[Transpose](#ZH-CN_TOPIC_0000002498475622)、[Transpose](#ZH-CN_TOPIC_0000002498635600)”。 |
| 01 | 2025-10-30 | 第一次正式版本发布。 |

# Converter\_lite工具使用环境搭建<a name="ZH-CN_TOPIC_0000002353769641" id="ZH-CN_TOPIC_0000002353769641"></a>

-   **[获取converter\_lite转换工具](#ZH-CN_TOPIC_0000002353895485)**  

-   **[设置环境变量](#ZH-CN_TOPIC_0000002353775693)**  

-   **[限制与约束](#ZH-CN_TOPIC_0000002319976756)**  

## 获取converter\_lite转换工具<a name="ZH-CN_TOPIC_0000002353895485" id="ZH-CN_TOPIC_0000002353895485"></a>

工具包获取：converter\_lite工具位于发布包的“mindspore-enterprise-lite-\{version\}-linux-x64/tools/converter/converter/converter\_lite”路径下，其中“version”为软件版本号。

本文档以converter\_lite转换工具的使用为例进行说明。

## 设置环境变量<a name="ZH-CN_TOPIC_0000002353775693" id="ZH-CN_TOPIC_0000002353775693"></a>

使用export方式设置环境变量后，环境变量仅在当前窗口有效。如果用户之前已在.bashrc文件中设置过环境变量，则需要在执行上述命令前，先手动删除原来设置的环境变量。

>![](public_sys-resources/icon-notice.gif) **须知：** 
>-   converter\_lite工具包依赖于GCC-14.3版本，可以通过点击链接访问官网（[GCC-14.3](https://github.com/gcc-mirror/gcc/releases/tag/releases%2Fgcc-14.3.0)），选择下载12.3.0版本。
>-   converter\_lite工具包依赖于Python3.11环境。
>-   “[必选环境变量](#section15381219152316)”中步骤必须按顺序执行，否则可能导致converter\_lite工具无法链接到动态库。

**必选环境变量<a name="section15381219152316" id="section15381219152316"></a>**

1.  设置converter\_lite工具动态库链接。

    ```
    export LD_LIBRARY_PATH=mindspore-enterprise-lite-{version}-linux-x64安装目录/tools/converter/lib:$LD_LIBRARY_PATH
    ```

1.  将Python3.11的路径添加到LD\_LIBRARY\_PATH中。

    ```
    export LD_LIBRARY_PATH=${py311_inptsll_path}/lib:$LD_LIBRARY_PATH
    ```

2.  将GCC的libstdc++6.0.30库路径添加到LD\_LIBRARY\_PATH中。

    ```
    export LD_LIBRARY_PATH=${libc++6.0.30_path}/libxx:$LD_LIBRARY_PATH
    ```

3.  切换到GCC中libstdc++.so.6.0.30的安装目录，为libstdc++建立软链接。

    ```
    ln -s libstdc++.so.6.0.30 libstdc++.so.6
    ```

**可选环境变量<a name="section119106478270"></a>**

若需要在RISCV平台进行部署推理，只需配置RISCV交叉编译链路径。

设置RISCV交叉编译工具链：

```
export HISPARK_RISCV_TOOLCHAIN_PATH=${sdk_install_path}/tools/bin/compiler/riscv/cc_riscv32_musl_105/
```

若需要在ARM平台进行部署推理，只需配置ARM交叉编译链路径。

设置ARM交叉编译工具链：

```
export HISPARK_ARM_TOOLCHAIN_PATH=${arm_compiler_path}/gcc-arm-v01c01-linux-musleabi/arm-v01c01-linux-musleabi-gcc/
```

## 限制与约束<a name="ZH-CN_TOPIC_0000002319976756" id="ZH-CN_TOPIC_0000002319976756"></a>

关于工具链版本的约束要求，如[表1](#table189802570121)所示。

**表 1**  工具链版本约束

<a name="table189802570121" id="table189802570121"></a>
<table><thead align="left"><tr id="row189814577129"><th class="cellrowborder" valign="top" width="50%" id="mcps1.2.3.1.1"><p id="p1575243117107"><a name="p1575243117107"></a><a name="p1575243117107"></a>工具链名称</p>
</th>
<th class="cellrowborder" valign="top" width="50%" id="mcps1.2.3.1.2"><p id="p19752133131013"><a name="p19752133131013"></a><a name="p19752133131013"></a>工具链版本</p>
</th>
</tr>
</thead>
<tbody><tr id="row89811757171215"><td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.1 "><p id="p167523317105"><a name="p167523317105"></a><a name="p167523317105"></a>GCC</p>
</td>
<td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.2 "><p id="p16752031121014"><a name="p16752031121014"></a><a name="p16752031121014"></a>14.3.0</p>
</td>
</tr>
<tr id="row179810570129"><td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.1 "><p id="p15486432191119"><a name="p15486432191119"></a><a name="p15486432191119"></a>CMake</p>
</td>
<td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.2 "><p id="p177528319108"><a name="p177528319108"></a><a name="p177528319108"></a>4.2.3</p>
</td>
</tr>
<tr id="row898115716128"><td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.1 "><p id="p379013544113"><a name="p379013544113"></a><a name="p379013544113"></a>riscv32-linux-musl-gcc</p>
</td>
<td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.2 "><p id="p117904548110"><a name="p117904548110"></a><a name="p117904548110"></a>(build ver100.090 2023-05-17) 7.3.0</p>
</td>
</tr>
<tr id="row139813576126"><td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.1 "><p id="p0752231101017"><a name="p0752231101017"></a><a name="p0752231101017"></a>riscv32-linux-musl-g++</p>
</td>
<td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.2 "><p id="p17527319106"><a name="p17527319106"></a><a name="p17527319106"></a>(build ver100.090 2023-05-17) 7.3.0</p>
</td>
</tr>
<tr id="row352812516528"><td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.1 "><p id="p105295259523"><a name="p105295259523"></a><a name="p105295259523"></a>arm-linux-musleabi-gcc</p>
</td>
<td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.2 "><p id="p125291225105214"><a name="p125291225105214"></a><a name="p125291225105214"></a>(musl-1.2.3 linux-5.10 V12CS61.003.020  2024-01-16 12:00:00) 10.3.0</p>
</td>
</tr>
<tr id="row41921831195219"><td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.1 "><p id="p5193153119526"><a name="p5193153119526"></a><a name="p5193153119526"></a>arm-linux-musleabi-g++</p>
</td>
<td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.2 "><p id="p15193203165218"><a name="p15193203165218"></a><a name="p15193203165218"></a>(musl-1.2.3 linux-5.10 V12CS61.003.020  2024-01-16 12:00:00) 10.3.0</p>
</td>
</tr>
<tr id="row2982557181213"><td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.1 "><p id="p2753431131020"><a name="p2753431131020"></a><a name="p2753431131020"></a>Ubuntu</p>
</td>
<td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.2 "><p id="p19753113191012"><a name="p19753113191012"></a><a name="p19753113191012"></a>22.04</p>
</td>
</tr>
<tr id="row14120345152815"><td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.1 "><p id="p8121194513282"><a name="p8121194513282"></a><a name="p8121194513282"></a>Python</p>
</td>
<td class="cellrowborder" valign="top" width="50%" headers="mcps1.2.3.1.2 "><p id="p10816952102817"><a name="p10816952102817"></a><a name="p10816952102817"></a>3.11</p>
</td>
</tr>
</tbody>
</table>

# 快速入门<a name="ZH-CN_TOPIC_0000002319973524" id="ZH-CN_TOPIC_0000002319973524"></a>

本章节以TFLite与ONNX框架的MNIST模型转换为例，演示如何快速转换生成Micro工程推理代码。

-   **[开源框架的TFLite/ONNX模型转换为Micro工程](#ZH-CN_TOPIC_0000002353945877)**  

## 开源框架的TFLite/ONNX模型转换为Micro工程<a name="ZH-CN_TOPIC_0000002353945877" id="ZH-CN_TOPIC_0000002353945877"></a>

1.  获取开源框架MNIST网络模型。
    -   TFLite模型：从链接中获取MNIST网络的模型文件：[mnist网络模型](https://download.mindspore.cn/model_zoo/official/lite/quick_start/micro/mnist.tar.gz)，下载后解压得到mnist.tflite、mnist.tflite.ms.bin（MNIST输入数据）、mnist.tflite.ms.out（标杆输出数据，可用于精度对比）。该模型为已经训练完成的MNIST分类模型，为TFLite模型，将mnist.tflite模型拷贝到开发环境任意目录，例如上传到“$HOME/module/”目录下。
    -   ONNX模型：从链接中获取mnist网络的模型文件：[mnist网络模型](https://github.com/onnx/models/tree/main/validated/vision/classification/mnist/model)，下载解压得到mnist-7.onnx，该模型为已经训练完成的MNIST分类模型，为ONNX模型，将mnist-7.onnx模型拷贝到开发环境任意目录，例如上传到“$HOME/module/”目录下。

2.  获取converter\_lite的压缩包，并进行解压。

    ```
    tar -xvf mindspore-enterprise-lite-{version}-linux-x64.tar.gz
    ```

3.  将转换工具运行时所需的动态链接库添加到环境变量LD\_LIBRARY\_PATH中。

    ```
    export LD_LIBRARY_PATH=mindspore-enterprise-lite-{version}-linux-x64/tools/converter/lib/tools/converter/lib:${LD_LIBRARY_PATH}
    ```

4.  进入转换目录。

    ```
    cd mindspore-enterprise-lite-{version}-linux-x64安装目录/tools/converter/converter
    ```

5.  设置Micro配置项。

    场景一：以RISCV平台部署为例，将原模型直接转换为Micro工程目录。

    ```
    #控制micro配置项
    [micro_param]
    # 支持code-gen生成Micro工程代码
    enable_micro=true
    # 支持x86,RISCV,ARM32平台
    target=RISCV
    # 配置是否并行推理，当前仅支持单线程推理
    support_parallel=false
    ```

    场景二：以RISCV平台部署为例，将FP32原模型转换为int8量化Micro工程目录，具体参数请参见“[参数说明](#ZH-CN_TOPIC_0000002319906348)”章节。

    ```
    #控制micro配置项
    [micro_param]
    # 支持code-gen生成Micro工程代码
    enable_micro=true
    # 支持x86,RISCV平台
    target=RISCV
    # 配置是否并行推理，当前仅支持单线程推理
    support_parallel=false
    #控制通用量化参数配置项
    [common_quant_param]
    # 当前仅支持全量化方式
    quant_type=FULL_QUANT
    # 全量化仅支持8bit量化
    bit_num=8
    # 配置校准数据集参数
    [data_preprocess_param]
    #关于calibrate_path解释为前半部分是网络的输入名称，后半部分是输入存放路径，详细设置请参见“5-参数说明”章节
    calibrate_path=input:${HOME}/module/dataset/quant_data
    #数据集大小，这里必须与calibrate_path目录下的数据集大小对应，请参见“5-参数说明”章节
    calibrate_size=1
    #数据集格式，仅支持bin校准数据集格式，且该数据集下不允许存储非bin格式文件
    input_type=BIN
    #全量化参数配置项
    [full_quant_param]
    #激活值量化算法选择MAX_MIN，当前仅支持MAX_MIN量化算法
    activation_quant_method=MAX_MIN
    #是否开启数据集校准
    bias_correction=true
    #扩展量化算子,提升量化精度且牺牲性能可关闭
    enable_all_ops=true
    ```

    场景三：以RISCV平台部署为例，将原模型转换为int8量化训练Micro工程目录，具体参数请参见“[参数说明](#ZH-CN_TOPIC_0000002319906348)”章节。

    ```
    #控制micro配置项
    [micro_param]
    # 支持code-gen生成Micro工程代码
    enable_micro=true
    # 支持x86,RISCV平台
    target=RISCV
    # 配置是否并行推理，当前仅支持单线程推理
    support_parallel=false
    #控制通用量化参数配置项
    [common_quant_param]
    # 当前仅支持全量化方式
    quant_type=FULL_QUANT
    # 全量化仅支持8bit量化
    bit_num=8
    # 配置校准数据集参数
    [data_preprocess_param]
    #关于calibrate_path解释为前半部分是网络的输入名称，后半部分是输入存放路径，详细设置请参见“5-参数说明”章节
    calibrate_path=input:${HOME}/module/dataset/quant_data
    #数据集大小，这里必须与calibrate_path目录下的数据集大小对应，请参见“5-参数说明”章节
    calibrate_size=1
    #数据集格式，仅支持bin校准数据集格式，且该数据集下不允许存储非bin格式文件
    input_type=BIN
    #全量化参数配置项
    [full_quant_param]
    #激活值量化算法选择MAX_MIN，当前仅支持MAX_MIN量化算法
    activation_quant_method=MAX_MIN
    #是否开启数据集校准
    bias_correction=true
    #扩展量化算子,提升量化精度且牺牲性能可关闭
    enable_all_ops=true
    #INT8量化训练参数配置项
    [train]
    #QAS INT8量化训练模式；配置后自动生成训练模式Micro工程
    train_mode=qas_int8
    #是否输出训练图和内存规划信息
    dump_training_graph=false
    #当前仅支持softmax_cross_entropy
    loss=softmax_cross_entropy
    #标签张量名称
    label_tensor_name=label
    #当前仅支持sgd_with_momentum
    optimizer=sgd_with_momentum
    #学习率，必须大于0
    learning_rate=0.005
    #动量，必须大于等于0
    momentum=0.9
    #当前仅支持批大小为1
    batch_size=1
    ```

    场景四：以RISCV平台部署为例，将FP32原模型转换为FP32训练Micro工程目录。FP32训练与量化训练使用不同的训练配置，
    不需要配置量化参数和校准数据集。

    ```
    #控制micro配置项
    [micro_param]
    #支持code-gen生成Micro工程代码
    enable_micro=true
    #支持x86、RISCV平台
    target=RISCV
    #配置是否并行执行，当前仅支持单线程
    support_parallel=false

    #FP32端侧训练参数配置项
    [train]
    #FP32训练模式；配置后自动生成训练模式Micro工程
    train_mode=fp32
    #支持softmax_cross_entropy、mean_squared_error
    loss=softmax_cross_entropy
    #标签或目标张量名称
    label_tensor_name=label
    #支持sgd_with_momentum、adam
    optimizer=sgd_with_momentum
    #学习率，必须大于0
    learning_rate=0.005
    #仅sgd_with_momentum使用，必须大于等于0
    momentum=0.9
    #当前仅支持批大小为1
    batch_size=1
    ```

    使用Adam优化器时，将`optimizer`配置为`adam`，并删除`momentum`。Adam参数`beta1`、`beta2`和`epsilon`
    可以省略，默认值依次为0.9、0.999和1e-8。

6.  执行如下命令生成Micro工程代码（如下命令中使用的目录以及文件均为样例，请以实际为准）**。**
    1.  TFLite模型converter\_lite转换命令：

        ```
        #转换TFLite框架的MNIST模型生成Micro工程代码，converter_lite转换时参数请参见“5-参数说明”章节
        ./converter_lite --fmk=TFLITE --modelFile=mnist.tflite --outputFile=mnist --configFile=micro.cfg --encryption=false --inputDataFormat=NHWC --outputDataFormat=NHWC --inputDataType=FLOAT --outputDataType=FLOAT
        ```

    2.  ONNX模型converter\_lite转换命令：

        ```
        #转换ONNX框架的MNIST模型生成Micro工程代码，converter_lite转换时参数请参见“5-参数说明”章节
        ./converter_lite --fmk=ONNX --modelFile=mnist-7.onnx --outputFile=mnist --configFile=micro.cfg --encryption=false --inputDataFormat=NCHW --outputDataFormat=NCHW --inputDataType=FLOAT --outputDataType=FLOAT
        ```

    3.  运行成功后的结果显示为：

        ```
        CONVERT RESULT SUCCESS:0
        ```

7.  若想快速体验转换后的Micro工程代码的编译与推理，请准备好环境、符合模型输入要求的\*.bin输入数据以及Micro工程代码，具体操作请参见“[初级功能](#ZH-CN_TOPIC_0000002319904560)”章节。

# 基础知识<a name="ZH-CN_TOPIC_0000002319816916" id="ZH-CN_TOPIC_0000002319816916"></a>

-   **[工具功能架构](#ZH-CN_TOPIC_0000002320039182)**  

-   **[工具运行流程](#ZH-CN_TOPIC_0000002353838137)**  

## 工具功能架构<a name="ZH-CN_TOPIC_0000002320039182" id="ZH-CN_TOPIC_0000002320039182"></a>

converter\_lite工具功能架构设计如[图1](#fig19815386014)所示。

**图 1**  converter\_lite工具功能架构<a name="fig19815386014" id="fig19815386014"></a>  
![](figures/converter_lite工具功能架构.png "converter_lite工具功能架构")

开源框架网络模型场景的详细流程如下：

1.  开源框架网络模型经过Parser解析后，转换为中间态IR Graph。
2.  中间态IR经过图拆分与图编译优化操作后，根据节点注册对应规格算子。
3.  生成模型权重数据、头文件与C源码等Micro工程代码。
4.  通过gcc或者RISCV交叉编译工具链生成静态库文件，并将其上传到指定平台执行推理。

## 工具运行流程<a name="ZH-CN_TOPIC_0000002353838137" id="ZH-CN_TOPIC_0000002353838137"></a>

使用converter\_lite工具将模型转成Micro工程代码的总体流程如[图1](#fig1738314214294)所示。

**图 1**  converter\_lite工具运行流程图<a name="fig1738314214294" id="fig1738314214294"></a>  
![](figures/converter_lite工具运行流程图.png "converter_lite工具运行流程图")

详细流程说明如下：

1.  使用converter\_lite工具之前，请先在开发环境中安装converter\_lite工具包，并获取相关路径下的converter\_lite工具。详细说明请参见“[Converter\_lite工具使用环境搭建](#ZH-CN_TOPIC_0000002353769641)”章节。
2.  准备要进行转换的模型文件，并将其上传到开发环境。
3.  设置Micro配置项，可根据需要进行量化与非量化的参数配置。
4.  使用converter\_lite工具进行模型转换，生成Micro工程代码。
5.  编译Micro工程。

# 初级功能<a name="ZH-CN_TOPIC_0000002319904560" id="ZH-CN_TOPIC_0000002319904560"></a>

本章节介绍如何在“[基础知识](#ZH-CN_TOPIC_0000002319816916)”Micro工程代码的基础上进行编译部署推理。当前支持模型规格如下：

-   FP32 TFLite模型FP32 Micro推理。
-   FP32 TFLite模型INT8量化Micro推理。
-   INT8 TFLite模型INT8 Micro推理。
-   FP32 ONNX模型FP32 Micro推理。
-   FP32 ONNX模型INT8量化Micro推理。

支持推理平台为：x86\_64平台（x86部署可以为板端调试提供精度标杆）与RISCV平台。

支持后端类型：CPU单核单线程。

-   **[RISCV平台编译部署](#ZH-CN_TOPIC_0000002354163653)**  

-   **[ARM平台编译部署](#ZH-CN_TOPIC_0000002590121500)**  

-   **[基于x86\_64平台精度调试](#ZH-CN_TOPIC_0000002320125106)**  

## RISCV平台编译部署<a name="ZH-CN_TOPIC_0000002354163653" id="ZH-CN_TOPIC_0000002354163653"></a>

本节以FP32的mnist.onnx模型为例，介绍如何利用生成的Micro INT8量化推理代码，并在RISCV平台部署推理。

1.  converter\_lite工具转换开源框架模型生成Micro工程，请参见“[快速入门](#ZH-CN_TOPIC_0000002319973524)”章节。

    >![](public_sys-resources/icon-notice.gif) **须知：** 
    >-   在使用converter\_lite转换命令时，--fmk选项必须与AI模型的开源框架对应，否则将导致转换失败。
    >-   micro.cfg的target必须选择RISCV，并且需要按照“[开源框架的TFLite/ONNX模型转换为Micro工程](#ZH-CN_TOPIC_0000002353945877)”章节中的[5](#li1849371193511)场景二进行配置。
    >-   RISCV平台部署编译需要依赖海思提供的RISCV编译工具链，需下载相应的工具包。

2.  切换到Micro工程目录。

    ```
    #切换到名为micro的Micro工程目录
    cd $HOME/micro/
    ```

1.  下载并解压converter\_lite工具包。

    ```
    #进入到算子库在开发环境的路径
    cd ${mindspore-enterprise-lite-{version}-linux-x64安装目录}
    #解压tar包
    tar -xvf mindspore-enterprise-lite-{version}-linux-x64.tar.gz
    ```

1.  在Micro工程目录新建“build\_riscv.sh”脚本，配置如下：

    ```
    #mindspore-enterprise-lite-{version}-linux-x64为converter_lite工具包在开发环境的路径，sdk_path为海思工具包在开发环境的路径
    rm -rf build
    cmake -S . -B build -D OP_LIB="${mindspore-enterprise-lite-{version}-linux-x64安装目录}/tools/codegen/lib/riscv/libnnacl.a" \
        -D WRAPPER_LIB="${mindspore-enterprise-lite-{version}-linux-x64安装目录}/tools/codegen/lib/riscv/libwrapper.a" -D RISCV_TOOLCHAIN_PATH="${sdk_path}/tools/bin/compiler/riscv/cc_riscv32_musl_b090/cc_riscv32_musl/bin" \
        -D PKG_PATH="${mindspore-enterprise-lite-{version}-linux-x64安装目录}"
    cd build
    make -j4
    ```

1.  在"Micro工程目录/build ”目录中生成算子执行文件，目录如下：

    ```
    Micro工程目录/build                                       # MCU推理代码目录
    ├── CMakeCache.txt
    ├── CMakeFiles
    ├── cmake_install.cmake
    ├── libmicro_runtime.a			          # 算子运行时静态库
    ├── Makefile
    └── src											
        ├── CMakeFiles
        ├── cmake_install.cmake
        ├── libnet.a				          # 算子定义与实现的静态库
        └── Makefile
    ```

    代码编译成功，屏幕显示结果如下：

    ```
    [ 50%] Built target net
    [100%] Built target micro_runtime
    ```

1.  将编译产物libnet.a与libmicro\_runtime.a上传至海思工具包再次编译得到编译产物\*.fwpkg文件。然后，使用海思工具在Windows平台烧录推理，具体步骤请参考对应的application/samples/ai中的readme.md。

## ARM平台编译部署<a name="ZH-CN_TOPIC_0000002590121500" id="ZH-CN_TOPIC_0000002590121500"></a>

本节以FP32的mnist.onnx模型为例，介绍如何利用生成的Micro INT8量化推理代码，并在RISCV平台部署推理。

1.  converter\_lite工具转换开源框架模型生成Micro工程，请参见“[快速入门](#ZH-CN_TOPIC_0000002319973524)”章节。

    >![](public_sys-resources/icon-notice.gif) **须知：** 
    >-   在使用converter\_lite转换命令时，--fmk选项必须与AI模型的开源框架对应，否则将导致转换失败。
    >-   micro.cfg的target必须选择ARM32，并且需要按照“[开源框架的TFLite/ONNX模型转换为Micro工程](#ZH-CN_TOPIC_0000002353945877)”章节中的[5](#li1849371193511)场景二进行配置。
    >-   ARM平台部署编译需要依赖海思提供的ARM编译工具链，需下载相应的工具包。

2.  切换到Micro工程目录。

    ```
    #切换到名为micro的Micro工程目录
    cd $HOME/micro/
    ```

1.  下载并解压converter\_lite工具包。

    ```
    #进入到算子库在开发环境的路径
    cd ${mindspore-enterprise-lite-{version}-linux-x64安装目录}
    #解压tar包
    tar -xvf mindspore-enterprise-lite-{version}-linux-x64.tar.gz
    ```

## 基于x86\_64平台精度调试<a name="ZH-CN_TOPIC_0000002320125106" id="ZH-CN_TOPIC_0000002320125106"></a>

本节以mnist.tflite模型为例，介绍在x86\_64平台上的编译和部署过程（x86部署可以为板端调试提供精度标杆）。

1.  使用converter\_lite工具将开源框架模型转换为Micro工程，请参见“[快速入门](#ZH-CN_TOPIC_0000002319973524)”章节

    >![](public_sys-resources/icon-notice.gif) **须知：** 
    >-   在使用converter\_lite转换命令时，--fmk选项必须与AI模型的开源框架对应，否则将导致转换失败，且需要配置--encryption=false参数。
    >-   micro.cfg的target必须选择x86，且需要按照“[开源框架的TFLite/ONNX模型转换为Micro工程](#ZH-CN_TOPIC_0000002353945877)”章节中的[5](#li1849371193511)场景一进行配置。

1.  切换到Micro工程目录。

    ```
    #切换到Micro工程目录，假设工程目录叫micro
    cd $HOME/micro/
    ```

1.  Micro工程目录结构如下，其中benchmark目录为x86\_64部署的样例工程，调用相关Micro API接口。

    ```
    micro                          # 指定的生成代码根目录名称
    ├── benchmark                  # 对模型推理代码进行集成调用的benchmark例程
    │   ├── benchmark.c
    │   ├── calib_output.c
    │   ├── calib_output.h
    │   ├── load_input.c
    │   └── load_input.h
    ├── CMakeLists.txt             # benchmark例程的cmake工程文件
    ├── include                    # 头文件
    │   ├── model_handle.h
    └── src                        # 模型推理代码目录
        ├── allocator.c
        ├── allocator.h    
        ├── CMakeLists.txt
        ├── context.c
        ├── context.h
        ├── model.c
        ├── model.h
        ├── net.cmake
        ├── tensor.c
        └── tensor.h
    ```

1.  gcc编译生成可执行文件。
    -   切换到converter\_lite工具包算子库路径，然后将算子库拷贝到父级目录。

        ```
        cd "mindspore-enterprise-lite-{version}-linux-x64安装目录"/tools/codegen/lib/cpu
        将算子库拷贝到父级目录
        cp libnnacl.a libwrapper.a ../
        ```

    -   创建编译目录，gcc编译benchmark可执行环境。

        ```
        #创建并且切换到编译目录
        mkdir build && cd build
        #gcc编译生成可执行文件
        cmake -DPKG_PATH="mindspore-enterprise-lite-{version}-linux-x64安装目录" ..
        make
        ```

    -   若Micro工程代码编译成功，屏幕将显示如下结果，此时在“Micro工程目录/build/src/”目录下会生成libnet.a。

        ```
        [100%] Linking C executable benchmark
        [100%] Built target benchmark
        ```

1.  运行benchmark推理流程，输入bin文件可以从mnist.tar.gz获取，也可以自行构造随机输入。
    -   构造随机输入数据，下面给出生成\[0,1\]范围内Fp32随机数据的Python参考脚本，输出结果为mnist.bin文件。

        >![](public_sys-resources/icon-notice.gif) **须知：** 
        >-   随机输入数据可以用于Micro工程推理，也可用于Micro INT8量化校准数据集。
        >-   若用户有真实数据集，可转换为Bin格式，无需参考下面的随机数据构造脚本。

        ```
        #随机输入构造脚本，仅供参考
        import numpy as np
        import os
        
        def generate_random_data(output_file, shape=(1, 25, 24, 1), dtype=np.float32):
            # 生成[0, 1)范围内的随机数
            random_data = np.random.uniform(low=0.0, high=1.0, size=shape).astype(dtype)
        
            # 手动将部分点设为1.0，确保范围包含1
            total_elements = np.prod(shape)
            if total_elements > 0:
                # 将最后一个元素设为1.0
                random_data.flat[-1] = 1.0
                # 再随机选一个元素设为0.0，确保包含0
                random_data.flat[np.random.randint(0, total_elements)] = 0.0
        
            # 验证数据范围
            min_val = np.min(random_data)
            max_val = np.max(random_data)
            assert min_val >= 0.0, f"数据最小值{min_val}小于0"
            assert max_val <= 1.0, f"数据最大值{max_val}大于1"
        
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
            # 保存为二进制文件
            with open(output_file, 'wb') as f:
                random_data.tofile(f)
        
            # 输出信息
            print(f"数据维度: {random_data.shape}")
            print(f"数据类型: {random_data.dtype}")
            print(f"数据范围: [{min_val:.6f}, {max_val:.6f}]")
            print("数据前5个元素预览:", random_data.flatten()[:5])
        
        if __name__ == "__main__":
            # 输出文件路径
            output_file = "mnist.bin"
        
            # 生成并保存数据
            generate_random_data(output_file)
        ```

    -   运行benchmark，在x86\_64平台完成推理。

        ```
        #benchmark是精度评测的可执行文件，用法为./benchmark "mnist.tflite.ms.bin路径" "net0.bin路径"，benchmark第一个参数是输入数据，第二个参数是模型权重文件(模型文件在benchmark目录同级的src/model0目录下)。假设mnist.tflite.ms.bin相对路径为"../../mnist/mnist.tflite.ms.bin"，net0.bin相对路径为"net0.bin"。执行命令可参考如下：
        ./benchmark ../../mnist/mnist.tflite.ms.bin ../src/model0/net0.bin
        ```

        推理成功，屏幕显示结果应该如下：

        ```
        =======run benchmark======
        ThreadNum: 1.
        BindMode: 0.
        input 0: ../../mnist/mnist.tflite.ms.bin
        Running warm up loops...========run success=======
        
        outputs: 
        name: Identity, DataType: 43, Elements: 10, Shape: [1 10 ], Data: 
        0.000036, 0.000000, 0.009328, 0.000032, 0.000011, 0.000002, 0.000000, 0.000000, 0.990591, 0.000000, 
        ========run success=======
        ```

# 参数说明<a name="ZH-CN_TOPIC_0000002319906348" id="ZH-CN_TOPIC_0000002319906348"></a>

-   **[总体约束](#ZH-CN_TOPIC_0000002353985077)**  

-   **[参数概览](#ZH-CN_TOPIC_0000002354104885)**  

-   **[基础功能参数](#ZH-CN_TOPIC_0000002320066172)**  

## 总体约束<a name="ZH-CN_TOPIC_0000002353985077" id="ZH-CN_TOPIC_0000002353985077"></a>

针对converter\_lite转换工具总体约束如下：

-   支持ONNX、TFLite开源框架的模型转换，当原始框架类型为ONNX、TFLite时，输入类型应为FP32、INT8、UINT8。
-   开源框架模型类型应与--fmk配置参数名称必须保持一致（包括大小写）。
-   在使用全量化转换时，必须构建校准输入数据集，且按照模型的输入名称设置Micro配置项。校准数据集和实际输入格式为BIN（即数据类型为.bin二进制文件），并且该路径下不允许存在其他格式文件。

## 参数概览<a name="ZH-CN_TOPIC_0000002354104885" id="ZH-CN_TOPIC_0000002354104885"></a>

>![](public_sys-resources/icon-notice.gif) **须知：** 
>-   如果通过./converter\_lite --help命令查询出的参数未在[表1](#table54678511574)中解释，则说明该参数预留或者适用于其他芯片版本，用户无需关注。
>-   使用converter\_lite命令进行Micro工程代码生成时，支持模型量化与非量化，x86\_64与RISCV编译，用户可根据实际情况进行选择。

converter\_lite参数概览如[表1](#table54678511574)所示，详细说明请参见“[基础功能参数](#ZH-CN_TOPIC_0000002320066172)”章节。

**表 1**  converter\_lite工具参数概览

<a name="table54678511574" id="table54678511574"></a>
<table><thead align="left"><tr id="row184680516710"><th class="cellrowborder" valign="top" width="30.65%" id="mcps1.2.6.1.1"><p id="p646815111711"><a name="p646815111711"></a><a name="p646815111711"></a>convert lite参数名称</p>
</th>
<th class="cellrowborder" valign="top" width="9.35%" id="mcps1.2.6.1.2"><p id="p16468651678"><a name="p16468651678"></a><a name="p16468651678"></a>是否必选</p>
</th>
<th class="cellrowborder" valign="top" width="26.939999999999998%" id="mcps1.2.6.1.3"><p id="p946815512710"><a name="p946815512710"></a><a name="p946815512710"></a>参数说明</p>
</th>
<th class="cellrowborder" valign="top" width="20.73%" id="mcps1.2.6.1.4"><p id="p94683515720"><a name="p94683515720"></a><a name="p94683515720"></a>取值范围</p>
</th>
<th class="cellrowborder" valign="top" width="12.33%" id="mcps1.2.6.1.5"><p id="p19468145120716"><a name="p19468145120716"></a><a name="p19468145120716"></a>默认值</p>
</th>
</tr>
</thead>
<tbody><tr id="row346810518716"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p246885116714"><a name="p246885116714"></a><a name="p246885116714"></a>--help</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p4468351174"><a name="p4468351174"></a><a name="p4468351174"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p24681451776"><a name="p24681451776"></a><a name="p24681451776"></a>打印全部帮助信息。</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p1546825119713"><a name="p1546825119713"></a><a name="p1546825119713"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p13469155112711"><a name="p13469155112711"></a><a name="p13469155112711"></a>-</p>
</td>
</tr>
<tr id="row1746919511879"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p5469951574"><a name="p5469951574"></a><a name="p5469951574"></a>--fmk=<FMK></p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p546913511973"><a name="p546913511973"></a><a name="p546913511973"></a>是</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p546918513716"><a name="p546918513716"></a><a name="p546918513716"></a>输入模型的原始格式。</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p114691511972"><a name="p114691511972"></a><a name="p114691511972"></a>TFLITE/ONNX</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p1046918514716"><a name="p1046918514716"></a><a name="p1046918514716"></a>-</p>
</td>
</tr>
<tr id="row1946911511176"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p44691051370"><a name="p44691051370"></a><a name="p44691051370"></a>--modelFile=<MODELFILE></p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p846935120717"><a name="p846935120717"></a><a name="p846935120717"></a>是</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p9469135110713"><a name="p9469135110713"></a><a name="p9469135110713"></a>输入模型的路径。</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p746918516712"><a name="p746918516712"></a><a name="p746918516712"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p14691451772"><a name="p14691451772"></a><a name="p14691451772"></a>-</p>
</td>
</tr>
<tr id="row204696511578"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p9469135112711"><a name="p9469135112711"></a><a name="p9469135112711"></a>--outputFile=<OUTPUTFILE></p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p84691551272"><a name="p84691551272"></a><a name="p84691551272"></a>是</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p1446925111720"><a name="p1446925111720"></a><a name="p1446925111720"></a>转成Micro工程代码的路径。</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p946911511975"><a name="p946911511975"></a><a name="p946911511975"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p164696511777"><a name="p164696511777"></a><a name="p164696511777"></a>-</p>
</td>
</tr>
<tr id="row7469751173"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p1646914511473"><a name="p1646914511473"></a><a name="p1646914511473"></a>--configFile=<CONFIGFILE></p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p15470135114711"><a name="p15470135114711"></a><a name="p15470135114711"></a>是</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p204701751570"><a name="p204701751570"></a><a name="p204701751570"></a>设置转换Micro工程的配置项。</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p14470115119718"><a name="p14470115119718"></a><a name="p14470115119718"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p15470951875"><a name="p15470951875"></a><a name="p15470951875"></a>-</p>
</td>
</tr>
<tr id="row44706511273"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p94709511173"><a name="p94709511173"></a><a name="p94709511173"></a>--encryption=<ENCRYPTION></p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p1470185115717"><a name="p1470185115717"></a><a name="p1470185115717"></a>是</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p44707511475"><a name="p44707511475"></a><a name="p44707511475"></a>不支持设置，取值范围暂不支持true，使用时必须配置为false。</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p0470105110715"><a name="p0470105110715"></a><a name="p0470105110715"></a>false</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p583795215246"><a name="p583795215246"></a><a name="p583795215246"></a>-</p>
</td>
</tr>
<tr id="row125531536196"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p1655313151916"><a name="p1655313151916"></a><a name="p1655313151916"></a>--inputDataFormat</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p125531315199"><a name="p125531315199"></a><a name="p125531315199"></a>是</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p655312318196"><a name="p655312318196"></a><a name="p655312318196"></a>设定导出模型的输入format，其中，源模型为ONNX框架应当设置为NCHW，为TFLITE框架应当设置为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p75531839194"><a name="p75531839194"></a><a name="p75531839194"></a>NCHW/NHWC</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p1855319311193"><a name="p1855319311193"></a><a name="p1855319311193"></a>-</p>
</td>
</tr>
<tr id="row1842192513569"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p146837292563"><a name="p146837292563"></a><a name="p146837292563"></a>--outputDataFormat</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p7683029115614"><a name="p7683029115614"></a><a name="p7683029115614"></a>是</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p20683229135616"><a name="p20683229135616"></a><a name="p20683229135616"></a>设定导出模型的输出format，其中源模型为ONNX框架应当设置为NCHW，为TFLITE框架应当设置为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p1468392912568"><a name="p1468392912568"></a><a name="p1468392912568"></a>NCHW/NHWC</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p4683152919564"><a name="p4683152919564"></a><a name="p4683152919564"></a>-</p>
</td>
</tr>
<tr id="row9681102215618"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p74838317563"><a name="p74838317563"></a><a name="p74838317563"></a>--inputDataType</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p1848393195615"><a name="p1848393195615"></a><a name="p1848393195615"></a>是</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p194838311568"><a name="p194838311568"></a><a name="p194838311568"></a>设定导出模型的输入数据类型，自研量化时类型与原始模型保持不变，TFLite第三方量化与量化后数据类型保持一致。</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p748393175618"><a name="p748393175618"></a><a name="p748393175618"></a>FLOAT/INT8/UINT8</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p13483183117567"><a name="p13483183117567"></a><a name="p13483183117567"></a>-</p>
</td>
</tr>
<tr id="row199831176564"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p838010338562"><a name="p838010338562"></a><a name="p838010338562"></a>--outputDataType</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p338013330568"><a name="p338013330568"></a><a name="p338013330568"></a>是</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p1589919193589"><a name="p1589919193589"></a><a name="p1589919193589"></a>设定导出模型的输出数据类型，自研量化时类型与原始模型保持不变，TFLite第三方量化与量化后数据类型保持一致。</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p1146811819571"><a name="p1146811819571"></a><a name="p1146811819571"></a>FLOAT/INT8/UINT8</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p15380143312563"><a name="p15380143312563"></a><a name="p15380143312563"></a>-</p>
</td>
</tr>
<tr id="row1151175018719"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p11511250474"><a name="p11511250474"></a><a name="p11511250474"></a>--decryptKey</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p15511175013718"><a name="p15511175013718"></a><a name="p15511175013718"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p11511350470"><a name="p11511350470"></a><a name="p11511350470"></a>解密密钥，Micro不支持</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p55112050676"><a name="p55112050676"></a><a name="p55112050676"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p145117507710"><a name="p145117507710"></a><a name="p145117507710"></a>-</p>
</td>
</tr>
<tr id="row19471102315813"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p1847216235815"><a name="p1847216235815"></a><a name="p1847216235815"></a>--encryptKey</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p44721623183"><a name="p44721623183"></a><a name="p44721623183"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p1472423684"><a name="p1472423684"></a><a name="p1472423684"></a>加密密钥，Micro不支持</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p1247216232815"><a name="p1247216232815"></a><a name="p1247216232815"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p144720236815"><a name="p144720236815"></a><a name="p144720236815"></a>-</p>
</td>
</tr>
<tr id="row192831846092"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p4283246795"><a name="p4283246795"></a><a name="p4283246795"></a>--infer</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p6284346899"><a name="p6284346899"></a><a name="p6284346899"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p728418461393"><a name="p728418461393"></a><a name="p728418461393"></a>预推理功能开关，Micro不支持</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p32846461693"><a name="p32846461693"></a><a name="p32846461693"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p172841746897"><a name="p172841746897"></a><a name="p172841746897"></a>false</p>
</td>
</tr>
<tr id="row678363621019"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p178353691010"><a name="p178353691010"></a><a name="p178353691010"></a>--fp16</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p87834367102"><a name="p87834367102"></a><a name="p87834367102"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p177831236101019"><a name="p177831236101019"></a><a name="p177831236101019"></a>开启fp16推理开关，Micro不支持</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p18783036101019"><a name="p18783036101019"></a><a name="p18783036101019"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p7783163611106"><a name="p7783163611106"></a><a name="p7783163611106"></a>false</p>
</td>
</tr>
<tr id="row16562194115101"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p1456334118107"><a name="p1456334118107"></a><a name="p1456334118107"></a>--optimize</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p7563134181013"><a name="p7563134181013"></a><a name="p7563134181013"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p1456324171017"><a name="p1456324171017"></a><a name="p1456324171017"></a>Micro仅支持general，不支持额外配置</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p15563204131014"><a name="p15563204131014"></a><a name="p15563204131014"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p65638419104"><a name="p65638419104"></a><a name="p65638419104"></a>general</p>
</td>
</tr>
<tr id="row19753164015123"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p9753140201219"><a name="p9753140201219"></a><a name="p9753140201219"></a>--optimizeTransformer</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p1075354017128"><a name="p1075354017128"></a><a name="p1075354017128"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p97531840151212"><a name="p97531840151212"></a><a name="p97531840151212"></a>Micro开启Transformer融合，Micro不支持</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p12753154081215"><a name="p12753154081215"></a><a name="p12753154081215"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p15753144031216"><a name="p15753144031216"></a><a name="p15753144031216"></a>false</p>
</td>
</tr>
<tr id="row63671011171316"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p103671511161313"><a name="p103671511161313"></a><a name="p103671511161313"></a>--saveType</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p1236711101311"><a name="p1236711101311"></a><a name="p1236711101311"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p1236771114131"><a name="p1236771114131"></a><a name="p1236771114131"></a>导出中间IR文件格式，Micro暂不支持其他配置</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p14367161111133"><a name="p14367161111133"></a><a name="p14367161111133"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p13367211101310"><a name="p13367211101310"></a><a name="p13367211101310"></a>MINDIR_LITE</p>
</td>
</tr>
<tr id="row33574131413"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p18351043148"><a name="p18351043148"></a><a name="p18351043148"></a>--trainModel</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p935174101418"><a name="p935174101418"></a><a name="p935174101418"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p8351347149"><a name="p8351347149"></a><a name="p8351347149"></a>端侧训练开关，Micro暂不支持</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p6350471414"><a name="p6350471414"></a><a name="p6350471414"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p153510441419"><a name="p153510441419"></a><a name="p153510441419"></a>false</p>
</td>
</tr>
<tr id="row1645913412146"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p74594412146"><a name="p74594412146"></a><a name="p74594412146"></a>--weightFile</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p34591541151411"><a name="p34591541151411"></a><a name="p34591541151411"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p184591341171416"><a name="p184591341171416"></a><a name="p184591341171416"></a>caffe格式模型配套的weight文件导入，Micro暂不支持</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p184594418149"><a name="p184594418149"></a><a name="p184594418149"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p645914191413"><a name="p645914191413"></a><a name="p645914191413"></a>-</p>
</td>
</tr>
<tr id="row16351122811455"><td class="cellrowborder" valign="top" width="30.65%" headers="mcps1.2.6.1.1 "><p id="p1135132884514"><a name="p1135132884514"></a><a name="p1135132884514"></a>--riscvOpt</p>
</td>
<td class="cellrowborder" valign="top" width="9.35%" headers="mcps1.2.6.1.2 "><p id="p113511928114519"><a name="p113511928114519"></a><a name="p113511928114519"></a>否</p>
</td>
<td class="cellrowborder" valign="top" width="26.939999999999998%" headers="mcps1.2.6.1.3 "><p id="p1135112813450"><a name="p1135112813450"></a><a name="p1135112813450"></a>开启RISC-V高性能优化，在优化列表内的算子规格能够有性能提升</p>
</td>
<td class="cellrowborder" valign="top" width="20.73%" headers="mcps1.2.6.1.4 "><p id="p1499072512465"><a name="p1499072512465"></a><a name="p1499072512465"></a>-</p>
</td>
<td class="cellrowborder" valign="top" width="12.33%" headers="mcps1.2.6.1.5 "><p id="p123521828144515"><a name="p123521828144515"></a><a name="p123521828144515"></a>false</p>
</td>
</tr>
</tbody>
</table>

## 基础功能参数<a name="ZH-CN_TOPIC_0000002320066172" id="ZH-CN_TOPIC_0000002320066172"></a>

-   **[总体选项](#ZH-CN_TOPIC_0000002319906352)**  

-   **[输入选项](#ZH-CN_TOPIC_0000002353985081)**  

-   **[输出选项](#ZH-CN_TOPIC_0000002354104889)**  

### 总体选项<a name="ZH-CN_TOPIC_0000002319906352" id="ZH-CN_TOPIC_0000002319906352"></a>

**--help<a name="section12231581328"></a>**

-   功能说明

    打印全部帮助信息。

-   关联参数

    无

-   参数取值

    无

-   推荐配置及收益

    无

-   示例

    ```
    #切换到converter_lite工具安装目录，配置LD_LIBRARY_PATH环境变量
    ./converter_lite --help
    ```

-   依赖约束

    无

### 输入选项<a name="ZH-CN_TOPIC_0000002353985081" id="ZH-CN_TOPIC_0000002353985081"></a>

**--fmk=<FMK\><a name="section1072137133513"></a>**

-   功能说明

    配置输入开源框架模型的原始格式。

-   关联参数

    无

-   参数取值
    -   TFLite：转换TFLite开源框架模型为Micro工程代码。
    -   ONNX：转换ONNX开源框架模型为Micro工程代码。
    -   参数默认值：无

-   推荐配置及收益

    无

-   示例

    ```
    #配置输入开源框架模型的原始格式，模型与fmk对应关系为*.tflite-TFLite；*.onnx->ONNX
    --fmk=TFLITE
    --fmk=ONNX 
    ```

-   依赖约束

    无

**--modelFile=<MODELFILE\><a name="section62409421366"></a>**

-   功能说明

    输入模型的路径。

-   关联参数

    无

-   参数取值

    参数默认值：无

-   推荐配置及收益

    无

-   示例

    ```
    #配置开源框架的输入模型路径，例如
    --modelFile=$HOME/module/mnist.tflite
    ```

-   依赖约束

    无

**--configFile=<CONFIGFILE\><a name="section12138185893618"></a>**

-   功能说明

    设置转换Micro工程的配置项。

-   关联参数

    无

-   参数取值

    参数取值参考如[表1](#table3808173922715)所示。

    >![](public_sys-resources/icon-notice.gif) **须知：** 
    >-   Micro配置项[表1](#table3808173922715)中未声明的参数不支持或者适用于其他芯片，用户无需关注。
    >-   如果不使用全量化，仅配置\[micro\_param\]、enable\_micro、target、support\_parallel，其中support\_parallel将默认配置为false。
    >-   如果需要使用全量化，需要配置[表1](#table3808173922715)中除debug\_mode以外的参数。quant\_type需要配置为FULL\_QUANT，bit\_num默认配置为8，bias\_correction默认配置为true，enable\_all\_ops默认配置为false。
    >-   全量化时配置calibrate\_path必须符合“input\_name\_1:input\_1\_dir,input\_name\_2:input\_2\_dir.... ”输入格式，且input\_name\_1、input\_name\_2等的输入数量与名称必须与开源框架AI模型的输入数量和名称相符合。
    >-   全量化时配置的calibrate\_size必须与calibrate\_path每个数据集目录元素数量相同。

    **表 1**  micro.cfg配置项参数概览

    <a name="table3808173922715" id="table3808173922715"></a>
    <table><thead align="left"><tr id="row11809339142713"><th class="cellrowborder" valign="top" width="19.55%" id="mcps1.2.6.1.1"><p id="p11809639122710"><a name="p11809639122710"></a><a name="p11809639122710"></a>参数名称</p>
    </th>
    <th class="cellrowborder" valign="top" width="7.41%" id="mcps1.2.6.1.2"><p id="p48091939192713"><a name="p48091939192713"></a><a name="p48091939192713"></a>是否必选</p>
    </th>
    <th class="cellrowborder" valign="top" width="46.1%" id="mcps1.2.6.1.3"><p id="p148091339132711"><a name="p148091339132711"></a><a name="p148091339132711"></a>参数说明</p>
    </th>
    <th class="cellrowborder" valign="top" width="21.33%" id="mcps1.2.6.1.4"><p id="p68097391279"><a name="p68097391279"></a><a name="p68097391279"></a>取值范围</p>
    </th>
    <th class="cellrowborder" valign="top" width="5.609999999999999%" id="mcps1.2.6.1.5"><p id="p981033913272"><a name="p981033913272"></a><a name="p981033913272"></a>默认值</p>
    </th>
    </tr>
    </thead>
    <tbody><tr id="row681033962714"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p118101039142719"><a name="p118101039142719"></a><a name="p118101039142719"></a>[micro_param]</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p4810173932715"><a name="p4810173932715"></a><a name="p4810173932715"></a>是</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p9810113982714"><a name="p9810113982714"></a><a name="p9810113982714"></a>当前正在设置Micro配置项，用于控制代码生成。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p148101939112713"><a name="p148101939112713"></a><a name="p148101939112713"></a>-</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p7810839162713"><a name="p7810839162713"></a><a name="p7810839162713"></a>-</p>
    </td>
    </tr>
    <tr id="row1581017393276"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p13810133919275"><a name="p13810133919275"></a><a name="p13810133919275"></a>enable_micro</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p14810139172717"><a name="p14810139172717"></a><a name="p14810139172717"></a>是</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p1981003915278"><a name="p1981003915278"></a><a name="p1981003915278"></a>使能convert lite生成Micro工程代码。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p28101539192717"><a name="p28101539192717"></a><a name="p28101539192717"></a>true/false</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p78101339122711"><a name="p78101339122711"></a><a name="p78101339122711"></a>false</p>
    </td>
    </tr>
    <tr id="row281019399277"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p98101439182715"><a name="p98101439182715"></a><a name="p98101439182715"></a>target</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p1810193962710"><a name="p1810193962710"></a><a name="p1810193962710"></a>是</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p208104398275"><a name="p208104398275"></a><a name="p208104398275"></a>Micro工程代码部署推理平台。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p1081019390273"><a name="p1081019390273"></a><a name="p1081019390273"></a>x86/RISCV</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p17810123919279"><a name="p17810123919279"></a><a name="p17810123919279"></a>x86</p>
    </td>
    </tr>
    <tr id="row3810113952716"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p17810103912718"><a name="p17810103912718"></a><a name="p17810103912718"></a>support_parallel</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p1281015391278"><a name="p1281015391278"></a><a name="p1281015391278"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p1381013918274"><a name="p1381013918274"></a><a name="p1381013918274"></a>是否生成多线程推理代码，当前尚未支持多线程即不支持置为true。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p12810939142717"><a name="p12810939142717"></a><a name="p12810939142717"></a>true/false</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p581116392276"><a name="p581116392276"></a><a name="p581116392276"></a>false</p>
    </td>
    </tr>
    <tr id="row0604101605615"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p17815439132719"><a name="p17815439132719"></a><a name="p17815439132719"></a>debug_mode</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p281593919279"><a name="p281593919279"></a><a name="p281593919279"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p13815133972710"><a name="p13815133972710"></a><a name="p13815133972710"></a>是否打开调测接口，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p681533911274"><a name="p681533911274"></a><a name="p681533911274"></a>true/false</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p3815103912720"><a name="p3815103912720"></a><a name="p3815103912720"></a>false</p>
    </td>
    </tr>
    <tr id="row1681133972713"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p138111539152714"><a name="p138111539152714"></a><a name="p138111539152714"></a>[common_quant_param]</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p781118399279"><a name="p781118399279"></a><a name="p781118399279"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p10811143932712"><a name="p10811143932712"></a><a name="p10811143932712"></a>公共量化参数，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p78117399278"><a name="p78117399278"></a><a name="p78117399278"></a>-</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p1681153910274"><a name="p1681153910274"></a><a name="p1681153910274"></a>-</p>
    </td>
    </tr>
    <tr id="row3811139102713"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p481113392272"><a name="p481113392272"></a><a name="p481113392272"></a>quant_type</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p16811133962717"><a name="p16811133962717"></a><a name="p16811133962717"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p6811133902710"><a name="p6811133902710"></a><a name="p6811133902710"></a>设置量化类型，启用全量化时需要配置为FULL_QUANT，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p581193913272"><a name="p581193913272"></a><a name="p581193913272"></a>FULL_QUANT/-</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p0811163922718"><a name="p0811163922718"></a><a name="p0811163922718"></a>-</p>
    </td>
    </tr>
    <tr id="row681243982718"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p0812173932713"><a name="p0812173932713"></a><a name="p0812173932713"></a>bit_num</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p1381203916276"><a name="p1381203916276"></a><a name="p1381203916276"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p1281233982719"><a name="p1281233982719"></a><a name="p1281233982719"></a>设置量化的比特数，目前仅支持8bit量化，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p10359162515326"><a name="p10359162515326"></a><a name="p10359162515326"></a>8</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p28121139122713"><a name="p28121139122713"></a><a name="p28121139122713"></a>-</p>
    </td>
    </tr>
    <tr id="row481293982716"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p0812739152715"><a name="p0812739152715"></a><a name="p0812739152715"></a>[data_preprocess_param]</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p18125395277"><a name="p18125395277"></a><a name="p18125395277"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p18121739122710"><a name="p18121739122710"></a><a name="p18121739122710"></a>校准数据集参数，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p20812123952711"><a name="p20812123952711"></a><a name="p20812123952711"></a>-</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p281219397273"><a name="p281219397273"></a><a name="p281219397273"></a>-</p>
    </td>
    </tr>
    <tr id="row3812203982716"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p08121039122715"><a name="p08121039122715"></a><a name="p08121039122715"></a>calibrate_path</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p138120394278"><a name="p138120394278"></a><a name="p138120394278"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p9812193912712"><a name="p9812193912712"></a><a name="p9812193912712"></a>校准数据集路径，该路径下不能存放非bin格式文件，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p19812039182713"><a name="p19812039182713"></a><a name="p19812039182713"></a>-</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p168121839202711"><a name="p168121839202711"></a><a name="p168121839202711"></a>-</p>
    </td>
    </tr>
    <tr id="row98121439122717"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p4812143982717"><a name="p4812143982717"></a><a name="p4812143982717"></a>calibrate_size</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p2813133962717"><a name="p2813133962717"></a><a name="p2813133962717"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p7813539132720"><a name="p7813539132720"></a><a name="p7813539132720"></a>校准数据集大小，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p148131939142710"><a name="p148131939142710"></a><a name="p148131939142710"></a>必须与calibrate_path数据集数量一致</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p1181363982711"><a name="p1181363982711"></a><a name="p1181363982711"></a>-</p>
    </td>
    </tr>
    <tr id="row15813143919275"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p11813193922717"><a name="p11813193922717"></a><a name="p11813193922717"></a>input_type</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p681313916276"><a name="p681313916276"></a><a name="p681313916276"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p10813143914272"><a name="p10813143914272"></a><a name="p10813143914272"></a>校准数据集格式，启用全量化时需要配置为BIN，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p68131939122717"><a name="p68131939122717"></a><a name="p68131939122717"></a>只支持BIN</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p4813153919270"><a name="p4813153919270"></a><a name="p4813153919270"></a>-</p>
    </td>
    </tr>
    <tr id="row1281312395271"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p16814173916277"><a name="p16814173916277"></a><a name="p16814173916277"></a>[full_quant_param]</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p11814839202715"><a name="p11814839202715"></a><a name="p11814839202715"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p2814839102710"><a name="p2814839102710"></a><a name="p2814839102710"></a>全量化参数，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p481413952719"><a name="p481413952719"></a><a name="p481413952719"></a>-</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p3814153914279"><a name="p3814153914279"></a><a name="p3814153914279"></a>-</p>
    </td>
    </tr>
    <tr id="row13814193962716"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p15814539202719"><a name="p15814539202719"></a><a name="p15814539202719"></a>activation_quant_method</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p68141539142717"><a name="p68141539142717"></a><a name="p68141539142717"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p98141339182716"><a name="p98141339182716"></a><a name="p98141339182716"></a>激活值量化算法，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p5814183982717"><a name="p5814183982717"></a><a name="p5814183982717"></a>只支持MAX_MIN</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p7814163914276"><a name="p7814163914276"></a><a name="p7814163914276"></a>-</p>
    </td>
    </tr>
    <tr id="row281473916278"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p1881411396277"><a name="p1881411396277"></a><a name="p1881411396277"></a>bias_correction</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p188142397279"><a name="p188142397279"></a><a name="p188142397279"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p14814203912273"><a name="p14814203912273"></a><a name="p14814203912273"></a>是否对量化误差进行校正，仅全量化时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p381463912273"><a name="p381463912273"></a><a name="p381463912273"></a>true/false</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p6815163992712"><a name="p6815163992712"></a><a name="p6815163992712"></a>-</p>
    </td>
    </tr>
    <tr id="row1746405596"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p134164065920"><a name="p134164065920"></a><a name="p134164065920"></a><span>enable_all_ops</span></p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p10474019597"><a name="p10474019597"></a><a name="p10474019597"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p676414163513"><a name="p676414163513"></a><a name="p676414163513"></a>是否开启进阶量化算子。</p>
    <p id="p19262195710404"><a name="p19262195710404"></a><a name="p19262195710404"></a>默认量化算子（无论是否配置均会开启）：Conv Matmul/Gemm(FullyConneted) /Reshape ；</p>
    <p id="p241940125913"><a name="p241940125913"></a><a name="p241940125913"></a>进阶量化算子（需要配置此属性为true才会开启）：Maxpool Relu Softmax Mul Add Sub Gather Concat Split AvgPool。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p14484045914"><a name="p14484045914"></a><a name="p14484045914"></a>true/false</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p11454045914"><a name="p11454045914"></a><a name="p11454045914"></a>-</p>
    </td>
    </tr>
    <tr id="row122396579551"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p423913570557"><a name="p423913570557"></a><a name="p423913570557"></a>[train]</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p122392579555"><a name="p122392579555"></a><a name="p122392579555"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p12239857195512"><a name="p12239857195512"></a><a name="p12239857195512"></a>训练参数，仅端侧训练时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p16239145775520"><a name="p16239145775520"></a><a name="p16239145775520"></a>-</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p20239757195515"><a name="p20239757195515"></a><a name="p20239757195515"></a>-</p>
    </td>
    </tr>
    <tr id="row1442934365610"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p4429124395617"><a name="p4429124395617"></a><a name="p4429124395617"></a>train_mode</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p442934316561"><a name="p442934316561"></a><a name="p442934316561"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p14429143115610"><a name="p14429143115610"></a><a name="p14429143115610"></a>训练模式，仅端侧训练时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p174291643165615"><a name="p174291643165615"></a><a name="p174291643165615"></a>量化训练配置qas_int8；FP32训练配置fp32</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p34295430565"><a name="p34295430565"></a><a name="p34295430565"></a>-</p>
    </td>
    </tr>
    <tr id="row82644535816"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p1626419511582"><a name="p1626419511582"></a><a name="p1626419511582"></a>loss</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p926445165818"><a name="p926445165818"></a><a name="p926445165818"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p202649510581"><a name="p202649510581"></a><a name="p202649510581"></a>训练使用的loss函数，仅端侧训练时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p162641250587"><a name="p162641250587"></a><a name="p162641250587"></a>量化训练支持softmax_cross_entropy；FP32训练还支持mean_squared_error</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p92646505816"><a name="p92646505816"></a><a name="p92646505816"></a>-</p>
    </td>
    </tr>
    <tr id="row578145415581"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p137811954115820"><a name="p137811954115820"></a><a name="p137811954115820"></a>label_tensor_name</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p107819547587"><a name="p107819547587"></a><a name="p107819547587"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p678155405810"><a name="p678155405810"></a><a name="p678155405810"></a>标签张量名称，仅端侧训练时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p1378145475810"><a name="p1378145475810"></a><a name="p1378145475810"></a>-</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p1578117542581"><a name="p1578117542581"></a><a name="p1578117542581"></a>-</p>
    </td>
    </tr>
    <tr id="row1588417296594"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p17937123725910"><a name="p17937123725910"></a><a name="p17937123725910"></a>optimizer</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p8885329115920"><a name="p8885329115920"></a><a name="p8885329115920"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p138859294595"><a name="p138859294595"></a><a name="p138859294595"></a>权重更新使用的优化器，仅端侧训练时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p1088513293597"><a name="p1088513293597"></a><a name="p1088513293597"></a>量化训练支持sgd_with_momentum；FP32训练还支持adam</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p8885182965919"><a name="p8885182965919"></a><a name="p8885182965919"></a>-</p>
    </td>
    </tr>
    <tr id="row6367281003"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p18697194016017"><a name="p18697194016017"></a><a name="p18697194016017"></a>learning_rate</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p63642815016"><a name="p63642815016"></a><a name="p63642815016"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p9365281707"><a name="p9365281707"></a><a name="p9365281707"></a>学习率，仅端侧训练时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p53612810012"><a name="p53612810012"></a><a name="p53612810012"></a>-</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p11363281709"><a name="p11363281709"></a><a name="p11363281709"></a>-</p>
    </td>
    </tr>
    <tr id="row984615915010"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p169331412611"><a name="p169331412611"></a><a name="p169331412611"></a>momentum</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p88468596012"><a name="p88468596012"></a><a name="p88468596012"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p20846195910015"><a name="p20846195910015"></a><a name="p20846195910015"></a>动量大小，仅端侧训练时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p1684618592015"><a name="p1684618592015"></a><a name="p1684618592015"></a>-</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p8846359009"><a name="p8846359009"></a><a name="p8846359009"></a>-</p>
    </td>
    </tr>
    <tr id="row773043218116"><td class="cellrowborder" valign="top" width="19.55%" headers="mcps1.2.6.1.1 "><p id="p47300321912"><a name="p47300321912"></a><a name="p47300321912"></a>batch_size</p>
    </td>
    <td class="cellrowborder" valign="top" width="7.41%" headers="mcps1.2.6.1.2 "><p id="p1473043215114"><a name="p1473043215114"></a><a name="p1473043215114"></a>否</p>
    </td>
    <td class="cellrowborder" valign="top" width="46.1%" headers="mcps1.2.6.1.3 "><p id="p5730173219116"><a name="p5730173219116"></a><a name="p5730173219116"></a>训练数据批次大小，仅端侧训练时选择。</p>
    </td>
    <td class="cellrowborder" valign="top" width="21.33%" headers="mcps1.2.6.1.4 "><p id="p19730032417"><a name="p19730032417"></a><a name="p19730032417"></a>只支持1</p>
    </td>
    <td class="cellrowborder" valign="top" width="5.609999999999999%" headers="mcps1.2.6.1.5 "><p id="p773012326117"><a name="p773012326117"></a><a name="p773012326117"></a>-</p>
    </td>
    </tr>
    <tr><td class="cellrowborder">dump_training_graph</td>
    <td class="cellrowborder">否</td>
    <td class="cellrowborder">是否输出训练图和内存规划信息，仅端侧训练时选择。</td>
    <td class="cellrowborder">true/false</td>
    <td class="cellrowborder">false</td>
    </tr>
    <tr><td class="cellrowborder">beta1</td>
    <td class="cellrowborder">否</td>
    <td class="cellrowborder">Adam一阶矩衰减率，仅FP32训练使用Adam优化器时选择。</td>
    <td class="cellrowborder">[0, 1)</td>
    <td class="cellrowborder">0.9</td>
    </tr>
    <tr><td class="cellrowborder">beta2</td>
    <td class="cellrowborder">否</td>
    <td class="cellrowborder">Adam二阶矩衰减率，仅FP32训练使用Adam优化器时选择。</td>
    <td class="cellrowborder">[0, 1)</td>
    <td class="cellrowborder">0.999</td>
    </tr>
    <tr><td class="cellrowborder">epsilon</td>
    <td class="cellrowborder">否</td>
    <td class="cellrowborder">Adam数值稳定参数，仅FP32训练使用Adam优化器时选择。</td>
    <td class="cellrowborder">大于0</td>
    <td class="cellrowborder">1e-8</td>
    </tr>
    </tbody>
    </table>

-   推荐配置及收益

    无

-   示例

    ```
    #配置Micro工程配置项绝对路径，例如
    --configFile=$HOME/module/micro.cfg
    ```

-   依赖约束

    无

### 输出选项<a name="ZH-CN_TOPIC_0000002354104889" id="ZH-CN_TOPIC_0000002354104889"></a>

**--outputFile=<OUTPUTFILE\><a name="section2155824122114"></a>**

-   功能说明

    转成Micro工程代码的路径

-   关联参数

    无

-   参数取值

    参数默认值：无

-   推荐配置及收益

    无

-   示例

    ```
     #Micro工程路径为当前目录的mnist文件夹
     --outputFile=mnist
     #Micro工程路径为当前目录的micro文件夹
     --outputFile=.
    ```

    命令执行完毕后，屏幕会打印类似如下信息：

    ```
    CONVERT RESULT SUCCESS:0
    ```

-   依赖约束

    无

# 算子规格参考<a name="ZH-CN_TOPIC_0000002354161329" id="ZH-CN_TOPIC_0000002354161329"></a>

本章主要介绍（MindSpore Lite）所支持的算子规格限制，目前主要支持ONNX格式以及TFLite格式的模型，并且支持算子的数据类型主要为int8以及fp32。

>![](public_sys-resources/icon-note.gif) **说明：** 
>Gemm是ONNX框架的矩阵乘法算子，而FullyConnected则是TFLite框架的矩阵乘法算子。目前，int8仅支持量化模型，不支持onnxruntime量化场景。

-   **[TFLite算子规格参考](#ZH-CN_TOPIC_0000002320146508)**  

-   **[ONNX算子规格参考](#ZH-CN_TOPIC_0000002320738138)**  

## TFLite算子规格参考<a name="ZH-CN_TOPIC_0000002320146508" id="ZH-CN_TOPIC_0000002320146508"></a>

-   **[Conv2D](#ZH-CN_TOPIC_0000002326184638)**  

-   **[MaxPool2D](#ZH-CN_TOPIC_0000002360102989)**  

-   **[FullyConnected](#ZH-CN_TOPIC_0000002326344486)**  

-   **[BatchMatmul](#ZH-CN_TOPIC_0000002421627894)**  

-   **[Softmax](#ZH-CN_TOPIC_0000002360223141)**  

-   **[Relu](#ZH-CN_TOPIC_0000002326184642)**  

-   **[Tanh](#ZH-CN_TOPIC_0000002474804265)**  

-   **[Logistic \(Sigmoid\)](#ZH-CN_TOPIC_0000002441404462)**  

-   **[Reshape](#ZH-CN_TOPIC_0000002360102993)**  

-   **[Mul](#ZH-CN_TOPIC_0000002421789214)**  

-   **[Add](#ZH-CN_TOPIC_0000002454832349)**  

-   **[Sub](#ZH-CN_TOPIC_0000002454792461)**  

-   **[Gather](#ZH-CN_TOPIC_0000002421683676)**  

-   **[Split](#ZH-CN_TOPIC_0000002455529089)**  

-   **[Concatenation](#ZH-CN_TOPIC_0000002421843540)**  

-   **[AveragePool2D](#ZH-CN_TOPIC_0000002455282373)**  

-   **[Tile](#ZH-CN_TOPIC_0000002480985174)**  

-   **[Pad](#ZH-CN_TOPIC_0000002480985538)**  

-   **[Resize](#ZH-CN_TOPIC_0000002513105415)**  

-   **[Squeeze](#ZH-CN_TOPIC_0000002515130287)**  

-   **[ExpandDims](#ZH-CN_TOPIC_0000002482930280)**  

-   **[Abs](#ZH-CN_TOPIC_0000002485399132)**  

-   **[Ceil](#ZH-CN_TOPIC_0000002517479769)**  

-   **[Cos](#ZH-CN_TOPIC_0000002485399848)**  

-   **[Exp](#ZH-CN_TOPIC_0000002485239884)**  

-   **[Floor](#ZH-CN_TOPIC_0000002517399793)**  

-   **[Log](#ZH-CN_TOPIC_0000002517479771)**  

-   **[Round](#ZH-CN_TOPIC_0000002485399850)**  

-   **[Rsqrt](#ZH-CN_TOPIC_0000002485239886)**  

-   **[Sin](#ZH-CN_TOPIC_0000002517399795)**  

-   **[Sqrt](#ZH-CN_TOPIC_0000002517479773)**  

-   **[Square](#ZH-CN_TOPIC_0000002485399852)**  

-   **[L2Normalization](#ZH-CN_TOPIC_0000002487557124)**  

-   **[Slice](#ZH-CN_TOPIC_0000002528693597)**  

-   **[DepthwiseConv2D](#ZH-CN_TOPIC_0000002529736261)**  

-   **[Transpose](#ZH-CN_TOPIC_0000002498475622)**  

-   **[ArgMax](#ZH-CN_TOPIC_0000002509946184)**  

-   **[ArgMin](#ZH-CN_TOPIC_0000002541666173)**  

-   **[Div](#ZH-CN_TOPIC_0000002516421386)**  

-   **[ReduceMax](#ZH-CN_TOPIC_0000002526421590)**  

-   **[ReduceMin](#ZH-CN_TOPIC_0000002526437776)**  

-   **[Sum](#ZH-CN_TOPIC_0000002557400507)**  

-   **[Mean](#ZH-CN_TOPIC_0000002557400907)**  

-   **[Cast](#ZH-CN_TOPIC_0000002557544885)**  

-   **[Quantize](#ZH-CN_TOPIC_0000002557589767)**  

-   **[Dequantize](#ZH-CN_TOPIC_0000002526509914)**  

-   **[PRelu](#ZH-CN_TOPIC_0000002599172631)**  

-   **[CumSum](#ZH-CN_TOPIC_0000002599292569)**  

-   **[ReverseSequence](#ZH-CN_TOPIC_0000002599187919)**  

-   **[Relu6](#ZH-CN_TOPIC_0000002574010852)**  

-   **[LeakyRelu](#ZH-CN_TOPIC_0000002604689955)**  

-   **[HardSwish](#ZH-CN_TOPIC_0000002574309498)**  

-   **[LogicalAnd](#ZH-CN_TOPIC_0000002574976868)**  

-   **[Equal](#ZH-CN_TOPIC_0000002605336325)**  

-   **[GreaterEqual](#ZH-CN_TOPIC_0000002574817236)**  

-   **[Greater](#ZH-CN_TOPIC_0000002605456261)**  

-   **[LessEqual](#ZH-CN_TOPIC_0000002574976872)**  

-   **[Less](#ZH-CN_TOPIC_0000002605336331)**  

-   **[NotEqual](#ZH-CN_TOPIC_0000002574817240)**  

-   **[LogicalNot](#ZH-CN_TOPIC_0000002605456267)**  

-   **[LogicalOr](#ZH-CN_TOPIC_0000002574976878)**  

-   **[Elu](#ZH-CN_TOPIC_0000002660274969)**  

-   **[DepthToSpace](#ZH-CN_TOPIC_0000002660395017)**  

-   **[SpaceToDepth](#ZH-CN_TOPIC_0000002630115702)**  

-   **[Select](#ZH-CN_TOPIC_0000002600000001)**  

-   **[SelectV2](#ZH-CN_TOPIC_0000002600000002)**  

-   **[ReverseV2](#ZH-CN_TOPIC_0000002600000003)**  

-   **[Gelu](#ZH-CN_TOPIC_0000002661401191)**  

-   **[Pack](#ZH-CN_TOPIC_0000002661401192)**  

-   **[Unpack](#ZH-CN_TOPIC_0000002661401193)** 

-   **[Fill](#ZH-CN_TOPIC_0000002800000001)**  

-   **[Neg](#ZH-CN_TOPIC_0000002900000001)**  

-   **[Pow](#ZH-CN_TOPIC_0000002476598365)**  

-   **[Shape](#ZH-CN_TOPIC_0000003030115702)**  

-   **[TopK](#ZH-CN_TOPIC_0000003050115702)**  

### Conv2D<a name="ZH-CN_TOPIC_0000002326184638" id="ZH-CN_TOPIC_0000002326184638"></a>

**功能描述<a name="section113841812134710"></a>**

对4D输入进行卷积计算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Conv2D参数概览

<a name="table668985955612"></a>
<table><thead align="left"><tr id="row13690359165613"><th class="cellrowborder" valign="top" width="18.05%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="10.92%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.25%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.94%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.840000000000003%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row0259114117411"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row105725371417"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p257316371747"><a name="p257316371747"></a><a name="p257316371747"></a>filter</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p1357393714410"><a name="p1357393714410"></a><a name="p1357393714410"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p145732037648"><a name="p145732037648"></a><a name="p145732037648"></a>filter张量，维度为4D。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p35731237948"><a name="p35731237948"></a><a name="p35731237948"></a>规格约束：权重为离线变量</p>
</td>
</tr>
<tr id="row04821554841"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p74821654243"><a name="p74821654243"></a><a name="p74821654243"></a>bias</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p11482185414420"><a name="p11482185414420"></a><a name="p11482185414420"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p194829542412"><a name="p194829542412"></a><a name="p194829542412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p17482125418417"><a name="p17482125418417"></a><a name="p17482125418417"></a>bias张量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p048220543413"><a name="p048220543413"></a><a name="p048220543413"></a>规格约束：偏置为离线变量</p>
</td>
</tr>
<tr id="row44831201652"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p194831017511"><a name="p194831017511"></a><a name="p194831017511"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p048340450"><a name="p048340450"></a><a name="p048340450"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p124839018518"><a name="p124839018518"></a><a name="p124839018518"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p13483801352"><a name="p13483801352"></a><a name="p13483801352"></a>输出张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p748310020510"><a name="p748310020510"></a><a name="p748310020510"></a>-</p>
</td>
</tr>
<tr id="row26911159125618"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p1269165919569"><a name="p1269165919569"></a><a name="p1269165919569"></a>dilation_h_factor</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p2509588318"><a name="p2509588318"></a><a name="p2509588318"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p469110599562"><a name="p469110599562"></a><a name="p469110599562"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p126911459165613"><a name="p126911459165613"></a><a name="p126911459165613"></a>filter在H方向上的扩张系数。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p1447651443920"><a name="p1447651443920"></a><a name="p1447651443920"></a>-</p>
</td>
</tr>
<tr id="row669175913568"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p1169119595569"><a name="p1169119595569"></a><a name="p1169119595569"></a>dilation_w_factor</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p65015581736"><a name="p65015581736"></a><a name="p65015581736"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p769119597568"><a name="p769119597568"></a><a name="p769119597568"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p12281134810395"><a name="p12281134810395"></a><a name="p12281134810395"></a>filter在W方向上的扩张系数。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p185499219400"><a name="p185499219400"></a><a name="p185499219400"></a>-</p>
</td>
</tr>
<tr id="row1469255925614"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p3692859195613"><a name="p3692859195613"></a><a name="p3692859195613"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p15692145965619"><a name="p15692145965619"></a><a name="p15692145965619"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p833042514011"><a name="p833042514011"></a><a name="p833042514011"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p7692759195616"><a name="p7692759195616"></a><a name="p7692759195616"></a>配置范围：NONE、RELU</p>
</td>
</tr>
<tr id="row869245925620"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p96921059125614"><a name="p96921059125614"></a><a name="p96921059125614"></a>padding</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p1150158930"><a name="p1150158930"></a><a name="p1150158930"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p76921259115619"><a name="p76921259115619"></a><a name="p76921259115619"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p10118203645110"><a name="p10118203645110"></a><a name="p10118203645110"></a>填充类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p1769285995619"><a name="p1769285995619"></a><a name="p1769285995619"></a>配置范围：SAME、VALID</p>
</td>
</tr>
<tr id="row369235919566"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p106921159195616"><a name="p106921159195616"></a><a name="p106921159195616"></a>stride_h</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p15015581132"><a name="p15015581132"></a><a name="p15015581132"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p56921593564"><a name="p56921593564"></a><a name="p56921593564"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p136921359195618"><a name="p136921359195618"></a><a name="p136921359195618"></a>filter在H方向上的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p523152894518"><a name="p523152894518"></a><a name="p523152894518"></a>-</p>
</td>
</tr>
<tr id="row1198393324510"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p1898353317457"><a name="p1898353317457"></a><a name="p1898353317457"></a>stride_w</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p16508581531"><a name="p16508581531"></a><a name="p16508581531"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p499819412458"><a name="p499819412458"></a><a name="p499819412458"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p1399834134511"><a name="p1399834134511"></a><a name="p1399834134511"></a>filter在W方向上的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p1798314337454"><a name="p1798314337454"></a><a name="p1798314337454"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 要求使用静态形状；仅对可微输入和可训练权重生成梯度 |
| FP32 | 支持 | 要求使用静态形状；仅对可微输入和可训练权重生成梯度 |

### MaxPool2D<a name="ZH-CN_TOPIC_0000002360102989" id="ZH-CN_TOPIC_0000002360102989"></a>

**功能描述<a name="section37550136507"></a>**

对4D输入进行最大池化计算。

**参数说明<a name="section162919203502"></a>**

**表 1**  MaxPool2D参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="18.58185818581858%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.22112211221122%" id="mcps1.2.6.1.2"><p id="p162409815313"><a name="p162409815313"></a><a name="p162409815313"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.821282128212822%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.47304730473047%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.902690269026902%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row5877176175416"><td class="cellrowborder" valign="top" width="18.58185818581858%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.22112211221122%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.821282128212822%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.47304730473047%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.902690269026902%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row1975102125412"><td class="cellrowborder" valign="top" width="18.58185818581858%" headers="mcps1.2.6.1.1 "><p id="p194831017511"><a name="p194831017511"></a><a name="p194831017511"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.22112211221122%" headers="mcps1.2.6.1.2 "><p id="p048340450"><a name="p048340450"></a><a name="p048340450"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.821282128212822%" headers="mcps1.2.6.1.3 "><p id="p124839018518"><a name="p124839018518"></a><a name="p124839018518"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.47304730473047%" headers="mcps1.2.6.1.4 "><p id="p13483801352"><a name="p13483801352"></a><a name="p13483801352"></a>输出张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.902690269026902%" headers="mcps1.2.6.1.5 "><p id="p748310020510"><a name="p748310020510"></a><a name="p748310020510"></a>-</p>
</td>
</tr>
<tr id="row16660151211817"><td class="cellrowborder" valign="top" width="18.58185818581858%" headers="mcps1.2.6.1.1 "><p id="p1269165919569"><a name="p1269165919569"></a><a name="p1269165919569"></a>filter_height</p>
</td>
<td class="cellrowborder" valign="top" width="11.22112211221122%" headers="mcps1.2.6.1.2 "><p id="p2509588318"><a name="p2509588318"></a><a name="p2509588318"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.821282128212822%" headers="mcps1.2.6.1.3 "><p id="p469110599562"><a name="p469110599562"></a><a name="p469110599562"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.47304730473047%" headers="mcps1.2.6.1.4 "><p id="p126911459165613"><a name="p126911459165613"></a><a name="p126911459165613"></a>在H方向上的过滤窗口大小。</p>
</td>
<td class="cellrowborder" valign="top" width="26.902690269026902%" headers="mcps1.2.6.1.5 "><p id="p1447651443920"><a name="p1447651443920"></a><a name="p1447651443920"></a>-</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="18.58185818581858%" headers="mcps1.2.6.1.1 "><p id="p1169119595569"><a name="p1169119595569"></a><a name="p1169119595569"></a>filter_width</p>
</td>
<td class="cellrowborder" valign="top" width="11.22112211221122%" headers="mcps1.2.6.1.2 "><p id="p65015581736"><a name="p65015581736"></a><a name="p65015581736"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.821282128212822%" headers="mcps1.2.6.1.3 "><p id="p769119597568"><a name="p769119597568"></a><a name="p769119597568"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.47304730473047%" headers="mcps1.2.6.1.4 "><p id="p1614615144496"><a name="p1614615144496"></a><a name="p1614615144496"></a>在W方向上的过滤窗口大小。</p>
</td>
<td class="cellrowborder" valign="top" width="26.902690269026902%" headers="mcps1.2.6.1.5 "><p id="p185499219400"><a name="p185499219400"></a><a name="p185499219400"></a>-</p>
</td>
</tr>
<tr id="row9660171281818"><td class="cellrowborder" valign="top" width="18.58185818581858%" headers="mcps1.2.6.1.1 "><p id="p3692859195613"><a name="p3692859195613"></a><a name="p3692859195613"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="11.22112211221122%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.821282128212822%" headers="mcps1.2.6.1.3 "><p id="p15692145965619"><a name="p15692145965619"></a><a name="p15692145965619"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.47304730473047%" headers="mcps1.2.6.1.4 "><p id="p833042514011"><a name="p833042514011"></a><a name="p833042514011"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.902690269026902%" headers="mcps1.2.6.1.5 "><p id="p7692759195616"><a name="p7692759195616"></a><a name="p7692759195616"></a>配置范围：NONE、RELU</p>
</td>
</tr>
<tr id="row7660151212186"><td class="cellrowborder" valign="top" width="18.58185818581858%" headers="mcps1.2.6.1.1 "><p id="p96921059125614"><a name="p96921059125614"></a><a name="p96921059125614"></a>padding</p>
</td>
<td class="cellrowborder" valign="top" width="11.22112211221122%" headers="mcps1.2.6.1.2 "><p id="p1150158930"><a name="p1150158930"></a><a name="p1150158930"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.821282128212822%" headers="mcps1.2.6.1.3 "><p id="p76921259115619"><a name="p76921259115619"></a><a name="p76921259115619"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.47304730473047%" headers="mcps1.2.6.1.4 "><p id="p10118203645110"><a name="p10118203645110"></a><a name="p10118203645110"></a>填充类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.902690269026902%" headers="mcps1.2.6.1.5 "><p id="p1769285995619"><a name="p1769285995619"></a><a name="p1769285995619"></a>配置范围：SAME、VALID</p>
</td>
</tr>
<tr id="row16661101271811"><td class="cellrowborder" valign="top" width="18.58185818581858%" headers="mcps1.2.6.1.1 "><p id="p106921159195616"><a name="p106921159195616"></a><a name="p106921159195616"></a>stride_h</p>
</td>
<td class="cellrowborder" valign="top" width="11.22112211221122%" headers="mcps1.2.6.1.2 "><p id="p15015581132"><a name="p15015581132"></a><a name="p15015581132"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.821282128212822%" headers="mcps1.2.6.1.3 "><p id="p56921593564"><a name="p56921593564"></a><a name="p56921593564"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.47304730473047%" headers="mcps1.2.6.1.4 "><p id="p136921359195618"><a name="p136921359195618"></a><a name="p136921359195618"></a>filter在H方向上的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="26.902690269026902%" headers="mcps1.2.6.1.5 "><p id="p523152894518"><a name="p523152894518"></a><a name="p523152894518"></a>-</p>
</td>
</tr>
<tr id="row16661171281819"><td class="cellrowborder" valign="top" width="18.58185818581858%" headers="mcps1.2.6.1.1 "><p id="p1898353317457"><a name="p1898353317457"></a><a name="p1898353317457"></a>stride_w</p>
</td>
<td class="cellrowborder" valign="top" width="11.22112211221122%" headers="mcps1.2.6.1.2 "><p id="p16508581531"><a name="p16508581531"></a><a name="p16508581531"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.821282128212822%" headers="mcps1.2.6.1.3 "><p id="p499819412458"><a name="p499819412458"></a><a name="p499819412458"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.47304730473047%" headers="mcps1.2.6.1.4 "><p id="p1399834134511"><a name="p1399834134511"></a><a name="p1399834134511"></a>filter在W方向上的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="26.902690269026902%" headers="mcps1.2.6.1.5 "><p id="p1798314337454"><a name="p1798314337454"></a><a name="p1798314337454"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 仅支持MaxPool，输入和输出均为四维量化张量 |
| FP32 | 不支持 | - |

### FullyConnected<a name="ZH-CN_TOPIC_0000002326344486" id="ZH-CN_TOPIC_0000002326344486"></a>

**功能描述<a name="section37550136507"></a>**

对2D、3D、4D输入的最后一个维度进行特征映射（类似Onnx规格中Gemm）。

**参数说明<a name="section162919203502"></a>**

**表 1**  FullyConnected参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="18.76%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.910000000000002%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.330000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.060000000000002%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.94%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row1881205855514"><td class="cellrowborder" valign="top" width="18.76%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.910000000000002%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.330000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.060000000000002%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.94%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row10383185419557"><td class="cellrowborder" valign="top" width="18.76%" headers="mcps1.2.6.1.1 "><p id="p1478312814577"><a name="p1478312814577"></a><a name="p1478312814577"></a>filter</p>
</td>
<td class="cellrowborder" valign="top" width="11.910000000000002%" headers="mcps1.2.6.1.2 "><p id="p17783152895719"><a name="p17783152895719"></a><a name="p17783152895719"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.330000000000002%" headers="mcps1.2.6.1.3 "><p id="p1978318288574"><a name="p1978318288574"></a><a name="p1978318288574"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.060000000000002%" headers="mcps1.2.6.1.4 "><p id="p478352815572"><a name="p478352815572"></a><a name="p478352815572"></a>权重张量，维度为2D。</p>
</td>
<td class="cellrowborder" valign="top" width="26.94%" headers="mcps1.2.6.1.5 "><p id="p1277012811575"><a name="p1277012811575"></a><a name="p1277012811575"></a>规格约束：权重为离线变量</p>
</td>
</tr>
<tr id="row36811212145610"><td class="cellrowborder" valign="top" width="18.76%" headers="mcps1.2.6.1.1 "><p id="p1068121255611"><a name="p1068121255611"></a><a name="p1068121255611"></a>bias</p>
</td>
<td class="cellrowborder" valign="top" width="11.910000000000002%" headers="mcps1.2.6.1.2 "><p id="p768141275618"><a name="p768141275618"></a><a name="p768141275618"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.330000000000002%" headers="mcps1.2.6.1.3 "><p id="p1368181275613"><a name="p1368181275613"></a><a name="p1368181275613"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.060000000000002%" headers="mcps1.2.6.1.4 "><p id="p09851557135719"><a name="p09851557135719"></a><a name="p09851557135719"></a>偏置张量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="26.94%" headers="mcps1.2.6.1.5 "><p id="p18681191211569"><a name="p18681191211569"></a><a name="p18681191211569"></a>规格约束：偏置为离线变量</p>
</td>
</tr>
<tr id="row125439162571"><td class="cellrowborder" valign="top" width="18.76%" headers="mcps1.2.6.1.1 "><p id="p198716219579"><a name="p198716219579"></a><a name="p198716219579"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.910000000000002%" headers="mcps1.2.6.1.2 "><p id="p1871182195716"><a name="p1871182195716"></a><a name="p1871182195716"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.330000000000002%" headers="mcps1.2.6.1.3 "><p id="p787102195717"><a name="p787102195717"></a><a name="p787102195717"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.060000000000002%" headers="mcps1.2.6.1.4 "><p id="p18871921165713"><a name="p18871921165713"></a><a name="p18871921165713"></a>输出张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.94%" headers="mcps1.2.6.1.5 "><p id="p3871132111571"><a name="p3871132111571"></a><a name="p3871132111571"></a>-</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="18.76%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="11.910000000000002%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.330000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.060000000000002%" headers="mcps1.2.6.1.4 "><p id="p833042514011"><a name="p833042514011"></a><a name="p833042514011"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.94%" headers="mcps1.2.6.1.5 "><p id="p109807391203"><a name="p109807391203"></a><a name="p109807391203"></a>配置范围：NONE、RELU</p>
</td>
</tr>
<tr id="row46789503544"><td class="cellrowborder" valign="top" width="18.76%" headers="mcps1.2.6.1.1 "><p id="p9156191441212"><a name="p9156191441212"></a><a name="p9156191441212"></a>weights_format</p>
</td>
<td class="cellrowborder" valign="top" width="11.910000000000002%" headers="mcps1.2.6.1.2 "><p id="p1150158930"><a name="p1150158930"></a><a name="p1150158930"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.330000000000002%" headers="mcps1.2.6.1.3 "><p id="p17678145075410"><a name="p17678145075410"></a><a name="p17678145075410"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.060000000000002%" headers="mcps1.2.6.1.4 "><p id="p987355119195"><a name="p987355119195"></a><a name="p987355119195"></a><span>权重张量在内存中的存储布局</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="26.94%" headers="mcps1.2.6.1.5 "><p id="p19964242119"><a name="p19964242119"></a><a name="p19964242119"></a>配置范围：DEFAULT，不支持其他配置</p>
</td>
</tr>
<tr id="row950820530549"><td class="cellrowborder" valign="top" width="18.76%" headers="mcps1.2.6.1.1 "><p id="p432217277129"><a name="p432217277129"></a><a name="p432217277129"></a>keep_num_dims</p>
</td>
<td class="cellrowborder" valign="top" width="11.910000000000002%" headers="mcps1.2.6.1.2 "><p id="p15015581132"><a name="p15015581132"></a><a name="p15015581132"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.330000000000002%" headers="mcps1.2.6.1.3 "><p id="p850915312546"><a name="p850915312546"></a><a name="p850915312546"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="30.060000000000002%" headers="mcps1.2.6.1.4 "><p id="p12715141542513"><a name="p12715141542513"></a><a name="p12715141542513"></a><span>是否对输入展平为2D进行计算</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="26.94%" headers="mcps1.2.6.1.5 "><p id="p35331053152419"><a name="p35331053152419"></a><a name="p35331053152419"></a>-</p>
</td>
</tr>
<tr id="row189543217113"><td class="cellrowborder" valign="top" width="18.76%" headers="mcps1.2.6.1.1 "><p id="p3771652101218"><a name="p3771652101218"></a><a name="p3771652101218"></a>asymmetric_quantize_inputs</p>
</td>
<td class="cellrowborder" valign="top" width="11.910000000000002%" headers="mcps1.2.6.1.2 "><p id="p16508581531"><a name="p16508581531"></a><a name="p16508581531"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.330000000000002%" headers="mcps1.2.6.1.3 "><p id="p8896113216114"><a name="p8896113216114"></a><a name="p8896113216114"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="30.060000000000002%" headers="mcps1.2.6.1.4 "><p id="p589620321015"><a name="p589620321015"></a><a name="p589620321015"></a><span>是否对输入进行非对称量化</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="26.94%" headers="mcps1.2.6.1.5 "><p id="p13463658122419"><a name="p13463658122419"></a><a name="p13463658122419"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 要求使用静态形状 |
| FP32 | 支持 | 要求使用静态形状 |

### BatchMatmul<a name="ZH-CN_TOPIC_0000002421627894" id="ZH-CN_TOPIC_0000002421627894"></a>

**功能描述<a name="section37550136507"></a>**

对两个2D/3D/4D输入张量进行矩阵乘法运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>BatchMatmul暂时不支持广播机制，x倒数两维为计算维度\[M, K\]，y倒数两维为计算维度\[K, N\]，K大小必须保持一致。计算维度前，维度必须保持一致。

**表 1**  BatchMatmul参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="18.02%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.4%" id="mcps1.2.6.1.2"><p id="p164533111319"><a name="p164533111319"></a><a name="p164533111319"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.53%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="34.68%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.369999999999997%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row622511541825"><td class="cellrowborder" valign="top" width="18.02%" headers="mcps1.2.6.1.1 "><p id="p112257544213"><a name="p112257544213"></a><a name="p112257544213"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.4%" headers="mcps1.2.6.1.2 "><p id="p17783152895719"><a name="p17783152895719"></a><a name="p17783152895719"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.53%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="34.68%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为3D/4D，格式分别为NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="23.369999999999997%" headers="mcps1.2.6.1.5 "><p id="p152258541128"><a name="p152258541128"></a><a name="p152258541128"></a>-</p>
</td>
</tr>
<tr id="row2077165116215"><td class="cellrowborder" valign="top" width="18.02%" headers="mcps1.2.6.1.1 "><p id="p13777511528"><a name="p13777511528"></a><a name="p13777511528"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.4%" headers="mcps1.2.6.1.2 "><p id="p768141275618"><a name="p768141275618"></a><a name="p768141275618"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.53%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="34.68%" headers="mcps1.2.6.1.4 "><p id="p1077351627"><a name="p1077351627"></a><a name="p1077351627"></a>权重张量，维度为3D/4D，格式分别为NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="23.369999999999997%" headers="mcps1.2.6.1.5 "><p id="p1478145119215"><a name="p1478145119215"></a><a name="p1478145119215"></a>-</p>
</td>
</tr>
<tr id="row785516466218"><td class="cellrowborder" valign="top" width="18.02%" headers="mcps1.2.6.1.1 "><p id="p085513466213"><a name="p085513466213"></a><a name="p085513466213"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.4%" headers="mcps1.2.6.1.2 "><p id="p1245412116319"><a name="p1245412116319"></a><a name="p1245412116319"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.53%" headers="mcps1.2.6.1.3 "><p id="p148550467217"><a name="p148550467217"></a><a name="p148550467217"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="34.68%" headers="mcps1.2.6.1.4 "><p id="p188554460214"><a name="p188554460214"></a><a name="p188554460214"></a>输出张量，维度为3D/4D，格式分别为NWC、NHWC。符合矩阵乘法运算规则。</p>
</td>
<td class="cellrowborder" valign="top" width="23.369999999999997%" headers="mcps1.2.6.1.5 "><p id="p1385574613215"><a name="p1385574613215"></a><a name="p1385574613215"></a>-</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="18.02%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>adj_x</p>
</td>
<td class="cellrowborder" valign="top" width="11.4%" headers="mcps1.2.6.1.2 "><p id="p1150158930"><a name="p1150158930"></a><a name="p1150158930"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.53%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="34.68%" headers="mcps1.2.6.1.4 "><p id="p1486615211304"><a name="p1486615211304"></a><a name="p1486615211304"></a>是否对x的最后两个维度进行转置。</p>
</td>
<td class="cellrowborder" valign="top" width="23.369999999999997%" headers="mcps1.2.6.1.5 "><p id="p1622416295371"><a name="p1622416295371"></a><a name="p1622416295371"></a>-</p>
</td>
</tr>
<tr id="row46789503544"><td class="cellrowborder" valign="top" width="18.02%" headers="mcps1.2.6.1.1 "><p id="p9156191441212"><a name="p9156191441212"></a><a name="p9156191441212"></a>adj_y</p>
</td>
<td class="cellrowborder" valign="top" width="11.4%" headers="mcps1.2.6.1.2 "><p id="p15015581132"><a name="p15015581132"></a><a name="p15015581132"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.53%" headers="mcps1.2.6.1.3 "><p id="p17678145075410"><a name="p17678145075410"></a><a name="p17678145075410"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="34.68%" headers="mcps1.2.6.1.4 "><p id="p45991644144318"><a name="p45991644144318"></a><a name="p45991644144318"></a>是否对y的最后两个维度进行转置。</p>
</td>
<td class="cellrowborder" valign="top" width="23.369999999999997%" headers="mcps1.2.6.1.5 "><p id="p52247295374"><a name="p52247295374"></a><a name="p52247295374"></a>-</p>
</td>
</tr>
<tr id="row189543217113"><td class="cellrowborder" valign="top" width="18.02%" headers="mcps1.2.6.1.1 "><p id="p3771652101218"><a name="p3771652101218"></a><a name="p3771652101218"></a>asymmetric_quantize_inputs</p>
</td>
<td class="cellrowborder" valign="top" width="11.4%" headers="mcps1.2.6.1.2 "><p id="p16508581531"><a name="p16508581531"></a><a name="p16508581531"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.53%" headers="mcps1.2.6.1.3 "><p id="p8896113216114"><a name="p8896113216114"></a><a name="p8896113216114"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="34.68%" headers="mcps1.2.6.1.4 "><p id="p3243165520376"><a name="p3243165520376"></a><a name="p3243165520376"></a><span>BatchMatmul是否对输入进行非对称量化</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="23.369999999999997%" headers="mcps1.2.6.1.5 "><p id="p13463658122419"><a name="p13463658122419"></a><a name="p13463658122419"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Softmax<a name="ZH-CN_TOPIC_0000002360223141" id="ZH-CN_TOPIC_0000002360223141"></a>

**功能描述<a name="section37550136507"></a>**

计算最后一维的归一化Softmax概率分布。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>受TFLite限制，Softmax仅支持在最后一维上进行计算。

**表 1**  Softmax参数概览

<a name="table1033212264218"></a>
<table><thead align="left"><tr id="row133331626923"><th class="cellrowborder" valign="top" width="17.89178917891789%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.14111411141114%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.09130913091309%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.17311731173117%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.7026702670267%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row11968131541819"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.17311731173117%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D / 3D / 4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.7026702670267%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row131890194187"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p0189101910184"><a name="p0189101910184"></a><a name="p0189101910184"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p418914198187"><a name="p418914198187"></a><a name="p418914198187"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.17311731173117%" headers="mcps1.2.6.1.4 "><p id="p121892195182"><a name="p121892195182"></a><a name="p121892195182"></a>输出张量，维度为2D / 3D / 4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.7026702670267%" headers="mcps1.2.6.1.5 "><p id="p1118918198181"><a name="p1118918198181"></a><a name="p1118918198181"></a>-</p>
</td>
</tr>
<tr id="row689365022815"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p106921159195616"><a name="p106921159195616"></a><a name="p106921159195616"></a>beta</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p85376113524"><a name="p85376113524"></a><a name="p85376113524"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p56921593564"><a name="p56921593564"></a><a name="p56921593564"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="31.17311731173117%" headers="mcps1.2.6.1.4 "><p id="p136921359195618"><a name="p136921359195618"></a><a name="p136921359195618"></a>对输入的缩放系数。</p>
</td>
<td class="cellrowborder" valign="top" width="26.7026702670267%" headers="mcps1.2.6.1.5 "><p id="p4340724152416"><a name="p4340724152416"></a><a name="p4340724152416"></a>配置范围：暂仅支持beta=1.0的情况</p>
</td>
</tr>
</tbody>
</table>

### Relu<a name="ZH-CN_TOPIC_0000002326184642" id="ZH-CN_TOPIC_0000002326184642"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量做Relu激活函数运算。

**参数说明<a name="section162919203502"></a>**

**表 1**  Relu参数概览

<a name="table542733973118"></a>
<table><thead align="left"><tr id="row742723916319"><th class="cellrowborder" valign="top" width="17.89178917891789%" id="mcps1.2.6.1.1"><p id="p6427153917312"><a name="p6427153917312"></a><a name="p6427153917312"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.14111411141114%" id="mcps1.2.6.1.2"><p id="p4537611185218"><a name="p4537611185218"></a><a name="p4537611185218"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.09130913091309%" id="mcps1.2.6.1.3"><p id="p1942815397310"><a name="p1942815397310"></a><a name="p1942815397310"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.18311831183118%" id="mcps1.2.6.1.4"><p id="p114282039103112"><a name="p114282039103112"></a><a name="p114282039103112"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.692669266926693%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row11968131541819"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.18311831183118%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.692669266926693%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row131890194187"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p0189101910184"><a name="p0189101910184"></a><a name="p0189101910184"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p418914198187"><a name="p418914198187"></a><a name="p418914198187"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.18311831183118%" headers="mcps1.2.6.1.4 "><p id="p121892195182"><a name="p121892195182"></a><a name="p121892195182"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.692669266926693%" headers="mcps1.2.6.1.5 "><p id="p1118918198181"><a name="p1118918198181"></a><a name="p1118918198181"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 当前Activation训练反向仅支持ReLU |
| FP32 | 支持 | 当前Activation训练反向仅支持ReLU |

### Tanh<a name="ZH-CN_TOPIC_0000002474804265" id="ZH-CN_TOPIC_0000002474804265"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量做Tanh激活函数运算。

**参数说明<a name="section162919203502"></a>**

**表 1**  Tanh参数概览

<a name="table542733973118"></a>
<table><thead align="left"><tr id="row742723916319"><th class="cellrowborder" valign="top" width="17.89178917891789%" id="mcps1.2.6.1.1"><p id="p6427153917312"><a name="p6427153917312"></a><a name="p6427153917312"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.14111411141114%" id="mcps1.2.6.1.2"><p id="p4537611185218"><a name="p4537611185218"></a><a name="p4537611185218"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.09130913091309%" id="mcps1.2.6.1.3"><p id="p1942815397310"><a name="p1942815397310"></a><a name="p1942815397310"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.293129312931296%" id="mcps1.2.6.1.4"><p id="p114282039103112"><a name="p114282039103112"></a><a name="p114282039103112"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.58265826582658%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row11968131541819"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.293129312931296%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.58265826582658%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row131890194187"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p0189101910184"><a name="p0189101910184"></a><a name="p0189101910184"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p418914198187"><a name="p418914198187"></a><a name="p418914198187"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.293129312931296%" headers="mcps1.2.6.1.4 "><p id="p121892195182"><a name="p121892195182"></a><a name="p121892195182"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.58265826582658%" headers="mcps1.2.6.1.5 "><p id="p1118918198181"><a name="p1118918198181"></a><a name="p1118918198181"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Logistic \(Sigmoid\)<a name="ZH-CN_TOPIC_0000002441404462" id="ZH-CN_TOPIC_0000002441404462"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量做Sigmoid激活函数运算。

**参数说明<a name="section162919203502"></a>**

**表 1**  Logistic参数概览

<a name="table542733973118"></a>
<table><thead align="left"><tr id="row742723916319"><th class="cellrowborder" valign="top" width="17.89178917891789%" id="mcps1.2.6.1.1"><p id="p6427153917312"><a name="p6427153917312"></a><a name="p6427153917312"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.14111411141114%" id="mcps1.2.6.1.2"><p id="p4537611185218"><a name="p4537611185218"></a><a name="p4537611185218"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.09130913091309%" id="mcps1.2.6.1.3"><p id="p1942815397310"><a name="p1942815397310"></a><a name="p1942815397310"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.463146314631462%" id="mcps1.2.6.1.4"><p id="p114282039103112"><a name="p114282039103112"></a><a name="p114282039103112"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.412641264126414%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row11968131541819"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.463146314631462%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.412641264126414%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row131890194187"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p0189101910184"><a name="p0189101910184"></a><a name="p0189101910184"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p418914198187"><a name="p418914198187"></a><a name="p418914198187"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.463146314631462%" headers="mcps1.2.6.1.4 "><p id="p121892195182"><a name="p121892195182"></a><a name="p121892195182"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.412641264126414%" headers="mcps1.2.6.1.5 "><p id="p1118918198181"><a name="p1118918198181"></a><a name="p1118918198181"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Reshape<a name="ZH-CN_TOPIC_0000002360102993" id="ZH-CN_TOPIC_0000002360102993"></a>

**功能描述<a name="section37550136507"></a>**

改变Tensor的Shape，但不改变其排布。

**参数说明<a name="section162919203502"></a>**

**表 1**  Reshape参数概览

<a name="table542733973118"></a>
<table><thead align="left"><tr id="row742723916319"><th class="cellrowborder" valign="top" width="17.89178917891789%" id="mcps1.2.6.1.1"><p id="p6427153917312"><a name="p6427153917312"></a><a name="p6427153917312"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.14111411141114%" id="mcps1.2.6.1.2"><p id="p4537611185218"><a name="p4537611185218"></a><a name="p4537611185218"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.09130913091309%" id="mcps1.2.6.1.3"><p id="p1942815397310"><a name="p1942815397310"></a><a name="p1942815397310"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.633163316331636%" id="mcps1.2.6.1.4"><p id="p114282039103112"><a name="p114282039103112"></a><a name="p114282039103112"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.242624262426244%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row11968131541819"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.633163316331636%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.242624262426244%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row93786149424"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p15763919174214"><a name="p15763919174214"></a><a name="p15763919174214"></a>shape</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p1876312194423"><a name="p1876312194423"></a><a name="p1876312194423"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="31.633163316331636%" headers="mcps1.2.6.1.4 "><p id="p19883459134217"><a name="p19883459134217"></a><a name="p19883459134217"></a>Shape张量，转换后的Shape。</p>
</td>
<td class="cellrowborder" valign="top" width="26.242624262426244%" headers="mcps1.2.6.1.5 "><p id="p97631219114220"><a name="p97631219114220"></a><a name="p97631219114220"></a>规格约束：所有元素之积与input包含的元素个数相等</p>
</td>
</tr>
<tr id="row131890194187"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p0189101910184"><a name="p0189101910184"></a><a name="p0189101910184"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p418914198187"><a name="p418914198187"></a><a name="p418914198187"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.633163316331636%" headers="mcps1.2.6.1.4 "><p id="p121892195182"><a name="p121892195182"></a><a name="p121892195182"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.242624262426244%" headers="mcps1.2.6.1.5 "><p id="p1118918198181"><a name="p1118918198181"></a><a name="p1118918198181"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 输入和输出元素数量必须一致 |
| FP32 | 支持 | 输入和输出元素数量必须一致 |

### Mul<a name="ZH-CN_TOPIC_0000002421789214" id="ZH-CN_TOPIC_0000002421789214"></a>

**功能描述<a name="section37550136507"></a>**

计算两个矩阵逐点相乘。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Mul支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Mul参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
<tr id="row33451752161111"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p6218353165419"><a name="p6218353165419"></a><a name="p6218353165419"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>配置范围：NONE、RELU</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 支持范围取决于输入角色和广播规格 |

### Add<a name="ZH-CN_TOPIC_0000002454832349" id="ZH-CN_TOPIC_0000002454832349"></a>

**功能描述<a name="section37550136507"></a>**

计算两个矩阵逐点相加。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Add支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Add参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>左输入张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>右输入张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
<tr id="row33451752161111"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p6218353165419"><a name="p6218353165419"></a><a name="p6218353165419"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>配置范围：NONE、RELU</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 支持范围取决于输入角色和广播规格 |

### Sub<a name="ZH-CN_TOPIC_0000002454792461" id="ZH-CN_TOPIC_0000002454792461"></a>

**功能描述<a name="section37550136507"></a>**

计算两个矩阵逐点相减。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Sub支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Sub参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>左输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>右输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
<tr id="row33451752161111"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p6218353165419"><a name="p6218353165419"></a><a name="p6218353165419"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>配置范围：NONE、RELU</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 支持范围取决于输入角色和广播规格 |

### Gather<a name="ZH-CN_TOPIC_0000002421683676" id="ZH-CN_TOPIC_0000002421683676"></a>

**功能描述<a name="section129901354195417"></a>**

根据指定索引，从输入张量的指定轴上提取元素，组合成新张量

**参数说明<a name="section162919203502"></a>**

**表 1**  Gather参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.67%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.65%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.169999999999998%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>params</p>
</td>
<td class="cellrowborder" valign="top" width="11.67%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.65%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.169999999999998%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>indices</p>
</td>
<td class="cellrowborder" valign="top" width="11.67%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.65%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="31.169999999999998%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>索引张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.67%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.65%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.169999999999998%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
<tr id="row21949558593"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p1628915591592"><a name="p1628915591592"></a><a name="p1628915591592"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="11.67%" headers="mcps1.2.6.1.2 "><p id="p4289105915916"><a name="p4289105915916"></a><a name="p4289105915916"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.65%" headers="mcps1.2.6.1.3 "><p id="p825114289017"><a name="p825114289017"></a><a name="p825114289017"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.169999999999998%" headers="mcps1.2.6.1.4 "><p id="p108197531101"><a name="p108197531101"></a><a name="p108197531101"></a>输入张量被切分的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="26%" headers="mcps1.2.6.1.5 "><p id="p1525013286014"><a name="p1525013286014"></a><a name="p1525013286014"></a>-rank(value)<=axis<rank(value)，rank为张量的秩</p>
</td>
</tr>
<tr id="row33451752161111"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>batch_dims</p>
</td>
<td class="cellrowborder" valign="top" width="11.67%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.65%" headers="mcps1.2.6.1.3 "><p id="p1925082817014"><a name="p1925082817014"></a><a name="p1925082817014"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.169999999999998%" headers="mcps1.2.6.1.4 "><p id="p32505281005"><a name="p32505281005"></a><a name="p32505281005"></a>将索引的前batch_dims个轴作为batch轴，切分行为有所改变。</p>
</td>
<td class="cellrowborder" valign="top" width="26%" headers="mcps1.2.6.1.5 "><p id="p6237172817014"><a name="p6237172817014"></a><a name="p6237172817014"></a>仅支持为batch_dims为0的情况</p>
</td>
</tr>
</tbody>
</table>

### Split<a name="ZH-CN_TOPIC_0000002455529089" id="ZH-CN_TOPIC_0000002455529089"></a>

Split算子在TFLITE框架中包含tfl.Split、tfl.SplitV等api，其中tfl.Split表示均匀划分，tfl.SplitV自定义非均匀划分。

-   **[Split](#ZH-CN_TOPIC_0000002482924716)**  

-   **[SplitV](#ZH-CN_TOPIC_0000002515004717)**  

#### Split<a name="ZH-CN_TOPIC_0000002482924716" id="ZH-CN_TOPIC_0000002482924716"></a>

**功能描述<a name="section129901354195417"></a>**

对张量分割按照某一轴平均切分成若干份。

**参数说明<a name="section14760100195516"></a>**

**表 1**  Split参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="17.508249175082494%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.998800119988001%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.588641135886412%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.956904309569044%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.947405259474053%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16313163412813"><td class="cellrowborder" valign="top" width="17.508249175082494%" headers="mcps1.2.6.1.1 "><p id="p498695217811"><a name="p498695217811"></a><a name="p498695217811"></a>value</p>
</td>
<td class="cellrowborder" valign="top" width="11.998800119988001%" headers="mcps1.2.6.1.2 "><p id="p798675218810"><a name="p798675218810"></a><a name="p798675218810"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.588641135886412%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.956904309569044%" headers="mcps1.2.6.1.4 "><p id="p398625217814"><a name="p398625217814"></a><a name="p398625217814"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.947405259474053%" headers="mcps1.2.6.1.5 "><p id="p3348132719916"><a name="p3348132719916"></a><a name="p3348132719916"></a>-</p>
</td>
</tr>
<tr id="row191569471550"><td class="cellrowborder" valign="top" width="17.508249175082494%" headers="mcps1.2.6.1.1 "><p id="p35882421986"><a name="p35882421986"></a><a name="p35882421986"></a>outputs</p>
</td>
<td class="cellrowborder" valign="top" width="11.998800119988001%" headers="mcps1.2.6.1.2 "><p id="p2589042983"><a name="p2589042983"></a><a name="p2589042983"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.588641135886412%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>varList(tensor)</p>
</td>
<td class="cellrowborder" valign="top" width="30.956904309569044%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.947405259474053%" headers="mcps1.2.6.1.5 "><p id="p133477272913"><a name="p133477272913"></a><a name="p133477272913"></a>-</p>
</td>
</tr>
<tr id="row15423221105011"><td class="cellrowborder" valign="top" width="17.508249175082494%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>num_splits</p>
</td>
<td class="cellrowborder" valign="top" width="11.998800119988001%" headers="mcps1.2.6.1.2 "><p id="p149461556450"><a name="p149461556450"></a><a name="p149461556450"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.588641135886412%" headers="mcps1.2.6.1.3 "><p id="p598010321611"><a name="p598010321611"></a><a name="p598010321611"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="30.956904309569044%" headers="mcps1.2.6.1.4 "><p id="p1726419586519"><a name="p1726419586519"></a><a name="p1726419586519"></a>平均分割的数量。</p>
</td>
<td class="cellrowborder" valign="top" width="25.947405259474053%" headers="mcps1.2.6.1.5 "><p id="p191284445610"><a name="p191284445610"></a><a name="p191284445610"></a>(0, split_dim] ，且 num_splits需要能被指定轴整除</p>
</td>
</tr>
<tr id="row164361335164118"><td class="cellrowborder" valign="top" width="17.508249175082494%" headers="mcps1.2.6.1.1 "><p id="p15436835124114"><a name="p15436835124114"></a><a name="p15436835124114"></a>split_dim</p>
</td>
<td class="cellrowborder" valign="top" width="11.998800119988001%" headers="mcps1.2.6.1.2 "><p id="p4289105915916"><a name="p4289105915916"></a><a name="p4289105915916"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.588641135886412%" headers="mcps1.2.6.1.3 "><p id="p825114289017"><a name="p825114289017"></a><a name="p825114289017"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="30.956904309569044%" headers="mcps1.2.6.1.4 "><p id="p108197531101"><a name="p108197531101"></a><a name="p108197531101"></a>指定被分割的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="25.947405259474053%" headers="mcps1.2.6.1.5 "><p id="p1525013286014"><a name="p1525013286014"></a><a name="p1525013286014"></a>维度索引</p>
</td>
</tr>
</tbody>
</table>

#### SplitV<a name="ZH-CN_TOPIC_0000002515004717" id="ZH-CN_TOPIC_0000002515004717"></a>

**功能描述<a name="section171987343553"></a>**

对张量分割按照某一轴非平均切分成若干份。

**参数说明<a name="section8688203805511"></a>**

**表 1**  SplitV参数概览

<a name="table6107104291014"></a>
<table><thead align="left"><tr id="row10107842101012"><th class="cellrowborder" valign="top" width="17.228277172282773%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.218778122187782%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.1985801419858%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.626937306269376%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.72742725727427%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16313163412813"><td class="cellrowborder" valign="top" width="17.228277172282773%" headers="mcps1.2.6.1.1 "><p id="p498695217811"><a name="p498695217811"></a><a name="p498695217811"></a>value</p>
</td>
<td class="cellrowborder" valign="top" width="12.218778122187782%" headers="mcps1.2.6.1.2 "><p id="p798675218810"><a name="p798675218810"></a><a name="p798675218810"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.1985801419858%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.626937306269376%" headers="mcps1.2.6.1.4 "><p id="p398625217814"><a name="p398625217814"></a><a name="p398625217814"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.72742725727427%" headers="mcps1.2.6.1.5 "><p id="p3348132719916"><a name="p3348132719916"></a><a name="p3348132719916"></a>-</p>
</td>
</tr>
<tr id="row191569471550"><td class="cellrowborder" valign="top" width="17.228277172282773%" headers="mcps1.2.6.1.1 "><p id="p35882421986"><a name="p35882421986"></a><a name="p35882421986"></a>outputs</p>
</td>
<td class="cellrowborder" valign="top" width="12.218778122187782%" headers="mcps1.2.6.1.2 "><p id="p2589042983"><a name="p2589042983"></a><a name="p2589042983"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.1985801419858%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>varList(tensor)</p>
</td>
<td class="cellrowborder" valign="top" width="30.626937306269376%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.72742725727427%" headers="mcps1.2.6.1.5 "><p id="p133477272913"><a name="p133477272913"></a><a name="p133477272913"></a>-</p>
</td>
</tr>
<tr id="row156999123132"><td class="cellrowborder" valign="top" width="17.228277172282773%" headers="mcps1.2.6.1.1 "><p id="p14700191217139"><a name="p14700191217139"></a><a name="p14700191217139"></a>num_splits</p>
</td>
<td class="cellrowborder" valign="top" width="12.218778122187782%" headers="mcps1.2.6.1.2 "><p id="p37001912101317"><a name="p37001912101317"></a><a name="p37001912101317"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.1985801419858%" headers="mcps1.2.6.1.3 "><p id="p6700612171312"><a name="p6700612171312"></a><a name="p6700612171312"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="30.626937306269376%" headers="mcps1.2.6.1.4 "><p id="p3700121219131"><a name="p3700121219131"></a><a name="p3700121219131"></a>分割的数量。</p>
</td>
<td class="cellrowborder" valign="top" width="25.72742725727427%" headers="mcps1.2.6.1.5 "><p id="p77001912191313"><a name="p77001912191313"></a><a name="p77001912191313"></a>-</p>
</td>
</tr>
<tr id="row6107174251010"><td class="cellrowborder" valign="top" width="17.228277172282773%" headers="mcps1.2.6.1.1 "><p id="p31078421103"><a name="p31078421103"></a><a name="p31078421103"></a>size_splits</p>
</td>
<td class="cellrowborder" valign="top" width="12.218778122187782%" headers="mcps1.2.6.1.2 "><p id="p91077427108"><a name="p91077427108"></a><a name="p91077427108"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.1985801419858%" headers="mcps1.2.6.1.3 "><p id="p2010715429101"><a name="p2010715429101"></a><a name="p2010715429101"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.626937306269376%" headers="mcps1.2.6.1.4 "><p id="p18107442101017"><a name="p18107442101017"></a><a name="p18107442101017"></a>具体每一份分割的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="25.72742725727427%" headers="mcps1.2.6.1.5 "><p id="p1071521961116"><a name="p1071521961116"></a><a name="p1071521961116"></a>[n<sub id="sub163541521663"><a name="sub163541521663"></a><a name="sub163541521663"></a>1</sub>, n<sub id="sub195419472612"><a name="sub195419472612"></a><a name="sub195419472612"></a>2</sub>, ..., n<sub id="sub1888985915616"><a name="sub1888985915616"></a><a name="sub1888985915616"></a>i</sub>]，∑n<sub id="sub1493118464"><a name="sub1493118464"></a><a name="sub1493118464"></a>i</sub> = axis，n > 0</p>
</td>
</tr>
<tr id="row610711426106"><td class="cellrowborder" valign="top" width="17.228277172282773%" headers="mcps1.2.6.1.1 "><p id="p1810754216104"><a name="p1810754216104"></a><a name="p1810754216104"></a>split_dim</p>
</td>
<td class="cellrowborder" valign="top" width="12.218778122187782%" headers="mcps1.2.6.1.2 "><p id="p4289105915916"><a name="p4289105915916"></a><a name="p4289105915916"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.1985801419858%" headers="mcps1.2.6.1.3 "><p id="p825114289017"><a name="p825114289017"></a><a name="p825114289017"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="30.626937306269376%" headers="mcps1.2.6.1.4 "><p id="p108197531101"><a name="p108197531101"></a><a name="p108197531101"></a>被分割的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="25.72742725727427%" headers="mcps1.2.6.1.5 "><p id="p1525013286014"><a name="p1525013286014"></a><a name="p1525013286014"></a>-rank(value)<=axis<rank(value)，rank为张量的秩</p>
</td>
</tr>
</tbody>
</table>

### Concatenation<a name="ZH-CN_TOPIC_0000002421843540" id="ZH-CN_TOPIC_0000002421843540"></a>

**功能描述<a name="section171987343553"></a>**

将多个张量拼接成某一个张量。

**参数说明<a name="section8688203805511"></a>**

**表 1**  Concatenation参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="17.078292170782923%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.348665133486653%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.928807119288072%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.00679932006799%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.637436256374365%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row2423132175015"><td class="cellrowborder" valign="top" width="17.078292170782923%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>values</p>
</td>
<td class="cellrowborder" valign="top" width="13.348665133486653%" headers="mcps1.2.6.1.2 "><p id="p189321956152"><a name="p189321956152"></a><a name="p189321956152"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.928807119288072%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>varList(tensor)</p>
</td>
<td class="cellrowborder" valign="top" width="32.00679932006799%" headers="mcps1.2.6.1.4 "><p id="p19305746101210"><a name="p19305746101210"></a><a name="p19305746101210"></a>输入张量列表，内部各张量维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.637436256374365%" headers="mcps1.2.6.1.5 "><p id="p66671634141811"><a name="p66671634141811"></a><a name="p66671634141811"></a>规格约束：列表中各张量在指定轴上元素个数相等</p>
</td>
</tr>
<tr id="row334168176"><td class="cellrowborder" valign="top" width="17.078292170782923%" headers="mcps1.2.6.1.1 "><p id="p6341189713"><a name="p6341189713"></a><a name="p6341189713"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.348665133486653%" headers="mcps1.2.6.1.2 "><p id="p6341289719"><a name="p6341289719"></a><a name="p6341289719"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.928807119288072%" headers="mcps1.2.6.1.3 "><p id="p6181781394"><a name="p6181781394"></a><a name="p6181781394"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.00679932006799%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.637436256374365%" headers="mcps1.2.6.1.5 "><p id="p55991825111919"><a name="p55991825111919"></a><a name="p55991825111919"></a>-</p>
</td>
</tr>
<tr id="row175528015178"><td class="cellrowborder" valign="top" width="17.078292170782923%" headers="mcps1.2.6.1.1 "><p id="p11498144101710"><a name="p11498144101710"></a><a name="p11498144101710"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="13.348665133486653%" headers="mcps1.2.6.1.2 "><p id="p1498946175"><a name="p1498946175"></a><a name="p1498946175"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.928807119288072%" headers="mcps1.2.6.1.3 "><p id="p1649814141714"><a name="p1649814141714"></a><a name="p1649814141714"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.00679932006799%" headers="mcps1.2.6.1.4 "><p id="p174988410177"><a name="p174988410177"></a><a name="p174988410177"></a>指定沿着哪个轴进行连接。</p>
</td>
<td class="cellrowborder" valign="top" width="25.637436256374365%" headers="mcps1.2.6.1.5 "><p id="p1525013286014"><a name="p1525013286014"></a><a name="p1525013286014"></a>规格约束：-rank(value)<=axis<rank(value)，rank为张量的秩</p>
</td>
</tr>
<tr id="row195632034203"><td class="cellrowborder" valign="top" width="17.078292170782923%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="13.348665133486653%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.928807119288072%" headers="mcps1.2.6.1.3 "><p id="p6218353165419"><a name="p6218353165419"></a><a name="p6218353165419"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="32.00679932006799%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="25.637436256374365%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>配置范围：NONE、RELU</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 输入rank、axis和静态形状必须满足拼接约束 |

### AveragePool2D<a name="ZH-CN_TOPIC_0000002455282373" id="ZH-CN_TOPIC_0000002455282373"></a>

**功能描述<a name="section113841812134710"></a>**

对4D输入进行平均池化计算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  AveragePool2D参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="16.8983101689831%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.95870412958704%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.088591140885912%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.556944305569438%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.497450254974503%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16660151211817"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.95870412958704%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.088591140885912%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p194831017511"><a name="p194831017511"></a><a name="p194831017511"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.95870412958704%" headers="mcps1.2.6.1.2 "><p id="p048340450"><a name="p048340450"></a><a name="p048340450"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.088591140885912%" headers="mcps1.2.6.1.3 "><p id="p124839018518"><a name="p124839018518"></a><a name="p124839018518"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p13483801352"><a name="p13483801352"></a><a name="p13483801352"></a>输出张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p748310020510"><a name="p748310020510"></a><a name="p748310020510"></a>-</p>
</td>
</tr>
<tr id="row158205562211"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p1269165919569"><a name="p1269165919569"></a><a name="p1269165919569"></a>filter_height</p>
</td>
<td class="cellrowborder" valign="top" width="12.95870412958704%" headers="mcps1.2.6.1.2 "><p id="p2509588318"><a name="p2509588318"></a><a name="p2509588318"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.088591140885912%" headers="mcps1.2.6.1.3 "><p id="p469110599562"><a name="p469110599562"></a><a name="p469110599562"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p126911459165613"><a name="p126911459165613"></a><a name="p126911459165613"></a>在H方向上的过滤窗口大小。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1447651443920"><a name="p1447651443920"></a><a name="p1447651443920"></a>-</p>
</td>
</tr>
<tr id="row9660171281818"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p1169119595569"><a name="p1169119595569"></a><a name="p1169119595569"></a>filter_width</p>
</td>
<td class="cellrowborder" valign="top" width="12.95870412958704%" headers="mcps1.2.6.1.2 "><p id="p65015581736"><a name="p65015581736"></a><a name="p65015581736"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.088591140885912%" headers="mcps1.2.6.1.3 "><p id="p769119597568"><a name="p769119597568"></a><a name="p769119597568"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p1614615144496"><a name="p1614615144496"></a><a name="p1614615144496"></a>在W方向上的过滤窗口大小。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p185499219400"><a name="p185499219400"></a><a name="p185499219400"></a>-</p>
</td>
</tr>
<tr id="row7660151212186"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p3692859195613"><a name="p3692859195613"></a><a name="p3692859195613"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="12.95870412958704%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.088591140885912%" headers="mcps1.2.6.1.3 "><p id="p15692145965619"><a name="p15692145965619"></a><a name="p15692145965619"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p833042514011"><a name="p833042514011"></a><a name="p833042514011"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p7692759195616"><a name="p7692759195616"></a><a name="p7692759195616"></a>配置范围：NONE、RELU</p>
</td>
</tr>
<tr id="row16661101271811"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p96921059125614"><a name="p96921059125614"></a><a name="p96921059125614"></a>padding</p>
</td>
<td class="cellrowborder" valign="top" width="12.95870412958704%" headers="mcps1.2.6.1.2 "><p id="p1150158930"><a name="p1150158930"></a><a name="p1150158930"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.088591140885912%" headers="mcps1.2.6.1.3 "><p id="p76921259115619"><a name="p76921259115619"></a><a name="p76921259115619"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p10118203645110"><a name="p10118203645110"></a><a name="p10118203645110"></a>填充类型。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1769285995619"><a name="p1769285995619"></a><a name="p1769285995619"></a>配置范围：SAME、VALID</p>
</td>
</tr>
<tr id="row167819451027"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p106921159195616"><a name="p106921159195616"></a><a name="p106921159195616"></a>stride_h</p>
</td>
<td class="cellrowborder" valign="top" width="12.95870412958704%" headers="mcps1.2.6.1.2 "><p id="p15015581132"><a name="p15015581132"></a><a name="p15015581132"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.088591140885912%" headers="mcps1.2.6.1.3 "><p id="p56921593564"><a name="p56921593564"></a><a name="p56921593564"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p136921359195618"><a name="p136921359195618"></a><a name="p136921359195618"></a>filter在H方向上的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p523152894518"><a name="p523152894518"></a><a name="p523152894518"></a>-</p>
</td>
</tr>
<tr id="row16661171281819"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p1898353317457"><a name="p1898353317457"></a><a name="p1898353317457"></a>stride_w</p>
</td>
<td class="cellrowborder" valign="top" width="12.95870412958704%" headers="mcps1.2.6.1.2 "><p id="p16508581531"><a name="p16508581531"></a><a name="p16508581531"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.088591140885912%" headers="mcps1.2.6.1.3 "><p id="p499819412458"><a name="p499819412458"></a><a name="p499819412458"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p1399834134511"><a name="p1399834134511"></a><a name="p1399834134511"></a>filter在W方向上的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1798314337454"><a name="p1798314337454"></a><a name="p1798314337454"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Tile<a name="ZH-CN_TOPIC_0000002480985174" id="ZH-CN_TOPIC_0000002480985174"></a>

**功能描述<a name="section113841812134710"></a>**

对2D/3D/4D输入沿指定维度做复制扩展。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Tile参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="16.8983101689831%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.938706129387059%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.108589141085892%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.556944305569438%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.497450254974503%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16660151211817"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p167712418440"><a name="p167712418440"></a><a name="p167712418440"></a>multiples</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p077044174411"><a name="p077044174411"></a><a name="p077044174411"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p676912411444"><a name="p676912411444"></a><a name="p676912411444"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p576810417443"><a name="p576810417443"></a><a name="p576810417443"></a>指定每个维度复制次数。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p17661841144412"><a name="p17661841144412"></a><a name="p17661841144412"></a>规格约束：multiples为离线常量</p>
</td>
</tr>
<tr id="row158205562211"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p163562048134411"><a name="p163562048134411"></a><a name="p163562048134411"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p03551948164416"><a name="p03551948164416"></a><a name="p03551948164416"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p173541548184411"><a name="p173541548184411"></a><a name="p173541548184411"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p123531648164412"><a name="p123531648164412"></a><a name="p123531648164412"></a>输出张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p143521048174416"><a name="p143521048174416"></a><a name="p143521048174416"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Pad<a name="ZH-CN_TOPIC_0000002480985538" id="ZH-CN_TOPIC_0000002480985538"></a>

Pad算子在TFLITE框架中包含tfl.Pad、tfl.PadV2、tfl.Mirror\_Pad等api，其中tfl.Pad表示零填充，tfl.Padv2表示自定义常量填充，tfl.Mirror\_Pad表示镜像反射填充。

-   **[Pad](#ZH-CN_TOPIC_0000002513166431)**  

-   **[PadV2](#ZH-CN_TOPIC_0000002513006453)**  

-   **[Mirror\_Pad](#ZH-CN_TOPIC_0000002480886588)**  

#### Pad<a name="ZH-CN_TOPIC_0000002513166431" id="ZH-CN_TOPIC_0000002513166431"></a>

**功能描述<a name="section69069544112"></a>**

对输入张量边界做零填充。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Pad参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="16.8983101689831%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.938706129387059%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.108589141085892%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.556944305569438%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.497450254974503%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16660151211817"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>规格约束：int8量化场景仅支持4D张量输入</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p167712418440"><a name="p167712418440"></a><a name="p167712418440"></a>padding</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p077044174411"><a name="p077044174411"></a><a name="p077044174411"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p676912411444"><a name="p676912411444"></a><a name="p676912411444"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p576810417443"><a name="p576810417443"></a><a name="p576810417443"></a>指定各输入维度填充范围。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p175411827202412"><a name="p175411827202412"></a><a name="p175411827202412"></a>规格约束：padding为离线常量，padding[i]<input_dim[i]</p>
</td>
</tr>
<tr id="row158205562211"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p163562048134411"><a name="p163562048134411"></a><a name="p163562048134411"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p03551948164416"><a name="p03551948164416"></a><a name="p03551948164416"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p173541548184411"><a name="p173541548184411"></a><a name="p173541548184411"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p123531648164412"><a name="p123531648164412"></a><a name="p123531648164412"></a>输出张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p143521048174416"><a name="p143521048174416"></a><a name="p143521048174416"></a>-</p>
</td>
</tr>
</tbody>
</table>

#### PadV2<a name="ZH-CN_TOPIC_0000002513006453" id="ZH-CN_TOPIC_0000002513006453"></a>

**功能描述<a name="section69069544112"></a>**

对输入张量边界做自定义常量填充。

**参数说明<a name="section15195134816462"></a>**

**表 1**  PadV2参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="18.04819518048195%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.788821117888212%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.108589141085892%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.077092290770924%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.977302269773023%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16660151211817"><td class="cellrowborder" valign="top" width="18.04819518048195%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.788821117888212%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.077092290770924%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.977302269773023%" headers="mcps1.2.6.1.5 "><p id="p640418163217"><a name="p640418163217"></a><a name="p640418163217"></a>规格约束：int8量化场景仅支持4D张量输入</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="18.04819518048195%" headers="mcps1.2.6.1.1 "><p id="p167712418440"><a name="p167712418440"></a><a name="p167712418440"></a>padding</p>
</td>
<td class="cellrowborder" valign="top" width="11.788821117888212%" headers="mcps1.2.6.1.2 "><p id="p077044174411"><a name="p077044174411"></a><a name="p077044174411"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p676912411444"><a name="p676912411444"></a><a name="p676912411444"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="29.077092290770924%" headers="mcps1.2.6.1.4 "><p id="p576810417443"><a name="p576810417443"></a><a name="p576810417443"></a>指定各输入维度填充范围。</p>
</td>
<td class="cellrowborder" valign="top" width="26.977302269773023%" headers="mcps1.2.6.1.5 "><p id="p175411827202412"><a name="p175411827202412"></a><a name="p175411827202412"></a>规格约束：padding为离线常量，padding[i]<input_dim[i]</p>
</td>
</tr>
<tr id="row735671642512"><td class="cellrowborder" valign="top" width="18.04819518048195%" headers="mcps1.2.6.1.1 "><p id="p8357121612258"><a name="p8357121612258"></a><a name="p8357121612258"></a>constant_values</p>
</td>
<td class="cellrowborder" valign="top" width="11.788821117888212%" headers="mcps1.2.6.1.2 "><p id="p183571016152512"><a name="p183571016152512"></a><a name="p183571016152512"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p10357616102513"><a name="p10357616102513"></a><a name="p10357616102513"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="29.077092290770924%" headers="mcps1.2.6.1.4 "><p id="p1435713167252"><a name="p1435713167252"></a><a name="p1435713167252"></a>自定义填充常数。</p>
</td>
<td class="cellrowborder" valign="top" width="26.977302269773023%" headers="mcps1.2.6.1.5 "><p id="p783313913452"><a name="p783313913452"></a><a name="p783313913452"></a>规格约束：constant_values为离线常量</p>
</td>
</tr>
<tr id="row158205562211"><td class="cellrowborder" valign="top" width="18.04819518048195%" headers="mcps1.2.6.1.1 "><p id="p163562048134411"><a name="p163562048134411"></a><a name="p163562048134411"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.788821117888212%" headers="mcps1.2.6.1.2 "><p id="p03551948164416"><a name="p03551948164416"></a><a name="p03551948164416"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p173541548184411"><a name="p173541548184411"></a><a name="p173541548184411"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.077092290770924%" headers="mcps1.2.6.1.4 "><p id="p123531648164412"><a name="p123531648164412"></a><a name="p123531648164412"></a>输出张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.977302269773023%" headers="mcps1.2.6.1.5 "><p id="p143521048174416"><a name="p143521048174416"></a><a name="p143521048174416"></a>-</p>
</td>
</tr>
</tbody>
</table>

#### Mirror\_Pad<a name="ZH-CN_TOPIC_0000002480886588" id="ZH-CN_TOPIC_0000002480886588"></a>

**功能描述<a name="section69069544112"></a>**

对输入张量边界做镜像反射填充。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Mirror\_Pad参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="18.04819518048195%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.788821117888212%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.108589141085892%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.556944305569438%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.497450254974503%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16660151211817"><td class="cellrowborder" valign="top" width="18.04819518048195%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.788821117888212%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="18.04819518048195%" headers="mcps1.2.6.1.1 "><p id="p167712418440"><a name="p167712418440"></a><a name="p167712418440"></a>pad</p>
</td>
<td class="cellrowborder" valign="top" width="11.788821117888212%" headers="mcps1.2.6.1.2 "><p id="p077044174411"><a name="p077044174411"></a><a name="p077044174411"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p676912411444"><a name="p676912411444"></a><a name="p676912411444"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p576810417443"><a name="p576810417443"></a><a name="p576810417443"></a>指定各输入维度填充范围。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p175411827202412"><a name="p175411827202412"></a><a name="p175411827202412"></a>规格约束：pad为离线常量，pad[i]<input_dim[i]</p>
</td>
</tr>
<tr id="row735671642512"><td class="cellrowborder" valign="top" width="18.04819518048195%" headers="mcps1.2.6.1.1 "><p id="p335143153114"><a name="p335143153114"></a><a name="p335143153114"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.788821117888212%" headers="mcps1.2.6.1.2 "><p id="p193051735183117"><a name="p193051735183117"></a><a name="p193051735183117"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p9217194093113"><a name="p9217194093113"></a><a name="p9217194093113"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p71956452312"><a name="p71956452312"></a><a name="p71956452312"></a>输出张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p13571616182518"><a name="p13571616182518"></a><a name="p13571616182518"></a>-</p>
</td>
</tr>
<tr id="row158205562211"><td class="cellrowborder" valign="top" width="18.04819518048195%" headers="mcps1.2.6.1.1 "><p id="p163562048134411"><a name="p163562048134411"></a><a name="p163562048134411"></a>mode</p>
</td>
<td class="cellrowborder" valign="top" width="11.788821117888212%" headers="mcps1.2.6.1.2 "><p id="p370513215312"><a name="p370513215312"></a><a name="p370513215312"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p173541548184411"><a name="p173541548184411"></a><a name="p173541548184411"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p123531648164412"><a name="p123531648164412"></a><a name="p123531648164412"></a>填充模式，指定边界填充方式。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p143521048174416"><a name="p143521048174416"></a><a name="p143521048174416"></a>配置范围：REFLECT、SYMMETRIC</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | pads必须为转换期常量 |

### Resize<a name="ZH-CN_TOPIC_0000002513105415" id="ZH-CN_TOPIC_0000002513105415"></a>

Resize算子在TFLITE框架中包含tfl.Resize\_Bilinear、tfl.Resize\_Nearest\_Neighbor等api，其中tfl.Pad表示零填充，tfl.Resize\_Bilinear表示双线性插值缩放，tfl.Resize\_Nearest\_Neighbor表示最近邻插值缩放。

-   **[Resize\_Bilinear](#ZH-CN_TOPIC_0000002481046548)**  

-   **[Resize\_Nearest\_Neighbor](#ZH-CN_TOPIC_0000002513166433)**  

#### Resize\_Bilinear<a name="ZH-CN_TOPIC_0000002481046548" id="ZH-CN_TOPIC_0000002481046548"></a>

**功能描述<a name="section69069544112"></a>**

对输入张量做双线性插值缩放。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Resize\_Bilinear参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="19.068093190680933%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="10.768923107689233%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.108589141085892%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.556944305569438%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.497450254974503%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16660151211817"><td class="cellrowborder" valign="top" width="19.068093190680933%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.768923107689233%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="19.068093190680933%" headers="mcps1.2.6.1.1 "><p id="p167712418440"><a name="p167712418440"></a><a name="p167712418440"></a>size</p>
</td>
<td class="cellrowborder" valign="top" width="10.768923107689233%" headers="mcps1.2.6.1.2 "><p id="p077044174411"><a name="p077044174411"></a><a name="p077044174411"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p676912411444"><a name="p676912411444"></a><a name="p676912411444"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p576810417443"><a name="p576810417443"></a><a name="p576810417443"></a>指定输出张量的目标尺寸。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p175411827202412"><a name="p175411827202412"></a><a name="p175411827202412"></a>规格约束：离线常量，NC维度与输入张量保持一致</p>
</td>
</tr>
<tr id="row735671642512"><td class="cellrowborder" valign="top" width="19.068093190680933%" headers="mcps1.2.6.1.1 "><p id="p335143153114"><a name="p335143153114"></a><a name="p335143153114"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="10.768923107689233%" headers="mcps1.2.6.1.2 "><p id="p193051735183117"><a name="p193051735183117"></a><a name="p193051735183117"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p9217194093113"><a name="p9217194093113"></a><a name="p9217194093113"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p71956452312"><a name="p71956452312"></a><a name="p71956452312"></a>输出张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p13571616182518"><a name="p13571616182518"></a><a name="p13571616182518"></a>-</p>
</td>
</tr>
<tr id="row158205562211"><td class="cellrowborder" valign="top" width="19.068093190680933%" headers="mcps1.2.6.1.1 "><p id="p163562048134411"><a name="p163562048134411"></a><a name="p163562048134411"></a>align_corners</p>
</td>
<td class="cellrowborder" valign="top" width="10.768923107689233%" headers="mcps1.2.6.1.2 "><p id="p370513215312"><a name="p370513215312"></a><a name="p370513215312"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p173541548184411"><a name="p173541548184411"></a><a name="p173541548184411"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p123531648164412"><a name="p123531648164412"></a><a name="p123531648164412"></a>缩放填充模式，是否对齐输入输出的角落像素。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p187252223"><a name="p187252223"></a><a name="p187252223"></a>配置范围：true、false，与half_pixel_centers必须配置一个且仅一个配置为true</p>
</td>
</tr>
<tr id="row116462211215"><td class="cellrowborder" valign="top" width="19.068093190680933%" headers="mcps1.2.6.1.1 "><p id="p86471027120"><a name="p86471027120"></a><a name="p86471027120"></a>half_pixel_centers</p>
</td>
<td class="cellrowborder" valign="top" width="10.768923107689233%" headers="mcps1.2.6.1.2 "><p id="p464752141211"><a name="p464752141211"></a><a name="p464752141211"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p1764715212123"><a name="p1764715212123"></a><a name="p1764715212123"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p117194918226"><a name="p117194918226"></a><a name="p117194918226"></a>缩放填充模式，像素坐标中心是否取(0.5, 0.5)计算。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p7360192916137"><a name="p7360192916137"></a><a name="p7360192916137"></a>配置范围：true、false</p>
</td>
</tr>
</tbody>
</table>

#### Resize\_Nearest\_Neighbor<a name="ZH-CN_TOPIC_0000002513166433" id="ZH-CN_TOPIC_0000002513166433"></a>

**功能描述<a name="section69069544112"></a>**

对输入张量做最近邻插值缩放。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Resize\_Nearest\_Neighbor参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="19.068093190680933%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="10.768923107689233%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.108589141085892%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.556944305569438%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.497450254974503%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16660151211817"><td class="cellrowborder" valign="top" width="19.068093190680933%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.768923107689233%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="19.068093190680933%" headers="mcps1.2.6.1.1 "><p id="p167712418440"><a name="p167712418440"></a><a name="p167712418440"></a>size</p>
</td>
<td class="cellrowborder" valign="top" width="10.768923107689233%" headers="mcps1.2.6.1.2 "><p id="p077044174411"><a name="p077044174411"></a><a name="p077044174411"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p676912411444"><a name="p676912411444"></a><a name="p676912411444"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p576810417443"><a name="p576810417443"></a><a name="p576810417443"></a>指定输出张量的目标尺寸。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p175411827202412"><a name="p175411827202412"></a><a name="p175411827202412"></a>规格约束：离线常量，NC维度与输入张量保持一致</p>
</td>
</tr>
<tr id="row735671642512"><td class="cellrowborder" valign="top" width="19.068093190680933%" headers="mcps1.2.6.1.1 "><p id="p335143153114"><a name="p335143153114"></a><a name="p335143153114"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="10.768923107689233%" headers="mcps1.2.6.1.2 "><p id="p193051735183117"><a name="p193051735183117"></a><a name="p193051735183117"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p9217194093113"><a name="p9217194093113"></a><a name="p9217194093113"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p71956452312"><a name="p71956452312"></a><a name="p71956452312"></a>输出张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p13571616182518"><a name="p13571616182518"></a><a name="p13571616182518"></a>-</p>
</td>
</tr>
<tr id="row158205562211"><td class="cellrowborder" valign="top" width="19.068093190680933%" headers="mcps1.2.6.1.1 "><p id="p163562048134411"><a name="p163562048134411"></a><a name="p163562048134411"></a>align_corners</p>
</td>
<td class="cellrowborder" valign="top" width="10.768923107689233%" headers="mcps1.2.6.1.2 "><p id="p370513215312"><a name="p370513215312"></a><a name="p370513215312"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p173541548184411"><a name="p173541548184411"></a><a name="p173541548184411"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p123531648164412"><a name="p123531648164412"></a><a name="p123531648164412"></a>缩放填充模式，是否对齐输入输出的角落像素。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p143521048174416"><a name="p143521048174416"></a><a name="p143521048174416"></a>配置范围：true、false，与half_pixel_centers必须配置一个且仅一个配置为true</p>
</td>
</tr>
<tr id="row116462211215"><td class="cellrowborder" valign="top" width="19.068093190680933%" headers="mcps1.2.6.1.1 "><p id="p86471027120"><a name="p86471027120"></a><a name="p86471027120"></a>half_pixel_centers</p>
</td>
<td class="cellrowborder" valign="top" width="10.768923107689233%" headers="mcps1.2.6.1.2 "><p id="p464752141211"><a name="p464752141211"></a><a name="p464752141211"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p1764715212123"><a name="p1764715212123"></a><a name="p1764715212123"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p117194918226"><a name="p117194918226"></a><a name="p117194918226"></a>缩放填充模式，像素坐标中心是否取(0.5, 0.5)计算。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p7360192916137"><a name="p7360192916137"></a><a name="p7360192916137"></a>配置范围：true、false</p>
</td>
</tr>
</tbody>
</table>

### Squeeze<a name="ZH-CN_TOPIC_0000002515130287" id="ZH-CN_TOPIC_0000002515130287"></a>

**功能描述<a name="section69069544112"></a>**

对输入张量进行shape压缩操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Squeeze参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="16.93830616938306%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.14848515148485%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.388461153884613%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.777122287771224%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.747625237476253%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1111813635119"><a name="p1111813635119"></a><a name="p1111813635119"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7349185545010"><a name="p7349185545010"></a><a name="p7349185545010"></a>-</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p187213431103"><a name="p187213431103"></a><a name="p187213431103"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1677592812"><a name="p1677592812"></a><a name="p1677592812"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p83481655175017"><a name="p83481655175017"></a><a name="p83481655175017"></a>-</p>
</td>
</tr>
<tr id="row168911912143417"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p12286124112430"><a name="p12286124112430"></a><a name="p12286124112430"></a>squeeze_dims（可选）</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p1299891713439"><a name="p1299891713439"></a><a name="p1299891713439"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p1551719012441"><a name="p1551719012441"></a><a name="p1551719012441"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p18141820435"><a name="p18141820435"></a><a name="p18141820435"></a>被压缩的轴列表。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p458116104314"><a name="p458116104314"></a><a name="p458116104314"></a>-Rank(tensor) <= axis <  Rank(tensor)</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 输入和输出元素数量必须一致 |
| FP32 | 支持 | 输入和输出元素数量必须一致 |

### ExpandDims<a name="ZH-CN_TOPIC_0000002482930280" id="ZH-CN_TOPIC_0000002482930280"></a>

**功能描述<a name="section69069544112"></a>**

对输入张量进行shape扩展操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  ExpandDims参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="16.93830616938306%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.14848515148485%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.388461153884613%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.777122287771224%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.747625237476253%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1111813635119"><a name="p1111813635119"></a><a name="p1111813635119"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7349185545010"><a name="p7349185545010"></a><a name="p7349185545010"></a>-</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p187213431103"><a name="p187213431103"></a><a name="p187213431103"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1677592812"><a name="p1677592812"></a><a name="p1677592812"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p83481655175017"><a name="p83481655175017"></a><a name="p83481655175017"></a>-</p>
</td>
</tr>
<tr id="row168911912143417"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p12286124112430"><a name="p12286124112430"></a><a name="p12286124112430"></a>dim</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p1299891713439"><a name="p1299891713439"></a><a name="p1299891713439"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p15768184753415"><a name="p15768184753415"></a><a name="p15768184753415"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p18141820435"><a name="p18141820435"></a><a name="p18141820435"></a>被扩展的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p458116104314"><a name="p458116104314"></a><a name="p458116104314"></a>-Rank(output) <= axis <  Rank(output)</p>
</td>
</tr>
</tbody>
</table>

### Abs<a name="ZH-CN_TOPIC_0000002485399132" id="ZH-CN_TOPIC_0000002485399132"></a>

**功能描述<a name="section270785104414"></a>**

对张量的每个元素做绝对值运算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Abs参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 要求使用FP32静态非空张量 |

### Ceil<a name="ZH-CN_TOPIC_0000002517479769" id="ZH-CN_TOPIC_0000002517479769"></a>

**功能描述<a name="section270785104414"></a>**

对张量中的每个元素做向上取整操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Ceil参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Cos<a name="ZH-CN_TOPIC_0000002485399848" id="ZH-CN_TOPIC_0000002485399848"></a>

**功能描述<a name="section270785104414"></a>**

对张量中的每个元素做余弦操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Cos参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p316239246"><a name="p316239246"></a><a name="p316239246"></a>[-1, 1]</p>
</td>
</tr>
</tbody>
</table>

### Exp<a name="ZH-CN_TOPIC_0000002485239884" id="ZH-CN_TOPIC_0000002485239884"></a>

**功能描述<a name="section270785104414"></a>**

对张量中的每个元素做指数计算操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Exp参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p789767519"><a name="p789767519"></a><a name="p789767519"></a>(0, 正无穷)</p>
</td>
</tr>
</tbody>
</table>

### Floor<a name="ZH-CN_TOPIC_0000002517399793" id="ZH-CN_TOPIC_0000002517399793"></a>

**功能描述<a name="section270785104414"></a>**

对张量中的每个元素做向下取整操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Floor参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Log<a name="ZH-CN_TOPIC_0000002517479771" id="ZH-CN_TOPIC_0000002517479771"></a>

**功能描述<a name="section270785104414"></a>**

对张量中的每个元素做对数计算操作（底数值为e）。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Log参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p185739401441"><a name="p185739401441"></a><a name="p185739401441"></a>(0, 正无穷)</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Round<a name="ZH-CN_TOPIC_0000002485399850" id="ZH-CN_TOPIC_0000002485399850"></a>

**功能描述<a name="section270785104414"></a>**

对张量中的每个元素做四舍五入操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Round参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p1368319278418"><a name="p1368319278418"></a><a name="p1368319278418"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Rsqrt<a name="ZH-CN_TOPIC_0000002485239886" id="ZH-CN_TOPIC_0000002485239886"></a>

**功能描述<a name="section270785104414"></a>**

对张量中的每个元素做平方根倒数计算操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Rsqrt参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>(0, 正无穷)</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>(0, 正无穷)</p>
</td>
</tr>
</tbody>
</table>

### Sin<a name="ZH-CN_TOPIC_0000002517399795" id="ZH-CN_TOPIC_0000002517399795"></a>

**功能描述<a name="section270785104414"></a>**

对张量中的每个元素做正弦计算操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Sin参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>[-1, 1]</p>
</td>
</tr>
</tbody>
</table>

### Sqrt<a name="ZH-CN_TOPIC_0000002517479773" id="ZH-CN_TOPIC_0000002517479773"></a>

**功能描述<a name="section270785104414"></a>**

对张量中的每个元素做平方根计算操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Sqrt参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>[0, 正无穷)</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>[0, 正无穷)</p>
</td>
</tr>
</tbody>
</table>

### Square<a name="ZH-CN_TOPIC_0000002485399852" id="ZH-CN_TOPIC_0000002485399852"></a>

**功能描述<a name="section270785104414"></a>**

对张量中的每个元素做平方计算操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Square参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### L2Normalization<a name="ZH-CN_TOPIC_0000002487557124" id="ZH-CN_TOPIC_0000002487557124"></a>

**功能描述<a name="section270785104414"></a>**

沿指定轴，用L2范数对输入张量执行归一化计算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  L2Normalization参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="17.078292170782923%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.348665133486653%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.928807119288072%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.00679932006799%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.637436256374365%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row2423132175015"><td class="cellrowborder" valign="top" width="17.078292170782923%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.348665133486653%" headers="mcps1.2.6.1.2 "><p id="p189321956152"><a name="p189321956152"></a><a name="p189321956152"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.928807119288072%" headers="mcps1.2.6.1.3 "><p id="p38331952113217"><a name="p38331952113217"></a><a name="p38331952113217"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.00679932006799%" headers="mcps1.2.6.1.4 "><p id="p19305746101210"><a name="p19305746101210"></a><a name="p19305746101210"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.637436256374365%" headers="mcps1.2.6.1.5 "><p id="p66671634141811"><a name="p66671634141811"></a><a name="p66671634141811"></a>-</p>
</td>
</tr>
<tr id="row334168176"><td class="cellrowborder" valign="top" width="17.078292170782923%" headers="mcps1.2.6.1.1 "><p id="p6341189713"><a name="p6341189713"></a><a name="p6341189713"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.348665133486653%" headers="mcps1.2.6.1.2 "><p id="p6341289719"><a name="p6341289719"></a><a name="p6341289719"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.928807119288072%" headers="mcps1.2.6.1.3 "><p id="p6181781394"><a name="p6181781394"></a><a name="p6181781394"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.00679932006799%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.637436256374365%" headers="mcps1.2.6.1.5 "><p id="p55991825111919"><a name="p55991825111919"></a><a name="p55991825111919"></a>-</p>
</td>
</tr>
<tr id="row195632034203"><td class="cellrowborder" valign="top" width="17.078292170782923%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="13.348665133486653%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.928807119288072%" headers="mcps1.2.6.1.3 "><p id="p6218353165419"><a name="p6218353165419"></a><a name="p6218353165419"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="32.00679932006799%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="25.637436256374365%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>配置范围：NONE、RELU、RELU6</p>
</td>
</tr>
</tbody>
</table>

### Slice<a name="ZH-CN_TOPIC_0000002528693597" id="ZH-CN_TOPIC_0000002528693597"></a>

Slice算子在TFLITE框架中包含tfl.slice、tfl.strided\_slice等api，其中tfl.slice为连续提取子张量，tfl.strided\_slice可以通过指定步长、掩码等方式更灵活地进行提取。

-   **[Slice](#ZH-CN_TOPIC_0000002528458741)**  

-   **[StridedSlice](#ZH-CN_TOPIC_0000002496933624)**  

#### Slice<a name="ZH-CN_TOPIC_0000002528458741" id="ZH-CN_TOPIC_0000002528458741"></a>

**功能描述<a name="section270785104414"></a>**

从输入张量中沿指定轴连续提取子张量。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Slice参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="14.06%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.62%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.940000000000001%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="35.67%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.71%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row1039757204714"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p163973710472"><a name="p163973710472"></a><a name="p163973710472"></a>begins</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p939877194717"><a name="p939877194717"></a><a name="p939877194717"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p173987784715"><a name="p173987784715"></a><a name="p173987784715"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p16309115118523"><a name="p16309115118523"></a><a name="p16309115118523"></a>维度为1D，<span>对应</span><span>各维度的起始索引</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p17661841144412"><a name="p17661841144412"></a><a name="p17661841144412"></a>规格约束：begins为离线常量</p>
</td>
</tr>
<tr id="row19512413114716"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p6512181384714"><a name="p6512181384714"></a><a name="p6512181384714"></a>size</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p1051241310472"><a name="p1051241310472"></a><a name="p1051241310472"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p25121813154717"><a name="p25121813154717"></a><a name="p25121813154717"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p5806154818521"><a name="p5806154818521"></a><a name="p5806154818521"></a>维度为1D，<span>各维度要提取的元素个数</span>。size[i]=-1时表示取i轴上从begins[i]开始的所有元素。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p1416923545"><a name="p1416923545"></a><a name="p1416923545"></a>规格约束：size为离线常量</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>-</p>
</td>
</tr>
</tbody>
</table>

#### StridedSlice<a name="ZH-CN_TOPIC_0000002496933624" id="ZH-CN_TOPIC_0000002496933624"></a>

**功能描述<a name="section270785104414"></a>**

从输入张量中沿指定轴提取子张量。

**参数说明<a name="section15195134816462"></a>**

**表 1**  StridedSlice参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="14.06%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.149999999999999%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.899999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="37.92%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="21.97%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度为2D/3D/4D，格式为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row1039757204714"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p163973710472"><a name="p163973710472"></a><a name="p163973710472"></a>begin</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p939877194717"><a name="p939877194717"></a><a name="p939877194717"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p173987784715"><a name="p173987784715"></a><a name="p173987784715"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p16309115118523"><a name="p16309115118523"></a><a name="p16309115118523"></a>维度为1D，<span>对应</span><span>各维度的起始索引</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p17661841144412"><a name="p17661841144412"></a><a name="p17661841144412"></a>规格约束：begin为离线常量</p>
</td>
</tr>
<tr id="row19512413114716"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p6512181384714"><a name="p6512181384714"></a><a name="p6512181384714"></a>end</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p1051241310472"><a name="p1051241310472"></a><a name="p1051241310472"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p25121813154717"><a name="p25121813154717"></a><a name="p25121813154717"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p5806154818521"><a name="p5806154818521"></a><a name="p5806154818521"></a>维度为1D，<span>对应</span><span>各维度的结束索引</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p1416923545"><a name="p1416923545"></a><a name="p1416923545"></a>规格约束：end为离线常量</p>
</td>
</tr>
<tr id="row562612196478"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p362651919474"><a name="p362651919474"></a><a name="p362651919474"></a>strides</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p2626191916478"><a name="p2626191916478"></a><a name="p2626191916478"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p126261119164714"><a name="p126261119164714"></a><a name="p126261119164714"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p9161847115212"><a name="p9161847115212"></a><a name="p9161847115212"></a>维度为1D，<span>对应</span><span>各维度的切片步长</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p165961325541"><a name="p165961325541"></a><a name="p165961325541"></a>规格约束：strides为离线常量</p>
</td>
</tr>
<tr id="row19755174721016"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p15755144717105"><a name="p15755144717105"></a><a name="p15755144717105"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p107551247171011"><a name="p107551247171011"></a><a name="p107551247171011"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p875514741016"><a name="p875514741016"></a><a name="p875514741016"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p19755347161010"><a name="p19755347161010"></a><a name="p19755347161010"></a>输出张量<span>，输出维度和尺寸由切片逻辑及掩码决定</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p207554473102"><a name="p207554473102"></a><a name="p207554473102"></a>-</p>
</td>
</tr>
<tr id="row57411716194713"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p1174116165478"><a name="p1174116165478"></a><a name="p1174116165478"></a>begin_mask</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p9741316184714"><a name="p9741316184714"></a><a name="p9741316184714"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p574141616470"><a name="p574141616470"></a><a name="p574141616470"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p17410164475"><a name="p17410164475"></a><a name="p17410164475"></a><span>第 i 维度对应位为 1 时，忽略该维度的 </span>begin[i]<span>，改用维度</span><span>起始边界</span><span>（正向切片 = 0，反向</span><span>切片</span><span> = 维度长度 - 1）</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p152310335413"><a name="p152310335413"></a><a name="p152310335413"></a>-</p>
</td>
</tr>
<tr id="row1266510302532"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p14666430115315"><a name="p14666430115315"></a><a name="p14666430115315"></a>end_mask</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p12208101913545"><a name="p12208101913545"></a><a name="p12208101913545"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p86661330185315"><a name="p86661330185315"></a><a name="p86661330185315"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p56661230155312"><a name="p56661230155312"></a><a name="p56661230155312"></a><span>第 i 维</span><span>度对应位为 1 时，忽略该维度的 </span>end[i]<span>，改用维度</span><span>结束边界</span><span>（正向 = 维度长度，反向切片 =-1）</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p1266614304531"><a name="p1266614304531"></a><a name="p1266614304531"></a>-</p>
</td>
</tr>
<tr id="row162892372535"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p102896371531"><a name="p102896371531"></a><a name="p102896371531"></a>ellipsis_mask</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p172491919542"><a name="p172491919542"></a><a name="p172491919542"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p1728993710533"><a name="p1728993710533"></a><a name="p1728993710533"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p328963725310"><a name="p328963725310"></a><a name="p328963725310"></a><span>第 i 维</span><span>度对应位为 1 时，</span><span>对应维度及后续未显式指定的维度完整保留</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p82901237155315"><a name="p82901237155315"></a><a name="p82901237155315"></a>规格约束：仅允许一个二进制位为1</p>
</td>
</tr>
<tr id="row8101540165316"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p21044011539"><a name="p21044011539"></a><a name="p21044011539"></a>new_axis_mask</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p5122920105413"><a name="p5122920105413"></a><a name="p5122920105413"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p111094012534"><a name="p111094012534"></a><a name="p111094012534"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p17101440155314"><a name="p17101440155314"></a><a name="p17101440155314"></a><span>第 i 维</span><span>度</span><span>对应位为 1 时，在输出中插入长度为 1 的新维度</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p10106408532"><a name="p10106408532"></a><a name="p10106408532"></a>-</p>
</td>
</tr>
<tr id="row1075211508536"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p1075215508531"><a name="p1075215508531"></a><a name="p1075215508531"></a>shrink_axis_mask</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p20520122014547"><a name="p20520122014547"></a><a name="p20520122014547"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p375375075317"><a name="p375375075317"></a><a name="p375375075317"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p1475315065311"><a name="p1475315065311"></a><a name="p1475315065311"></a><span>第 i 维</span><span>度</span><span>对应位为 1 时，</span><span>在输出中</span><span>移除该维度</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p975310506533"><a name="p975310506533"></a><a name="p975310506533"></a>-</p>
</td>
</tr>
<tr id="row6354174314538"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p135414439535"><a name="p135414439535"></a><a name="p135414439535"></a>offset</p>
</td>
<td class="cellrowborder" valign="top" width="14.149999999999999%" headers="mcps1.2.6.1.2 "><p id="p1394312065416"><a name="p1394312065416"></a><a name="p1394312065416"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.899999999999999%" headers="mcps1.2.6.1.3 "><p id="p19354243165310"><a name="p19354243165310"></a><a name="p19354243165310"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="37.92%" headers="mcps1.2.6.1.4 "><p id="p0354134312538"><a name="p0354134312538"></a><a name="p0354134312538"></a>取值为true：end输入表示切片长度。</p>
<p id="p621712598013"><a name="p621712598013"></a><a name="p621712598013"></a>取值为false：直接使用原始索引。</p>
</td>
<td class="cellrowborder" valign="top" width="21.97%" headers="mcps1.2.6.1.5 "><p id="p1535416434534"><a name="p1535416434534"></a><a name="p1535416434534"></a>暂不支持配置，默认为false</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | begin、end和stride等结构输入必须为转换期常量 |

### DepthwiseConv2D<a name="ZH-CN_TOPIC_0000002529736261" id="ZH-CN_TOPIC_0000002529736261"></a>

**功能描述<a name="section270785104414"></a>**

对4D输入进行深度可分离卷积计算。

**参数说明<a name="section1970335944611"></a>**

**表 1**  DepthwiseConv2D参数概览

<a name="table668985955612"></a>
<table><thead align="left"><tr id="row13690359165613"><th class="cellrowborder" valign="top" width="18.05%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="10.92%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.25%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.94%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.840000000000003%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row0259114117411"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row105725371417"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p257316371747"><a name="p257316371747"></a><a name="p257316371747"></a>filter</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p1357393714410"><a name="p1357393714410"></a><a name="p1357393714410"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p145732037648"><a name="p145732037648"></a><a name="p145732037648"></a>filter张量，维度为4D。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p35731237948"><a name="p35731237948"></a><a name="p35731237948"></a>规格约束：权重为离线常量</p>
</td>
</tr>
<tr id="row04821554841"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p74821654243"><a name="p74821654243"></a><a name="p74821654243"></a>bias</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p11482185414420"><a name="p11482185414420"></a><a name="p11482185414420"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p194829542412"><a name="p194829542412"></a><a name="p194829542412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p17482125418417"><a name="p17482125418417"></a><a name="p17482125418417"></a>bias张量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p048220543413"><a name="p048220543413"></a><a name="p048220543413"></a>规格约束：偏置为离线常量</p>
</td>
</tr>
<tr id="row44831201652"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p194831017511"><a name="p194831017511"></a><a name="p194831017511"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p048340450"><a name="p048340450"></a><a name="p048340450"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p124839018518"><a name="p124839018518"></a><a name="p124839018518"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p13483801352"><a name="p13483801352"></a><a name="p13483801352"></a>输出张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p748310020510"><a name="p748310020510"></a><a name="p748310020510"></a>-</p>
</td>
</tr>
<tr id="row26911159125618"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p1269165919569"><a name="p1269165919569"></a><a name="p1269165919569"></a>dilation_h_factor</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p2509588318"><a name="p2509588318"></a><a name="p2509588318"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p469110599562"><a name="p469110599562"></a><a name="p469110599562"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p126911459165613"><a name="p126911459165613"></a><a name="p126911459165613"></a>filter在H方向上的扩张系数。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p1447651443920"><a name="p1447651443920"></a><a name="p1447651443920"></a>-</p>
</td>
</tr>
<tr id="row669175913568"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p1169119595569"><a name="p1169119595569"></a><a name="p1169119595569"></a>dilation_w_factor</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p65015581736"><a name="p65015581736"></a><a name="p65015581736"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p769119597568"><a name="p769119597568"></a><a name="p769119597568"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p12281134810395"><a name="p12281134810395"></a><a name="p12281134810395"></a>filter在W方向上的扩张系数。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p185499219400"><a name="p185499219400"></a><a name="p185499219400"></a>-</p>
</td>
</tr>
<tr id="row1469255925614"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p3692859195613"><a name="p3692859195613"></a><a name="p3692859195613"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p15692145965619"><a name="p15692145965619"></a><a name="p15692145965619"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p833042514011"><a name="p833042514011"></a><a name="p833042514011"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p7692759195616"><a name="p7692759195616"></a><a name="p7692759195616"></a>配置范围：NONE、RELU</p>
</td>
</tr>
<tr id="row869245925620"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p96921059125614"><a name="p96921059125614"></a><a name="p96921059125614"></a>padding</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p1150158930"><a name="p1150158930"></a><a name="p1150158930"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p76921259115619"><a name="p76921259115619"></a><a name="p76921259115619"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p10118203645110"><a name="p10118203645110"></a><a name="p10118203645110"></a>填充类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p1769285995619"><a name="p1769285995619"></a><a name="p1769285995619"></a>配置范围：SAME、VALID</p>
</td>
</tr>
<tr id="row369235919566"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p106921159195616"><a name="p106921159195616"></a><a name="p106921159195616"></a>stride_h</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p15015581132"><a name="p15015581132"></a><a name="p15015581132"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p56921593564"><a name="p56921593564"></a><a name="p56921593564"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p136921359195618"><a name="p136921359195618"></a><a name="p136921359195618"></a>filter在H方向上的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p523152894518"><a name="p523152894518"></a><a name="p523152894518"></a>-</p>
</td>
</tr>
<tr id="row1198393324510"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p1898353317457"><a name="p1898353317457"></a><a name="p1898353317457"></a>stride_w</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p16508581531"><a name="p16508581531"></a><a name="p16508581531"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p499819412458"><a name="p499819412458"></a><a name="p499819412458"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p1399834134511"><a name="p1399834134511"></a><a name="p1399834134511"></a>filter在W方向上的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p1798314337454"><a name="p1798314337454"></a><a name="p1798314337454"></a>-</p>
</td>
</tr>
<tr id="row173436158535"><td class="cellrowborder" valign="top" width="18.05%" headers="mcps1.2.6.1.1 "><p id="p1934371516538"><a name="p1934371516538"></a><a name="p1934371516538"></a>depth_multiplier</p>
</td>
<td class="cellrowborder" valign="top" width="10.92%" headers="mcps1.2.6.1.2 "><p id="p1334391514533"><a name="p1334391514533"></a><a name="p1334391514533"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.25%" headers="mcps1.2.6.1.3 "><p id="p33431153533"><a name="p33431153533"></a><a name="p33431153533"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.94%" headers="mcps1.2.6.1.4 "><p id="p2343141545315"><a name="p2343141545315"></a><a name="p2343141545315"></a>深度乘法因子，控制通道数缩放。</p>
</td>
<td class="cellrowborder" valign="top" width="26.840000000000003%" headers="mcps1.2.6.1.5 "><p id="p1934391510536"><a name="p1934391510536"></a><a name="p1934391510536"></a>规格约束：INT8量化场景仅支持配置为1</p>
</td>
</tr>
</tbody>
</table>

### Transpose<a name="ZH-CN_TOPIC_0000002498475622" id="ZH-CN_TOPIC_0000002498475622"></a>

**功能描述<a name="section270785104414"></a>**

对输入张量进行转置。

**参数说明<a name="section1970335944611"></a>**

**表 1**  Transpose参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="14.06%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.610000000000001%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="35.67%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.71%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.610000000000001%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.95%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row1039757204714"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p163973710472"><a name="p163973710472"></a><a name="p163973710472"></a>perm</p>
</td>
<td class="cellrowborder" valign="top" width="14.610000000000001%" headers="mcps1.2.6.1.2 "><p id="p939877194717"><a name="p939877194717"></a><a name="p939877194717"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.95%" headers="mcps1.2.6.1.3 "><p id="p173987784715"><a name="p173987784715"></a><a name="p173987784715"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p499234194217"><a name="p499234194217"></a><a name="p499234194217"></a>输入张量的维度重排顺序。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p17661841144412"><a name="p17661841144412"></a><a name="p17661841144412"></a>规格约束：不支持perm=[0,3,1,2]、[0,2,3,1]的Transpose单算子转换</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.610000000000001%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.95%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | perm必须是合法的常量全排列 |
| FP32 | 支持 | perm必须是合法的常量全排列 |

### ArgMax<a name="ZH-CN_TOPIC_0000002509946184" id="ZH-CN_TOPIC_0000002509946184"></a>

**功能描述<a name="section270785104414"></a>**

在张量的指定维度上，计算并返回最大值对应的位置索引。

**参数说明<a name="section1970335944611"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>仅支持float类型，不支持int8类型。

**表 1**  ArgMax参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="14.06%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.62%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.940000000000001%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.05%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="27.33%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.05%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="27.33%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row1039757204714"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p163973710472"><a name="p163973710472"></a><a name="p163973710472"></a>dim</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p939877194717"><a name="p939877194717"></a><a name="p939877194717"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p173987784715"><a name="p173987784715"></a><a name="p173987784715"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.05%" headers="mcps1.2.6.1.4 "><p id="p499234194217"><a name="p499234194217"></a><a name="p499234194217"></a><span>指定在张量中执行计算逻辑</span>的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="27.33%" headers="mcps1.2.6.1.5 "><p id="p17661841144412"><a name="p17661841144412"></a><a name="p17661841144412"></a>规格约束：-rank(input)<=axis<rank(input)，rank为张量的秩</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="32.05%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为1D/2D/3D，格式为N/ND/NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="27.33%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>-</p>
</td>
</tr>
<tr id="row3838183521112"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p58391835121118"><a name="p58391835121118"></a><a name="p58391835121118"></a>output_type</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p10839435141118"><a name="p10839435141118"></a><a name="p10839435141118"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p68391335181117"><a name="p68391335181117"></a><a name="p68391335181117"></a>TensorType</p>
</td>
<td class="cellrowborder" valign="top" width="32.05%" headers="mcps1.2.6.1.4 "><p id="p6839183591113"><a name="p6839183591113"></a><a name="p6839183591113"></a><span>指定算子输出张量的元素数据类型。</span></p>
</td>
<td class="cellrowborder" valign="top" width="27.33%" headers="mcps1.2.6.1.5 "><p id="p1083963571117"><a name="p1083963571117"></a><a name="p1083963571117"></a>规格约束：仅支持配置为tf.int32</p>
</td>
</tr>
</tbody>
</table>

### ArgMin<a name="ZH-CN_TOPIC_0000002541666173" id="ZH-CN_TOPIC_0000002541666173"></a>

**功能描述<a name="section270785104414"></a>**

在张量的指定维度上，计算并返回最小值对应的位置索引。

**参数说明<a name="section1970335944611"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>仅支持float类型，不支持int8类型。

**表 1**  ArgMin参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="14.06%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.62%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.940000000000001%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.43%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.950000000000003%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.43%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.950000000000003%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row1039757204714"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p163973710472"><a name="p163973710472"></a><a name="p163973710472"></a>dim</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p939877194717"><a name="p939877194717"></a><a name="p939877194717"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p173987784715"><a name="p173987784715"></a><a name="p173987784715"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.43%" headers="mcps1.2.6.1.4 "><p id="p499234194217"><a name="p499234194217"></a><a name="p499234194217"></a><span>指定在张量中执行计算逻辑</span>的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="26.950000000000003%" headers="mcps1.2.6.1.5 "><p id="p17661841144412"><a name="p17661841144412"></a><a name="p17661841144412"></a>规格约束：-rank(input)<=axis<rank(input)，rank为张量的秩</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="32.43%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为1D/2D/3D，格式为N/ND/NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="26.950000000000003%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>-</p>
</td>
</tr>
<tr id="row75869407156"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p0586040141515"><a name="p0586040141515"></a><a name="p0586040141515"></a>output_type</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p15861740171510"><a name="p15861740171510"></a><a name="p15861740171510"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p5586640171519"><a name="p5586640171519"></a><a name="p5586640171519"></a>TensorType</p>
</td>
<td class="cellrowborder" valign="top" width="32.43%" headers="mcps1.2.6.1.4 "><p id="p15861540171510"><a name="p15861540171510"></a><a name="p15861540171510"></a><span>指定算子输出张量的元素数据类型。</span></p>
</td>
<td class="cellrowborder" valign="top" width="26.950000000000003%" headers="mcps1.2.6.1.5 "><p id="p3586640141514"><a name="p3586640141514"></a><a name="p3586640141514"></a>规格约束：仅支持配置为tf.int32</p>
</td>
</tr>
</tbody>
</table>

### Div<a name="ZH-CN_TOPIC_0000002516421386" id="ZH-CN_TOPIC_0000002516421386"></a>

**功能描述<a name="section270785104414"></a>**

对两输入张量进行除法运算。

**参数说明<a name="section1970335944611"></a>**

**表 1**  Div参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
<tr id="row33451752161111"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>fused_activation_function</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p6218353165419"><a name="p6218353165419"></a><a name="p6218353165419"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>融合的激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>配置范围：NONE、RELU</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 支持范围取决于输入角色和广播规格 |

### ReduceMax<a name="ZH-CN_TOPIC_0000002526421590" id="ZH-CN_TOPIC_0000002526421590"></a>

**功能描述<a name="section270785104414"></a>**

对指定维度的张量进行最大值归约计算。

**参数说明<a name="section1970335944611"></a>**

**表 1**  ReduceMax参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，不支持axis为空list</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
<tr id="row33451752161111"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>keep_dims</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p6218353165419"><a name="p6218353165419"></a><a name="p6218353165419"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>是否需要保留归约轴的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>配置范围：true/false</p>
</td>
</tr>
</tbody>
</table>

### ReduceMin<a name="ZH-CN_TOPIC_0000002526437776" id="ZH-CN_TOPIC_0000002526437776"></a>

**功能描述<a name="section270785104414"></a>**

对指定维度的张量进行最小值归约计算。

**参数说明<a name="section1970335944611"></a>**

**表 1**  ReduceMin参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，不支持axis为空list</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
<tr id="row33451752161111"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>keep_dims</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p162622912107"><a name="p162622912107"></a><a name="p162622912107"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>是否需要保留归约轴的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>配置范围：true/false</p>
</td>
</tr>
</tbody>
</table>

### Sum<a name="ZH-CN_TOPIC_0000002557400507" id="ZH-CN_TOPIC_0000002557400507"></a>

**功能描述<a name="section270785104414"></a>**

对指定维度的张量进行求和归约计算。

**参数说明<a name="section1970335944611"></a>**

**表 1**  Sum参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，不支持axis为空list</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
<tr id="row33451752161111"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>keep_dims</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p458301411104"><a name="p458301411104"></a><a name="p458301411104"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>是否需要保留归约轴的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>配置范围：true/false</p>
</td>
</tr>
</tbody>
</table>

### Mean<a name="ZH-CN_TOPIC_0000002557400907" id="ZH-CN_TOPIC_0000002557400907"></a>

**功能描述<a name="section270785104414"></a>**

对指定维度的张量进行均值归约计算。

**参数说明<a name="section1970335944611"></a>**

**表 1**  Mean参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，不支持axis为空list</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
<tr id="row33451752161111"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>keep_dims</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p1066012121018"><a name="p1066012121018"></a><a name="p1066012121018"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>是否需要保留归约轴的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>配置范围：true/false</p>
</td>
</tr>
</tbody>
</table>

### Cast<a name="ZH-CN_TOPIC_0000002557544885" id="ZH-CN_TOPIC_0000002557544885"></a>

**功能描述<a name="section270785104414"></a>**

对输入张量进行数据类型的转换。

**参数说明<a name="section1970335944611"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Cast算子不支持量化。

**表 1**  Cast参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>数据类型仅支持float32、uint8、int8、int32</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>数据类型仅支持float32、uint8、int8、int32</p>
</td>
</tr>
</tbody>
</table>

### Quantize<a name="ZH-CN_TOPIC_0000002557589767" id="ZH-CN_TOPIC_0000002557589767"></a>

**功能描述<a name="section270785104414"></a>**

对输入张量进行量化操作。

**参数说明<a name="section1970335944611"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Quantize算子不支持量化。

**表 1**  Quantize参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>int8, uint8</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>float32, int8, uint8</p>
</td>
</tr>
</tbody>
</table>

### Dequantize<a name="ZH-CN_TOPIC_0000002526509914" id="ZH-CN_TOPIC_0000002526509914"></a>

**功能描述<a name="section270785104414"></a>**

对输入张量进行反量化操作。

**参数说明<a name="section1970335944611"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Dequantize算子不支持量化。

**表 1**  Dequantize参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>float32, int8, uint8</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>int8, uint8</p>
</td>
</tr>
</tbody>
</table>

### PRelu<a name="ZH-CN_TOPIC_0000002599172631" id="ZH-CN_TOPIC_0000002599172631"></a>

**功能描述<a name="section167661757173918"></a>**

对输入张量进行参数化 ReLU 激活处理。其在输入为非负值时保持原值，在输入为负值时根据斜率参数进行线性缩放。

**参数说明<a name="section63411171435"></a>**

**表 1**  PRelu参数概览

<a name="table95484381742"></a>
<table><thead align="left"><tr id="row55487385415"><th class="cellrowborder" valign="top" width="7.68%" id="mcps1.2.6.1.1"><p id="p4548123817416"><a name="p4548123817416"></a><a name="p4548123817416"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.86%" id="mcps1.2.6.1.2"><p id="p1054819381546"><a name="p1054819381546"></a><a name="p1054819381546"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="8.959999999999999%" id="mcps1.2.6.1.3"><p id="p354873813414"><a name="p354873813414"></a><a name="p354873813414"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="27.93%" id="mcps1.2.6.1.4"><p id="p154810381346"><a name="p154810381346"></a><a name="p154810381346"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="42.57%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row75486381541"><td class="cellrowborder" valign="top" width="7.68%" headers="mcps1.2.6.1.1 "><p id="p125485388410"><a name="p125485388410"></a><a name="p125485388410"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.86%" headers="mcps1.2.6.1.2 "><p id="p1454810381748"><a name="p1454810381748"></a><a name="p1454810381748"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="8.959999999999999%" headers="mcps1.2.6.1.3 "><p id="p195481038743"><a name="p195481038743"></a><a name="p195481038743"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.93%" headers="mcps1.2.6.1.4 "><p id="p854912385419"><a name="p854912385419"></a><a name="p854912385419"></a>待进行PReLU激活处理的数据，维度为1D / 2D / 3D / 4D。</p>
</td>
<td class="cellrowborder" valign="top" width="42.57%" headers="mcps1.2.6.1.5 "><p id="p45491138649"><a name="p45491138649"></a><a name="p45491138649"></a>数据类型仅支持 float32、int8；不限定具体数据格式。</p>
</td>
</tr>
<tr id="row35491338744"><td class="cellrowborder" valign="top" width="7.68%" headers="mcps1.2.6.1.1 "><p id="p1054915383410"><a name="p1054915383410"></a><a name="p1054915383410"></a>alpha</p>
</td>
<td class="cellrowborder" valign="top" width="12.86%" headers="mcps1.2.6.1.2 "><p id="p154920381346"><a name="p154920381346"></a><a name="p154920381346"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="8.959999999999999%" headers="mcps1.2.6.1.3 "><p id="p14549738646"><a name="p14549738646"></a><a name="p14549738646"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.93%" headers="mcps1.2.6.1.4 "><p id="p16576113045316"><a name="p16576113045316"></a><a name="p16576113045316"></a>负半轴斜率参数，维度为0D / 1D / 2D / 3D / 4D。</p>
</td>
<td class="cellrowborder" valign="top" width="42.57%" headers="mcps1.2.6.1.5 "><p id="p854916389413"><a name="p854916389413"></a><a name="p854916389413"></a>数据类型仅支持 float32；不限定具体数据格式，但其形状需支持单向广播到 input 。</p>
</td>
</tr>
<tr id="row12549113810416"><td class="cellrowborder" valign="top" width="7.68%" headers="mcps1.2.6.1.1 "><p id="p15491838743"><a name="p15491838743"></a><a name="p15491838743"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.86%" headers="mcps1.2.6.1.2 "><p id="p1254913817417"><a name="p1254913817417"></a><a name="p1254913817417"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="8.959999999999999%" headers="mcps1.2.6.1.3 "><p id="p13549738642"><a name="p13549738642"></a><a name="p13549738642"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.93%" headers="mcps1.2.6.1.4 "><p id="p1054913810418"><a name="p1054913810418"></a><a name="p1054913810418"></a>输出张量，维度与 input 一致。</p>
</td>
<td class="cellrowborder" valign="top" width="42.57%" headers="mcps1.2.6.1.5 "><p id="p185490381646"><a name="p185490381646"></a><a name="p185490381646"></a>数据类型仅支持 float32、int8；维度与 input 一致。</p>
</td>
</tr>
</tbody>
</table>

>![](public_sys-resources/icon-note.gif) **说明：** 
>在量化过程中，PReLU算子的第二输入保留FP32格式，以保证负半轴计算精度。

### CumSum<a name="ZH-CN_TOPIC_0000002599292569" id="ZH-CN_TOPIC_0000002599292569"></a>

**功能描述<a name="section167661757173918"></a>**

对输入张量沿指定维度进行累加求和处理，输出结果为该维度上的前缀和。

**参数说明<a name="section63411171435"></a>**

**表 1**  CumSum参数概览

<a name="table95484381742"></a>
<table><thead align="left"><tr id="row55487385415"><th class="cellrowborder" valign="top" width="10.299999999999999%" id="mcps1.2.6.1.1"><p id="p4548123817416"><a name="p4548123817416"></a><a name="p4548123817416"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.709999999999999%" id="mcps1.2.6.1.2"><p id="p1054819381546"><a name="p1054819381546"></a><a name="p1054819381546"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="8.32%" id="mcps1.2.6.1.3"><p id="p354873813414"><a name="p354873813414"></a><a name="p354873813414"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="27.689999999999998%" id="mcps1.2.6.1.4"><p id="p154810381346"><a name="p154810381346"></a><a name="p154810381346"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="40.98%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row75486381541"><td class="cellrowborder" valign="top" width="10.299999999999999%" headers="mcps1.2.6.1.1 "><p id="p125485388410"><a name="p125485388410"></a><a name="p125485388410"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.709999999999999%" headers="mcps1.2.6.1.2 "><p id="p1454810381748"><a name="p1454810381748"></a><a name="p1454810381748"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="8.32%" headers="mcps1.2.6.1.3 "><p id="p195481038743"><a name="p195481038743"></a><a name="p195481038743"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.689999999999998%" headers="mcps1.2.6.1.4 "><p id="p854912385419"><a name="p854912385419"></a><a name="p854912385419"></a>待进行累加求和处理的输入张量，维度为 1D / 2D / 3D / 4D。</p>
</td>
<td class="cellrowborder" valign="top" width="40.98%" headers="mcps1.2.6.1.5 "><p id="p45491138649"><a name="p45491138649"></a><a name="p45491138649"></a>数据类型仅支持 float32、int8；不限定具体数据格式。</p>
</td>
</tr>
<tr id="row35491338744"><td class="cellrowborder" valign="top" width="10.299999999999999%" headers="mcps1.2.6.1.1 "><p id="p1054915383410"><a name="p1054915383410"></a><a name="p1054915383410"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="12.709999999999999%" headers="mcps1.2.6.1.2 "><p id="p154920381346"><a name="p154920381346"></a><a name="p154920381346"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="8.32%" headers="mcps1.2.6.1.3 "><p id="p14549738646"><a name="p14549738646"></a><a name="p14549738646"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.689999999999998%" headers="mcps1.2.6.1.4 "><p id="p16576113045316"><a name="p16576113045316"></a><a name="p16576113045316"></a>进行累加求和的维度，维度为 0D。</p>
</td>
<td class="cellrowborder" valign="top" width="40.98%" headers="mcps1.2.6.1.5 "><p id="p854916389413"><a name="p854916389413"></a><a name="p854916389413"></a>数据类型仅支持 int32、int64；取值范围为 [ -rank(input), rank(input) - 1]，当 axis 为负数时，表示从最后一个维度开始反向索引。</p>
</td>
</tr>
<tr id="row12549113810416"><td class="cellrowborder" valign="top" width="10.299999999999999%" headers="mcps1.2.6.1.1 "><p id="p15491838743"><a name="p15491838743"></a><a name="p15491838743"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.709999999999999%" headers="mcps1.2.6.1.2 "><p id="p1254913817417"><a name="p1254913817417"></a><a name="p1254913817417"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="8.32%" headers="mcps1.2.6.1.3 "><p id="p13549738642"><a name="p13549738642"></a><a name="p13549738642"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.689999999999998%" headers="mcps1.2.6.1.4 "><p id="p1054913810418"><a name="p1054913810418"></a><a name="p1054913810418"></a>沿 axis 维度进行累加求和后的结果。</p>
</td>
<td class="cellrowborder" valign="top" width="40.98%" headers="mcps1.2.6.1.5 "><p id="p185490381646"><a name="p185490381646"></a><a name="p185490381646"></a>数据类型和维度与 input 一致。</p>
</td>
</tr>
<tr id="row3425133971415"><td class="cellrowborder" valign="top" width="10.299999999999999%" headers="mcps1.2.6.1.1 "><p id="p19426639191411"><a name="p19426639191411"></a><a name="p19426639191411"></a>exclusive</p>
</td>
<td class="cellrowborder" valign="top" width="12.709999999999999%" headers="mcps1.2.6.1.2 "><p id="p19426113912149"><a name="p19426113912149"></a><a name="p19426113912149"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="8.32%" headers="mcps1.2.6.1.3 "><p id="p10426113912149"><a name="p10426113912149"></a><a name="p10426113912149"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="27.689999999999998%" headers="mcps1.2.6.1.4 "><p id="p3426139111418"><a name="p3426139111418"></a><a name="p3426139111418"></a>是否采用排除当前元素的累加方式。</p>
</td>
<td class="cellrowborder" valign="top" width="40.98%" headers="mcps1.2.6.1.5 "><p id="p642683971412"><a name="p642683971412"></a><a name="p642683971412"></a>-</p>
</td>
</tr>
<tr id="row163915351615"><td class="cellrowborder" valign="top" width="10.299999999999999%" headers="mcps1.2.6.1.1 "><p id="p763963191615"><a name="p763963191615"></a><a name="p763963191615"></a>reverse</p>
</td>
<td class="cellrowborder" valign="top" width="12.709999999999999%" headers="mcps1.2.6.1.2 "><p id="p963943121617"><a name="p963943121617"></a><a name="p963943121617"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="8.32%" headers="mcps1.2.6.1.3 "><p id="p18639113171615"><a name="p18639113171615"></a><a name="p18639113171615"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="27.689999999999998%" headers="mcps1.2.6.1.4 "><p id="p1863916311619"><a name="p1863916311619"></a><a name="p1863916311619"></a>是否沿指定维度反向累加。</p>
</td>
<td class="cellrowborder" valign="top" width="40.98%" headers="mcps1.2.6.1.5 "><p id="p563912361615"><a name="p563912361615"></a><a name="p563912361615"></a>-</p>
</td>
</tr>
</tbody>
</table>

### ReverseSequence<a name="ZH-CN_TOPIC_0000002599187919" id="ZH-CN_TOPIC_0000002599187919"></a>

**功能描述<a name="section167661757173918"></a>**

对输入张量指定轴前N个数据进行反转。

**表 1**  ReverseSequence参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.22%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.01%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.370000000000001%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.940000000000005%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.370000000000001%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.940000000000005%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>数据类型仅支持float32、uint8、int8、int32</p>
</td>
</tr>
<tr id="row10551185241"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p8555819241"><a name="p8555819241"></a><a name="p8555819241"></a>seq_lengths</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p165512815246"><a name="p165512815246"></a><a name="p165512815246"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.370000000000001%" headers="mcps1.2.6.1.3 "><p id="p115515818249"><a name="p115515818249"></a><a name="p115515818249"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.940000000000005%" headers="mcps1.2.6.1.4 "><p id="p10558802416"><a name="p10558802416"></a><a name="p10558802416"></a>输入张量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p25511814243"><a name="p25511814243"></a><a name="p25511814243"></a>数据类型仅支持int32，每个数据均满足0<=seq_len<=input_shape[seq_axis]</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.370000000000001%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.940000000000005%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>数据类型仅支持float32、uint8、int8、int32</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>batch_axis</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1159893018254"><a name="p1159893018254"></a><a name="p1159893018254"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.370000000000001%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.940000000000005%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a>批次轴的序号。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p516765919329"><a name="p516765919329"></a><a name="p516765919329"></a>默认为1，可支持缺省配置，必须与time_axis不同。仅支持0，1配置。</p>
</td>
</tr>
<tr id="row3838183521112"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p1879163715523"><a name="p1879163715523"></a><a name="p1879163715523"></a>seq_axis</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p10839435141118"><a name="p10839435141118"></a><a name="p10839435141118"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.370000000000001%" headers="mcps1.2.6.1.3 "><p id="p68391335181117"><a name="p68391335181117"></a><a name="p68391335181117"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.940000000000005%" headers="mcps1.2.6.1.4 "><p id="p6839183591113"><a name="p6839183591113"></a><a name="p6839183591113"></a>反转轴的序号。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p15970115515271"><a name="p15970115515271"></a><a name="p15970115515271"></a>默认为0，可支持缺省配置，必须与batch_axis不同。仅支持0，1配置。</p>
</td>
</tr>
</tbody>
</table>

### Relu6<a name="ZH-CN_TOPIC_0000002574010852" id="ZH-CN_TOPIC_0000002574010852"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量做Relu6激活函数运算。在输入为非负值且不大于 6 时保持原值，在输入为负值时置为 0，在输入大于 6 时置为 6。

**参数说明<a name="section162919203502"></a>**

**表 1**  Relu6参数概览

<a name="table542733973118"></a>
<table><thead align="left"><tr id="row742723916319"><th class="cellrowborder" valign="top" width="17.89178917891789%" id="mcps1.2.6.1.1"><p id="p6427153917312"><a name="p6427153917312"></a><a name="p6427153917312"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.14111411141114%" id="mcps1.2.6.1.2"><p id="p4537611185218"><a name="p4537611185218"></a><a name="p4537611185218"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.09130913091309%" id="mcps1.2.6.1.3"><p id="p1942815397310"><a name="p1942815397310"></a><a name="p1942815397310"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.18311831183118%" id="mcps1.2.6.1.4"><p id="p114282039103112"><a name="p114282039103112"></a><a name="p114282039103112"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.692669266926693%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row11968131541819"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.18311831183118%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.692669266926693%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row131890194187"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p0189101910184"><a name="p0189101910184"></a><a name="p0189101910184"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p418914198187"><a name="p418914198187"></a><a name="p418914198187"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.18311831183118%" headers="mcps1.2.6.1.4 "><p id="p121892195182"><a name="p121892195182"></a><a name="p121892195182"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.692669266926693%" headers="mcps1.2.6.1.5 "><p id="p1118918198181"><a name="p1118918198181"></a><a name="p1118918198181"></a>-</p>
</td>
</tr>
</tbody>
</table>

### LeakyRelu<a name="ZH-CN_TOPIC_0000002604689955" id="ZH-CN_TOPIC_0000002604689955"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量做LeakyRelu激活函数运算。在输入为非负值时保持原值，在输入为负值时根据缩放系数进行线性缩放。

**参数说明<a name="section162919203502"></a>**

**表 1**  LeakyRelu参数概览

<a name="table542733973118"></a>
<table><thead align="left"><tr id="row742723916319"><th class="cellrowborder" valign="top" width="17.89178917891789%" id="mcps1.2.6.1.1"><p id="p6427153917312"><a name="p6427153917312"></a><a name="p6427153917312"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.14111411141114%" id="mcps1.2.6.1.2"><p id="p4537611185218"><a name="p4537611185218"></a><a name="p4537611185218"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.09130913091309%" id="mcps1.2.6.1.3"><p id="p1942815397310"><a name="p1942815397310"></a><a name="p1942815397310"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.18311831183118%" id="mcps1.2.6.1.4"><p id="p114282039103112"><a name="p114282039103112"></a><a name="p114282039103112"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.692669266926693%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row11968131541819"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.18311831183118%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.692669266926693%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row71248273359"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p71241927203513"><a name="p71241927203513"></a><a name="p71241927203513"></a>alpha</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p6124102703518"><a name="p6124102703518"></a><a name="p6124102703518"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p612442712353"><a name="p612442712353"></a><a name="p612442712353"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="31.18311831183118%" headers="mcps1.2.6.1.4 "><p id="p13124127123514"><a name="p13124127123514"></a><a name="p13124127123514"></a>负半轴缩放系数</p>
</td>
<td class="cellrowborder" valign="top" width="26.692669266926693%" headers="mcps1.2.6.1.5 "><p id="p131243279356"><a name="p131243279356"></a><a name="p131243279356"></a>-</p>
</td>
</tr>
<tr id="row131890194187"><td class="cellrowborder" valign="top" width="17.89178917891789%" headers="mcps1.2.6.1.1 "><p id="p0189101910184"><a name="p0189101910184"></a><a name="p0189101910184"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.14111411141114%" headers="mcps1.2.6.1.2 "><p id="p418914198187"><a name="p418914198187"></a><a name="p418914198187"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.09130913091309%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.18311831183118%" headers="mcps1.2.6.1.4 "><p id="p121892195182"><a name="p121892195182"></a><a name="p121892195182"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.692669266926693%" headers="mcps1.2.6.1.5 "><p id="p1118918198181"><a name="p1118918198181"></a><a name="p1118918198181"></a>-</p>
</td>
</tr>
</tbody>
</table>

### HardSwish<a name="ZH-CN_TOPIC_0000002574309498" id="ZH-CN_TOPIC_0000002574309498"></a>

**功能描述<a name="section113841812134710"></a>**

对输入张量做HardSwish激活函数运算。公式为：output = input \* HardSigmoid\(α=1/6, β=0.5, input\)

**参数说明<a name="section15195134816462"></a>**

**表 1**  HardSwish参数概览

<a name="table1033212264218"></a>
<table><thead align="left"><tr id="row133331626923"><th class="cellrowborder" valign="top" width="16.619999999999997%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.56%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.889999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.320000000000004%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.610000000000003%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row14333926224"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p1790719584217"><a name="p1790719584217"></a><a name="p1790719584217"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p199084588217"><a name="p199084588217"></a><a name="p199084588217"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p11673723615"><a name="p11673723615"></a><a name="p11673723615"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCL/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p035182116187"><a name="p035182116187"></a><a name="p035182116187"></a>-</p>
</td>
</tr>
<tr id="row9388316349"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p193881514347"><a name="p193881514347"></a><a name="p193881514347"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p163881913346"><a name="p163881913346"></a><a name="p163881913346"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p1517530111819"><a name="p1517530111819"></a><a name="p1517530111819"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p18351172171817"><a name="p18351172171817"></a><a name="p18351172171817"></a>-</p>
</td>
</tr>
</tbody>
</table>

### LogicalAnd<a name="ZH-CN_TOPIC_0000002574976868" id="ZH-CN_TOPIC_0000002574976868"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“与”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![img](public_sys-resources/icon-note.gif) **说明：**
>LogicalAnd支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。
>LogicalAnd算子不支持量化。

**表 1**  LogicalAnd参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>左输入张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>右输入张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Equal<a name="ZH-CN_TOPIC_0000002605336325" id="ZH-CN_TOPIC_0000002605336325"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“等于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Equal支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Equal参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>左输入张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>右输入张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
</tbody>
</table>

### GreaterEqual<a name="ZH-CN_TOPIC_0000002574817236" id="ZH-CN_TOPIC_0000002574817236"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“大于等于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>GreaterEqual支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  GreaterEqual参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>左输入张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>右输入张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Greater<a name="ZH-CN_TOPIC_0000002605456261" id="ZH-CN_TOPIC_0000002605456261"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“大于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Greater支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Greater参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>左输入张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>右输入张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
</tbody>
</table>

### LessEqual<a name="ZH-CN_TOPIC_0000002574976872" id="ZH-CN_TOPIC_0000002574976872"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“小于等于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>LessEqual支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  LessEqual参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>左输入张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>右输入张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Less<a name="ZH-CN_TOPIC_0000002605336331" id="ZH-CN_TOPIC_0000002605336331"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“小于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Less支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Less参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>左输入张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>右输入张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
</tbody>
</table>

### NotEqual<a name="ZH-CN_TOPIC_0000002574817240" id="ZH-CN_TOPIC_0000002574817240"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“不等于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>NotEqual支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  NotEqual参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>左输入张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>右输入张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
</tbody>
</table>

### LogicalNot<a name="ZH-CN_TOPIC_0000002605456267" id="ZH-CN_TOPIC_0000002605456267"></a>

**功能描述<a name="section270785104414"></a>**

逐元素返回输入张量的取反值。

**参数说明<a name="section162919203502"></a>**

> ![img](public_sys-resources/icon-note.gif) **说明：**
> LogicalNot算子不支持量化。

**表 1**  LogicalNot参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p1368319278418"><a name="p1368319278418"></a><a name="p1368319278418"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### LogicalOr<a name="ZH-CN_TOPIC_0000002574976878" id="ZH-CN_TOPIC_0000002574976878"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“或”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![img](public_sys-resources/icon-note.gif) **说明：**
>LogicalOr支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。
>LogicalOr算子不支持量化。

**表 1**  LogicalOr参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>lhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>左输入张量，维度为2D/3D/4D，格式分别为ND、NWC，NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>rhs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>右输入张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND，NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Elu<a name="ZH-CN_TOPIC_0000002660274969" id="ZH-CN_TOPIC_0000002660274969"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量做Elu激活函数运算。公式为：y = x if x \>= 0 else  \(exp\(x\)-1\)

**参数说明<a name="section12350142612246"></a>**

**表 1**  Elu参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
</tbody>
</table>

### DepthToSpace<a name="ZH-CN_TOPIC_0000002660395017" id="ZH-CN_TOPIC_0000002660395017"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量维度的深度（通道）维度的数据重排到空间（高、宽）维度。

**参数说明<a name="section12350142612246"></a>**

**表 1**  DepthToSpace参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为4D，格式分别为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为4D，格式分别为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row16646162255418"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p464613227544"><a name="p464613227544"></a><a name="p464613227544"></a>block_size</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p196461422105415"><a name="p196461422105415"></a><a name="p196461422105415"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p464652265416"><a name="p464652265416"></a><a name="p464652265416"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1564612213546"><a name="p1564612213546"></a><a name="p1564612213546"></a>从深度维度重组到空间维度的基础块尺寸</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p196467225548"><a name="p196467225548"></a><a name="p196467225548"></a>规格约束：block_size>=2， C%block_size^2 == 0</p>
</td>
</tr>
</tbody>
</table>

### SpaceToDepth<a name="ZH-CN_TOPIC_0000002630115702" id="ZH-CN_TOPIC_0000002630115702"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量空间（高、宽）维度的数据重排到深度（通道）维度。

**参数说明<a name="section12350142612246"></a>**

**表 1**  SpaceToDepth参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为4D，格式分别为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为4D，格式分别为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row16646162255418"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p464613227544"><a name="p464613227544"></a><a name="p464613227544"></a>block_size</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p196461422105415"><a name="p196461422105415"></a><a name="p196461422105415"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p464652265416"><a name="p464652265416"></a><a name="p464652265416"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1564612213546"><a name="p1564612213546"></a><a name="p1564612213546"></a>从空间维度重组到深度维度的基础块尺寸</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p196467225548"><a name="p196467225548"></a><a name="p196467225548"></a>规格约束：block_size>=2， H%block_size == 0，W%block_size == 0</p>
</td>
</tr>
</tbody>
</table>

### Fill<a name="ZH-CN_TOPIC_0000002800000001" id="ZH-CN_TOPIC_0000002800000001"></a>

**功能描述<a name="section_fill_func_desc"></a>**

创建形状为 dims 的张量，所有元素填充为给定的标量 value。该算子仅在 TFLITE 框架中定义（BuiltinOperator 编号：94），ONNX 框架无对应标准算子。不支持 ONNX 格式转换。

**参数说明<a name="section_fill_param_desc"></a>**

**表 1**  Fill参数概览

<a name="table_fill_param"></a>
<table><thead align="left"><tr id="row_fill_header"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p_fill_h1"><a name="p_fill_h1"></a><a name="p_fill_h1"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p_fill_h2"><a name="p_fill_h2"></a><a name="p_fill_h2"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.49%" id="mcps1.2.6.1.3"><p id="p_fill_h3"><a name="p_fill_h3"></a><a name="p_fill_h3"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p_fill_h4"><a name="p_fill_h4"></a><a name="p_fill_h4"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p_fill_h5"><a name="p_fill_h5"></a><a name="p_fill_h5"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row_fill_dims"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p_fill_dims_p"><a name="p_fill_dims_p"></a><a name="p_fill_dims_p"></a>dims</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p_fill_dims_io"><a name="p_fill_dims_io"></a><a name="p_fill_dims_io"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.49%" headers="mcps1.2.6.1.3 "><p id="p_fill_dims_dt"><a name="p_fill_dims_dt"></a><a name="p_fill_dims_dt"></a>tensor(int32)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p_fill_dims_desc"><a name="p_fill_dims_desc"></a><a name="p_fill_dims_desc"></a>输出张量的形状，维度为1D，每个元素指定一个维度的大小。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p_fill_dims_limit"><a name="p_fill_dims_limit"></a><a name="p_fill_dims_limit"></a>规格约束：每个元素 &ge; 0，维度数不超过 32</p>
</td>
</tr>
<tr id="row_fill_value"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p_fill_value_p"><a name="p_fill_value_p"></a><a name="p_fill_value_p"></a>value</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p_fill_value_io"><a name="p_fill_value_io"></a><a name="p_fill_value_io"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.49%" headers="mcps1.2.6.1.3 "><p id="p_fill_value_dt"><a name="p_fill_value_dt"></a><a name="p_fill_value_dt"></a>tensor(fp32/int32/bool/int8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p_fill_value_desc"><a name="p_fill_value_desc"></a><a name="p_fill_value_desc"></a>填充值，标量（0-D 张量），数据类型决定输出张量的数据类型。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p_fill_value_limit"><a name="p_fill_value_limit"></a><a name="p_fill_value_limit"></a>规格约束：fp16 不支持该类型</p>
</td>
</tr>
<tr id="row_fill_output"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p_fill_output_p"><a name="p_fill_output_p"></a><a name="p_fill_output_p"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p_fill_output_io"><a name="p_fill_output_io"></a><a name="p_fill_output_io"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.49%" headers="mcps1.2.6.1.3 "><p id="p_fill_output_dt"><a name="p_fill_output_dt"></a><a name="p_fill_output_dt"></a>tensor(fp32/int32/bool/int8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p_fill_output_desc"><a name="p_fill_output_desc"></a><a name="p_fill_output_desc"></a>输出张量，形状 = dims，全部元素 = value，数据类型与 value 一致。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p_fill_output_limit"><a name="p_fill_output_limit"></a><a name="p_fill_output_limit"></a>-</p></td>
</tr>
</tbody>
</table>

### Shape<a name="ZH-CN_TOPIC_0000003030115702" id="ZH-CN_TOPIC_0000003030115702"></a>

**功能描述<a name="section3030115702a"></a>**

获取输入张量的形状信息。

**参数说明<a name="section3030115702b"></a>**

**表 1**  Shape参数概览

<a name="table3030115702a"></a>
<table><thead align="left"><tr id="row3030115702h"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p30301157021"><a name="p30301157021"></a><a name="p30301157021"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p30301157022"><a name="p30301157022"></a><a name="p30301157022"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p30301157023"><a name="p30301157023"></a><a name="p30301157023"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p30301157024"><a name="p30301157024"></a><a name="p30301157024"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p30301157025"><a name="p30301157025"></a><a name="p30301157025"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row3030115702r1"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3030115702r1a"><a name="p3030115702r1a"></a><a name="p3030115702r1a"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3030115702r1b"><a name="p3030115702r1b"></a><a name="p3030115702r1b"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3030115702r1c"><a name="p3030115702r1c"></a><a name="p3030115702r1c"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3030115702r1d"><a name="p3030115702r1d"></a><a name="p3030115702r1d"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3030115702r1e"><a name="p3030115702r1e"></a><a name="p3030115702r1e"></a>-</p>
</td>
</tr>
<tr id="row3030115702r2"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3030115702r2a"><a name="p3030115702r2a"></a><a name="p3030115702r2a"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3030115702r2b"><a name="p3030115702r2b"></a><a name="p3030115702r2b"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3030115702r2c"><a name="p3030115702r2c"></a><a name="p3030115702r2c"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3030115702r2d"><a name="p3030115702r2d"></a><a name="p3030115702r2d"></a>输出张量，维度为1D，元素为输入张量的各维度大小。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3030115702r2e"><a name="p3030115702r2e"></a><a name="p3030115702r2e"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Neg<a name="ZH-CN_TOPIC_0000002900000001" id="ZH-CN_TOPIC_0000002900000001"></a>

**功能描述<a name="section_neg_tflite_desc"></a>**

对张量的每个元素做取负运算（符号取反），即 y = -x。

**参数说明<a name="section_neg_tflite_param"></a>**

**表 1**  Neg参数概览

<a name="table_neg_tflite"></a>
<table><thead align="left"><tr id="row_neg_tflite_hdr"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p_neg_tflite_hdr1"><a name="p_neg_tflite_hdr1"></a><a name="p_neg_tflite_hdr1"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p_neg_tflite_hdr2"><a name="p_neg_tflite_hdr2"></a><a name="p_neg_tflite_hdr2"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.49%" id="mcps1.2.6.1.3"><p id="p_neg_tflite_hdr3"><a name="p_neg_tflite_hdr3"></a><a name="p_neg_tflite_hdr3"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p_neg_tflite_hdr4"><a name="p_neg_tflite_hdr4"></a><a name="p_neg_tflite_hdr4"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p_neg_tflite_hdr5"><a name="p_neg_tflite_hdr5"></a><a name="p_neg_tflite_hdr5"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row_neg_tflite_in"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p_neg_tflite_in_p"><a name="p_neg_tflite_in_p"></a><a name="p_neg_tflite_in_p"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p_neg_tflite_in_io"><a name="p_neg_tflite_in_io"></a><a name="p_neg_tflite_in_io"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.49%" headers="mcps1.2.6.1.3 "><p id="p_neg_tflite_in_dt"><a name="p_neg_tflite_in_dt"></a><a name="p_neg_tflite_in_dt"></a>tensor(fp32/int8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p_neg_tflite_in_desc"><a name="p_neg_tflite_in_desc"></a><a name="p_neg_tflite_in_desc"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p_neg_tflite_in_limit"><a name="p_neg_tflite_in_limit"></a><a name="p_neg_tflite_in_limit"></a>规格约束：fp16 不支持该类型；int8 需全量化 cfg</p>
</td>
</tr>
<tr id="row_neg_tflite_out"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p_neg_tflite_out_p"><a name="p_neg_tflite_out_p"></a><a name="p_neg_tflite_out_p"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p_neg_tflite_out_io"><a name="p_neg_tflite_out_io"></a><a name="p_neg_tflite_out_io"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.49%" headers="mcps1.2.6.1.3 "><p id="p_neg_tflite_out_dt"><a name="p_neg_tflite_out_dt"></a><a name="p_neg_tflite_out_dt"></a>tensor(fp32/int8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p_neg_tflite_out_desc"><a name="p_neg_tflite_out_desc"></a><a name="p_neg_tflite_out_desc"></a>输出张量，维度与输入 x 相同，每个元素为 x 对应元素的相反数。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p_neg_tflite_out_limit"><a name="p_neg_tflite_out_limit"></a><a name="p_neg_tflite_out_limit"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Pow<a name="ZH-CN_TOPIC_0000002476598365" id="ZH-CN_TOPIC_0000002476598365"></a>

**功能描述<a name="section_pow_func"></a>**

计算两个张量的逐元素幂运算，base 为底数张量，exponent 为指数张量，输出 result = base^exponent。支持 NumPy 风格广播。

**参数说明<a name="section_pow_param"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>1. Pow 无内置属性，转换时自动填充。支持广播特性，双向广播需在转换命令中明确配置 inputDataFormat 和 outputDataFormat 参数。
>2. 推荐使用 X ≥ 0 的输入组合确保结果确定性；X < 0 且 Y 为非整数时实数域无定义，输出值取决于底层数学库。
>3. INT8 量化仅支持 X ≥ 0 的输入，X < 0 时负数值在 int8 对称量化中将被映射为 0。

**表 1**  Pow参数概览

<a name="table_pow_tflite"></a>
<table><thead align="left"><tr id="row_pow_tflite_hdr"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p_pow_tflite_hdr1"><a name="p_pow_tflite_hdr1"></a><a name="p_pow_tflite_hdr1"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p_pow_tflite_hdr2"><a name="p_pow_tflite_hdr2"></a><a name="p_pow_tflite_hdr2"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p_pow_tflite_hdr3"><a name="p_pow_tflite_hdr3"></a><a name="p_pow_tflite_hdr3"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p_pow_tflite_hdr4"><a name="p_pow_tflite_hdr4"></a><a name="p_pow_tflite_hdr4"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p_pow_tflite_hdr5"><a name="p_pow_tflite_hdr5"></a><a name="p_pow_tflite_hdr5"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row_pow_tflite_base"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p_pow_tflite_base_name"><a name="p_pow_tflite_base_name"></a><a name="p_pow_tflite_base_name"></a>base</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p_pow_tflite_base_io"><a name="p_pow_tflite_base_io"></a><a name="p_pow_tflite_base_io"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p_pow_tflite_base_dt"><a name="p_pow_tflite_base_dt"></a><a name="p_pow_tflite_base_dt"></a>tensor(fp32/int8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p_pow_tflite_base_desc"><a name="p_pow_tflite_base_desc"></a><a name="p_pow_tflite_base_desc"></a>底数张量，维度为 1D/2D/3D/4D，格式分别为 ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p_pow_tflite_base_limit"><a name="p_pow_tflite_base_limit"></a><a name="p_pow_tflite_base_limit"></a>规格约束：最大维度 4D；支持 NumPy 广播；fp16 不支持该类型；INT8 不支持 X&lt;0 的输入</p>
</td>
</tr>
<tr id="row_pow_tflite_exp"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p_pow_tflite_exp_name"><a name="p_pow_tflite_exp_name"></a><a name="p_pow_tflite_exp_name"></a>exponent</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p_pow_tflite_exp_io"><a name="p_pow_tflite_exp_io"></a><a name="p_pow_tflite_exp_io"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p_pow_tflite_exp_dt"><a name="p_pow_tflite_exp_dt"></a><a name="p_pow_tflite_exp_dt"></a>tensor(fp32/int8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p_pow_tflite_exp_desc"><a name="p_pow_tflite_exp_desc"></a><a name="p_pow_tflite_exp_desc"></a>指数张量，维度为 1D/2D/3D/4D，与 base 广播兼容。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p_pow_tflite_exp_limit"><a name="p_pow_tflite_exp_limit"></a><a name="p_pow_tflite_exp_limit"></a>规格约束：最大维度 4D；fp16 不支持该类型</p>
</td>
</tr>
<tr id="row_pow_tflite_out"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p_pow_tflite_out_name"><a name="p_pow_tflite_out_name"></a><a name="p_pow_tflite_out_name"></a>result</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p_pow_tflite_out_io"><a name="p_pow_tflite_out_io"></a><a name="p_pow_tflite_out_io"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p_pow_tflite_out_dt"><a name="p_pow_tflite_out_dt"></a><a name="p_pow_tflite_out_dt"></a>tensor(fp32/int8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p_pow_tflite_out_desc"><a name="p_pow_tflite_out_desc"></a><a name="p_pow_tflite_out_desc"></a>输出张量，维度为 base 与 exponent 的广播结果，格式分别为 ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p_pow_tflite_out_limit"><a name="p_pow_tflite_out_limit"></a><a name="p_pow_tflite_out_limit"></a>规格约束：最大维度 4D；fp16 不支持该类型</p></td>
</tr>
</tbody>
</table>

### TopK<a name="ZH-CN_TOPIC_0000003050115702" id="ZH-CN_TOPIC_0000003050115702"></a>

**功能描述<a name="section3050115702a"></a>**

获取输入张量中沿指定维度前K个最大值。

**参数说明<a name="section3050115702b"></a>**

**表 1**  TopK参数概览

<a name="table3050115702a"></a>
<table><thead align="left"><tr id="row3050115702h"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p30501157021"><a name="p30501157021"></a><a name="p30501157021"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p30501157022"><a name="p30501157022"></a><a name="p30501157022"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p30501157023"><a name="p30501157023"></a><a name="p30501157023"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p30501157024"><a name="p30501157024"></a><a name="p30501157024"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p30501157025"><a name="p30501157025"></a><a name="p30501157025"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row3050115702r1"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115702r1a"><a name="p3050115702r1a"></a><a name="p3050115702r1a"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115702r1b"><a name="p3050115702r1b"></a><a name="p3050115702r1b"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115702r1c"><a name="p3050115702r1c"></a><a name="p3050115702r1c"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115702r1d"><a name="p3050115702r1d"></a><a name="p3050115702r1d"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115702r1e"><a name="p3050115702r1e"></a><a name="p3050115702r1e"></a>-</p>
</td>
</tr>
<tr id="row3050115702r2"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115702r2a"><a name="p3050115702r2a"></a><a name="p3050115702r2a"></a>k</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115702r2b"><a name="p3050115702r2b"></a><a name="p3050115702r2b"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115702r2c"><a name="p3050115702r2c"></a><a name="p3050115702r2c"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115702r2d"><a name="p3050115702r2d"></a><a name="p3050115702r2d"></a>需要获取的TopK个数，标量。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115702r2e"><a name="p3050115702r2e"></a><a name="p3050115702r2e"></a>-</p>
</td>
</tr>
<tr id="row3050115702r3"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115702r3a"><a name="p3050115702r3a"></a><a name="p3050115702r3a"></a>values</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115702r3b"><a name="p3050115702r3b"></a><a name="p3050115702r3b"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115702r3c"><a name="p3050115702r3c"></a><a name="p3050115702r3c"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115702r3d"><a name="p3050115702r3d"></a><a name="p3050115702r3d"></a>TopK值张量，最后一维为K。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115702r3e"><a name="p3050115702r3e"></a><a name="p3050115702r3e"></a>-</p>
</td>
</tr>
<tr id="row3050115702r4"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115702r4a"><a name="p3050115702r4a"></a><a name="p3050115702r4a"></a>indices</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115702r4b"><a name="p3050115702r4b"></a><a name="p3050115702r4b"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115702r4c"><a name="p3050115702r4c"></a><a name="p3050115702r4c"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115702r4d"><a name="p3050115702r4d"></a><a name="p3050115702r4d"></a>TopK值的索引张量，最后一维为K。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115702r4e"><a name="p3050115702r4e"></a><a name="p3050115702r4e"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Gelu<a name="ZH-CN_TOPIC_0000002661401191" id="ZH-CN_TOPIC_0000002661401191"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量做Gelu激活函数运算。Gelu（Gaussian Error Linear Unit）基于正态分布累积概率，对输入乘以其概率分布的值实现连续非线性变换，相比传统激活函数在负值区域具有平滑的非零梯度。

**参数说明<a name="section12350142612246"></a>**

**表 1**  Gelu参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row16646162255418"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p464613227544"><a name="p464613227544"></a><a name="p464613227544"></a>approximate</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p196461422105415"><a name="p196461422105415"></a><a name="p196461422105415"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p464652265416"><a name="p464652265416"></a><a name="p464652265416"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1564612213546"><a name="p1564612213546"></a><a name="p1564612213546"></a>是否启用tanh近似计算模式，默认值false。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p196467225548"><a name="p196467225548"></a><a name="p196467225548"></a>配置范围：false（采用高精度拟合计算）、true（采用tanh快速近似算法）</p>
</td>
</tr>
</tbody>
</table>

### Pack<a name="ZH-CN_TOPIC_0000002661401192" id="ZH-CN_TOPIC_0000002661401192"></a>

**功能描述<a name="section37550136507"></a>**

Pack算子用于沿着指定的新轴（axis）将一组形状相同的输入张量堆叠（拼接）成一个新的高维张量。堆叠后输出张量的维度（Rank）相比单个输入张量增加1。

**参数说明<a name="section12350142612246"></a>**

**表 1**  Pack参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row2423132175015"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>values</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p189321956152"><a name="p189321956152"></a><a name="p189321956152"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>varList(tensor)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p19305746101210"><a name="p19305746101210"></a><a name="p19305746101210"></a>输入张量列表，内部各张量维度为2D/3D/4D，格式分别为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p66671634141811"><a name="p66671634141811"></a><a name="p66671634141811"></a>规格约束：列表中各张量形状完全相同</p>
</td>
</tr>
<tr id="row334168176"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p6341189713"><a name="p6341189713"></a><a name="p6341189713"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p6341289719"><a name="p6341289719"></a><a name="p6341289719"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p6181781394"><a name="p6181781394"></a><a name="p6181781394"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度比单个输入多1维（输出Rank=输入Rank+1），格式分别为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p55991825111919"><a name="p55991825111919"></a><a name="p55991825111919"></a>-</p>
</td>
</tr>
<tr id="row175528015178"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p11498144101710"><a name="p11498144101710"></a><a name="p11498144101710"></a>values_count</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p1498946175"><a name="p1498946175"></a><a name="p1498946175"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p1649814141714"><a name="p1649814141714"></a><a name="p1649814141714"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p174988410177"><a name="p174988410177"></a><a name="p174988410177"></a>输入张量列表中张量的个数。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p1525013286014"><a name="p1525013286014"></a><a name="p1525013286014"></a>规格约束：必须与实际传入的输入张量数量一致（values_count&gt;=1）</p>
</td>
</tr>
<tr id="row195632034203"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p6218353165419"><a name="p6218353165419"></a><a name="p6218353165419"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>堆叠操作插入的新维度轴编号。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>规格约束：范围为[-(R+1), R]（其中R为单个输入张量的维度数）</p>
</td>
</tr>
</tbody>
</table>

### Unpack<a name="ZH-CN_TOPIC_0000002661401193" id="ZH-CN_TOPIC_0000002661401193"></a>

**功能描述<a name="section37550136507"></a>**

Unpack算子用于沿指定的轴（axis）将一个高维张量拆分（解包）成一组低维张量，是Pack算子的逆向操作。解包后每个输出张量的维度（Rank）相比输入张量减少1。

**参数说明<a name="section12350142612246"></a>**

**表 1**  Unpack参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NWC/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row2423132175015"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>outputs</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p189321956152"><a name="p189321956152"></a><a name="p189321956152"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>varList(tensor)</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p19305746101210"><a name="p19305746101210"></a><a name="p19305746101210"></a>输出张量列表，每个输出张量维度为输入维度-1（输出Rank=输入Rank-1），输出张量数量等于输入在axis轴上的Size。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p66671634141811"><a name="p66671634141811"></a><a name="p66671634141811"></a>-</p>
</td>
</tr>
<tr id="row175528015178"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p11498144101710"><a name="p11498144101710"></a><a name="p11498144101710"></a>num</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p1498946175"><a name="p1498946175"></a><a name="p1498946175"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p1649814141714"><a name="p1649814141714"></a><a name="p1649814141714"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p174988410177"><a name="p174988410177"></a><a name="p174988410177"></a>从输入中拆分出的张量数量（即输出列表长度）。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p1525013286014"><a name="p1525013286014"></a><a name="p1525013286014"></a>规格约束：必须严格等于输入张量在指定axis轴上的维度大小（input.shape[axis]==num）</p>
</td>
</tr>
<tr id="row195632034203"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p7218175312547"><a name="p7218175312547"></a><a name="p7218175312547"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p14218953115410"><a name="p14218953115410"></a><a name="p14218953115410"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p6218353165419"><a name="p6218353165419"></a><a name="p6218353165419"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p12181953195416"><a name="p12181953195416"></a><a name="p12181953195416"></a>执行拆分操作的维度轴编号。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p1221875316545"><a name="p1221875316545"></a><a name="p1221875316545"></a>规格约束：范围为[-R, R-1]（其中R为输入张量的维度数）</p>
</td>
</tr>
</tbody>
</table>

### Select<a name="ZH-CN_TOPIC_0000002600000001" id="ZH-CN_TOPIC_0000002600000001"></a>

**功能描述<a name="section270785104415"></a>**

根据条件张量从两输入张量中选择元素,不支持广播。

**参数说明<a name="section1970335944612"></a>**

**表 1**  Select参数概览

<a name="table4179355155017"></a>
<table><thead align="left"><tr id="row417995510502"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912565"><a name="p369065912565"></a><a name="p369065912565"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319550"><a name="p4185174319550"></a><a name="p4185174319550"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599567"><a name="p769019599567"></a><a name="p769019599567"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919566"><a name="p1069045919566"></a><a name="p1069045919566"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913565"><a name="p1769075913565"></a><a name="p1769075913565"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045215"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191813"><a name="p109681815191813"></a><a name="p109681815191813"></a>condition</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161818"><a name="p15968615161818"></a><a name="p15968615161818"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411150"><a name="p82590411150"></a><a name="p82590411150"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413219"><a name="p11225145413219"></a><a name="p11225145413219"></a>条件张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171818"><a name="p6968615171818"></a><a name="p6968615171818"></a>规格约束：数据类型为bool</p>
</td>
</tr>
<tr id="row14341183720527"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115216"><a name="p23411437115216"></a><a name="p23411437115216"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735217"><a name="p13341143735217"></a><a name="p13341143735217"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720522"><a name="p19341103720522"></a><a name="p19341103720522"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655320"><a name="p191865655320"></a><a name="p191865655320"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377530"><a name="p193418377530"></a><a name="p193418377530"></a>-</p>
</td>
</tr>
<tr id="row14341183720528"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115217"><a name="p23411437115217"></a><a name="p23411437115217"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735218"><a name="p13341143735218"></a><a name="p13341143735218"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720523"><a name="p19341103720523"></a><a name="p19341103720523"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655321"><a name="p191865655321"></a><a name="p191865655321"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377531"><a name="p193418377531"></a><a name="p193418377531"></a>-</p>
</td>
</tr>
<tr id="row141801355145020"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115015"><a name="p191801255115015"></a><a name="p191801255115015"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258233"><a name="p5501258233"></a><a name="p5501258233"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345213"><a name="p526953345213"></a><a name="p526953345213"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215559"><a name="p1985391215559"></a><a name="p1985391215559"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165521"><a name="p12336815165521"></a><a name="p12336815165521"></a>-</p>
</td>
</tr>
</tbody>
</table>

### SelectV2<a name="ZH-CN_TOPIC_0000002600000002" id="ZH-CN_TOPIC_0000002600000002"></a>

**功能描述<a name="section270785104416"></a>**

根据条件张量从两输入张量中选择元素，支持广播。

**参数说明<a name="section1970335944613"></a>**

**表 1**  SelectV2参数概览

<a name="table4179355155018"></a>
<table><thead align="left"><tr id="row417995510503"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912566"><a name="p369065912566"></a><a name="p369065912566"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319551"><a name="p4185174319551"></a><a name="p4185174319551"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599568"><a name="p769019599568"></a><a name="p769019599568"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919567"><a name="p1069045919567"></a><a name="p1069045919567"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913566"><a name="p1769075913566"></a><a name="p1769075913566"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045216"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191814"><a name="p109681815191814"></a><a name="p109681815191814"></a>condition</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161819"><a name="p15968615161819"></a><a name="p15968615161819"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411151"><a name="p82590411151"></a><a name="p82590411151"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413220"><a name="p11225145413220"></a><a name="p11225145413220"></a>条件张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171819"><a name="p6968615171819"></a><a name="p6968615171819"></a>规格约束：数据类型为bool</p>
</td>
</tr>
<tr id="row14341183720529"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115218"><a name="p23411437115218"></a><a name="p23411437115218"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735219"><a name="p13341143735219"></a><a name="p13341143735219"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720524"><a name="p19341103720524"></a><a name="p19341103720524"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655322"><a name="p191865655322"></a><a name="p191865655322"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377532"><a name="p193418377532"></a><a name="p193418377532"></a>-</p>
</td>
</tr>
<tr id="row14341183720530"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115219"><a name="p23411437115219"></a><a name="p23411437115219"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735220"><a name="p13341143735220"></a><a name="p13341143735220"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720525"><a name="p19341103720525"></a><a name="p19341103720525"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655323"><a name="p191865655323"></a><a name="p191865655323"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377533"><a name="p193418377533"></a><a name="p193418377533"></a>-</p>
</td>
</tr>
<tr id="row141801355145021"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115016"><a name="p191801255115016"></a><a name="p191801255115016"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258234"><a name="p5501258234"></a><a name="p5501258234"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345214"><a name="p526953345214"></a><a name="p526953345214"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215560"><a name="p1985391215560"></a><a name="p1985391215560"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165522"><a name="p12336815165522"></a><a name="p12336815165522"></a>-</p>
</td>
</tr>
</tbody>
</table>

### ReverseV2<a name="ZH-CN_TOPIC_0000002600000003" id="ZH-CN_TOPIC_0000002600000003"></a>

**功能描述<a name="section270785104417"></a>**

沿指定轴对张量进行反转。

**参数说明<a name="section1970335944614"></a>**

**表 1**  ReverseV2参数概览

<a name="table4179355155019"></a>
<table><thead align="left"><tr id="row417995510504"><th class="cellrowborder" valign="top" width="17.79%" id="mcps1.2.6.1.1"><p id="p369065912567"><a name="p369065912567"></a><a name="p369065912567"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.17%" id="mcps1.2.6.1.2"><p id="p4185174319552"><a name="p4185174319552"></a><a name="p4185174319552"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.320000000000002%" id="mcps1.2.6.1.3"><p id="p769019599569"><a name="p769019599569"></a><a name="p769019599569"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.44%" id="mcps1.2.6.1.4"><p id="p1069045919568"><a name="p1069045919568"></a><a name="p1069045919568"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.279999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913567"><a name="p1769075913567"></a><a name="p1769075913567"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045217"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p109681815191815"><a name="p109681815191815"></a><a name="p109681815191815"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p15968615161820"><a name="p15968615161820"></a><a name="p15968615161820"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p82590411152"><a name="p82590411152"></a><a name="p82590411152"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p11225145413221"><a name="p11225145413221"></a><a name="p11225145413221"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p6968615171820"><a name="p6968615171820"></a><a name="p6968615171820"></a>-</p>
</td>
</tr>
<tr id="row14341183720531"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p23411437115220"><a name="p23411437115220"></a><a name="p23411437115220"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p13341143735221"><a name="p13341143735221"></a><a name="p13341143735221"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p19341103720526"><a name="p19341103720526"></a><a name="p19341103720526"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p191865655324"><a name="p191865655324"></a><a name="p191865655324"></a>指定反转的轴，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p193418377534"><a name="p193418377534"></a><a name="p193418377534"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，元素不重复，元素数量不超过4</p>
</td>
</tr>
<tr id="row141801355145022"><td class="cellrowborder" valign="top" width="17.79%" headers="mcps1.2.6.1.1 "><p id="p191801255115017"><a name="p191801255115017"></a><a name="p191801255115017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.17%" headers="mcps1.2.6.1.2 "><p id="p5501258235"><a name="p5501258235"></a><a name="p5501258235"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.320000000000002%" headers="mcps1.2.6.1.3 "><p id="p526953345215"><a name="p526953345215"></a><a name="p526953345215"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.44%" headers="mcps1.2.6.1.4 "><p id="p1985391215561"><a name="p1985391215561"></a><a name="p1985391215561"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.279999999999998%" headers="mcps1.2.6.1.5 "><p id="p12336815165523"><a name="p12336815165523"></a><a name="p12336815165523"></a>-</p>
</td>
</tr>
</tbody>
</table>

## ONNX算子规格参考<a name="ZH-CN_TOPIC_0000002320738138" id="ZH-CN_TOPIC_0000002320738138"></a>

-   **[Conv](#ZH-CN_TOPIC_0000002326152940)**  

-   **[MaxPool](#ZH-CN_TOPIC_0000002325993104)**  

-   **[Gemm](#ZH-CN_TOPIC_0000002360071441)**  

-   **[Matmul](#ZH-CN_TOPIC_0000002455345333)**  

-   **[Softmax](#ZH-CN_TOPIC_0000002360191597)**  

-   **[Relu](#ZH-CN_TOPIC_0000002326152944)**  

-   **[Tanh](#ZH-CN_TOPIC_0000002474764481)**  

-   **[Sigmoid](#ZH-CN_TOPIC_0000002441564330)**  

-   **[Reshape](#ZH-CN_TOPIC_0000002325993108)**  

-   **[Mul](#ZH-CN_TOPIC_0000002455226053)**  

-   **[Add](#ZH-CN_TOPIC_0000002454832353)**  

-   **[Sub](#ZH-CN_TOPIC_0000002454792465)**  

-   **[Gather](#ZH-CN_TOPIC_0000002421843980)**  

-   **[Split](#ZH-CN_TOPIC_0000002421393470)**  

-   **[Concat](#ZH-CN_TOPIC_0000002421233606)**  

-   **[AveragePool](#ZH-CN_TOPIC_0000002455402925)**  

-   **[InstanceNormalization](#ZH-CN_TOPIC_0000002453072106)**  

-   **[LSTM](#ZH-CN_TOPIC_0000002486111849)**  

-   **[Tile](#ZH-CN_TOPIC_0000002513105051)**  

-   **[Pad](#ZH-CN_TOPIC_0000002480825566)**  

-   **[Resize](#ZH-CN_TOPIC_0000002512945433)**  

-   **[Squeeze](#ZH-CN_TOPIC_0000002482800962)**  

-   **[Unsqueeze](#ZH-CN_TOPIC_0000002482804754)**  

-   **[Flatten](#ZH-CN_TOPIC_0000002515124725)**  

-   **[Abs](#ZH-CN_TOPIC_0000002485239888)**  

-   **[Ceil](#ZH-CN_TOPIC_0000002517399797)**  

-   **[Cos](#ZH-CN_TOPIC_0000002517479775)**  

-   **[Exp](#ZH-CN_TOPIC_0000002485399854)**  

-   **[Floor](#ZH-CN_TOPIC_0000002485239890)**  

-   **[Log](#ZH-CN_TOPIC_0000002517399799)**  

-   **[Round](#ZH-CN_TOPIC_0000002517479777)**  

-   **[Sin](#ZH-CN_TOPIC_0000002485399856)**  

-   **[Sqrt](#ZH-CN_TOPIC_0000002485239892)**  

-   **[BatchNormalization](#ZH-CN_TOPIC_0000002487717084)**  

-   **[LayerNormalization](#ZH-CN_TOPIC_0000002519876961)**  

-   **[LpNormalization](#ZH-CN_TOPIC_0000002519796953)**  

-   **[Slice](#ZH-CN_TOPIC_0000002528453623)**  

-   **[GlobalMaxPool](#ZH-CN_TOPIC_0000002497018654)**  

-   **[GlobalAveragePool](#ZH-CN_TOPIC_0000002496698634)**  

-   **[Transpose](#ZH-CN_TOPIC_0000002498635600)**  

-   **[ArgMax](#ZH-CN_TOPIC_0000002510106182)**  

-   **[ArgMin](#ZH-CN_TOPIC_0000002541586163)**  

-   **[Div](#ZH-CN_TOPIC_0000002516261490)**  

-   **[Mod](#ZH-CN_TOPIC_0000002600000004)**  

-   **[Clip](#ZH-CN_TOPIC_0000002552815891)**  

-   **[ReduceMax](#ZH-CN_TOPIC_0000002557401349)**  

-   **[ReduceMin](#ZH-CN_TOPIC_0000002526441430)**  

-   **[ReduceSum](#ZH-CN_TOPIC_0000002557481311)**  

-   **[ReduceMean](#ZH-CN_TOPIC_0000002526281478)**  

-   **[ReduceL1](#ZH-CN_TOPIC_0000002600000005)**  

-   **[ReduceL2](#ZH-CN_TOPIC_0000002600000006)**  

-   **[Cast](#ZH-CN_TOPIC_0000002526464964)**  

-   **[PRelu](#ZH-CN_TOPIC_0000002568693026)**  

-   **[CumSum](#ZH-CN_TOPIC_0000002568533372)**  

-   **[ReverseSequence](#ZH-CN_TOPIC_0000002599187805)**  

-   **[Einsum](#ZH-CN_TOPIC_0000002599307751)**  

-   **[LeakyRelu](#ZH-CN_TOPIC_0000002574170496)**  

-   **[HardSwish](#ZH-CN_TOPIC_0000002574469146)**  

-   **[Swish](#ZH-CN_TOPIC_0000002605108551)**  

-   **[And](#ZH-CN_TOPIC_0000002574578826)**  

-   **[Equal](#ZH-CN_TOPIC_0000002605257907)**  

-   **[GreaterOrEqual](#ZH-CN_TOPIC_0000002605377849)**  

-   **[Greater](#ZH-CN_TOPIC_0000002574738452)**  

-   **[LessOrEqual](#ZH-CN_TOPIC_0000002574578828)**  

-   **[Less](#ZH-CN_TOPIC_0000002605257909)**  

-   **[Not](#ZH-CN_TOPIC_0000002605377851)**  

-   **[Or](#ZH-CN_TOPIC_0000002574738488)**  

-   **[Xor](#ZH-CN_TOPIC_0000002574578874)**  

-   **[Dropout](#ZH-CN_TOPIC_0000002659215655)**  

-   **[Identity](#ZH-CN_TOPIC_0000002628696446)**  

-   **[GatherElements](#ZH-CN_TOPIC_0000002659095703)**  

-   **[ReduceLogSum](#ZH-CN_TOPIC_0000002628856352)**  

-   **[ReduceLogSumExp](#ZH-CN_TOPIC_0000002659215657)**  

-   **[Expand](#ZH-CN_TOPIC_0000002628696448)**  

-   **[Elu](#ZH-CN_TOPIC_0000002660394575)**  

-   **[DepthToSpace](#ZH-CN_TOPIC_0000002629955352)**  

-   **[SpaceToDepth](#ZH-CN_TOPIC_0000002660274511)**  

-   **[GRU](#ZH-CN_TOPIC_0000002631448488)** 

-   **[Gelu](#ZH-CN_TOPIC_0000002661401194)**  

-   **[Trilu](#ZH-CN_TOPIC_0000002661401195)**  

-   **[Neg](#ZH-CN_TOPIC_0000002900000002)**  

-   **[Pow](#ZH-CN_TOPIC_0000002476598371)**  

-   **[Shape](#ZH-CN_TOPIC_0000003030115802)**  

-   **[MatMulInteger](#ZH-CN_TOPIC_0000003040115702)**  

-   **[TopK](#ZH-CN_TOPIC_0000003050115802)**  

-   **[Erf](#ZH-CN_TOPIC_0000002026072801)**  

-   **[HardSigmoid](#ZH-CN_TOPIC_0000002026072802)**  

-   **[Celu](#ZH-CN_TOPIC_0000002026072803)**  

### Conv<a name="ZH-CN_TOPIC_0000002326152940" id="ZH-CN_TOPIC_0000002326152940"></a>

**功能描述<a name="section113841812134710"></a>**

基于一个filter模板对3D或4D输入进行卷积计算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Conv参数概览

<a name="table189651429122117"></a>
<table><thead align="left"><tr id="row1496911294216"><th class="cellrowborder" valign="top" width="17.33346669333867%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.922584516903383%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.252850570114022%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.96599319863973%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.5251050210042%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row4970192982114"><td class="cellrowborder" valign="top" width="17.33346669333867%" headers="mcps1.2.6.1.1 "><p id="p1477616583269"><a name="p1477616583269"></a><a name="p1477616583269"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="12.922584516903383%" headers="mcps1.2.6.1.2 "><p id="p2776155811264"><a name="p2776155811264"></a><a name="p2776155811264"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.252850570114022%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.96599319863973%" headers="mcps1.2.6.1.4 "><p id="p5776175813266"><a name="p5776175813266"></a><a name="p5776175813266"></a>输入张量，维度为3D或4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.5251050210042%" headers="mcps1.2.6.1.5 "><p id="p1947857133216"><a name="p1947857133216"></a><a name="p1947857133216"></a>-</p>
</td>
</tr>
<tr id="row13970202992119"><td class="cellrowborder" valign="top" width="17.33346669333867%" headers="mcps1.2.6.1.1 "><p id="p18776135802612"><a name="p18776135802612"></a><a name="p18776135802612"></a>W</p>
</td>
<td class="cellrowborder" valign="top" width="12.922584516903383%" headers="mcps1.2.6.1.2 "><p id="p10776145822620"><a name="p10776145822620"></a><a name="p10776145822620"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.252850570114022%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.96599319863973%" headers="mcps1.2.6.1.4 "><p id="p1577675813263"><a name="p1577675813263"></a><a name="p1577675813263"></a>权重张量，维度为3D或4D。</p>
</td>
<td class="cellrowborder" valign="top" width="25.5251050210042%" headers="mcps1.2.6.1.5 "><p id="p1886016418364"><a name="p1886016418364"></a><a name="p1886016418364"></a>规格约束：权重为离线常量</p>
</td>
</tr>
<tr id="row69711129152113"><td class="cellrowborder" valign="top" width="17.33346669333867%" headers="mcps1.2.6.1.1 "><p id="p677611585261"><a name="p677611585261"></a><a name="p677611585261"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="12.922584516903383%" headers="mcps1.2.6.1.2 "><p id="p977617585262"><a name="p977617585262"></a><a name="p977617585262"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.252850570114022%" headers="mcps1.2.6.1.3 "><p id="p11776358112614"><a name="p11776358112614"></a><a name="p11776358112614"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.96599319863973%" headers="mcps1.2.6.1.4 "><p id="p1777613587268"><a name="p1777613587268"></a><a name="p1777613587268"></a>偏置张量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="25.5251050210042%" headers="mcps1.2.6.1.5 "><p id="p055215412145"><a name="p055215412145"></a><a name="p055215412145"></a>规格约束：偏置为离线常量</p>
</td>
</tr>
<tr id="row6971132912215"><td class="cellrowborder" valign="top" width="17.33346669333867%" headers="mcps1.2.6.1.1 "><p id="p19727413172119"><a name="p19727413172119"></a><a name="p19727413172119"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="12.922584516903383%" headers="mcps1.2.6.1.2 "><p id="p107261213152117"><a name="p107261213152117"></a><a name="p107261213152117"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.252850570114022%" headers="mcps1.2.6.1.3 "><p id="p67261313102115"><a name="p67261313102115"></a><a name="p67261313102115"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.96599319863973%" headers="mcps1.2.6.1.4 "><p id="p57261613112110"><a name="p57261613112110"></a><a name="p57261613112110"></a>输出张量，维度为3D或4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.5251050210042%" headers="mcps1.2.6.1.5 "><p id="p12121758258"><a name="p12121758258"></a><a name="p12121758258"></a>-</p>
</td>
</tr>
<tr id="row15971102915211"><td class="cellrowborder" valign="top" width="17.33346669333867%" headers="mcps1.2.6.1.1 "><p id="p177765587262"><a name="p177765587262"></a><a name="p177765587262"></a>auto_pad</p>
</td>
<td class="cellrowborder" valign="top" width="12.922584516903383%" headers="mcps1.2.6.1.2 "><p id="p1877665814265"><a name="p1877665814265"></a><a name="p1877665814265"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.252850570114022%" headers="mcps1.2.6.1.3 "><p id="p777610581262"><a name="p777610581262"></a><a name="p777610581262"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="29.96599319863973%" headers="mcps1.2.6.1.4 "><p id="p1577685818263"><a name="p1577685818263"></a><a name="p1577685818263"></a>指定padding的类型。</p>
</td>
<td class="cellrowborder" valign="top" width="25.5251050210042%" headers="mcps1.2.6.1.5 "><p id="p14897185443916"><a name="p14897185443916"></a><a name="p14897185443916"></a>规格约束：仅支持NOTSET</p>
</td>
</tr>
<tr id="row199721829122118"><td class="cellrowborder" valign="top" width="17.33346669333867%" headers="mcps1.2.6.1.1 "><p id="p147769587262"><a name="p147769587262"></a><a name="p147769587262"></a>dilations</p>
</td>
<td class="cellrowborder" valign="top" width="12.922584516903383%" headers="mcps1.2.6.1.2 "><p id="p15776958132619"><a name="p15776958132619"></a><a name="p15776958132619"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.252850570114022%" headers="mcps1.2.6.1.3 "><p id="p877612584267"><a name="p877612584267"></a><a name="p877612584267"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="29.96599319863973%" headers="mcps1.2.6.1.4 "><p id="p3776105813265"><a name="p3776105813265"></a><a name="p3776105813265"></a>每个轴上的扩张系数。</p>
</td>
<td class="cellrowborder" valign="top" width="25.5251050210042%" headers="mcps1.2.6.1.5 "><p id="p133481431132514"><a name="p133481431132514"></a><a name="p133481431132514"></a>-</p>
</td>
</tr>
<tr id="row179724291210"><td class="cellrowborder" valign="top" width="17.33346669333867%" headers="mcps1.2.6.1.1 "><p id="p577613585260"><a name="p577613585260"></a><a name="p577613585260"></a>group</p>
</td>
<td class="cellrowborder" valign="top" width="12.922584516903383%" headers="mcps1.2.6.1.2 "><p id="p577715832617"><a name="p577715832617"></a><a name="p577715832617"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.252850570114022%" headers="mcps1.2.6.1.3 "><p id="p18777658172610"><a name="p18777658172610"></a><a name="p18777658172610"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.96599319863973%" headers="mcps1.2.6.1.4 "><p id="p038543712304"><a name="p038543712304"></a><a name="p038543712304"></a>在输入输出channel上划分的分组个数。</p>
</td>
<td class="cellrowborder" valign="top" width="25.5251050210042%" headers="mcps1.2.6.1.5 "><p id="p1459552217255"><a name="p1459552217255"></a><a name="p1459552217255"></a>规格约束：仅支持输入为1的情况</p>
</td>
</tr>
<tr id="row13973529102110"><td class="cellrowborder" valign="top" width="17.33346669333867%" headers="mcps1.2.6.1.1 "><p id="p177785819261"><a name="p177785819261"></a><a name="p177785819261"></a>kernel_shape</p>
</td>
<td class="cellrowborder" valign="top" width="12.922584516903383%" headers="mcps1.2.6.1.2 "><p id="p977718586269"><a name="p977718586269"></a><a name="p977718586269"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.252850570114022%" headers="mcps1.2.6.1.3 "><p id="p17777145822614"><a name="p17777145822614"></a><a name="p17777145822614"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="29.96599319863973%" headers="mcps1.2.6.1.4 "><p id="p1011953613513"><a name="p1011953613513"></a><a name="p1011953613513"></a>kernel沿各轴的大小。</p>
</td>
<td class="cellrowborder" valign="top" width="25.5251050210042%" headers="mcps1.2.6.1.5 "><p id="p5119025112510"><a name="p5119025112510"></a><a name="p5119025112510"></a>-</p>
</td>
</tr>
<tr id="row19973129102114"><td class="cellrowborder" valign="top" width="17.33346669333867%" headers="mcps1.2.6.1.1 "><p id="p1414571372710"><a name="p1414571372710"></a><a name="p1414571372710"></a>pads</p>
</td>
<td class="cellrowborder" valign="top" width="12.922584516903383%" headers="mcps1.2.6.1.2 "><p id="p614519131277"><a name="p614519131277"></a><a name="p614519131277"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.252850570114022%" headers="mcps1.2.6.1.3 "><p id="p16338550143115"><a name="p16338550143115"></a><a name="p16338550143115"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="29.96599319863973%" headers="mcps1.2.6.1.4 "><p id="p85157422328"><a name="p85157422328"></a><a name="p85157422328"></a>各轴前后填充零的个数。</p>
</td>
<td class="cellrowborder" valign="top" width="25.5251050210042%" headers="mcps1.2.6.1.5 "><p id="p11118122518259"><a name="p11118122518259"></a><a name="p11118122518259"></a>-</p>
</td>
</tr>
<tr id="row48490213206"><td class="cellrowborder" valign="top" width="17.33346669333867%" headers="mcps1.2.6.1.1 "><p id="p1851524472710"><a name="p1851524472710"></a><a name="p1851524472710"></a>strides</p>
</td>
<td class="cellrowborder" valign="top" width="12.922584516903383%" headers="mcps1.2.6.1.2 "><p id="p1451574413278"><a name="p1451574413278"></a><a name="p1451574413278"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.252850570114022%" headers="mcps1.2.6.1.3 "><p id="p2077235113117"><a name="p2077235113117"></a><a name="p2077235113117"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="29.96599319863973%" headers="mcps1.2.6.1.4 "><p id="p18216141324"><a name="p18216141324"></a><a name="p18216141324"></a>各个方向上kernel的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="25.5251050210042%" headers="mcps1.2.6.1.5 "><p id="p121181125172518"><a name="p121181125172518"></a><a name="p121181125172518"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 要求使用静态形状；仅对可微输入和可训练权重生成梯度 |
| FP32 | 支持 | 要求使用静态形状；仅对可微输入和可训练权重生成梯度 |

### MaxPool<a name="ZH-CN_TOPIC_0000002325993104" id="ZH-CN_TOPIC_0000002325993104"></a>

**功能描述<a name="section113841812134710"></a>**

对3D或4D输入进行最大池化计算。

**参数说明<a name="section15195134816462"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Maxpool双输出规格暂不支持。

**表 1**  MaxPool参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="17.458254174582542%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.078692130786921%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.878612138786123%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.186981301869814%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.3974602539746%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="17.458254174582542%" headers="mcps1.2.6.1.1 "><p id="p814484714519"><a name="p814484714519"></a><a name="p814484714519"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="13.078692130786921%" headers="mcps1.2.6.1.2 "><p id="p16144114785114"><a name="p16144114785114"></a><a name="p16144114785114"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.878612138786123%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.186981301869814%" headers="mcps1.2.6.1.4 "><p id="p5776175813266"><a name="p5776175813266"></a><a name="p5776175813266"></a>输入张量，维度为3D或4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.3974602539746%" headers="mcps1.2.6.1.5 "><p id="p18848151322319"><a name="p18848151322319"></a><a name="p18848151322319"></a>-</p>
</td>
</tr>
<tr id="row15423221105011"><td class="cellrowborder" valign="top" width="17.458254174582542%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="13.078692130786921%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.878612138786123%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.186981301869814%" headers="mcps1.2.6.1.4 "><p id="p57261613112110"><a name="p57261613112110"></a><a name="p57261613112110"></a>输出张量，维度为3D或4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.3974602539746%" headers="mcps1.2.6.1.5 "><p id="p6847131316239"><a name="p6847131316239"></a><a name="p6847131316239"></a>-</p>
</td>
</tr>
<tr id="row2423132175015"><td class="cellrowborder" valign="top" width="17.458254174582542%" headers="mcps1.2.6.1.1 "><p id="p211803695110"><a name="p211803695110"></a><a name="p211803695110"></a>auto_pad</p>
</td>
<td class="cellrowborder" valign="top" width="13.078692130786921%" headers="mcps1.2.6.1.2 "><p id="p4118173613511"><a name="p4118173613511"></a><a name="p4118173613511"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.878612138786123%" headers="mcps1.2.6.1.3 "><p id="p71181836115119"><a name="p71181836115119"></a><a name="p71181836115119"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.186981301869814%" headers="mcps1.2.6.1.4 "><p id="p1577685818263"><a name="p1577685818263"></a><a name="p1577685818263"></a>指定padding的类型。</p>
</td>
<td class="cellrowborder" valign="top" width="25.3974602539746%" headers="mcps1.2.6.1.5 "><p id="p14897185443916"><a name="p14897185443916"></a><a name="p14897185443916"></a>配置范围：NOTSET、SAME_UPPER、SAME_LOWER、VALID</p>
</td>
</tr>
<tr id="row9424122145019"><td class="cellrowborder" valign="top" width="17.458254174582542%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>ceil_mode</p>
</td>
<td class="cellrowborder" valign="top" width="13.078692130786921%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.878612138786123%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="30.186981301869814%" headers="mcps1.2.6.1.4 "><p id="p1351318783714"><a name="p1351318783714"></a><a name="p1351318783714"></a>输出形状的取整方式。</p>
</td>
<td class="cellrowborder" valign="top" width="25.3974602539746%" headers="mcps1.2.6.1.5 "><p id="p10748523112318"><a name="p10748523112318"></a><a name="p10748523112318"></a>规格约束：仅支持floor</p>
</td>
</tr>
<tr id="row19424152111505"><td class="cellrowborder" valign="top" width="17.458254174582542%" headers="mcps1.2.6.1.1 "><p id="p211883675111"><a name="p211883675111"></a><a name="p211883675111"></a>dilations</p>
</td>
<td class="cellrowborder" valign="top" width="13.078692130786921%" headers="mcps1.2.6.1.2 "><p id="p811833615513"><a name="p811833615513"></a><a name="p811833615513"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.878612138786123%" headers="mcps1.2.6.1.3 "><p id="p17777145822614"><a name="p17777145822614"></a><a name="p17777145822614"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.186981301869814%" headers="mcps1.2.6.1.4 "><p id="p3776105813265"><a name="p3776105813265"></a><a name="p3776105813265"></a>每个轴上的扩张系数。</p>
</td>
<td class="cellrowborder" valign="top" width="25.3974602539746%" headers="mcps1.2.6.1.5 "><p id="p147561323132312"><a name="p147561323132312"></a><a name="p147561323132312"></a>规格约束：仅支持1</p>
</td>
</tr>
<tr id="row1242515218501"><td class="cellrowborder" valign="top" width="17.458254174582542%" headers="mcps1.2.6.1.1 "><p id="p611873695118"><a name="p611873695118"></a><a name="p611873695118"></a>kernel_shape</p>
</td>
<td class="cellrowborder" valign="top" width="13.078692130786921%" headers="mcps1.2.6.1.2 "><p id="p6118173618512"><a name="p6118173618512"></a><a name="p6118173618512"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.878612138786123%" headers="mcps1.2.6.1.3 "><p id="p1837728133615"><a name="p1837728133615"></a><a name="p1837728133615"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.186981301869814%" headers="mcps1.2.6.1.4 "><p id="p1011953613513"><a name="p1011953613513"></a><a name="p1011953613513"></a>kernel沿各轴的大小。</p>
</td>
<td class="cellrowborder" valign="top" width="25.3974602539746%" headers="mcps1.2.6.1.5 "><p id="p208161758122315"><a name="p208161758122315"></a><a name="p208161758122315"></a>-</p>
</td>
</tr>
<tr id="row1142582117505"><td class="cellrowborder" valign="top" width="17.458254174582542%" headers="mcps1.2.6.1.1 "><p id="p41191436195118"><a name="p41191436195118"></a><a name="p41191436195118"></a>pads</p>
</td>
<td class="cellrowborder" valign="top" width="13.078692130786921%" headers="mcps1.2.6.1.2 "><p id="p101191368518"><a name="p101191368518"></a><a name="p101191368518"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.878612138786123%" headers="mcps1.2.6.1.3 "><p id="p189871429153615"><a name="p189871429153615"></a><a name="p189871429153615"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.186981301869814%" headers="mcps1.2.6.1.4 "><p id="p85157422328"><a name="p85157422328"></a><a name="p85157422328"></a>各轴前后填充零的个数。</p>
</td>
<td class="cellrowborder" valign="top" width="25.3974602539746%" headers="mcps1.2.6.1.5 "><p id="p68151858122318"><a name="p68151858122318"></a><a name="p68151858122318"></a>-</p>
</td>
</tr>
<tr id="row1742542125016"><td class="cellrowborder" valign="top" width="17.458254174582542%" headers="mcps1.2.6.1.1 "><p id="p11119123645111"><a name="p11119123645111"></a><a name="p11119123645111"></a>storage_order</p>
</td>
<td class="cellrowborder" valign="top" width="13.078692130786921%" headers="mcps1.2.6.1.2 "><p id="p3119183675110"><a name="p3119183675110"></a><a name="p3119183675110"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.878612138786123%" headers="mcps1.2.6.1.3 "><p id="p141191136145117"><a name="p141191136145117"></a><a name="p141191136145117"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="30.186981301869814%" headers="mcps1.2.6.1.4 "><p id="p7517113815389"><a name="p7517113815389"></a><a name="p7517113815389"></a>张量存储主序。</p>
</td>
<td class="cellrowborder" valign="top" width="25.3974602539746%" headers="mcps1.2.6.1.5 "><p id="p218945214234"><a name="p218945214234"></a><a name="p218945214234"></a>规格约束：仅支持0</p>
</td>
</tr>
<tr id="row1387274316020"><td class="cellrowborder" valign="top" width="17.458254174582542%" headers="mcps1.2.6.1.1 "><p id="p17121123613512"><a name="p17121123613512"></a><a name="p17121123613512"></a>strides</p>
</td>
<td class="cellrowborder" valign="top" width="13.078692130786921%" headers="mcps1.2.6.1.2 "><p id="p14121123611515"><a name="p14121123611515"></a><a name="p14121123611515"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.878612138786123%" headers="mcps1.2.6.1.3 "><p id="p1270517343361"><a name="p1270517343361"></a><a name="p1270517343361"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.186981301869814%" headers="mcps1.2.6.1.4 "><p id="p18216141324"><a name="p18216141324"></a><a name="p18216141324"></a>各个方向上kernel的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="25.3974602539746%" headers="mcps1.2.6.1.5 "><p id="p3933556122319"><a name="p3933556122319"></a><a name="p3933556122319"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 仅支持MaxPool，输入和输出均为四维量化张量 |
| FP32 | 不支持 | - |

### Gemm<a name="ZH-CN_TOPIC_0000002360071441" id="ZH-CN_TOPIC_0000002360071441"></a>

**功能描述<a name="section113841812134710"></a>**

对两个2D张量进行矩阵乘积运算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Gemm参数概览

<a name="table439841210111"></a>
<table><thead align="left"><tr id="row163989125117"><th class="cellrowborder" valign="top" width="16.78%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.919999999999998%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.030000000000001%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.240000000000002%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.03%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row3313125816711"><td class="cellrowborder" valign="top" width="16.78%" headers="mcps1.2.6.1.1 "><p id="p103983121012"><a name="p103983121012"></a><a name="p103983121012"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="13.919999999999998%" headers="mcps1.2.6.1.2 "><p id="p139812121213"><a name="p139812121213"></a><a name="p139812121213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.030000000000001%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.240000000000002%" headers="mcps1.2.6.1.4 "><p id="p1039831214110"><a name="p1039831214110"></a><a name="p1039831214110"></a>输入张量，维度为2D，格式为ND。</p>
</td>
<td class="cellrowborder" valign="top" width="25.03%" headers="mcps1.2.6.1.5 "><p id="p2877368212"><a name="p2877368212"></a><a name="p2877368212"></a>-</p>
</td>
</tr>
<tr id="row17827105518718"><td class="cellrowborder" valign="top" width="16.78%" headers="mcps1.2.6.1.1 "><p id="p14399111216119"><a name="p14399111216119"></a><a name="p14399111216119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="13.919999999999998%" headers="mcps1.2.6.1.2 "><p id="p73991412910"><a name="p73991412910"></a><a name="p73991412910"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.030000000000001%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.240000000000002%" headers="mcps1.2.6.1.4 "><p id="p20860222122017"><a name="p20860222122017"></a><a name="p20860222122017"></a>权重张量，维度为2D。</p>
</td>
<td class="cellrowborder" valign="top" width="25.03%" headers="mcps1.2.6.1.5 "><p id="p8875567211"><a name="p8875567211"></a><a name="p8875567211"></a>规格约束：仅支持离线变量</p>
</td>
</tr>
<tr id="row174235315712"><td class="cellrowborder" valign="top" width="16.78%" headers="mcps1.2.6.1.1 "><p id="p639913125119"><a name="p639913125119"></a><a name="p639913125119"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="13.919999999999998%" headers="mcps1.2.6.1.2 "><p id="p639920123113"><a name="p639920123113"></a><a name="p639920123113"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.030000000000001%" headers="mcps1.2.6.1.3 "><p id="p14476173516477"><a name="p14476173516477"></a><a name="p14476173516477"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.240000000000002%" headers="mcps1.2.6.1.4 "><p id="p639917121713"><a name="p639917121713"></a><a name="p639917121713"></a>偏置张量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="25.03%" headers="mcps1.2.6.1.5 "><p id="p108757615216"><a name="p108757615216"></a><a name="p108757615216"></a>规格约束：仅支持离线变量</p>
</td>
</tr>
<tr id="row177177511714"><td class="cellrowborder" valign="top" width="16.78%" headers="mcps1.2.6.1.1 "><p id="p75541850190"><a name="p75541850190"></a><a name="p75541850190"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="13.919999999999998%" headers="mcps1.2.6.1.2 "><p id="p655417501497"><a name="p655417501497"></a><a name="p655417501497"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.030000000000001%" headers="mcps1.2.6.1.3 "><p id="p1447613357472"><a name="p1447613357472"></a><a name="p1447613357472"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.240000000000002%" headers="mcps1.2.6.1.4 "><p id="p155541650997"><a name="p155541650997"></a><a name="p155541650997"></a>输出张量，维度为2D，格式为ND。</p>
</td>
<td class="cellrowborder" valign="top" width="25.03%" headers="mcps1.2.6.1.5 "><p id="p987496132113"><a name="p987496132113"></a><a name="p987496132113"></a>-</p>
</td>
</tr>
<tr id="row16398161215117"><td class="cellrowborder" valign="top" width="16.78%" headers="mcps1.2.6.1.1 "><p id="p1254114101281"><a name="p1254114101281"></a><a name="p1254114101281"></a>alpha</p>
</td>
<td class="cellrowborder" valign="top" width="13.919999999999998%" headers="mcps1.2.6.1.2 "><p id="p25419101988"><a name="p25419101988"></a><a name="p25419101988"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.030000000000001%" headers="mcps1.2.6.1.3 "><p id="p954191019819"><a name="p954191019819"></a><a name="p954191019819"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="30.240000000000002%" headers="mcps1.2.6.1.4 "><p id="p1631314581473"><a name="p1631314581473"></a><a name="p1631314581473"></a>A×B张量的缩放系数。</p>
</td>
<td class="cellrowborder" valign="top" width="25.03%" headers="mcps1.2.6.1.5 "><p id="p205798531213"><a name="p205798531213"></a><a name="p205798531213"></a>规格约束：仅支持1.0</p>
</td>
</tr>
<tr id="row1739810121114"><td class="cellrowborder" valign="top" width="16.78%" headers="mcps1.2.6.1.1 "><p id="p141832350812"><a name="p141832350812"></a><a name="p141832350812"></a>beta</p>
</td>
<td class="cellrowborder" valign="top" width="13.919999999999998%" headers="mcps1.2.6.1.2 "><p id="p1718316351819"><a name="p1718316351819"></a><a name="p1718316351819"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.030000000000001%" headers="mcps1.2.6.1.3 "><p id="p61831351586"><a name="p61831351586"></a><a name="p61831351586"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="30.240000000000002%" headers="mcps1.2.6.1.4 "><p id="p518318359813"><a name="p518318359813"></a><a name="p518318359813"></a>C的乘数。</p>
</td>
<td class="cellrowborder" valign="top" width="25.03%" headers="mcps1.2.6.1.5 "><p id="p87252520109"><a name="p87252520109"></a><a name="p87252520109"></a>规格约束：仅支持0.0</p>
</td>
</tr>
<tr id="row839917121811"><td class="cellrowborder" valign="top" width="16.78%" headers="mcps1.2.6.1.1 "><p id="p16966343883"><a name="p16966343883"></a><a name="p16966343883"></a>transA</p>
</td>
<td class="cellrowborder" valign="top" width="13.919999999999998%" headers="mcps1.2.6.1.2 "><p id="p39663431381"><a name="p39663431381"></a><a name="p39663431381"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.030000000000001%" headers="mcps1.2.6.1.3 "><p id="p496634317816"><a name="p496634317816"></a><a name="p496634317816"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="30.240000000000002%" headers="mcps1.2.6.1.4 "><p id="p796674319812"><a name="p796674319812"></a><a name="p796674319812"></a>决定输入A是否转置。</p>
</td>
<td class="cellrowborder" valign="top" width="25.03%" headers="mcps1.2.6.1.5 "><p id="p9231102162112"><a name="p9231102162112"></a><a name="p9231102162112"></a>配置范围：0、1</p>
</td>
</tr>
<tr id="row1055318501099"><td class="cellrowborder" valign="top" width="16.78%" headers="mcps1.2.6.1.1 "><p id="p349564916814"><a name="p349564916814"></a><a name="p349564916814"></a>transB</p>
</td>
<td class="cellrowborder" valign="top" width="13.919999999999998%" headers="mcps1.2.6.1.2 "><p id="p44954491885"><a name="p44954491885"></a><a name="p44954491885"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.030000000000001%" headers="mcps1.2.6.1.3 "><p id="p114951249283"><a name="p114951249283"></a><a name="p114951249283"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="30.240000000000002%" headers="mcps1.2.6.1.4 "><p id="p18495184913816"><a name="p18495184913816"></a><a name="p18495184913816"></a>决定输入B是否转置。</p>
</td>
<td class="cellrowborder" valign="top" width="25.03%" headers="mcps1.2.6.1.5 "><p id="p6512935202111"><a name="p6512935202111"></a><a name="p6512935202111"></a>配置范围：0、1</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 要求使用静态形状；仅对可微输入和可训练权重生成梯度 |
| FP32 | 支持 | 要求使用静态形状；仅对可微输入和可训练权重生成梯度 |

### Matmul<a name="ZH-CN_TOPIC_0000002455345333" id="ZH-CN_TOPIC_0000002455345333"></a>

**功能描述<a name="section113841812134710"></a>**

对两个2D/3D/4D张量进行矩阵乘积运算。

**参数说明<a name="section15195134816462"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Matmul不支持广播场景。

**表 1**  Matmul参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="16.88%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.900000000000002%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.750000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.740000000000002%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="16.88%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="13.900000000000002%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.750000000000002%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.73%" headers="mcps1.2.6.1.4 "><p id="p11673723615"><a name="p11673723615"></a><a name="p11673723615"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.740000000000002%" headers="mcps1.2.6.1.5 "><p id="p1281118459199"><a name="p1281118459199"></a><a name="p1281118459199"></a>-</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="16.88%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="13.900000000000002%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.750000000000002%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.73%" headers="mcps1.2.6.1.4 "><p id="p1517530111819"><a name="p1517530111819"></a><a name="p1517530111819"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.740000000000002%" headers="mcps1.2.6.1.5 "><p id="p128111545121916"><a name="p128111545121916"></a><a name="p128111545121916"></a>-</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="16.88%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="13.900000000000002%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.750000000000002%" headers="mcps1.2.6.1.3 "><p id="p14476173516477"><a name="p14476173516477"></a><a name="p14476173516477"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.740000000000002%" headers="mcps1.2.6.1.5 "><p id="p12810164591917"><a name="p12810164591917"></a><a name="p12810164591917"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 要求使用静态形状；仅对可微输入和可训练权重生成梯度 |
| FP32 | 支持 | 要求使用静态形状；仅对可微输入和可训练权重生成梯度 |

### Softmax<a name="ZH-CN_TOPIC_0000002360191597" id="ZH-CN_TOPIC_0000002360191597"></a>

**功能描述<a name="section37550136507"></a>**

计算指定维度的归一化Softmax概率分布。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>当Softmax维度较大时，int8量化损失较大，推荐使用fp32模式的算子，关闭cfg中的enable\_all\_ops选项（仅保留矩阵运算类算子的量化）。

**表 1**  Softmax参数概览

<a name="table11657133510577"></a>
<table><thead align="left"><tr id="row4659835175719"><th class="cellrowborder" valign="top" width="16.92169216921692%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.161416141614161%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.711371137113712%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.533053305330533%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.672467246724672%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row1765918354578"><td class="cellrowborder" valign="top" width="16.92169216921692%" headers="mcps1.2.6.1.1 "><p id="p174143115814"><a name="p174143115814"></a><a name="p174143115814"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.161416141614161%" headers="mcps1.2.6.1.2 "><p id="p194638583"><a name="p194638583"></a><a name="p194638583"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.711371137113712%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.533053305330533%" headers="mcps1.2.6.1.4 "><p id="p11673723615"><a name="p11673723615"></a><a name="p11673723615"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.672467246724672%" headers="mcps1.2.6.1.5 "><p id="p89391247161815"><a name="p89391247161815"></a><a name="p89391247161815"></a>-</p>
</td>
</tr>
<tr id="row66596352573"><td class="cellrowborder" valign="top" width="16.92169216921692%" headers="mcps1.2.6.1.1 "><p id="p138121843173014"><a name="p138121843173014"></a><a name="p138121843173014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.161416141614161%" headers="mcps1.2.6.1.2 "><p id="p8812154310307"><a name="p8812154310307"></a><a name="p8812154310307"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.711371137113712%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.533053305330533%" headers="mcps1.2.6.1.4 "><p id="p1517530111819"><a name="p1517530111819"></a><a name="p1517530111819"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.672467246724672%" headers="mcps1.2.6.1.5 "><p id="p1265905012184"><a name="p1265905012184"></a><a name="p1265905012184"></a>-</p>
</td>
</tr>
<tr id="row781184313010"><td class="cellrowborder" valign="top" width="16.92169216921692%" headers="mcps1.2.6.1.1 "><p id="p9433105818"><a name="p9433105818"></a><a name="p9433105818"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="14.161416141614161%" headers="mcps1.2.6.1.2 "><p id="p204143155816"><a name="p204143155816"></a><a name="p204143155816"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.711371137113712%" headers="mcps1.2.6.1.3 "><p id="p1147312584"><a name="p1147312584"></a><a name="p1147312584"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="30.533053305330533%" headers="mcps1.2.6.1.4 "><p id="p108197531101"><a name="p108197531101"></a><a name="p108197531101"></a>Softmax的计算轴。</p>
</td>
<td class="cellrowborder" valign="top" width="24.672467246724672%" headers="mcps1.2.6.1.5 "><p id="p1525013286014"><a name="p1525013286014"></a><a name="p1525013286014"></a>-rank(input)<=axis<rank(input)，rank为张量的秩</p>
</td>
</tr>
</tbody>
</table>

### Relu<a name="ZH-CN_TOPIC_0000002326152944" id="ZH-CN_TOPIC_0000002326152944"></a>

**功能描述<a name="section113841812134710"></a>**

对输入张量做Relu激活函数运算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Relu参数概览

<a name="table1033212264218"></a>
<table><thead align="left"><tr id="row133331626923"><th class="cellrowborder" valign="top" width="16.619999999999997%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.56%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.889999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.320000000000004%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.610000000000003%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row14333926224"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p1790719584217"><a name="p1790719584217"></a><a name="p1790719584217"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p199084588217"><a name="p199084588217"></a><a name="p199084588217"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p11673723615"><a name="p11673723615"></a><a name="p11673723615"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCL/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p035182116187"><a name="p035182116187"></a><a name="p035182116187"></a>-</p>
</td>
</tr>
<tr id="row9388316349"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p193881514347"><a name="p193881514347"></a><a name="p193881514347"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p163881913346"><a name="p163881913346"></a><a name="p163881913346"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p1517530111819"><a name="p1517530111819"></a><a name="p1517530111819"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p18351172171817"><a name="p18351172171817"></a><a name="p18351172171817"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 当前Activation训练反向仅支持ReLU |
| FP32 | 支持 | 当前Activation训练反向仅支持ReLU |

### Tanh<a name="ZH-CN_TOPIC_0000002474764481" id="ZH-CN_TOPIC_0000002474764481"></a>

**功能描述<a name="section113841812134710"></a>**

对输入张量做Tanh激活函数运算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Tanh参数概览

<a name="table1033212264218"></a>
<table><thead align="left"><tr id="row133331626923"><th class="cellrowborder" valign="top" width="16.85%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.23%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.330000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.240000000000002%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.349999999999998%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row14333926224"><td class="cellrowborder" valign="top" width="16.85%" headers="mcps1.2.6.1.1 "><p id="p1790719584217"><a name="p1790719584217"></a><a name="p1790719584217"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="14.23%" headers="mcps1.2.6.1.2 "><p id="p199084588217"><a name="p199084588217"></a><a name="p199084588217"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.330000000000002%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.240000000000002%" headers="mcps1.2.6.1.4 "><p id="p11673723615"><a name="p11673723615"></a><a name="p11673723615"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.349999999999998%" headers="mcps1.2.6.1.5 "><p id="p035182116187"><a name="p035182116187"></a><a name="p035182116187"></a>-</p>
</td>
</tr>
<tr id="row9388316349"><td class="cellrowborder" valign="top" width="16.85%" headers="mcps1.2.6.1.1 "><p id="p193881514347"><a name="p193881514347"></a><a name="p193881514347"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="14.23%" headers="mcps1.2.6.1.2 "><p id="p163881913346"><a name="p163881913346"></a><a name="p163881913346"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.330000000000002%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.240000000000002%" headers="mcps1.2.6.1.4 "><p id="p1517530111819"><a name="p1517530111819"></a><a name="p1517530111819"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.349999999999998%" headers="mcps1.2.6.1.5 "><p id="p18351172171817"><a name="p18351172171817"></a><a name="p18351172171817"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Sigmoid<a name="ZH-CN_TOPIC_0000002441564330" id="ZH-CN_TOPIC_0000002441564330"></a>

**功能描述<a name="section113841812134710"></a>**

对输入张量做Sigmoid激活函数运算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Sigmoid参数概览

<a name="table1033212264218"></a>
<table><thead align="left"><tr id="row133331626923"><th class="cellrowborder" valign="top" width="16.850000000000005%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.120000000000003%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.500000000000002%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.810000000000002%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.720000000000002%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row14333926224"><td class="cellrowborder" valign="top" width="16.850000000000005%" headers="mcps1.2.6.1.1 "><p id="p1790719584217"><a name="p1790719584217"></a><a name="p1790719584217"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="14.120000000000003%" headers="mcps1.2.6.1.2 "><p id="p199084588217"><a name="p199084588217"></a><a name="p199084588217"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.500000000000002%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.810000000000002%" headers="mcps1.2.6.1.4 "><p id="p11673723615"><a name="p11673723615"></a><a name="p11673723615"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.720000000000002%" headers="mcps1.2.6.1.5 "><p id="p035182116187"><a name="p035182116187"></a><a name="p035182116187"></a>-</p>
</td>
</tr>
<tr id="row9388316349"><td class="cellrowborder" valign="top" width="16.850000000000005%" headers="mcps1.2.6.1.1 "><p id="p193881514347"><a name="p193881514347"></a><a name="p193881514347"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="14.120000000000003%" headers="mcps1.2.6.1.2 "><p id="p163881913346"><a name="p163881913346"></a><a name="p163881913346"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.500000000000002%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.810000000000002%" headers="mcps1.2.6.1.4 "><p id="p1517530111819"><a name="p1517530111819"></a><a name="p1517530111819"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.720000000000002%" headers="mcps1.2.6.1.5 "><p id="p18351172171817"><a name="p18351172171817"></a><a name="p18351172171817"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Reshape<a name="ZH-CN_TOPIC_0000002325993108" id="ZH-CN_TOPIC_0000002325993108"></a>

**功能描述<a name="section37550136507"></a>**

改变Tensor的Shape，但不改变其排布。

**参数说明<a name="section162919203502"></a>**

**表 1**  Reshape参数概览

<a name="table542733973118"></a>
<table><thead align="left"><tr id="row742723916319"><th class="cellrowborder" valign="top" width="17.111711171117115%" id="mcps1.2.6.1.1"><p id="p6427153917312"><a name="p6427153917312"></a><a name="p6427153917312"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.851385138513855%" id="mcps1.2.6.1.2"><p id="p4537611185218"><a name="p4537611185218"></a><a name="p4537611185218"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.651465146514653%" id="mcps1.2.6.1.3"><p id="p1942815397310"><a name="p1942815397310"></a><a name="p1942815397310"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.692969296929693%" id="mcps1.2.6.1.4"><p id="p114282039103112"><a name="p114282039103112"></a><a name="p114282039103112"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.692469246924695%" id="mcps1.2.6.1.5"><p id="p358711825616"><a name="p358711825616"></a><a name="p358711825616"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row11968131541819"><td class="cellrowborder" valign="top" width="17.111711171117115%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.851385138513855%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.651465146514653%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.692969296929693%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NCW、NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.692469246924695%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row93786149424"><td class="cellrowborder" valign="top" width="17.111711171117115%" headers="mcps1.2.6.1.1 "><p id="p15763919174214"><a name="p15763919174214"></a><a name="p15763919174214"></a>shape</p>
</td>
<td class="cellrowborder" valign="top" width="13.851385138513855%" headers="mcps1.2.6.1.2 "><p id="p1876312194423"><a name="p1876312194423"></a><a name="p1876312194423"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.651465146514653%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor (int64)</p>
</td>
<td class="cellrowborder" valign="top" width="29.692969296929693%" headers="mcps1.2.6.1.4 "><p id="p19883459134217"><a name="p19883459134217"></a><a name="p19883459134217"></a>Shape张量，转换后的Shape。</p>
</td>
<td class="cellrowborder" valign="top" width="24.692469246924695%" headers="mcps1.2.6.1.5 "><p id="p97631219114220"><a name="p97631219114220"></a><a name="p97631219114220"></a>所有元素之积与input包含的元素个数相等</p>
</td>
</tr>
<tr id="row131890194187"><td class="cellrowborder" valign="top" width="17.111711171117115%" headers="mcps1.2.6.1.1 "><p id="p0189101910184"><a name="p0189101910184"></a><a name="p0189101910184"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.851385138513855%" headers="mcps1.2.6.1.2 "><p id="p418914198187"><a name="p418914198187"></a><a name="p418914198187"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.651465146514653%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.692969296929693%" headers="mcps1.2.6.1.4 "><p id="p121892195182"><a name="p121892195182"></a><a name="p121892195182"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NCW、NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.692469246924695%" headers="mcps1.2.6.1.5 "><p id="p1118918198181"><a name="p1118918198181"></a><a name="p1118918198181"></a>-</p>
</td>
</tr>
<tr id="row1991465535618"><td class="cellrowborder" valign="top" width="17.111711171117115%" headers="mcps1.2.6.1.1 "><p id="p184517615573"><a name="p184517615573"></a><a name="p184517615573"></a>allowzero</p>
</td>
<td class="cellrowborder" valign="top" width="13.851385138513855%" headers="mcps1.2.6.1.2 "><p id="p1945114655710"><a name="p1945114655710"></a><a name="p1945114655710"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.651465146514653%" headers="mcps1.2.6.1.3 "><p id="p204512066575"><a name="p204512066575"></a><a name="p204512066575"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.692969296929693%" headers="mcps1.2.6.1.4 "><p id="p645116611579"><a name="p645116611579"></a><a name="p645116611579"></a>判断是否对目标形状做适配（默认0）。</p>
</td>
<td class="cellrowborder" valign="top" width="24.692469246924695%" headers="mcps1.2.6.1.5 "><p id="p179151855175614"><a name="p179151855175614"></a><a name="p179151855175614"></a>仅支持0</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 输入和输出元素数量必须一致 |
| FP32 | 支持 | 输入和输出元素数量必须一致 |

### Mul<a name="ZH-CN_TOPIC_0000002455226053" id="ZH-CN_TOPIC_0000002455226053"></a>

**功能描述<a name="section37550136507"></a>**

计算两个矩阵逐点相乘。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Mul支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Mul参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="16.85%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.430000000000001%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.62%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.62%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.48%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="16.85%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.430000000000001%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.62%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.48%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>-</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="16.85%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.430000000000001%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.62%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.48%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>-</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="16.85%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.430000000000001%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.62%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.48%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 支持范围取决于输入角色和广播规格 |

### Add<a name="ZH-CN_TOPIC_0000002454832353" id="ZH-CN_TOPIC_0000002454832353"></a>

**功能描述<a name="section37550136507"></a>**

计算两个矩阵逐点相加。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Add支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Add参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>左输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>-</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>-</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 支持范围取决于输入角色和广播规格 |

### Sub<a name="ZH-CN_TOPIC_0000002454792465" id="ZH-CN_TOPIC_0000002454792465"></a>

**功能描述<a name="section37550136507"></a>**

计算两个矩阵逐点相减。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Sub支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Sub参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="16.520000000000003%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.93%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.229999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.54%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.78%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="16.520000000000003%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.93%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.229999999999999%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.54%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>左输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.78%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>-</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="16.520000000000003%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.93%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.229999999999999%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.54%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.78%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>-</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="16.520000000000003%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.93%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.229999999999999%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.54%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.78%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 支持范围取决于输入角色和广播规格 |

### Gather<a name="ZH-CN_TOPIC_0000002421843980" id="ZH-CN_TOPIC_0000002421843980"></a>

**功能描述<a name="section129901354195417"></a>**

根据指定索引，从输入张量的指定轴上提取元素，组合成新张量。

**参数说明<a name="section162919203502"></a>**

**表 1**  Gather参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="16.35%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.160000000000002%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.6%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.049999999999997%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.84%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="16.35%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="15.160000000000002%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.6%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.049999999999997%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NCW、NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.84%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="16.35%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>index</p>
</td>
<td class="cellrowborder" valign="top" width="15.160000000000002%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.6%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="29.049999999999997%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>索引张量，维度为2D/3D/4D，格式分别为ND、NCW、NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.84%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row141801355145019"><td class="cellrowborder" valign="top" width="16.35%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.160000000000002%" headers="mcps1.2.6.1.2 "><p id="p5501258232"><a name="p5501258232"></a><a name="p5501258232"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.6%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.049999999999997%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NCW、NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.84%" headers="mcps1.2.6.1.5 "><p id="p12336815165520"><a name="p12336815165520"></a><a name="p12336815165520"></a>-</p>
</td>
</tr>
<tr id="row21949558593"><td class="cellrowborder" valign="top" width="16.35%" headers="mcps1.2.6.1.1 "><p id="p1628915591592"><a name="p1628915591592"></a><a name="p1628915591592"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="15.160000000000002%" headers="mcps1.2.6.1.2 "><p id="p4289105915916"><a name="p4289105915916"></a><a name="p4289105915916"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.6%" headers="mcps1.2.6.1.3 "><p id="p825114289017"><a name="p825114289017"></a><a name="p825114289017"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.049999999999997%" headers="mcps1.2.6.1.4 "><p id="p108197531101"><a name="p108197531101"></a><a name="p108197531101"></a>输入张量被切分的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="23.84%" headers="mcps1.2.6.1.5 "><p id="p1525013286014"><a name="p1525013286014"></a><a name="p1525013286014"></a>-rank(data)<=axis<rank(data)，rank为张量的秩</p>
</td>
</tr>
</tbody>
</table>

### Split<a name="ZH-CN_TOPIC_0000002421393470" id="ZH-CN_TOPIC_0000002421393470"></a>

**功能描述<a name="section129901354195417"></a>**

对张量分割按照某一轴平均或非平均切分成若干份。

**参数说明<a name="section14760100195516"></a>**

**表 1**  Split参数概览

<a name="table193991958163314"></a>
<table><thead align="left"><tr id="row239925803313"><th class="cellrowborder" valign="top" width="16.22837716228377%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.388461153884613%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.638436156384364%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.007099290070997%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.737626237376265%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16313163412813"><td class="cellrowborder" valign="top" width="16.22837716228377%" headers="mcps1.2.6.1.1 "><p id="p498695217811"><a name="p498695217811"></a><a name="p498695217811"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.2 "><p id="p798675218810"><a name="p798675218810"></a><a name="p798675218810"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.638436156384364%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.007099290070997%" headers="mcps1.2.6.1.4 "><p id="p398625217814"><a name="p398625217814"></a><a name="p398625217814"></a>输入张量，维度为2D/3D/4D，格式分别为ND、NCW、NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.737626237376265%" headers="mcps1.2.6.1.5 "><p id="p3348132719916"><a name="p3348132719916"></a><a name="p3348132719916"></a>-</p>
</td>
</tr>
<tr id="row191569471550"><td class="cellrowborder" valign="top" width="16.22837716228377%" headers="mcps1.2.6.1.1 "><p id="p35882421986"><a name="p35882421986"></a><a name="p35882421986"></a>outputs</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.2 "><p id="p2589042983"><a name="p2589042983"></a><a name="p2589042983"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.638436156384364%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>varList(tensor)</p>
</td>
<td class="cellrowborder" valign="top" width="29.007099290070997%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NCW、NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.737626237376265%" headers="mcps1.2.6.1.5 "><p id="p133477272913"><a name="p133477272913"></a><a name="p133477272913"></a>-</p>
</td>
</tr>
<tr id="row8400195817332"><td class="cellrowborder" valign="top" width="16.22837716228377%" headers="mcps1.2.6.1.1 "><p id="p74001583338"><a name="p74001583338"></a><a name="p74001583338"></a>num_outputs</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.2 "><p id="p1640095843317"><a name="p1640095843317"></a><a name="p1640095843317"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.638436156384364%" headers="mcps1.2.6.1.3 "><p id="p1140045853318"><a name="p1140045853318"></a><a name="p1140045853318"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.007099290070997%" headers="mcps1.2.6.1.4 "><p id="p174001758173319"><a name="p174001758173319"></a><a name="p174001758173319"></a>分割的数量。</p>
</td>
<td class="cellrowborder" valign="top" width="23.737626237376265%" headers="mcps1.2.6.1.5 "><p id="p191284445610"><a name="p191284445610"></a><a name="p191284445610"></a>(0, split_dim] </p>
</td>
</tr>
<tr id="row164361335164118"><td class="cellrowborder" valign="top" width="16.22837716228377%" headers="mcps1.2.6.1.1 "><p id="p15436835124114"><a name="p15436835124114"></a><a name="p15436835124114"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.2 "><p id="p4289105915916"><a name="p4289105915916"></a><a name="p4289105915916"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.638436156384364%" headers="mcps1.2.6.1.3 "><p id="p825114289017"><a name="p825114289017"></a><a name="p825114289017"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.007099290070997%" headers="mcps1.2.6.1.4 "><p id="p108197531101"><a name="p108197531101"></a><a name="p108197531101"></a>被分割的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="23.737626237376265%" headers="mcps1.2.6.1.5 "><p id="p1525013286014"><a name="p1525013286014"></a><a name="p1525013286014"></a>维度索引</p>
</td>
</tr>
<tr id="row9903413143510"><td class="cellrowborder" valign="top" width="16.22837716228377%" headers="mcps1.2.6.1.1 "><p id="p49031913103511"><a name="p49031913103511"></a><a name="p49031913103511"></a>split</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.2 "><p id="p19031913113515"><a name="p19031913113515"></a><a name="p19031913113515"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.638436156384364%" headers="mcps1.2.6.1.3 "><p id="p790316136353"><a name="p790316136353"></a><a name="p790316136353"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.007099290070997%" headers="mcps1.2.6.1.4 "><p id="p18107442101017"><a name="p18107442101017"></a><a name="p18107442101017"></a>具体每一份分割的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="23.737626237376265%" headers="mcps1.2.6.1.5 "><p id="p1071521961116"><a name="p1071521961116"></a><a name="p1071521961116"></a>[n<sub id="sub3534611270"><a name="sub3534611270"></a><a name="sub3534611270"></a>1</sub>, n<sub id="sub1617612165714"><a name="sub1617612165714"></a><a name="sub1617612165714"></a>2</sub>, ..., n<sub id="sub19981122510712"><a name="sub19981122510712"></a><a name="sub19981122510712"></a>i</sub>]，∑n<sub id="sub516495511517"><a name="sub516495511517"></a><a name="sub516495511517"></a>i</sub> = 轴的值，n > 0</p>
</td>
</tr>
</tbody>
</table>

### Concat<a name="ZH-CN_TOPIC_0000002421233606" id="ZH-CN_TOPIC_0000002421233606"></a>

**功能描述<a name="section171987343553"></a>**

将多个张量拼接成某一个张量。

**参数说明<a name="section8688203805511"></a>**

**表 1**  Concat参数概览

<a name="table179393574363"></a>
<table><thead align="left"><tr id="row12939105703610"><th class="cellrowborder" valign="top" width="12.57874212578742%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.618638136186382%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.70872912708729%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="37.286271372862714%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.807619238076192%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row129391557183613"><td class="cellrowborder" valign="top" width="12.57874212578742%" headers="mcps1.2.6.1.1 "><p id="p493918572366"><a name="p493918572366"></a><a name="p493918572366"></a>inputs</p>
</td>
<td class="cellrowborder" valign="top" width="13.618638136186382%" headers="mcps1.2.6.1.2 "><p id="p1793915574368"><a name="p1793915574368"></a><a name="p1793915574368"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.70872912708729%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>varList(tensor)</p>
</td>
<td class="cellrowborder" valign="top" width="37.286271372862714%" headers="mcps1.2.6.1.4 "><p id="p10939057123612"><a name="p10939057123612"></a><a name="p10939057123612"></a>输入张量列表，内部各张量维度为2D/3D/4D，格式分别为ND、NCW、NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.807619238076192%" headers="mcps1.2.6.1.5 "><p id="p66671634141811"><a name="p66671634141811"></a><a name="p66671634141811"></a>规格约束：列表中各张量在指定轴上元素个数相等</p>
</td>
</tr>
<tr id="row10939657183610"><td class="cellrowborder" valign="top" width="12.57874212578742%" headers="mcps1.2.6.1.1 "><p id="p179391957153611"><a name="p179391957153611"></a><a name="p179391957153611"></a>concat_result</p>
</td>
<td class="cellrowborder" valign="top" width="13.618638136186382%" headers="mcps1.2.6.1.2 "><p id="p18939195712367"><a name="p18939195712367"></a><a name="p18939195712367"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.70872912708729%" headers="mcps1.2.6.1.3 "><p id="p59391057173614"><a name="p59391057173614"></a><a name="p59391057173614"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="37.286271372862714%" headers="mcps1.2.6.1.4 "><p id="p1985391215558"><a name="p1985391215558"></a><a name="p1985391215558"></a>输出张量，维度为2D/3D/4D，格式分别为ND、NCW、NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.807619238076192%" headers="mcps1.2.6.1.5 "><p id="p55991825111919"><a name="p55991825111919"></a><a name="p55991825111919"></a>-</p>
</td>
</tr>
<tr id="row175528015178"><td class="cellrowborder" valign="top" width="12.57874212578742%" headers="mcps1.2.6.1.1 "><p id="p11498144101710"><a name="p11498144101710"></a><a name="p11498144101710"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="13.618638136186382%" headers="mcps1.2.6.1.2 "><p id="p1498946175"><a name="p1498946175"></a><a name="p1498946175"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.70872912708729%" headers="mcps1.2.6.1.3 "><p id="p1649814141714"><a name="p1649814141714"></a><a name="p1649814141714"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="37.286271372862714%" headers="mcps1.2.6.1.4 "><p id="p174988410177"><a name="p174988410177"></a><a name="p174988410177"></a>指定沿着哪个轴进行连接。</p>
</td>
<td class="cellrowborder" valign="top" width="23.807619238076192%" headers="mcps1.2.6.1.5 "><p id="p1525013286014"><a name="p1525013286014"></a><a name="p1525013286014"></a>规格约束：-rank(data)≤axis<rank(data)，rank为张量的秩</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 输入rank、axis和静态形状必须满足拼接约束 |

### AveragePool<a name="ZH-CN_TOPIC_0000002455402925" id="ZH-CN_TOPIC_0000002455402925"></a>

**功能描述<a name="section113841812134710"></a>**

对3D或4D输入进行平均池化计算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  AveragePool参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="16.518348165183482%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.408459154084591%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.368463153684633%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.837116288371163%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.86761323867613%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="16.518348165183482%" headers="mcps1.2.6.1.1 "><p id="p814484714519"><a name="p814484714519"></a><a name="p814484714519"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="15.408459154084591%" headers="mcps1.2.6.1.2 "><p id="p16144114785114"><a name="p16144114785114"></a><a name="p16144114785114"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.368463153684633%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.837116288371163%" headers="mcps1.2.6.1.4 "><p id="p5776175813266"><a name="p5776175813266"></a><a name="p5776175813266"></a>输入张量，维度为3D或4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.86761323867613%" headers="mcps1.2.6.1.5 "><p id="p18848151322319"><a name="p18848151322319"></a><a name="p18848151322319"></a>-</p>
</td>
</tr>
<tr id="row15423221105011"><td class="cellrowborder" valign="top" width="16.518348165183482%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="15.408459154084591%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.368463153684633%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.837116288371163%" headers="mcps1.2.6.1.4 "><p id="p57261613112110"><a name="p57261613112110"></a><a name="p57261613112110"></a>输出张量，维度为3D或4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.86761323867613%" headers="mcps1.2.6.1.5 "><p id="p6847131316239"><a name="p6847131316239"></a><a name="p6847131316239"></a>-</p>
</td>
</tr>
<tr id="row2423132175015"><td class="cellrowborder" valign="top" width="16.518348165183482%" headers="mcps1.2.6.1.1 "><p id="p211803695110"><a name="p211803695110"></a><a name="p211803695110"></a>auto_pad</p>
</td>
<td class="cellrowborder" valign="top" width="15.408459154084591%" headers="mcps1.2.6.1.2 "><p id="p4118173613511"><a name="p4118173613511"></a><a name="p4118173613511"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.368463153684633%" headers="mcps1.2.6.1.3 "><p id="p71181836115119"><a name="p71181836115119"></a><a name="p71181836115119"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="28.837116288371163%" headers="mcps1.2.6.1.4 "><p id="p1577685818263"><a name="p1577685818263"></a><a name="p1577685818263"></a>指定padding的类型。</p>
</td>
<td class="cellrowborder" valign="top" width="23.86761323867613%" headers="mcps1.2.6.1.5 "><p id="p14897185443916"><a name="p14897185443916"></a><a name="p14897185443916"></a>配置范围：NOTSET、SAME_UPPER、SAME_LOWER、VALID</p>
</td>
</tr>
<tr id="row9424122145019"><td class="cellrowborder" valign="top" width="16.518348165183482%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>ceil_mode</p>
</td>
<td class="cellrowborder" valign="top" width="15.408459154084591%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.368463153684633%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="28.837116288371163%" headers="mcps1.2.6.1.4 "><p id="p1351318783714"><a name="p1351318783714"></a><a name="p1351318783714"></a>输出形状的取整方式。</p>
</td>
<td class="cellrowborder" valign="top" width="23.86761323867613%" headers="mcps1.2.6.1.5 "><p id="p10748523112318"><a name="p10748523112318"></a><a name="p10748523112318"></a>仅支持floor</p>
</td>
</tr>
<tr id="row19424152111505"><td class="cellrowborder" valign="top" width="16.518348165183482%" headers="mcps1.2.6.1.1 "><p id="p211883675111"><a name="p211883675111"></a><a name="p211883675111"></a>dilations</p>
</td>
<td class="cellrowborder" valign="top" width="15.408459154084591%" headers="mcps1.2.6.1.2 "><p id="p811833615513"><a name="p811833615513"></a><a name="p811833615513"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.368463153684633%" headers="mcps1.2.6.1.3 "><p id="p196681283714"><a name="p196681283714"></a><a name="p196681283714"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="28.837116288371163%" headers="mcps1.2.6.1.4 "><p id="p3776105813265"><a name="p3776105813265"></a><a name="p3776105813265"></a>每个轴上的扩张系数。</p>
</td>
<td class="cellrowborder" valign="top" width="23.86761323867613%" headers="mcps1.2.6.1.5 "><p id="p147561323132312"><a name="p147561323132312"></a><a name="p147561323132312"></a>仅支持1</p>
</td>
</tr>
<tr id="row1242515218501"><td class="cellrowborder" valign="top" width="16.518348165183482%" headers="mcps1.2.6.1.1 "><p id="p611873695118"><a name="p611873695118"></a><a name="p611873695118"></a>kernel_shape</p>
</td>
<td class="cellrowborder" valign="top" width="15.408459154084591%" headers="mcps1.2.6.1.2 "><p id="p6118173618512"><a name="p6118173618512"></a><a name="p6118173618512"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.368463153684633%" headers="mcps1.2.6.1.3 "><p id="p768111213375"><a name="p768111213375"></a><a name="p768111213375"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="28.837116288371163%" headers="mcps1.2.6.1.4 "><p id="p1011953613513"><a name="p1011953613513"></a><a name="p1011953613513"></a>kernel沿各轴的大小。</p>
</td>
<td class="cellrowborder" valign="top" width="23.86761323867613%" headers="mcps1.2.6.1.5 "><p id="p208161758122315"><a name="p208161758122315"></a><a name="p208161758122315"></a>-</p>
</td>
</tr>
<tr id="row1142582117505"><td class="cellrowborder" valign="top" width="16.518348165183482%" headers="mcps1.2.6.1.1 "><p id="p41191436195118"><a name="p41191436195118"></a><a name="p41191436195118"></a>pads</p>
</td>
<td class="cellrowborder" valign="top" width="15.408459154084591%" headers="mcps1.2.6.1.2 "><p id="p101191368518"><a name="p101191368518"></a><a name="p101191368518"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.368463153684633%" headers="mcps1.2.6.1.3 "><p id="p411953685110"><a name="p411953685110"></a><a name="p411953685110"></a></p>
<p id="p17777145822614"><a name="p17777145822614"></a><a name="p17777145822614"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="28.837116288371163%" headers="mcps1.2.6.1.4 "><p id="p85157422328"><a name="p85157422328"></a><a name="p85157422328"></a>各轴前后填充零的个数。</p>
</td>
<td class="cellrowborder" valign="top" width="23.86761323867613%" headers="mcps1.2.6.1.5 "><p id="p68151858122318"><a name="p68151858122318"></a><a name="p68151858122318"></a>-</p>
</td>
</tr>
<tr id="row1742542125016"><td class="cellrowborder" valign="top" width="16.518348165183482%" headers="mcps1.2.6.1.1 "><p id="p11119123645111"><a name="p11119123645111"></a><a name="p11119123645111"></a>storage_order</p>
</td>
<td class="cellrowborder" valign="top" width="15.408459154084591%" headers="mcps1.2.6.1.2 "><p id="p3119183675110"><a name="p3119183675110"></a><a name="p3119183675110"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.368463153684633%" headers="mcps1.2.6.1.3 "><p id="p141191136145117"><a name="p141191136145117"></a><a name="p141191136145117"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="28.837116288371163%" headers="mcps1.2.6.1.4 "><p id="p7517113815389"><a name="p7517113815389"></a><a name="p7517113815389"></a>张量存储主序。</p>
</td>
<td class="cellrowborder" valign="top" width="23.86761323867613%" headers="mcps1.2.6.1.5 "><p id="p218945214234"><a name="p218945214234"></a><a name="p218945214234"></a>仅支持0</p>
</td>
</tr>
<tr id="row1387274316020"><td class="cellrowborder" valign="top" width="16.518348165183482%" headers="mcps1.2.6.1.1 "><p id="p17121123613512"><a name="p17121123613512"></a><a name="p17121123613512"></a>strides</p>
</td>
<td class="cellrowborder" valign="top" width="15.408459154084591%" headers="mcps1.2.6.1.2 "><p id="p14121123611515"><a name="p14121123611515"></a><a name="p14121123611515"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.368463153684633%" headers="mcps1.2.6.1.3 "><p id="p1444016203712"><a name="p1444016203712"></a><a name="p1444016203712"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="28.837116288371163%" headers="mcps1.2.6.1.4 "><p id="p18216141324"><a name="p18216141324"></a><a name="p18216141324"></a>各个方向上kernel的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="23.86761323867613%" headers="mcps1.2.6.1.5 "><p id="p3933556122319"><a name="p3933556122319"></a><a name="p3933556122319"></a>-</p>
</td>
</tr>
</tbody>
</table>

### InstanceNormalization<a name="ZH-CN_TOPIC_0000002453072106" id="ZH-CN_TOPIC_0000002453072106"></a>

**功能描述<a name="section113841812134710"></a>**

对3D输入张量做归一化计算。

**参数说明<a name="section15195134816462"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>暂时只支持1D，仅支持float类型，暂不支持int8类型。

**表 1**  InstanceNormalization参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="16.93830616938306%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.14848515148485%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.388461153884613%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.777122287771224%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.747625237476253%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1111813635119"><a name="p1111813635119"></a><a name="p1111813635119"></a>输入张量，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7349185545010"><a name="p7349185545010"></a><a name="p7349185545010"></a>-</p>
</td>
</tr>
<tr id="row15423221105011"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p814484714519"><a name="p814484714519"></a><a name="p814484714519"></a>scale</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p16144114785114"><a name="p16144114785114"></a><a name="p16144114785114"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p17144134765111"><a name="p17144134765111"></a><a name="p17144134765111"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p11441547135118"><a name="p11441547135118"></a><a name="p11441547135118"></a>输入张量的放缩系数，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p16977195144313"><a name="p16977195144313"></a><a name="p16977195144313"></a>-</p>
</td>
</tr>
<tr id="row1742542125016"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p11150123511475"><a name="p11150123511475"></a><a name="p11150123511475"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p8151173534717"><a name="p8151173534717"></a><a name="p8151173534717"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p19151163511479"><a name="p19151163511479"></a><a name="p19151163511479"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p4151635144712"><a name="p4151635144712"></a><a name="p4151635144712"></a>偏置向量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p99771651174319"><a name="p99771651174319"></a><a name="p99771651174319"></a>-</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p187213431103"><a name="p187213431103"></a><a name="p187213431103"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1677592812"><a name="p1677592812"></a><a name="p1677592812"></a>输出张量，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p83481655175017"><a name="p83481655175017"></a><a name="p83481655175017"></a>-</p>
</td>
</tr>
<tr id="row168911912143417"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p12286124112430"><a name="p12286124112430"></a><a name="p12286124112430"></a>epsilon</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p1299891713439"><a name="p1299891713439"></a><a name="p1299891713439"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p1551719012441"><a name="p1551719012441"></a><a name="p1551719012441"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p18141820435"><a name="p18141820435"></a><a name="p18141820435"></a>用于避免除零溢出（默认1e-5）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p458116104314"><a name="p458116104314"></a><a name="p458116104314"></a>-</p>
</td>
</tr>
</tbody>
</table>

### LSTM<a name="ZH-CN_TOPIC_0000002486111849" id="ZH-CN_TOPIC_0000002486111849"></a>

**功能描述<a name="section113841812134710"></a>**

一种循环神经网络，用于捕捉输入的时序数据长期依赖关系。

**参数说明<a name="section15195134816462"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>仅支持float类型，暂不支持int8类型。

**表 1**  LSTM参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="15.90840915908409%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="16.75832416758324%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.948505149485051%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.027097290270977%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.357664233576642%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1248010314128"><a name="p1248010314128"></a><a name="p1248010314128"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p194805351219"><a name="p194805351219"></a><a name="p194805351219"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p17480935121"><a name="p17480935121"></a><a name="p17480935121"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p74809310127"><a name="p74809310127"></a><a name="p74809310127"></a>输入时序数据，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p64168815415"><a name="p64168815415"></a><a name="p64168815415"></a>规格约束：作为在线变量</p>
</td>
</tr>
<tr id="row15423221105011"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p173274161212"><a name="p173274161212"></a><a name="p173274161212"></a>W</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p165092761312"><a name="p165092761312"></a><a name="p165092761312"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p128033051319"><a name="p128033051319"></a><a name="p128033051319"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1932818111219"><a name="p1932818111219"></a><a name="p1932818111219"></a>门的权重张量，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p13647141201617"><a name="p13647141201617"></a><a name="p13647141201617"></a>规格约束：离线常量</p>
</td>
</tr>
<tr id="row1742542125016"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1512710595112"><a name="p1512710595112"></a><a name="p1512710595112"></a>R</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p452202712134"><a name="p452202712134"></a><a name="p452202712134"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p7282153014134"><a name="p7282153014134"></a><a name="p7282153014134"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p161271459131112"><a name="p161271459131112"></a><a name="p161271459131112"></a>循环权重张量，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p145531546141511"><a name="p145531546141511"></a><a name="p145531546141511"></a>规格约束：离线常量</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1717255617118"><a name="p1717255617118"></a><a name="p1717255617118"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p354172712133"><a name="p354172712133"></a><a name="p354172712133"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p228403041310"><a name="p228403041310"></a><a name="p228403041310"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1217255681116"><a name="p1217255681116"></a><a name="p1217255681116"></a>输入门偏置张量，维度为2D，格式为ND。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p1012716593152"><a name="p1012716593152"></a><a name="p1012716593152"></a>规格约束：离线常量</p>
</td>
</tr>
<tr id="row8258131210520"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1174453181112"><a name="p1174453181112"></a><a name="p1174453181112"></a>sequence_lens</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p1856182719134"><a name="p1856182719134"></a><a name="p1856182719134"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p1728619308134"><a name="p1728619308134"></a><a name="p1728619308134"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p11741531119"><a name="p11741531119"></a><a name="p11741531119"></a>确定每个批数据中时序长度。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p14212322135813"><a name="p14212322135813"></a><a name="p14212322135813"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row54041919451"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1955815503116"><a name="p1955815503116"></a><a name="p1955815503116"></a>initial_h</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p155812276131"><a name="p155812276131"></a><a name="p155812276131"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p1528816306136"><a name="p1528816306136"></a><a name="p1528816306136"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p115591850141116"><a name="p115591850141116"></a><a name="p115591850141116"></a>隐藏层初始值，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p95910116584"><a name="p95910116584"></a><a name="p95910116584"></a>规格约束：作为在线变量</p>
</td>
</tr>
<tr id="row74161017452"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p6603747181216"><a name="p6603747181216"></a><a name="p6603747181216"></a>initial_c</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p859182720134"><a name="p859182720134"></a><a name="p859182720134"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p3290193010133"><a name="p3290193010133"></a><a name="p3290193010133"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p15604104711211"><a name="p15604104711211"></a><a name="p15604104711211"></a>细胞层初始值，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p1458181116586"><a name="p1458181116586"></a><a name="p1458181116586"></a>规格约束：作为在线变量</p>
</td>
</tr>
<tr id="row32806151753"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p948565041213"><a name="p948565041213"></a><a name="p948565041213"></a>P</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p1861827171310"><a name="p1861827171310"></a><a name="p1861827171310"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p18292143010131"><a name="p18292143010131"></a><a name="p18292143010131"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p348516504121"><a name="p348516504121"></a><a name="p348516504121"></a>窥视孔权重向量。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p65421353144519"><a name="p65421353144519"></a><a name="p65421353144519"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row1747910320121"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p39589539121"><a name="p39589539121"></a><a name="p39589539121"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p2031972391316"><a name="p2031972391316"></a><a name="p2031972391316"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p1929412304133"><a name="p1929412304133"></a><a name="p1929412304133"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1995935341212"><a name="p1995935341212"></a><a name="p1995935341212"></a>隐藏层所有中间输出值张量拼接后的向量，维度为4D，格式为NCHW。</p>
</td>
<td class="cellrowborder" align="left" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p6883163513716"><a name="p6883163513716"></a><a name="p6883163513716"></a>规格约束：作为在线输出变量</p>
</td>
</tr>
<tr id="row133273120124"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p16121151191316"><a name="p16121151191316"></a><a name="p16121151191316"></a>Y_h</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p17322122381314"><a name="p17322122381314"></a><a name="p17322122381314"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p0296143011135"><a name="p0296143011135"></a><a name="p0296143011135"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p6121411161316"><a name="p6121411161316"></a><a name="p6121411161316"></a>隐藏层输出向量，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p1558163514172"><a name="p1558163514172"></a><a name="p1558163514172"></a>规格约束：作为在线输出变量</p>
</td>
</tr>
<tr id="row121271459101119"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>Y_c</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p187213431103"><a name="p187213431103"></a><a name="p187213431103"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1677592812"><a name="p1677592812"></a><a name="p1677592812"></a>细胞层输出向量，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p1228211105468"><a name="p1228211105468"></a><a name="p1228211105468"></a>规格约束：作为在线输出变量</p>
</td>
</tr>
<tr id="row18172056141112"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p12286124112430"><a name="p12286124112430"></a><a name="p12286124112430"></a>activation_alpha</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p1299891713439"><a name="p1299891713439"></a><a name="p1299891713439"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p1551719012441"><a name="p1551719012441"></a><a name="p1551719012441"></a>list(float)</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p18141820435"><a name="p18141820435"></a><a name="p18141820435"></a>对LSTM激活函数结果做放缩（默认0.01）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p19495356105713"><a name="p19495356105713"></a><a name="p19495356105713"></a>-</p>
</td>
</tr>
<tr id="row5174753191116"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1833217289114"><a name="p1833217289114"></a><a name="p1833217289114"></a>activation_beta</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p1233202816110"><a name="p1233202816110"></a><a name="p1233202816110"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p733262818115"><a name="p733262818115"></a><a name="p733262818115"></a>list(float)</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1889316380591"><a name="p1889316380591"></a><a name="p1889316380591"></a>对LSTM激活函数结果做偏置（默认0.01）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p1493456185711"><a name="p1493456185711"></a><a name="p1493456185711"></a>-</p>
</td>
</tr>
<tr id="row5558115019118"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p814484714519"><a name="p814484714519"></a><a name="p814484714519"></a>activations</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p16144114785114"><a name="p16144114785114"></a><a name="p16144114785114"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p17144134765111"><a name="p17144134765111"></a><a name="p17144134765111"></a>list(string)</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p11441547135118"><a name="p11441547135118"></a><a name="p11441547135118"></a>LSTM激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p13184196144711"><a name="p13184196144711"></a><a name="p13184196144711"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row3603184731217"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p11150123511475"><a name="p11150123511475"></a><a name="p11150123511475"></a>clip</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p8151173534717"><a name="p8151173534717"></a><a name="p8151173534717"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p19151163511479"><a name="p19151163511479"></a><a name="p19151163511479"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p4151635144712"><a name="p4151635144712"></a><a name="p4151635144712"></a>梯度裁剪阈值。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p58086713473"><a name="p58086713473"></a><a name="p58086713473"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row848595061211"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p122585121956"><a name="p122585121956"></a><a name="p122585121956"></a>direction</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p69881303515"><a name="p69881303515"></a><a name="p69881303515"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p09887301258"><a name="p09887301258"></a><a name="p09887301258"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1025881214516"><a name="p1025881214516"></a><a name="p1025881214516"></a>指定LSTM处理输入数据的方式（默认'forward'）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p21042917473"><a name="p21042917473"></a><a name="p21042917473"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row1295885371216"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p5405319458"><a name="p5405319458"></a><a name="p5405319458"></a>hidden_size</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p1640511191451"><a name="p1640511191451"></a><a name="p1640511191451"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p440551918512"><a name="p440551918512"></a><a name="p440551918512"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p540511193519"><a name="p540511193519"></a><a name="p540511193519"></a>隐藏层大小。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p5682102735713"><a name="p5682102735713"></a><a name="p5682102735713"></a>-</p>
</td>
</tr>
<tr id="row14121211111319"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p44171317051"><a name="p44171317051"></a><a name="p44171317051"></a>input_forget</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p0161181888"><a name="p0161181888"></a><a name="p0161181888"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p1316111980"><a name="p1316111980"></a><a name="p1316111980"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p84171017153"><a name="p84171017153"></a><a name="p84171017153"></a>是否对输入和遗忘门进行耦合（默认0）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p62042515101"><a name="p62042515101"></a><a name="p62042515101"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row168911912143417"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p12281171514519"><a name="p12281171514519"></a><a name="p12281171514519"></a>layout</p>
</td>
<td class="cellrowborder" valign="top" width="16.75832416758324%" headers="mcps1.2.6.1.2 "><p id="p745164516104"><a name="p745164516104"></a><a name="p745164516104"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.948505149485051%" headers="mcps1.2.6.1.3 "><p id="p114594511107"><a name="p114594511107"></a><a name="p114594511107"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p328171514518"><a name="p328171514518"></a><a name="p328171514518"></a>确定输入数据的排布格式，取值范围0或1（默认0）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p136612151473"><a name="p136612151473"></a><a name="p136612151473"></a>暂不支持配置</p>
</td>
</tr>
</tbody>
</table>

### Tile<a name="ZH-CN_TOPIC_0000002513105051" id="ZH-CN_TOPIC_0000002513105051"></a>

**功能描述<a name="section144144283412"></a>**

对2D/3D/4D输入沿指定维度做复制扩展。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Tile参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="16.8983101689831%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.938706129387059%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.108589141085892%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.556944305569438%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.497450254974503%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16660151211817"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p167712418440"><a name="p167712418440"></a><a name="p167712418440"></a>repeats</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p077044174411"><a name="p077044174411"></a><a name="p077044174411"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p676912411444"><a name="p676912411444"></a><a name="p676912411444"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p576810417443"><a name="p576810417443"></a><a name="p576810417443"></a>指定每个维度复制次数。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p17661841144412"><a name="p17661841144412"></a><a name="p17661841144412"></a>规格约束：repeats为离线常量</p>
</td>
</tr>
<tr id="row158205562211"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p163562048134411"><a name="p163562048134411"></a><a name="p163562048134411"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p03551948164416"><a name="p03551948164416"></a><a name="p03551948164416"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p173541548184411"><a name="p173541548184411"></a><a name="p173541548184411"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p123531648164412"><a name="p123531648164412"></a><a name="p123531648164412"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p136681122157"><a name="p136681122157"></a><a name="p136681122157"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Pad<a name="ZH-CN_TOPIC_0000002480825566" id="ZH-CN_TOPIC_0000002480825566"></a>

**功能描述<a name="section144144283412"></a>**

对输入张量边界做填充。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Pad参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="16.8983101689831%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.938706129387059%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.108589141085892%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.556944305569438%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.497450254974503%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16660151211817"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>规格约束：mode=constant的int8量化场景仅支持4D张量输入</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p167712418440"><a name="p167712418440"></a><a name="p167712418440"></a>pads</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p077044174411"><a name="p077044174411"></a><a name="p077044174411"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p676912411444"><a name="p676912411444"></a><a name="p676912411444"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p576810417443"><a name="p576810417443"></a><a name="p576810417443"></a>指定各输入维度填充范围。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p18895954132310"><a name="p18895954132310"></a><a name="p18895954132310"></a>规格约束：pads为离线常量，pads[i]<input_dim[i]</p>
<p id="p2490184017266"><a name="p2490184017266"></a><a name="p2490184017266"></a>pads[i]非负</p>
</td>
</tr>
<tr id="row274274614198"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p5742114621912"><a name="p5742114621912"></a><a name="p5742114621912"></a>constant_value</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p374211467192"><a name="p374211467192"></a><a name="p374211467192"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p1174210465192"><a name="p1174210465192"></a><a name="p1174210465192"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p874294691912"><a name="p874294691912"></a><a name="p874294691912"></a>自定义填充常量。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p10743204616199"><a name="p10743204616199"></a><a name="p10743204616199"></a>规格约束：constant_value为离线常量</p>
</td>
</tr>
<tr id="row5732154110208"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p17732134115208"><a name="p17732134115208"></a><a name="p17732134115208"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p6732941102016"><a name="p6732941102016"></a><a name="p6732941102016"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p197321041102019"><a name="p197321041102019"></a><a name="p197321041102019"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p3732141102012"><a name="p3732141102012"></a><a name="p3732141102012"></a>指定需要填充的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p6732641182019"><a name="p6732641182019"></a><a name="p6732641182019"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row158205562211"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p163562048134411"><a name="p163562048134411"></a><a name="p163562048134411"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p03551948164416"><a name="p03551948164416"></a><a name="p03551948164416"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p173541548184411"><a name="p173541548184411"></a><a name="p173541548184411"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p123531648164412"><a name="p123531648164412"></a><a name="p123531648164412"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p143521048174416"><a name="p143521048174416"></a><a name="p143521048174416"></a>-</p>
</td>
</tr>
<tr id="row8442402249"><td class="cellrowborder" valign="top" width="16.8983101689831%" headers="mcps1.2.6.1.1 "><p id="p144317011245"><a name="p144317011245"></a><a name="p144317011245"></a>mode</p>
</td>
<td class="cellrowborder" valign="top" width="12.938706129387059%" headers="mcps1.2.6.1.2 "><p id="p144315016242"><a name="p144315016242"></a><a name="p144315016242"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.108589141085892%" headers="mcps1.2.6.1.3 "><p id="p644314062411"><a name="p644314062411"></a><a name="p644314062411"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="30.556944305569438%" headers="mcps1.2.6.1.4 "><p id="p1544360152417"><a name="p1544360152417"></a><a name="p1544360152417"></a>指定填充模式。</p>
</td>
<td class="cellrowborder" valign="top" width="25.497450254974503%" headers="mcps1.2.6.1.5 "><p id="p134430012413"><a name="p134430012413"></a><a name="p134430012413"></a>配置范围：constant、reflect、edge</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | pads必须为转换期常量 |

### Resize<a name="ZH-CN_TOPIC_0000002512945433" id="ZH-CN_TOPIC_0000002512945433"></a>

**功能描述<a name="section144144283412"></a>**

对输入张量按照指定填充模式做缩放。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Resize参数概览

<a name="table465813123188"></a>
<table><thead align="left"><tr id="row1965941210180"><th class="cellrowborder" valign="top" width="19.748025197480253%" id="mcps1.2.6.1.1"><p id="p9337191714595"><a name="p9337191714595"></a><a name="p9337191714595"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="10.048995100489952%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="10.808919108089192%" id="mcps1.2.6.1.3"><p id="p1033751719595"><a name="p1033751719595"></a><a name="p1033751719595"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.456854314568545%" id="mcps1.2.6.1.4"><p id="p123372017105917"><a name="p123372017105917"></a><a name="p123372017105917"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="27.937206279372063%" id="mcps1.2.6.1.5"><p id="p333721725916"><a name="p333721725916"></a><a name="p333721725916"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16660151211817"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为4D，格式为NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>-</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p167712418440"><a name="p167712418440"></a><a name="p167712418440"></a>roi</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p077044174411"><a name="p077044174411"></a><a name="p077044174411"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p676912411444"><a name="p676912411444"></a><a name="p676912411444"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p576810417443"><a name="p576810417443"></a><a name="p576810417443"></a>指定每个维度复制次数。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p18895954132310"><a name="p18895954132310"></a><a name="p18895954132310"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row274274614198"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p5742114621912"><a name="p5742114621912"></a><a name="p5742114621912"></a>scales</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p374211467192"><a name="p374211467192"></a><a name="p374211467192"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p1174210465192"><a name="p1174210465192"></a><a name="p1174210465192"></a>list(float)</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p874294691912"><a name="p874294691912"></a><a name="p874294691912"></a>自定义填充常量。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p10743204616199"><a name="p10743204616199"></a><a name="p10743204616199"></a>规格约束：离线常量，NC轴保持1.0。fp32仅支持out_dim为整数，int8不支持配置，scales为离线常量，与sizes必须配置且仅配置一个</p>
</td>
</tr>
<tr id="row5732154110208"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p17732134115208"><a name="p17732134115208"></a><a name="p17732134115208"></a>sizes</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p6732941102016"><a name="p6732941102016"></a><a name="p6732941102016"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p197321041102019"><a name="p197321041102019"></a><a name="p197321041102019"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p3732141102012"><a name="p3732141102012"></a><a name="p3732141102012"></a>指定需要填充的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p9355151618"><a name="p9355151618"></a><a name="p9355151618"></a>规格约束：离线常量，NC轴同输入张量保持一致，sizes为离线常量</p>
</td>
</tr>
<tr id="row158205562211"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p163562048134411"><a name="p163562048134411"></a><a name="p163562048134411"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p03551948164416"><a name="p03551948164416"></a><a name="p03551948164416"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p173541548184411"><a name="p173541548184411"></a><a name="p173541548184411"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p123531648164412"><a name="p123531648164412"></a><a name="p123531648164412"></a>输出张量，维度为4D，格式为NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p143521048174416"><a name="p143521048174416"></a><a name="p143521048174416"></a>-</p>
</td>
</tr>
<tr id="row8442402249"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p144317011245"><a name="p144317011245"></a><a name="p144317011245"></a>antialias</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p144315016242"><a name="p144315016242"></a><a name="p144315016242"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p1156692220816"><a name="p1156692220816"></a><a name="p1156692220816"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p1544360152417"><a name="p1544360152417"></a><a name="p1544360152417"></a>默认值：0。抗锯齿开关，用于平滑缩小图像边缘锯齿。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p134430012413"><a name="p134430012413"></a><a name="p134430012413"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row338714333710"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p1738717331672"><a name="p1738717331672"></a><a name="p1738717331672"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p182400481280"><a name="p182400481280"></a><a name="p182400481280"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p13874335717"><a name="p13874335717"></a><a name="p13874335717"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p93876331172"><a name="p93876331172"></a><a name="p93876331172"></a>指定缩放的维度轴索引。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p13870331477"><a name="p13870331477"></a><a name="p13870331477"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row5203338773"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p17203238879"><a name="p17203238879"></a><a name="p17203238879"></a>coordinate_transformation_mode</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p1724434814817"><a name="p1724434814817"></a><a name="p1724434814817"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p1720383812711"><a name="p1720383812711"></a><a name="p1720383812711"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p1820314381072"><a name="p1820314381072"></a><a name="p1820314381072"></a>默认值："half_pixel"。指定坐标转换模式，控制像素映射关系。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p159739201146"><a name="p159739201146"></a><a name="p159739201146"></a>配置范围：</p>
<p id="p182037389718"><a name="p182037389718"></a><a name="p182037389718"></a>'half_pixel'、"align_corners"、"asymmetric"</p>
</td>
</tr>
<tr id="row6725643279"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p19725174320720"><a name="p19725174320720"></a><a name="p19725174320720"></a>cubic_coeff_a</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p024713484810"><a name="p024713484810"></a><a name="p024713484810"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p8725443972"><a name="p8725443972"></a><a name="p8725443972"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p147252431172"><a name="p147252431172"></a><a name="p147252431172"></a>默认值："-0.75"。三次插值系数，影响插值平滑程度。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p57256431675"><a name="p57256431675"></a><a name="p57256431675"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row27257431271"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p472517431473"><a name="p472517431473"></a><a name="p472517431473"></a>exclude_outside</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p224912484810"><a name="p224912484810"></a><a name="p224912484810"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p5725134315712"><a name="p5725134315712"></a><a name="p5725134315712"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p55291222141917"><a name="p55291222141917"></a><a name="p55291222141917"></a>默认值："0"。边界处理开关，是否排除外部像素。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p157252043778"><a name="p157252043778"></a><a name="p157252043778"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row11527652676"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p135279526717"><a name="p135279526717"></a><a name="p135279526717"></a>extrapolation_value</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p18251948780"><a name="p18251948780"></a><a name="p18251948780"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p952717521270"><a name="p952717521270"></a><a name="p952717521270"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p175278521720"><a name="p175278521720"></a><a name="p175278521720"></a>默认值："0.0"。外推填充值，越界时使用的数值。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p1352141115716"><a name="p1352141115716"></a><a name="p1352141115716"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row652716522713"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p2527352375"><a name="p2527352375"></a><a name="p2527352375"></a>keep_aspect_ratio_policy</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p6253194816813"><a name="p6253194816813"></a><a name="p6253194816813"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p2527452072"><a name="p2527452072"></a><a name="p2527452072"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p85272521370"><a name="p85272521370"></a><a name="p85272521370"></a>默认值："stretch"。保持高宽比策略，缩放比例计算方式。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p75273521873"><a name="p75273521873"></a><a name="p75273521873"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row45271252975"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p125276520716"><a name="p125276520716"></a><a name="p125276520716"></a>mode</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p11255448487"><a name="p11255448487"></a><a name="p11255448487"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p125288521978"><a name="p125288521978"></a><a name="p125288521978"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p75284524716"><a name="p75284524716"></a><a name="p75284524716"></a>默认值："nearest"。指定缩放插值模式。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p0951104572118"><a name="p0951104572118"></a><a name="p0951104572118"></a>配置范围：</p>
<p id="p652811522712"><a name="p652811522712"></a><a name="p652811522712"></a>"nearest"、"linear"</p>
</td>
</tr>
<tr id="row195281752676"><td class="cellrowborder" valign="top" width="19.748025197480253%" headers="mcps1.2.6.1.1 "><p id="p18528952476"><a name="p18528952476"></a><a name="p18528952476"></a>nearest_mode</p>
</td>
<td class="cellrowborder" valign="top" width="10.048995100489952%" headers="mcps1.2.6.1.2 "><p id="p1825784812817"><a name="p1825784812817"></a><a name="p1825784812817"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.808919108089192%" headers="mcps1.2.6.1.3 "><p id="p452817528720"><a name="p452817528720"></a><a name="p452817528720"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="31.456854314568545%" headers="mcps1.2.6.1.4 "><p id="p164412047122420"><a name="p164412047122420"></a><a name="p164412047122420"></a>默认值："round_prefer_floor"。</p>
<p id="p952865216715"><a name="p952865216715"></a><a name="p952865216715"></a>最近邻插值模式下取整函数。</p>
</td>
<td class="cellrowborder" valign="top" width="27.937206279372063%" headers="mcps1.2.6.1.5 "><p id="p17188026171412"><a name="p17188026171412"></a><a name="p17188026171412"></a>配置范围：</p>
<p id="p14528952770"><a name="p14528952770"></a><a name="p14528952770"></a>"round_prefer_floor"、"round_prefer_ceil"、"floor"</p>
</td>
</tr>
</tbody>
</table>

### Squeeze<a name="ZH-CN_TOPIC_0000002482800962" id="ZH-CN_TOPIC_0000002482800962"></a>

**功能描述<a name="section144144283412"></a>**

对输入张量进行shape压缩操作，被压缩维度的dim值必须为1。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Squeeze参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="16.93830616938306%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.14848515148485%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.388461153884613%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.777122287771224%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.747625237476253%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1111813635119"><a name="p1111813635119"></a><a name="p1111813635119"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7349185545010"><a name="p7349185545010"></a><a name="p7349185545010"></a>-</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>squeezed</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p187213431103"><a name="p187213431103"></a><a name="p187213431103"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1677592812"><a name="p1677592812"></a><a name="p1677592812"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p83481655175017"><a name="p83481655175017"></a><a name="p83481655175017"></a>-</p>
</td>
</tr>
<tr id="row168911912143417"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p12286124112430"><a name="p12286124112430"></a><a name="p12286124112430"></a>axes（可选）</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p1299891713439"><a name="p1299891713439"></a><a name="p1299891713439"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p1551719012441"><a name="p1551719012441"></a><a name="p1551719012441"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p18141820435"><a name="p18141820435"></a><a name="p18141820435"></a>被压缩的轴列表。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p458116104314"><a name="p458116104314"></a><a name="p458116104314"></a>-Rank(tensor) <= axis <  Rank(tensor)</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 输入和输出元素数量必须一致 |
| FP32 | 支持 | 输入和输出元素数量必须一致 |

### Unsqueeze<a name="ZH-CN_TOPIC_0000002482804754" id="ZH-CN_TOPIC_0000002482804754"></a>

**功能描述<a name="section144144283412"></a>**

对多维Tensor进行shape扩展。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Unsqueeze参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="16.93830616938306%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.14848515148485%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.388461153884613%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.777122287771224%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.747625237476253%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1111813635119"><a name="p1111813635119"></a><a name="p1111813635119"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7349185545010"><a name="p7349185545010"></a><a name="p7349185545010"></a>-</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>expanded</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p187213431103"><a name="p187213431103"></a><a name="p187213431103"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1677592812"><a name="p1677592812"></a><a name="p1677592812"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p83481655175017"><a name="p83481655175017"></a><a name="p83481655175017"></a>-</p>
</td>
</tr>
<tr id="row168911912143417"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p12286124112430"><a name="p12286124112430"></a><a name="p12286124112430"></a>axes（可选）</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p1299891713439"><a name="p1299891713439"></a><a name="p1299891713439"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p1551719012441"><a name="p1551719012441"></a><a name="p1551719012441"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p18141820435"><a name="p18141820435"></a><a name="p18141820435"></a>被扩展的轴列表。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p458116104314"><a name="p458116104314"></a><a name="p458116104314"></a>-Rank(expanded) <= axis <  Rank(expanded)</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 输入和输出元素数量必须一致 |
| FP32 | 支持 | 输入和输出元素数量必须一致 |

### Flatten<a name="ZH-CN_TOPIC_0000002515124725" id="ZH-CN_TOPIC_0000002515124725"></a>

**功能描述<a name="section144144283412"></a>**

对多维Tensor进行维度展平。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Flatten参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="16.93830616938306%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.14848515148485%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.388461153884613%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.777122287771224%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.747625237476253%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1111813635119"><a name="p1111813635119"></a><a name="p1111813635119"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7349185545010"><a name="p7349185545010"></a><a name="p7349185545010"></a>-</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>flattened</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p187213431103"><a name="p187213431103"></a><a name="p187213431103"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1677592812"><a name="p1677592812"></a><a name="p1677592812"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p83481655175017"><a name="p83481655175017"></a><a name="p83481655175017"></a>-</p>
</td>
</tr>
<tr id="row2141153352915"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p4141143320299"><a name="p4141143320299"></a><a name="p4141143320299"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p151411933132915"><a name="p151411933132915"></a><a name="p151411933132915"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p1014183322911"><a name="p1014183322911"></a><a name="p1014183322911"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p714153362912"><a name="p714153362912"></a><a name="p714153362912"></a>展平终止维度 (不包括），默认为1。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p458116104314"><a name="p458116104314"></a><a name="p458116104314"></a>-Rank(tensor) <= axis <=  Rank(tensor)</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | 输入和输出元素数量必须一致 |
| FP32 | 支持 | 输入和输出元素数量必须一致 |

### Abs<a name="ZH-CN_TOPIC_0000002485239888" id="ZH-CN_TOPIC_0000002485239888"></a>

**功能描述<a name="section144144283412"></a>**

对张量的每个元素做绝对值运算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Abs参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 要求使用FP32静态非空张量 |

### Ceil<a name="ZH-CN_TOPIC_0000002517399797" id="ZH-CN_TOPIC_0000002517399797"></a>

**功能描述<a name="section144144283412"></a>**

对张量中的每个元素做向上取整操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Ceil参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Cos<a name="ZH-CN_TOPIC_0000002517479775" id="ZH-CN_TOPIC_0000002517479775"></a>

**功能描述<a name="section144144283412"></a>**

对张量中的每个元素做余弦操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Cos参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p316239246"><a name="p316239246"></a><a name="p316239246"></a>[-1, 1]</p>
</td>
</tr>
</tbody>
</table>

### Exp<a name="ZH-CN_TOPIC_0000002485399854" id="ZH-CN_TOPIC_0000002485399854"></a>

**功能描述<a name="section144144283412"></a>**

对张量中的每个元素做指数计算操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Exp参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p17329612553"><a name="p17329612553"></a><a name="p17329612553"></a>(0, 正无穷)</p>
</td>
</tr>
</tbody>
</table>

### Floor<a name="ZH-CN_TOPIC_0000002485239890" id="ZH-CN_TOPIC_0000002485239890"></a>

**功能描述<a name="section144144283412"></a>**

对张量中的每个元素做向下取整操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Floor参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Log<a name="ZH-CN_TOPIC_0000002517399799" id="ZH-CN_TOPIC_0000002517399799"></a>

**功能描述<a name="section144144283412"></a>**

对张量中的每个元素做对数计算操作（底数值为e）。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Log参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p12470145213415"><a name="p12470145213415"></a><a name="p12470145213415"></a>(0, 正无穷)</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Round<a name="ZH-CN_TOPIC_0000002517479777" id="ZH-CN_TOPIC_0000002517479777"></a>

**功能描述<a name="section144144283412"></a>**

对张量中的每个元素做四舍五入操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Round参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Sin<a name="ZH-CN_TOPIC_0000002485399856" id="ZH-CN_TOPIC_0000002485399856"></a>

**功能描述<a name="section144144283412"></a>**

对张量中的每个元素做正弦计算操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Sin参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p316239246"><a name="p316239246"></a><a name="p316239246"></a>[-1, 1]</p>
</td>
</tr>
</tbody>
</table>

### Sqrt<a name="ZH-CN_TOPIC_0000002485239892" id="ZH-CN_TOPIC_0000002485239892"></a>

**功能描述<a name="section144144283412"></a>**

对张量中的每个元素做平方根计算操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Sqrt参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>[0, 正无穷)</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>[0, 正无穷)</p>
</td>
</tr>
</tbody>
</table>

### BatchNormalization<a name="ZH-CN_TOPIC_0000002487717084" id="ZH-CN_TOPIC_0000002487717084"></a>

**功能描述<a name="section144144283412"></a>**

对输入张量做批归一化计算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  BatchNormalization参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="16.93830616938306%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.14848515148485%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.388461153884613%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.777122287771224%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.747625237476253%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1111813635119"><a name="p1111813635119"></a><a name="p1111813635119"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7349185545010"><a name="p7349185545010"></a><a name="p7349185545010"></a>-</p>
</td>
</tr>
<tr id="row15423221105011"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p814484714519"><a name="p814484714519"></a><a name="p814484714519"></a>scale</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p16144114785114"><a name="p16144114785114"></a><a name="p16144114785114"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p17144134765111"><a name="p17144134765111"></a><a name="p17144134765111"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p11441547135118"><a name="p11441547135118"></a><a name="p11441547135118"></a>输入张量的放缩系数，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p16977195144313"><a name="p16977195144313"></a><a name="p16977195144313"></a>-</p>
</td>
</tr>
<tr id="row1742542125016"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p11150123511475"><a name="p11150123511475"></a><a name="p11150123511475"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p8151173534717"><a name="p8151173534717"></a><a name="p8151173534717"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p19151163511479"><a name="p19151163511479"></a><a name="p19151163511479"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p4151635144712"><a name="p4151635144712"></a><a name="p4151635144712"></a>偏置向量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p99771651174319"><a name="p99771651174319"></a><a name="p99771651174319"></a>-</p>
</td>
</tr>
<tr id="row4969183704815"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p697019372481"><a name="p697019372481"></a><a name="p697019372481"></a>input_mean</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p139706378484"><a name="p139706378484"></a><a name="p139706378484"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p18970113719482"><a name="p18970113719482"></a><a name="p18970113719482"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p4970137104810"><a name="p4970137104810"></a><a name="p4970137104810"></a><span>每个通道的全局均值</span>，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p189706375485"><a name="p189706375485"></a><a name="p189706375485"></a>-</p>
</td>
</tr>
<tr id="row72131842104819"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p2021374216485"><a name="p2021374216485"></a><a name="p2021374216485"></a>input_var</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p22141242174815"><a name="p22141242174815"></a><a name="p22141242174815"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p5214184254818"><a name="p5214184254818"></a><a name="p5214184254818"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p421416424485"><a name="p421416424485"></a><a name="p421416424485"></a><span>每个通道的全局方差</span>，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p182141742124818"><a name="p182141742124818"></a><a name="p182141742124818"></a>-</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p187213431103"><a name="p187213431103"></a><a name="p187213431103"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1677592812"><a name="p1677592812"></a><a name="p1677592812"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p83481655175017"><a name="p83481655175017"></a><a name="p83481655175017"></a>-</p>
</td>
</tr>
<tr id="row168911912143417"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p12286124112430"><a name="p12286124112430"></a><a name="p12286124112430"></a>epsilon</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p1299891713439"><a name="p1299891713439"></a><a name="p1299891713439"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p1551719012441"><a name="p1551719012441"></a><a name="p1551719012441"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p18141820435"><a name="p18141820435"></a><a name="p18141820435"></a>用于避免除零溢出（默认1e-5）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p458116104314"><a name="p458116104314"></a><a name="p458116104314"></a>-</p>
</td>
</tr>
</tbody>
</table>

### LayerNormalization<a name="ZH-CN_TOPIC_0000002519876961" id="ZH-CN_TOPIC_0000002519876961"></a>

**功能描述<a name="section144144283412"></a>**

对输入张量做层归一化计算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  LayerNormalization参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="16.93830616938306%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.14848515148485%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.388461153884613%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.777122287771224%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.747625237476253%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1111813635119"><a name="p1111813635119"></a><a name="p1111813635119"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7349185545010"><a name="p7349185545010"></a><a name="p7349185545010"></a>-</p>
</td>
</tr>
<tr id="row15423221105011"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p814484714519"><a name="p814484714519"></a><a name="p814484714519"></a>scale</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p16144114785114"><a name="p16144114785114"></a><a name="p16144114785114"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p17144134765111"><a name="p17144134765111"></a><a name="p17144134765111"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p11441547135118"><a name="p11441547135118"></a><a name="p11441547135118"></a>输入张量的放缩系数，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p16977195144313"><a name="p16977195144313"></a><a name="p16977195144313"></a>-</p>
</td>
</tr>
<tr id="row1742542125016"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p11150123511475"><a name="p11150123511475"></a><a name="p11150123511475"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p8151173534717"><a name="p8151173534717"></a><a name="p8151173534717"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p19151163511479"><a name="p19151163511479"></a><a name="p19151163511479"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p4151635144712"><a name="p4151635144712"></a><a name="p4151635144712"></a>偏置向量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p99771651174319"><a name="p99771651174319"></a><a name="p99771651174319"></a>-</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p187213431103"><a name="p187213431103"></a><a name="p187213431103"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1677592812"><a name="p1677592812"></a><a name="p1677592812"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p83481655175017"><a name="p83481655175017"></a><a name="p83481655175017"></a>-</p>
</td>
</tr>
<tr id="row168911912143417"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p12286124112430"><a name="p12286124112430"></a><a name="p12286124112430"></a>epsilon</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p1299891713439"><a name="p1299891713439"></a><a name="p1299891713439"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p1551719012441"><a name="p1551719012441"></a><a name="p1551719012441"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p18141820435"><a name="p18141820435"></a><a name="p18141820435"></a>用于避免除零溢出（默认1e-5）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p458116104314"><a name="p458116104314"></a><a name="p458116104314"></a>-</p>
</td>
</tr>
<tr id="row447481785514"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p8474151710555"><a name="p8474151710555"></a><a name="p8474151710555"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p124741117145516"><a name="p124741117145516"></a><a name="p124741117145516"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p13474417165516"><a name="p13474417165516"></a><a name="p13474417165516"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p11474181735514"><a name="p11474181735514"></a><a name="p11474181735514"></a>用于指定归一化的维度（默认-1）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7178121810585"><a name="p7178121810585"></a><a name="p7178121810585"></a>规格约束：-Rank(input) <= axis <  Rank(input)</p>
</td>
</tr>
</tbody>
</table>

### LpNormalization<a name="ZH-CN_TOPIC_0000002519796953" id="ZH-CN_TOPIC_0000002519796953"></a>

**功能描述<a name="section144144283412"></a>**

沿指定轴，用 1 或 2 阶 Lp 范数对输入张量执行归一化计算。

**参数说明<a name="section15195134816462"></a>**

**表 1**  LpNormalization参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="16.93830616938306%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.14848515148485%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="15.388461153884613%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.777122287771224%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.747625237476253%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1111813635119"><a name="p1111813635119"></a><a name="p1111813635119"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7349185545010"><a name="p7349185545010"></a><a name="p7349185545010"></a>-</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p187213431103"><a name="p187213431103"></a><a name="p187213431103"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p1677592812"><a name="p1677592812"></a><a name="p1677592812"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p83481655175017"><a name="p83481655175017"></a><a name="p83481655175017"></a>-</p>
</td>
</tr>
<tr id="row168911912143417"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p12286124112430"><a name="p12286124112430"></a><a name="p12286124112430"></a>p</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p1299891713439"><a name="p1299891713439"></a><a name="p1299891713439"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p1551719012441"><a name="p1551719012441"></a><a name="p1551719012441"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p18141820435"><a name="p18141820435"></a><a name="p18141820435"></a><span>用于指定 Lp 范数的阶数</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p458116104314"><a name="p458116104314"></a><a name="p458116104314"></a>规格约束：只支持取值1或2</p>
</td>
</tr>
<tr id="row447481785514"><td class="cellrowborder" valign="top" width="16.93830616938306%" headers="mcps1.2.6.1.1 "><p id="p8474151710555"><a name="p8474151710555"></a><a name="p8474151710555"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="15.14848515148485%" headers="mcps1.2.6.1.2 "><p id="p124741117145516"><a name="p124741117145516"></a><a name="p124741117145516"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="15.388461153884613%" headers="mcps1.2.6.1.3 "><p id="p13474417165516"><a name="p13474417165516"></a><a name="p13474417165516"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="28.777122287771224%" headers="mcps1.2.6.1.4 "><p id="p11474181735514"><a name="p11474181735514"></a><a name="p11474181735514"></a>用于指定归一化的维度（默认-1）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.747625237476253%" headers="mcps1.2.6.1.5 "><p id="p7178121810585"><a name="p7178121810585"></a><a name="p7178121810585"></a>规格约束：-Rank(input) <= axis <  Rank(input)</p>
</td>
</tr>
</tbody>
</table>

### Slice<a name="ZH-CN_TOPIC_0000002528453623" id="ZH-CN_TOPIC_0000002528453623"></a>

**功能描述<a name="section144144283412"></a>**

从输入张量中沿指定轴提取子张量。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Slice参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="14.06%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.62%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.940000000000001%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="35.67%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.71%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row1039757204714"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p163973710472"><a name="p163973710472"></a><a name="p163973710472"></a>starts</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p939877194717"><a name="p939877194717"></a><a name="p939877194717"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p173987784715"><a name="p173987784715"></a><a name="p173987784715"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p16309115118523"><a name="p16309115118523"></a><a name="p16309115118523"></a>维度为1D，<span>对应 </span>axes<span> 中每个轴的</span><span>起始索引</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p17661841144412"><a name="p17661841144412"></a><a name="p17661841144412"></a>规格约束：starts为离线常量</p>
</td>
</tr>
<tr id="row19512413114716"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p6512181384714"><a name="p6512181384714"></a><a name="p6512181384714"></a>ends</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p1051241310472"><a name="p1051241310472"></a><a name="p1051241310472"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p25121813154717"><a name="p25121813154717"></a><a name="p25121813154717"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p5806154818521"><a name="p5806154818521"></a><a name="p5806154818521"></a>维度为1D，<span>对应 </span>axes<span> 中每个轴的</span><span>结束索引</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p1416923545"><a name="p1416923545"></a><a name="p1416923545"></a>规格约束：ends为离线常量</p>
</td>
</tr>
<tr id="row562612196478"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p362651919474"><a name="p362651919474"></a><a name="p362651919474"></a>axes（可选）</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p2626191916478"><a name="p2626191916478"></a><a name="p2626191916478"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p126261119164714"><a name="p126261119164714"></a><a name="p126261119164714"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p9161847115212"><a name="p9161847115212"></a><a name="p9161847115212"></a>维度为1D，<span>指定要切片的轴（默认值为 </span>[0,1,...,r-1]）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p165961325541"><a name="p165961325541"></a><a name="p165961325541"></a>规格约束：axes为离线常量</p>
</td>
</tr>
<tr id="row57411716194713"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p1174116165478"><a name="p1174116165478"></a><a name="p1174116165478"></a>steps（可选）</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p9741316184714"><a name="p9741316184714"></a><a name="p9741316184714"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p574141616470"><a name="p574141616470"></a><a name="p574141616470"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p17410164475"><a name="p17410164475"></a><a name="p17410164475"></a>维度为1D，<span>对应 </span>axes<span> 中每个轴的切片步长</span><span>（默认值为[1,1…,1]</span><span>）</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p152310335413"><a name="p152310335413"></a><a name="p152310335413"></a>规格约束：steps为离线常量</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | starts、ends、axes和steps必须为转换期常量 |

### GlobalMaxPool<a name="ZH-CN_TOPIC_0000002497018654" id="ZH-CN_TOPIC_0000002497018654"></a>

**功能描述<a name="section144144283412"></a>**

对输入张量除通道轴以外进行最大池化操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  GlobalMaxpool参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="14.06%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.62%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.940000000000001%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="35.67%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.71%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度为3D/4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>规格约束：仅支持3D、4D</p>
</td>
</tr>
<tr id="row1039757204714"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p163973710472"><a name="p163973710472"></a><a name="p163973710472"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p939877194717"><a name="p939877194717"></a><a name="p939877194717"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p173987784715"><a name="p173987784715"></a><a name="p173987784715"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p16309115118523"><a name="p16309115118523"></a><a name="p16309115118523"></a>输出张量，维度为3D/4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p2032891175417"><a name="p2032891175417"></a><a name="p2032891175417"></a>-</p>
</td>
</tr>
</tbody>
</table>

### GlobalAveragePool<a name="ZH-CN_TOPIC_0000002496698634" id="ZH-CN_TOPIC_0000002496698634"></a>

**功能描述<a name="section144144283412"></a>**

对输入张量除通道轴以外进行平均池化操作。

**参数说明<a name="section15195134816462"></a>**

**表 1**  GlobalAveragePool参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="14.06%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.62%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.940000000000001%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="35.67%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.71%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度为3D/4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p17531139205411"><a name="p17531139205411"></a><a name="p17531139205411"></a>规格约束：仅支持3D、4D</p>
</td>
</tr>
<tr id="row1039757204714"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p163973710472"><a name="p163973710472"></a><a name="p163973710472"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p939877194717"><a name="p939877194717"></a><a name="p939877194717"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p173987784715"><a name="p173987784715"></a><a name="p173987784715"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p16309115118523"><a name="p16309115118523"></a><a name="p16309115118523"></a>输出张量，维度为3D/4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p17661841144412"><a name="p17661841144412"></a><a name="p17661841144412"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Transpose<a name="ZH-CN_TOPIC_0000002498635600" id="ZH-CN_TOPIC_0000002498635600"></a>

**功能描述<a name="section144144283412"></a>**

对输入张量进行转置。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Transpose参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="14.06%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.62%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.940000000000001%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="35.67%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.71%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row1039757204714"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p163973710472"><a name="p163973710472"></a><a name="p163973710472"></a>perm</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p939877194717"><a name="p939877194717"></a><a name="p939877194717"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p173987784715"><a name="p173987784715"></a><a name="p173987784715"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p499234194217"><a name="p499234194217"></a><a name="p499234194217"></a>输入张量的维度重排顺序。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p2402123716292"><a name="p2402123716292"></a><a name="p2402123716292"></a>规格约束：不支持perm=[0,3,1,2]、[0,2,3,1]的Transpose单算子转换</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="14.06%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.62%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.940000000000001%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="35.67%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.71%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 支持 | perm必须是合法的常量全排列 |
| FP32 | 支持 | perm必须是合法的常量全排列 |

### ArgMax<a name="ZH-CN_TOPIC_0000002510106182" id="ZH-CN_TOPIC_0000002510106182"></a>

**功能描述<a name="section144144283412"></a>**

在张量的指定维度上，计算并返回最大值对应的位置索引。

**参数说明<a name="section143505379395"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>仅支持float类型，不支持int8类型。

**表 1**  ArgMax参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.22%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.01%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>reduced</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为1D/2D/3D/4D，格式为N/ND/NCW/NCHW，取决于参数配置。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>-</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1159893018254"><a name="p1159893018254"></a><a name="p1159893018254"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a><span>指定在张量中执行计算逻辑</span>的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p125981130162518"><a name="p125981130162518"></a><a name="p125981130162518"></a>规格约束：-rank(value)<=axis<rank(value)，rank为张量的秩。默认为0</p>
</td>
</tr>
<tr id="row3838183521112"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p58391835121118"><a name="p58391835121118"></a><a name="p58391835121118"></a>keepdims</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p10839435141118"><a name="p10839435141118"></a><a name="p10839435141118"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p68391335181117"><a name="p68391335181117"></a><a name="p68391335181117"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p6839183591113"><a name="p6839183591113"></a><a name="p6839183591113"></a><span>控制是否保留被降维的轴</span><span>。</span></p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1083963571117"><a name="p1083963571117"></a><a name="p1083963571117"></a>规格约束：只支持取值0或1。默认为1</p>
</td>
</tr>
<tr id="row1355283711302"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p1055253715307"><a name="p1055253715307"></a><a name="p1055253715307"></a>select_last_index</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p20552193723016"><a name="p20552193723016"></a><a name="p20552193723016"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p2552183773017"><a name="p2552183773017"></a><a name="p2552183773017"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p13552537173010"><a name="p13552537173010"></a><a name="p13552537173010"></a><span>控制最大值重复时的索引选择策略。为 </span>0<span> 时返回</span><span>第一个</span><span>最大值的索引；为 </span>1<span> 时返回</span><span>最后一个</span><span>最大值的索引。</span></p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p125521237123011"><a name="p125521237123011"></a><a name="p125521237123011"></a>规格约束：只支持取值0或1。默认为0</p>
</td>
</tr>
</tbody>
</table>

### ArgMin<a name="ZH-CN_TOPIC_0000002541586163" id="ZH-CN_TOPIC_0000002541586163"></a>

**功能描述<a name="section167661757173918"></a>**

在张量的指定维度上，计算并返回最小值对应的位置索引。

**参数说明<a name="section3766155710394"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>仅支持float类型，不支持int8类型。

**表 1**  ArgMin参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.22%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.01%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>reduced</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为1D/2D/3D/4D，格式为N/ND/NCW/NCHW，取决于参数配置。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>-</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1159893018254"><a name="p1159893018254"></a><a name="p1159893018254"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a><span>指定在张量中执行计算逻辑</span>的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p125981130162518"><a name="p125981130162518"></a><a name="p125981130162518"></a>规格约束：-rank(value)<=axis<rank(value)，rank为张量的秩。默认为0</p>
</td>
</tr>
<tr id="row3838183521112"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p58391835121118"><a name="p58391835121118"></a><a name="p58391835121118"></a>keepdims</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p10839435141118"><a name="p10839435141118"></a><a name="p10839435141118"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p68391335181117"><a name="p68391335181117"></a><a name="p68391335181117"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p6839183591113"><a name="p6839183591113"></a><a name="p6839183591113"></a><span>控制是否保留被降维的轴</span><span>。</span></p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1083963571117"><a name="p1083963571117"></a><a name="p1083963571117"></a>规格约束：只支持取值0或1。默认为1</p>
</td>
</tr>
<tr id="row1355283711302"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p1055253715307"><a name="p1055253715307"></a><a name="p1055253715307"></a>select_last_index</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p20552193723016"><a name="p20552193723016"></a><a name="p20552193723016"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p2552183773017"><a name="p2552183773017"></a><a name="p2552183773017"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p13552537173010"><a name="p13552537173010"></a><a name="p13552537173010"></a><span>控制最小值重复时的索引选择策略。为 </span>0<span> 时返回</span><span>第一个</span><span>最小值的索引；为 </span>1<span> 时返回</span><span>最后一个</span><span>最小值的索引。</span></p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p125521237123011"><a name="p125521237123011"></a><a name="p125521237123011"></a>规格约束：只支持取值0或1。默认为0</p>
</td>
</tr>
</tbody>
</table>

### Div<a name="ZH-CN_TOPIC_0000002516261490" id="ZH-CN_TOPIC_0000002516261490"></a>

**功能描述<a name="section167661757173918"></a>**

对两输入张量进行除法运算。

**参数说明<a name="section3766155710394"></a>**

**表 1**  Div参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.22%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.01%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p10833525154211"><a name="p10833525154211"></a><a name="p10833525154211"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p864712157434"><a name="p864712157434"></a><a name="p864712157434"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p16178165364319"><a name="p16178165364319"></a><a name="p16178165364319"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>-</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1056142311422"><a name="p1056142311422"></a><a name="p1056142311422"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p0332121194412"><a name="p0332121194412"></a><a name="p0332121194412"></a>-</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | 支持范围取决于输入角色和广播规格 |

### Mod<a name="ZH-CN_TOPIC_0000002600000004" id="ZH-CN_TOPIC_0000002600000004"></a>

**功能描述<a name="section167661757173919"></a>**

对两输入张量进行取模运算。

**参数说明<a name="section3766155710395"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Mod算子不支持量化。

**表 1**  Mod参数概览

<a name="table4179355155020"></a>
<table><thead align="left"><tr id="row417995510505"><th class="cellrowborder" valign="top" width="13.22%" id="mcps1.2.6.1.1"><p id="p369065912568"><a name="p369065912568"></a><a name="p369065912568"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.01%" id="mcps1.2.6.1.2"><p id="p4185174319553"><a name="p4185174319553"></a><a name="p4185174319553"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599570"><a name="p769019599570"></a><a name="p769019599570"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919569"><a name="p1069045919569"></a><a name="p1069045919569"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913568"><a name="p1769075913568"></a><a name="p1769075913568"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045218"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p145351923959"><a name="p145351923959"></a><a name="p145351923959"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p85343231058"><a name="p85343231058"></a><a name="p85343231058"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231657"><a name="p45333231657"></a><a name="p45333231657"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178446"><a name="p1950510178446"></a><a name="p1950510178446"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584315"><a name="p1037517584315"></a><a name="p1037517584315"></a>-</p>
</td>
</tr>
<tr id="row163619594920"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p106376574913"><a name="p106376574913"></a><a name="p106376574913"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p10833525154212"><a name="p10833525154212"></a><a name="p10833525154212"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p864712157435"><a name="p864712157435"></a><a name="p864712157435"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p16178165364320"><a name="p16178165364320"></a><a name="p16178165364320"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554917"><a name="p106371554917"></a><a name="p106371554917"></a>-</p>
</td>
</tr>
<tr id="row10598163022521"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p19598930132516"><a name="p19598930132516"></a><a name="p19598930132516"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1056142311423"><a name="p1056142311423"></a><a name="p1056142311423"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192512"><a name="p155981630192512"></a><a name="p155981630192512"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122516"><a name="p15598130122516"></a><a name="p15598130122516"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p0332121194413"><a name="p0332121194413"></a><a name="p0332121194413"></a>-</p>
</td>
</tr>
<tr id="row12231555153218"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p1623125523216"><a name="p1623125523216"></a><a name="p1623125523216"></a>fmod</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1123115573219"><a name="p1123115573219"></a><a name="p1123115573219"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p42316550322"><a name="p42316550322"></a><a name="p42316550322"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p14231955173217"><a name="p14231955173217"></a><a name="p14231955173217"></a>取模方式，0表示truncate模式，1表示floor模式。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1223105583216"><a name="p1223105583216"></a><a name="p1223105583216"></a>配置范围：0/1</p>
</td>
</tr>
</tbody>
</table>


### Clip<a name="ZH-CN_TOPIC_0000002552815891" id="ZH-CN_TOPIC_0000002552815891"></a>

**功能描述<a name="section167661757173918"></a>**

对张量进行最大最小值截断操作。

**参数说明<a name="section3766155710394"></a>**

**表 1**  Clip参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.22%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.01%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>min</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p10833525154211"><a name="p10833525154211"></a><a name="p10833525154211"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p864712157434"><a name="p864712157434"></a><a name="p864712157434"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p16178165364319"><a name="p16178165364319"></a><a name="p16178165364319"></a>输入张量，维度为标量。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>-</p>
</td>
</tr>
<tr id="row119971026124210"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p1599742614219"><a name="p1599742614219"></a><a name="p1599742614219"></a>max</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p99970265421"><a name="p99970265421"></a><a name="p99970265421"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p1999714261425"><a name="p1999714261425"></a><a name="p1999714261425"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p2036135617426"><a name="p2036135617426"></a><a name="p2036135617426"></a>输入张量，维度为标量。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p7997112664216"><a name="p7997112664216"></a><a name="p7997112664216"></a>-</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1056142311422"><a name="p1056142311422"></a><a name="p1056142311422"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p0332121194412"><a name="p0332121194412"></a><a name="p0332121194412"></a>-</p>
</td>
</tr>
</tbody>
</table>

### ReduceMax<a name="ZH-CN_TOPIC_0000002557401349" id="ZH-CN_TOPIC_0000002557401349"></a>

**功能描述<a name="section167661757173918"></a>**

对指定维度的张量进行最大值归约计算。

**参数说明<a name="section3766155710394"></a>**

**表 1**  ReduceMax参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.58%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.65%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p10833525154211"><a name="p10833525154211"></a><a name="p10833525154211"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p864712157434"><a name="p864712157434"></a><a name="p864712157434"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p16178165364319"><a name="p16178165364319"></a><a name="p16178165364319"></a>输入张量，维度为1D，指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，不支持axis为空list</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>reduced</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1056142311422"><a name="p1056142311422"></a><a name="p1056142311422"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p0332121194412"><a name="p0332121194412"></a><a name="p0332121194412"></a>-</p>
</td>
</tr>
<tr id="row12231555153217"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p1623125523215"><a name="p1623125523215"></a><a name="p1623125523215"></a>keepdims</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1123115573218"><a name="p1123115573218"></a><a name="p1123115573218"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p42316550321"><a name="p42316550321"></a><a name="p42316550321"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p14231955173216"><a name="p14231955173216"></a><a name="p14231955173216"></a>是否需要保留归约轴的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1223105583215"><a name="p1223105583215"></a><a name="p1223105583215"></a>配置范围：0/1</p>
</td>
</tr>
<tr id="row116605973217"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p7167959113216"><a name="p7167959113216"></a><a name="p7167959113216"></a>noop_with_empty_axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p73022429331"><a name="p73022429331"></a><a name="p73022429331"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p51671259193214"><a name="p51671259193214"></a><a name="p51671259193214"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p19167115913211"><a name="p19167115913211"></a><a name="p19167115913211"></a>定义归约轴为空时的行为。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p516765919329"><a name="p516765919329"></a><a name="p516765919329"></a>规格约束：不支持配置</p>
</td>
</tr>
</tbody>
</table>

### ReduceMin<a name="ZH-CN_TOPIC_0000002526441430" id="ZH-CN_TOPIC_0000002526441430"></a>

**功能描述<a name="section167661757173918"></a>**

对指定维度的张量进行最小值归约计算。

**参数说明<a name="section3766155710394"></a>**

**表 1**  ReduceMin参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.58%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.65%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p10833525154211"><a name="p10833525154211"></a><a name="p10833525154211"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p864712157434"><a name="p864712157434"></a><a name="p864712157434"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p18451820983"><a name="p18451820983"></a><a name="p18451820983"></a>输入张量，维度为1D，指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，不支持axis为空list</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>reduced</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1056142311422"><a name="p1056142311422"></a><a name="p1056142311422"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p0332121194412"><a name="p0332121194412"></a><a name="p0332121194412"></a>-</p>
</td>
</tr>
<tr id="row12231555153217"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p1623125523215"><a name="p1623125523215"></a><a name="p1623125523215"></a>keepdims</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1123115573218"><a name="p1123115573218"></a><a name="p1123115573218"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p42316550321"><a name="p42316550321"></a><a name="p42316550321"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p14231955173216"><a name="p14231955173216"></a><a name="p14231955173216"></a>是否需要保留归约轴的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1223105583215"><a name="p1223105583215"></a><a name="p1223105583215"></a>配置范围：0/1</p>
</td>
</tr>
<tr id="row116605973217"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p7167959113216"><a name="p7167959113216"></a><a name="p7167959113216"></a>noop_with_empty_axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p73022429331"><a name="p73022429331"></a><a name="p73022429331"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p51671259193214"><a name="p51671259193214"></a><a name="p51671259193214"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p19167115913211"><a name="p19167115913211"></a><a name="p19167115913211"></a>定义归约轴为空时的行为。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p516765919329"><a name="p516765919329"></a><a name="p516765919329"></a>规格约束：不支持配置</p>
</td>
</tr>
</tbody>
</table>

### ReduceSum<a name="ZH-CN_TOPIC_0000002557481311" id="ZH-CN_TOPIC_0000002557481311"></a>

**功能描述<a name="section167661757173918"></a>**

对指定维度的张量进行求和归约计算。

**参数说明<a name="section3766155710394"></a>**

**表 1**  ReduceSum参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.58%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.65%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p10833525154211"><a name="p10833525154211"></a><a name="p10833525154211"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p864712157434"><a name="p864712157434"></a><a name="p864712157434"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p16178165364319"><a name="p16178165364319"></a><a name="p16178165364319"></a>输入张量，维度为1D，指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，不支持axis为空list</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>reduced</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1056142311422"><a name="p1056142311422"></a><a name="p1056142311422"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p0332121194412"><a name="p0332121194412"></a><a name="p0332121194412"></a>-</p>
</td>
</tr>
<tr id="row12231555153217"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p1623125523215"><a name="p1623125523215"></a><a name="p1623125523215"></a>keepdims</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1123115573218"><a name="p1123115573218"></a><a name="p1123115573218"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p42316550321"><a name="p42316550321"></a><a name="p42316550321"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p14231955173216"><a name="p14231955173216"></a><a name="p14231955173216"></a>是否需要保留归约轴的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1223105583215"><a name="p1223105583215"></a><a name="p1223105583215"></a>配置范围：0/1</p>
</td>
</tr>
<tr id="row116605973217"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p7167959113216"><a name="p7167959113216"></a><a name="p7167959113216"></a>noop_with_empty_axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p73022429331"><a name="p73022429331"></a><a name="p73022429331"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p51671259193214"><a name="p51671259193214"></a><a name="p51671259193214"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p19167115913211"><a name="p19167115913211"></a><a name="p19167115913211"></a>定义归约轴为空时的行为。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p516765919329"><a name="p516765919329"></a><a name="p516765919329"></a>规格约束：不支持配置</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | rank为1～8，axes必须为转换期常量 |

### ReduceMean<a name="ZH-CN_TOPIC_0000002526281478" id="ZH-CN_TOPIC_0000002526281478"></a>

**功能描述<a name="section167661757173918"></a>**

对指定维度的张量进行均值归约计算。

**参数说明<a name="section3766155710394"></a>**

**表 1**  ReduceMean参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.58%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.65%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584314"><a name="p1037517584314"></a><a name="p1037517584314"></a>-</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p10833525154211"><a name="p10833525154211"></a><a name="p10833525154211"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p864712157434"><a name="p864712157434"></a><a name="p864712157434"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p5952244184"><a name="p5952244184"></a><a name="p5952244184"></a>输入张量，维度为1D，指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，不支持axis为空list</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>reduced</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1056142311422"><a name="p1056142311422"></a><a name="p1056142311422"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p0332121194412"><a name="p0332121194412"></a><a name="p0332121194412"></a>-</p>
</td>
</tr>
<tr id="row12231555153217"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p1623125523215"><a name="p1623125523215"></a><a name="p1623125523215"></a>keepdims</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1123115573218"><a name="p1123115573218"></a><a name="p1123115573218"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p42316550321"><a name="p42316550321"></a><a name="p42316550321"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p14231955173216"><a name="p14231955173216"></a><a name="p14231955173216"></a>是否需要保留归约轴的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1223105583215"><a name="p1223105583215"></a><a name="p1223105583215"></a>配置范围：0/1</p>
</td>
</tr>
<tr id="row116605973217"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p7167959113216"><a name="p7167959113216"></a><a name="p7167959113216"></a>noop_with_empty_axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p73022429331"><a name="p73022429331"></a><a name="p73022429331"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p51671259193214"><a name="p51671259193214"></a><a name="p51671259193214"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p19167115913211"><a name="p19167115913211"></a><a name="p19167115913211"></a>定义归约轴为空时的行为。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p516765919329"><a name="p516765919329"></a><a name="p516765919329"></a>规格约束：不支持配置</p>
</td>
</tr>
</tbody>
</table>

**训练支持规格**

| 训练模式 | 支持情况 | 规格约束 |
|---|---|---|
| QAS INT8 | 不支持 | - |
| FP32 | 支持 | rank为1～8，axes必须为转换期常量 |

### ReduceL1<a name="ZH-CN_TOPIC_0000002600000005" id="ZH-CN_TOPIC_0000002600000005"></a>

**功能描述<a name="section167661757173920"></a>**

对指定维度的张量进行L1范数归约计算。

**参数说明<a name="section3766155710396"></a>**

**表 1**  ReduceL1参数概览

<a name="table4179355155021"></a>
<table><thead align="left"><tr id="row417995510506"><th class="cellrowborder" valign="top" width="13.58%" id="mcps1.2.6.1.1"><p id="p369065912569"><a name="p369065912569"></a><a name="p369065912569"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.65%" id="mcps1.2.6.1.2"><p id="p4185174319554"><a name="p4185174319554"></a><a name="p4185174319554"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599571"><a name="p769019599571"></a><a name="p769019599571"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919570"><a name="p1069045919570"></a><a name="p1069045919570"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913569"><a name="p1769075913569"></a><a name="p1769075913569"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045219"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p145351923960"><a name="p145351923960"></a><a name="p145351923960"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p85343231059"><a name="p85343231059"></a><a name="p85343231059"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231658"><a name="p45333231658"></a><a name="p45333231658"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178447"><a name="p1950510178447"></a><a name="p1950510178447"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584316"><a name="p1037517584316"></a><a name="p1037517584316"></a>-</p>
</td>
</tr>
<tr id="row163619594921"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p106376574914"><a name="p106376574914"></a><a name="p106376574914"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p10833525154213"><a name="p10833525154213"></a><a name="p10833525154213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p864712157436"><a name="p864712157436"></a><a name="p864712157436"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p5952244185"><a name="p5952244185"></a><a name="p5952244185"></a>输入张量，维度为1D，指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554918"><a name="p106371554918"></a><a name="p106371554918"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))</p>
</td>
</tr>
<tr id="row10598163022522"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p19598930132517"><a name="p19598930132517"></a><a name="p19598930132517"></a>reduced</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1056142311424"><a name="p1056142311424"></a><a name="p1056142311424"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192513"><a name="p155981630192513"></a><a name="p155981630192513"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122517"><a name="p15598130122517"></a><a name="p15598130122517"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p0332121194414"><a name="p0332121194414"></a><a name="p0332121194414"></a>-</p>
</td>
</tr>
<tr id="row12231555153219"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p1623125523217"><a name="p1623125523217"></a><a name="p1623125523217"></a>keepdims</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1123115573220"><a name="p1123115573220"></a><a name="p1123115573220"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p42316550323"><a name="p42316550323"></a><a name="p42316550323"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p14231955173218"><a name="p14231955173218"></a><a name="p14231955173218"></a>是否需要保留归约轴的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1223105583217"><a name="p1223105583217"></a><a name="p1223105583217"></a>配置范围：0/1</p>
</td>
</tr>
<tr id="row116605973218"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p7167959113217"><a name="p7167959113217"></a><a name="p7167959113217"></a>noop_with_empty_axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p73022429332"><a name="p73022429332"></a><a name="p73022429332"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p51671259193215"><a name="p51671259193215"></a><a name="p51671259193215"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p19167115913212"><a name="p19167115913212"></a><a name="p19167115913212"></a>定义归约轴为空时的行为。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p516765919330"><a name="p516765919330"></a><a name="p516765919330"></a>规格约束：不支持配置</p>
</td>
</tr>
</tbody>
</table>

### ReduceL2<a name="ZH-CN_TOPIC_0000002600000006" id="ZH-CN_TOPIC_0000002600000006"></a>

**功能描述<a name="section167661757173921"></a>**

对指定维度的张量进行L2范数归约计算。

**参数说明<a name="section3766155710397"></a>**

**表 1**  ReduceL2参数概览

<a name="table4179355155022"></a>
<table><thead align="left"><tr id="row417995510507"><th class="cellrowborder" valign="top" width="13.58%" id="mcps1.2.6.1.1"><p id="p369065912570"><a name="p369065912570"></a><a name="p369065912570"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.65%" id="mcps1.2.6.1.2"><p id="p4185174319555"><a name="p4185174319555"></a><a name="p4185174319555"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599572"><a name="p769019599572"></a><a name="p769019599572"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919571"><a name="p1069045919571"></a><a name="p1069045919571"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913570"><a name="p1769075913570"></a><a name="p1769075913570"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045220"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p145351923961"><a name="p145351923961"></a><a name="p145351923961"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p85343231060"><a name="p85343231060"></a><a name="p85343231060"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231659"><a name="p45333231659"></a><a name="p45333231659"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178448"><a name="p1950510178448"></a><a name="p1950510178448"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1037517584317"><a name="p1037517584317"></a><a name="p1037517584317"></a>-</p>
</td>
</tr>
<tr id="row163619594922"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p106376574915"><a name="p106376574915"></a><a name="p106376574915"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p10833525154214"><a name="p10833525154214"></a><a name="p10833525154214"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p864712157437"><a name="p864712157437"></a><a name="p864712157437"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p5952244186"><a name="p5952244186"></a><a name="p5952244186"></a>输入张量，维度为1D，指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554919"><a name="p106371554919"></a><a name="p106371554919"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))</p>
</td>
</tr>
<tr id="row10598163022523"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p19598930132518"><a name="p19598930132518"></a><a name="p19598930132518"></a>reduced</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1056142311425"><a name="p1056142311425"></a><a name="p1056142311425"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192514"><a name="p155981630192514"></a><a name="p155981630192514"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122518"><a name="p15598130122518"></a><a name="p15598130122518"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p0332121194415"><a name="p0332121194415"></a><a name="p0332121194415"></a>-</p>
</td>
</tr>
<tr id="row12231555153220"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p1623125523218"><a name="p1623125523218"></a><a name="p1623125523218"></a>keepdims</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p1123115573221"><a name="p1123115573221"></a><a name="p1123115573221"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p42316550324"><a name="p42316550324"></a><a name="p42316550324"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p14231955173219"><a name="p14231955173219"></a><a name="p14231955173219"></a>是否需要保留归约轴的维度。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1223105583218"><a name="p1223105583218"></a><a name="p1223105583218"></a>配置范围：0/1</p>
</td>
</tr>
<tr id="row116605973219"><td class="cellrowborder" valign="top" width="13.58%" headers="mcps1.2.6.1.1 "><p id="p7167959113218"><a name="p7167959113218"></a><a name="p7167959113218"></a>noop_with_empty_axes</p>
</td>
<td class="cellrowborder" valign="top" width="12.65%" headers="mcps1.2.6.1.2 "><p id="p73022429333"><a name="p73022429333"></a><a name="p73022429333"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p51671259193216"><a name="p51671259193216"></a><a name="p51671259193216"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p19167115913213"><a name="p19167115913213"></a><a name="p19167115913213"></a>定义归约轴为空时的行为。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p516765919331"><a name="p516765919331"></a><a name="p516765919331"></a>规格约束：不支持配置</p>
</td>
</tr>
</tbody>
</table>


### Cast<a name="ZH-CN_TOPIC_0000002526464964" id="ZH-CN_TOPIC_0000002526464964"></a>

**功能描述<a name="section167661757173918"></a>**

对输入张量进行数据类型的转换。

**参数说明<a name="section3766155710394"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Cast算子不支持量化。

**表 1**  Cast参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.22%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.01%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>数据类型仅支持float32、uint8、int8、int32</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>数据类型仅支持float32、uint8、int8、int32</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>round_mode</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1159893018254"><a name="p1159893018254"></a><a name="p1159893018254"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a>转换为 FLOAT8E8M0 类型时的舍入模式配置。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p516765919329"><a name="p516765919329"></a><a name="p516765919329"></a>规格约束：不支持配置</p>
</td>
</tr>
<tr id="row3838183521112"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p1879163715523"><a name="p1879163715523"></a><a name="p1879163715523"></a>saturate</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p10839435141118"><a name="p10839435141118"></a><a name="p10839435141118"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p68391335181117"><a name="p68391335181117"></a><a name="p68391335181117"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p6839183591113"><a name="p6839183591113"></a><a name="p6839183591113"></a>设定输入值超出目标类型取值范围时的转换行为，仅对float8类型转换有效。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p1083963571117"><a name="p1083963571117"></a><a name="p1083963571117"></a>规格约束：不支持配置</p>
</td>
</tr>
<tr id="row1355283711302"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p1055253715307"><a name="p1055253715307"></a><a name="p1055253715307"></a>to</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p20552193723016"><a name="p20552193723016"></a><a name="p20552193723016"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p2552183773017"><a name="p2552183773017"></a><a name="p2552183773017"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p13552537173010"><a name="p13552537173010"></a><a name="p13552537173010"></a>指定输入张量元素需要转换的目标数据类型。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p125521237123011"><a name="p125521237123011"></a><a name="p125521237123011"></a>规格约束：取值仅支持FLOAT、UINT8、INT8、INT32</p>
</td>
</tr>
</tbody>
</table>

### PRelu<a name="ZH-CN_TOPIC_0000002568693026" id="ZH-CN_TOPIC_0000002568693026"></a>

**功能描述<a name="section167661757173918"></a>**

对输入张量进行参数化 PRelu 激活处理。其在输入为非负值时保持原值，在输入为负值时根据斜率参数进行线性缩放。

**参数说明<a name="section63411171435"></a>**

**表 1**  PRelu参数概览

<a name="table95484381742"></a>
<table><thead align="left"><tr id="row55487385415"><th class="cellrowborder" valign="top" width="7.68%" id="mcps1.2.6.1.1"><p id="p4548123817416"><a name="p4548123817416"></a><a name="p4548123817416"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.86%" id="mcps1.2.6.1.2"><p id="p1054819381546"><a name="p1054819381546"></a><a name="p1054819381546"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="8.959999999999999%" id="mcps1.2.6.1.3"><p id="p354873813414"><a name="p354873813414"></a><a name="p354873813414"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="27.93%" id="mcps1.2.6.1.4"><p id="p154810381346"><a name="p154810381346"></a><a name="p154810381346"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="42.57%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row75486381541"><td class="cellrowborder" valign="top" width="7.68%" headers="mcps1.2.6.1.1 "><p id="p125485388410"><a name="p125485388410"></a><a name="p125485388410"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="12.86%" headers="mcps1.2.6.1.2 "><p id="p1454810381748"><a name="p1454810381748"></a><a name="p1454810381748"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="8.959999999999999%" headers="mcps1.2.6.1.3 "><p id="p195481038743"><a name="p195481038743"></a><a name="p195481038743"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.93%" headers="mcps1.2.6.1.4 "><p id="p854912385419"><a name="p854912385419"></a><a name="p854912385419"></a>待进行 PReLU 激活处理的数据，维度为1D / 2D / 3D / 4D。</p>
</td>
<td class="cellrowborder" valign="top" width="42.57%" headers="mcps1.2.6.1.5 "><p id="p45491138649"><a name="p45491138649"></a><a name="p45491138649"></a>数据类型仅支持 float32、int8；不限定具体数据格式。</p>
</td>
</tr>
<tr id="row35491338744"><td class="cellrowborder" valign="top" width="7.68%" headers="mcps1.2.6.1.1 "><p id="p1054915383410"><a name="p1054915383410"></a><a name="p1054915383410"></a>slope</p>
</td>
<td class="cellrowborder" valign="top" width="12.86%" headers="mcps1.2.6.1.2 "><p id="p154920381346"><a name="p154920381346"></a><a name="p154920381346"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="8.959999999999999%" headers="mcps1.2.6.1.3 "><p id="p14549738646"><a name="p14549738646"></a><a name="p14549738646"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.93%" headers="mcps1.2.6.1.4 "><p id="p10634155882616"><a name="p10634155882616"></a><a name="p10634155882616"></a>负半轴斜率参数，维度为0D / 1D / 2D / 3D / 4D。</p>
</td>
<td class="cellrowborder" valign="top" width="42.57%" headers="mcps1.2.6.1.5 "><p id="p854916389413"><a name="p854916389413"></a><a name="p854916389413"></a>数据类型仅支持 float32；不限定具体数据格式，但其形状需支持单向广播到 X 。</p>
</td>
</tr>
<tr id="row12549113810416"><td class="cellrowborder" valign="top" width="7.68%" headers="mcps1.2.6.1.1 "><p id="p15491838743"><a name="p15491838743"></a><a name="p15491838743"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="12.86%" headers="mcps1.2.6.1.2 "><p id="p1254913817417"><a name="p1254913817417"></a><a name="p1254913817417"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="8.959999999999999%" headers="mcps1.2.6.1.3 "><p id="p13549738642"><a name="p13549738642"></a><a name="p13549738642"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.93%" headers="mcps1.2.6.1.4 "><p id="p1054913810418"><a name="p1054913810418"></a><a name="p1054913810418"></a>输出张量，维度与 X 一致。</p>
</td>
<td class="cellrowborder" valign="top" width="42.57%" headers="mcps1.2.6.1.5 "><p id="p185490381646"><a name="p185490381646"></a><a name="p185490381646"></a>数据类型仅支持 float32、int8；维度与 X 一致。</p>
</td>
</tr>
</tbody>
</table>

>![](public_sys-resources/icon-note.gif) **说明：** 
>在量化过程中，PReLU 算子的第二输入保留 FP32 格式，以保证负半轴计算精度。

### CumSum<a name="ZH-CN_TOPIC_0000002568533372" id="ZH-CN_TOPIC_0000002568533372"></a>

**功能描述<a name="section167661757173918"></a>**

对输入张量沿指定维度进行累加求和处理，输出结果为该维度上的前缀和。

**参数说明<a name="section63411171435"></a>**

**表 1**  CumSum参数概览

<a name="table95484381742"></a>
<table><thead align="left"><tr id="row55487385415"><th class="cellrowborder" valign="top" width="10.299999999999999%" id="mcps1.2.6.1.1"><p id="p4548123817416"><a name="p4548123817416"></a><a name="p4548123817416"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.709999999999999%" id="mcps1.2.6.1.2"><p id="p1054819381546"><a name="p1054819381546"></a><a name="p1054819381546"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="8.32%" id="mcps1.2.6.1.3"><p id="p354873813414"><a name="p354873813414"></a><a name="p354873813414"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="27.689999999999998%" id="mcps1.2.6.1.4"><p id="p154810381346"><a name="p154810381346"></a><a name="p154810381346"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="40.98%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row75486381541"><td class="cellrowborder" valign="top" width="10.299999999999999%" headers="mcps1.2.6.1.1 "><p id="p125485388410"><a name="p125485388410"></a><a name="p125485388410"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="12.709999999999999%" headers="mcps1.2.6.1.2 "><p id="p1454810381748"><a name="p1454810381748"></a><a name="p1454810381748"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="8.32%" headers="mcps1.2.6.1.3 "><p id="p195481038743"><a name="p195481038743"></a><a name="p195481038743"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.689999999999998%" headers="mcps1.2.6.1.4 "><p id="p854912385419"><a name="p854912385419"></a><a name="p854912385419"></a>待进行累加求和处理的输入张量，维度为 1D / 2D / 3D / 4D。</p>
</td>
<td class="cellrowborder" valign="top" width="40.98%" headers="mcps1.2.6.1.5 "><p id="p45491138649"><a name="p45491138649"></a><a name="p45491138649"></a>数据类型仅支持 float32、int8；不限定具体数据格式。</p>
</td>
</tr>
<tr id="row35491338744"><td class="cellrowborder" valign="top" width="10.299999999999999%" headers="mcps1.2.6.1.1 "><p id="p1054915383410"><a name="p1054915383410"></a><a name="p1054915383410"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="12.709999999999999%" headers="mcps1.2.6.1.2 "><p id="p154920381346"><a name="p154920381346"></a><a name="p154920381346"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="8.32%" headers="mcps1.2.6.1.3 "><p id="p14549738646"><a name="p14549738646"></a><a name="p14549738646"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.689999999999998%" headers="mcps1.2.6.1.4 "><p id="p16576113045316"><a name="p16576113045316"></a><a name="p16576113045316"></a>进行累加求和的维度，维度为 0D。</p>
</td>
<td class="cellrowborder" valign="top" width="40.98%" headers="mcps1.2.6.1.5 "><p id="p854916389413"><a name="p854916389413"></a><a name="p854916389413"></a>数据类型仅支持 int32、int64；取值范围为 [-rank(input), rank(input))，当 axis 为负数时，表示从最后一个维度开始反向索引。</p>
</td>
</tr>
<tr id="row12549113810416"><td class="cellrowborder" valign="top" width="10.299999999999999%" headers="mcps1.2.6.1.1 "><p id="p15491838743"><a name="p15491838743"></a><a name="p15491838743"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="12.709999999999999%" headers="mcps1.2.6.1.2 "><p id="p1254913817417"><a name="p1254913817417"></a><a name="p1254913817417"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="8.32%" headers="mcps1.2.6.1.3 "><p id="p13549738642"><a name="p13549738642"></a><a name="p13549738642"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="27.689999999999998%" headers="mcps1.2.6.1.4 "><p id="p1054913810418"><a name="p1054913810418"></a><a name="p1054913810418"></a>沿 axis 维度进行累加求和后的结果。</p>
</td>
<td class="cellrowborder" valign="top" width="40.98%" headers="mcps1.2.6.1.5 "><p id="p185490381646"><a name="p185490381646"></a><a name="p185490381646"></a>数据类型和维度与 x一致。</p>
</td>
</tr>
<tr id="row3425133971415"><td class="cellrowborder" valign="top" width="10.299999999999999%" headers="mcps1.2.6.1.1 "><p id="p19426639191411"><a name="p19426639191411"></a><a name="p19426639191411"></a>exclusive</p>
</td>
<td class="cellrowborder" valign="top" width="12.709999999999999%" headers="mcps1.2.6.1.2 "><p id="p19426113912149"><a name="p19426113912149"></a><a name="p19426113912149"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="8.32%" headers="mcps1.2.6.1.3 "><p id="p10426113912149"><a name="p10426113912149"></a><a name="p10426113912149"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="27.689999999999998%" headers="mcps1.2.6.1.4 "><p id="p3426139111418"><a name="p3426139111418"></a><a name="p3426139111418"></a>是否采用排除当前元素的累加方式。</p>
</td>
<td class="cellrowborder" valign="top" width="40.98%" headers="mcps1.2.6.1.5 "><p id="p642683971412"><a name="p642683971412"></a><a name="p642683971412"></a>取值范围为 [0 , 1]，默认值为0。</p>
</td>
</tr>
<tr id="row163915351615"><td class="cellrowborder" valign="top" width="10.299999999999999%" headers="mcps1.2.6.1.1 "><p id="p763963191615"><a name="p763963191615"></a><a name="p763963191615"></a>reverse</p>
</td>
<td class="cellrowborder" valign="top" width="12.709999999999999%" headers="mcps1.2.6.1.2 "><p id="p963943121617"><a name="p963943121617"></a><a name="p963943121617"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="8.32%" headers="mcps1.2.6.1.3 "><p id="p18639113171615"><a name="p18639113171615"></a><a name="p18639113171615"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="27.689999999999998%" headers="mcps1.2.6.1.4 "><p id="p1863916311619"><a name="p1863916311619"></a><a name="p1863916311619"></a>是否沿指定维度反向累加。</p>
</td>
<td class="cellrowborder" valign="top" width="40.98%" headers="mcps1.2.6.1.5 "><p id="p422073914196"><a name="p422073914196"></a><a name="p422073914196"></a>取值范围为 [0 , 1]，默认值为0。</p>
</td>
</tr>
</tbody>
</table>

### ReverseSequence<a name="ZH-CN_TOPIC_0000002599187805" id="ZH-CN_TOPIC_0000002599187805"></a>

**功能描述<a name="section167661757173918"></a>**

对输入张量指定轴前N个数据进行反转。

**参数说明<a name="section172851342295"></a>**

**表 1**  ReverseSequence参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.22%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.01%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.370000000000001%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.940000000000005%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.370000000000001%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.940000000000005%" headers="mcps1.2.6.1.4 "><p id="p1950510178445"><a name="p1950510178445"></a><a name="p1950510178445"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>数据类型仅支持float32、uint8、int8、int32</p>
</td>
</tr>
<tr id="row10551185241"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p8555819241"><a name="p8555819241"></a><a name="p8555819241"></a>sequence_lens</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p165512815246"><a name="p165512815246"></a><a name="p165512815246"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.370000000000001%" headers="mcps1.2.6.1.3 "><p id="p115515818249"><a name="p115515818249"></a><a name="p115515818249"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.940000000000005%" headers="mcps1.2.6.1.4 "><p id="p10558802416"><a name="p10558802416"></a><a name="p10558802416"></a>输入张量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p25511814243"><a name="p25511814243"></a><a name="p25511814243"></a>数据类型仅支持int32，每个数据均满足0<=seq_len<=input_shape[time_axis]</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.370000000000001%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.940000000000005%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>数据类型仅支持float32、uint8、int8、int32</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>batch_axis</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1159893018254"><a name="p1159893018254"></a><a name="p1159893018254"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.370000000000001%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.940000000000005%" headers="mcps1.2.6.1.4 "><p id="p15598130122515"><a name="p15598130122515"></a><a name="p15598130122515"></a>批次轴的序号。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p516765919329"><a name="p516765919329"></a><a name="p516765919329"></a>默认为1，可支持缺省配置，必须与time_axis不同。仅支持0，1配置。</p>
</td>
</tr>
<tr id="row3838183521112"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p1879163715523"><a name="p1879163715523"></a><a name="p1879163715523"></a>time_axis</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p10839435141118"><a name="p10839435141118"></a><a name="p10839435141118"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.370000000000001%" headers="mcps1.2.6.1.3 "><p id="p68391335181117"><a name="p68391335181117"></a><a name="p68391335181117"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="32.940000000000005%" headers="mcps1.2.6.1.4 "><p id="p6839183591113"><a name="p6839183591113"></a><a name="p6839183591113"></a>反转轴的序号。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p15970115515271"><a name="p15970115515271"></a><a name="p15970115515271"></a>默认为0，可支持缺省配置，必须与batch_axis不同。仅支持0，1配置。</p>
</td>
</tr>
</tbody>
</table>

### Einsum<a name="ZH-CN_TOPIC_0000002599307751" id="ZH-CN_TOPIC_0000002599307751"></a>

**功能描述<a name="section167661757173918"></a>**

对输入张量进行简约求和，支持多输入的矩阵乘，对角，旋转，规约等操作。

**参数说明<a name="section3766155710394"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>详细规则请参考[Einsum](https://onnx.com.cn/onnx/operators/onnx__Einsum.html)，不支持...操作。

**表 1**  Einsum参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="13.22%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.01%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="12.379999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="32.93%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.46%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p1394261283415"><a name="p1394261283415"></a><a name="p1394261283415"></a>inputs</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p9664184133413"><a name="p9664184133413"></a><a name="p9664184133413"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>varList(tensor)</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p10939057123612"><a name="p10939057123612"></a><a name="p10939057123612"></a>输入张量列表，内部各张量维度为2D/3D/4D，格式分别为ND、NCW、NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p8544752203320"><a name="p8544752203320"></a><a name="p8544752203320"></a>数据类型仅支持float32、uint8、int8、int32</p>
</td>
</tr>
<tr id="row163619594919"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p106376574912"><a name="p106376574912"></a><a name="p106376574912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1063715511496"><a name="p1063715511496"></a><a name="p1063715511496"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p46372511497"><a name="p46372511497"></a><a name="p46372511497"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p186376512499"><a name="p186376512499"></a><a name="p186376512499"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p106371554916"><a name="p106371554916"></a><a name="p106371554916"></a>数据类型仅支持float32、uint8、int8、int32</p>
</td>
</tr>
<tr id="row10598163022520"><td class="cellrowborder" valign="top" width="13.22%" headers="mcps1.2.6.1.1 "><p id="p19598930132515"><a name="p19598930132515"></a><a name="p19598930132515"></a>equation</p>
</td>
<td class="cellrowborder" valign="top" width="13.01%" headers="mcps1.2.6.1.2 "><p id="p1159893018254"><a name="p1159893018254"></a><a name="p1159893018254"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="12.379999999999999%" headers="mcps1.2.6.1.3 "><p id="p155981630192511"><a name="p155981630192511"></a><a name="p155981630192511"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="32.93%" headers="mcps1.2.6.1.4 "><p id="p372210153334"><a name="p372210153334"></a><a name="p372210153334"></a>转换规则</p>
</td>
<td class="cellrowborder" valign="top" width="28.46%" headers="mcps1.2.6.1.5 "><p id="p2034918277332"><a name="p2034918277332"></a><a name="p2034918277332"></a>不支持...操作。</p>
</td>
</tr>
</tbody>
</table>

### LeakyRelu<a name="ZH-CN_TOPIC_0000002574170496" id="ZH-CN_TOPIC_0000002574170496"></a>

**功能描述<a name="section113841812134710"></a>**

对输入张量做LeakyRelu激活函数运算。在输入为非负值时保持原值，在输入为负值时根据缩放系数进行线性缩放。

**参数说明<a name="section15195134816462"></a>**

**表 1**  LeakyRelu参数概览

<a name="table1033212264218"></a>
<table><thead align="left"><tr id="row133331626923"><th class="cellrowborder" valign="top" width="16.619999999999997%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.56%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.889999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.320000000000004%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.610000000000003%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row14333926224"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p1790719584217"><a name="p1790719584217"></a><a name="p1790719584217"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p199084588217"><a name="p199084588217"></a><a name="p199084588217"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p11673723615"><a name="p11673723615"></a><a name="p11673723615"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCL/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p035182116187"><a name="p035182116187"></a><a name="p035182116187"></a>-</p>
</td>
</tr>
<tr id="row182331935113910"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p12341735113913"><a name="p12341735113913"></a><a name="p12341735113913"></a>alpha</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p14234143512393"><a name="p14234143512393"></a><a name="p14234143512393"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p1023463533915"><a name="p1023463533915"></a><a name="p1023463533915"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p3234203517397"><a name="p3234203517397"></a><a name="p3234203517397"></a>负半轴缩放系数</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p223463516394"><a name="p223463516394"></a><a name="p223463516394"></a>-</p>
</td>
</tr>
<tr id="row9388316349"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p193881514347"><a name="p193881514347"></a><a name="p193881514347"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p163881913346"><a name="p163881913346"></a><a name="p163881913346"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p1517530111819"><a name="p1517530111819"></a><a name="p1517530111819"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p18351172171817"><a name="p18351172171817"></a><a name="p18351172171817"></a>-</p>
</td>
</tr>
</tbody>
</table>

### HardSwish<a name="ZH-CN_TOPIC_0000002574469146" id="ZH-CN_TOPIC_0000002574469146"></a>

**功能描述<a name="section113841812134710"></a>**

对输入张量做HardSwish激活函数运算。公式为：Y = X \* HardSigmoid\(α=1/6, β=0.5, X\)

**参数说明<a name="section15195134816462"></a>**

**表 1**  HardSwish参数概览

<a name="table1033212264218"></a>
<table><thead align="left"><tr id="row133331626923"><th class="cellrowborder" valign="top" width="16.619999999999997%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.56%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.889999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.320000000000004%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.610000000000003%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row14333926224"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p1790719584217"><a name="p1790719584217"></a><a name="p1790719584217"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p199084588217"><a name="p199084588217"></a><a name="p199084588217"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p11673723615"><a name="p11673723615"></a><a name="p11673723615"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCL/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p035182116187"><a name="p035182116187"></a><a name="p035182116187"></a>-</p>
</td>
</tr>
<tr id="row9388316349"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p193881514347"><a name="p193881514347"></a><a name="p193881514347"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p163881913346"><a name="p163881913346"></a><a name="p163881913346"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p1517530111819"><a name="p1517530111819"></a><a name="p1517530111819"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p18351172171817"><a name="p18351172171817"></a><a name="p18351172171817"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Swish<a name="ZH-CN_TOPIC_0000002605108551" id="ZH-CN_TOPIC_0000002605108551"></a>

**功能描述<a name="section113841812134710"></a>**

对输入张量做Swish激活函数运算。公式为：Y = X \* sigmoid\(alpha \* X\)

**参数说明<a name="section15195134816462"></a>**

**表 1**  Swish参数概览

<a name="table1033212264218"></a>
<table><thead align="left"><tr id="row133331626923"><th class="cellrowborder" valign="top" width="16.619999999999997%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.56%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.889999999999999%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.320000000000004%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="24.610000000000003%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row14333926224"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p1790719584217"><a name="p1790719584217"></a><a name="p1790719584217"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p199084588217"><a name="p199084588217"></a><a name="p199084588217"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p11673723615"><a name="p11673723615"></a><a name="p11673723615"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCL/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p035182116187"><a name="p035182116187"></a><a name="p035182116187"></a>-</p>
</td>
</tr>
<tr id="row182331935113910"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p12341735113913"><a name="p12341735113913"></a><a name="p12341735113913"></a>alpha</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p14234143512393"><a name="p14234143512393"></a><a name="p14234143512393"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p1023463533915"><a name="p1023463533915"></a><a name="p1023463533915"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p3234203517397"><a name="p3234203517397"></a><a name="p3234203517397"></a>缩放系数。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p223463516394"><a name="p223463516394"></a><a name="p223463516394"></a>-</p>
</td>
</tr>
<tr id="row9388316349"><td class="cellrowborder" valign="top" width="16.619999999999997%" headers="mcps1.2.6.1.1 "><p id="p193881514347"><a name="p193881514347"></a><a name="p193881514347"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="14.56%" headers="mcps1.2.6.1.2 "><p id="p163881913346"><a name="p163881913346"></a><a name="p163881913346"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.889999999999999%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.320000000000004%" headers="mcps1.2.6.1.4 "><p id="p1517530111819"><a name="p1517530111819"></a><a name="p1517530111819"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="24.610000000000003%" headers="mcps1.2.6.1.5 "><p id="p18351172171817"><a name="p18351172171817"></a><a name="p18351172171817"></a>-</p>
</td>
</tr>
</tbody>
</table>

>![](public_sys-resources/icon-note.gif) **说明：** 
>在ONNX Opset24以上才支持构造Swish算子，对应ONNX版本为1.19.0以上。

### And<a name="ZH-CN_TOPIC_0000002574578826" id="ZH-CN_TOPIC_0000002574578826"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“与”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![img](public_sys-resources/icon-note.gif) **说明：**
>And支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。
>And算子不支持量化。

**表 1**  And参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>左输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>-</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>-</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Equal<a name="ZH-CN_TOPIC_0000002605257907" id="ZH-CN_TOPIC_0000002605257907"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“等于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Equal支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Equal参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>左输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

### GreaterOrEqual<a name="ZH-CN_TOPIC_0000002605377849" id="ZH-CN_TOPIC_0000002605377849"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“大于等于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>GreaterOrEqual支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  GreaterOrEqual参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>左输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Greater<a name="ZH-CN_TOPIC_0000002574738452" id="ZH-CN_TOPIC_0000002574738452"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“大于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Greater支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Greater参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>左输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

### LessOrEqual<a name="ZH-CN_TOPIC_0000002574578828" id="ZH-CN_TOPIC_0000002574578828"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“小于等于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>LessOrEqual支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  LessOrEqual参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>左输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Less<a name="ZH-CN_TOPIC_0000002605257909" id="ZH-CN_TOPIC_0000002605257909"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“小于”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>Less支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。

**表 1**  Less参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>左输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>数据类型仅支持float32、bool</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Not<a name="ZH-CN_TOPIC_0000002605377851" id="ZH-CN_TOPIC_0000002605377851"></a>

**功能描述<a name="section144144283412"></a>**

逐元素返回输入张量的取反值。

**参数说明<a name="section162919203502"></a>**

> ![img](public_sys-resources/icon-note.gif) **说明：**
> Not算子不支持量化。

**表 1**  Not参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p145351923958"><a name="p145351923958"></a><a name="p145351923958"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p85343231057"><a name="p85343231057"></a><a name="p85343231057"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p45333231656"><a name="p45333231656"></a><a name="p45333231656"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p253318238515"><a name="p253318238515"></a><a name="p253318238515"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145328231557"><a name="p145328231557"></a><a name="p145328231557"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p1053215237510"><a name="p1053215237510"></a><a name="p1053215237510"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p141985531820"><a name="p141985531820"></a><a name="p141985531820"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p1346416128194"><a name="p1346416128194"></a><a name="p1346416128194"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p453052318510"><a name="p453052318510"></a><a name="p453052318510"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p145302023959"><a name="p145302023959"></a><a name="p145302023959"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Or<a name="ZH-CN_TOPIC_0000002574738488" id="ZH-CN_TOPIC_0000002574738488"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“或”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![img](public_sys-resources/icon-note.gif) **说明：**
>Or支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。
>Or算子不支持量化。

**表 1**  Or参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>左输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>-</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>-</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Xor<a name="ZH-CN_TOPIC_0000002574578874" id="ZH-CN_TOPIC_0000002574578874"></a>

**功能描述<a name="section37550136507"></a>**

对两个输入张量执行逐元素“异或”逻辑运算。

**参数说明<a name="section162919203502"></a>**

>![img](public_sys-resources/icon-note.gif) **说明：**
>Xor支持广播特性。双向广播需要在转换命令中明确配置inputDataFormat和outputDataFormat参数。
>Xor算子不支持量化。

**表 1**  Xor参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>左输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>-</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>-</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(bool)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Dropout<a name="ZH-CN_TOPIC_0000002659215655" id="ZH-CN_TOPIC_0000002659215655"></a>

**功能描述<a name="section787325354211"></a>**

对输入张量进行 Dropout 处理。推理场景下，Dropout 等价于 Identity，输出张量与输入张量保持一致，不进行随机屏蔽和缩放处理。

**参数说明<a name="section138929514307"></a>**

**表 1**  Dropout参数概览

<a name="table4396103964610"></a>
<table><thead align="left"><tr id="row4396739164610"><th class="cellrowborder" valign="top" width="18.029999999999998%" id="mcps1.2.6.1.1"><p id="p08981354154614"><a name="p08981354154614"></a><a name="p08981354154614"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="13.750000000000002%" id="mcps1.2.6.1.2"><p id="p989865464616"><a name="p989865464616"></a><a name="p989865464616"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="16.29%" id="mcps1.2.6.1.3"><p id="p18898165434618"><a name="p18898165434618"></a><a name="p18898165434618"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.389999999999997%" id="mcps1.2.6.1.4"><p id="p88981154114615"><a name="p88981154114615"></a><a name="p88981154114615"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.54%" id="mcps1.2.6.1.5"><p id="p82407924717"><a name="p82407924717"></a><a name="p82407924717"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row248211012480"><td class="cellrowborder" valign="top" width="18.029999999999998%" headers="mcps1.2.6.1.1 "><p id="p2034495934720"><a name="p2034495934720"></a><a name="p2034495934720"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="13.750000000000002%" headers="mcps1.2.6.1.2 "><p id="p434465913471"><a name="p434465913471"></a><a name="p434465913471"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="16.29%" headers="mcps1.2.6.1.3 "><p id="p12344155964718"><a name="p12344155964718"></a><a name="p12344155964718"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.389999999999997%" headers="mcps1.2.6.1.4 "><p id="p163441959144719"><a name="p163441959144719"></a><a name="p163441959144719"></a>待进行 Dropout 处理的输入数据。</p>
</td>
<td class="cellrowborder" valign="top" width="23.54%" headers="mcps1.2.6.1.5 "><p id="p8344115974713"><a name="p8344115974713"></a><a name="p8344115974713"></a>维度为 0D / 1D / 2D / 3D / 4D；数据类型支持 float32、int8；不限定具体数据格式。</p>
</td>
</tr>
<tr id="row248210014485"><td class="cellrowborder" valign="top" width="18.029999999999998%" headers="mcps1.2.6.1.1 "><p id="p13344259114717"><a name="p13344259114717"></a><a name="p13344259114717"></a>ratio</p>
</td>
<td class="cellrowborder" valign="top" width="13.750000000000002%" headers="mcps1.2.6.1.2 "><p id="p103447595473"><a name="p103447595473"></a><a name="p103447595473"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="16.29%" headers="mcps1.2.6.1.3 "><p id="p53440593472"><a name="p53440593472"></a><a name="p53440593472"></a>scalar / tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.389999999999997%" headers="mcps1.2.6.1.4 "><p id="p8344859164715"><a name="p8344859164715"></a><a name="p8344859164715"></a>Dropout 屏蔽比例。</p>
</td>
<td class="cellrowborder" valign="top" width="23.54%" headers="mcps1.2.6.1.5 "><p id="p0344159154718"><a name="p0344159154718"></a><a name="p0344159154718"></a>可选输入；数据类型通常为 float32；取值范围为 [0, 1)。推理场景下该参数不影响输出结果。</p>
</td>
</tr>
<tr id="row174821002481"><td class="cellrowborder" valign="top" width="18.029999999999998%" headers="mcps1.2.6.1.1 "><p id="p1234405934712"><a name="p1234405934712"></a><a name="p1234405934712"></a>training_mode</p>
</td>
<td class="cellrowborder" valign="top" width="13.750000000000002%" headers="mcps1.2.6.1.2 "><p id="p0344959184719"><a name="p0344959184719"></a><a name="p0344959184719"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="16.29%" headers="mcps1.2.6.1.3 "><p id="p12344659184713"><a name="p12344659184713"></a><a name="p12344659184713"></a>scalar / tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.389999999999997%" headers="mcps1.2.6.1.4 "><p id="p1734445919476"><a name="p1734445919476"></a><a name="p1734445919476"></a>是否处于训练模式。</p>
</td>
<td class="cellrowborder" valign="top" width="23.54%" headers="mcps1.2.6.1.5 "><p id="p19344155911471"><a name="p19344155911471"></a><a name="p19344155911471"></a>可选输入；数据类型通常为 bool。为 false 或未配置时表示推理模式，Dropout 等价于 Identity。当前端侧推理场景通常按 false 处理。</p>
</td>
</tr>
<tr id="row34826010485"><td class="cellrowborder" valign="top" width="18.029999999999998%" headers="mcps1.2.6.1.1 "><p id="p434435994719"><a name="p434435994719"></a><a name="p434435994719"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="13.750000000000002%" headers="mcps1.2.6.1.2 "><p id="p134465924713"><a name="p134465924713"></a><a name="p134465924713"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="16.29%" headers="mcps1.2.6.1.3 "><p id="p8344259194717"><a name="p8344259194717"></a><a name="p8344259194717"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.389999999999997%" headers="mcps1.2.6.1.4 "><p id="p103444599475"><a name="p103444599475"></a><a name="p103444599475"></a>Dropout 输出结果。</p>
</td>
<td class="cellrowborder" valign="top" width="23.54%" headers="mcps1.2.6.1.5 "><p id="p334455912475"><a name="p334455912475"></a><a name="p334455912475"></a>维度与 X 一致；数据类型与 X 一致。推理场景下，输出数据与输入数据保持一致。</p>
</td>
</tr>
<tr id="row1848111054818"><td class="cellrowborder" valign="top" width="18.029999999999998%" headers="mcps1.2.6.1.1 "><p id="p5344165910474"><a name="p5344165910474"></a><a name="p5344165910474"></a>mask</p>
</td>
<td class="cellrowborder" valign="top" width="13.750000000000002%" headers="mcps1.2.6.1.2 "><p id="p9344205916478"><a name="p9344205916478"></a><a name="p9344205916478"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="16.29%" headers="mcps1.2.6.1.3 "><p id="p13344195954715"><a name="p13344195954715"></a><a name="p13344195954715"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.389999999999997%" headers="mcps1.2.6.1.4 "><p id="p23441459154716"><a name="p23441459154716"></a><a name="p23441459154716"></a>Dropout 随机屏蔽掩码。</p>
</td>
<td class="cellrowborder" valign="top" width="23.54%" headers="mcps1.2.6.1.5 "><p id="p134475917479"><a name="p134475917479"></a><a name="p134475917479"></a>可选输出；数据类型通常为 bool；维度与 X 一致。推理场景下通常不使用该输出，若框架保留该输出，其值不参与后续推理计算。</p>
</td>
</tr>
</tbody>
</table>

>![](public_sys-resources/icon-note.gif) **说明：** 
>暂不支持training\_mode为true，暂不支持ratio或training\_mode为运行时输入。

### Identity<a name="ZH-CN_TOPIC_0000002628696446" id="ZH-CN_TOPIC_0000002628696446"></a>

**功能描述<a name="section650819295436"></a>**

对输入张量进行恒等映射处理。该算子不改变输入数据的数值、数据类型和维度信息，输出张量与输入张量保持一致。

**参数说明<a name="section1144321103112"></a>**

**表 1**  Identity参数概览

<a name="table171244295114"></a>
<table><thead align="left"><tr id="row771214211512"><th class="cellrowborder" valign="top" width="16.96%" id="mcps1.2.6.1.1"><p id="p871212424518"><a name="p871212424518"></a><a name="p871212424518"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="15.989999999999998%" id="mcps1.2.6.1.2"><p id="p1971216423512"><a name="p1971216423512"></a><a name="p1971216423512"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="16.88%" id="mcps1.2.6.1.3"><p id="p1712144218513"><a name="p1712144218513"></a><a name="p1712144218513"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="26.82%" id="mcps1.2.6.1.4"><p id="p187123421519"><a name="p187123421519"></a><a name="p187123421519"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.35%" id="mcps1.2.6.1.5"><p id="p107121342115111"><a name="p107121342115111"></a><a name="p107121342115111"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row6712104218513"><td class="cellrowborder" valign="top" width="16.96%" headers="mcps1.2.6.1.1 "><p id="p844510358525"><a name="p844510358525"></a><a name="p844510358525"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="15.989999999999998%" headers="mcps1.2.6.1.2 "><p id="p107531028185219"><a name="p107531028185219"></a><a name="p107531028185219"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="16.88%" headers="mcps1.2.6.1.3 "><p id="p575392817522"><a name="p575392817522"></a><a name="p575392817522"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="26.82%" headers="mcps1.2.6.1.4 "><p id="p1644217352528"><a name="p1644217352528"></a><a name="p1644217352528"></a>输入张量。</p>
</td>
<td class="cellrowborder" valign="top" width="23.35%" headers="mcps1.2.6.1.5 "><p id="p3753162805216"><a name="p3753162805216"></a><a name="p3753162805216"></a>维度为 0D / 1D / 2D / 3D / 4D；数据类型支持 float32、int8；不限定具体数据格式。</p>
</td>
</tr>
<tr id="row1871334211516"><td class="cellrowborder" valign="top" width="16.96%" headers="mcps1.2.6.1.1 "><p id="p16753528135214"><a name="p16753528135214"></a><a name="p16753528135214"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="15.989999999999998%" headers="mcps1.2.6.1.2 "><p id="p175332855214"><a name="p175332855214"></a><a name="p175332855214"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="16.88%" headers="mcps1.2.6.1.3 "><p id="p375313283525"><a name="p375313283525"></a><a name="p375313283525"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="26.82%" headers="mcps1.2.6.1.4 "><p id="p875316286526"><a name="p875316286526"></a><a name="p875316286526"></a>输出张量。</p>
</td>
<td class="cellrowborder" valign="top" width="23.35%" headers="mcps1.2.6.1.5 "><p id="p33911144532"><a name="p33911144532"></a><a name="p33911144532"></a>维度与 X 一致；数据类型与 X 一致；输出数据与输入数据保持一致。</p>
</td>
</tr>
</tbody>
</table>

### GatherElements<a name="ZH-CN_TOPIC_0000002659095703" id="ZH-CN_TOPIC_0000002659095703"></a>

**功能描述<a name="section37550136507"></a>**

对目标张量的某个轴进行重新取索引，索引为一个与目标张量相同大小的整型张量。

**参数说明<a name="section1542812396314"></a>**

**表 1**  GatherElements参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor(float)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>-</p>
</td>
</tr>
<tr id="row498019321712"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p698043213119"><a name="p698043213119"></a><a name="p698043213119"></a>indices</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p3980123213110"><a name="p3980123213110"></a><a name="p3980123213110"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p207631119144216"><a name="p207631119144216"></a><a name="p207631119144216"></a>tensor(int32)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1785025910810"><a name="p1785025910810"></a><a name="p1785025910810"></a>右输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p7459131017911"><a name="p7459131017911"></a><a name="p7459131017911"></a>大小必须与data相同</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(float)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
<tr id="row03562011520"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18356911156"><a name="p18356911156"></a><a name="p18356911156"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p15356131054"><a name="p15356131054"></a><a name="p15356131054"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p153563119518"><a name="p153563119518"></a><a name="p153563119518"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p13561016515"><a name="p13561016515"></a><a name="p13561016515"></a>重新按照元素取索引的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p6356418510"><a name="p6356418510"></a><a name="p6356418510"></a>-rank(input) <= axis < rank(input)</p>
</td>
</tr>
</tbody>
</table>

### ReduceLogSum<a name="ZH-CN_TOPIC_0000002628856352" id="ZH-CN_TOPIC_0000002628856352"></a>

**功能描述<a name="section37550136507"></a>**

对目标张量进行Reduce操作，Reduce操作为LogSum。

**参数说明<a name="section1542812396314"></a>**

**表 1**  ReduceLogSum参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor(float)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>-</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>reduced</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(float)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
<tr id="row1782813472266"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p8405184919261"><a name="p8405184919261"></a><a name="p8405184919261"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p124057496260"><a name="p124057496260"></a><a name="p124057496260"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p4405449162617"><a name="p4405449162617"></a><a name="p4405449162617"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p134051498263"><a name="p134051498263"></a><a name="p134051498263"></a>输入张量，维度为1D，指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p13405124902617"><a name="p13405124902617"></a><a name="p13405124902617"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，不支持axis为空list</p>
</td>
</tr>
</tbody>
</table>

### ReduceLogSumExp<a name="ZH-CN_TOPIC_0000002659215657" id="ZH-CN_TOPIC_0000002659215657"></a>

**功能描述<a name="section37550136507"></a>**

对目标张量进行Reduce操作，Reduce操作为LogSumExp。

**参数说明<a name="section1542812396314"></a>**

**表 1**  GatherElements参数概览

<a name="table39806321816"></a>
<table><thead align="left"><tr id="row159801532115"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row119801332015"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p16980173210111"><a name="p16980173210111"></a><a name="p16980173210111"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p119801732213"><a name="p119801732213"></a><a name="p119801732213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor(float)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p109809321013"><a name="p109809321013"></a><a name="p109809321013"></a>输入张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p046011019919"><a name="p046011019919"></a><a name="p046011019919"></a>-</p>
</td>
</tr>
<tr id="row49814324114"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p18981132815"><a name="p18981132815"></a><a name="p18981132815"></a>reduced</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p9981123212111"><a name="p9981123212111"></a><a name="p9981123212111"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor(float)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p1598120321816"><a name="p1598120321816"></a><a name="p1598120321816"></a>输出张量，维度为2D/3D/4D，格式为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p1145891012919"><a name="p1145891012919"></a><a name="p1145891012919"></a>-</p>
</td>
</tr>
<tr id="row1782813472266"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p8405184919261"><a name="p8405184919261"></a><a name="p8405184919261"></a>axes</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p124057496260"><a name="p124057496260"></a><a name="p124057496260"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p4405449162617"><a name="p4405449162617"></a><a name="p4405449162617"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p134051498263"><a name="p134051498263"></a><a name="p134051498263"></a>输入张量，维度为1D，指定归约的轴。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p13405124902617"><a name="p13405124902617"></a><a name="p13405124902617"></a>规格约束：离线常量，元素范围[-rank(input), rank(input))，不支持axis为空list</p>
</td>
</tr>
</tbody>
</table>

### Expand<a name="ZH-CN_TOPIC_0000002628696448" id="ZH-CN_TOPIC_0000002628696448"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量按目标形状进行扩展运算，扩展规则遵循广播机制。

**参数说明<a name="section1542812396314"></a>**

**表 1**  Expand参数概览

<a name="table6180713299"></a>
<table><thead align="left"><tr id="row0181419295"><th class="cellrowborder" valign="top" width="17.44%" id="mcps1.2.6.1.1"><p id="p18505182473012"><a name="p18505182473012"></a><a name="p18505182473012"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="17.11%" id="mcps1.2.6.1.2"><p id="p52111022183012"><a name="p52111022183012"></a><a name="p52111022183012"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="11.18%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.22%" id="mcps1.2.6.1.4"><p id="p1420581753016"><a name="p1420581753016"></a><a name="p1420581753016"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.05%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row182510158295"><td class="cellrowborder" valign="top" width="17.44%" headers="mcps1.2.6.1.1 "><p id="p105651059142916"><a name="p105651059142916"></a><a name="p105651059142916"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="17.11%" headers="mcps1.2.6.1.2 "><p id="p203009218306"><a name="p203009218306"></a><a name="p203009218306"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.18%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.22%" headers="mcps1.2.6.1.4 "><p id="p69725815301"><a name="p69725815301"></a><a name="p69725815301"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.05%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>输入维度需满足广播规则。</p>
</td>
</tr>
<tr id="row1318111112294"><td class="cellrowborder" valign="top" width="17.44%" headers="mcps1.2.6.1.1 "><p id="p4201165752919"><a name="p4201165752919"></a><a name="p4201165752919"></a>shape</p>
</td>
<td class="cellrowborder" valign="top" width="17.11%" headers="mcps1.2.6.1.2 "><p id="p5405195412918"><a name="p5405195412918"></a><a name="p5405195412918"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.18%" headers="mcps1.2.6.1.3 "><p id="p0291651162913"><a name="p0291651162913"></a><a name="p0291651162913"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.22%" headers="mcps1.2.6.1.4 "><p id="p7405184892919"><a name="p7405184892919"></a><a name="p7405184892919"></a>目标输出形状，一维张量。</p>
</td>
<td class="cellrowborder" valign="top" width="23.05%" headers="mcps1.2.6.1.5 "><p id="p1117716459292"><a name="p1117716459292"></a><a name="p1117716459292"></a>shape中的维度值需大于0；目标形状需与输入张量形状满足广播规则。</p>
</td>
</tr>
<tr id="row1918181112916"><td class="cellrowborder" valign="top" width="17.44%" headers="mcps1.2.6.1.1 "><p id="p10611128112917"><a name="p10611128112917"></a><a name="p10611128112917"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="17.11%" headers="mcps1.2.6.1.2 "><p id="p5760113152912"><a name="p5760113152912"></a><a name="p5760113152912"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.18%" headers="mcps1.2.6.1.3 "><p id="p169703452917"><a name="p169703452917"></a><a name="p169703452917"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.22%" headers="mcps1.2.6.1.4 "><p id="p104661037192916"><a name="p104661037192916"></a><a name="p104661037192916"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.05%" headers="mcps1.2.6.1.5 "><p id="p44336427298"><a name="p44336427298"></a><a name="p44336427298"></a>输出形状由shape指定。</p>
</td>
</tr>
</tbody>
</table>

### Elu<a name="ZH-CN_TOPIC_0000002660394575" id="ZH-CN_TOPIC_0000002660394575"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量做Elu激活函数运算。公式为：Y= X if X \>= 0 else alpha \* \(exp\(X\)-1\)

**参数说明<a name="section1542812396314"></a>**

**表 1**  Elu参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row1828913718442"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p1628997204413"><a name="p1628997204413"></a><a name="p1628997204413"></a>alpha</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p182895718442"><a name="p182895718442"></a><a name="p182895718442"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p6289470448"><a name="p6289470448"></a><a name="p6289470448"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p128919774419"><a name="p128919774419"></a><a name="p128919774419"></a>负值区间饱和值缩放系数，默认值1.0。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p1328912713448"><a name="p1328912713448"></a><a name="p1328912713448"></a>-</p>
</td>
</tr>
</tbody>
</table>

### DepthToSpace<a name="ZH-CN_TOPIC_0000002629955352" id="ZH-CN_TOPIC_0000002629955352"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量维度的深度（通道）维度的数据重排到空间（高、宽）维度。

**参数说明<a name="section1542812396314"></a>**

**表 1**  DepthToSpace参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为4D，格式分别为NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为4D，格式分别为NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row16646162255418"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p464613227544"><a name="p464613227544"></a><a name="p464613227544"></a>blocksize</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p196461422105415"><a name="p196461422105415"></a><a name="p196461422105415"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p464652265416"><a name="p464652265416"></a><a name="p464652265416"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1564612213546"><a name="p1564612213546"></a><a name="p1564612213546"></a>从深度维度重组到空间维度的基础块尺寸。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p196467225548"><a name="p196467225548"></a><a name="p196467225548"></a>规格约束：blocksize>=2， C%blocksize^2 == 0</p>
</td>
</tr>
<tr id="row63381758105712"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p10339165818575"><a name="p10339165818575"></a><a name="p10339165818575"></a>mode</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p1632325175814"><a name="p1632325175814"></a><a name="p1632325175814"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p10339145817579"><a name="p10339145817579"></a><a name="p10339145817579"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p13339125865718"><a name="p13339125865718"></a><a name="p13339125865718"></a>重排模式。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p19339758165712"><a name="p19339758165712"></a><a name="p19339758165712"></a>配置范围：DCR、CRD</p>
</td>
</tr>
</tbody>
</table>

### SpaceToDepth<a name="ZH-CN_TOPIC_0000002660274511" id="ZH-CN_TOPIC_0000002660274511"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量空间（高、宽）维度的数据重排到深度（通道）维度。

**参数说明<a name="section1542812396314"></a>**

**表 1**  SpaceToDepth参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为4D，格式分别为NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为4D，格式分别为NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row16646162255418"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p464613227544"><a name="p464613227544"></a><a name="p464613227544"></a>blocksize</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p196461422105415"><a name="p196461422105415"></a><a name="p196461422105415"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p464652265416"><a name="p464652265416"></a><a name="p464652265416"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1564612213546"><a name="p1564612213546"></a><a name="p1564612213546"></a>从空间维度重组到深度维度的基础块尺寸。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p196467225548"><a name="p196467225548"></a><a name="p196467225548"></a>规格约束：blocksize>=2， H%blocksize == 0，W%blocksize == 0</p>
</td>
</tr>
</tbody>
</table>

### GRU<a name="ZH-CN_TOPIC_0000002631448488" id="ZH-CN_TOPIC_0000002631448488"></a>

**功能描述<a name="section113841812134710"></a>**

一种循环神经网络，用于捕捉输入的时序数据长期依赖关系。

**参数说明<a name="section15195134816462"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>仅支持float类型，暂不支持int8类型。

**表 1**  GRU参数概览

<a name="table74161021105020"></a>
<table><thead align="left"><tr id="row442112115020"><th class="cellrowborder" valign="top" width="15.90840915908409%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="16.73832616738326%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.96850314968503%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.027097290270977%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.357664233576642%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row16422621165017"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1248010314128"><a name="p1248010314128"></a><a name="p1248010314128"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p194805351219"><a name="p194805351219"></a><a name="p194805351219"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p17480935121"><a name="p17480935121"></a><a name="p17480935121"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p74809310127"><a name="p74809310127"></a><a name="p74809310127"></a>输入时序数据，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p64168815415"><a name="p64168815415"></a><a name="p64168815415"></a>规格约束：作为在线变量</p>
</td>
</tr>
<tr id="row15423221105011"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p173274161212"><a name="p173274161212"></a><a name="p173274161212"></a>W</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p165092761312"><a name="p165092761312"></a><a name="p165092761312"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p128033051319"><a name="p128033051319"></a><a name="p128033051319"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1932818111219"><a name="p1932818111219"></a><a name="p1932818111219"></a>门的权重张量，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p13647141201617"><a name="p13647141201617"></a><a name="p13647141201617"></a>规格约束：离线常量</p>
</td>
</tr>
<tr id="row1742542125016"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1512710595112"><a name="p1512710595112"></a><a name="p1512710595112"></a>R</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p452202712134"><a name="p452202712134"></a><a name="p452202712134"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p7282153014134"><a name="p7282153014134"></a><a name="p7282153014134"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p161271459131112"><a name="p161271459131112"></a><a name="p161271459131112"></a>循环权重张量，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p145531546141511"><a name="p145531546141511"></a><a name="p145531546141511"></a>规格约束：离线常量</p>
</td>
</tr>
<tr id="row3150335124713"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1717255617118"><a name="p1717255617118"></a><a name="p1717255617118"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p354172712133"><a name="p354172712133"></a><a name="p354172712133"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p228403041310"><a name="p228403041310"></a><a name="p228403041310"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1217255681116"><a name="p1217255681116"></a><a name="p1217255681116"></a>输入门偏置张量，维度为2D，格式为ND。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p1012716593152"><a name="p1012716593152"></a><a name="p1012716593152"></a>规格约束：离线常量</p>
<p id="p12861127125811"><a name="p12861127125811"></a><a name="p12861127125811"></a></p>
</td>
</tr>
<tr id="row8258131210520"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1174453181112"><a name="p1174453181112"></a><a name="p1174453181112"></a>sequence_lens</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p1856182719134"><a name="p1856182719134"></a><a name="p1856182719134"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p1728619308134"><a name="p1728619308134"></a><a name="p1728619308134"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p11741531119"><a name="p11741531119"></a><a name="p11741531119"></a>确定每个批数据中时序长度。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p14212322135813"><a name="p14212322135813"></a><a name="p14212322135813"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row54041919451"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1955815503116"><a name="p1955815503116"></a><a name="p1955815503116"></a>initial_h</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p155812276131"><a name="p155812276131"></a><a name="p155812276131"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p1528816306136"><a name="p1528816306136"></a><a name="p1528816306136"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p115591850141116"><a name="p115591850141116"></a><a name="p115591850141116"></a>隐藏层初始值，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p95910116584"><a name="p95910116584"></a><a name="p95910116584"></a>规格约束：作为在线变量</p>
</td>
</tr>
<tr id="row1747910320121"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p39589539121"><a name="p39589539121"></a><a name="p39589539121"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p2031972391316"><a name="p2031972391316"></a><a name="p2031972391316"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p1929412304133"><a name="p1929412304133"></a><a name="p1929412304133"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1995935341212"><a name="p1995935341212"></a><a name="p1995935341212"></a>隐藏层所有中间输出值张量拼接后的向量，维度为4D，格式为NCHW。</p>
</td>
<td class="cellrowborder" align="left" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p6883163513716"><a name="p6883163513716"></a><a name="p6883163513716"></a>规格约束：作为在线输出变量</p>
</td>
</tr>
<tr id="row133273120124"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p16121151191316"><a name="p16121151191316"></a><a name="p16121151191316"></a>Y_h</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p17322122381314"><a name="p17322122381314"></a><a name="p17322122381314"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p0296143011135"><a name="p0296143011135"></a><a name="p0296143011135"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p6121411161316"><a name="p6121411161316"></a><a name="p6121411161316"></a>隐藏层输出向量，维度为3D，格式为NCW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p1558163514172"><a name="p1558163514172"></a><a name="p1558163514172"></a>规格约束：作为在线输出变量</p>
</td>
</tr>
<tr id="row18172056141112"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p12286124112430"><a name="p12286124112430"></a><a name="p12286124112430"></a>activation_alpha</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p1299891713439"><a name="p1299891713439"></a><a name="p1299891713439"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p1551719012441"><a name="p1551719012441"></a><a name="p1551719012441"></a>list(float)</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p18141820435"><a name="p18141820435"></a><a name="p18141820435"></a>对LSTM激活函数结果做放缩（默认0.01）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p131501922132513"><a name="p131501922132513"></a><a name="p131501922132513"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row5174753191116"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p1833217289114"><a name="p1833217289114"></a><a name="p1833217289114"></a>activation_beta</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p1233202816110"><a name="p1233202816110"></a><a name="p1233202816110"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p733262818115"><a name="p733262818115"></a><a name="p733262818115"></a>list(float)</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1889316380591"><a name="p1889316380591"></a><a name="p1889316380591"></a>对LSTM激活函数结果做偏置（默认0.01）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p19660719132510"><a name="p19660719132510"></a><a name="p19660719132510"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row5558115019118"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p814484714519"><a name="p814484714519"></a><a name="p814484714519"></a>activations</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p16144114785114"><a name="p16144114785114"></a><a name="p16144114785114"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p17144134765111"><a name="p17144134765111"></a><a name="p17144134765111"></a>list(string)</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p11441547135118"><a name="p11441547135118"></a><a name="p11441547135118"></a>LSTM激活函数类型。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p13184196144711"><a name="p13184196144711"></a><a name="p13184196144711"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row3603184731217"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p11150123511475"><a name="p11150123511475"></a><a name="p11150123511475"></a>clip</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p8151173534717"><a name="p8151173534717"></a><a name="p8151173534717"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p19151163511479"><a name="p19151163511479"></a><a name="p19151163511479"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p4151635144712"><a name="p4151635144712"></a><a name="p4151635144712"></a>梯度裁剪阈值。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p58086713473"><a name="p58086713473"></a><a name="p58086713473"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row848595061211"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p122585121956"><a name="p122585121956"></a><a name="p122585121956"></a>direction</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p69881303515"><a name="p69881303515"></a><a name="p69881303515"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p09887301258"><a name="p09887301258"></a><a name="p09887301258"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1025881214516"><a name="p1025881214516"></a><a name="p1025881214516"></a>指定LSTM处理输入数据的方式（默认'forward'）。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p21042917473"><a name="p21042917473"></a><a name="p21042917473"></a>配置范围：forward/reverse/bidirectional</p>
</td>
</tr>
<tr id="row1295885371216"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p5405319458"><a name="p5405319458"></a><a name="p5405319458"></a>hidden_size</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p1640511191451"><a name="p1640511191451"></a><a name="p1640511191451"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p440551918512"><a name="p440551918512"></a><a name="p440551918512"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p540511193519"><a name="p540511193519"></a><a name="p540511193519"></a>隐藏层大小。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p5682102735713"><a name="p5682102735713"></a><a name="p5682102735713"></a>-</p>
</td>
</tr>
<tr id="row10786154512711"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p8787545192719"><a name="p8787545192719"></a><a name="p8787545192719"></a>layout</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p78041228288"><a name="p78041228288"></a><a name="p78041228288"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p67871645132716"><a name="p67871645132716"></a><a name="p67871645132716"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p1278714459273"><a name="p1278714459273"></a><a name="p1278714459273"></a>确定输入数据的排布格式，取值范围0或1。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p1978794518276"><a name="p1978794518276"></a><a name="p1978794518276"></a>暂不支持配置</p>
</td>
</tr>
<tr id="row33741849202715"><td class="cellrowborder" valign="top" width="15.90840915908409%" headers="mcps1.2.6.1.1 "><p id="p137410498278"><a name="p137410498278"></a><a name="p137410498278"></a>linear_before_reset</p>
</td>
<td class="cellrowborder" valign="top" width="16.73832616738326%" headers="mcps1.2.6.1.2 "><p id="p1946615882914"><a name="p1946615882914"></a><a name="p1946615882914"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.96850314968503%" headers="mcps1.2.6.1.3 "><p id="p12320812132911"><a name="p12320812132911"></a><a name="p12320812132911"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="29.027097290270977%" headers="mcps1.2.6.1.4 "><p id="p113752491276"><a name="p113752491276"></a><a name="p113752491276"></a>区分GRU候选隐藏层状态计算范式：值为1代表先对隐藏层做线性变换再与重置门相乘否则咸鱼重置门相乘再做线性变换。</p>
</td>
<td class="cellrowborder" valign="top" width="23.357664233576642%" headers="mcps1.2.6.1.5 "><p id="p2037554982712"><a name="p2037554982712"></a><a name="p2037554982712"></a>配置范围：0或1</p>
</td>
</tr>
</tbody>
</table>

### Gelu<a name="ZH-CN_TOPIC_0000002661401194" id="ZH-CN_TOPIC_0000002661401194"></a>

**功能描述<a name="section113841812134710"></a>**

对输入张量做Gelu激活函数运算。Gelu（Gaussian Error Linear Unit）基于正态分布累积概率，对输入乘以其概率分布的值实现连续非线性变换，相比传统激活函数在负值区域具有平滑的非零梯度。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Gelu参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row16646162255418"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p464613227544"><a name="p464613227544"></a><a name="p464613227544"></a>approximate</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p196461422105415"><a name="p196461422105415"></a><a name="p196461422105415"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p464652265416"><a name="p464652265416"></a><a name="p464652265416"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1564612213546"><a name="p1564612213546"></a><a name="p1564612213546"></a>Gelu近似计算模式，默认值"none"。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p196467225548"><a name="p196467225548"></a><a name="p196467225548"></a>配置范围：只能配置为"none"或"tanh"，"none"使用erf精确形式计算，"tanh"使用tanh近似算法计算</p>
</td>
</tr>
</tbody>
</table>

### Trilu<a name="ZH-CN_TOPIC_0000002661401195" id="ZH-CN_TOPIC_0000002661401195"></a>

**功能描述<a name="section113841812134710"></a>**

Trilu（Triangular Upper / Lower）算子用于提取输入张量的三角矩阵部分，将保留区域之外的元素全部置为零。根据配置可提取上三角矩阵或下三角矩阵；对高维张量作用在最后两个维度组成的每一个二维矩阵上，批次维度保持不变。

**参数说明<a name="section15195134816462"></a>**

**表 1**  Trilu参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row666041212188"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p167712418440"><a name="p167712418440"></a><a name="p167712418440"></a>k</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p077044174411"><a name="p077044174411"></a><a name="p077044174411"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p676912411444"><a name="p676912411444"></a><a name="p676912411444"></a>int64</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p576810417443"><a name="p576810417443"></a><a name="p576810417443"></a>对角线偏移量（Diagonal Offset），默认值0。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p175411827202412"><a name="p175411827202412"></a><a name="p175411827202412"></a>规格约束：离线常量</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度与数据类型与输入严格保持一致。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row16646162255418"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p464613227544"><a name="p464613227544"></a><a name="p464613227544"></a>upper</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p196461422105415"><a name="p196461422105415"></a><a name="p196461422105415"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p464652265416"><a name="p464652265416"></a><a name="p464652265416"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p1564612213546"><a name="p1564612213546"></a><a name="p1564612213546"></a>是否保留上三角区域，默认值1（true）。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p196467225548"><a name="p196467225548"></a><a name="p196467225548"></a>配置范围：1（true，提取上三角矩阵，下三角置0）、0（false，提取下三角矩阵，上三角置0）</p>
</td>
</tr>
</tbody>
</table>

### Shape<a name="ZH-CN_TOPIC_0000003030115802" id="ZH-CN_TOPIC_0000003030115802"></a>

**功能描述<a name="section3030115802a"></a>**

获取输入张量的形状信息。

**参数说明<a name="section3030115802b"></a>**

**表 1**  Shape参数概览

<a name="table3030115802a"></a>
<table><thead align="left"><tr id="row3030115802h"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p30301158021"><a name="p30301158021"></a><a name="p30301158021"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p30301158022"><a name="p30301158022"></a><a name="p30301158022"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p30301158023"><a name="p30301158023"></a><a name="p30301158023"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p30301158024"><a name="p30301158024"></a><a name="p30301158024"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p30301158025"><a name="p30301158025"></a><a name="p30301158025"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row3030115802r1"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3030115802r1a"><a name="p3030115802r1a"></a><a name="p3030115802r1a"></a>data</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3030115802r1b"><a name="p3030115802r1b"></a><a name="p3030115802r1b"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3030115802r1c"><a name="p3030115802r1c"></a><a name="p3030115802r1c"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3030115802r1d"><a name="p3030115802r1d"></a><a name="p3030115802r1d"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3030115802r1e"><a name="p3030115802r1e"></a><a name="p3030115802r1e"></a>-</p>
</td>
</tr>
<tr id="row3030115802r2"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3030115802r2a"><a name="p3030115802r2a"></a><a name="p3030115802r2a"></a>shape</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3030115802r2b"><a name="p3030115802r2b"></a><a name="p3030115802r2b"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3030115802r2c"><a name="p3030115802r2c"></a><a name="p3030115802r2c"></a>tensor (int64)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3030115802r2d"><a name="p3030115802r2d"></a><a name="p3030115802r2d"></a>输出张量，维度为1D，元素为输入张量的各维度大小。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3030115802r2e"><a name="p3030115802r2e"></a><a name="p3030115802r2e"></a>-</p>
</td>
</tr>
<tr id="row3030115802r3"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3030115802r3a"><a name="p3030115802r3a"></a><a name="p3030115802r3a"></a>start</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3030115802r3b"><a name="p3030115802r3b"></a><a name="p3030115802r3b"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3030115802r3c"><a name="p3030115802r3c"></a><a name="p3030115802r3c"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3030115802r3d"><a name="p3030115802r3d"></a><a name="p3030115802r3d"></a>指定输出形状切片的起始维度索引（默认0）。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3030115802r3e"><a name="p3030115802r3e"></a><a name="p3030115802r3e"></a>-</p>
</td>
</tr>
<tr id="row3030115802r4"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3030115802r4a"><a name="p3030115802r4a"></a><a name="p3030115802r4a"></a>end</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3030115802r4b"><a name="p3030115802r4b"></a><a name="p3030115802r4b"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3030115802r4c"><a name="p3030115802r4c"></a><a name="p3030115802r4c"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3030115802r4d"><a name="p3030115802r4d"></a><a name="p3030115802r4d"></a>指定输出形状切片的结束维度索引（不含，默认输出全部）。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3030115802r4e"><a name="p3030115802r4e"></a><a name="p3030115802r4e"></a>-</p>
</td>
</tr>
</tbody>
</table>

### MatMulInteger<a name="ZH-CN_TOPIC_0000003040115702" id="ZH-CN_TOPIC_0000003040115702"></a>

**功能描述<a name="section3040115702a"></a>**

对两个量化后的整数矩阵进行乘积运算，计算 `Y = (A - a_zero_point) * (B - b_zero_point)`。

**参数说明<a name="section3040115702b"></a>**

**表 1**  MatMulInteger参数概览

<a name="table3040115702a"></a>
<table><thead align="left"><tr id="row3040115702h"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p30401157021"><a name="p30401157021"></a><a name="p30401157021"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p30401157022"><a name="p30401157022"></a><a name="p30401157022"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p30401157023"><a name="p30401157023"></a><a name="p30401157023"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p30401157024"><a name="p30401157024"></a><a name="p30401157024"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p30401157025"><a name="p30401157025"></a><a name="p30401157025"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row3040115702r1"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3040115702r1a"><a name="p3040115702r1a"></a><a name="p3040115702r1a"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3040115702r1b"><a name="p3040115702r1b"></a><a name="p3040115702r1b"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3040115702r1c"><a name="p3040115702r1c"></a><a name="p3040115702r1c"></a>tensor (int8/uint8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3040115702r1d"><a name="p3040115702r1d"></a><a name="p3040115702r1d"></a>量化的左输入矩阵。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3040115702r1e"><a name="p3040115702r1e"></a><a name="p3040115702r1e"></a>-</p>
</td>
</tr>
<tr id="row3040115702r2"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3040115702r2a"><a name="p3040115702r2a"></a><a name="p3040115702r2a"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3040115702r2b"><a name="p3040115702r2b"></a><a name="p3040115702r2b"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3040115702r2c"><a name="p3040115702r2c"></a><a name="p3040115702r2c"></a>tensor (int8/uint8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3040115702r2d"><a name="p3040115702r2d"></a><a name="p3040115702r2d"></a>量化的右输入矩阵。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3040115702r2e"><a name="p3040115702r2e"></a><a name="p3040115702r2e"></a>-</p>
</td>
</tr>
<tr id="row3040115702r3"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3040115702r3a"><a name="p3040115702r3a"></a><a name="p3040115702r3a"></a>a_zero_point</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3040115702r3b"><a name="p3040115702r3b"></a><a name="p3040115702r3b"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3040115702r3c"><a name="p3040115702r3c"></a><a name="p3040115702r3c"></a>tensor (int8/uint8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3040115702r3d"><a name="p3040115702r3d"></a><a name="p3040115702r3d"></a>输入A量化零点，可选输入，默认值为0。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3040115702r3e"><a name="p3040115702r3e"></a><a name="p3040115702r3e"></a>-</p>
</td>
</tr>
<tr id="row3040115702r4"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3040115702r4a"><a name="p3040115702r4a"></a><a name="p3040115702r4a"></a>b_zero_point</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3040115702r4b"><a name="p3040115702r4b"></a><a name="p3040115702r4b"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3040115702r4c"><a name="p3040115702r4c"></a><a name="p3040115702r4c"></a>tensor (int8/uint8)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3040115702r4d"><a name="p3040115702r4d"></a><a name="p3040115702r4d"></a>输入B量化零点，可选输入，默认值为0。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3040115702r4e"><a name="p3040115702r4e"></a><a name="p3040115702r4e"></a>-</p>
</td>
</tr>
<tr id="row3040115702r5"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3040115702r5a"><a name="p3040115702r5a"></a><a name="p3040115702r5a"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3040115702r5b"><a name="p3040115702r5b"></a><a name="p3040115702r5b"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3040115702r5c"><a name="p3040115702r5c"></a><a name="p3040115702r5c"></a>tensor (int32)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3040115702r5d"><a name="p3040115702r5d"></a><a name="p3040115702r5d"></a>去量化乘积结果输出矩阵。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3040115702r5e"><a name="p3040115702r5e"></a><a name="p3040115702r5e"></a>-</p>
</td>
</tr>
</tbody>
</table>

### TopK<a name="ZH-CN_TOPIC_0000003050115802" id="ZH-CN_TOPIC_0000003050115802"></a>

**功能描述<a name="section3050115802a"></a>**

获取输入张量中沿指定维度前K个最大值，并返回其值及对应的索引。

**参数说明<a name="section3050115802b"></a>**

**表 1**  TopK参数概览

<a name="table3050115802a"></a>
<table><thead align="left"><tr id="row3050115802h"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p30501158021"><a name="p30501158021"></a><a name="p30501158021"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p30501158022"><a name="p30501158022"></a><a name="p30501158022"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.489999999999998%" id="mcps1.2.6.1.3"><p id="p30501158023"><a name="p30501158023"></a><a name="p30501158023"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p30501158024"><a name="p30501158024"></a><a name="p30501158024"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p30501158025"><a name="p30501158025"></a><a name="p30501158025"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row3050115802r1"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115802r1a"><a name="p3050115802r1a"></a><a name="p3050115802r1a"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115802r1b"><a name="p3050115802r1b"></a><a name="p3050115802r1b"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115802r1c"><a name="p3050115802r1c"></a><a name="p3050115802r1c"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115802r1d"><a name="p3050115802r1d"></a><a name="p3050115802r1d"></a>输入张量，维度不限制。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115802r1e"><a name="p3050115802r1e"></a><a name="p3050115802r1e"></a>-</p>
</td>
</tr>
<tr id="row3050115802r2"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115802r2a"><a name="p3050115802r2a"></a><a name="p3050115802r2a"></a>K</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115802r2b"><a name="p3050115802r2b"></a><a name="p3050115802r2b"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115802r2c"><a name="p3050115802r2c"></a><a name="p3050115802r2c"></a>tensor (int64)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115802r2d"><a name="p3050115802r2d"></a><a name="p3050115802r2d"></a>需要获取的TopK个数，标量。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115802r2e"><a name="p3050115802r2e"></a><a name="p3050115802r2e"></a>-</p>
</td>
</tr>
<tr id="row3050115802r3"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115802r3a"><a name="p3050115802r3a"></a><a name="p3050115802r3a"></a>Values</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115802r3b"><a name="p3050115802r3b"></a><a name="p3050115802r3b"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115802r3c"><a name="p3050115802r3c"></a><a name="p3050115802r3c"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115802r3d"><a name="p3050115802r3d"></a><a name="p3050115802r3d"></a>TopK值张量，axis维度为K。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115802r3e"><a name="p3050115802r3e"></a><a name="p3050115802r3e"></a>-</p>
</td>
</tr>
<tr id="row3050115802r4"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115802r4a"><a name="p3050115802r4a"></a><a name="p3050115802r4a"></a>Indices</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115802r4b"><a name="p3050115802r4b"></a><a name="p3050115802r4b"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115802r4c"><a name="p3050115802r4c"></a><a name="p3050115802r4c"></a>tensor (int64)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115802r4d"><a name="p3050115802r4d"></a><a name="p3050115802r4d"></a>TopK值的索引张量，axis维度为K。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115802r4e"><a name="p3050115802r4e"></a><a name="p3050115802r4e"></a>-</p>
</td>
</tr>
<tr id="row3050115802r5"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115802r5a"><a name="p3050115802r5a"></a><a name="p3050115802r5a"></a>axis</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115802r5b"><a name="p3050115802r5b"></a><a name="p3050115802r5b"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115802r5c"><a name="p3050115802r5c"></a><a name="p3050115802r5c"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115802r5d"><a name="p3050115802r5d"></a><a name="p3050115802r5d"></a>指定选取TopK的维度（默认-1，即最后一维）。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115802r5e"><a name="p3050115802r5e"></a><a name="p3050115802r5e"></a>-</p>
</td>
</tr>
<tr id="row3050115802r6"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115802r6a"><a name="p3050115802r6a"></a><a name="p3050115802r6a"></a>largest</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115802r6b"><a name="p3050115802r6b"></a><a name="p3050115802r6b"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115802r6c"><a name="p3050115802r6c"></a><a name="p3050115802r6c"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115802r6d"><a name="p3050115802r6d"></a><a name="p3050115802r6d"></a>控制返回最大值（1）还是最小值（0）。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115802r6e"><a name="p3050115802r6e"></a><a name="p3050115802r6e"></a>默认1</p>
</td>
</tr>
<tr id="row3050115802r7"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p3050115802r7a"><a name="p3050115802r7a"></a><a name="p3050115802r7a"></a>sorted</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p3050115802r7b"><a name="p3050115802r7b"></a><a name="p3050115802r7b"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.489999999999998%" headers="mcps1.2.6.1.3 "><p id="p3050115802r7c"><a name="p3050115802r7c"></a><a name="p3050115802r7c"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p3050115802r7d"><a name="p3050115802r7d"></a><a name="p3050115802r7d"></a>控制返回结果是否按序排列（1）或不排序（0）。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p3050115802r7e"><a name="p3050115802r7e"></a><a name="p3050115802r7e"></a>默认1</p>
</td>
</tr>
</tbody>
</table>

### Erf<a name="ZH-CN_TOPIC_0000002026072801" id="ZH-CN_TOPIC_0000002026072801"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量逐元素计算高斯误差函数值。

**参数说明<a name="section1542812396314"></a>**

**表 1**  Erf参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
</tbody>
</table>

### HardSigmoid<a name="ZH-CN_TOPIC_0000002026072802" id="ZH-CN_TOPIC_0000002026072802"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量做HardSigmoid激活函数运算。公式为：Y=max\(0, min\(1, α·X+β))

**参数说明<a name="section1542812396314"></a>**

**表 1**  HardSigmoid参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row1828913718442"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p1628997204413"><a name="p1628997204413"></a><a name="p1628997204413"></a>alpha</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p182895718442"><a name="p182895718442"></a><a name="p182895718442"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p6289470448"><a name="p6289470448"></a><a name="p6289470448"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p128919774419"><a name="p128919774419"></a><a name="p128919774419"></a>激活曲线斜率调控系数，默认值0.2。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p1328912713448"><a name="p1328912713448"></a><a name="p1328912713448"></a>-</p>
</td>
</tr>
<tr id="row1828913718442"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p1628997204413"><a name="p1628997204413"></a><a name="p1628997204413"></a>beta</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p182895718442"><a name="p182895718442"></a><a name="p182895718442"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p6289470448"><a name="p6289470448"></a><a name="p6289470448"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p128919774419"><a name="p128919774419"></a><a name="p128919774419"></a>激活曲线偏移调控系数，默认值0.5。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p1328912713448"><a name="p1328912713448"></a><a name="p1328912713448"></a>-</p>
</td>
</tr>
</tbody>
</table>



### Celu<a name="ZH-CN_TOPIC_0000002026072803" id="ZH-CN_TOPIC_0000002026072803"></a>

**功能描述<a name="section37550136507"></a>**

对输入张量做Celu激活函数运算。公式为：Y=max\(0, x)+min\(0, α·(exp(x/α)-1))

**参数说明<a name="section1542812396314"></a>**

**表 1**  Celu参数概览

<a name="table4179355155016"></a>
<table><thead align="left"><tr id="row417995510501"><th class="cellrowborder" valign="top" width="17.51%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.5%" id="mcps1.2.6.1.2"><p id="p4185174319549"><a name="p4185174319549"></a><a name="p4185174319549"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.33%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.71%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="25.95%" id="mcps1.2.6.1.5"><p id="p1769075913564"><a name="p1769075913564"></a><a name="p1769075913564"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row760104045214"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p109681815191812"><a name="p109681815191812"></a><a name="p109681815191812"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p15968615161817"><a name="p15968615161817"></a><a name="p15968615161817"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p6968615171817"><a name="p6968615171817"></a><a name="p6968615171817"></a>-</p>
</td>
</tr>
<tr id="row14341183720526"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p23411437115215"><a name="p23411437115215"></a><a name="p23411437115215"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p13341143735216"><a name="p13341143735216"></a><a name="p13341143735216"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p19341103720521"><a name="p19341103720521"></a><a name="p19341103720521"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p191865655319"><a name="p191865655319"></a><a name="p191865655319"></a>输出张量，维度为2D/3D/4D，格式分别为ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="25.95%" headers="mcps1.2.6.1.5 "><p id="p193418377529"><a name="p193418377529"></a><a name="p193418377529"></a>-</p>
</td>
</tr>
<tr id="row1828913718442"><td class="cellrowborder" valign="top" width="17.51%" headers="mcps1.2.6.1.1 "><p id="p1628997204413"><a name="p1628997204413"></a><a name="p1628997204413"></a>alpha</p>
</td>
<td class="cellrowborder" valign="top" width="11.5%" headers="mcps1.2.6.1.2 "><p id="p182895718442"><a name="p182895718442"></a><a name="p182895718442"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="13.33%" headers="mcps1.2.6.1.3 "><p id="p6289470448"><a name="p6289470448"></a><a name="p6289470448"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p128919774419"><a name="p128919774419"></a><a name="p128919774419"></a>Celu负值区间系数，默认值1.0。</p>
</td>
<td class="cellrowborder" valign="top" width="31.71%" headers="mcps1.2.6.1.4 "><p id="p128919774419"><a name="p128919774419"></a><a name="p128919774419"></a>规格约束：alpha>0。</p>
</td>
</tr>
</tbody>
</table>



# 专题<a name="ZH-CN_TOPIC_0000002562713759" id="ZH-CN_TOPIC_0000002562713759"></a>

-   **[高效算子支持](#ZH-CN_TOPIC_0000002531793838)**  

### Neg<a name="ZH-CN_TOPIC_0000002900000002" id="ZH-CN_TOPIC_0000002900000002"></a>

**功能描述<a name="section_neg_onnx_desc"></a>**

对张量的每个元素做取负运算（符号取反），即 y = -x。

**参数说明<a name="section_neg_onnx_param"></a>**

**表 1**  Neg参数概览

<a name="table_neg_onnx"></a>
<table><thead align="left"><tr id="row_neg_onnx_hdr"><th class="cellrowborder" valign="top" width="17.68%" id="mcps1.2.6.1.1"><p id="p_neg_onnx_hdr1"><a name="p_neg_onnx_hdr1"></a><a name="p_neg_onnx_hdr1"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.33%" id="mcps1.2.6.1.2"><p id="p_neg_onnx_hdr2"><a name="p_neg_onnx_hdr2"></a><a name="p_neg_onnx_hdr2"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="13.49%" id="mcps1.2.6.1.3"><p id="p_neg_onnx_hdr3"><a name="p_neg_onnx_hdr3"></a><a name="p_neg_onnx_hdr3"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="31.39%" id="mcps1.2.6.1.4"><p id="p_neg_onnx_hdr4"><a name="p_neg_onnx_hdr4"></a><a name="p_neg_onnx_hdr4"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="26.11%" id="mcps1.2.6.1.5"><p id="p_neg_onnx_hdr5"><a name="p_neg_onnx_hdr5"></a><a name="p_neg_onnx_hdr5"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row_neg_onnx_in"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p_neg_onnx_in_p"><a name="p_neg_onnx_in_p"></a><a name="p_neg_onnx_in_p"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p_neg_onnx_in_io"><a name="p_neg_onnx_in_io"></a><a name="p_neg_onnx_in_io"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="13.49%" headers="mcps1.2.6.1.3 "><p id="p_neg_onnx_in_dt"><a name="p_neg_onnx_in_dt"></a><a name="p_neg_onnx_in_dt"></a>tensor(fp32)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p_neg_onnx_in_desc"><a name="p_neg_onnx_in_desc"></a><a name="p_neg_onnx_in_desc"></a>输入张量，维度为2D/3D/4D，格式为ND/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p_neg_onnx_in_limit"><a name="p_neg_onnx_in_limit"></a><a name="p_neg_onnx_in_limit"></a>规格约束：fp16/int32 不支持该类型（Micro coder 未注册）；不支持 rank>4</p>
</td>
</tr>
<tr id="row_neg_onnx_out"><td class="cellrowborder" valign="top" width="17.68%" headers="mcps1.2.6.1.1 "><p id="p_neg_onnx_out_p"><a name="p_neg_onnx_out_p"></a><a name="p_neg_onnx_out_p"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="11.33%" headers="mcps1.2.6.1.2 "><p id="p_neg_onnx_out_io"><a name="p_neg_onnx_out_io"></a><a name="p_neg_onnx_out_io"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="13.49%" headers="mcps1.2.6.1.3 "><p id="p_neg_onnx_out_dt"><a name="p_neg_onnx_out_dt"></a><a name="p_neg_onnx_out_dt"></a>tensor(fp32)</p>
</td>
<td class="cellrowborder" valign="top" width="31.39%" headers="mcps1.2.6.1.4 "><p id="p_neg_onnx_out_desc"><a name="p_neg_onnx_out_desc"></a><a name="p_neg_onnx_out_desc"></a>输出张量，维度与输入 X 相同，每个元素为 X 对应元素的相反数。</p>
</td>
<td class="cellrowborder" valign="top" width="26.11%" headers="mcps1.2.6.1.5 "><p id="p_neg_onnx_out_limit"><a name="p_neg_onnx_out_limit"></a><a name="p_neg_onnx_out_limit"></a>-</p>
</td>
</tr>
</tbody>
</table>

### Pow<a name="ZH-CN_TOPIC_0000002476598371" id="ZH-CN_TOPIC_0000002476598371"></a>

**功能描述<a name="section_onnx_pow_func"></a>**

计算两个张量的逐元素幂运算，X 为底数张量，Y 为指数张量，输出 Z = X^Y。支持 NumPy 风格广播。

**参数说明<a name="section_onnx_pow_param"></a>**

>![](public_sys-resources/icon-note.gif) **说明：** 
>1. Pow 无原生属性，转换时 MSLite 内部 scale=1.0, shift=0.0 等价于标准幂运算。支持广播特性，双向广播需在转换命令中明确配置 inputDataFormat 和 outputDataFormat 参数。
>2. 推荐使用 X ≥ 0 的输入组合确保结果确定性；X < 0 且 Y 为非整数时实数域无定义，输出值取决于底层数学库。
>3. INT8 量化仅支持 X ≥ 0 的输入，X < 0 时负数值在 int8 对称量化中将被映射为 0。

**表 1**  Pow参数概览

<a name="table_pow_onnx"></a>
<table><thead align="left"><tr id="row_pow_onnx_hdr"><th class="cellrowborder" valign="top" width="17.07%" id="mcps1.2.6.1.1"><p id="p_pow_onnx_hdr1"><a name="p_pow_onnx_hdr1"></a><a name="p_pow_onnx_hdr1"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.49%" id="mcps1.2.6.1.2"><p id="p_pow_onnx_hdr2"><a name="p_pow_onnx_hdr2"></a><a name="p_pow_onnx_hdr2"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.95%" id="mcps1.2.6.1.3"><p id="p_pow_onnx_hdr3"><a name="p_pow_onnx_hdr3"></a><a name="p_pow_onnx_hdr3"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="29.73%" id="mcps1.2.6.1.4"><p id="p_pow_onnx_hdr4"><a name="p_pow_onnx_hdr4"></a><a name="p_pow_onnx_hdr4"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="23.76%" id="mcps1.2.6.1.5"><p id="p_pow_onnx_hdr5"><a name="p_pow_onnx_hdr5"></a><a name="p_pow_onnx_hdr5"></a>配置范围及规格约束说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row_pow_onnx_x"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p_pow_onnx_x_name"><a name="p_pow_onnx_x_name"></a><a name="p_pow_onnx_x_name"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p_pow_onnx_x_io"><a name="p_pow_onnx_x_io"></a><a name="p_pow_onnx_x_io"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p_pow_onnx_x_dt"><a name="p_pow_onnx_x_dt"></a><a name="p_pow_onnx_x_dt"></a>tensor(fp32/int8)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p_pow_onnx_x_desc"><a name="p_pow_onnx_x_desc"></a><a name="p_pow_onnx_x_desc"></a>底数张量，维度为 1D/2D/3D/4D，格式为 ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p_pow_onnx_x_limit"><a name="p_pow_onnx_x_limit"></a><a name="p_pow_onnx_x_limit"></a>规格约束：最大维度 4D；支持 NumPy 广播；fp16/fp64/int32/int64 不支持该类型；INT8 不支持 X&lt;0 的输入</p>
</td>
</tr>
<tr id="row_pow_onnx_y"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p_pow_onnx_y_name"><a name="p_pow_onnx_y_name"></a><a name="p_pow_onnx_y_name"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p_pow_onnx_y_io"><a name="p_pow_onnx_y_io"></a><a name="p_pow_onnx_y_io"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p_pow_onnx_y_dt"><a name="p_pow_onnx_y_dt"></a><a name="p_pow_onnx_y_dt"></a>tensor(fp32/int8)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p_pow_onnx_y_desc"><a name="p_pow_onnx_y_desc"></a><a name="p_pow_onnx_y_desc"></a>指数张量，维度为 1D/2D/3D/4D，与 X 广播兼容。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p_pow_onnx_y_limit"><a name="p_pow_onnx_y_limit"></a><a name="p_pow_onnx_y_limit"></a>规格约束：最大维度 4D；fp16/fp64/int32/int64 不支持该类型</p>
</td>
</tr>
<tr id="row_pow_onnx_z"><td class="cellrowborder" valign="top" width="17.07%" headers="mcps1.2.6.1.1 "><p id="p_pow_onnx_z_name"><a name="p_pow_onnx_z_name"></a><a name="p_pow_onnx_z_name"></a>Z</p>
</td>
<td class="cellrowborder" valign="top" width="14.49%" headers="mcps1.2.6.1.2 "><p id="p_pow_onnx_z_io"><a name="p_pow_onnx_z_io"></a><a name="p_pow_onnx_z_io"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.95%" headers="mcps1.2.6.1.3 "><p id="p_pow_onnx_z_dt"><a name="p_pow_onnx_z_dt"></a><a name="p_pow_onnx_z_dt"></a>tensor(fp32/int8)</p>
</td>
<td class="cellrowborder" valign="top" width="29.73%" headers="mcps1.2.6.1.4 "><p id="p_pow_onnx_z_desc"><a name="p_pow_onnx_z_desc"></a><a name="p_pow_onnx_z_desc"></a>输出张量，维度为 X 与 Y 的广播结果，格式为 ND/NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="23.76%" headers="mcps1.2.6.1.5 "><p id="p_pow_onnx_z_limit"><a name="p_pow_onnx_z_limit"></a><a name="p_pow_onnx_z_limit"></a>规格约束：最大维度 4D；fp16/fp64/int32/int64 不支持该类型</p>
</td>
</tr>
</tbody>
</table>

## 高效算子支持<a name="ZH-CN_TOPIC_0000002531793838" id="ZH-CN_TOPIC_0000002531793838"></a>

HiSpark.AI工具链对部分常用嵌入式AI的算子规格进行了RISC-V专题的性能优化。在converter\_lite命令行中开启riscvOpt选项，即可启用高性能模式。对性能要求较高的嵌入式AI场景中，在AI模型设计时可以优先采用以下规格。

-   **[Conv优化](#ZH-CN_TOPIC_0000002531633886)**  

-   **[Matmul优化](#ZH-CN_TOPIC_0000002628690692)**  

-   **[MaxPooling/AveragePooling优化](#ZH-CN_TOPIC_0000002661401189)**  

### Conv优化<a name="ZH-CN_TOPIC_0000002531633886" id="ZH-CN_TOPIC_0000002531633886"></a>

以下规格的Onnx算子在riscvOpt高性能模式下推理时间上有较大优化，算法工程师在AI模型设计时可以优先采用以下规格。

**表 1**  Conv Onnx高效算子支持规格列表

<a name="table189651429122117"></a>
<table><thead align="left"><tr id="row1496911294216"><th class="cellrowborder" valign="top" width="14.032806561312263%" id="mcps1.2.6.1.1"><p id="p3340101235915"><a name="p3340101235915"></a><a name="p3340101235915"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.822364472894579%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="10.072014402880576%" id="mcps1.2.6.1.3"><p id="p1534011285913"><a name="p1534011285913"></a><a name="p1534011285913"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="25.725145029005798%" id="mcps1.2.6.1.4"><p id="p7340612155913"><a name="p7340612155913"></a><a name="p7340612155913"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="38.34766953390678%" id="mcps1.2.6.1.5"><p id="p1072813016591"><a name="p1072813016591"></a><a name="p1072813016591"></a>高效算子规格支持范围说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row4970192982114"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p1477616583269"><a name="p1477616583269"></a><a name="p1477616583269"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p2776155811264"><a name="p2776155811264"></a><a name="p2776155811264"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p5776175813266"><a name="p5776175813266"></a><a name="p5776175813266"></a>输入张量，维度为3D或4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p573518356592"><a name="p573518356592"></a><a name="p573518356592"></a>C在 [1, 8, 16, 32]列表中</p>
<p id="p27351535105914"><a name="p27351535105914"></a><a name="p27351535105914"></a>H，W均满足 6<=H, W <= 32</p>
</td>
</tr>
<tr id="row6971132912215"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p19727413172119"><a name="p19727413172119"></a><a name="p19727413172119"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p107261213152117"><a name="p107261213152117"></a><a name="p107261213152117"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p67261313102115"><a name="p67261313102115"></a><a name="p67261313102115"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p57261613112110"><a name="p57261613112110"></a><a name="p57261613112110"></a>输出张量，维度为3D或4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p10324174213592"><a name="p10324174213592"></a><a name="p10324174213592"></a>C在 [1, 8, 16, 32]列表中</p>
<p id="p193241942175913"><a name="p193241942175913"></a><a name="p193241942175913"></a>H，W均满足 6<=H, W <= 32</p>
</td>
</tr>
<tr id="row13973529102110"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p177785819261"><a name="p177785819261"></a><a name="p177785819261"></a>kernel_shape</p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p977718586269"><a name="p977718586269"></a><a name="p977718586269"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p17777145822614"><a name="p17777145822614"></a><a name="p17777145822614"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p1011953613513"><a name="p1011953613513"></a><a name="p1011953613513"></a>kernel沿各轴的大小。</p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p1836342918014"><a name="p1836342918014"></a><a name="p1836342918014"></a>1D支持kernel_shape = 3, 5，2D支持kernel_shape = 3,3</p>
</td>
</tr>
<tr id="row19973129102114"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p1414571372710"><a name="p1414571372710"></a><a name="p1414571372710"></a>pads</p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p614519131277"><a name="p614519131277"></a><a name="p614519131277"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p16338550143115"><a name="p16338550143115"></a><a name="p16338550143115"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p85157422328"><a name="p85157422328"></a><a name="p85157422328"></a>各轴前后填充零的个数。</p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p11118122518259"><a name="p11118122518259"></a><a name="p11118122518259"></a>支持pads满足输入输出tensor H/W相等的情况</p>
</td>
</tr>
<tr id="row48490213206"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p1851524472710"><a name="p1851524472710"></a><a name="p1851524472710"></a>strides</p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p1451574413278"><a name="p1451574413278"></a><a name="p1451574413278"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p2077235113117"><a name="p2077235113117"></a><a name="p2077235113117"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p18216141324"><a name="p18216141324"></a><a name="p18216141324"></a>各个方向上kernel的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p121181125172518"><a name="p121181125172518"></a><a name="p121181125172518"></a>stride = 1</p>
</td>
</tr>
</tbody>
</table>

以下规格的TFLite算子在riscvOpt高性能模式下推理时间上有较大优化，算法工程师在AI模型设计时可以优先采用以下规格。

**表 2**  Conv TFLite高效算子支持规格列表

<a name="table668985955612"></a>
<table><thead align="left"><tr id="row13690359165613"><th class="cellrowborder" valign="top" width="13.120000000000001%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="12.44%" id="mcps1.2.6.1.2"><p id="p2136105314214"><a name="p2136105314214"></a><a name="p2136105314214"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="10.61%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="25.480000000000004%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="38.35%" id="mcps1.2.6.1.5"><p id="p11445381638"><a name="p11445381638"></a><a name="p11445381638"></a>高效算子规格支持范围说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row0259114117411"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="12.44%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.61%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="25.480000000000004%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="38.35%" headers="mcps1.2.6.1.5 "><p id="p14237385316"><a name="p14237385316"></a><a name="p14237385316"></a>C在 [1, 8, 16, 32]列表中</p>
<p id="p42375811311"><a name="p42375811311"></a><a name="p42375811311"></a>H，W均满足 6<=H, W <= 32</p>
</td>
</tr>
<tr id="row44831201652"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p194831017511"><a name="p194831017511"></a><a name="p194831017511"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="12.44%" headers="mcps1.2.6.1.2 "><p id="p048340450"><a name="p048340450"></a><a name="p048340450"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="10.61%" headers="mcps1.2.6.1.3 "><p id="p124839018518"><a name="p124839018518"></a><a name="p124839018518"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="25.480000000000004%" headers="mcps1.2.6.1.4 "><p id="p13483801352"><a name="p13483801352"></a><a name="p13483801352"></a>输出张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="38.35%" headers="mcps1.2.6.1.5 "><p id="p2659101217314"><a name="p2659101217314"></a><a name="p2659101217314"></a>C在 [1, 8, 16, 32]列表中</p>
<p id="p1465941219318"><a name="p1465941219318"></a><a name="p1465941219318"></a>H，W均满足 6<=H, W <= 32</p>
</td>
</tr>
<tr id="row869245925620"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p96921059125614"><a name="p96921059125614"></a><a name="p96921059125614"></a>padding</p>
</td>
<td class="cellrowborder" valign="top" width="12.44%" headers="mcps1.2.6.1.2 "><p id="p1150158930"><a name="p1150158930"></a><a name="p1150158930"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.61%" headers="mcps1.2.6.1.3 "><p id="p76921259115619"><a name="p76921259115619"></a><a name="p76921259115619"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="25.480000000000004%" headers="mcps1.2.6.1.4 "><p id="p10118203645110"><a name="p10118203645110"></a><a name="p10118203645110"></a>填充类型。</p>
</td>
<td class="cellrowborder" valign="top" width="38.35%" headers="mcps1.2.6.1.5 "><p id="p1769285995619"><a name="p1769285995619"></a><a name="p1769285995619"></a>配置范围：支持SAME</p>
</td>
</tr>
<tr id="row369235919566"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p106921159195616"><a name="p106921159195616"></a><a name="p106921159195616"></a>stride_h</p>
</td>
<td class="cellrowborder" valign="top" width="12.44%" headers="mcps1.2.6.1.2 "><p id="p15015581132"><a name="p15015581132"></a><a name="p15015581132"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.61%" headers="mcps1.2.6.1.3 "><p id="p56921593564"><a name="p56921593564"></a><a name="p56921593564"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="25.480000000000004%" headers="mcps1.2.6.1.4 "><p id="p136921359195618"><a name="p136921359195618"></a><a name="p136921359195618"></a>filter在H方向上的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="38.35%" headers="mcps1.2.6.1.5 "><p id="p523152894518"><a name="p523152894518"></a><a name="p523152894518"></a>stride_h = 1</p>
</td>
</tr>
<tr id="row1198393324510"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p1898353317457"><a name="p1898353317457"></a><a name="p1898353317457"></a>stride_w</p>
</td>
<td class="cellrowborder" valign="top" width="12.44%" headers="mcps1.2.6.1.2 "><p id="p16508581531"><a name="p16508581531"></a><a name="p16508581531"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.61%" headers="mcps1.2.6.1.3 "><p id="p499819412458"><a name="p499819412458"></a><a name="p499819412458"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="25.480000000000004%" headers="mcps1.2.6.1.4 "><p id="p1399834134511"><a name="p1399834134511"></a><a name="p1399834134511"></a>filter在W方向上的移动步长。</p>
</td>
<td class="cellrowborder" valign="top" width="38.35%" headers="mcps1.2.6.1.5 "><p id="p1986020122419"><a name="p1986020122419"></a><a name="p1986020122419"></a>stride_w = 1</p>
</td>
</tr>
</tbody>
</table>

### Matmul优化<a name="ZH-CN_TOPIC_0000002628690692" id="ZH-CN_TOPIC_0000002628690692"></a>

以下规格的Onnx算子在riscvOpt高性能模式下推理时间上有较大优化，算法工程师在AI模型设计时可以优先采用以下规格。

**表 1**  Matmul Onnx高效算子支持规格列表

<a name="table189651429122117"></a>
<table><thead align="left"><tr id="row1496911294216"><th class="cellrowborder" valign="top" width="14.032806561312263%" id="mcps1.2.6.1.1"><p id="p3340101235915"><a name="p3340101235915"></a><a name="p3340101235915"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.932986597319465%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.222844568913784%" id="mcps1.2.6.1.3"><p id="p1534011285913"><a name="p1534011285913"></a><a name="p1534011285913"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="28.875775155031008%" id="mcps1.2.6.1.4"><p id="p7340612155913"><a name="p7340612155913"></a><a name="p7340612155913"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="27.935587117423488%" id="mcps1.2.6.1.5"><p id="p1072813016591"><a name="p1072813016591"></a><a name="p1072813016591"></a>高效算子规格支持范围说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row4970192982114"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p103983121012"><a name="p103983121012"></a><a name="p103983121012"></a>A</p>
</td>
<td class="cellrowborder" valign="top" width="14.932986597319465%" headers="mcps1.2.6.1.2 "><p id="p139812121213"><a name="p139812121213"></a><a name="p139812121213"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.222844568913784%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.875775155031008%" headers="mcps1.2.6.1.4 "><p id="p1039831214110"><a name="p1039831214110"></a><a name="p1039831214110"></a>输入张量，维度为2D，格式为ND。</p>
</td>
<td class="cellrowborder" valign="top" width="27.935587117423488%" headers="mcps1.2.6.1.5 "><p id="p2877368212"><a name="p2877368212"></a><a name="p2877368212"></a>无特殊限制</p>
</td>
</tr>
<tr id="row6971132912215"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p14399111216119"><a name="p14399111216119"></a><a name="p14399111216119"></a>B</p>
</td>
<td class="cellrowborder" valign="top" width="14.932986597319465%" headers="mcps1.2.6.1.2 "><p id="p73991412910"><a name="p73991412910"></a><a name="p73991412910"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.222844568913784%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.875775155031008%" headers="mcps1.2.6.1.4 "><p id="p20860222122017"><a name="p20860222122017"></a><a name="p20860222122017"></a>权重张量，维度为2D。</p>
</td>
<td class="cellrowborder" valign="top" width="27.935587117423488%" headers="mcps1.2.6.1.5 "><p id="p94354200476"><a name="p94354200476"></a><a name="p94354200476"></a>无特殊限制</p>
</td>
</tr>
<tr id="row13973529102110"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p639913125119"><a name="p639913125119"></a><a name="p639913125119"></a>C</p>
</td>
<td class="cellrowborder" valign="top" width="14.932986597319465%" headers="mcps1.2.6.1.2 "><p id="p639920123113"><a name="p639920123113"></a><a name="p639920123113"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.222844568913784%" headers="mcps1.2.6.1.3 "><p id="p14476173516477"><a name="p14476173516477"></a><a name="p14476173516477"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.875775155031008%" headers="mcps1.2.6.1.4 "><p id="p639917121713"><a name="p639917121713"></a><a name="p639917121713"></a>偏置张量，维度为1D。</p>
</td>
<td class="cellrowborder" valign="top" width="27.935587117423488%" headers="mcps1.2.6.1.5 "><p id="p2043462094715"><a name="p2043462094715"></a><a name="p2043462094715"></a>无特殊限制</p>
</td>
</tr>
<tr id="row19973129102114"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p75541850190"><a name="p75541850190"></a><a name="p75541850190"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="14.932986597319465%" headers="mcps1.2.6.1.2 "><p id="p655417501497"><a name="p655417501497"></a><a name="p655417501497"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.222844568913784%" headers="mcps1.2.6.1.3 "><p id="p1447613357472"><a name="p1447613357472"></a><a name="p1447613357472"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="28.875775155031008%" headers="mcps1.2.6.1.4 "><p id="p155541650997"><a name="p155541650997"></a><a name="p155541650997"></a>输出张量，维度为2D，格式为ND。</p>
</td>
<td class="cellrowborder" valign="top" width="27.935587117423488%" headers="mcps1.2.6.1.5 "><p id="p343402019479"><a name="p343402019479"></a><a name="p343402019479"></a>无特殊限制</p>
</td>
</tr>
<tr id="row48490213206"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p1254114101281"><a name="p1254114101281"></a><a name="p1254114101281"></a>alpha</p>
</td>
<td class="cellrowborder" valign="top" width="14.932986597319465%" headers="mcps1.2.6.1.2 "><p id="p25419101988"><a name="p25419101988"></a><a name="p25419101988"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.222844568913784%" headers="mcps1.2.6.1.3 "><p id="p954191019819"><a name="p954191019819"></a><a name="p954191019819"></a>float</p>
</td>
<td class="cellrowborder" valign="top" width="28.875775155031008%" headers="mcps1.2.6.1.4 "><p id="p1631314581473"><a name="p1631314581473"></a><a name="p1631314581473"></a>A×B张量的缩放系数。</p>
</td>
<td class="cellrowborder" valign="top" width="27.935587117423488%" headers="mcps1.2.6.1.5 "><p id="p443312044717"><a name="p443312044717"></a><a name="p443312044717"></a>无特殊限制</p>
</td>
</tr>
<tr id="row18678242382"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p196785421812"><a name="p196785421812"></a><a name="p196785421812"></a><span id="ph1047817574113"><a name="ph1047817574113"></a><a name="ph1047817574113"></a>beta</span></p>
</td>
<td class="cellrowborder" valign="top" width="14.932986597319465%" headers="mcps1.2.6.1.2 "><p id="p1267810421187"><a name="p1267810421187"></a><a name="p1267810421187"></a><span id="ph20220250121218"><a name="ph20220250121218"></a><a name="ph20220250121218"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="14.222844568913784%" headers="mcps1.2.6.1.3 "><p id="p4678104211819"><a name="p4678104211819"></a><a name="p4678104211819"></a><span id="ph13200943161217"><a name="ph13200943161217"></a><a name="ph13200943161217"></a>float</span></p>
</td>
<td class="cellrowborder" valign="top" width="28.875775155031008%" headers="mcps1.2.6.1.4 "><p id="p26781742289"><a name="p26781742289"></a><a name="p26781742289"></a><span id="ph525523561214"><a name="ph525523561214"></a><a name="ph525523561214"></a>C的乘数。</span></p>
</td>
<td class="cellrowborder" valign="top" width="27.935587117423488%" headers="mcps1.2.6.1.5 "><p id="p96786421288"><a name="p96786421288"></a><a name="p96786421288"></a><span id="ph726891131316"><a name="ph726891131316"></a><a name="ph726891131316"></a>无特殊限制</span></p>
</td>
</tr>
<tr id="row17998732181019"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p3998832121015"><a name="p3998832121015"></a><a name="p3998832121015"></a><span id="ph10691833124"><a name="ph10691833124"></a><a name="ph10691833124"></a>transA</span></p>
</td>
<td class="cellrowborder" valign="top" width="14.932986597319465%" headers="mcps1.2.6.1.2 "><p id="p899817323105"><a name="p899817323105"></a><a name="p899817323105"></a><span id="ph1996620596126"><a name="ph1996620596126"></a><a name="ph1996620596126"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="14.222844568913784%" headers="mcps1.2.6.1.3 "><p id="p17998103213104"><a name="p17998103213104"></a><a name="p17998103213104"></a><span id="ph51857460126"><a name="ph51857460126"></a><a name="ph51857460126"></a>int</span></p>
</td>
<td class="cellrowborder" valign="top" width="28.875775155031008%" headers="mcps1.2.6.1.4 "><p id="p179986322104"><a name="p179986322104"></a><a name="p179986322104"></a><span id="ph71282038161218"><a name="ph71282038161218"></a><a name="ph71282038161218"></a>决定输入A是否转置。</span></p>
</td>
<td class="cellrowborder" valign="top" width="27.935587117423488%" headers="mcps1.2.6.1.5 "><p id="p129988328102"><a name="p129988328102"></a><a name="p129988328102"></a><span id="ph117442115131"><a name="ph117442115131"></a><a name="ph117442115131"></a>无特殊限制</span></p>
</td>
</tr>
<tr id="row13400111081217"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p8401710191214"><a name="p8401710191214"></a><a name="p8401710191214"></a><span id="ph44182118124"><a name="ph44182118124"></a><a name="ph44182118124"></a>transB</span></p>
</td>
<td class="cellrowborder" valign="top" width="14.932986597319465%" headers="mcps1.2.6.1.2 "><p id="p540151014123"><a name="p540151014123"></a><a name="p540151014123"></a><span id="ph14377019131"><a name="ph14377019131"></a><a name="ph14377019131"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="14.222844568913784%" headers="mcps1.2.6.1.3 "><p id="p13401171091218"><a name="p13401171091218"></a><a name="p13401171091218"></a><span id="ph8369174781213"><a name="ph8369174781213"></a><a name="ph8369174781213"></a>int</span></p>
</td>
<td class="cellrowborder" valign="top" width="28.875775155031008%" headers="mcps1.2.6.1.4 "><p id="p10401310121219"><a name="p10401310121219"></a><a name="p10401310121219"></a><span id="ph19697740171214"><a name="ph19697740171214"></a><a name="ph19697740171214"></a>决定输入B是否转置。</span></p>
</td>
<td class="cellrowborder" valign="top" width="27.935587117423488%" headers="mcps1.2.6.1.5 "><p id="p154011710151219"><a name="p154011710151219"></a><a name="p154011710151219"></a><span id="ph2016891211134"><a name="ph2016891211134"></a><a name="ph2016891211134"></a>无特殊限制</span></p>
</td>
</tr>
</tbody>
</table>

以下规格的TFLite算子在riscvOpt高性能模式下推理时间上有较大优化，算法工程师在AI模型设计时可以优先采用以下规格。

**表 2**  Matmul TFLite高效算子支持规格列表

<a name="table668985955612"></a>
<table><thead align="left"><tr id="row13690359165613"><th class="cellrowborder" valign="top" width="13.120000000000001%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="17.549999999999997%" id="mcps1.2.6.1.2"><p id="p2136105314214"><a name="p2136105314214"></a><a name="p2136105314214"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="14.39%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="26.87%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="28.07%" id="mcps1.2.6.1.5"><p id="p11445381638"><a name="p11445381638"></a><a name="p11445381638"></a>高效算子规格支持范围说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row0259114117411"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p112257544213"><a name="p112257544213"></a><a name="p112257544213"></a>x</p>
</td>
<td class="cellrowborder" valign="top" width="17.549999999999997%" headers="mcps1.2.6.1.2 "><p id="p17783152895719"><a name="p17783152895719"></a><a name="p17783152895719"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.39%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="26.87%" headers="mcps1.2.6.1.4 "><p id="p11225145413218"><a name="p11225145413218"></a><a name="p11225145413218"></a>输入张量，维度为3D/4D，格式分别为NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="28.07%" headers="mcps1.2.6.1.5 "><p id="p3958445174614"><a name="p3958445174614"></a><a name="p3958445174614"></a>无特殊限制</p>
</td>
</tr>
<tr id="row44831201652"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p13777511528"><a name="p13777511528"></a><a name="p13777511528"></a>y</p>
</td>
<td class="cellrowborder" valign="top" width="17.549999999999997%" headers="mcps1.2.6.1.2 "><p id="p768141275618"><a name="p768141275618"></a><a name="p768141275618"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.39%" headers="mcps1.2.6.1.3 "><p id="p17573133716412"><a name="p17573133716412"></a><a name="p17573133716412"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="26.87%" headers="mcps1.2.6.1.4 "><p id="p1077351627"><a name="p1077351627"></a><a name="p1077351627"></a>权重张量，维度为3D/4D，格式分别为NWC、NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="28.07%" headers="mcps1.2.6.1.5 "><p id="p495814453468"><a name="p495814453468"></a><a name="p495814453468"></a>无特殊限制</p>
</td>
</tr>
<tr id="row869245925620"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p085513466213"><a name="p085513466213"></a><a name="p085513466213"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="17.549999999999997%" headers="mcps1.2.6.1.2 "><p id="p1245412116319"><a name="p1245412116319"></a><a name="p1245412116319"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.39%" headers="mcps1.2.6.1.3 "><p id="p148550467217"><a name="p148550467217"></a><a name="p148550467217"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="26.87%" headers="mcps1.2.6.1.4 "><p id="p188554460214"><a name="p188554460214"></a><a name="p188554460214"></a>输出张量，维度为3D/4D，格式分别为NWC、NHWC。符合矩阵乘法运算规则。</p>
</td>
<td class="cellrowborder" valign="top" width="28.07%" headers="mcps1.2.6.1.5 "><p id="p14959745174611"><a name="p14959745174611"></a><a name="p14959745174611"></a>无特殊限制</p>
</td>
</tr>
<tr id="row369235919566"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p191801255115014"><a name="p191801255115014"></a><a name="p191801255115014"></a>adj_x</p>
</td>
<td class="cellrowborder" valign="top" width="17.549999999999997%" headers="mcps1.2.6.1.2 "><p id="p1150158930"><a name="p1150158930"></a><a name="p1150158930"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.39%" headers="mcps1.2.6.1.3 "><p id="p526953345212"><a name="p526953345212"></a><a name="p526953345212"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="26.87%" headers="mcps1.2.6.1.4 "><p id="p1486615211304"><a name="p1486615211304"></a><a name="p1486615211304"></a>是否对x的最后两个维度进行转置。</p>
</td>
<td class="cellrowborder" valign="top" width="28.07%" headers="mcps1.2.6.1.5 "><p id="p09591845144614"><a name="p09591845144614"></a><a name="p09591845144614"></a>无特殊限制</p>
</td>
</tr>
<tr id="row1198393324510"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p9156191441212"><a name="p9156191441212"></a><a name="p9156191441212"></a>adj_y</p>
</td>
<td class="cellrowborder" valign="top" width="17.549999999999997%" headers="mcps1.2.6.1.2 "><p id="p15015581132"><a name="p15015581132"></a><a name="p15015581132"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.39%" headers="mcps1.2.6.1.3 "><p id="p17678145075410"><a name="p17678145075410"></a><a name="p17678145075410"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="26.87%" headers="mcps1.2.6.1.4 "><p id="p45991644144318"><a name="p45991644144318"></a><a name="p45991644144318"></a>是否对y的最后两个维度进行转置。</p>
</td>
<td class="cellrowborder" valign="top" width="28.07%" headers="mcps1.2.6.1.5 "><p id="p1495914554617"><a name="p1495914554617"></a><a name="p1495914554617"></a><span id="ph175114117194"><a name="ph175114117194"></a><a name="ph175114117194"></a>无特殊限制</span></p>
</td>
</tr>
<tr id="row124651007199"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p147686913197"><a name="p147686913197"></a><a name="p147686913197"></a>asymmetric_quantize_inputs</p>
</td>
<td class="cellrowborder" valign="top" width="17.549999999999997%" headers="mcps1.2.6.1.2 "><p id="p11741141351919"><a name="p11741141351919"></a><a name="p11741141351919"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="14.39%" headers="mcps1.2.6.1.3 "><p id="p18720171691910"><a name="p18720171691910"></a><a name="p18720171691910"></a>bool</p>
</td>
<td class="cellrowborder" valign="top" width="26.87%" headers="mcps1.2.6.1.4 "><p id="p71921430151914"><a name="p71921430151914"></a><a name="p71921430151914"></a><span>BatchMatmul是否对输入进行非对称量化</span>。</p>
</td>
<td class="cellrowborder" valign="top" width="28.07%" headers="mcps1.2.6.1.5 "><p id="p13465160131918"><a name="p13465160131918"></a><a name="p13465160131918"></a><span id="ph8733142101917"><a name="ph8733142101917"></a><a name="ph8733142101917"></a>无特殊限制</span></p>
</td>
</tr>
</tbody>
</table>

### MaxPool/AveragePool优化<a name="ZH-CN_TOPIC_0000002661401189" id="ZH-CN_TOPIC_0000002661401189"></a>

以下规格的Onnx算子在riscvOpt高性能模式下推理时间上有较大优化，算法工程师在AI模型设计时可以优先采用以下规格。

**表 1**  MaxPool / AveragePool Onnx高效算子支持规格列表

<a name="table189651429122117"></a>
<table><thead align="left"><tr id="row1496911294216"><th class="cellrowborder" valign="top" width="14.032806561312263%" id="mcps1.2.6.1.1"><p id="p3340101235915"><a name="p3340101235915"></a><a name="p3340101235915"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="11.822364472894579%" id="mcps1.2.6.1.2"><p id="p1650105819311"><a name="p1650105819311"></a><a name="p1650105819311"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="10.072014402880576%" id="mcps1.2.6.1.3"><p id="p1534011285913"><a name="p1534011285913"></a><a name="p1534011285913"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="25.725145029005798%" id="mcps1.2.6.1.4"><p id="p7340612155913"><a name="p7340612155913"></a><a name="p7340612155913"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="38.34766953390678%" id="mcps1.2.6.1.5"><p id="p1072813016591"><a name="p1072813016591"></a><a name="p1072813016591"></a>高效算子规格支持范围说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row4970192982114"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p814484714519"><a name="p814484714519"></a><a name="p814484714519"></a>X</p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p16144114785114"><a name="p16144114785114"></a><a name="p16144114785114"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p67768585268"><a name="p67768585268"></a><a name="p67768585268"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p5776175813266"><a name="p5776175813266"></a><a name="p5776175813266"></a>输入张量，维度为3D或4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p18848151322319"><a name="p18848151322319"></a><a name="p18848151322319"></a>无特殊限制</p>
</td>
</tr>
<tr id="row6971132912215"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p18729439018"><a name="p18729439018"></a><a name="p18729439018"></a>Y</p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p198723431017"><a name="p198723431017"></a><a name="p198723431017"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p577685812611"><a name="p577685812611"></a><a name="p577685812611"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p57261613112110"><a name="p57261613112110"></a><a name="p57261613112110"></a>输出张量，维度为3D或4D，格式为NCW/NCHW。</p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p6847131316239"><a name="p6847131316239"></a><a name="p6847131316239"></a>无特殊限制</p>
</td>
</tr>
<tr id="row13973529102110"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p211803695110"><a name="p211803695110"></a><a name="p211803695110"></a>auto_pad</p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p4118173613511"><a name="p4118173613511"></a><a name="p4118173613511"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p71181836115119"><a name="p71181836115119"></a><a name="p71181836115119"></a>string</p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p1577685818263"><a name="p1577685818263"></a><a name="p1577685818263"></a>指定padding的类型。</p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p14897185443916"><a name="p14897185443916"></a><a name="p14897185443916"></a>配置范围：NOTSET、SAME_UPPER、SAME_LOWER、VALID</p>
</td>
</tr>
<tr id="row19973129102114"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p1311833614510"><a name="p1311833614510"></a><a name="p1311833614510"></a>ceil_mode</p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p10118153617514"><a name="p10118153617514"></a><a name="p10118153617514"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p411814360514"><a name="p411814360514"></a><a name="p411814360514"></a>int</p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p1351318783714"><a name="p1351318783714"></a><a name="p1351318783714"></a>输出形状的取整方式。</p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p10748523112318"><a name="p10748523112318"></a><a name="p10748523112318"></a>规格约束：仅支持floor</p>
</td>
</tr>
<tr id="row48490213206"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p211883675111"><a name="p211883675111"></a><a name="p211883675111"></a>dilations</p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p811833615513"><a name="p811833615513"></a><a name="p811833615513"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p17777145822614"><a name="p17777145822614"></a><a name="p17777145822614"></a>list(int)</p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p3776105813265"><a name="p3776105813265"></a><a name="p3776105813265"></a>每个轴上的扩张系数。</p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p147561323132312"><a name="p147561323132312"></a><a name="p147561323132312"></a><span id="ph183481916394"><a name="ph183481916394"></a><a name="ph183481916394"></a>dilations</span> = 1</p>
</td>
</tr>
<tr id="row697811471398"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p8979647133920"><a name="p8979647133920"></a><a name="p8979647133920"></a><span id="ph958483420407"><a name="ph958483420407"></a><a name="ph958483420407"></a>kernel_shape</span></p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p3979184718393"><a name="p3979184718393"></a><a name="p3979184718393"></a><span id="ph59404412408"><a name="ph59404412408"></a><a name="ph59404412408"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p139791447113914"><a name="p139791447113914"></a><a name="p139791447113914"></a><span id="ph7997135284013"><a name="ph7997135284013"></a><a name="ph7997135284013"></a>list(int)</span></p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p15979114763915"><a name="p15979114763915"></a><a name="p15979114763915"></a><span id="ph189885813407"><a name="ph189885813407"></a><a name="ph189885813407"></a>kernel沿各轴的大小。</span></p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p20979164773916"><a name="p20979164773916"></a><a name="p20979164773916"></a><span id="ph14561167114115"><a name="ph14561167114115"></a><a name="ph14561167114115"></a>1 <= kernel_shape <=5</span></p>
</td>
</tr>
<tr id="row4613111544115"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p36136152412"><a name="p36136152412"></a><a name="p36136152412"></a><span id="ph23589202418"><a name="ph23589202418"></a><a name="ph23589202418"></a>pads</span></p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p0613215114112"><a name="p0613215114112"></a><a name="p0613215114112"></a><span id="ph1142523134116"><a name="ph1142523134116"></a><a name="ph1142523134116"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p7613121544112"><a name="p7613121544112"></a><a name="p7613121544112"></a><span id="ph1815828144113"><a name="ph1815828144113"></a><a name="ph1815828144113"></a>list(int)</span></p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p1761319156416"><a name="p1761319156416"></a><a name="p1761319156416"></a><span id="ph1669283017411"><a name="ph1669283017411"></a><a name="ph1669283017411"></a>各轴前后填充零的个数。</span></p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p5613215154111"><a name="p5613215154111"></a><a name="p5613215154111"></a><span id="ph169811446154115"><a name="ph169811446154115"></a><a name="ph169811446154115"></a>无特殊限制</span></p>
</td>
</tr>
<tr id="row58991352204119"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p10899185219412"><a name="p10899185219412"></a><a name="p10899185219412"></a><span id="ph76365412429"><a name="ph76365412429"></a><a name="ph76365412429"></a>storage_order</span></p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p1089913522412"><a name="p1089913522412"></a><a name="p1089913522412"></a><span id="ph199245610427"><a name="ph199245610427"></a><a name="ph199245610427"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p289918520414"><a name="p289918520414"></a><a name="p289918520414"></a><span id="ph1658216818426"><a name="ph1658216818426"></a><a name="ph1658216818426"></a>int</span></p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p58991352154113"><a name="p58991352154113"></a><a name="p58991352154113"></a><span id="ph114961511134212"><a name="ph114961511134212"></a><a name="ph114961511134212"></a>张量存储主序。</span></p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p1389915214112"><a name="p1389915214112"></a><a name="p1389915214112"></a><span id="ph3294651124417"><a name="ph3294651124417"></a><a name="ph3294651124417"></a>规格约束：仅支持0</span></p>
</td>
</tr>
<tr id="row13111119104213"><td class="cellrowborder" valign="top" width="14.032806561312263%" headers="mcps1.2.6.1.1 "><p id="p113123191421"><a name="p113123191421"></a><a name="p113123191421"></a><span id="ph9885822104212"><a name="ph9885822104212"></a><a name="ph9885822104212"></a>strides</span></p>
</td>
<td class="cellrowborder" valign="top" width="11.822364472894579%" headers="mcps1.2.6.1.2 "><p id="p19312141994220"><a name="p19312141994220"></a><a name="p19312141994220"></a><span id="ph734213255421"><a name="ph734213255421"></a><a name="ph734213255421"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="10.072014402880576%" headers="mcps1.2.6.1.3 "><p id="p9312151974219"><a name="p9312151974219"></a><a name="p9312151974219"></a><span id="ph29007288424"><a name="ph29007288424"></a><a name="ph29007288424"></a>list(int)</span></p>
</td>
<td class="cellrowborder" valign="top" width="25.725145029005798%" headers="mcps1.2.6.1.4 "><p id="p14312111954212"><a name="p14312111954212"></a><a name="p14312111954212"></a><span id="ph07981031184214"><a name="ph07981031184214"></a><a name="ph07981031184214"></a>各个方向上kernel的移动步长。</span></p>
</td>
<td class="cellrowborder" valign="top" width="38.34766953390678%" headers="mcps1.2.6.1.5 "><p id="p203121819124217"><a name="p203121819124217"></a><a name="p203121819124217"></a><span id="ph2811113444216"><a name="ph2811113444216"></a><a name="ph2811113444216"></a>1 <= strides <= 5</span></p>
</td>
</tr>
</tbody>
</table>

以下规格的TFLite算子在riscvOpt高性能模式下推理时间上有较大优化，算法工程师在AI模型设计时可以优先采用以下规格。

**表 2**  MaxPool2D / AveragePool2D TFLite高效算子支持规格列表

<a name="table668985955612"></a>
<table><thead align="left"><tr id="row13690359165613"><th class="cellrowborder" valign="top" width="13.120000000000001%" id="mcps1.2.6.1.1"><p id="p369065912564"><a name="p369065912564"></a><a name="p369065912564"></a>参数名</p>
</th>
<th class="cellrowborder" valign="top" width="14.77%" id="mcps1.2.6.1.2"><p id="p2136105314214"><a name="p2136105314214"></a><a name="p2136105314214"></a>参数/输入输出</p>
</th>
<th class="cellrowborder" valign="top" width="10.27%" id="mcps1.2.6.1.3"><p id="p769019599566"><a name="p769019599566"></a><a name="p769019599566"></a>数据类型</p>
</th>
<th class="cellrowborder" valign="top" width="30.959999999999997%" id="mcps1.2.6.1.4"><p id="p1069045919565"><a name="p1069045919565"></a><a name="p1069045919565"></a>参数含义</p>
</th>
<th class="cellrowborder" valign="top" width="30.880000000000003%" id="mcps1.2.6.1.5"><p id="p11445381638"><a name="p11445381638"></a><a name="p11445381638"></a>高效算子规格支持范围说明</p>
</th>
</tr>
</thead>
<tbody><tr id="row44831201652"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p72592411944"><a name="p72592411944"></a><a name="p72592411944"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="14.77%" headers="mcps1.2.6.1.2 "><p id="p1425914411416"><a name="p1425914411416"></a><a name="p1425914411416"></a>input</p>
</td>
<td class="cellrowborder" valign="top" width="10.27%" headers="mcps1.2.6.1.3 "><p id="p82590411149"><a name="p82590411149"></a><a name="p82590411149"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.959999999999997%" headers="mcps1.2.6.1.4 "><p id="p9421530351"><a name="p9421530351"></a><a name="p9421530351"></a>输入张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="30.880000000000003%" headers="mcps1.2.6.1.5 "><p id="p1725934116412"><a name="p1725934116412"></a><a name="p1725934116412"></a>无特殊限制</p>
</td>
</tr>
<tr id="row869245925620"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p194831017511"><a name="p194831017511"></a><a name="p194831017511"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="14.77%" headers="mcps1.2.6.1.2 "><p id="p048340450"><a name="p048340450"></a><a name="p048340450"></a>output</p>
</td>
<td class="cellrowborder" valign="top" width="10.27%" headers="mcps1.2.6.1.3 "><p id="p124839018518"><a name="p124839018518"></a><a name="p124839018518"></a>tensor</p>
</td>
<td class="cellrowborder" valign="top" width="30.959999999999997%" headers="mcps1.2.6.1.4 "><p id="p13483801352"><a name="p13483801352"></a><a name="p13483801352"></a>输出张量，维度为4D，格式为NHWC。</p>
</td>
<td class="cellrowborder" valign="top" width="30.880000000000003%" headers="mcps1.2.6.1.5 "><p id="p748310020510"><a name="p748310020510"></a><a name="p748310020510"></a>无特殊限制</p>
</td>
</tr>
<tr id="row369235919566"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p1269165919569"><a name="p1269165919569"></a><a name="p1269165919569"></a>filter_height</p>
</td>
<td class="cellrowborder" valign="top" width="14.77%" headers="mcps1.2.6.1.2 "><p id="p2509588318"><a name="p2509588318"></a><a name="p2509588318"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.27%" headers="mcps1.2.6.1.3 "><p id="p469110599562"><a name="p469110599562"></a><a name="p469110599562"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.959999999999997%" headers="mcps1.2.6.1.4 "><p id="p126911459165613"><a name="p126911459165613"></a><a name="p126911459165613"></a>在H方向上的过滤窗口大小。</p>
</td>
<td class="cellrowborder" valign="top" width="30.880000000000003%" headers="mcps1.2.6.1.5 "><p id="p1447651443920"><a name="p1447651443920"></a><a name="p1447651443920"></a>1<=filter_height<=5</p>
</td>
</tr>
<tr id="row1198393324510"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p1169119595569"><a name="p1169119595569"></a><a name="p1169119595569"></a>filter_width</p>
</td>
<td class="cellrowborder" valign="top" width="14.77%" headers="mcps1.2.6.1.2 "><p id="p65015581736"><a name="p65015581736"></a><a name="p65015581736"></a>attribute</p>
</td>
<td class="cellrowborder" valign="top" width="10.27%" headers="mcps1.2.6.1.3 "><p id="p769119597568"><a name="p769119597568"></a><a name="p769119597568"></a>int32</p>
</td>
<td class="cellrowborder" valign="top" width="30.959999999999997%" headers="mcps1.2.6.1.4 "><p id="p1614615144496"><a name="p1614615144496"></a><a name="p1614615144496"></a>在W方向上的过滤窗口大小。</p>
</td>
<td class="cellrowborder" valign="top" width="30.880000000000003%" headers="mcps1.2.6.1.5 "><p id="p4868183464414"><a name="p4868183464414"></a><a name="p4868183464414"></a>1<=<span id="ph343635465210"><a name="ph343635465210"></a><a name="ph343635465210"></a>filter_width</span><=5</p>
</td>
</tr>
<tr id="row993262644317"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p793312260434"><a name="p793312260434"></a><a name="p793312260434"></a><span id="ph55381038194319"><a name="ph55381038194319"></a><a name="ph55381038194319"></a>fused_activation_function</span></p>
</td>
<td class="cellrowborder" valign="top" width="14.77%" headers="mcps1.2.6.1.2 "><p id="p893372674320"><a name="p893372674320"></a><a name="p893372674320"></a><span id="ph756312401437"><a name="ph756312401437"></a><a name="ph756312401437"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="10.27%" headers="mcps1.2.6.1.3 "><p id="p6933182654313"><a name="p6933182654313"></a><a name="p6933182654313"></a><span id="ph6327742174316"><a name="ph6327742174316"></a><a name="ph6327742174316"></a>string</span></p>
</td>
<td class="cellrowborder" valign="top" width="30.959999999999997%" headers="mcps1.2.6.1.4 "><p id="p99331726154312"><a name="p99331726154312"></a><a name="p99331726154312"></a><span id="ph663712442434"><a name="ph663712442434"></a><a name="ph663712442434"></a>融合的激活函数类型。</span></p>
</td>
<td class="cellrowborder" valign="top" width="30.880000000000003%" headers="mcps1.2.6.1.5 "><p id="p1293342694311"><a name="p1293342694311"></a><a name="p1293342694311"></a><span id="ph158441816448"><a name="ph158441816448"></a><a name="ph158441816448"></a>配置范围：NONE、RELU</span></p>
</td>
</tr>
<tr id="row16677233154317"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p5677533114319"><a name="p5677533114319"></a><a name="p5677533114319"></a><span id="ph198105894911"><a name="ph198105894911"></a><a name="ph198105894911"></a>padding</span></p>
</td>
<td class="cellrowborder" valign="top" width="14.77%" headers="mcps1.2.6.1.2 "><p id="p1267743324312"><a name="p1267743324312"></a><a name="p1267743324312"></a><span id="ph871215085013"><a name="ph871215085013"></a><a name="ph871215085013"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="10.27%" headers="mcps1.2.6.1.3 "><p id="p1467716336437"><a name="p1467716336437"></a><a name="p1467716336437"></a><span id="ph78446319509"><a name="ph78446319509"></a><a name="ph78446319509"></a>string</span></p>
</td>
<td class="cellrowborder" valign="top" width="30.959999999999997%" headers="mcps1.2.6.1.4 "><p id="p16677103344313"><a name="p16677103344313"></a><a name="p16677103344313"></a><span id="ph184682545012"><a name="ph184682545012"></a><a name="ph184682545012"></a>填充类型。</span></p>
</td>
<td class="cellrowborder" valign="top" width="30.880000000000003%" headers="mcps1.2.6.1.5 "><p id="p17677183315437"><a name="p17677183315437"></a><a name="p17677183315437"></a><span id="ph9253156165415"><a name="ph9253156165415"></a><a name="ph9253156165415"></a>配置范围：SAME、VALID</span></p>
</td>
</tr>
<tr id="row198553296437"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p1285582916435"><a name="p1285582916435"></a><a name="p1285582916435"></a><span id="ph12951484502"><a name="ph12951484502"></a><a name="ph12951484502"></a>stride_h</span></p>
</td>
<td class="cellrowborder" valign="top" width="14.77%" headers="mcps1.2.6.1.2 "><p id="p3855172918433"><a name="p3855172918433"></a><a name="p3855172918433"></a><span id="ph421691165014"><a name="ph421691165014"></a><a name="ph421691165014"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="10.27%" headers="mcps1.2.6.1.3 "><p id="p985502924312"><a name="p985502924312"></a><a name="p985502924312"></a><span id="ph9761350502"><a name="ph9761350502"></a><a name="ph9761350502"></a>int32</span></p>
</td>
<td class="cellrowborder" valign="top" width="30.959999999999997%" headers="mcps1.2.6.1.4 "><p id="p4855162916437"><a name="p4855162916437"></a><a name="p4855162916437"></a><span id="ph1832414270501"><a name="ph1832414270501"></a><a name="ph1832414270501"></a>filter在H方向上的移动步长。</span></p>
</td>
<td class="cellrowborder" valign="top" width="30.880000000000003%" headers="mcps1.2.6.1.5 "><p id="p585520299434"><a name="p585520299434"></a><a name="p585520299434"></a><span id="ph172631628155319"><a name="ph172631628155319"></a><a name="ph172631628155319"></a>1<=stride_h<=5</span></p>
</td>
</tr>
<tr id="row2232919114316"><td class="cellrowborder" valign="top" width="13.120000000000001%" headers="mcps1.2.6.1.1 "><p id="p52337195436"><a name="p52337195436"></a><a name="p52337195436"></a><span id="ph878018106502"><a name="ph878018106502"></a><a name="ph878018106502"></a>stride_w</span></p>
</td>
<td class="cellrowborder" valign="top" width="14.77%" headers="mcps1.2.6.1.2 "><p id="p52331219144311"><a name="p52331219144311"></a><a name="p52331219144311"></a><span id="ph188311814509"><a name="ph188311814509"></a><a name="ph188311814509"></a>attribute</span></p>
</td>
<td class="cellrowborder" valign="top" width="10.27%" headers="mcps1.2.6.1.3 "><p id="p5233619134311"><a name="p5233619134311"></a><a name="p5233619134311"></a><span id="ph1117314614509"><a name="ph1117314614509"></a><a name="ph1117314614509"></a>int32</span></p>
</td>
<td class="cellrowborder" valign="top" width="30.959999999999997%" headers="mcps1.2.6.1.4 "><p id="p1923311196432"><a name="p1923311196432"></a><a name="p1923311196432"></a><span id="ph753092915020"><a name="ph753092915020"></a><a name="ph753092915020"></a>filter在W方向上的移动步长。</span></p>
</td>
<td class="cellrowborder" valign="top" width="30.880000000000003%" headers="mcps1.2.6.1.5 "><p id="p18233161919436"><a name="p18233161919436"></a><a name="p18233161919436"></a><span id="ph129761031105317"><a name="ph129761031105317"></a><a name="ph129761031105317"></a>1<=stride_w<=5</span></p>
</td>
</tr>
</tbody>
</table>
