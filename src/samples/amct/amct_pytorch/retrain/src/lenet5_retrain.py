#!/usr/bin/python3.11
# -*- coding: utf-8 -*-
# Copyright (c) 2025-2025 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
import os
import time
import argparse
import csv
from glob import glob

import logging
import numpy as np
import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
import torch.optim
import onnxruntime as ort
from torch.utils.data import DataLoader

import amct_pytorch as amct

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()])

SIZE = 28
OUTPUTS = "./output"
TMP = "./tmp"

parser = argparse.ArgumentParser(description='PyTorch Mnist Training')
parser.add_argument(
    '--model', dest='model', default=None, type=str, help='The path of pt/pth file.')
parser.add_argument(
    '--config_defination', dest='config_defination', default=None, type=str, help='The simple configure define file.')
parser.add_argument('--batch_num', dest='batch_num', default=2, type=int, help='number of total batch to run')
parser.add_argument(
    '--train_set', dest='train_set', default=None, type=str, help='The path of Mnist dataset for training.')
parser.add_argument(
    '--eval_set', dest='eval_set', default=None, type=str, help='The path of Mnist dataset for evaluation.')
parser.add_argument(
    '--num_parallel_reads', dest='num_parallel_reads', default=4, type=int,
    help='The number of files to read in parallel.')
parser.add_argument('--batch_size', dest='batch_size', default=25, type=int, help='batch size (default: 25)')
parser.add_argument('--learning_rate', dest='learning_rate', default=1e-5, type=float, help='initial learning rate')
parser.add_argument(
    '--train_iter', dest='train_iter', default=2000, type=int, help='number of total iterations to run')
parser.add_argument('--print_freq', dest='print_freq', default=10, type=int, help='print frequency (default: 10)')


class LeNet5(nn.Module):
    def __init__(self) -> None:
        super().__init__()

        self.conv1 = nn.Conv2d(1, 8, kernel_size=(5, 5), padding=2)
        self.relu1 = nn.ReLU()
        self.maxpool1 = nn.MaxPool2d(kernel_size=(2, 2), stride=(2, 2), padding=(0, 0), dilation=1, ceil_mode=False)

        self.conv2 = nn.Conv2d(8, 16, kernel_size=(5, 5), padding=2)
        self.relu2 = nn.ReLU()
        self.maxpool2 = nn.MaxPool2d(kernel_size=(3, 3), stride=(3, 3), padding=(0, 0), dilation=1, ceil_mode=False)

        self.fc = torch.nn.Linear(256, 10, bias=True)

    def forward(self, img):
        out = self.conv1(img)
        out = self.relu1(out)
        out = self.maxpool1(out)
        out = self.conv2(out)

        out = self.relu2(out)
        out = self.maxpool2(out)
        out = out.reshape(-1, 256)
        out = self.fc(out)
        return out


class Dataset(torch.utils.data.Dataset):
    """
    Dataset for loading image data from npy files and corresponding labels from CSV.
    """
    def __init__(self, input_dir, output_dir):
        """
        Initialize dataset by loading file paths and labels.

        Args:
            input_dir (str): Directory containing input data files
            output_dir (str): Path to CSV file containing labels
        """
        self.input_files = sorted(glob(os.path.join(input_dir, "*.npy")))
        self.labels = self._load_labels(output_dir)

    def __getitem__(self, index):
        """
        Get data and label by index.

        Args:
            index (int): Dataset index

        Returns:
            tuple: (input_tensor, label_tensor)
        """
        input_data = np.load(self.input_files[index]).reshape(1, SIZE, SIZE)
        input_tensor = torch.from_numpy(input_data)

        label_tensor = torch.tensor(self.labels[index], dtype=torch.int64)
        return input_tensor, label_tensor

    def __len__(self):
        """Return total number of samples in dataset."""
        return len(self.input_files)

    def _load_labels(self, label_dir):
        """Load labels from CSV file."""
        csv_files = glob(os.path.join(label_dir, "*.csv"))
        csv_files = [f for f in csv_files if os.path.isfile(f)]
        label_path = csv_files[0]
        labels = []
        with open(label_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                labels.append(int(row["label"]))
        return labels


def create_data_loader(train_input_dir, train_output_dir, val_input_dir, val_output_dir, args):
    """
    Create DataLoader instances for training and validation datasets.

    Args:
        train_input_dir (str): Path to training input data directory
        train_output_dir (str): Path to training labels CSV file
        val_input_dir (str): Path to validation input data directory
        val_output_dir (str): Path to validation labels CSV file

    Returns:
        tuple: (train_loader, val_loader)
    """
    batch_size = args.batch_size
    num_parallel_reads = args.num_parallel_reads

    # Create datasets
    train_dataset = Dataset(train_input_dir, train_output_dir)
    val_dataset = Dataset(val_input_dir, val_output_dir)

    train_loader = DataLoader(
        dataset=train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=num_parallel_reads, pin_memory=True, sampler=None)
    val_loader = DataLoader(
        dataset=val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_parallel_reads, pin_memory=True, sampler=None)
    return train_loader, val_loader


def args_check(args):
    """Verify the validity of input parameters"""
    if args.model is None:
        raise RuntimeError('Must specify a checkpoint path!')
    args.model = os.path.realpath(args.model)

    if args.train_set is None:
        raise RuntimeError('Must specify a training dataset path!')
    args.train_set = os.path.realpath(args.train_set)
    if not os.access(args.train_set, os.F_OK):
        raise RuntimeError('Must specify a valid training dataset path!')

    if args.eval_set is None:
        raise RuntimeError('Must specify a evaluation dataset path!')
    args.eval_set = os.path.realpath(args.eval_set)
    if not os.access(args.eval_set, os.F_OK):
        raise RuntimeError('Must specify a valid evaluation dataset path!')


def get_input_data(shape_list, model):
    """Get input data to generate onnx graph for amct_pytorch tools"""
    device = next(model.parameters()).device
    input_data = tuple([torch.randn(shape).to(device) for shape in shape_list])
    return input_data


def adjust_learning_rate(optimizer, epoch, learning_rate):
    """Set the learning rate to the initial LR decayed by 10 every 30 epochs"""
    learning_rate = learning_rate * (0.1 ** (epoch // 30))
    for param_group in optimizer.param_groups:
        param_group['lr'] = learning_rate


def accuracy(output, target):
    """Compute accuracy"""
    with torch.no_grad():
        batch_size = target.size(0)

        _, prediction = output.topk(1, 1, True, True)
        prediction = prediction.t()
        correct = prediction.eq(target.view(1, -1).expand_as(prediction))

        correct = correct.reshape(-1).float().sum(0, keepdim=True)
        return correct.mul_(100.0 / batch_size)


def train(train_loader, model, optimizer, iteration, gpu_index, print_freq):
    """Train the model"""
    # switch to train mode.
    model.train()

    criterion = nn.CrossEntropyLoss()
    if gpu_index >= 0:
        criterion = nn.CrossEntropyLoss().cuda(gpu_index)

    sample_cnt = 0
    acc_sum = 0.
    loss_sum = 0.

    for i, (images, target) in enumerate(train_loader):
        if gpu_index >= 0:
            images = images.cuda(gpu_index, non_blocking=True)
            target = target.cuda(gpu_index, non_blocking=True)

        # compute output.
        output = model(images)
        loss = criterion(output, target)

        # measure accuracy and record loss.
        acc = accuracy(output, target)

        sample_cnt += images.size(0)
        acc_sum += (float)(acc * images.size(0))
        loss_sum += (float)(loss.item() * images.size(0))

        # compute gradient and do SGD step.
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if (i + 1) % print_freq == 0:
            logger.info(
                "Train: [{}/{}]   Loss {:.6f}({:.6f})   Acc {:.6f}".format(
                i+1, iteration, loss.item(), loss_sum/sample_cnt, acc_sum/sample_cnt))
        if (i + 1) >= iteration:
            break


def validate(val_loader, model, iteration, gpu_index, print_freq):
    """Validate the model"""
    # switch to evaluate mode.
    model.eval()

    sample_cnt = 0
    acc_sum = 0.

    with torch.no_grad():
        for i, (images, target) in enumerate(val_loader):
            if gpu_index >= 0:
                images = images.cuda(gpu_index, non_blocking=True)
                target = target.cuda(gpu_index, non_blocking=True)

            # compute output.
            output = model(images)

            # measure accuracy and record loss.
            acc1 = accuracy(output, target)

            sample_cnt += images.size(0)
            acc_sum += (float)(acc1 * images.size(0))

            if (i + 1) % print_freq == 0:
                logger.info("Test: [{}/{}]   Acc {:.6f}".format(i+1, len(val_loader), acc_sum/sample_cnt))
            if (i + 1) >= iteration:
                break

    return acc_sum/sample_cnt


def validate_onnx(val_loader, model, print_freq):
    """Validate the onnx model"""
    # switch to evaluate mode.
    ort_session = ort.InferenceSession(model, providers=['CPUExecutionProvider'])

    sample_cnt = 0
    acc_sum = 0.

    with torch.no_grad():
        for i, (images, target) in enumerate(val_loader):
            # compute output.
            output = ort_session.run(None, {'input': images.numpy()})
            output = torch.from_numpy(output[0])

            # measure accuracy and record loss.
            acc1 = accuracy(output, target)

            sample_cnt += images.size(0)
            acc_sum += (float)(acc1 * images.size(0))

            if (i + 1) % print_freq == 0:
                logger.info("Test: [{}/{}]   Acc {:.6f}".format(i+1, len(val_loader), acc_sum/sample_cnt))

    return acc_sum/sample_cnt


def cal_original_model_accuracy(model, gpu_index, val_loader, args):
    """Infer the accuracy of the original model."""
    if gpu_index >= 0:
        torch.cuda.set_device(gpu_index)
        model = model.cuda(gpu_index)

    acc = validate(val_loader, model, len(val_loader), gpu_index, args.print_freq)
    return acc


def train_and_val(model, gpu_index, train_loader, val_loader, args):
    """train_and_val"""
    # Allocating a model to a specified device.
    if gpu_index >= 0:
        torch.cuda.set_device(gpu_index)
        model = model.cuda(gpu_index)

    # Define optimizer.
    optimizer = torch.optim.SGD(model.parameters(), args.learning_rate, momentum=0.9, weight_decay=1e-4)

    # Retrain the model.
    for epoch in range(0, 1):
        adjust_learning_rate(optimizer, epoch, args.learning_rate)

        # train for train_iter.
        logger.info("training quantized model")
        train(train_loader, model, optimizer, args.train_iter, gpu_index, args.print_freq)

        # evaluate on validation set.
        _ = validate(val_loader, model, args.batch_num, gpu_index, args.print_freq)


def cal_quant_model_accuracy(model, val_loader, args, config_file, record_file):
    """Save the quantized model and infer the accuracy of the quantized model."""
    torch.save({'state_dict': model.state_dict()}, os.path.join(TMP, 'model_best.pth.tar'))
    quantized_pb_path = os.path.join(OUTPUTS, 'lenet5')
    amct.save_quant_retrain_model(
        config_file, model, record_file, quantized_pb_path, get_input_data([(1, 1, SIZE, SIZE)], model),
        input_names=['input'], output_names=['output'],
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}})

    logger.info("validating fake quant model")
    quant_acc = validate_onnx(val_loader, ''.join([quantized_pb_path, '_fake_quant_model.onnx']), args.print_freq)
    return quant_acc


def main():
    """retrain"""
    args = parser.parse_args()
    args_check(args)

    if torch.cuda.is_available():
        gpu_index = 0
        logger.info('Using GPU.')
    else:
        gpu_index = -1
        logger.info('Using CPU, this will be slow')

    # Generate training dataset and validation dataset loader.
    train_loader, val_loader = create_data_loader(
        os.path.join(args.train_set, "npy"), args.train_set, os.path.join(args.eval_set, "npy"), args.eval_set, args)

    # Step 1: Create model.
    logger.info("Create pre-trained model 'LeNet5'")
    model = LeNet5()
    model.load_state_dict(torch.load(args.model))

    # Step 2: Calculate origin model's accuracy.
    ori_acc = cal_original_model_accuracy(model, gpu_index, val_loader, args)

    # Step 3: Create the retraining configuration file.
    logger.info('AMCT step1: create_quant_retrain_config..')
    config_file = os.path.join(TMP, 'config.json')
    record_file = os.path.join(TMP, 'record.txt')
    amct.create_quant_retrain_config(
        config_file, model, get_input_data([(1, 1, SIZE, SIZE)], model), args.config_defination)

    # Step 4: Generate the retraining model in default graph and create the quantization factor record_file.
    logger.info('AMCT step2: create_quant_retrain_model..')
    model = amct.create_quant_retrain_model(
        config_file, model, record_file, get_input_data([(1, 1, SIZE, SIZE)], model))

    # Step 5: Retraining quantitative model and inferencing.
    train_and_val(model, gpu_index, train_loader, val_loader, args)

    # Step 6: Save the quantized model and infer the accuracy of the quantized model.
    quant_acc = cal_quant_model_accuracy(model, val_loader, args, config_file, record_file)

    logger.info('[INFO] Accuracy before retrain: {:.3f}%'.format(ori_acc))
    logger.info('[INFO] Accuracy after retrain: {:.3f}%'.format(quant_acc))


if __name__ == '__main__':
    main()