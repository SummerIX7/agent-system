---
title: 函数与模块
source_type: book
source_name: Python编程从入门到实践
author: Eric Matthes
publisher: 人民邮电出版社
year: 2023
chapter: 第8章 函数、第9章 类
---

# 函数与模块

## 概述

函数是 Python 代码组织的基本单元，通过将功能封装为函数，可以实现代码复用、提高可读性。模块则是将相关函数和类组织在一起的文件，是 Python 项目结构化的核心机制。本文介绍函数定义、参数处理、装饰器以及模块导入等关键知识点。

## 核心概念

### 函数定义与参数

函数通过 `def` 关键字定义，支持多种参数形式，包括位置参数、默认参数、可变参数和关键字参数。

```python
# 基本函数定义
def calculate_mean(data):
    """计算列表的平均值"""
    return sum(data) / len(data)

# 默认参数
def normalize(data, method="minmax"):
    if method == "minmax":
        min_val, max_val = min(data), max(data)
        return [(x - min_val) / (max_val - min_val) for x in data]
    elif method == "zscore":
        mean = sum(data) / len(data)
        std = (sum((x - mean)**2 for x in data) / len(data))**0.5
        return [(x - mean) / std for x in data]

# 可变参数
def summary(*args, **kwargs):
    """接收任意数量的位置参数和关键字参数"""
    print(f"位置参数: {args}")
    print(f"关键字参数: {kwargs}")

summary(1, 2, 3, name="test", mode="debug")
```

### 装饰器

装饰器是 Python 的高阶函数语法糖，用于在不修改原函数代码的前提下为函数添加额外功能，常用于日志记录、权限校验、性能计时等场景。

```python
import time
from functools import wraps

# 计时装饰器
def timer(func):
    @wraps(func)  # 保留原函数的元信息
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} 执行耗时: {elapsed:.4f}秒")
        return result
    return wrapper

@timer
def heavy_computation(n):
    """模拟耗时计算"""
    return sum(i**2 for i in range(n))

result = heavy_computation(1000000)
```

### Lambda 表达式

Lambda 是匿名函数，适用于简短的一次性函数场景，在排序、过滤等操作中尤为常见。

```python
# Lambda 基本用法
square = lambda x: x ** 2
print(square(5))  # 25

# 配合 sorted 使用
students = [
    {"name": "张三", "score": 85},
    {"name": "李四", "score": 92},
    {"name": "王五", "score": 78}
]
sorted_students = sorted(students, key=lambda s: s["score"], reverse=True)

# 配合 map 和 filter
scores = [85, 92, 78, 96, 88, 45]
passed = list(filter(lambda x: x >= 60, scores))
doubled = list(map(lambda x: x * 2, scores))
```

### 模块与包

模块是 `.py` 文件，包是包含 `__init__.py` 的目录。通过 `import` 语句导入模块，可以使用标准库和第三方库的丰富功能。

```python
# 导入方式
import os                          # 导入整个模块
from datetime import datetime     # 导入特定对象
import numpy as np                 # 别名导入
from collections import Counter, defaultdict

# 自定义模块示例：utils.py
# def clean_data(data):
#     return [x for x in data if x is not None]

# 在其他文件中使用
# from utils import clean_data

# 常用标准库
import json
import csv
import re
import pathlib
```

## 常用函数/方法

```python
# 常用高阶函数
map(func, iterable)        # 对每个元素应用函数
filter(func, iterable)     # 过滤满足条件的元素
reduce(func, iterable)     # 累积计算（需 from functools import reduce）
sorted(iterable, key=func) # 自定义排序

# 常用内置模块
math.ceil(3.2)             # 向上取整: 4
math.floor(3.8)            # 向下取整: 3
random.randint(1, 100)     # 随机整数
random.choice([1, 2, 3])   # 随机选择
random.sample(range(100), 5)  # 随机抽样
```

## 注意事项

1. 函数应遵循单一职责原则，一个函数只做一件事，便于测试和维护。
2. 默认参数应使用不可变对象（如 `None`、数字、字符串），避免使用可变对象（如列表、字典）作为默认值，否则会导致意外的副作用。
3. 使用 `@wraps(func)` 装饰器包装内层函数，否则原函数的 `__name__`、`__doc__` 等属性会丢失。
4. 模块导入应放在文件顶部，按标准库、第三方库、本地模块的顺序分组排列。
