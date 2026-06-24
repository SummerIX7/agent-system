---
title: 数据可视化原则
source_type: book
source_name: 数据可视化实战
author: 谢彦麒
publisher: 电子工业出版社
year: 2022
chapter: 第1章 可视化概述、第3章 图表设计
---

# 数据可视化原则

## 概述

数据可视化是将数据转化为图形表示的过程，其核心目的是帮助人们更高效地理解数据中的模式、趋势和异常。好的可视化不仅需要正确的图表选择，还需要遵循设计原则来确保信息传达的准确性和有效性。本文介绍图表选择策略、设计原则以及 Python 中的常用可视化方法。

## 核心概念

### 图表选择策略

不同类型的数据关系适合不同的图表形式。选择图表时应首先明确分析目的：是比较、分布、组成还是关系。

```python
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体支持
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# 比较关系 - 柱状图
categories = ["产品A", "产品B", "产品C", "产品D", "产品E"]
values = [120, 98, 156, 88, 135]

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 柱状图：比较不同类别的数值
axes[0, 0].bar(categories, values, color="steelblue")
axes[0, 0].set_title("各类别销售额对比")
axes[0, 0].set_ylabel("销售额（万元）")

# 折线图：展示时间趋势
months = [f"{i}月" for i in range(1, 13)]
trend = [80, 85, 92, 88, 95, 102, 98, 110, 105, 115, 120, 130]
axes[0, 1].plot(months, trend, marker="o", color="coral")
axes[0, 1].set_title("月度销售趋势")
axes[0, 1].tick_params(axis="x", rotation=45)

# 散点图：展示两个变量的关系
np.random.seed(42)
x = np.random.normal(50, 15, 100)
y = 0.8 * x + np.random.normal(0, 10, 100)
axes[1, 0].scatter(x, y, alpha=0.6, color="green")
axes[1, 0].set_title("广告投入与销售额关系")
axes[1, 0].set_xlabel("广告投入（万元）")
axes[1, 0].set_ylabel("销售额（万元）")

# 直方图：展示数据分布
data = np.random.normal(100, 15, 500)
axes[1, 1].hist(data, bins=20, color="purple", alpha=0.7, edgecolor="white")
axes[1, 1].set_title("成绩分布")
axes[1, 1].set_xlabel("分数")
axes[1, 1].set_ylabel("频次")

plt.tight_layout()
plt.savefig("chart_selection.png", dpi=150)
plt.show()
```

### 设计原则

优秀的数据可视化应遵循准确性、简洁性、一致性和可读性四项基本原则。

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# 原则一：准确性 - 不扭曲数据
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

categories = ["A", "B", "C", "D"]
values = [25, 30, 28, 32]

# 错误示范：Y轴不从0开始，夸大差异
ax1.bar(categories, values)
ax1.set_ylim(20, 35)
ax1.set_title("误导：Y轴截断（不推荐）")

# 正确示范：Y轴从0开始
ax2.bar(categories, values, color="steelblue")
ax2.set_ylim(0, 40)
ax2.set_title("准确：Y轴从0开始（推荐）")

plt.tight_layout()
plt.savefig("design_accuracy.png", dpi=150)
plt.show()

# 原则二：简洁性 - 去除不必要的装饰
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# 过度装饰
ax1.bar(categories, values, color=["red", "blue", "green", "orange"])
ax1.set_title("过度装饰（不推荐）")
ax1.grid(True, linestyle="--", alpha=0.5)
ax1.set_facecolor("#f0f0f0")

# 简洁设计
ax2.bar(categories, values, color="steelblue")
ax2.set_title("简洁设计（推荐）")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

plt.tight_layout()
plt.savefig("design_simplicity.png", dpi=150)
plt.show()
```

### 配色与标注

合理的配色方案和清晰的标注能显著提升图表的可读性和信息传达效率。

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# 配色方案示例
fig, ax = plt.subplots(figsize=(10, 6))

months = [f"{i}月" for i in range(1, 7)]
product_a = [120, 135, 148, 142, 155, 168]
product_b = [95, 108, 115, 125, 118, 130]
product_c = [80, 75, 88, 92, 98, 105]

# 使用协调的配色
ax.plot(months, product_a, marker="o", label="产品A", color="#2196F3", linewidth=2)
ax.plot(months, product_b, marker="s", label="产品B", color="#FF9800", linewidth=2)
ax.plot(months, product_c, marker="^", label="产品C", color="#4CAF50", linewidth=2)

# 数据标注
for i, (a, b, c) in enumerate(zip(product_a, product_b, product_c)):
    if i == len(months) - 1:
        ax.annotate(f"{a}", (i, a), textcoords="offset points",
                   xytext=(10, 0), fontsize=10, color="#2196F3")
        ax.annotate(f"{b}", (i, b), textcoords="offset points",
                   xytext=(10, 0), fontsize=10, color="#FF9800")
        ax.annotate(f"{c}", (i, c), textcoords="offset points",
                   xytext=(10, 0), fontsize=10, color="#4CAF50")

ax.set_title("上半年产品销售趋势", fontsize=14, fontweight="bold")
ax.set_ylabel("销售额（万元）")
ax.legend(loc="upper left")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()
plt.savefig("design_color.png", dpi=150)
plt.show()
```

## 常用函数/方法

```python
# Matplotlib 核心函数
plt.figure(figsize=(10, 6))         # 创建画布
fig, ax = plt.subplots(2, 2)        # 创建子图网格
ax.plot(x, y)                       # 折线图
ax.bar(x, y)                        # 柱状图
ax.scatter(x, y)                    # 散点图
ax.hist(data, bins=20)             # 直方图
ax.boxplot(data)                    # 箱线图
ax.pie(sizes, labels=labels)       # 饼图
ax.set_title("标题")               # 设置标题
ax.set_xlabel("X轴")               # 设置X轴标签
ax.legend()                         # 显示图例
plt.tight_layout()                  # 自动调整间距
plt.savefig("fig.png", dpi=150)    # 保存图片

# Seaborn 高级统计图
import seaborn as sns
sns.heatmap(corr_matrix, annot=True)  # 热力图
sns.boxplot(x="group", y="value", data=df)  # 分组箱线图
sns.violinplot(x="group", y="value", data=df)  # 小提琴图
sns.pairplot(df, hue="category")  # 变量关系矩阵图
```

## 注意事项

1. 避免使用3D效果和过多装饰元素，这些会扭曲数据感知并分散注意力，应优先使用2D平面图表。
2. 饼图仅适用于展示少量类别（不超过5-6个）的占比关系，类别过多时应改用柱状图。
3. 配色应考虑色盲友好性，避免仅依赖红绿对比区分数据，可使用 ColorBrewer 等工具选择无障碍配色方案。
4. 图表标题、坐标轴标签和图例应清晰完整，确保读者无需额外说明即可理解图表所传达的信息。
