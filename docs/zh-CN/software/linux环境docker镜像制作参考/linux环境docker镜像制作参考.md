# linux环境docker镜像制作参考

## 背景

HiSpark.AI 面向 Hi3863 / Hi3322 端侧 AI，模型需经 AMCT 量化、ATC / MSLite 转换后才能部署到芯片。由于该工具链依赖较重、版本严格锁定，手动安装易冲突且环境难一致，故将其打包为 Docker 镜像，作为 HiSpark Studio AI 插件在 Linux 服务器端的量化与转换后端。

本文档汇总 HiSpark.AI 各 AI 环境在 Linux 服务器端使用 Dockerfile 制作 Docker 镜像的方法，包含以下三种环境：

- MSLite 环境（Hi3863）：使用 `Dockerfile_mslite`。
- CANN 基础版环境（Hi3322）：使用 `Dockerfile_cann_cpu`。
- CANN GPU 加速版环境（Hi3322）：使用 `Dockerfile_cann_gpu`。

## 资源获取

各环境所需的安装包，从 HiSilicon 社区的「资源下载」部分下载 [HiSpark.AI 组件](https://developers.hisilicon.com/cn/developerTool)（下载前请先注册登录 HiSilicon 社区账号）。下载压缩包解压后，内部 customer 文件夹下包含：

- MSLite（Hi3863 AI 工具链）：内含 MSLite 环境所需的安装包（`HiSpark.AI_xx.xx.xx-mindspore-enterprise-lite-xx.xx.xx-linux-x64.tar.gz`）。
- CANN（Hi3322 AI 工具链）：内含 CANN 环境所需的安装包（`CANN-runtime`、`CANN-compiler`、`CANN-opp`、`CANN-toolkit`、`CANN-amct` 等）。

各环境的 Dockerfile 内容见下文对应章节。

## MSLite 环境（Hi3863）

使用 Dockerfile 准备 Linux 服务器端 AI 环境。环境安装前，需要从发布包获取 Dockerfile 文件、MSLite 安装包，并放置于同级目录下。

Dockerfile 包括 `Dockerfile_mslite`，为基础版环境准备配置文件。

环境安装前，请先检查目录下是否包含如下文件：

```
.
├── Dockerfile_mslite
└── HiSpark.AI_xx.xx.xx-mindspore-enterprise-lite-xx.xx.xx-linux-x64.tar.gz
```

> **须知：**
> 1. 请勿将多个不同版本的 MSLite 包放置于该目录下。
> 2. 请保持 Linux 服务器网络畅通。

### Dockerfile 内容

```dockerfile
ARG http_proxy https_proxy no_proxy

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends wget curl  build-essential python3.11-dev libpython3.11 python3-pip python3-dev ssh vim git \
    && rm -rf /var/lib/apt/lists/*

# GCC 14 工具链（官方依赖要求 GCC 14.3.x）。用 ubuntu-toolchain-r PPA（为 22.04 编译，不污染 glibc/binutils）
RUN apt-get install -y --no-install-recommends gpg wget \
    && wget -qO - https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x60C317803A41BA51845E371A1E9377A2BA9EF27F | gpg --dearmor -o /etc/apt/trusted.gpg.d/toolchain-r.gpg \
    && echo "deb https://ppa.launchpadcontent.net/ubuntu-toolchain-r/test/ubuntu jammy main" > /etc/apt/sources.list.d/toolchain-r-test.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gcc-14 g++-14 cmake \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 100 \
    && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-14 100 \
    && rm -rf /var/lib/apt/lists/*

# 1. 软链接：RUN ln -S /usr/bin/python3.11 python
RUN /usr/bin/python3.11 -m pip install wheel decorator sympy scipy==1.10.1 onnx==1.14.0 onnxruntime==1.15.0 numpy==1.24.3 tensorflow==2.13.0 torch==2.1.0 torchvision==0.16.0
RUN mkdir -p /usr/src/mindspore
COPY HiSpark.AI*-mindspore-*-x64.tar.gz /usr/src/env/mindspore-lite.tar.gz
RUN /usr/bin/tar -zxvf /usr/src/env/mindspore-lite.tar.gz -C /usr/src/mindspore

RUN echo "service ssh start" >> /root/.bashrc

# set ssh env，移除UsePAM=no那一行
RUN sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#*StrictModes yes/StrictModes yes/g' /etc/ssh/sshd_config

RUN ln -sf /usr/bin/python3.11 /usr/bin/python
```

### 环境准备步骤

环境准备前，请先保证 Linux 服务器安装 Docker。

1. 构建 Docker 镜像：

    执行如下命令构建 Docker 镜像：

    ```
    docker build -f Dockerfile_mslite -t {镜像名称}:{镜像标签} .
    ```

    如需要配置代理，请执行如下命令：

    ```
    docker build -f Dockerfile_mslite --build-arg http_proxy={http代理地址} --build-arg https_proxy={https代理地址} --build-arg no_proxy={排除代理地址} -t {镜像名称}:{镜像标签} .
    ```

    如果打印如下类似信息，表示 Docker 构建成功。

    ```
    Successfully built xxx
    Successfully tagged xxx
    ```

2. 执行如下命令运行容器，并关联端口及挂载文件夹：

    ```
    docker run -itd --ipc=host -p {服务器端口}:22 -v {服务器路径}:{容器路径} --name {容器名称} {镜像名称}:{镜像标签}
    ```

    其中：

    - `--ipc=host`：可选，配置后容器共享宿主机的内存。
    - `-p` 参数：表示将服务器对应端口映射到容器的 {服务器端口}:22 端口。
    - `-v` 参数：表示将服务器相应路径映射到容器内的相应路径。该参数为可选参数。

3. 执行如下命令启动容器：

    ```
    docker start {容器名称}
    ```

    使用如下指令查询运行的容器，如果查询的表格中包含启动的容器，则表示启动成功。

    ```
    docker ps
    ```

4. 配置容器 root 密码。
    1. 使用如下命令进入容器：

        ```
        docker exec -it {容器名称} /bin/bash
        ```

    2. 配置密码：

        ```
        passwd
        ```

5. 执行如下命令测试 ssh 连接。按照提示输入 root 密码，能够顺利进入容器，则表示 ssh 连接正常。

    ```
    ssh root@{服务器IP地址} -p {服务器端口}
    ```

### 镜像源配置说明

> 由于镜像构建过程中使用的镜像源由基础镜像 Ubuntu XX.XX 决定，请用户根据基础镜像决定是否更换镜像源。更换镜像源可参考 common 文件夹中 `Mirror_conf.sh` 中提供的示例进行修改，示例仅供参考，并不适用所有环境，请用户根据环境需要自行设置合适的镜像源。如用户 Ubuntu XX.XX 中配置的镜像源在 Docker 镜像构建过程中无法正常下载所需软件包，请参考 `Mirror_conf.sh` 修改合适的镜像源。

下述示例中，设置了 http://mirrors.aliyun.com 为镜像源，该镜像源并不一定适用所有的环境，请用户选择适合的镜像源进行替换。

```
#!/bin/bash
# Mirror source configuration

# The following configuration of mirror sources is for reference only.
# You need to configure proper mirror sources based on your environment requirements.
# Configure the image source according to the following example to ensure that the software package can be downloaded during image construction.

############## Modify the following information as required. ##################
# cp -a /etc/apt/sources.list /etc/apt/sources.list.bak
# sed -i "s@http://.*archive.ubuntu.com@http://mirrors.aliyun.com@g" /etc/apt/sources.list
# sed -i "s@http://.*security.ubuntu.com@http://mirrors.aliyun.com@g" /etc/apt/sources.list
# mkdir -p /root/.pip/
# echo '[global]' >> /root/.pip/pip.conf
# echo 'trusted-host=mirrors.aliyun.com' >> /root/.pip/pip.conf
# echo 'index-url=http://mirrors.aliyun.com/pypi/simple' >> /root/.pip/pip.conf
```

## CANN 基础版环境（Hi3322）

使用 Dockerfile 准备 Linux 服务器端 AI 环境。环境安装前需要从发布包获取 Dockerfile 文件、ATC 安装包、AMCT 安装包，并将其放置在同级目录下。

基础版环境使用 `Dockerfile_cann_cpu` 作为环境准备配置文件。

环境安装前，请先检查目录下是否包含如下文件：

```
.
├── CANN-amct-{版本号}-linux.x86_64.tar.gz
├── CANN-compiler-{版本号}-linux.x86_64.run
├── CANN-opp-{版本号}-linux.x86_64.run
├── CANN-runtime-{版本号}-linux.x86_64.run
├── CANN-toolkit-{版本号}-linux.x86_64.run
└── Dockerfile_cann_cpu
```

> **须知：**
> 1. 请勿将多个不同版本的 ATC 和 AMCT 安装包放置于该目录下。
> 2. 请保持 Linux 服务器网络畅通。

### Dockerfile 内容

```dockerfile
FROM ubuntu:22.04
WORKDIR /root
# Environment dependency packages download and install
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends wget curl build-essential python3 python3-pip python3-dev libxml2 vim ssh git cmake \
 && rm -rf /var/lib/apt/lists/*
# Python dependency packages install
RUN pip3 install wheel decorator sympy scipy==1.9.3 attrs psutil==5.8.0 setuptools==80.9.0 onnx==1.14.0 onnxruntime==1.16.0 protobuf==3.20.2 numpy==1.23.5 tensorflow-cpu==2.8.0 kconfiglib==14.1.0 pycparser==2.23 \
 && pip3 install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu
# Install ATC
COPY CANN-runtime-*-linux.x86_64.run runtime.run
RUN mkdir -p /usr/local/hisparkai \
 && chmod +x runtime.run \
 && ./runtime.run --full --install-path=/usr/local/hisparkai/Ascend \
 && rm -rf runtime.run
COPY CANN-compiler-*-linux.x86_64.run compiler.run
RUN chmod +x compiler.run \
 && ./compiler.run --full --install-path=/usr/local/hisparkai/Ascend --pylocal \
 && rm -rf compiler.run
COPY CANN-opp-*-linux.x86_64.run opp.run
RUN chmod +x opp.run \
 && ./opp.run --full --install-path=/usr/local/hisparkai/Ascend \
 && rm -rf opp.run
COPY CANN-toolkit-*-linux.x86_64.run toolkit.run
RUN chmod +x toolkit.run \
 && ./toolkit.run --full --install-path=/usr/local/hisparkai/Ascend \
 && rm -rf toolkit.run
# Install AMCT
COPY CANN-amct-*-linux.x86_64.tar.gz amct.tar.gz
RUN tar -zxvf amct.tar.gz -C . \
 && pip3 install ./amct/amct_onnx/amct_onnx-*-py3-none-linux_x86_64.whl \
 && tar -zxvf ./amct/amct_onnx/amct_onnx_op.tar.gz -C ./amct/amct_onnx \
 && cd ./amct/amct_onnx/amct_onnx_op \
 && python3 setup.py build \
 && cd /root/amct/amct_pytorch \
 && pip3 install amct_pytorch-*-py3-none-linux_x86_64.tar.gz \
 && rm -rf amct \
 && rm -rf amct.tar.gz
# SET env
RUN echo "source /usr/local/hisparkai/Ascend/latest/x86_64-linux/bin/setenv.bash" >> /root/.bashrc \
 && echo "service ssh start" >> /root/.bashrc
# set python -> python3
RUN ln -sf /usr/bin/python3.10 /usr/bin/python
# set ssh env
RUN sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config \
 && sed -i 's/^#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
 && sed -i 's/#*StrictModes yes/StrictModes yes/g' /etc/ssh/sshd_config \
 && sed -i 's/UsePAM yes/UsePAM no/g' /etc/ssh/sshd_config
EXPOSE 22
```

### 环境准备步骤

环境准备前，请先保证 Linux 服务器安装 Docker。

1. 构建 Docker 镜像：

    ```
    docker build -f Dockerfile_cann_cpu -t {镜像名称}:{镜像标签} .
    ```

    如需要配置代理，请执行如下命令：

    ```
    docker build -f Dockerfile_cann_cpu --build-arg http_proxy={http代理地址} --build-arg https_proxy={https代理地址} --build-arg no_proxy={排除代理地址} -t {镜像名称}:{镜像标签} .
    ```

    如果打印如下类似信息，表示 Docker 构建成功。

    ```
    Successfully built 61bc7fae9f9e
    Successfully tagged {镜像名称}:{镜像标签}
    ```

2. 执行如下命令运行容器，并关联端口及挂载文件夹：

    ```
    docker run -itd --ipc=host -p {服务器端口}:22 -v {服务器路径}:{容器路径} --name {容器名称} {镜像名称}:{镜像标签}
    ```

    其中：

    - `--ipc=host`：可选，配置后容器共享宿主机的内存。
    - `-p` 参数：表示将服务器对应端口映射到容器的 {服务器端口}:22 端口。
    - `-v` 参数：表示将服务器相应路径映射到容器内的相应路径。该参数为可选参数。

3. 执行如下命令启动容器：

    ```
    docker start {容器名称}
    ```

    使用如下指令查询运行的容器，如果查询的表格中包含启动的容器，则表示启动成功。

    ```
    docker ps
    ```

4. 配置容器 root 密码。
    - 使用如下命令进入容器：

        ```
        docker exec -it {容器名称} /bin/bash
        ```

    - 配置密码：

        ```
        passwd
        ```

5. 执行如下命令测试 ssh 连接。按照提示输入 root 密码，能够顺利进入容器，则表示 ssh 连接正常。

    ```
    ssh root@{服务器IP地址} -p {服务器端口}
    ```

> **说明：** 如遇到镜像代理未配置的网络问题，请参考上文「MSLite 环境（Hi3863）」中的「镜像源配置说明」完成代理配置。

## CANN GPU 加速版环境（Hi3322）

GPU 加速版环境使用 `Dockerfile_cann_gpu` 作为环境准备配置文件，GPU 可以加速量化感知训练的效率。

环境安装前，请先检查目录下是否包含如下文件：

```
.
├── CANN-amct-{版本号}-linux.x86_64.tar.gz
├── CANN-compiler-{版本号}-linux.x86_64.run
├── CANN-opp-{版本号}-linux.x86_64.run
├── CANN-runtime-{版本号}-linux.x86_64.run
├── CANN-toolkit-{版本号}-linux.x86_64.run
└── Dockerfile_cann_gpu
```

> **须知：**
> 1. 请勿将多个不同版本的 ATC 和 AMCT 安装包放置于该目录下。
> 2. 请保持 Linux 服务器网络畅通。

### Dockerfile 内容

```dockerfile
FROM ubuntu:22.04
WORKDIR /root
# Environment dependency packages download and install
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends wget curl build-essential python3 python3-pip libxml2 python3-dev git vim ssh cmake \
 && rm -rf /var/lib/apt/lists/*
# Install CUDA
RUN wget --no-check-certificate -c https://developer.download.nvidia.com/compute/cuda/12.2.0/local_installers/cuda_12.2.0_535.54.03_linux.run -O cuda_linux.run \
 && chmod +x cuda_linux.run \
 && ./cuda_linux.run --toolkit --silent \
 && rm -rf cuda_linux.run
# Install PYTHON environment dependency library
RUN pip3 install --no-cache-dir wheel decorator sympy scipy==1.9.3 attrs psutil==5.8.0 setuptools==80.9.0 onnx==1.14.0 onnxruntime==1.16.0 protobuf==3.20.2 torch==2.1.0 torchvision==0.16.0 numpy==1.23.5 tensorflow==2.8.0 kconfiglib==14.1.0 pycparser==2.23
# Install ATC
COPY CANN-runtime-*-linux.x86_64.run runtime.run
RUN mkdir -p /usr/local/hisparkai \
 && chmod +x runtime.run \
 && ./runtime.run --full --install-path=/usr/local/hisparkai/Ascend \
 && rm -rf runtime.run
COPY CANN-compiler-*-linux.x86_64.run compiler.run
RUN chmod +x compiler.run \
 && ./compiler.run --full --install-path=/usr/local/hisparkai/Ascend --pylocal \
 && rm -rf compiler.run
COPY CANN-opp-*-linux.x86_64.run opp.run
RUN chmod +x opp.run \
 && ./opp.run --full --install-path=/usr/local/hisparkai/Ascend \
 && rm -rf opp.run
COPY CANN-toolkit-*-linux.x86_64.run toolkit.run
RUN chmod +x toolkit.run \
 && ./toolkit.run --full --install-path=/usr/local/hisparkai/Ascend \
 && rm -rf toolkit.run
# Install AMCT
COPY CANN-amct-*-linux.x86_64.tar.gz amct.tar.gz
RUN tar -zxvf amct.tar.gz -C . \
 && pip3 install ./amct/amct_onnx/amct_onnx-*-py3-none-linux_x86_64.whl \
 && tar -zxvf ./amct/amct_onnx/amct_onnx_op.tar.gz -C ./amct/amct_onnx \
 && cd ./amct/amct_onnx/amct_onnx_op \
 && python3 setup.py build \
 && cd /root/amct/amct_pytorch \
 && pip3 install amct_pytorch-*-py3-none-linux_x86_64.tar.gz \
 && rm -rf amct \
 && rm -rf amct.tar.gz
# SET env
RUN echo "source /usr/local/hisparkai/Ascend/latest/x86_64-linux/bin/setenv.bash" >> /root/.bashrc \
 && echo "service ssh start" >> /root/.bashrc
# set python -> python3
RUN ln -sf /usr/bin/python3.10 /usr/bin/python
# set ssh env
RUN sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config \
 && sed -i 's/^#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
 && sed -i 's/#*StrictModes yes/StrictModes yes/g' /etc/ssh/sshd_config \
 && sed -i 's/UsePAM yes/UsePAM no/g' /etc/ssh/sshd_config
EXPOSE 22
```

### 前置条件

GPU 加速版环境准备前，请先保证 Linux 服务器：

1. 安装 Docker。
2. 安装 GPU 驱动，并保证版本号 ≥ 525。
3. 安装和配置 NVIDIA Container Toolkit。

### 环境准备步骤

1. 构建 Docker 镜像：

    ```
    docker build -f Dockerfile_cann_gpu -t {镜像名称}:{镜像标签} .
    ```

    如需要配置代理，请执行如下命令：

    ```
    docker build -f Dockerfile_cann_gpu --build-arg http_proxy={http代理地址} --build-arg https_proxy={https代理地址} --build-arg no_proxy={排除代理地址} -t {镜像名称}:{镜像标签} .
    ```

    如果打印如下类似信息，表示 Docker 构建成功。

    ```
    Successfully built 61bc7fae9f9e
    Successfully tagged {镜像名称}:{镜像标签}
    ```

2. 执行如下命令运行容器，并关联端口及挂载文件夹：

    ```
    docker run -itd --ipc=host -p {服务器端口}:22 --gpus all -v {服务器路径}:{容器路径} --name {容器名称} {镜像名称}:{镜像标签}
    ```

    其中：

    - `--ipc=host`：可选，配置后容器共享宿主机的内存。
    - `-p` 参数：表示将服务器对应端口映射到容器的 22 端口。
    - `--gpus` 参数：表示 GPU 对容器可见。
    - `-v` 参数：表示将服务器相应路径映射到容器内的相应路径。该参数为可选参数。

3. 执行如下命令启动容器：

    ```
    docker start {容器名称}
    ```

    使用如下指令查询运行的容器，如果查询的表格中包含启动的容器，则表示启动成功。

    ```
    docker ps
    ```

4. 配置容器 root 密码。
    - 使用如下命令进入容器：

        ```
        docker exec -it {容器名称} /bin/bash
        ```

    - 配置密码：

        ```
        passwd
        ```

5. 在容器内执行如下命令测试 GPU 是否可用。

    ```
    nvidia-smi
    ```

    命令输出类似信息（如 GPU 型号、驱动版本、显存使用情况等），表示 GPU 可用。

6. 在 Linux 服务器执行如下命令测试 ssh 连接。按照提示输入 root 密码，能够顺利进入容器，则表示 ssh 连接正常。

    ```
    ssh root@{服务器IP地址} -p {服务器端口}
    ```
