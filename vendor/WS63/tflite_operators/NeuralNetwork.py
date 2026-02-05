# Copyright (c) 2025-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
import logging
import tensorflow as tf
import numpy as np

logging.basicConfig(level=logging.NOTSET)

def create_neuralnetwork_tflite_model(output_path):
    '''输入 → Conv2D → Relu → MaxPool2D → AveragePool2D → Reshape1 → FullyConnected
    → Tanh → Sigmoid → Softmax → Batch_Matmul → Add → Sub → Mul → Reshape2 → Split
    → ExpandDims → Squeeze → 输出'''
    class NeuralNetworkModel(tf.Module):
        def __init__(self):
            super(NeuralNetworkModel, self).__init__()
            # 定义可训练的权重
            self.conv_weights = tf.Variable(
                tf.random.normal([3, 3, 1, 16], dtype=tf.float32),
                trainable=False
            )
            self.fc_weights = tf.Variable(
                tf.random.normal([784, 10], dtype=tf.float32),
                trainable=False
            )
            self.batch_matmul_weights = tf.Variable(
                tf.random.normal([10, 4], dtype=tf.float32),
                trainable=False
            )
        
        @tf.function(input_signature=[
            tf.TensorSpec(shape=[1, 28, 28, 1], dtype=tf.float32, name="input")
        ])
        def __call__(self, x):
            # 1. Conv2D
            x = tf.nn.conv2d(x, self.conv_weights, strides=[1, 1, 1, 1], padding='SAME', name="conv2d")
            # 2. Relu
            x = tf.nn.relu(x, name="relu")
            # 3. MaxPool2D
            x = tf.nn.max_pool2d(x, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME', name="maxpool2d")
            # 4. AveragePool2D
            x = tf.nn.avg_pool2d(x, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME', name="avgpool2d")
            # 5. Reshape
            x = tf.reshape(x, [1, -1], name="reshape1")
            # 6. FullyConnected (Dense)
            x = tf.matmul(x, self.fc_weights, name="fully_connected")
            # 7. Tanh
            x = tf.tanh(x, name="tanh")
            # 8. Logistic (Sigmoid)
            x = tf.sigmoid(x, name="sigmoid")
            # 9. Softmax
            x = tf.nn.softmax(x, name="softmax")
            # 10. Batch Matmul
            mat_a = tf.reshape(x, [1, 1, 10])
            mat_b = tf.expand_dims(self.batch_matmul_weights, 0)
            x = tf.matmul(mat_a, mat_b, name="batch_matmul")  # 形状: [1, 1, 4]
            # 11. Add
            bias = tf.constant([0.1], dtype=tf.float32)
            x = tf.add(x, bias, name="add")
            # 12. Sub
            x = tf.subtract(x, tf.constant([0.05], dtype=tf.float32), name="sub")
            # 13. Mul
            x = tf.multiply(x, tf.constant([2.0], dtype=tf.float32), name="mul")
            # 14. Reshape
            x = tf.reshape(x, [2, 2], name="reshape2")
            # 15. Split
            split_result = tf.split(x, num_or_size_splits=2, axis=0, name="split")
            x = split_result[0]
            # 16. ExpandDims
            x = tf.expand_dims(x, axis=0, name="expand_dims")
            # 17. Squeeze
            x = tf.squeeze(x, axis=0, name="squeeze")
            return x
        
    # 创建和转换模型
    model = NeuralNetworkModel()
    converter = tf.lite.TFLiteConverter.from_concrete_functions(
        [model.__call__.get_concrete_function()],
        model
    )
    
    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    logging.info(f"✓ 神经网络算子模型已保存: {output_path}")