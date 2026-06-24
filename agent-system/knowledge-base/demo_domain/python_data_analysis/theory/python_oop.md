---
title: 面向对象编程
source_type: book
source_name: Python编程从入门到实践
author: Eric Matthes
publisher: 人民邮电出版社
year: 2023
chapter: 第9章 类
---

# 面向对象编程

## 概述

面向对象编程（OOP）是 Python 的重要编程范式，通过类和对象将数据与操作封装在一起。在数据分析领域，OOP 可以帮助我们构建数据处理器、模型封装器等可复用组件。本文介绍类的定义、继承机制以及魔术方法等核心概念。

## 核心概念

### 类的定义与实例化

类是对象的蓝图，通过 `class` 关键字定义。`__init__` 方法是构造函数，在实例化时自动调用，用于初始化对象属性。

```python
class DataCleaner:
    """数据清洗器"""

    def __init__(self, data, missing_strategy="mean"):
        self.data = data
        self.missing_strategy = missing_strategy
        self._log = []  # 私有属性

    def remove_outliers(self, threshold=3):
        """基于Z-score移除异常值"""
        mean = sum(self.data) / len(self.data)
        std = (sum((x - mean)**2 for x in self.data) / len(self.data))**0.5
        self.data = [x for x in self.data
                     if abs((x - mean) / std) <= threshold]
        self._log.append(f"移除异常值, 阈值={threshold}")
        return self

    def fill_missing(self, values):
        """填充缺失值（用None表示）"""
        if self.missing_strategy == "mean":
            fill_val = sum(v for v in values if v is not None) / len([v for v in values if v is not None])
        else:
            fill_val = 0
        self.data = [v if v is not None else fill_val for v in values]
        return self

    def get_result(self):
        return self.data

# 实例化使用
cleaner = DataCleaner([1, 2, 100, 3, 4, 5])
result = cleaner.remove_outliers(threshold=2).get_result()
print(result)
```

### 继承

继承允许子类复用父类的属性和方法，并可以扩展或重写父类功能。Python 支持单继承和多继承。

```python
class BaseProcessor:
    """基础处理器"""

    def __init__(self, name):
        self.name = name

    def process(self, data):
        raise NotImplementedError("子类必须实现 process 方法")

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}')"


class Normalizer(BaseProcessor):
    """归一化处理器，继承自 BaseProcessor"""

    def __init__(self, name, method="minmax"):
        super().__init__(name)  # 调用父类构造函数
        self.method = method

    def process(self, data):
        """重写父类方法"""
        if self.method == "minmax":
            min_val, max_val = min(data), max(data)
            return [(x - min_val) / (max_val - min_val) for x in data]
        return data

    def inverse(self, normalized_data):
        """子类独有方法"""
        pass

norm = Normalizer("特征归一化")
print(norm)  # Normalizer(name='特征归一化')
print(norm.process([10, 20, 30, 40, 50]))
```

### 魔术方法

魔术方法（双下划线方法）让自定义类可以像内置类型一样使用，支持运算符重载、字符串表示、容器协议等。

```python
class DataPoint:
    """数据点类，演示魔术方法"""

    def __init__(self, values):
        self.values = list(values)

    def __repr__(self):
        return f"DataPoint({self.values})"

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        return self.values[index]

    def __add__(self, other):
        """支持 + 运算符"""
        return DataPoint([a + b for a, b in zip(self.values, other.values)])

    def __eq__(self, other):
        """支持 == 比较"""
        return self.values == other.values

    def __contains__(self, item):
        """支持 in 运算符"""
        return item in self.values

p1 = DataPoint([1, 2, 3])
p2 = DataPoint([4, 5, 6])
p3 = p1 + p2        # DataPoint([5, 7, 9])
print(len(p1))       # 3
print(p1[0])         # 1
print(2 in p1)       # True
```

## 常用函数/方法

```python
# 类相关的内置函数和方法
isinstance(obj, ClassName)    # 检查对象是否为某类的实例
issubclass(Sub, Parent)       # 检查是否为子类
hasattr(obj, "attr_name")     # 检查属性是否存在
getattr(obj, "attr", default) # 获取属性值
vars(obj)                     # 获取对象的所有属性字典

# 属性控制
class Example:
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        if val < 0:
            raise ValueError("值不能为负数")
        self._value = val
```

## 注意事项

1. Python 没有严格的访问控制，约定以下划线开头的属性（如 `_attr`）为私有，双下划线（如 `__attr`）会触发名称修饰机制。
2. 优先使用组合（has-a）而非继承（is-a）来实现代码复用，继承层次过深会增加维护难度。
3. `super().__init__()` 的调用在多重继承场景下需要注意方法解析顺序（MRO），可使用 `ClassName.__mro__` 查看。
4. 魔术方法应保持语义一致性，例如 `__add__` 不应有副作用，`__len__` 应返回非负整数。
