---
title: Python 调试技巧
source_type: practice
source_name: Python数据分析实战
author: 张明
publisher: 人民邮电出版社
year: 2021
chapter: 实战指南
---

# Python 调试技巧

## 概述

调试是编程中不可或缺的技能。掌握高效的调试方法能大幅缩短问题定位时间，提高开发效率。本文介绍四种主流调试方式：print调试、pdb调试器、IDE可视化调试以及常见错误排查技巧。

## 实操步骤

### 步骤1：print 调试法

最简单的调试方式，适合快速定位问题：

```python
def calculate_average(numbers):
    print(f"输入数据: {numbers}")  # 检查输入
    total = sum(numbers)
    print(f"总和: {total}")  # 检查中间结果
    count = len(numbers)
    print(f"数量: {count}")
    result = total / count
    print(f"结果: {result}")  # 检查最终输出
    return result

# 使用logging模块替代print（生产环境推荐）
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process_data(data):
    logger.debug(f"处理数据: {data}")
    # 处理逻辑
    logger.info("处理完成")
```

### 步骤2：pdb 交互式调试

Python内置调试器，支持断点、单步执行、变量检查：

```python
import pdb

def complex_function(data):
    result = []
    for item in data:
        pdb.set_trace()  # 设置断点，程序会在此暂停
        processed = item * 2
        result.append(processed)
    return result

# pdb常用命令：
# n (next) - 执行下一行
# s (step) - 进入函数
# c (continue) - 继续执行
# p variable - 打印变量值
# l (list) - 显示当前代码
# q (quit) - 退出调试
```

### 步骤3：IDE 可视化调试

以VS Code为例配置调试环境：

```python
# launch.json配置
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: 当前文件",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}

# 在代码中设置断点后，按F5启动调试
# 支持：条件断点、日志断点、异常断点
```

### 步骤4：常见错误排查

```python
# 1. IndexError - 索引越界
data = [1, 2, 3]
# 错误：data[10]
# 解决：检查列表长度，使用try-except

# 2. KeyError - 字典键不存在
my_dict = {"name": "Alice"}
# 错误：my_dict["age"]
# 解决：使用get方法或检查键是否存在

# 3. TypeError - 类型错误
# 错误：1 + "2"
# 解决：类型转换 int("2") 或 str(1)

# 4. AttributeError - 属性不存在
# 解决：使用hasattr()检查，或dir()查看可用属性
```

## 常见问题与解决方案

1. **问题**：断点不生效 **解决**：检查代码是否已保存，确认调试器附加到正确进程
2. **问题**：调试时变量显示为 `<optimized out>` **解决**：关闭编译器优化，使用debug模式运行
3. **问题**：异常被吞掉无法定位 **解决**：避免空的except块，记录异常日志

## 最佳实践

1. 开发阶段使用logging替代print，便于控制输出级别
2. 复杂逻辑优先使用IDE调试器，支持变量监视和调用栈查看
3. 编写单元测试预防bug，使用pytest的--pdb选项自动进入调试
4. 善用断言(assert)进行前置条件检查
