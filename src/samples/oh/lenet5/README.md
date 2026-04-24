# HiSpark.AI LeNet-5 手写数字识别 Sample

## 介绍
LeNet-5手写数字识别Sample基于Yann LeCun团队开源的MNIST数据集以及开源LeNet-5模型，为海思智能终端芯片提供适配的量化，模型转换以及端侧部署的Sample。客户可以基于此Sample为范式迁移部署相应的手写数字识别模型。

支持的芯片列表如下：
- **Hi3863**: 基于MSLite-Micro平台进行模型部署，依靠RISC-V CPU核进行AI推理。
- **Hi3322**: 基于CANN平台进行模型部署，依靠Nano NPU核进行AI推理。
- **Hi1156**: 基于CANN平台进行模型部署，依靠Tiny NPU核进行AI推理。

## 目录结构
samples lenet5的目录结构如下所示：
```
samples
├── CMakeLists.txt
├── oh
│   ├── lenet5
│   │   ├── build.sh
│   │   ├── CMakeLists.txt
│   │   ├── data
│   │   │   └── README.md
│   │   ├── model
│   │   │   ├── mnist-12.onnx
│   │   │   └── README.md
│   │   ├── README.md
│   │   ├── scripts
│   │   │   └── preproc_mnist_data.py
│   │   └── src
│   │       └── ai_main.c
│   └── ......
└── README.md
```
- **build.sh脚本**: 用于编译Sample模型。需要配置对应的SDK_PATH 以及 ADAPTOR_PATH。
- **CMakeLists.txt**: Sample的编译框架，C代码实现。
- **model目录**: 用于存放对应的onnx原始模型。
- **scripts目录**: 用于存放对应的数据处理脚本，自动生成量化以及验证数据。
- **src文件夹**: 用于存放板端推理源文件源码。
- **README**: 此Sample的介绍。

## 预处理

- **模型准备：**
对应的原始模型 **mnist-12.onnx**已放置在model一级目录下。

- **数据准备：**
运行Scripts目录下的预处理脚本，自动下载对应的原始MNIST数据集，并处理和保存生成Sample需要的文件格式。
    ```
python scripts/preproc_mnist_data.py --orig_path ./data --train_path ./train_data --test_path ./test_data --train_file_format bin --test_file_format all [--test_data_type float32]
    ```
    参数说明：
    - --orig_path：MNIST原始数据对应的目录
    - --train_path：训练集保存目录
    - --test_path：测试集保存目录
    - --train_file_format：训练集的保存格式，可选值包括bin，npy, all
    - --test_file_format：测试集的保存格式，可选值包括bin，npy, all
    - --test_data_type：测试集的bin格式文件的数据类型，可选值包括float16, float32  

Tips:
1. 如果为RISC-V平台需要在之后加上 [--test_data_type float32] 选项，Nano、Tiny平台则不需要。
2. 网络问题导致下载出现问题，可以手动创建./data/MNIST/raw文件夹，并下载数据包 [train-images-idx3-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/train-images-idx3-ubyte.gz)、[train-labels-idx1-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/train-labels-idx1-ubyte.gz)、[t10k-images-idx3-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/t10k-images-idx3-ubyte.gz)、[t10k-labels-idx1-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/t10k-labels-idx1-ubyte.gz)到raw下，再执行脚本。

- **配置文件准备：**
新建micro_quant.cfg文件，其中train_data/bin替换为实际的绝对路径
    ```
    [micro_param]
    enable_micro=true
    target=RISCV
    support_parallel=false
    [common_quant_param]
    quant_type=FULL_QUANT
    bit_num=8
    [data_preprocess_param]
    calibrate_path=Input3:train_data/bin
    calibrate_size=60000
    input_type=BIN
    [full_quant_param]
    activation_quant_method=MAX_MIN
    bias_correction=true
    enable_all_ops=false
    ```

## 模型转换&编译&烧录调试
参考[HiSpark.AI开源项目](https://gitcode.com/HiSpark/hispark_ai)README.md中"HiSpark.AI 平台快速入门指南"小节完成模型转换、编译、烧录调试  
其中模型转换时使用的cfg_path更改为上述准备的配置文件

- **Nano平台量化指南**
```
amct_onnx calibration --model "./model/mnist-12.onnx" --save_path "./output/mnist" --input_shape "Input3:1,1,28,28" --data_dir "./train_data/bin" --data_types "float32" --batch_num 9999
```
参数说明：
- --model：原始ONNX模型路径
- --save_path: 量化后模型的存放路径
- --input_shape: 指定模型输入的shape
- --data_dir: 与模型匹配的bin格式数据集路径
- --data_types: 输入数据的类型
- --batch_num: 训练后量化推理阶段的batch数

运行成功后生成
- ./output/mnist_fake_quant_model.onnx
- ./output/mnist_deploy_model.onnx

## RISC-V平台模型转换指南
- **模型代码生成**
将mindspore lib库的路径添加到LD_LIBRARY_PATH中
```
export LD_LIBRARY_PATH={PKG}/mindspore-enterprise-lite-{version}-linux-x64/tools/converter/lib:$LD_LIBRARY_PATH
```
接着开始进行模型的编译：
```
./{PKG}/mindspore-enterprise-lite-{version}-linux-x64/tools/converter/converter/converter_lite --fmk=ONNX --modelFile={MODEL_PATH}/xxx.onnx --outputFile={OUTPUT_PATH} --configFile={MODEL_PATH}/micro_quant.cfg --encryption=false --inputDataFormat=NCHW --outputDataFormat=NCHW --inputDataType=FLOAT --outputDataType=FLOAT
```
以Onnx为例，{MODEL_PATH}模型用例路径，{PKG}表示整包路径，{OUTPUT_PATH}表示自动生成项目的输出路径。

- **链接库编译（二次编译）**
到达生成库同级路径，并且解压WS63中SDK包，找到编译链路径，默认推荐：
```
COMPILER_PATH={SDK}/tools/bin/compiler/riscv/cc_riscv32_musl_{version}/cc_riscv32_musl/bin
```
之后进行链接库编译：
```
cd {OUTPUT_PATH}
rm -rf build
cmake -S . -B build \
        -D OP_LIB="{PKG}/mindspore-enterprise-lite-{version}-linux-x64/tools/codegen/lib/riscv/libnnacl.a" \
        -D WRAPPER_LIB="{PKG}/mindspore-enterprise-lite-{version}-linux-x64/tools/codegen/lib/riscv/libwrapper.a" \
        -D RISCV_TOOLCHAIN_PATH={COMPILER_PATH} \
        -D PKG_PATH="{PKG}/mindspore-enterprise-lite-{version}-linux-x64"
cd build
make -j4
```
编译完成后，将build文件夹生成的libnet.a以及libmicro_runtime.a拷贝到SDK对应路径下：
```
cp {OUTPUT_PATH}/build/libmicro_runtime.a {SDK}/middleware/utils/ai_mcu/lib
cp {OUTPUT_PATH}/build/src/libnet.a {SDK}/middleware/utils/ai_mcu/lib
```
之后参考运行指南，完成samples的修改，以及samples的编译

## Nano平台模型转换指南
```
atc --model=./output/mnist_deploy_model.onnx --framework=5 --output=./output/mnist --input_fp16_nodes="Input3" --output_type=FP16 --soc_version=Ascend035A --input_shape=Input3:1,1,28,28 --mode=30
```

参数说明
- --model: 网络模型文件路径与文件名
- --framework: 原始网络模型框架类型。5表示ONNX
- --output：存放转换后的离线模型的路径以及文件名
- --input_fp16_nodes：指定输入数据类型为FP16的输入节点名称
- --output_type：指定网络输出数据类型
- --soc_version：指定模型转换时昇腾AI处理器的版本
- --input_shape：指定模型输入数据的shape
- --mode：运行模式

运行成功后生成
- ./output/mnist.exeom
- ./output/mnist.dbg

## Tiny平台模型转换指南
```
atc --model=./model/mnist-12.onnx --framework=5 --output=./output/mnist --input_fp16_nodes="Input3" --output_type=FP16 --soc_version=Ascend031 --input_shape=Input3:1,1,28,28
```
参数说明
- --model: 网络模型文件路径与文件名
- --framework: 原始网络模型框架类型。5表示ONNX
- --output：存放转换后的离线模型的路径以及文件名
- --input_fp16_nodes：指定输入数据类型为FP16的输入节点名称
- --output_type：指定网络输出数据类型
- --soc_version：指定模型转换时昇腾AI处理器的版本
- --input_shape：指定模型输入数据的shape
- --mode：运行模式

运行成功后生成
- ./output/mnist.om

## RISC-V平台编译指南
1. 获取Hi3863 SDK的代码，保存在用户指定路径，其路径为{SDK_PATH}。
    路径如下表示解压成功，且目录正确：
    {SDK_PATH}
        |---- application
        |---- drivers
        |---- build
        |---- protocol
        |---- ....
        |---- build.py
2. 获取HiSpark.AI Adaptor包，并进行解压,其以及路径为{ADAPTOR_PATH}。
    解压命令为；tar -zxvf HiSpark.AI_{version}-adaptor.tar.gz -C ${ADAPTOR_PATH}
    路径如下表示解压成功，且目录正确：
    {ADAPTOR_PATH}
        |---- adaptor
        |---- include
3. 获取此HiSpark.AI Samples包
4. 根据业务修改Sample包，根据下方新版本Sample的说明
5. 将HiSpark.AI MSLite Micro工具链编译出的libmicro_runtime.a libnet.a复制到SDK的路径下
        即${SDK_PATH}/middleware/utils/ai_mcu/lib目录下，若目录不存在则需要创建此目录
6. 在命令行输入：
```
export SDK_PATH=${SDK_PATH}
export ADAPTOR_PATH=${ADAPTOR_PATH}
./build.sh
```
7. 获取编译成功的fwpkg文件，在${SDK_PATH}/output/ws63/fwpkg/ws63-liteos-app/ws63-liteos-app_all.fwpkg路径下

## Nano平台编译指南
1. 获取Hi3322 SDK的代码，保存在用户指定路径
    路径如下表示解压成功，且目录正确：
    {SDK_PATH}
        |---- application
        |---- bootloader
        |---- build
        |---- drivers
        |---- ....
        |---- build.py
2. 获取HiSpark.AI Adaptor包，并进行解压
    解压命令为；tar -zxvf HiSpark.AI_{version}-adaptor.tar.gz
    路径如下表示解压成功，且目录正确：
    {ADAPTOR_PATH}
        |---- adaptor
        |---- include
        |---- README.md
3. 获取此HiSpark.AI Samples包，并进行解压
    解压命令为；tar -zxvf HiSpark.AI_{version}-sample.tar.gz
    路径如下表示解压成功，且目录正确：
    {SAMPLE_PATH}
        |---- amct
        |---- oh
        |---- CMakeLists.txt
        |---- README.md
4. 切换到lenet5目录，在命令行输入：
```
export SDK_PATH=${SDK_PATH}
export ADAPTOR_PATH=${ADAPTOR_PATH}
bash ${SAMPLE_PATH}/oh/lenet5/build_npu.sh 3322
```
5. 获取编译成功的fwpkg文件，在${SAMPLE_PATH}/oh/lenet5/output路径下

**烧录指南**
1. 使用burntool工具将fwpkg镜像烧录到3322单板

**文件上传指南**
1. 使用Debugkits工具将输入数据上传到板端如下路径/user/sample_mnist.bin
    在Debugkits中依次选择 System / Uploading And Downloading / To Board
    在Local File Path中选择要上传的数据文件，即preprocess_mnist_data脚本生成的验证集数据文件，如./test_data/bin/sample_00000_7.bin
    在Board File Path中填入：/user/sample_mnist.bin
2. 使用Debugkits工具将模型上传到板端如下路径/user/mnist.exeom
    在Debugkits中依次选择 System / Uploading And Downloading / To Board
    在Local File Path中选择要上传的数据文件，如模型转换指南中生成的./output/mnist.exeom
    在Board File Path中填入：/user/mnist.exeom

**运行指南**
1. 使用sscom发送AT指令：AT^SAMPLE

## Tiny平台编译指南
1. 获取Hi1156 SDK的代码，保存在用户指定路径
2. 获取HiSpark.AI Adaptor包，并进行解压
    解压命令为；tar -zxvf HiSpark.AI_{version}-adaptor.tar.gz
    路径如下表示解压成功，且目录正确：
    {ADAPTOR_PATH}
        |---- adaptor
        |---- include
        |---- README.md
3. 获取此HiSpark.AI Samples包，并进行解压
    解压命令为；tar -zxvf HiSpark.AI_{version}-sample.tar.gz
    路径如下表示解压成功，且目录正确：
    {SAMPLE_PATH}
        |---- amct
        |---- oh
        |---- CMakeLists.txt
        |---- README.md
4. 切换到lenet5目录，在命令行输入：
```
export SDK_PATH=${SDK_PATH}
export ADAPTOR_PATH=${ADAPTOR_PATH}
export COMPILER_PATH=${COMPILER_PATH}
export ACL_HEADER_PATH=${ACL_HEADER_PATH}
bash ${SAMPLE_PATH}/oh/lenet5/build_npu.sh 1156
```
注：
(1) COMPILER_PATH即交叉编译工具的路径，例如：/subsystem/prebuilts/compiler/gcc-arm-v01c01-linux-musleabi/arm-v01c01-linux-musleabi-gcc
(2) ACL_HEADER_PATH即AscendCL头文件目录，例如：/image/hi5612/npu/cann_lib/acl

5. 获取编译成功的可执行文件lenet1156，在./src/build路径下
   获取编译成功的so文件libai_adaptor_tiny.so，在`${ADAPTOR_PATH}/adaptor/npu/build`路径下

**运行指南**
1. 创建一个目录，将其路径记作SRC_PATH。
    将`${SDK_PATH}/software/tiangong2_image_release/NPU/npu_turing_master/release/lib`目录拷贝到SRC_PATH下
    将`${SDK_PATH}/software/tiangong2_image_release/NPU/npu_turing_master/release/ko`目录拷贝到SRC_PATH下
    将编译指南中获得的可执行文件lenet1156拷贝到SRC_PATH下
    将编译指南中获得的so文件libai_adaptor_tiny.so复制到SRC_PATH/lib下
    将模型转换指南中获得的模型文件，如./output/mnist.om，拷贝到SRC_PATH下
    将数据处理指南中获得的输入数据，如./test_data/bin/sample_00000_7.bin，拷贝到SRC_PATH下并重命名为sample.bin
2. 在板端/etc目录下创建workspace目录，利用nfs工具将SRC_PATH挂载到板端/etc/workspace
3. 进入/etc/workspace/ko文件夹,依次执行以下命令
    #若之前加载过，就先卸载ko
    rmmod drv_tsdrv.ko
    rmmod drv_tsmem.ko
    rmmod drv_log.ko
    #加载ko
    insmod drv_log.ko
    insmod drv_tsmem.ko
    insmod drv_tsdrv.ko
4. 进入/etc/workspace文件夹，
    配置LIB库路径，export LD_LIBRARY_PATH=/etc/workspace/lib:$LD_LIBRARY_PATH
    修改可执行文件lenet1156的权限，chmod 777 ./lenet1156
    运行可执行文件lenet1156, ./lenet1156


## 目录结构
lenet5 Samples的目录结构如下所示：
lenet5
├── CMakeLists.txt
├── oh
│   ├── lenet5
│   │   ├── build.sh
│   │   ├── build_npu.sh
│   │   ├── CMakeLists.txt
│   │   ├── data
│   │   │   └── README.md
│   │   ├── model
│   │   │   └── README.md
│   │   ├── README.md
│   │   ├── scripts
│   │   │   └── preproc_mnist_data.py
│   │   └── src
│   │       └── ai_deploy_main_npu.c
│   │       └── ai_main.c
│   │       └── ai_main.h
│   │       └── CMakeLists.txt
│   └── ......
└── README.md
- **build.sh脚本**: 用于编译Sample模型。需要配置对应的SDK_PATH 以及 ADAPTOR_PATH。Hi3863 以及 Hi3322的SDK下载链接为(https://xxx)。
- **CMakeLists.txt**: Sample的编译框架，C代码实现。
- **model目录**: 用于存放对应的onnx原始模型。
- **scripts目录**: 用于存放对应的数据处理脚本，自动生成量化以及验证数据。
- **src文件夹**: 用于存放板端推理源文件源码。
- **README**: 此Sample的介绍。

## 常见问题
若出现GLIBC环境不符，或者python环境不符，依次配置gcc环境，python3.11环境，将libstdc++ / libpython的动态链接库添加到LD_LIBRARY_PATH中
```
# 1. 先链接mindspore-enterprise-lite-{version}-linux-x64/tools/converter/lib下的动态链接库
export LD_LIBRARY_PATH={PKG}/mindspore-enterprise-lite-{version}-linux-x64/tools/converter/lib:$LD_LIBRARY_PATH

# 2. 再链接 包含libpython3.11.so的同级目录，例如：
export LD_LIBRARY_PATH={Python3.11_ENV}/lib:$LD_LIBRARY_PATH

# 3. 配置gcc 6.0.30的动态链接库软链接
cd {gcc_lib}
ln -s libstdc++.so.6.0.30 libstdc++.so.6

# 3. 最后链接gcc的lib
export LD_LIBRARY_PATH={gcc_lib}:$LD_LIBRARY_PATH
```

## 引用和致谢
本项目部分模型与代码参考或修改自以下开源项目：https://github.com/onnx/models