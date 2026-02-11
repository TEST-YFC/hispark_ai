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
    → Tanh → Sigmoid → Softmax → Batch_Matmul → Add → Sub → Mul → Reshape2 → 
    ExpandDims → Squeeze → 输出'''
    class NeuralNetworkModel(tf.Module):
        def __init__(self):
            super(NeuralNetworkModel, self).__init__()
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
            batch_size = tf.shape(x)[0]
            height = tf.shape(x)[1]
            width = tf.shape(x)[2]
            channels = tf.shape(x)[3]
            total_size = height * width * channels
            x = tf.reshape(x, [batch_size, total_size], name="reshape1")
            # 6. FullyConnected (Dense)
            x = tf.matmul(x, self.fc_weights, name="fully_connected")
            # 7. Tanh
            x = tf.tanh(x, name="tanh")
            # 8. Logistic (Sigmoid)
            x = tf.sigmoid(x, name="sigmoid")
            # 9. Softmax
            x = tf.nn.softmax(x, name="softmax")
            # 10. Batch Matmul
            x_reshaped = tf.reshape(x, [1, 1, 10], name="reshape_for_batch_matmul")
            weights_expanded = tf.expand_dims(self.batch_matmul_weights, 0)
            x = tf.matmul(x_reshaped, weights_expanded, name="batch_matmul")
            # 11. Add
            bias = tf.constant([[0.1, 0.1, 0.1, 0.1]], dtype=tf.float32)
            bias_reshaped = tf.reshape(bias, [1, 1, 4])
            x = tf.add(x, bias_reshaped, name="add")
            # 12. Sub
            sub_const = tf.constant([[0.05, 0.05, 0.05, 0.05]], dtype=tf.float32)
            sub_const_reshaped = tf.reshape(sub_const, [1, 1, 4])
            x = tf.subtract(x, sub_const_reshaped, name="sub")
            # 13. Mul
            mul_const = tf.constant([[2.0, 2.0, 2.0, 2.0]], dtype=tf.float32)
            mul_const_reshaped = tf.reshape(mul_const, [1, 1, 4])
            x = tf.multiply(x, mul_const_reshaped, name="mul")
            # 14. Reshape
            x = tf.reshape(x, [1, 4], name="reshape2")
            # 15. ExpandDims
            x = tf.expand_dims(x, axis=0, name="expand_dims")
            # 16. Squeeze
            x = tf.squeeze(x, axis=0, name="squeeze")
            x = tf.identity(x, name="output")
            return x
        

    model = NeuralNetworkModel()
    concrete_func = model.__call__.get_concrete_function()
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_func], model)
    converter.optimizations = []
    converter.target_spec.supported_types = [tf.float32]
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,
        tf.lite.OpsSet.SELECT_TF_OPS
    ]
    converter.allow_custom_ops = True
    
    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    logging.info(f"✓ 神经网络算子模型已保存: {output_path}")