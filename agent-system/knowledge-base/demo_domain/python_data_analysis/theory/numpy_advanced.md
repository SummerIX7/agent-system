# NumPy 高级特性

## 广播机制（Broadcasting）

广播是 NumPy 处理不同形状数组运算的机制。当两个数组形状不同时，NumPy 会自动扩展较小的数组。

### 广播规则

1. 如果两个数组的维度数不同，形状较短的数组会在**左侧**补 1
2. 如果在某个维度上大小相同，或者其中一个为 1，则兼容
3. 如果在某个维度上大小不同且都不为 1，则报错

```python
import numpy as np

# 标量与数组运算
arr = np.array([[1, 2, 3], [4, 5, 6]])
arr + 10  # 标量 10 被广播到每个元素

# 一维与二维运算
a = np.array([[1, 2, 3], [4, 5, 6]])  # shape: (2, 3)
b = np.array([10, 20, 30])             # shape: (3,)
a + b  # b 被广播为 [[10,20,30], [10,20,30]]

# 列向量与行向量
col = np.array([[1], [2], [3]])  # shape: (3, 1)
row = np.array([10, 20])         # shape: (2,)
col + row  # 结果 shape: (3, 2)
```

### 广播的实际应用

```python
# 数据标准化（Z-score）
data = np.random.rand(100, 5)  # 100个样本，5个特征
mean = data.mean(axis=0)       # 每列均值
std = data.std(axis=0)         # 每列标准差
normalized = (data - mean) / std  # 广播自动对齐
```

## 向量化运算

向量化是用数组操作替代 Python 循环，大幅提升性能。

```python
import numpy as np
import time

# 非向量化（慢）
def dot_product_loop(a, b):
    result = 0
    for i in range(len(a)):
        result += a[i] * b[i]
    return result

# 向量化（快）
def dot_product_numpy(a, b):
    return np.dot(a, b)

# 性能对比
a = np.random.rand(1000000)
b = np.random.rand(1000000)

start = time.time()
dot_product_loop(a, b)
print(f"循环耗时: {time.time() - start:.3f}s")

start = time.time()
dot_product_numpy(a, b)
print(f"NumPy 耗时: {time.time() - start:.3f}s")
# NumPy 通常快 100-1000 倍
```

## 花式索引（Fancy Indexing）

```python
arr = np.array([10, 20, 30, 40, 50])

# 整数数组索引
indices = [0, 2, 4]
arr[indices]  # [10, 30, 50]

# 二维花式索引
arr2d = np.arange(12).reshape(3, 4)
rows = np.array([0, 2])
cols = np.array([1, 3])
arr2d[rows, cols]  # [1, 11]

# ix_ 函数
arr2d[np.ix_([0, 2], [1, 3])]  # 选取行0,2和列1,3的交叉元素
```

## 数组重塑

```python
arr = np.arange(12)

# reshape
arr.reshape(3, 4)      # 3x4 矩阵
arr.reshape(3, -1)     # -1 表示自动计算
arr.reshape(-1, 4)     # 自动计算行数

# flatten vs ravel
arr2d = np.array([[1, 2], [3, 4]])
arr2d.flatten()   # 返回副本 [1, 2, 3, 4]
arr2d.ravel()     # 返回视图 [1, 2, 3, 4]

# 转置
arr2d.T           # 转置
np.transpose(arr2d)  # 等价写法
```

## 性能优化技巧

1. **避免 Python 循环**：尽量使用 NumPy 内置函数
2. **预分配内存**：用 `np.empty()` 或 `np.zeros()` 预分配数组
3. **就地操作**：使用 `+=`、`*=` 等就地运算符减少内存分配
4. **选择合适的数据类型**：不需要高精度时用 `float32` 而非 `float64`

```python
# 就地操作
arr = np.zeros(1000000)
arr += 1  # 就地加法，不创建新数组

# 合适的数据类型
arr = np.array([1, 2, 3], dtype=np.float32)  # 比 float64 省一半内存
```
