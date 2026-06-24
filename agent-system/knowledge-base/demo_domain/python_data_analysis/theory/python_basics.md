---
title: Python 基础语法
source_type: book
source_name: Python编程从入门到实践
author: Eric Matthes
publisher: 人民邮电出版社
year: 2023
chapter: 第2章 变量和简单数据类型、第5章 if语句、第7章 用户输入和while循环
---

# Python 基础语法

## 概述

Python 是一种解释型、动态类型的高级编程语言，以其简洁清晰的语法著称。掌握 Python 的变量、数据类型和控制流是进行数据分析的基石。本文涵盖变量命名规则、基本数据类型、条件判断和循环结构等核心内容。

## 核心概念

### 变量与数据类型

Python 是动态类型语言，变量无需声明类型即可直接赋值。常用的基本数据类型包括整数（int）、浮点数（float）、字符串（str）和布尔值（bool）。

```python
# 变量赋值
name = "数据分析"
version = 3.11
count = 100
is_ready = True

# 类型检查
print(type(name))     # <class 'str'>
print(type(version))  # <class 'float'>
print(type(count))    # <class 'int'>
print(type(is_ready)) # <class 'bool'>

# 类型转换
num_str = "42"
num_int = int(num_str)       # 字符串转整数
num_float = float(num_str)   # 字符串转浮点数
back_str = str(num_int)      # 整数转字符串
```

### 数据结构

Python 内置了列表（list）、元组（tuple）、字典（dict）和集合（set）四种核心数据结构，在数据处理中极为常用。

```python
# 列表：有序可变序列
scores = [85, 92, 78, 96, 88]
scores.append(90)          # 添加元素
top_scores = scores[:3]    # 切片操作

# 字典：键值对映射
student = {
    "name": "张三",
    "age": 20,
    "scores": scores
}
student["grade"] = "大一"  # 新增键值对

# 列表推导式
high_scores = [s for s in scores if s >= 90]
```

### 条件判断

条件语句通过 `if`/`elif`/`else` 实现分支逻辑，支持嵌套和多条件组合。

```python
# 条件判断
score = 85
if score >= 90:
    level = "优秀"
elif score >= 80:
    level = "良好"
elif score >= 60:
    level = "及格"
else:
    level = "不及格"

# 多条件组合
age = 25
income = 8000
if age >= 18 and income >= 5000:
    print("符合申请条件")
```

### 循环结构

Python 提供 `for` 和 `while` 两种循环，`for` 循环常用于遍历可迭代对象，`while` 循环用于条件驱动的重复执行。

```python
# for 循环遍历
fruits = ["苹果", "香蕉", "橙子"]
for i, fruit in enumerate(fruits):
    print(f"{i}: {fruit}")

# while 循环
total = 0
n = 1
while n <= 100:
    total += n
    n += 1
print(f"1到100的和: {total}")  # 5050

# break 和 continue
for num in range(10):
    if num == 3:
        continue  # 跳过3
    if num == 7:
        break     # 到7停止
    print(num)
```

## 常用函数/方法

```python
# 常用内置函数
len([1, 2, 3])         # 获取长度: 3
range(5)               # 生成序列: 0,1,2,3,4
sorted([3, 1, 2])      # 排序: [1, 2, 3]
isinstance(42, int)    # 类型判断: True
enumerate(["a", "b"])  # 带索引遍历
zip([1, 2], [3, 4])    # 并行遍历

# 字符串常用方法
text = "Hello, World!"
text.lower()           # 转小写
text.split(",")        # 分割字符串
text.replace("H", "h") # 替换子串
```

## 注意事项

1. Python 使用缩进（通常为4个空格）来表示代码块，而非花括号，缩进不一致会导致 `IndentationError`。
2. 变量名区分大小写，`Name` 和 `name` 是两个不同的变量。
3. 浮点数运算存在精度问题（如 `0.1 + 0.2 != 0.3`），涉及精确计算时应使用 `decimal` 模块。
4. 列表是可变对象，赋值操作传递的是引用而非副本，修改副本会影响原对象，必要时使用 `copy()` 或切片创建副本。
