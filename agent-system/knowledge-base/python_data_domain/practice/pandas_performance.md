---
title: Pandas 性能优化
source_type: practice
source_name: Pandas高性能数据分析
author: 王强
publisher: 机械工业出版社
year: 2023
chapter: 实战指南
---

# Pandas 性能优化

## 概述

处理大规模数据时，Pandas的性能优化至关重要。本文介绍三种核心优化策略：向量化操作替代循环、eval/query表达式优化、内存优化技巧，可将数据处理速度提升数倍甚至数十倍。

## 实操步骤

### 步骤1：向量化操作

向量化是Pandas性能优化的核心，利用NumPy底层C实现避免Python循环：

```python
import pandas as pd
import numpy as np

# 低效方式：使用循环
df = pd.DataFrame({'A': range(1000000), 'B': range(1000000)})
result = []
for i in range(len(df)):
    result.append(df.iloc[i]['A'] + df.iloc[i]['B'])
df['C'] = result

# 高效方式：向量化操作（快100倍以上）
df['C'] = df['A'] + df['B']

# 条件计算向量化
# 低效：使用apply
df['category'] = df['A'].apply(lambda x: 'high' if x > 500 else 'low')

# 高效：使用np.where或np.select
df['category'] = np.where(df['A'] > 500, 'high', 'low')

# 多条件使用np.select
conditions = [df['A'] < 100, df['A'] < 500, df['A'] >= 500]
choices = ['low', 'medium', 'high']
df['category'] = np.select(conditions, choices)
```

### 步骤2：eval 和 query 表达式

Pandas提供的高性能表达式引擎，减少中间变量内存分配：

```python
# 使用eval进行列运算
# 传统方式（创建多个临时Series）
df['D'] = df['A'] + df['B'] * df['C']

# 使用eval（内存效率更高）
df.eval('D = A + B * C', inplace=True)

# eval支持局部变量
threshold = 100
df.eval('E = A > @threshold', inplace=True)

# 使用query进行行筛选
# 传统方式
filtered = df[(df['A'] > 100) & (df['B'] < 500)]

# 使用query（更简洁，大数据时更快）
filtered = df.query('A > 100 and B < 500')

# query支持变量引用
min_val = 100
max_val = 500
filtered = df.query('@min_val < A < @max_val')
```

### 步骤3：内存优化

合理选择数据类型可大幅减少内存占用：

```python
# 查看内存使用
print(df.info(memory_usage='deep'))

# 优化数值类型
df['int_col'] = df['int_col'].astype('int32')  # 默认int64
df['float_col'] = df['float_col'].astype('float32')

# 优化字符串为category类型（适用于低基数列）
df['category_col'] = df['category_col'].astype('category')

# 批量优化函数
def optimize_memory(df):
    for col in df.columns:
        col_type = df[col].dtype
        if col_type == 'int64':
            if df[col].max() < 2**31:
                df[col] = df[col].astype('int32')
        elif col_type == 'float64':
            df[col] = df[col].astype('float32')
        elif col_type == 'object':
            if df[col].nunique() / len(df) < 0.5:
                df[col] = df[col].astype('category')
    return df

# 使用Chunking处理大文件
chunks = pd.read_csv('large.csv', chunksize=10000)
result = pd.concat([chunk.groupby('key').sum() for chunk in chunks])
```

### 步骤4：其他优化技巧

```python
# 1. 使用适当的方法
# 频繁查找用map而非apply
mapping = {'A': 1, 'B': 2, 'C': 3}
df['code'] = df['type'].map(mapping)

# 2. 避免链式索引
# 错误：df[df['A']>0]['B'] = 1
# 正确：df.loc[df['A']>0, 'B'] = 1

# 3. 使用swifter加速apply
import swifter
df['result'] = df['data'].swifter.apply(complex_function)
```

## 常见问题与解决方案

1. **问题**：内存溢出 **解决**：使用chunking分块读取，优化数据类型，及时删除临时变量
2. **问题**：eval/query报错 **解决**：检查列名是否与Python关键字冲突，使用反引号包裹
3. **问题**：向量化后结果不一致 **解决**：检查NaN处理逻辑，使用fill_value参数

## 最佳实践

1. 优先使用内置向量化方法，避免Python循环
2. 大数据集读取时指定dtype，避免自动推断
3. 定期使用memory_profiler监控内存使用
4. 考虑使用polars或dask处理超大规模数据
