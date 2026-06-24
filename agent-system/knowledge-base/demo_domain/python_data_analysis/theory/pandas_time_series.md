---
title: 时间序列处理
source_type: book
source_name: 利用Python进行数据分析
author: Wes McKinney
publisher: O'Reilly
year: 2022
chapter: 第11章 时间序列
---

# 时间序列处理

## 概述

时间序列数据广泛存在于金融、气象、物联网等领域，Pandas 提供了强大的时间序列处理工具。DatetimeIndex 让时间索引操作变得直观，重采样功能支持灵活的频率转换，滚动窗口计算则用于移动平均等统计分析。本文介绍 Pandas 中时间序列处理的核心方法。

## 核心概念

### DatetimeIndex 与时间解析

Pandas 通过 `pd.to_datetime()` 将字符串或数值转换为 datetime 对象，并可设置为 DataFrame 的索引，从而支持基于时间的切片和对齐。

```python
import pandas as pd
import numpy as np

# 创建时间序列
dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
df = pd.DataFrame({
    "date": dates,
    "sales": np.random.randint(100, 1000, size=len(dates))
})

# 设置 DatetimeIndex
df = df.set_index("date")

# 字符串转日期
df2 = pd.DataFrame({
    "date": ["2024-01-15", "2024-02-20", "2024-03-10"],
    "value": [100, 200, 300]
})
df2["date"] = pd.to_datetime(df2["date"])

# 时间索引切片
january_data = df["2024-01"]         # 整个1月的数据
q1_data = df["2024-01":"2024-03"]    # 第一季度数据
print(january_data.head())
```

### 时间分量提取

从 datetime 对象中可以方便地提取年、月、日、星期等分量，用于分组聚合分析。

```python
# 提取时间分量
df["year"] = df.index.year
df["month"] = df.index.month
df["day"] = df.index.day
df["weekday"] = df.index.day_name()   # 星期名称
df["quarter"] = df.index.quarter

# 按月份统计
monthly_sales = df.groupby(df.index.month)["sales"].sum()
print(monthly_sales)

# 按星期统计平均销量
weekday_avg = df.groupby(df.index.dayofweek)["sales"].mean()
weekday_avg.index = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
print(weekday_avg)
```

### 重采样（Resample）

重采样是时间序列频率转换的核心操作，分为降采样（高频到低频，如日到月）和升采样（低频到高频，如月到日）。

```python
# 降采样：日数据聚合为月数据
monthly = df["sales"].resample("M").agg(["mean", "sum", "std"])
monthly.columns = ["月均销量", "月总销量", "月标准差"]
print(monthly.head())

# 降采样：自定义聚合函数
weekly = df["sales"].resample("W").agg(
    total="sum",
    max_day="max",
    min_day="min"
)

# 升采样并向前填充
monthly_data = pd.Series(
    [100, 200, 300],
    index=pd.date_range("2024-01-01", periods=3, freq="M")
)
daily_data = monthly_data.resample("D").ffill()  # 前向填充
```

### 滚动窗口计算

滚动窗口（rolling）用于计算移动平均、移动标准差等统计量，是时间序列平滑和趋势分析的常用方法。

```python
# 简单移动平均
df["sales_ma7"] = df["sales"].rolling(window=7).mean()    # 7日移动平均
df["sales_ma30"] = df["sales"].rolling(window=30).mean()  # 30日移动平均

# 滚动标准差（波动率）
df["volatility"] = df["sales"].rolling(window=7).std()

# 指数加权移动平均（EWMA），近期数据权重更大
df["sales_ewma"] = df["sales"].ewm(span=7).mean()

# 自定义滚动计算
df["rolling_max"] = df["sales"].rolling(window=7).max()
df["rolling_min"] = df["sales"].rolling(window=7).min()

# 查看结果
print(df[["sales", "sales_ma7", "sales_ewma"]].tail(10))
```

## 常用函数/方法

```python
# 时间序列常用函数
pd.Timestamp("2024-06-15")          # 创建时间戳
pd.Timedelta(days=7, hours=3)       # 创建时间差
pd.DateOffset(months=3)             # 日期偏移

# 时间范围生成
pd.date_range("2024-01-01", periods=12, freq="M")  # 月末
pd.date_range("2024-01-01", periods=4, freq="Q")   # 季度末
pd.bdate_range("2024-01-01", periods=10)           # 工作日

# 时区处理
ts = pd.Timestamp("2024-01-01 12:00", tz="Asia/Shanghai")
ts_utc = ts.tz_convert("UTC")       # 转换时区

# 时期转换
period = pd.Period("2024-03", freq="M")
print(period.start_time)            # 月初
print(period.end_time)              # 月末
```

## 注意事项

1. 使用 `pd.to_datetime()` 时注意指定 `format` 参数以提高解析速度和准确性，例如 `format="%Y-%m-%d"`。
2. 重采样时注意区分 `"M"`（月末）和 `"MS"`（月初）、`"Q"`（季末）和 `"QS"`（季初）等频率字符串。
3. 滚动窗口的 `min_periods` 参数控制最少需要多少个非空值才输出结果，避免窗口起始处出现过多 `NaN`。
4. 时间序列索引必须是单调递增的，否则切片和重采样可能产生意外结果，可使用 `df.sort_index()` 排序。
