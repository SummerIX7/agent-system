---
title: 数据清洗实战案例
source_type: practice
source_name: Python数据清洗实战
author: 刘伟
publisher: 电子工业出版社
year: 2021
chapter: 实战指南
---

# 数据清洗实战案例

## 概述

数据清洗是数据分析中最耗时但至关重要的环节，通常占据整个分析流程60%以上的时间。本文通过三个典型场景：缺失值处理、异常值检测、格式转换，展示系统化的数据清洗方法。

## 实操步骤

### 步骤1：缺失值处理

```python
import pandas as pd
import numpy as np

# 创建含缺失值的示例数据
df = pd.DataFrame({
    'name': ['Alice', 'Bob', None, 'David', 'Eve'],
    'age': [25, np.nan, 35, 40, np.nan],
    'salary': [50000, 60000, np.nan, 80000, 55000],
    'city': ['Beijing', None, 'Shanghai', 'Beijing', None]
})

# 1. 检测缺失值
print(df.isnull().sum())  # 每列缺失数量
print(df.isnull().mean())  # 每列缺失比例

# 2. 删除缺失值
df_dropped = df.dropna()  # 删除任何含缺失的行
df_dropped = df.dropna(subset=['age', 'salary'])  # 指定列
df_dropped = df.dropna(thresh=3)  # 保留至少3个非空值的行

# 3. 填充缺失值
df['age'].fillna(df['age'].median(), inplace=True)  # 中位数填充
df['city'].fillna(df['city'].mode()[0], inplace=True)  # 众数填充
df['salary'].fillna(method='ffill', inplace=True)  # 前向填充

# 4. 插值填充（适合时间序列）
df['value'] = df['value'].interpolate(method='linear')

# 5. 使用模型预测填充
from sklearn.impute import KNNImputer
imputer = KNNImputer(n_neighbors=2)
df[['age', 'salary']] = imputer.fit_transform(df[['age', 'salary']])
```

### 步骤2：异常值检测与处理

```python
# 1. 基于统计方法检测（Z-Score）
from scipy import stats
z_scores = np.abs(stats.zscore(df['salary']))
outliers = df[z_scores > 3]  # Z值大于3为异常

# 2. IQR方法（更稳健）
Q1 = df['salary'].quantile(0.25)
Q3 = df['salary'].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR
outliers = df[(df['salary'] < lower_bound) | (df['salary'] > upper_bound)]

# 3. 处理异常值
# 方法1：删除
df_clean = df[(df['salary'] >= lower_bound) & (df['salary'] <= upper_bound)]

# 方法2：截断（Winsorize）
df['salary'] = df['salary'].clip(lower=lower_bound, upper=upper_bound)

# 方法3：替换为边界值
df.loc[df['salary'] > upper_bound, 'salary'] = upper_bound
df.loc[df['salary'] < lower_bound, 'salary'] = lower_bound

# 方法4：标记为异常
df['is_outlier'] = (df['salary'] < lower_bound) | (df['salary'] > upper_bound)
```

### 步骤3：格式转换

```python
# 1. 日期格式转换
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['weekday'] = df['date'].dt.day_name()

# 2. 字符串清洗
df['name'] = df['name'].str.strip()  # 去除首尾空格
df['name'] = df['name'].str.lower()  # 转小写
df['phone'] = df['phone'].str.replace('-', '')  # 去除分隔符

# 3. 数值类型转换
df['price'] = df['price'].astype(str).str.replace(',', '').astype(float)

# 4. 分类变量编码
df['city_code'] = df['city'].astype('category').cat.codes

# 5. 正则表达式清洗
import re
def extract_number(text):
    match = re.search(r'(\d+\.?\d*)', str(text))
    return float(match.group(1)) if match else None

df['quantity'] = df['raw_text'].apply(extract_number)

# 6. 重复值处理
print(f"重复行数: {df.duplicated().sum()}")
df = df.drop_duplicates(subset=['name', 'date'], keep='last')
```

### 步骤4：完整清洗流程

```python
def clean_pipeline(df):
    """数据清洗流水线"""
    df = df.copy()

    # 1. 去除重复
    df = df.drop_duplicates()

    # 2. 处理缺失值
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())

    # 3. 处理异常值
    for col in numeric_cols:
        Q1, Q3 = df[col].quantile([0.25, 0.75])
        IQR = Q3 - Q1
        df[col] = df[col].clip(Q1-1.5*IQR, Q3+1.5*IQR)

    # 4. 格式标准化
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].str.strip().str.lower()

    return df
```

## 常见问题与解决方案

1. **问题**：缺失值填充策略选择不当 **解决**：根据业务逻辑和数据分布选择，数值用中位数，分类用众数
2. **问题**：异常值误判 **解决**：结合业务背景，区分真实异常和数据错误
3. **问题**：日期解析失败 **解决**：使用`errors='coerce'`参数，无效日期变为NaT

## 最佳实践

1. 清洗前保留原始数据副本，便于回溯
2. 记录所有清洗步骤和参数，确保可复现
3. 清洗后进行数据质量检查，验证处理效果
4. 建立清洗规则库，标准化常见问题处理流程
