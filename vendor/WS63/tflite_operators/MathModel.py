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


def create_mathmodel_tflite_model(output_path):
    """输入 → Abs → Ceil → Cos → Exp → Floor → Log → Round → Rsqrt → Sin
    → Sqrt → Square → [Gather] → [Split] → [SplitV] → Concatenation → Tile
    → Pad → PadV2 → Mirror_Pad → Resize_Bilinear → Resize_Nearest_Neighbor → 输出"""
    class MathOperatorsModel(tf.Module):
        def __init__(self):
            super(MathOperatorsModel, self).__init__()
        
        @tf.function(input_signature=[
            tf.TensorSpec(shape=[4, 6, 8], dtype=tf.float32, name="input")
        ])
        def __call__(self, x):
            # 1. Abs
            x = tf.abs(x, name="abs")
            # 2. Ceil
            x = tf.math.ceil(x, name="ceil")
            # 3. Cos
            x = tf.math.cos(x, name="cos")
            # 4. Exp
            x = tf.math.exp(x, name="exp")
            # 5. Floor
            x = tf.math.floor(x, name="floor")
            # 6. Log
            x = tf.math.log(tf.abs(x) + 1.0, name="log")
            # 7. Round
            x = tf.math.round(x, name="round")
            # 8. Rsqrt
            x = tf.math.rsqrt(tf.abs(x) + 1.0, name="rsqrt")
            # 9. Sin
            x = tf.math.sin(x, name="sin")
            # 10. Sqrt
            x = tf.sqrt(tf.abs(x) + 1.0, name="sqrt")
            # 11. Square
            x = tf.square(x, name="square")
            # 12. Gather
            indices = tf.constant([0, 2, 4], dtype=tf.int32)
            gathered = tf.gather(x, indices, axis=1, name="gather")
            # 13. Split
            split_result = tf.split(x, num_or_size_splits=2, axis=1, name="split")
            # 14. SplitV
            split_v_result = tf.split(x, [3, 5], axis=2, name="splitv")
            # 15. Concatenation
            concat_input1 = split_result[0]
            concat_input2 = split_v_result[0][:, :, :3]
            concat_input2_reshaped = concat_input2[:, :3, :]
            x = tf.concat([concat_input1[:, :, :3], concat_input2_reshaped], axis=2, name="concat")
            # 16. Tile
            x = tf.tile(x, [1, 2, 2], name="tile")
            # 17. Pad
            paddings = tf.constant([[1, 1], [2, 2], [0, 0]])
            x = tf.pad(x, paddings, mode='CONSTANT', name="pad")
            # 18. PadV2
            x = tf.pad(x, paddings, mode='CONSTANT', constant_values=0.5, name="pad_v2")
            # 19. Mirror Pad
            x = tf.pad(x, paddings, mode='REFLECT', name="mirror_pad")
            # 20. Resize Bilinear
            if len(x.shape) == 3:
                x_4d = tf.expand_dims(x, axis=0)
                x_resized = tf.image.resize(x_4d, [8, 12], method=tf.image.ResizeMethod.BILINEAR, name="resize_bilinear")
                x = tf.squeeze(x_resized, axis=0)
            # 21. Resize Nearest Neighbor
            if len(x.shape) == 3:
                x_4d = tf.expand_dims(x, axis=0)
                x_resized = tf.image.resize(x_4d, [8, 12], method=tf.image.ResizeMethod.NEAREST_NEIGHBOR, name="resize_nearest")
                x = tf.squeeze(x_resized, axis=0)
            
            return x
    
    # 创建和转换模型
    model = MathOperatorsModel()
    concrete_func = model.__call__.get_concrete_function()
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_func])
    
    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    logging.info(f"✓ 数学运算算子模型已保存: {output_path}")