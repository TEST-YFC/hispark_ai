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
from collections import namedtuple
import tensorflow as tf
import numpy as np

logging.basicConfig(level=logging.NOTSET)

ReductionResult = namedtuple('ReductionResult',
                             ['red_max', 'red_min', 'red_mean', 'red_sum', 'cast_argmax', 'cast_argmin'])


class _mathoperatorsmodel(tf.Module):
    def __init__(self):
        super(_mathoperatorsmodel, self).__init__()
        self.prelu_alpha = tf.Variable(
            tf.constant([[0.25, 0.25], [0.25, 0.25]], dtype=tf.float32),
            trainable=False, name="prelu_alpha"
        )
        self.einsum_weight = tf.Variable(
            tf.constant([[1.0, 0.5], [0.5, 1.0]], dtype=tf.float32),
            trainable=False, name="einsum_weight"
        )
    
    @tf.function(input_signature=[
        tf.TensorSpec(shape=[1, 2, 2], dtype=tf.float32, name="input")
    ])
    def __call__(self, x):
        x, x_new = self._run_unary_math_ops(x)
        original_out = self._run_gather_concat_pad_resize(x)
        x_1d, cumsum_2d = self._run_extended_activations(x_new)
        reduction_result = self._run_reductions_and_args(x_1d)
        red_max = reduction_result.red_max
        red_min = reduction_result.red_min
        red_mean = reduction_result.red_mean
        red_sum = reduction_result.red_sum
        cast_argmax = reduction_result.cast_argmax
        cast_argmin = reduction_result.cast_argmin
        sliced = self._run_comparisons_and_logical(x_1d)
        einsum_s = self._run_einsum(cumsum_2d)
        merged = tf.concat([
            original_out, red_max, red_min, red_mean, red_sum,
            cast_argmax, cast_argmin,
            sliced[0], sliced[1], sliced[2], sliced[3],
            sliced[4], sliced[5], sliced[6], sliced[7], sliced[8],
            einsum_s,
        ], axis=1, name="merged_output")
        return merged

    def _run_unary_math_ops(self, x):
        x = tf.abs(x, name="abs")
        x = tf.math.ceil(x, name="ceil")
        x = tf.math.cos(x, name="cos")
        x = tf.math.exp(x, name="exp")
        x = tf.math.floor(x, name="floor")
        x = tf.math.log(tf.abs(x) + 1.0, name="log")
        x = tf.math.round(x, name="round")
        x = tf.math.rsqrt(tf.abs(x) + 1.0, name="rsqrt")
        x = tf.math.sin(x, name="sin")
        x = tf.sqrt(tf.abs(x) + 1.0, name="sqrt")
        x = tf.square(x, name="square")
        x_new = tf.identity(x, name="branch_point")
        return x, x_new

    def _run_gather_concat_pad_resize(self, x):
        indices = tf.constant([0], dtype=tf.int32)
        gathered = tf.gather(x, indices, axis=1, name="gather")
        other_tensor = x[:, :1, :1]
        gathered_part = gathered[:, :, :1]
        x = tf.concat([other_tensor, gathered_part], axis=2, name="concat")
        x = tf.tile(x, [1, 1, 1], name="tile")
        paddings = tf.constant([[0, 0], [0, 0], [0, 0]])
        x = tf.pad(x, paddings, mode='CONSTANT', name="pad")
        x = tf.pad(x, paddings, mode='CONSTANT', constant_values=0.5,
                   name="pad_v2")
        x = tf.pad(x, paddings, mode='REFLECT', name="mirror_pad")
        if len(x.shape) == 3:
            x_4d = tf.expand_dims(x, axis=0)
            x_resized = tf.image.resize(
                x_4d, [1, 1],
                method=tf.image.ResizeMethod.BILINEAR,
                name="resize_bilinear")
            x = tf.squeeze(x_resized, axis=0)
        if len(x.shape) == 3:
            x_4d = tf.expand_dims(x, axis=0)
            x_resized = tf.image.resize(
                x_4d, [1, 1],
                method=tf.image.ResizeMethod.NEAREST_NEIGHBOR,
                name="resize_nearest")
            x = tf.squeeze(x_resized, axis=0)
        x_flat = tf.reshape(x, [-1], name="original_path_flat")
        original_out = tf.reshape(
            tf.slice(x_flat, [0], [1]), [1, 1], name="original_flat")
        return original_out

    def _run_extended_activations(self, x_new):
        x_new = tf.nn.elu(x_new, name="elu")
        x_new = tf.nn.relu6(x_new, name="relu6")
        x_new = tf.nn.leaky_relu(x_new, alpha=0.01, name="leaky_relu")
        x_new = x_new * tf.nn.relu6(x_new + 3.0) / 6.0
        x_new = tf.identity(x_new, name="hard_swish")
        x_new = (tf.maximum(0.0, x_new) +
                 self.prelu_alpha * tf.minimum(0.0, x_new))
        x_new = tf.identity(x_new, name="prelu")
        x_new = tf.quantization.fake_quant_with_min_max_args(
            x_new, min=-20.0, max=20.0, num_bits=8, narrow_range=False,
            name="fake_quant"
        )
        div_const = tf.constant([[[0.5, 1.0], [2.0, 0.5]]],
                                dtype=tf.float32)
        x_new = tf.math.divide(x_new, div_const + 0.1, name="div")
        x_new = tf.math.l2_normalize(x_new, axis=-1, name="l2_norm")
        x_new = tf.transpose(x_new, perm=[0, 2, 1], name="transpose")
        x_new = tf.math.cumsum(x_new, axis=-1, name="cumsum")
        cumsum_2d = tf.reshape(x_new, [2, 2], name="cumsum_2d")
        x_1d = tf.reshape(x_new, [1, 4], name="new_1d")
        return x_1d, cumsum_2d

    def _run_reductions_and_args(self, x_1d):
        red_max = tf.math.reduce_max(x_1d, axis=1, keepdims=True,
                                     name="reduce_max")
        red_min = tf.math.reduce_min(x_1d, axis=1, keepdims=True,
                                     name="reduce_min")
        red_mean = tf.math.reduce_mean(x_1d, axis=1, keepdims=True,
                                       name="reduce_mean")
        red_sum = tf.math.reduce_sum(x_1d, axis=1, keepdims=True,
                                     name="reduce_sum")
        argmax_i = tf.math.argmax(x_1d, axis=1, name="argmax")
        argmin_i = tf.math.argmin(x_1d, axis=1, name="argmin")
        cast_argmax = tf.cast(tf.expand_dims(argmax_i, 0), tf.float32,
                              name="cast_argmax")
        cast_argmin = tf.cast(tf.expand_dims(argmin_i, 0), tf.float32,
                              name="cast_argmin")
        return ReductionResult(red_max, red_min, red_mean, red_sum, cast_argmax, cast_argmin)

    def _run_comparisons_and_logical(self, x_1d):
        ref = tf.constant([[0.0, 0.5, 1.0, 1.5]], dtype=tf.float32,
                          name="cmp_ref")
        equal_b = tf.math.equal(x_1d, ref, name="equal")
        greater_b = tf.math.greater(x_1d, ref, name="greater")
        ge_b = tf.math.greater_equal(x_1d, ref, name="greater_or_equal")
        less_b = tf.math.less(x_1d, ref, name="less")
        not_equal_b = tf.math.not_equal(x_1d, ref, name="not_equal")
        le_b = tf.math.less_equal(x_1d, ref, name="less_or_equal")
        not_b = tf.math.logical_not(equal_b, name="logical_not")
        and_b = tf.math.logical_and(greater_b, ge_b, name="logical_and")
        or_b = tf.math.logical_or(greater_b, less_b, name="logical_or")
        bool_tensors = [
            equal_b, greater_b, ge_b, less_b,
            not_b, and_b, or_b, not_equal_b, le_b
        ]
        sliced_results = []
        for i, bt in enumerate(bool_tensors):
            f_val = tf.cast(bt, tf.float32, name="cast_cmp_{}".format(i))
            s_val = tf.slice(f_val, [0, 0], [1, 1],
                             name="slice_cmp_{}".format(i))
            sliced_results.append(s_val)
        return tuple(sliced_results)

    def _run_einsum(self, cumsum_2d):
        einsum_out = tf.einsum('ij,jk->ik', cumsum_2d,
                               self.einsum_weight, name="einsum")
        einsum_f = tf.reshape(einsum_out, [1, 4], name="einsum_flat")
        einsum_s = tf.slice(einsum_f, [0, 0], [1, 2], name="einsum_slice")
        return einsum_s


def create_mathmodel_tflite_model(output_path):
    model = _mathoperatorsmodel()
    concrete_func = model.__call__.get_concrete_function()
    converter = tf.lite.TFLiteConverter.from_concrete_functions(
        [concrete_func])
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,
        tf.lite.OpsSet.SELECT_TF_OPS
    ]
    converter.allow_custom_ops = True
    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    logging.info(f"math operators tflite model saved: {output_path}")
