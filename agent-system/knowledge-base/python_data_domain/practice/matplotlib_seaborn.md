---
title: Seaborn 高级可视化
source_type: practice
source_name: Python数据可视化实战
author: 陈静
publisher: 人民邮电出版社
year: 2022
chapter: 实战指南
---

# Seaborn 高级可视化

## 概述

Seaborn是基于Matplotlib的高级统计可视化库，提供了简洁的API和美观的默认样式。本文重点介绍三类核心图表：分布图、关系图、分类图的绘制方法和定制技巧。

## 实操步骤

### 步骤1：分布图绘制

用于展示数据分布特征，包括直方图、核密度图、经验分布图：

```python
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# 加载示例数据
tips = sns.load_dataset('tips')

# 单变量分布：直方图+核密度估计
sns.histplot(data=tips, x='total_bill', kde=True, bins=30)
plt.title('账单金额分布')
plt.show()

# 核密度图（KDE）
sns.kdeplot(data=tips, x='total_bill', hue='time', fill=True, alpha=0.5)
plt.title('不同时间段账单分布')
plt.show()

# 双变量分布
sns.jointplot(data=tips, x='total_bill', y='tip', kind='hex')
plt.show()

# 成对分布矩阵
sns.pairplot(tips, hue='day', diag_kind='kde')
plt.show()
```

### 步骤2：关系图绘制

展示变量间的相关性和趋势：

```python
# 散点图+回归线
sns.lmplot(data=tips, x='total_bill', y='tip', hue='smoker',
           col='time', row='sex', height=4)
plt.show()

# 散点图（更灵活的控制）
sns.scatterplot(data=tips, x='total_bill', y='tip',
                hue='day', size='size', style='time',
                sizes=(20, 200))
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()

# 线图（适合时间序列）
fmri = sns.load_dataset('fmri')
sns.lineplot(data=fmri, x='timepoint', y='signal',
             hue='event', style='region', ci=95)
plt.title('fMRI信号变化趋势')
plt.show()

# 热力图（相关性矩阵）
corr = tips.select_dtypes(include=[np.number]).corr()
sns.heatmap(corr, annot=True, cmap='coolwarm', center=0,
            square=True, linewidths=1)
plt.title('变量相关性热力图')
plt.show()
```

### 步骤3：分类图绘制

展示不同类别数据的分布和比较：

```python
# 箱线图
sns.boxplot(data=tips, x='day', y='total_bill', hue='sex',
            palette='Set2')
plt.title('不同性别每日消费分布')
plt.show()

# 小提琴图（箱线图+核密度）
sns.violinplot(data=tips, x='day', y='total_bill', hue='sex',
               split=True, inner='quartile')
plt.show()

# 条形图（带置信区间）
sns.barplot(data=tips, x='day', y='total_bill', hue='sex',
            estimator=np.mean, ci=95)
plt.title('平均消费金额')
plt.show()

# 计数图
sns.countplot(data=tips, x='day', hue='sex')
plt.title('每日就餐人数统计')
plt.show()

# 分类散点图
sns.stripplot(data=tips, x='day', y='total_bill', jitter=True,
              alpha=0.5)
sns.swarmplot(data=tips, x='day', y='total_bill', color='black',
              size=3)
plt.show()
```

### 步骤4：样式和主题定制

```python
# 设置主题风格
sns.set_theme(style='whitegrid',  # darkgrid, whitegrid, dark, white, ticks
              palette='deep',      # 颜色方案
              font='sans-serif',   # 字体
              font_scale=1.1)      # 字体缩放

# 自定义调色板
sns.set_palette('husl', 8)  # 预设方案
custom_palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
sns.set_palette(custom_palette)

# FacetGrid多面板图
g = sns.FacetGrid(tips, col='time', row='sex', margin_titles=True)
g.map_dataframe(sns.histplot, x='total_bill', kde=True)
g.set_axis_labels('账单金额', '频次')
g.set_titles(col_template='{col_name}时段', row_template='{row_name}')
plt.show()

# 保存高清图片
sns.savefig('chart.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
```

## 常见问题与解决方案

1. **问题**：中文显示乱码 **解决**：设置`plt.rcParams['font.sans-serif'] = ['SimHei']`
2. **问题**：图例遮挡图表 **解决**：使用`bbox_to_anchor`调整图例位置
3. **问题**：Seaborn与Matplotlib混用冲突 **解决**：明确使用`ax`参数传递坐标轴对象

## 最佳实践

1. 探索阶段使用Seaborn快速出图，定制阶段结合Matplotlib精细调整
2. 根据数据类型选择合适的图表：分布用histplot/kdeplot，关系用scatterplot/lineplot
3. 使用FacetGrid进行多维度对比分析
4. 保持配色一致性，使用同一调色板系列
