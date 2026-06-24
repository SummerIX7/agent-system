---
title: 文本数据处理
source_type: book
source_name: 利用Python进行数据分析
author: Wes McKinney
publisher: O'Reilly
year: 2022
chapter: 第7章 数据清洗和准备
---

# 文本数据处理

## 概述

数据分析中经常需要处理文本数据，包括数据清洗、特征提取和格式转换等任务。Pandas 通过 `.str` 访问器提供了向量化的字符串操作方法，配合 Python 的 `re` 模块可以高效地完成复杂的文本处理工作。本文介绍 Pandas 中文本数据处理的核心技巧。

## 核心概念

### str 访问器

Pandas 的 `.str` 访问器将 Python 字符串方法应用于 Series 的每个元素，实现向量化操作，性能远优于逐元素循环。

```python
import pandas as pd

names = pd.Series(["  张三  ", "李四", "王五", "赵六", "钱七"])

# 基本字符串操作
cleaned = names.str.strip()           # 去除首尾空格
upper = names.str.upper()             # 转大写（对英文有效）
length = names.str.len()              # 计算字符串长度

# 判断和筛选
mask = names.str.contains("张")       # 是否包含"张"
filtered = names[mask]

# 替换
replaced = names.str.replace("三", "叁")

# 分割
emails = pd.Series(["zhang@163.com", "li@qq.com", "wang@gmail.com"])
domains = emails.str.split("@").str[1]  # 提取域名
usernames = emails.str.split("@").str[0]

print(domains)
# 0      163.com
# 1       qq.com
# 2    gmail.com
```

### 正则表达式

正则表达式是文本处理的强大工具，Pandas 的 `.str` 方法原生支持正则表达式，可以实现复杂的模式匹配和提取。

```python
import pandas as pd

# 使用正则表达式提取数据
phones = pd.Series(["138-1234-5678", "139-8765-4321", "150-0000-1111"])

# 提取中间四位数字
middle = phones.str.extract(r"\d{3}-(\d{4})-\d{4}")
print(middle)

# 使用命名捕获组
data = pd.Series(["2024-01-15", "2024-02-20", "2024-12-31"])
parts = data.str.extract(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")
print(parts)
#    year month day
# 0  2024    01  15
# 1  2024    02  20
# 2  2024    12  31

# 正则替换：去除所有非数字字符
messy = pd.Series(["价格:￥100", "价格:￥250", "价格:￥88"])
numbers = messy.str.replace(r"[^\d]", "", regex=True).astype(int)
print(numbers)

# 使用 findall 查找所有匹配
text = pd.Series(["联系方式: 1381234, 1398765", "电话: 1500000"])
all_phones = text.str.findall(r"1[3-9]\d{8}")
print(all_phones)
```

### 文本编码与格式处理

在实际数据处理中，文本数据经常存在编码不一致、格式混乱等问题，需要进行规范化处理。

```python
import pandas as pd

# 多列文本拼接
df = pd.DataFrame({
    "first": ["张", "李", "王"],
    "middle": ["小", "大", "中"],
    "last": ["三", "四", "五"]
})
df["full_name"] = df["first"].str.cat([df["middle"], df["last"]], sep="")
print(df["full_name"])

# pad/ljust/rjust 填充对齐
codes = pd.Series(["A1", "B12", "C123"])
padded = codes.str.pad(width=6, fillchar="0", side="left")
print(padded)
# 0    0000A1
# 1    000B12
# 2    00C123

# get_dummies 进行文本编码（one-hot）
categories = pd.Series(["red", "blue", "red", "green", "blue"])
dummies = categories.str.get_dummies()
print(dummies)

# 处理缺失值
names = pd.Series(["张三", None, "王五"])
filled = names.str.upper()          # None 会变为 NaN
has_value = names.str.contains("张") # NaN 处理
print(has_value)
# 0     True
# 1      NaN
# 2    False
```

## 常用函数/方法

```python
# 常用 .str 方法一览
s = pd.Series(["Hello World", "Python Pandas", "Data Analysis"])

s.str.lower()               # 转小写
s.str.upper()               # 转大写
s.str.title()               # 首字母大写
s.str.strip()               # 去除首尾空白
s.str.split(" ")            # 按空格分割
s.str.len()                 # 字符串长度
s.str.startswith("P")       # 是否以P开头
s.str.endswith("s")         # 是否以s结尾
s.str.contains("Data")      # 是否包含
s.str.replace("Data", "数据")  # 替换
s.str.slice(0, 5)           # 切片
s.str.findall(r"\b\w+\b")   # 查找所有单词
s.str.extract(r"(\w+)")     # 提取第一个匹配
s.str.cat(sep=", ")         # 连接所有元素
```

## 注意事项

1. `.str` 方法会自动处理 `NaN` 值，返回 `NaN` 而非报错，但 `contains()` 等方法需注意 `na` 参数的设置。
2. 使用正则表达式时，`regex=True` 参数在 Pandas 较新版本中需要显式指定，未来版本可能改变默认行为。
3. 处理大规模文本数据时，向量化的 `.str` 方法比 `apply()` + lambda 快很多，尽量避免使用循环。
4. 文本比较和匹配时注意编码问题，确保数据统一使用 UTF-8 编码，避免出现乱码导致匹配失败。
