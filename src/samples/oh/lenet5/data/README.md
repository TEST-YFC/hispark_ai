# Introduction of Mnist Dataset

## 数据介绍
此数据集来源于NIST（美国国家标准与技术研究院），包含大量手写数字灰度图像，是计算机视觉领域的经典基准数据集。数据集包含0-9共10个类别的手写数字图像。

## 数据来源 && License
原始数据下载链接：
- [train-images-idx3-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/train-images-idx3-ubyte.gz)：训练集图像 
- [train-labels-idx1-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/train-labels-idx1-ubyte.gz)：训练集标签
- [t10k-images-idx3-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/t10k-images-idx3-ubyte.gz)：测试集图像
- [t10k-labels-idx1-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/t10k-labels-idx1-ubyte.gz)：测试集标签

## 数据划分方法
数据集已预先划分为60,000张训练图像和10,000张测试图像。

## 预处理流程
预处理包含图像张量化、数据类型转换、归一化等步骤。