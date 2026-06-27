---
title: Pandas 分组聚合
source_type: book
source_name: 利用Python进行数据分析
author: Wes McKinney
publisher: O'Reilly
year: 2022
chapter: 第10章
---

# Pandas 分组聚合

## groupby 基础

```python
import pandas as pd

df = pd.DataFrame({
    'department': ['IT', 'HR', 'IT', 'HR', 'IT'],
    'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
    'salary': [8000, 6000, 9000, 6500, 8500],
    'age': [25, 30, 35, 28, 32]
})

# 按部门分组求均值
df.groupby('department')['salary'].mean()

# 多列聚合
df.groupby('department')[['salary', 'age']].mean()

# 多个聚合函数
df.groupby('department')['salary'].agg(['mean', 'max', 'min', 'count'])

# 自定义聚合函数
df.groupby('department')['salary'].agg(lambda x: x.max() - x.min())
```

## 多级分组

```python
df.groupby(['department', 'gender'])['salary'].mean()

# 重置索引方便后续操作
df.groupby('department')['salary'].mean().reset_index()
```

## agg 方法详解

```python
# 不同列不同聚合
df.groupby('department').agg({
    'salary': ['mean', 'max'],
    'age': ['mean', 'min']
})

# 命名聚合
df.groupby('department').agg(
    avg_salary=('salary', 'mean'),
    max_salary=('salary', 'max'),
    avg_age=('age', 'mean')
).reset_index()
```

## transform 方法

transform 返回与原 DataFrame 相同长度的结果，常用于组内标准化。

```python
# 组内标准化
df['salary_zscore'] = df.groupby('department')['salary'].transform(
    lambda x: (x - x.mean()) / x.std()
)

# 组内填充缺失值
df['salary'] = df.groupby('department')['salary'].transform(
    lambda x: x.fillna(x.mean())
)

# 组内排名
df['rank'] = df.groupby('department')['salary'].transform(
    lambda x: x.rank(ascending=False)
)
```

## apply 方法

apply 更灵活，可以返回任意形状的结果。

```python
# 返回每组的 top N
def top_n(group, n=2):
    return group.nlargest(n, 'salary')

df.groupby('department').apply(top_n, n=2)

# 组内计算
df.groupby('department').apply(
    lambda g: pd.Series({
        'avg_salary': g['salary'].mean(),
        'salary_range': g['salary'].max() - g['salary'].min()
    })
)
```

## 透视表（pivot_table）

```python
# 基本透视表
pd.pivot_table(df, values='salary', index='department', aggfunc='mean')

# 多值透视表
pd.pivot_table(df, values='salary', index='department', aggfunc=['mean', 'count'])

# 多级索引透视表
pd.pivot_table(df, values='salary', index='department', columns='gender', aggfunc='mean')

# 填充缺失值
pd.pivot_table(df, values='salary', index='department', columns='gender',
               aggfunc='mean', fill_value=0)

# 边际合计
pd.pivot_table(df, values='salary', index='department', columns='gender',
               aggfunc='mean', margins=True, margins_name='合计')
```

## 交叉表（crosstab）

```python
# 频率交叉表
pd.crosstab(df['department'], df['gender'])

# 带比例
pd.crosstab(df['department'], df['gender'], normalize='index')  # 行比例
pd.crosstab(df['department'], df['gender'], normalize='columns')  # 列比例
```

## 常见聚合场景

```python
# 1. 每组最大值对应的行
df.loc[df.groupby('department')['salary'].idxmax()]

# 2. 组内差值
df['salary_diff'] = df.groupby('department')['salary'].diff()

# 3. 组内累计和
df['cumsum'] = df.groupby('department')['salary'].cumsum()

# 4. 组内百分比
df['pct'] = df['salary'] / df.groupby('department')['salary'].transform('sum') * 100
```
