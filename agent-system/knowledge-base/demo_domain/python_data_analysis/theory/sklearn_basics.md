---
title: 机器学习基础
source_type: book
source_name: 机器学习实战
author: Peter Harrington
publisher: 人民邮电出版社
year: 2023
chapter: 第2章 KNN、第3章 决策树、第4章 朴素贝叶斯
---

# 机器学习基础

## 概述

Scikit-learn（sklearn）是 Python 最流行的机器学习库，提供了统一的 API 接口，覆盖分类、回归、聚类三大任务类型以及丰富的模型评估工具。本文介绍 sklearn 的核心使用流程，包括数据预处理、模型训练、预测和评估等环节。

## 核心概念

### 分类任务

分类是预测离散类别的监督学习任务，常用算法包括 K 近邻（KNN）、决策树、随机森林等。

```python
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report, accuracy_score

# 加载数据集
iris = load_iris()
X, y = iris.data, iris.target

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 特征标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)  # 注意：用训练集参数转换测试集

# KNN 分类
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(X_train_scaled, y_train)
y_pred = knn.predict(X_test_scaled)

print(f"准确率: {accuracy_score(y_test, y_pred):.4f}")
print(classification_report(y_test, y_pred, target_names=iris.target_names))
```

### 回归任务

回归用于预测连续数值，常用算法包括线性回归、岭回归、随机森林回归等。

```python
from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np

# 加载房价数据
housing = fetch_california_housing()
X, y = housing.data, housing.target

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 线性回归
lr = LinearRegression()
lr.fit(X_train, y_train)
y_pred = lr.predict(X_test)

print(f"线性回归 - MSE: {mean_squared_error(y_test, y_pred):.4f}")
print(f"线性回归 - R²: {r2_score(y_test, y_pred):.4f}")

# 岭回归（带正则化）
ridge = Ridge(alpha=1.0)
ridge.fit(X_train, y_train)
y_pred_ridge = ridge.predict(X_test)
print(f"岭回归 - R²: {r2_score(y_test, y_pred_ridge):.4f}")

# 查看特征重要性（随机森林）
rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)
importances = rf.feature_importances_
for name, imp in zip(housing.feature_names, importances):
    print(f"  {name}: {imp:.4f}")
```

### 聚类任务

聚类是无监督学习任务，将数据自动划分为若干组。K-Means 是最常用的聚类算法。

```python
from sklearn.cluster import KMeans, DBSCAN
from sklearn.datasets import make_blobs
from sklearn.metrics import silhouette_score
import numpy as np

# 生成模拟数据
X, y_true = make_blobs(n_samples=300, centers=4, random_state=42)

# K-Means 聚类
kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
labels = kmeans.fit_predict(X)

# 轮廓系数评估聚类质量（越接近1越好）
sil_score = silhouette_score(X, labels)
print(f"轮廓系数: {sil_score:.4f}")

# 肘部法则选择 K 值
inertias = []
K_range = range(2, 10)
for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X)
    inertias.append(km.inertia_)
print("肘部法则 - 各K值的惯性:")
for k, inertia in zip(K_range, inertias):
    print(f"  K={k}: {inertia:.2f}")

# DBSCAN 密度聚类（自动确定簇数量）
dbscan = DBSCAN(eps=0.5, min_samples=5)
db_labels = dbscan.fit_predict(X)
n_clusters = len(set(db_labels)) - (1 if -1 in db_labels else 0)
print(f"DBSCAN 发现的簇数量: {n_clusters}")
```

### 模型评估与选择

合理的模型评估是避免过拟合、选择最优模型的关键。交叉验证和网格搜索是常用的模型选择方法。

```python
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris

X, y = load_iris(return_X_y=True)

# 交叉验证
rf = RandomForestClassifier(n_estimators=100, random_state=42)
scores = cross_val_score(rf, X, y, cv=5, scoring="accuracy")
print(f"5折交叉验证准确率: {scores.mean():.4f} ± {scores.std():.4f}")

# 网格搜索调参
param_grid = {
    "n_estimators": [50, 100, 200],
    "max_depth": [3, 5, 10, None],
    "min_samples_split": [2, 5, 10]
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42),
    param_grid,
    cv=5,
    scoring="accuracy",
    n_jobs=-1
)
grid_search.fit(X, y)

print(f"最优参数: {grid_search.best_params_}")
print(f"最优准确率: {grid_search.best_score_:.4f}")

# 混淆矩阵
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
grid_search.best_estimator_.fit(X_train, y_train)
y_pred = grid_search.best_estimator_.predict(X_test)
cm = confusion_matrix(y_test, y_pred)
print(f"混淆矩阵:\n{cm}")
```

## 常用函数/方法

```python
# sklearn 统一 API 模式
model = SomeModel(hyperparameters)  # 1. 实例化
model.fit(X_train, y_train)         # 2. 训练
y_pred = model.predict(X_test)      # 3. 预测
score = model.score(X_test, y_test) # 4. 评估

# 数据预处理
StandardScaler()                    # 标准化（均值0，方差1）
MinMaxScaler()                      # 归一化（0-1区间）
LabelEncoder()                      # 标签编码
OneHotEncoder()                     # 独热编码
train_test_split(X, y, test_size=0.2)  # 数据划分

# 评估指标
accuracy_score(y_true, y_pred)      # 分类准确率
precision_score(y_true, y_pred)     # 精确率
recall_score(y_true, y_pred)        # 召回率
f1_score(y_true, y_pred)            # F1分数
mean_squared_error(y_true, y_pred)  # 均方误差
r2_score(y_true, y_pred)            # R²决定系数
```

## 注意事项

1. 特征标准化应在训练集上 `fit` 后再 `transform` 测试集，避免数据泄漏导致评估结果虚高。
2. 分类任务中数据类别不平衡时，应使用分层采样（`stratify=y`）和合适的评估指标（如 F1-score），而非单纯依赖准确率。
3. 过拟合表现为训练集表现好但测试集表现差，可通过正则化、减少特征、增加数据量、交叉验证等手段缓解。
4. 无监督学习（如聚类）没有标准答案，应结合业务理解和轮廓系数等指标综合判断聚类质量。
