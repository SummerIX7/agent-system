---
title: Pandas 基础
source_type: book
source_name: 利用Python进行数据分析
author: Wes McKinney
publisher: O'Reilly
year: 2022
chapter: 第5章
---

# Pandas 基础

## 概述

Pandas 是 Python 数据分析的核心库，提供了 DataFrame 和 Series 两种核心数据结构，用于高效处理结构化数据。

## 核心数据结构

### Series

Series 是带标签的一维数组，类似于 Python 的字典和 NumPy 数组的结合。

```python
import pandas as pd

# 创建 Series
s = pd.Series([1, 3, 5, 7, 9])
s = pd.Series([1, 3, 5], index=['a', 'b', 'c'])
s = pd.Series({'a': 1, 'b': 3, 'c': 5})

# 访问
s['a']      # 通过标签访问
s[0]        # 通过位置访问
s[['a', 'c']]  # 多个值
```

### DataFrame

DataFrame 是带标签的二维表格，是 Pandas 最常用的数据结构。

```python
# 创建 DataFrame
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'city': ['Beijing', 'Shanghai', 'Guangzhou']
})

# 从字典列表创建
data = [
    {'name': 'Alice', 'age': 25},
    {'name': 'Bob', 'age': 30}
]
df = pd.DataFrame(data)

# 从 CSV 文件创建
df = pd.read_csv('data.csv')
df = pd.read_csv('data.csv', encoding='utf-8', index_col=0)
```

## 基本操作

### 查看数据

```python
df.head()        # 前5行
df.tail()        # 后5行
df.shape         # 形状 (行数, 列数)
df.info()        # 列信息、数据类型、非空数量
df.describe()    # 数值列的统计摘要
df.dtypes        # 各列数据类型
df.columns       # 列名
df.index         # 索引
df.values        # 底层 NumPy 数组
```

### 选择数据

```python
# 选择列
df['name']           # 单列（返回 Series）
df[['name', 'age']]  # 多列（返回 DataFrame）

# 选择行（loc - 基于标签）
df.loc[0]              # 第0行
df.loc[0:2]            # 第0到2行（包含2）
df.loc[0:2, 'name']    # 第0到2行的 name 列

# 选择行（iloc - 基于位置）
df.iloc[0]             # 第0行
df.iloc[0:2]           # 第0到1行（不包含2）
df.iloc[0:2, 0]        # 第0到1行的第0列

# 布尔索引
df[df['age'] > 25]                    # age > 25 的行
df[(df['age'] > 25) & (df['city'] == 'Beijing')]  # 多条件
```

### 添加/删除列

```python
# 添加列
df['salary'] = [5000, 6000, 7000]
df['bonus'] = df['salary'] * 0.1

# 删除列
df.drop('bonus', axis=1, inplace=True)

# 删除行
df.drop(0, axis=0, inplace=True)
```

### 排序

```python
df.sort_values('age')                    # 按 age 升序
df.sort_values('age', ascending=False)   # 按 age 降序
df.sort_values(['age', 'salary'])        # 多列排序
```

## 数据读写

```python
# CSV
df = pd.read_csv('data.csv')
df.to_csv('output.csv', index=False, encoding='utf-8-sig')

# Excel
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')
df.to_excel('output.xlsx', index=False)

# JSON
df = pd.read_json('data.json')
df.to_json('output.json', orient='records', force_ascii=False)

# SQL
from sqlalchemy import create_engine
engine = create_engine('mysql+pymysql://user:pass@host/db')
df = pd.read_sql('SELECT * FROM table_name', engine)
df.to_sql('table_name', engine, if_exists='replace', index=False)
```

## 常见陷阱

1. **链式赋值警告**：`df[df['age'] > 25]['name'] = 'New'` 会报警告，应使用 `df.loc[df['age'] > 25, 'name'] = 'New'`
2. **SettingWithCopyWarning**：使用 `.loc` 避免此警告
3. **数据类型问题**：读取 CSV 时所有列可能被识别为 object，需要手动转换
