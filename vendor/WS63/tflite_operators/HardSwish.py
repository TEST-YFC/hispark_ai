# Copyright (c) 2025-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import tensorflow as tf

logging.basicConfig(level=logging.NOTSET)


def create_hardswish_tflite_model(output_path):
    """Create TFLite model with HardSwish operator.

    Exports as TFLite builtin HARD_SWISH via pattern: x * relu6(x + 3) / 6.

    Args:
        output_path: Path to save the generated TFLite model
    """
    class HardSwishModel(tf.Module):
        def __init__(self):
            super(HardSwishModel, self).__init__()

        @tf.function(input_signature=[
            tf.TensorSpec(shape=[1, 3, 4, 4], dtype=tf.float32, name="input")
        ])
        def __call__(self, x):
            return x * tf.nn.relu6(x + 3.0) / 6.0

    model = HardSwishModel()

    converter = tf.lite.TFLiteConverter.from_concrete_functions(
        [model.__call__.get_concrete_function()],
        model
    )
    converter.experimental_new_converter = False

    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    logging.info(f"Successfully created HardSwish TFLite model at: {output_path}")
