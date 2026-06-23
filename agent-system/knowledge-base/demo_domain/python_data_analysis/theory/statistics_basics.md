# 统计学基础

## 描述统计

### 集中趋势

```python
import numpy as np
import pandas as pd

data = [23, 25, 28, 30, 32, 35, 38, 40, 42, 45]

# 均值（Mean）
mean = np.mean(data)  # 33.8

# 中位数（Median）
median = np.median(data)  # 33.5

# 众数（Mode）
from scipy import stats
mode = stats.mode(data)  # 出现最频繁的值
```

### 离散趋势

```python
# 极差（Range）
data_range = max(data) - min(data)  # 22

# 方差（Variance）
variance = np.var(data)  # 总体方差
variance_sample = np.var(data, ddof=1)  # 样本方差

# 标准差（Standard Deviation）
std = np.std(data)  # 总体标准差
std_sample = np.std(data, ddof=1)  # 样本标准差

# 四分位距（IQR）
Q1 = np.percentile(data, 25)
Q3 = np.percentile(data, 75)
IQR = Q3 - Q1

# 变异系数（CV）
cv = std / mean  # 标准差/均值，用于比较不同量纲的离散程度
```

### 分布形状

```python
# 偏度（Skewness）
from scipy.stats import skew
skewness = skew(data)
# skewness > 0：右偏（正偏）
# skewness < 0：左偏（负偏）
# skewness ≈ 0：对称

# 峰度（Kurtosis）
from scipy.stats import kurtosis
kurt = kurtosis(data)
# kurt > 0：尖峰（重尾）
# kurt < 0：平峰（轻尾）
# kurt ≈ 0：正态分布
```

## 常见概率分布

### 正态分布（Normal Distribution）

```python
from scipy.stats import norm

# 概率密度函数
x = np.linspace(-4, 4, 100)
pdf = norm.pdf(x, loc=0, scale=1)  # 均值0，标准差1

# 累积分布函数
cdf = norm.cdf(x, loc=0, scale=1)

# 分位数函数
q = norm.ppf(0.95)  # 95% 分位数 ≈ 1.645

# 随机数生成
samples = norm.rvs(loc=0, scale=1, size=1000)
```

### 其他常用分布

```python
from scipy.stats import binom, poisson, uniform, expon

# 二项分布
binom.pmf(k=5, n=10, p=0.5)  # P(X=5)
binom.rvs(n=10, p=0.5, size=100)

# 泊松分布
poisson.pmf(k=3, mu=5)  # P(X=3), lambda=5

# 均匀分布
uniform.pdf(x=0.5, loc=0, scale=1)

# 指数分布
expon.pdf(x=1, scale=1/0.5)  # rate=0.5
```

## 假设检验

### t 检验

```python
from scipy.stats import ttest_1samp, ttest_ind

# 单样本 t 检验
data = np.random.normal(100, 15, 50)
t_stat, p_value = ttest_1samp(data, popmean=105)
# H0: 总体均值 = 105
# p < 0.05 则拒绝 H0

# 双样本 t 检验（独立样本）
group1 = np.random.normal(100, 15, 50)
group2 = np.random.normal(105, 15, 50)
t_stat, p_value = ttest_ind(group1, group2)
# H0: 两组均值相等
```

### 卡方检验

```python
from scipy.stats import chi2_contingency

# 独立性检验
observed = np.array([[50, 30, 20], [35, 40, 25]])
chi2, p_value, dof, expected = chi2_contingency(observed)
# H0: 两个变量独立
```

### 相关性检验

```python
from scipy.stats import pearsonr, spearmanr

x = np.random.normal(0, 1, 100)
y = 2 * x + np.random.normal(0, 1, 100)

# Pearson 相关系数（线性相关）
r, p_value = pearsonr(x, y)

# Spearman 相关系数（单调相关）
rho, p_value = spearmanr(x, y)
```

## 置信区间

```python
from scipy.stats import t

data = np.random.normal(100, 15, 50)
n = len(data)
mean = np.mean(data)
se = stats.sem(data)  # 标准误

# 95% 置信区间
ci = t.interval(0.95, df=n-1, loc=mean, scale=se)
print(f"95% CI: [{ci[0]:.2f}, {ci[1]:.2f}]")
```

## pandas 中的统计方法

```python
df = pd.DataFrame({'A': np.random.normal(0, 1, 1000),
                   'B': np.random.normal(5, 2, 1000)})

df.describe()      # 完整描述统计
df.mean()          # 均值
df.median()        # 中位数
df.std()           # 标准差
df.corr()          # 相关系数矩阵
df.cov()           # 协方差矩阵
df.skew()          # 偏度
df.kurt()          # 峰度
```
