#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) 2026-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
"""Data Preprocessing Script

This script downloads the MNIST dataset and processes it into the data format required by the HiSpark.AI Studio
"""
import argparse
import os
from pathlib import Path
import shutil
import logging
import struct

import numpy as np
from torchvision.datasets import MNIST

CALIB_COUNT = 500
TRAIN_PER_CLASS = 50
EVAL_COUNT = 500
SHUFFLE_SEED = 3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def recreate_dir(path: str) -> None:
    """Recreate an output directory to avoid stale calibration files."""
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    logger.info("INFO: recreate dir {}".format(path))


def export_calibration_bins(orig_path: str, calib_path: str) -> None:
    """Export MNIST test images as float32 BIN files for converter calibration.

    Args:
        orig_path: Path to save the original data
        calib_path: Path to save calibration BIN files
    """
    dataset = MNIST(root=orig_path, train=False, download=True)

    bin_path = os.path.join(calib_path, "bin")
    recreate_dir(bin_path)

    for idx, (image, label) in enumerate(dataset):
        if idx >= CALIB_COUNT:
            break
        tensor = np.array(image).astype(np.float32) / 255
        tensor = np.expand_dims(np.expand_dims(tensor, axis=0), axis=0)

        sample_name = "sample_{:0>5d}_{}".format(idx, label)
        tensor.tofile(os.path.join(bin_path, "{}.bin".format(sample_name)))


def read_images(path: Path) -> np.ndarray:
    """Read MNIST IDX image data as uint8 flattened images."""
    with path.open("rb") as handle:
        magic, count, rows, cols = struct.unpack(">IIII", handle.read(16))
        if magic != 2051:
            raise ValueError(f"Unexpected image magic in {path}: {magic}")
        return np.frombuffer(handle.read(), dtype=np.uint8).reshape(count, rows * cols)


def read_labels(path: Path) -> np.ndarray:
    """Read MNIST IDX labels as int32 labels."""
    with path.open("rb") as handle:
        magic, _ = struct.unpack(">II", handle.read(8))
        if magic != 2049:
            raise ValueError(f"Unexpected label magic in {path}: {magic}")
        return np.frombuffer(handle.read(), dtype=np.uint8).astype(np.int32)


def balanced_indices(labels: np.ndarray) -> np.ndarray:
    """Pick the fixed balanced training subset used by the MCU sample."""
    indices = []
    for class_id in range(10):
        class_indices = np.flatnonzero(labels == class_id)
        if len(class_indices) < TRAIN_PER_CLASS:
            raise ValueError(f"class {class_id} has only {len(class_indices)} samples")
        indices.extend(class_indices[:TRAIN_PER_CLASS].tolist())
    return np.array(indices, dtype=np.int64)


def write_u8_array(handle, name: str, values: np.ndarray, count_macro: str) -> None:
    """Write uint8 image data as a C two-dimensional array."""
    handle.write(f"const uint8_t {name}[{count_macro}][AI_MCU_SAMPLE_INPUT_1_SIZE] = {{\n")
    for sample in values:
        handle.write("    {\n")
        for start in range(0, sample.size, 28):
            row = ", ".join(str(int(value)) for value in sample[start:start + 28])
            handle.write(f"        {row},\n")
        handle.write("    },\n")
    handle.write("};\n")


def write_i32_array(handle, name: str, values: np.ndarray, count_macro: str) -> None:
    """Write int32 labels as a C array."""
    handle.write(f"const int32_t {name}[{count_macro}] = {{\n")
    for start in range(0, len(values), 20):
        row = ", ".join(str(int(value)) for value in values[start:start + 20])
        handle.write(f"    {row},\n")
    handle.write("};\n")


def export_training_data_c(orig_path: str, output: Path) -> None:
    """Generate the MCU sample's built-in uint8 train/eval dataset."""
    raw_path = Path(orig_path) / "MNIST" / "raw"
    train_images = read_images(raw_path / "train-images-idx3-ubyte")
    train_labels = read_labels(raw_path / "train-labels-idx1-ubyte")
    eval_images = read_images(raw_path / "t10k-images-idx3-ubyte")[:EVAL_COUNT]
    eval_labels = read_labels(raw_path / "t10k-labels-idx1-ubyte")[:EVAL_COUNT]

    train_indices = balanced_indices(train_labels)
    rng = np.random.default_rng(SHUFFLE_SEED)
    rng.shuffle(train_indices)
    train_images = train_images[train_indices]
    train_labels = train_labels[train_indices]

    with output.open("w") as handle:
        handle.write("/**\n")
        handle.write(" * Copyright (c) 2026-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.\n")
        handle.write(" * Licensed under the Apache License, Version 2.0 (the \"License\").\n")
        handle.write(" */\n")
        handle.write("#include \"mnist_training_data.h\"\n\n")
        handle.write("/* Generated from MNIST raw data. Training data is balanced across all digits. */\n")
        write_u8_array(handle, "g_mnist_train_inputs", train_images, "AI_MCU_SAMPLE_TRAIN_DATASET_SIZE")
        handle.write("\n")
        write_i32_array(handle, "g_mnist_train_labels", train_labels, "AI_MCU_SAMPLE_TRAIN_DATASET_SIZE")
        handle.write("\n")
        write_u8_array(handle, "g_mnist_eval_inputs", eval_images, "AI_MCU_SAMPLE_EVAL_DATASET_SIZE")
        handle.write("\n")
        write_i32_array(handle, "g_mnist_eval_labels", eval_labels, "AI_MCU_SAMPLE_EVAL_DATASET_SIZE")

    logger.info("INFO: generated {}".format(output))
    logger.info("INFO: train samples: {}, label counts: {}".format(
        len(train_labels), np.bincount(train_labels, minlength=10).tolist()))
    logger.info("INFO: eval samples: {}".format(len(eval_labels)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='download and preprocess MNIST dataset')
    parser.add_argument('--orig_path', help='Path to save the original data', required=True)
    parser.add_argument('--calib_path', help='Path to save the calibration set', required=True)
    parser.add_argument('--output',
        help='Path to save mnist_training_data.c',
        default=str(Path(__file__).resolve().parent.parent / "src" / "mnist_training_data.c"),
        required=False)
    args = parser.parse_args()

    export_calibration_bins(args.orig_path, args.calib_path)
    logger.info("INFO: Calibration BIN data exported.")
    export_training_data_c(args.orig_path, Path(args.output))
