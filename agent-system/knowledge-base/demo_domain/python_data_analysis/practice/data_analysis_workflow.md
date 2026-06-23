# 数据分析完整流程

## 流程概述

一个完整的数据分析项目通常包含以下步骤：

1. **明确问题**：理解业务需求，确定分析目标
2. **数据收集**：获取相关数据
3. **数据清洗**：处理缺失值、异常值、重复值
4. **探索性分析（EDA）**：了解数据分布和特征
5. **特征工程**：创建、选择、转换特征
6. **建模分析**：选择合适的方法进行分析
7. **结果可视化**：用图表展示发现
8. **得出结论**：撰写分析报告

## 示例：电商用户行为分析

### 1. 数据加载与初步查看

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 加载数据
df = pd.read_csv('user_behavior.csv')

# 初步查看
print(f"数据形状: {df.shape}")
print(f"\n数据类型:\n{df.dtypes}")
print(f"\n前5行:\n{df.head()}")
print(f"\n缺失值:\n{df.isnull().sum()}")
print(f"\n基本统计:\n{df.describe()}")
```

### 2. 数据清洗

```python
# 处理缺失值
df['age'].fillna(df['age'].median(), inplace=True)
df['city'].fillna('未知', inplace=True)

# 处理重复值
print(f"重复行数: {df.duplicated().sum()}")
df.drop_duplicates(inplace=True)

# 处理异常值
df = df[df['age'].between(18, 80)]
df = df[df['purchase_amount'] > 0]

# 类型转换
df['register_date'] = pd.to_datetime(df['register_date'])
df['user_id'] = df['user_id'].astype(str)
```

### 3. 探索性数据分析（EDA）

```python
# 用户年龄分布
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

axes[0].hist(df['age'], bins=30, edgecolor='black')
axes[0].set_title('Age Distribution')
axes[0].set_xlabel('Age')

# 消费金额分布
axes[1].hist(df['purchase_amount'], bins=50, edgecolor='black')
axes[1].set_title('Purchase Amount Distribution')

# 性别分布
gender_counts = df['gender'].value_counts()
axes[2].pie(gender_counts, labels=gender_counts.index, autopct='%1.1f%%')
axes[2].set_title('Gender Distribution')

plt.tight_layout()
plt.show()

# 相关性分析
numeric_cols = df.select_dtypes(include=[np.number])
correlation = numeric_cols.corr()
print(correlation)
```

### 4. 特征工程

```python
# 用户生命周期
df['lifetime_days'] = (pd.Timestamp.now() - df['register_date']).dt.days

# 消费频次
user_frequency = df.groupby('user_id').size().reset_index(name='order_count')

# RFM 模型
rfm = df.groupby('user_id').agg({
    'order_date': lambda x: (pd.Timestamp.now() - x.max()).days,  # Recency
    'order_id': 'count',  # Frequency
    'purchase_amount': 'sum'  # Monetary
}).rename(columns={
    'order_date': 'recency',
    'order_id': 'frequency',
    'purchase_amount': 'monetary'
})

# 用户分层
rfm['R_score'] = pd.qcut(rfm['recency'], 4, labels=[4, 3, 2, 1])
rfm['F_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 4, labels=[1, 2, 3, 4])
rfm['M_score'] = pd.qcut(rfm['monetary'], 4, labels=[1, 2, 3, 4])
```

### 5. 分析与可视化

```python
# 用户价值分层分布
rfm['segment'] = rfm['R_score'].astype(str) + rfm['F_score'].astype(str)
segment_counts = rfm['segment'].value_counts()

plt.figure(figsize=(10, 6))
segment_counts.plot(kind='bar')
plt.title('User Segment Distribution')
plt.xlabel('RFM Segment')
plt.ylabel('Count')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# 月度趋势
df['month'] = df['order_date'].dt.to_period('M')
monthly_stats = df.groupby('month').agg({
    'user_id': 'nunique',
    'purchase_amount': 'sum'
}).rename(columns={'user_id': 'active_users', 'purchase_amount': 'revenue'})

fig, ax1 = plt.subplots(figsize=(12, 6))
ax1.bar(monthly_stats.index.astype(str), monthly_stats['revenue'], alpha=0.7, label='Revenue')
ax1.set_ylabel('Revenue')

ax2 = ax1.twinx()
ax2.plot(monthly_stats.index.astype(str), monthly_stats['active_users'], 'r-o', label='Active Users')
ax2.set_ylabel('Active Users')

plt.title('Monthly Revenue and Active Users')
fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.95))
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

### 6. 结论输出

```python
report = f"""
# 电商用户行为分析报告

## 数据概览
- 总用户数: {df['user_id'].nunique()}
- 总订单数: {len(df)}
- 时间范围: {df['order_date'].min()} ~ {df['order_date'].max()}

## 关键发现
1. 用户平均消费: {rfm['monetary'].mean():.2f} 元
2. 高价值用户占比: {(rfm['segment'] >= '33').mean() * 100:.1f}%
3. 用户复购率: {(rfm['frequency'] > 1).mean() * 100:.1f}%

## 建议
1. 针对高价值用户提供专属服务
2. 对沉默用户进行唤醒营销
3. 提升新用户的首次购买转化
"""
print(report)
```

## 最佳实践

1. **先理解业务**：数据分析的目标是解决业务问题，不是炫技
2. **保持代码可读**：使用有意义的变量名，添加注释
3. **记录发现**：随时记录分析过程中的发现和想法
4. **可复现性**：确保分析流程可以被他人复现
5. **讲故事能力**：用数据讲述一个有说服力的故事
