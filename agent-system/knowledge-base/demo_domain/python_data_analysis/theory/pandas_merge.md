# Pandas 数据合并与连接

## merge（类似 SQL JOIN）

```python
import pandas as pd

df_users = pd.DataFrame({
    'user_id': [1, 2, 3, 4],
    'name': ['Alice', 'Bob', 'Charlie', 'David']
})

df_orders = pd.DataFrame({
    'order_id': [101, 102, 103],
    'user_id': [1, 2, 1],
    'amount': [100, 200, 150]
})

# 内连接（默认）
pd.merge(df_users, df_orders, on='user_id')
pd.merge(df_users, df_orders, on='user_id', how='inner')

# 左连接
pd.merge(df_users, df_orders, on='user_id', how='left')

# 右连接
pd.merge(df_users, df_orders, on='user_id', how='right')

# 外连接
pd.merge(df_users, df_orders, on='user_id', how='outer')

# 不同列名合并
pd.merge(df_users, df_orders, left_on='user_id', right_on='user_id')

# 多列合并
pd.merge(df1, df2, on=['key1', 'key2'])
```

## concat（拼接）

```python
df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
df2 = pd.DataFrame({'A': [5, 6], 'B': [7, 8]})

# 纵向拼接（行增加）
pd.concat([df1, df2])
pd.concat([df1, df2], ignore_index=True)  # 重置索引

# 横向拼接（列增加）
pd.concat([df1, df2], axis=1)

# 处理列不一致
df3 = pd.DataFrame({'A': [1, 2], 'C': [9, 10]})
pd.concat([df1, df3])         # 缺失列用 NaN 填充
pd.concat([df1, df3], join='inner')  # 只保留共有列
```

## join（基于索引）

```python
df1 = pd.DataFrame({'A': [1, 2, 3]}, index=['a', 'b', 'c'])
df2 = pd.DataFrame({'B': [4, 5, 6]}, index=['a', 'b', 'd'])

df1.join(df2)          # 左连接（默认）
df1.join(df2, how='inner')  # 内连接
df1.join(df2, how='outer')  # 外连接
```

## append（已弃用，用 concat 替代）

```python
# 旧写法（已弃用）
# df.append(df2)

# 新写法
pd.concat([df, df2], ignore_index=True)
```

## 实际应用场景

```python
# 场景1：合并用户信息和订单信息
user_orders = pd.merge(df_users, df_orders, on='user_id', how='left')

# 场景2：拼接多个月份的数据
files = ['jan.csv', 'feb.csv', 'mar.csv']
dfs = [pd.read_csv(f) for f in files]
all_data = pd.concat(dfs, ignore_index=True)

# 场景3：添加计算列后合并
df_users['level'] = df_users['age'].apply(lambda x: 'senior' if x > 30 else 'junior')
```

## 常见问题

1. **重复列名**：合并后出现 `_x`, `_y` 后缀，使用 `suffixes` 参数自定义
2. **索引混乱**：合并后记得 `reset_index()`
3. **数据膨胀**：一对多合并会导致行数增加，注意检查
4. **内存问题**：大数据集合并时考虑分批处理
