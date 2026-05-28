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

logging.basicConfig(level=logging.NOTSET)


def create_cumsum_tflite_model(output_path):
    """Create CumSum TFLite model.

    Args:
        output_path: Model save path.
    """
    class CumSumModel(tf.Module):
        def __init__(self):
            super(CumSumModel, self).__init__()

        @tf.function(input_signature=[
            tf.TensorSpec(shape=[2, 3, 4], dtype=tf.float32, name="input")
        ])
        def __call__(self, x):
            return tf.math.cumsum(x, axis=2, name="output")

    model = CumSumModel()

    converter = tf.lite.TFLiteConverter.from_concrete_functions(
        [model.__call__.get_concrete_function()],
        model
    )

    converter.experimental_new_converter = True

    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    logging.info(f"CumSum TFLite model saved: {output_path}")
