---
title: Pandas 数据清洗
source_type: book
source_name: 利用Python进行数据分析
author: Wes McKinney
publisher: O'Reilly
year: 2022
chapter: 第7章
---

# Pandas 数据清洗

## 缺失值处理

### 检测缺失值

```python
import pandas as pd
import numpy as np

df = pd.DataFrame({
    'name': ['Alice', 'Bob', None, 'David'],
    'age': [25, np.nan, 35, 40],
    'city': ['Beijing', 'Shanghai', 'Guangzhou', None]
})

# 检测缺失值
df.isnull()          # 布尔 DataFrame
df.notnull()         # 反向
df.isnull().sum()    # 每列缺失值数量
df.isnull().sum().sum()  # 总缺失值数量

# 缺失值比例
df.isnull().mean() * 100
```

### 删除缺失值

```python
df.dropna()                    # 删除任何含缺失值的行
df.dropna(axis=1)              # 删除任何含缺失值的列
df.dropna(subset=['age'])      # 只看 age 列
df.dropna(thresh=2)            # 至少有2个非空值才保留
```

### 填充缺失值

```python
df.fillna(0)                           # 用 0 填充
df.fillna({'age': 0, 'city': '未知'})   # 按列指定填充值
df['age'].fillna(df['age'].mean())     # 用均值填充
df['age'].fillna(df['age'].median())   # 用中位数填充
df['city'].fillna(method='ffill')      # 前向填充
df['city'].fillna(method='bfill')      # 后向填充
df.interpolate()                       # 线性插值
```

## 重复值处理

```python
# 检测重复值
df.duplicated()                        # 布尔 Series
df.duplicated(subset=['name'])         # 按指定列检测
df.duplicated().sum()                  # 重复行数量

# 删除重复值
df.drop_duplicates()                   # 删除完全重复的行
df.drop_duplicates(subset=['name'])    # 按指定列去重
df.drop_duplicates(keep='last')        # 保留最后一条
df.drop_duplicates(keep=False)         # 删除所有重复项
```

## 数据类型转换

```python
# 查看类型
df.dtypes

# 转换类型
df['age'] = df['age'].astype(int)
df['age'] = pd.to_numeric(df['age'], errors='coerce')  # 无法转换的变为 NaN
df['date'] = pd.to_datetime(df['date'])
df['category'] = df['category'].astype('category')

# 类型推断
pd.to_numeric(df['col'], downcast='integer')   # 自动选择最小整数类型
pd.to_numeric(df['col'], downcast='float')     # 自动选择最小浮点类型
```

## 字符串处理

```python
# str 访问器
df['name'].str.lower()           # 转小写
df['name'].str.upper()           # 转大写
df['name'].str.strip()           # 去除首尾空格
df['name'].str.len()             # 字符串长度
df['name'].str.contains('li')    # 包含检测
df['name'].str.startswith('A')   # 前缀检测
df['name'].str.replace('a', 'A') # 替换
df['name'].str.split(' ')        # 分割

# 提取
df['email'].str.extract(r'@(.+)$')  # 正则提取域名
```

## 异常值处理

```python
# 方法1：IQR（四分位距）
Q1 = df['age'].quantile(0.25)
Q3 = df['age'].quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR
df_clean = df[(df['age'] >= lower) & (df['age'] <= upper)]

# 方法2：Z-score
from scipy import stats
z_scores = np.abs(stats.zscore(df['age']))
df_clean = df[z_scores < 3]

# 方法3：截断（Winsorize）
df['age'] = df['age'].clip(lower=18, upper=65)
```

## 数据清洗流程

1. **查看数据**：`df.info()`, `df.describe()`, `df.head()`
2. **处理缺失值**：删除或填充
3. **处理重复值**：`drop_duplicates()`
4. **类型转换**：确保每列类型正确
5. **处理异常值**：检测并处理极端值
6. **标准化**：统一格式（大小写、空格、日期格式等）
