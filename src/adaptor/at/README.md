# WS63 AT系统使用

## 系统介绍
WS63 AI AT系统包含三条命令，AIINIT，AIINFER，AIDESTROY，旨在提升HiSpark Studio AI的易用性 以及 性能。

[1] AIINIT  
* 设置指令 AI+AIINIT
* 响应：成功：OK；失败：ERROR  
* 参数说明：-
* 实例：AT+AIINIT加载AI资源

[2] AIINFER  
* 设置指令 AI+AIINFER=<START_ADDR>,<DUMP_OFFSET>,<LOAD_OFFSET>
* 响应：成功：OK；失败：ERROR  
* 参数说明：
1. START_ADDR起始地址，范围为[0x00390000,0x00450000]
2. DUMP_OFFSET为DUMP功能预留空间大小，范围为(0,0x00030000]
3. LOAD_OFFSET为LOAD功能预留空间大小，范围为(0,0x00030000]
* 实例：AI+AIINFER=0x00390000,0x00030000,0x00030000 完成AI推理

[3] AIDESTROY
* 设置指令 AI+AIDESTROY
* 响应：成功：OK；失败：ERROR  
* 参数说明：-
* 实例：AT+AIDESTROY销毁AI资源


## 操作指南

### 1.1 组合SDK
1. 将ai_adaptor发布包中的at/at_ai_cmd文件夹，拷贝到middleware/utils/at目录下
2. 将ai_adaptor发布包中的adaptor以及include文件夹，拷贝到middleware/utils/ai_mcu目录下

### 1.2 修改SDK默认选项
1. 将middleware/utils/CMakeLists.txt中加入 "add_subdirectory_if_exist(ai_mcu/adaptor/cpu)"
2. 将middleware/utils/at/CMakeLists.txt中加入 "add_subdirectory_if_exist(at_ai_cmd)"
3. 将build/config/target_config/ws63/config.py中 ws63-liteos-app字段中，"ram_component"选项加入 "ai_at", "ai_adaptor_cpu"两个组件。

### 1.3 新增AT注册
找到application/ws63/ws63_liteos_application/main.c
1. 增加 "#include "at_ai_cmd_register.h"在app_task_definition_t结构体定义上方。
2. 在do_at_cmd_register函数中，增加 "at_ai_cmd_register();"这一行。

### 2. 使用Converter_lite工具链进行转换（后续由HiSpark Studio AI自动执行）
此步骤请参考《HiSpark.AI转换工具指南》将客户的目标模型转换成libnet.a以及libmicro_runtime.a放置在middleware/utils/ai_mcu/lib下，如果用户未创建目录，请手动创建。

### 3. 烧录数据（后续由HiSpark Studio AI自动执行）
调用mslite_burn_data.py脚本，将npy数据烧录到板端；  
命令如下所示：
```
D:\tools\python\python.exe "xxx\profiling\mslite_burn_data.py" --input_data "testcases\mnist\npy_data_mnist\sample_00000_7.npy" --burn_tool_path "xxx\\BurnTool.exe" --port "COM9"
```

Tip: 提前确保板端Ready，根据实际情况调整--port选项为实际WS63烧录口。

### 4. 发送AT命令（后续由HiSpark Studio AI自动执行）
利用SSCOM工具发送AT命令
```
AT+AIINIT
```
板端提示 AT+AIINIT OK 字样即表示成功

```
AT+AIINFER=0X00390000,0x00030000,0x00030000
```
板端提示 OK 字样即表示成功

### 5. 取出数据
调用mslite_export_data.py脚本，将npy数据烧录到板端；  
命令如下所示：
```
D:\tools\python\python.exe "xxx\profiling\mslite_export_data.py" --burn_tool_path "xxx\\BurnTool.exe" --port "COM9"
```

Tip: 提前确保板端Ready，根据实际情况调整--port选项为实际WS63烧录口。

脚本会打印真实的结果，如[(-29.55451011657715, 25.502681732177734, 7.150284767150879, -9.295370101928711, -4.528513431549072, 17.160682678222656, -8.818684577941895, 30.26953887939453, -28.839481353759766, -30.03119468688965)]