---
title: NumPy 随机数与性能优化
source_type: book
source_name: Python数据科学手册
author: Jake VanderPlas
publisher: O'Reilly
year: 2023
chapter: 第2章
---

# NumPy 随机数与性能优化

## 随机数生成

### numpy.random 模块

```python
import numpy as np

# 设置随机种子（可复现）
np.random.seed(42)

# 均匀分布 [0, 1)
np.random.rand(3, 3)           # 3x3 矩阵
np.random.rand(10)             # 10 个数

# 正态分布（均值0，标准差1）
np.random.randn(3, 3)          # 标准正态分布
np.random.normal(5, 2, 100)    # 均值5，标准差2，100个数

# 整数随机数
np.random.randint(0, 10, 5)    # [0, 10) 中取 5 个
np.random.randint(1, 7, size=(3, 4))  # 3x4 矩阵

# 选择
arr = np.array([10, 20, 30, 40, 50])
np.random.choice(arr, 3)               # 随机选 3 个
np.random.choice(arr, 3, replace=False) # 不重复选择
np.random.choice(arr, 100, p=[0.1, 0.2, 0.3, 0.2, 0.2])  # 带概率

# 打乱顺序
data = np.arange(10)
np.random.shuffle(data)        # 原地打乱
np.random.permutation(data)    # 返回新数组
```

### 新版随机数 API（推荐）

```python
# numpy 1.17+ 推荐使用 Generator
rng = np.random.default_rng(seed=42)

rng.random((3, 3))             # 均匀分布
rng.normal(5, 2, 100)          # 正态分布
rng.integers(0, 10, 5)         # 整数
rng.choice(arr, 3)             # 选择
rng.permutation(arr)           # 打乱
rng.shuffle(arr)               # 原地打乱
```

## 性能优化技巧

### 1. 避免 Python 循环

```python
import time

# 慢：Python 循环
def sum_loop(arr):
    total = 0
    for x in arr:
        total += x
    return total

# 快：NumPy 内置
arr = np.random.rand(1000000)

start = time.time()
sum_loop(arr)
print(f"循环: {time.time()-start:.4f}s")

start = time.time()
np.sum(arr)
print(f"NumPy: {time.time()-start:.4f}s")
```

### 2. 预分配内存

```python
# 慢：动态增长
result = []
for i in range(100000):
    result.append(i * 2)
result = np.array(result)

# 快：预分配
result = np.empty(100000)
for i in range(100000):
    result[i] = i * 2

# 更快：向量化
result = np.arange(100000) * 2
```

### 3. 就地操作

```python
# 创建新数组（慢）
arr = arr + 1
arr = arr * 2

# 就地操作（快）
arr += 1
arr *= 2
```

### 4. 选择合适的数据类型

```python
# 默认 float64
arr64 = np.zeros(1000000)  # 8MB

# 使用 float32
arr32 = np.zeros(1000000, dtype=np.float32)  # 4MB

# 使用 float16（精度较低）
arr16 = np.zeros(1000000, dtype=np.float16)  # 2MB
```

### 5. 使用 numexpr 加速复杂表达式

```python
import numexpr as ne

a = np.random.rand(1000000)
b = np.random.rand(1000000)

# NumPy
result = a**2 + b**2 + 2*a*b

# numexpr（自动多线程）
result = ne.evaluate('a**2 + b**2 + 2*a*b')
```

## 内存映射大文件

```python
# 创建内存映射文件
fp = np.memmap('large_data.dat', dtype='float64', mode='w+', shape=(10000, 10000))
fp[:] = np.random.rand(10000, 10000)
del fp  # 关闭并写入磁盘

# 读取内存映射
fp = np.memmap('large_data.dat', dtype='float64', mode='r', shape=(10000, 10000))
# 可以像普通数组一样操作，但不会全部加载到内存
```

## 广播性能对比

```python
# 慢：显式循环
def normalize_loop(data, mean, std):
    result = np.empty_like(data)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            result[i, j] = (data[i, j] - mean[j]) / std[j]
    return result

# 快：广播
def normalize_broadcast(data, mean, std):
    return (data - mean) / std

data = np.random.rand(1000, 100)
mean = data.mean(axis=0)
std = data.std(axis=0)
```
