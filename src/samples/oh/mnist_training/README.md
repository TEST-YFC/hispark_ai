# HiSpark.AI MNIST 训练 Sample

## 目录结构

```text
mnist_training
├── build.sh
├── CMakeLists.txt
├── data
│   └── README.md
├── model
│   └── micro_train.cfg
├── scripts
│   └── preproc_mnist_data.py
└── src
    ├── ai_main_training.c
    └── mnist_training_data.h
```

## 1. 准备模型和 MNIST 数据

运行前需要先下载模型文件，并保存为 `model/mnist_training_init.onnx`：

```bash
wget -O model/mnist_training_init.onnx \
  "https://api.gitcode.com/api/v5/repos/HiSpark/hispark_ai/raw/src/samples/oh/mnist_training/model/mnist_training_init.onnx?ref=master"
```
> `mnist_training_init.onnx` 是用于 MNIST 手写数字分类的 LeNet-style CNN 示例模型。该类网络结构来源于 Yann LeCun 团队提出的 LeNet 系列卷积神经网络思想，本 Sample 使用的模型并非严格复现原始 LeNet-5，而是面向端侧训练验证做了简化。

在 `samples/oh/mnist_training` 目录下执行：

```bash
python scripts/preproc_mnist_data.py \
  --orig_path ./data \
  --calib_path ./data/calib_data
```

该脚本会生成 converter 量化校准数据和 MCU sample 内置训练/评估数据：

```text
data/calib_data/bin/    # converter 量化校准使用的 BIN 数据
src/mnist_training_data.c
```

`model/micro_train.cfg` 默认使用：

```ini
calibrate_path=input:data/calib_data/bin
calibrate_size=500
```

因此 converter 也需要在 `samples/oh/mnist_training` 目录下执行，或者将该路径改成绝对路径。
`calibrate_size` 必须和 `data/calib_data/bin` 下的 bin 文件数量一致。


## 2. 生成 micro 工程

配置 MindSpore Lite 包路径：

```bash
export MSLITE_PKG=/path/to/mindspore-lite-2.8.0-linux-x64
export PATH=${MSLITE_PKG}/tools/converter/converter:${PATH}
export LD_LIBRARY_PATH=${MSLITE_PKG}/tools/converter/lib:${LD_LIBRARY_PATH}
```

执行 converter：

```bash
mkdir -p output
${MSLITE_PKG}/tools/converter/converter/converter_lite \
  --fmk=ONNX \
  --modelFile=./model/mnist_training_init.onnx \
  --outputFile=./output/micro_train \
  --configFile=./model/micro_train.cfg \
  --inputDataFormat=NCHW \
  --outputDataFormat=NCHW \
  --inputDataType=FLOAT \
  --outputDataType=FLOAT
```

## 3. 编译 micro 产物

配置 RISC-V 工具链路径：

```bash
export RISCV_TOOLCHAIN_PATH=/path/to/cc_riscv32_musl/bin
```

编译 converter 生成的 micro 工程：

```bash
cd output/micro_train
rm -rf build
cmake -S . -B build \
  -DOP_LIB="${MSLITE_PKG}/tools/codegen/lib/riscv/libnnacl.a" \
  -DWRAPPER_LIB="${MSLITE_PKG}/tools/codegen/lib/riscv/libwrapper.a" \
  -DRISCV_TOOLCHAIN_PATH="${RISCV_TOOLCHAIN_PATH}" \
  -DPKG_PATH="${MSLITE_PKG}"
cmake --build build -j4
cd -
```

编译完成后需要得到：

```text
output/micro_train/build/libmicro_runtime.a
output/micro_train/build/src/libnet.a
```

## 4. 拷贝 micro 库到 SDK

配置 SDK 路径：

```bash
export SDK_PATH=/path/to/ws63_sdk
mkdir -p ${SDK_PATH}/middleware/utils/ai_mcu/lib
cp -f output/micro_train/build/libmicro_runtime.a ${SDK_PATH}/middleware/utils/ai_mcu/lib/
cp -f output/micro_train/build/src/libnet.a ${SDK_PATH}/middleware/utils/ai_mcu/lib/
```

## 5. 编译 Sample 固件

配置 adaptor 路径：

```bash
export ADAPTOR_PATH=/path/to/hispark_ai_adaptor
```

在 `samples/oh/mnist_training` 目录下执行：

```bash
bash build.sh
```

成功后生成固件：

```text
output/ws63-ai-mnist-training-sample.fwpkg
```

## 6. 烧录运行

将生成的 `output/ws63-ai-mnist-training-sample.fwpkg` 烧录到 WS63 单板。

上板运行后，Sample 会依次执行：

```text
predict -> eval before -> train 1 epoch -> eval after
```

预期打印格式如下，数值仅以占位符表示，实际结果会随模型、量化参数和训练数据变化：

```text
[MNIST_TRAIN] Prediction
[MNIST_TRAIN]   pred: <digit>
[MNIST_TRAIN]   time: <time>ms
[MNIST_TRAIN]   logits: [<logit0>, <logit1>, ..., <logit9>]
[MNIST_TRAIN]
[MNIST_TRAIN] Evaluation (before training)
[MNIST_TRAIN]   avg loss: <loss>
[MNIST_TRAIN]   accuracy: <correct>/500
[MNIST_TRAIN]
[MNIST_TRAIN] Training (steps 1-100)
[MNIST_TRAIN] Evaluation (after 100 training steps)
[MNIST_TRAIN]   avg loss: <loss>
[MNIST_TRAIN]   accuracy: <correct>/500
[MNIST_TRAIN]
[MNIST_TRAIN] Training (steps 101-200)
[MNIST_TRAIN] Evaluation (after 200 training steps)
[MNIST_TRAIN]   avg loss: <loss>
[MNIST_TRAIN]   accuracy: <correct>/500
[MNIST_TRAIN]
[MNIST_TRAIN] ...
[MNIST_TRAIN]
[MNIST_TRAIN] Prediction
[MNIST_TRAIN]   pred: <digit>
[MNIST_TRAIN]   time: <time>ms
[MNIST_TRAIN]   logits: [<logit0>, <logit1>, ..., <logit9>]
```
