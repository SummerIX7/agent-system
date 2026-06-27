---
title: API 数据采集
source_type: practice
source_name: Python网络数据采集实战
author: 吴磊
publisher: 人民邮电出版社
year: 2021
chapter: 实战指南
---

# API 数据采集

## 概述

API是获取结构化数据的主要途径，相比网页爬虫更稳定、高效。本文介绍使用requests库进行API调用、反爬策略处理、以及响应数据解析的完整流程。

## 实操步骤

### 步骤1：基础API调用

```python
import requests
import json

# 1. GET请求
url = "https://api.example.com/data"
params = {
    "page": 1,
    "per_page": 20,
    "sort": "created_at"
}
headers = {
    "Authorization": "Bearer your_token_here",
    "Content-Type": "application/json"
}

response = requests.get(url, params=params, headers=headers, timeout=30)

# 检查响应状态
if response.status_code == 200:
    data = response.json()  # 解析JSON
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print(f"请求失败: {response.status_code}, {response.text}")

# 2. POST请求
payload = {
    "query": "python",
    "filters": {"language": "zh", "date_range": "2023-01-01:2023-12-31"}
}
response = requests.post(url, json=payload, headers=headers)

# 3. 带重试的请求
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retry))
response = session.get(url, timeout=30)
```

### 步骤2：分页数据采集

```python
def fetch_all_pages(base_url, params=None, max_pages=100):
    """通用分页采集函数"""
    all_data = []
    page = 1

    while page <= max_pages:
        params = params or {}
        params['page'] = page
        params['per_page'] = 100

        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # 根据API返回结构调整
        if isinstance(data, dict):
            items = data.get('items', data.get('data', []))
            total_pages = data.get('total_pages', max_pages)
        elif isinstance(data, list):
            items = data
            total_pages = max_pages
        else:
            break

        if not items:
            break

        all_data.extend(items)
        print(f"已采集第 {page}/{total_pages} 页，本页 {len(items)} 条")

        page += 1

        # 避免请求过快
        import time
        time.sleep(0.5)

    return all_data

# 使用示例
all_items = fetch_all_pages("https://api.example.com/items")
```

### 步骤3：反爬策略处理

```python
import random
import time

# 1. 随机User-Agent
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
]

headers = {
    "User-Agent": random.choice(user_agents),
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

# 2. 代理IP池
proxies = [
    {"http": "http://proxy1:port", "https": "http://proxy1:port"},
    {"http": "http://proxy2:port", "https": "http://proxy2:port"},
]

def make_request_with_proxy(url, proxies_list):
    """带代理的请求"""
    for proxy in random.sample(proxies_list, len(proxies_list)):
        try:
            response = requests.get(url, proxies=proxy, timeout=10)
            if response.status_code == 200:
                return response
        except Exception as e:
            print(f"代理 {proxy} 失败: {e}")
            continue
    return None

# 3. 请求频率控制
import time
from functools import wraps

def rate_limit(calls_per_second=1):
    """请求限速装饰器"""
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

@rate_limit(calls_per_second=2)
def fetch_data(url):
    return requests.get(url, headers=headers, timeout=30)
```

### 步骤4：响应数据解析

```python
import pandas as pd
from datetime import datetime

# 1. JSON解析
def parse_json_response(response):
    """解析JSON响应"""
    data = response.json()

    # 嵌套结构提取
    if 'results' in data:
        items = data['results']
    elif 'data' in data and isinstance(data['data'], list):
        items = data['data']
    else:
        items = [data]

    # 转换为DataFrame
    df = pd.DataFrame(items)
    return df

# 2. 日期解析
def parse_dates(df, date_columns):
    """解析日期列"""
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df

# 3. 嵌套字段展开
def flatten_nested(df, column):
    """展开嵌套JSON列"""
    if column in df.columns:
        nested_df = pd.json_normalize(df[column])
        nested_df.columns = [f"{column}_{col}" for col in nested_df.columns]
        df = pd.concat([df.drop(column, axis=1), nested_df], axis=1)
    return df

# 完整处理流程
response = requests.get(url, headers=headers)
df = parse_json_response(response)
df = parse_dates(df, ['created_at', 'updated_at'])
df = flatten_nested(df, 'metadata')
df.to_csv('api_data.csv', index=False, encoding='utf-8-sig')
```

## 常见问题与解决方案

1. **问题**：API限流(429错误) **解决**：实现指数退避重试，降低请求频率
2. **问题**：Token过期 **解决**：捕获401错误，自动刷新Token后重试
3. **问题**：响应数据不完整 **解决**：检查API文档，确认分页参数和字段选择

## 最佳实践

1. 遵守API使用条款，设置合理的请求间隔
2. 使用Session保持连接，减少握手开销
3. 缓存已采集数据，避免重复请求
4. 记录采集日志，便于问题追踪和数据溯源
