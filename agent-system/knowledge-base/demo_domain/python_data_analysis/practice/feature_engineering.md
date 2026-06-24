---
title: 特征工程实践
source_type: practice
source_name: 特征工程实战
author: 孙强
publisher: 机械工业出版社
year: 2023
chapter: 实战指南
---

# 特征工程实践

## 概述

特征工程是将原始数据转换为机器学习算法可有效利用的特征的过程，直接影响模型性能。本文介绍三大核心环节：特征编码、特征缩放、特征选择的实用方法。

## 实操步骤

### 步骤1：分类变量编码

```python
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, OrdinalEncoder

df = pd.DataFrame({
    'color': ['red', 'blue', 'green', 'red', 'blue'],
    'size': ['S', 'M', 'L', 'XL', 'M'],
    'price': [100, 200, 150, 300, 250]
})

# 1. 标签编码（有序分类变量）
le = LabelEncoder()
df['size_encoded'] = le.fit_transform(df['size'])
# S=2, M=1, L=0, XL=3（按字母排序）

# 2. 有序编码（指定顺序）
ordinal_encoder = OrdinalEncoder(categories=[['S', 'M', 'L', 'XL']])
df['size_ordinal'] = ordinal_encoder.fit_transform(df[['size']])
# S=0, M=1, L=2, XL=3

# 3. 独热编码（无序分类变量）
df_onehot = pd.get_dummies(df, columns=['color'], prefix='color', drop_first=True)
# drop_first=True 避免多重共线性

# 4. 目标编码（高基数分类变量）
from category_encoders import TargetEncoder
te = TargetEncoder()
df['color_target'] = te.fit_transform(df['color'], df['price'])

# 5. 频率编码
freq_encoding = df['color'].value_counts(normalize=True)
df['color_freq'] = df['color'].map(freq_encoding)
```

### 步骤2：数值特征缩放

```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

# 示例数据
data = np.array([[100, 0.1], [200, 0.5], [150, 0.3], [300, 0.8]])

# 1. 标准化（Z-Score）- 适用于正态分布数据
scaler = StandardScaler()
data_standardized = scaler.fit_transform(data)
# 均值为0，标准差为1

# 2. 归一化（Min-Max）- 适用于有界数据
scaler = MinMaxScaler(feature_range=(0, 1))
data_normalized = scaler.fit_transform(data)

# 3. 鲁棒缩放 - 适用于有异常值的数据
scaler = RobustScaler()
data_robust = scaler.fit_transform(data)
# 使用中位数和四分位距，对异常值不敏感

# 4. 对数变换 - 处理右偏分布
df['log_revenue'] = np.log1p(df['revenue'])  # log(x+1)，避免log(0)

# 5. Box-Cox变换 - 自动选择最佳变换
from scipy.stats import boxcox
df['bc_revenue'], lambda_param = boxcox(df['revenue'] + 1)
```

### 步骤3：特征构造

```python
# 1. 时间特征提取
df['date'] = pd.to_datetime(df['date'])
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['dayofweek'] = df['date'].dt.dayofweek
df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
df['quarter'] = df['date'].dt.quarter

# 2. 交互特征
df['price_quantity'] = df['price'] * df['quantity']
df['price_ratio'] = df['price'] / df['price'].mean()

# 3. 多项式特征
from sklearn.preprocessing import PolynomialFeatures
poly = PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)
poly_features = poly.fit_transform(df[['price', 'quantity']])

# 4. 分箱（Binning）
df['price_bin'] = pd.cut(df['price'], bins=5, labels=['very_low', 'low', 'medium', 'high', 'very_high'])
df['price_qbin'] = pd.qcut(df['price'], q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])

# 5. 文本特征（TF-IDF）
from sklearn.feature_extraction.text import TfidfVectorizer
tfidf = TfidfVectorizer(max_features=100)
text_features = tfidf.fit_transform(df['description'])
```

### 步骤4：特征选择

```python
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.ensemble import RandomForestClassifier

X = df.drop('target', axis=1)
y = df['target']

# 1. 过滤法 - 方差阈值
from sklearn.feature_selection import VarianceThreshold
selector = VarianceThreshold(threshold=0.01)
X_filtered = selector.fit_transform(X)

# 2. 过滤法 - 相关系数
corr_with_target = X.corrwith(y).abs().sort_values(ascending=False)
selected_features = corr_with_target[corr_with_target > 0.1].index.tolist()

# 3. 包裹法 - 递归特征消除
from sklearn.feature_selection import RFE
from sklearn.linear_model import LogisticRegression
rfe = RFE(estimator=LogisticRegression(), n_features_to_select=10)
X_rfe = rfe.fit_transform(X, y)
selected_features = X.columns[rfe.support_].tolist()

# 4. 嵌入法 - 基于模型重要性
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X, y)
importances = pd.Series(rf.feature_importances_, index=X.columns)
top_features = importances.nlargest(15).index.tolist()
```

## 常见问题与解决方案

1. **问题**：独热编码导致维度爆炸 **解决**：使用目标编码或频率编码替代，或限制类别数量
2. **问题**：缩放后丢失原始含义 **解决**：保留原始特征，同时添加缩放版本
3. **特征选择**：过多或过少 **解决**：使用交叉验证评估不同特征子集的模型性能

## 最佳实践

1. 先进行EDA了解数据分布，再选择合适的编码和缩放方法
2. 使用Pipeline封装特征工程流程，避免数据泄露
3. 特征工程需要结合业务领域知识，创造有意义的特征
4. 记录所有特征的来源和含义，便于模型解释
