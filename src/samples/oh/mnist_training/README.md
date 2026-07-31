# HiSpark.AI MNIST 训练 Sample

## 目录结构

```text
mnist_training
├── build.sh
├── CMakeLists.txt
├── data
│   └── README.md
├── model
│   ├── micro_train.cfg
│   └── model.onnx
├── scripts
│   └── preproc_mnist_data.py
└── src
    └── ai_main_training.c
```

## 1. 生成 MNIST 数据

在 `samples/oh/mnist_training` 目录下执行：

```bash
python scripts/preproc_mnist_data.py \
  --orig_path ./data \
  --train_path ./data/train_data \
  --test_path ./data/test_data \
  --train_file_format bin \
  --test_file_format all \
  --test_data_type float32 \
  --train_count 50
```

生成的数据目录如下：

```text
data/train_data/bin/    # converter 量化校准数据
data/test_data/bin/     # 测试集 BIN 数据
data/test_data/npy/     # 测试集 NPY 数据
data/test_data/label.csv
```

`model/micro_train.cfg` 默认使用：

```ini
calibrate_path=input:data/train_data/bin
calibrate_size=50
```

因此 converter 也需要在 `samples/oh/mnist_training` 目录下执行，或者将该路径改成绝对路径。
`calibrate_size` 必须和 `data/train_data/bin` 下的 bin 文件数量一致。

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
  --modelFile=./model/model.onnx \
  --outputFile=./output/micro_train \
  --configFile=./model/micro_train.cfg \
  --encryption=false \
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
predict -> train -> eval
```
