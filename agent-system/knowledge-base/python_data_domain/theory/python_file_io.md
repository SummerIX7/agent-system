---
title: 文件操作
source_type: book
source_name: Python编程从入门到实践
author: Eric Matthes
publisher: 人民邮电出版社
year: 2023
chapter: 第10章 文件和异常
---

# 文件操作

## 概述

文件读写是数据分析的基础环节，数据的输入输出都依赖于文件操作。Python 提供了丰富的文件处理能力，涵盖文本文件、CSV、JSON 等多种格式。掌握 `with` 语句、上下文管理器以及常用数据格式的解析方法，是高效进行数据处理的关键。

## 核心概念

### 文件读写基础

Python 使用内置的 `open()` 函数打开文件，通过模式参数控制读写行为。`with` 语句（上下文管理器）能确保文件在使用后自动关闭，避免资源泄漏。

```python
# 写入文本文件
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("第一行数据\n")
    f.write("第二行数据\n")

# 读取文本文件
with open("output.txt", "r", encoding="utf-8") as f:
    content = f.read()          # 读取全部内容
    print(content)

# 逐行读取（适合大文件）
with open("output.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(line.strip())     # strip() 去除换行符

# 追加写入
with open("output.txt", "a", encoding="utf-8") as f:
    f.write("追加的内容\n")
```

### CSV 文件处理

CSV 是数据分析中最常见的数据交换格式。Python 标准库的 `csv` 模块提供了基本的 CSV 读写功能。

```python
import csv

# 写入 CSV
data = [
    ["姓名", "年龄", "城市"],
    ["张三", 25, "北京"],
    ["李四", 30, "上海"],
    ["王五", 28, "广州"]
]

with open("people.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerows(data)

# 读取 CSV
with open("people.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    header = next(reader)       # 读取表头
    for row in reader:
        name, age, city = row
        print(f"{name}, {age}岁, {city}")

# 使用 DictReader（以字典形式读取）
with open("people.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row["姓名"], row["城市"])
```

### JSON 文件处理

JSON 是 Web API 和配置文件的通用格式，`json` 模块支持 Python 对象与 JSON 字符串之间的序列化和反序列化。

```python
import json

# Python 对象转 JSON
data = {
    "project": "数据分析",
    "version": 1.0,
    "tags": ["python", "data", "analysis"],
    "config": {
        "debug": False,
        "max_rows": 1000
    }
}

with open("config.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# JSON 文件读取
with open("config.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)
    print(loaded["project"])     # 数据分析
    print(loaded["tags"][0])     # python

# JSON 字符串转换
json_str = json.dumps(data, ensure_ascii=False)
obj = json.loads(json_str)
```

### 路径处理

`pathlib` 模块提供了面向对象的路径操作方式，比传统的 `os.path` 更加简洁和跨平台。

```python
from pathlib import Path

# 创建路径对象
data_dir = Path("data") / "raw"
data_dir.mkdir(parents=True, exist_ok=True)

# 遍历目录
for csv_file in Path(".").glob("*.csv"):
    print(f"文件: {csv_file.name}, 大小: {csv_file.stat().st_size} 字节")

# 递归搜索
for py_file in Path(".").rglob("*.py"):
    print(py_file)

# 路径属性
p = Path("/home/user/data/report.csv")
print(p.name)       # report.csv
print(p.stem)       # report
print(p.suffix)     # .csv
print(p.parent)     # /home/user/data
```

## 常用函数/方法

```python
# 文件常用操作
import os

os.path.exists("file.txt")      # 检查文件是否存在
os.path.getsize("file.txt")     # 获取文件大小
os.rename("old.txt", "new.txt") # 重命名文件
os.remove("file.txt")           # 删除文件

# pathlib 常用方法
p = Path("data.csv")
p.exists()                      # 是否存在
p.is_file()                     # 是否为文件
p.suffix                        # 文件扩展名
p.with_suffix(".json")          # 更换扩展名
p.read_text(encoding="utf-8")  # 读取文本内容
p.write_text("内容", encoding="utf-8")  # 写入文本
```

## 注意事项

1. 始终使用 `with` 语句管理文件，确保文件句柄被正确释放，避免在循环中反复打开关闭同一文件。
2. 处理中文内容时，指定 `encoding="utf-8"` 编码；写入 CSV 时使用 `utf-8-sig` 以兼容 Excel 打开。
3. 读取大文件时避免 `f.read()` 一次性加载，应使用逐行迭代或分块读取（`f.read(chunk_size)`）。
4. JSON 中的键名和字符串值必须使用双引号，Python 的 `json` 模块会自动处理这一转换。
