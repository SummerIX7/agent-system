---
title: SciPy 统计分析
source_type: book
source_name: Python数据科学手册
author: Jake VanderPlas
publisher: O'Reilly
year: 2023
chapter: 第4章 数据可视化、第5章 机器学习
---

# SciPy 统计分析

## 概述

SciPy 的 `stats` 模块是 Python 生态中最全面的统计分析工具库，提供了概率分布、假设检验、置信区间估计等功能。在数据分析中，统计检验用于验证数据假设、比较组间差异、评估实验效果等。本文介绍 `scipy.stats` 中最常用的统计分析方法。

## 核心概念

### 概率分布

`scipy.stats` 包含了超过100种连续和离散概率分布，每种分布都支持概率密度函数（PDF）、累积分布函数（CDF）、随机采样等操作。

```python
import numpy as np
from scipy import stats

# 正态分布
norm = stats.norm(loc=0, scale=1)  # 均值0，标准差1
print(f"PDF at 0: {norm.pdf(0):.4f}")      # 0.3989
print(f"CDF at 1.96: {norm.cdf(1.96):.4f}") # 0.9750
print(f"95%分位数: {norm.ppf(0.95):.4f}")   # 1.6449

# 随机采样
samples = norm.rvs(size=1000, random_state=42)
print(f"样本均值: {samples.mean():.4f}")
print(f"样本标准差: {samples.std():.4f}")

# 其他常用分布
t_dist = stats.t(df=10)          # t分布
chi2_dist = stats.chi2(df=5)     # 卡方分布
f_dist = stats.f(dfn=5, dfd=10)  # F分布
poisson_dist = stats.poisson(mu=3)  # 泊松分布

# 拟合分布参数
data = np.random.normal(loc=5, scale=2, size=1000)
loc_fit, scale_fit = stats.norm.fit(data)
print(f"拟合均值: {loc_fit:.4f}, 拟合标准差: {scale_fit:.4f}")
```

### 假设检验

假设检验是统计推断的核心，通过样本数据对总体参数或分布做出判断。常用的检验方法包括 t 检验、卡方检验和非参数检验。

```python
import numpy as np
from scipy import stats

# 单样本 t 检验：检验均值是否等于某值
np.random.seed(42)
sample = np.random.normal(loc=102, scale=15, size=50)
t_stat, p_value = stats.ttest_1samp(sample, popmean=100)
print(f"单样本 t 检验: t={t_stat:.4f}, p={p_value:.4f}")
# 若 p < 0.05，拒绝"均值等于100"的原假设

# 独立双样本 t 检验：比较两组均值
group_a = np.random.normal(loc=100, scale=10, size=30)
group_b = np.random.normal(loc=105, scale=10, size=30)
t_stat, p_value = stats.ttest_ind(group_a, group_b)
print(f"双样本 t 检验: t={t_stat:.4f}, p={p_value:.4f}")

# 配对 t 检验：同一组对象前后对比
before = np.random.normal(loc=130, scale=15, size=20)
after = before - np.random.normal(loc=5, scale=3, size=20)
t_stat, p_value = stats.ttest_rel(before, after)
print(f"配对 t 检验: t={t_stat:.4f}, p={p_value:.4f}")

# 卡方检验：检验分类变量的独立性
observed = np.array([[50, 30, 20], [35, 40, 25]])
chi2, p_value, dof, expected = stats.chi2_contingency(observed)
print(f"卡方检验: chi2={chi2:.4f}, p={p_value:.4f}")

# Mann-Whitney U 检验（非参数检验，不要求正态分布）
u_stat, p_value = stats.mannwhitneyu(group_a, group_b)
print(f"Mann-Whitney U: U={u_stat:.4f}, p={p_value:.4f}")
```

### 置信区间

置信区间提供了参数估计的不确定性范围，比单一的点估计包含更多信息。

```python
import numpy as np
from scipy import stats

data = np.random.normal(loc=50, scale=10, size=100)

# 计算均值的95%置信区间
n = len(data)
mean = np.mean(data)
se = stats.sem(data)  # 标准误差
ci = stats.t.interval(0.95, df=n-1, loc=mean, scale=se)
print(f"均值95%置信区间: [{ci[0]:.2f}, {ci[1]:.2f}]")

# 使用 scipy 内置方法
ci_result = stats.ttest_1samp(data, 0)  # 获取统计量
# 手动计算置信区间
alpha = 0.05
t_critical = stats.t.ppf(1 - alpha/2, df=n-1)
margin = t_critical * se
print(f"置信区间: [{mean - margin:.2f}, {mean + margin:.2f}]")

# 比例的置信区间（二项分布）
successes = 60
trials = 100
proportion = successes / trials
ci_prop = stats.binom.interval(0.95, trials, proportion)
print(f"比例置信区间: [{ci_prop[0]/trials:.4f}, {ci_prop[1]/trials:.4f}]")

# 正态性检验（Shapiro-Wilk）
stat, p_value = stats.shapiro(data)
print(f"Shapiro-Wilk 检验: W={stat:.4f}, p={p_value:.4f}")
# p > 0.05 则不能拒绝正态性假设
```

## 常用函数/方法

```python
# 常用统计检验函数
stats.ttest_1samp(data, popmean)    # 单样本 t 检验
stats.ttest_ind(data1, data2)       # 独立双样本 t 检验
stats.ttest_rel(data1, data2)       # 配对 t 检验
stats.chi2_contingency(table)       # 卡方独立性检验
stats.mannwhitneyu(data1, data2)    # Mann-Whitney U 检验
stats.wilcoxon(data1, data2)        # Wilcoxon 符号秩检验
stats.kruskal(*groups)              # Kruskal-Wallis H 检验
stats.f_oneway(*groups)             # 单因素方差分析

# 正态性检验
stats.shapiro(data)                 # Shapiro-Wilk 检验
stats.normaltest(data)              # D'Agostino-Pearson 检验
stats.kstest(data, "norm")         # Kolmogorov-Smirnov 检验

# 描述性统计
stats.describe(data)                # 综合描述统计
stats.iqr(data)                     # 四分位距
```

## 注意事项

1. t 检验要求数据近似正态分布，样本量较小时（n < 30）需进行正态性检验；不满足正态性时应使用非参数检验。
2. p 值不是效应大小的度量，p 值小不代表实际差异大，应结合效应量（如 Cohen's d）综合判断。
3. 多重比较问题需注意，同时进行多次检验时应使用 Bonferroni 校正等方法控制整体错误率。
4. 置信区间的宽度受样本量和数据变异性影响，样本量越大、变异性越小，置信区间越窄。
