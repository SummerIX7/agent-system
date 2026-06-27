---
title: 探索性数据分析流程
source_type: practice
source_name: 探索性数据分析实战
author: 赵明
publisher: 人民邮电出版社
year: 2020
chapter: 实战指南
---

# 探索性数据分析流程

## 概述

探索性数据分析(EDA)是建模前的关键步骤，通过统计描述和可视化手段理解数据特征、发现规律和问题。本文介绍完整的EDA流程：单变量分析、多变量分析、相关性分析。

## 实操步骤

### 步骤1：数据概览

```python
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# 加载数据
df = pd.read_csv('sales_data.csv')

# 基本信息查看
print(f"数据形状: {df.shape}")
print(f"\n数据类型:\n{df.dtypes}")
print(f"\n前5行:\n{df.head()}")
print(f"\n描述统计:\n{df.describe()}")
print(f"\n缺失值:\n{df.isnull().sum()}")
print(f"\n重复行: {df.duplicated().sum()}")
```

### 步骤2：单变量分析

```python
# 数值变量分析
def analyze_numeric(df, column):
    """数值变量分析函数"""
    print(f"\n=== {column} 分析 ===")
    print(f"均值: {df[column].mean():.2f}")
    print(f"中位数: {df[column].median():.2f}")
    print(f"标准差: {df[column].std():.2f}")
    print(f"偏度: {df[column].skew():.2f}")
    print(f"峰度: {df[column].kurtosis():.2f}")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    sns.histplot(df[column], kde=True, ax=axes[0])
    axes[0].set_title(f'{column} 分布')
    sns.boxplot(x=df[column], ax=axes[1])
    axes[1].set_title(f'{column} 箱线图')
    plt.tight_layout()
    plt.show()

analyze_numeric(df, 'revenue')

# 分类变量分析
def analyze_categorical(df, column):
    """分类变量分析函数"""
    print(f"\n=== {column} 分析 ===")
    print(f"唯一值数量: {df[column].nunique()}")
    print(f"\n频率分布:\n{df[column].value_counts()}")

    plt.figure(figsize=(10, 5))
    sns.countplot(data=df, y=column, order=df[column].value_counts().index)
    plt.title(f'{column} 分布')
    plt.show()

analyze_categorical(df, 'category')
```

### 步骤3：多变量分析

```python
# 数值-数值关系
def analyze_numeric_relationship(df, x, y):
    """分析两个数值变量关系"""
    correlation = df[x].corr(df[y])
    print(f"{x} 与 {y} 相关系数: {correlation:.3f}")

    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=df, x=x, y=y, alpha=0.5)
    sns.regplot(data=df, x=x, y=y, scatter=False, color='red')
    plt.title(f'{x} vs {y} (r={correlation:.3f})')
    plt.show()

analyze_numeric_relationship(df, 'price', 'quantity')

# 数值-分类关系
def analyze_mixed(df, numeric_col, categorical_col):
    """分析数值与分类变量关系"""
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x=categorical_col, y=numeric_col)
    plt.title(f'{numeric_col} by {categorical_col}')
    plt.xticks(rotation=45)
    plt.show()

    # ANOVA检验
    from scipy.stats import f_oneway
    groups = [group[numeric_col].values for name, group in df.groupby(categorical_col)]
    f_stat, p_value = f_oneway(*groups)
    print(f"ANOVA F-statistic: {f_stat:.3f}, p-value: {p_value:.4f}")

analyze_mixed(df, 'revenue', 'region')
```

### 步骤4：相关性分析

```python
# 相关性矩阵
numeric_df = df.select_dtypes(include=[np.number])
corr_matrix = numeric_df.corr()

# 热力图可视化
plt.figure(figsize=(12, 10))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, mask=mask, annot=True, fmt='.2f',
            cmap='coolwarm', center=0, square=True)
plt.title('变量相关性矩阵')
plt.tight_layout()
plt.show()

# 高相关变量筛选
high_corr_pairs = []
for i in range(len(corr_matrix.columns)):
    for j in range(i+1, len(corr_matrix.columns)):
        if abs(corr_matrix.iloc[i, j]) > 0.7:
            high_corr_pairs.append({
                'var1': corr_matrix.columns[i],
                'var2': corr_matrix.columns[j],
                'correlation': corr_matrix.iloc[i, j]
            })
print("高相关变量对:", pd.DataFrame(high_corr_pairs))

# 分组统计分析
summary = df.groupby('category').agg({
    'revenue': ['mean', 'sum', 'count'],
    'quantity': ['mean', 'sum']
}).round(2)
print(summary)
```

## 常见问题与解决方案

1. **问题**：数据量太大绘图慢 **解决**：采样绘制，或使用`plotnine`的高效实现
2. **问题**：分类变量类别太多 **解决**：合并低频类别为"其他"，或使用交互式图表
3. **问题**：相关性不等于因果 **解决**：结合业务背景分析，必要时进行因果推断

## 最佳实践

1. 按照数据概览 -> 单变量 -> 多变量 -> 相关性的顺序进行分析
2. 每一步都记录发现和疑问，形成分析笔记
3. 使用函数封装重复分析逻辑，提高效率
4. EDA结果应形成结论，指导后续特征工程和建模方向
