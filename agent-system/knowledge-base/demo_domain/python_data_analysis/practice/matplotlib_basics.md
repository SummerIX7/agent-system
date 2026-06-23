---
title: Matplotlib 基础图表
source_type: book
source_name: Python数据科学手册
author: Jake VanderPlas
publisher: O'Reilly
year: 2023
chapter: 第4章
---

# Matplotlib 基础图表

## 概述

Matplotlib 是 Python 最基础的绑图库，pyplot 模块提供了类似 MATLAB 的绑图接口。

## 折线图

```python
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y1, label='sin(x)', color='blue', linewidth=2)
plt.plot(x, y2, label='cos(x)', color='red', linewidth=2, linestyle='--')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Sine and Cosine')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

## 柱状图

```python
categories = ['A', 'B', 'C', 'D']
values = [23, 45, 56, 78]

plt.figure(figsize=(8, 5))
plt.bar(categories, values, color=['#3498db', '#2ecc71', '#e74c3c', '#f39c12'])
plt.xlabel('Category')
plt.ylabel('Value')
plt.title('Bar Chart')

# 在柱子上方显示数值
for i, v in enumerate(values):
    plt.text(i, v + 1, str(v), ha='center', fontweight='bold')

plt.show()
```

## 散点图

```python
x = np.random.rand(50)
y = np.random.rand(50)
colors = np.random.rand(50)
sizes = 1000 * np.random.rand(50)

plt.figure(figsize=(8, 6))
plt.scatter(x, y, c=colors, s=sizes, alpha=0.5, cmap='viridis')
plt.colorbar(label='Color Value')
plt.xlabel('X')
plt.ylabel('Y')
plt.title('Scatter Plot')
plt.show()
```

## 饼图

```python
labels = ['Python', 'Java', 'C++', 'JavaScript']
sizes = [35, 25, 20, 20]
colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12']
explode = (0.1, 0, 0, 0)  # 突出第一块

plt.figure(figsize=(8, 8))
plt.pie(sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.1f%%', shadow=True, startangle=90)
plt.title('Programming Language Usage')
plt.show()
```

## 直方图

```python
data = np.random.randn(1000)

plt.figure(figsize=(8, 5))
plt.hist(data, bins=30, edgecolor='black', alpha=0.7)
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.title('Histogram')
plt.axvline(data.mean(), color='red', linestyle='--', label=f'Mean: {data.mean():.2f}')
plt.legend()
plt.show()
```

## 箱线图

```python
data = [np.random.normal(0, std, 100) for std in range(1, 4)]

plt.figure(figsize=(8, 5))
plt.boxplot(data, labels=['std=1', 'std=2', 'std=3'])
plt.ylabel('Value')
plt.title('Box Plot')
plt.show()
```

## 保存图片

```python
plt.savefig('figure.png', dpi=300, bbox_inches='tight')
plt.savefig('figure.pdf', bbox_inches='tight')
plt.savefig('figure.svg', bbox_inches='tight')
```

## 常用设置

```python
# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows
plt.rcParams['axes.unicode_minus'] = False

# 设置风格
plt.style.use('seaborn-v0_8')  # 或 'ggplot', 'bmh', 'dark_background'

# 设置图片大小
plt.figure(figsize=(12, 8))
```
