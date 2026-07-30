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


class _neuralnetworkmodel(tf.Module):
    def __init__(self):
        super(_neuralnetworkmodel, self).__init__()
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
        x, orig_input = self._run_conv_pool(x)
        x = self._run_dense_activations(x)
        x, main_out = self._run_batch_matmul_arith(x)
        sliced, sts_flat, rs_flat = self._run_extra_ops(x, orig_input)
        merged = tf.concat([
            main_out, sliced, sts_flat, rs_flat,
        ], axis=1, name="output")
        return merged

    def _run_conv_pool(self, x):
        orig_input = tf.identity(x, name="orig_input")
        x = tf.nn.conv2d(x, self.conv_weights, strides=[1, 1, 1, 1],
                         padding='SAME', name="conv2d")
        x = tf.nn.relu(x, name="relu")
        x = tf.nn.max_pool2d(x, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1],
                             padding='SAME', name="maxpool2d")
        x = tf.nn.avg_pool2d(x, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1],
                             padding='SAME', name="avgpool2d")
        return x, orig_input

    def _run_dense_activations(self, x):
        batch_size = tf.shape(x)[0]
        height = tf.shape(x)[1]
        width = tf.shape(x)[2]
        channels = tf.shape(x)[3]
        total_size = height * width * channels
        x = tf.reshape(x, [batch_size, total_size], name="reshape1")
        x = tf.matmul(x, self.fc_weights, name="fully_connected")
        x = tf.tanh(x, name="tanh")
        x = tf.sigmoid(x, name="sigmoid")
        x = tf.nn.softmax(x, name="softmax")
        return x

    def _run_batch_matmul_arith(self, x):
        x_reshaped = tf.reshape(x, [1, 1, 10],
                                name="reshape_for_batch_matmul")
        weights_expanded = tf.expand_dims(self.batch_matmul_weights, 0)
        x = tf.matmul(x_reshaped, weights_expanded, name="batch_matmul")
        bias = tf.constant([[0.1, 0.1, 0.1, 0.1]], dtype=tf.float32)
        bias_reshaped = tf.reshape(bias, [1, 1, 4])
        x = tf.add(x, bias_reshaped, name="add")
        sub_const = tf.constant([[0.05, 0.05, 0.05, 0.05]], dtype=tf.float32)
        sub_const_reshaped = tf.reshape(sub_const, [1, 1, 4])
        x = tf.subtract(x, sub_const_reshaped, name="sub")
        mul_const = tf.constant([[2.0, 2.0, 2.0, 2.0]], dtype=tf.float32)
        mul_const_reshaped = tf.reshape(mul_const, [1, 1, 4])
        x = tf.multiply(x, mul_const_reshaped, name="mul")
        x = tf.reshape(x, [1, 4], name="reshape2")
        x = tf.expand_dims(x, axis=0, name="expand_dims")
        x = tf.squeeze(x, axis=0, name="squeeze")
        main_out = tf.reshape(x, [1, 4], name="main_out")
        return x, main_out

    def _run_extra_ops(self, x, orig_input):
        sliced = tf.slice(x, [0, 0], [1, 2], name="slice_op")
        dts_in = tf.reshape(x, [1, 1, 1, 4], name="dts_input")
        dts_out = tf.nn.depth_to_space(dts_in, block_size=2,
                                       name="depth_to_space")
        sts_out = tf.nn.space_to_depth(dts_out, block_size=2,
                                       name="space_to_depth")
        sts_flat = tf.reshape(sts_out, [1, 4], name="sts_flat")
        rs_in = tf.reshape(orig_input, [1, 28, 28], name="rs_input")
        rs_out = tf.reverse_sequence(
            rs_in,
            seq_lengths=tf.constant([14], dtype=tf.int32),
            seq_axis=1, batch_axis=0,
            name="reverse_sequence"
        )
        rs_sliced = tf.slice(rs_out, [0, 0, 0], [1, 1, 4],
                             name="rs_sliced")
        rs_flat = tf.reshape(rs_sliced, [1, 4], name="rs_flat")
        return sliced, sts_flat, rs_flat


def create_neuralnetwork_tflite_model(output_path):
    model = _neuralnetworkmodel()
    concrete_func = model.__call__.get_concrete_function()
    converter = tf.lite.TFLiteConverter.from_concrete_functions(
        [concrete_func], model)
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
    logging.info(f"neural network tflite model saved: {output_path}")
