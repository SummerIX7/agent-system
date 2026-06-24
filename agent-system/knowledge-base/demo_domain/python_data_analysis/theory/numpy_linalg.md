---
title: 线性代数运算
source_type: book
source_name: Python数据科学手册
author: Jake VanderPlas
publisher: O'Reilly
year: 2023
chapter: 第2章 NumPy入门
---

# 线性代数运算

## 概述

线性代数是数据科学和机器学习的数学基础，NumPy 的 `linalg` 子模块提供了高效的矩阵运算、特征值分解、线性方程组求解等功能。相比纯 Python 实现，NumPy 底层调用优化的 BLAS/LAPACK 库，运算速度可提升数十倍。本文介绍 NumPy 中线性代数运算的核心方法。

## 核心概念

### 矩阵基本运算

NumPy 使用二维数组（ndarray）表示矩阵，支持矩阵加法、乘法、转置等基本运算，通过 `@` 运算符或 `np.dot()` 实现矩阵乘法。

```python
import numpy as np

# 创建矩阵
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

# 矩阵加法
C = A + B
print(C)
# [[ 6  8]
#  [10 12]]

# 矩阵乘法（三种方式）
D = A @ B                # 推荐方式
D = np.dot(A, B)         # 函数方式
D = A.dot(B)             # 方法方式

print(D)
# [[19 22]
#  [43 50]]

# 逐元素乘法（Hadamard积）
E = A * B

# 矩阵转置
A_T = A.T
print(A_T)
# [[1 3]
#  [2 4]]

# 矩阵的迹（对角线元素之和）
trace = np.trace(A)
print(trace)  # 5

# 矩阵行列式
det = np.linalg.det(A)
print(det)    # -2.0
```

### 特征值与特征向量

特征值分解是许多机器学习算法（如 PCA）的核心步骤。`np.linalg.eig()` 返回矩阵的特征值和对应的特征向量。

```python
import numpy as np

# 特征值分解
A = np.array([[4, -2],
              [1,  1]])

eigenvalues, eigenvectors = np.linalg.eig(A)
print(f"特征值: {eigenvalues}")       # [3. 2.]
print(f"特征向量:\n{eigenvectors}")

# 验证: A @ v = lambda * v
for i in range(len(eigenvalues)):
    lhs = A @ eigenvectors[:, i]
    rhs = eigenvalues[i] * eigenvectors[:, i]
    print(f"验证特征值 {eigenvalues[i]}: {np.allclose(lhs, rhs)}")

# 对称矩阵的特征值分解（更快、更稳定）
S = np.array([[2, 1], [1, 2]])
eigenvalues, eigenvectors = np.linalg.eigh(S)  # 专用于对称矩阵
print(f"对称矩阵特征值: {eigenvalues}")  # [1. 3.]

# 奇异值分解（SVD）
U, S_vals, Vt = np.linalg.svd(A, full_matrices=False)
print(f"奇异值: {S_vals}")
# 通过 SVD 重构矩阵
A_reconstructed = U @ np.diag(S_vals) @ Vt
print(f"重构误差: {np.linalg.norm(A - A_reconstructed):.10f}")
```

### 求解线性方程组

线性方程组 Ax = b 的求解是科学计算的基本任务，`np.linalg.solve()` 提供了高效且数值稳定的求解方法。

```python
import numpy as np

# 求解 Ax = b
A = np.array([[3, 1],
              [1, 2]])
b = np.array([9, 8])

x = np.linalg.solve(A, b)
print(f"解: x = {x}")  # [2.  3.]

# 验证
print(f"验证: {A @ x}")  # [9. 8.]

# 求解多个右侧向量（批量求解）
B = np.array([[9, 5],
              [8, 6]])
X = np.linalg.solve(A, B)
print(f"批量解:\n{X}")

# 求逆矩阵
A_inv = np.linalg.inv(A)
# 用逆矩阵求解（数值上不如 solve 稳定）
x_via_inv = A_inv @ b
print(f"逆矩阵求解: {x_via_inv}")

# 伪逆（适用于非方阵或奇异矩阵）
# 最小二乘问题: min ||Ax - b||^2
A_tall = np.array([[1, 1], [1, 2], [1, 3]])
b_tall = np.array([1, 2, 2.5])
x_lstsq = np.linalg.lstsq(A_tall, b_tall, rcond=None)[0]
print(f"最小二乘解: {x_lstsq}")
```

## 常用函数/方法

```python
# numpy.linalg 模块常用函数
np.linalg.det(A)          # 行列式
np.linalg.inv(A)          # 逆矩阵
np.linalg.pinv(A)         # 伪逆（Moore-Penrose）
np.linalg.matrix_rank(A)  # 矩阵的秩
np.linalg.norm(A)         # 矩阵/向量范数
np.linalg.eig(A)          # 特征值分解
np.linalg.eigh(A)         # 对称矩阵特征值分解
np.linalg.svd(A)          # 奇异值分解
np.linalg.solve(A, b)     # 解线性方程组
np.linalg.lstsq(A, b)    # 最小二乘解
np.linalg.cholesky(A)     # Cholesky 分解（正定矩阵）

# 矩阵范数
np.linalg.norm(A, ord=1)      # 1-范数
np.linalg.norm(A, ord=np.inf) # 无穷范数
np.linalg.norm(A, ord="fro")  # Frobenius范数
```

## 注意事项

1. 求解线性方程组优先使用 `np.linalg.solve()` 而非手动计算逆矩阵再相乘，前者数值稳定性更好且速度更快。
2. `np.linalg.eig()` 返回的特征向量按列排列，提取第 i 个特征向量应使用 `eigenvectors[:, i]`。
3. 对于大规模稀疏矩阵，应使用 `scipy.sparse.linalg` 模块而非 `numpy.linalg`，前者针对稀疏结构进行了优化。
4. 浮点运算存在精度误差，判断矩阵是否相等时应使用 `np.allclose()` 而非 `==` 运算符。
