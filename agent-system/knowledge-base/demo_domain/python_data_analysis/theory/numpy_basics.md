# NumPy 基础

## 概述

NumPy（Numerical Python）是 Python 科学计算的基础库，提供了高性能的多维数组对象和丰富的数学函数。

## 核心概念

### ndarray（N-dimensional Array）

NumPy 的核心数据结构是 `ndarray`，它是一个多维、同类型的数组对象。

```python
import numpy as np

# 创建数组
arr1d = np.array([1, 2, 3, 4, 5])          # 一维数组
arr2d = np.array([[1, 2, 3], [4, 5, 6]])    # 二维数组

# 常用创建函数
zeros = np.zeros((3, 4))      # 3x4 全零矩阵
ones = np.ones((2, 3))        # 2x3 全一矩阵
eye = np.eye(3)               # 3x3 单位矩阵
arange = np.arange(0, 10, 2)  # [0, 2, 4, 6, 8]
linspace = np.linspace(0, 1, 5)  # [0, 0.25, 0.5, 0.75, 1.0]
random = np.random.rand(3, 3) # 3x3 随机矩阵（0-1）
```

### 数组属性

```python
arr = np.array([[1, 2, 3], [4, 5, 6]])

arr.ndim     # 维度数：2
arr.shape    # 形状：(2, 3)
arr.size     # 元素总数：6
arr.dtype    # 数据类型：int64
arr.itemsize # 每个元素的字节数：8
```

### 索引与切片

```python
arr = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

# 基本索引
arr[0, 0]      # 1（第0行第0列）
arr[1, 2]      # 6（第1行第2列）

# 切片
arr[0:2, :]    # 前两行所有列
arr[:, 1]      # 所有行的第1列
arr[0:2, 0:2]  # 前两行前两列

# 布尔索引
mask = arr > 5
arr[mask]      # [6, 7, 8, 9]
```

### 数据类型

```python
np.array([1, 2, 3], dtype=np.float64)   # 指定 float64
np.array([1, 2, 3], dtype=np.int32)     # 指定 int32
np.array([1, 2, 3]).astype(float)       # 类型转换
```

## 常用函数

```python
arr = np.array([3, 1, 4, 1, 5, 9, 2, 6])

# 排序
np.sort(arr)           # [1, 1, 2, 3, 4, 5, 6, 9]

# 聚合
np.sum(arr)            # 求和：31
np.mean(arr)           # 平均值：3.875
np.std(arr)            # 标准差
np.min(arr)            # 最小值：1
np.max(arr)            # 最大值：9
np.argmin(arr)         # 最小值索引：1
np.argmax(arr)         # 最大值索引：5

# 数学运算
np.sqrt(arr)           # 平方根
np.exp(arr)            # 指数
np.log(arr)            # 自然对数
```

## 注意事项

1. NumPy 数组是同质的，所有元素必须是同一类型
2. NumPy 的切片返回的是**视图**而非副本，修改切片会影响原数组
3. 使用 `arr.copy()` 创建独立副本
