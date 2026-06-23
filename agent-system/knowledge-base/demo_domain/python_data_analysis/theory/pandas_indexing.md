# Pandas 数据索引与切片

## loc 与 iloc 的区别

| 方法 | 基于 | 包含终点 | 示例 |
|------|------|----------|------|
| `loc` | 标签（label） | 是 | `df.loc[0:3]` 返回标签 0,1,2,3 |
| `iloc` | 位置（integer position） | 否 | `df.iloc[0:3]` 返回位置 0,1,2 |

## loc 详解

```python
import pandas as pd

df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie', 'David'],
    'age': [25, 30, 35, 40],
    'city': ['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen']
}, index=['a', 'b', 'c', 'd'])

# 选择单行
df.loc['a']

# 选择多行
df.loc['a':'c']          # 标签切片，包含终点
df.loc[['a', 'c']]       # 花式索引

# 选择行列
df.loc['a':'c', 'name']           # 行切片 + 单列
df.loc['a':'c', ['name', 'age']]  # 行切片 + 多列

# 布尔索引
df.loc[df['age'] > 30]
df.loc[df['city'] == 'Beijing', ['name', 'age']]

# 修改数据
df.loc['a', 'age'] = 26
df.loc[df['age'] > 30, 'city'] = 'Other'
```

## iloc 详解

```python
# 选择单行
df.iloc[0]

# 选择多行
df.iloc[0:2]             # 位置切片，不包含终点
df.iloc[[0, 2]]          # 花式索引

# 选择行列
df.iloc[0:2, 0]          # 前2行第0列
df.iloc[0:2, [0, 1]]     # 前2行第0和1列
df.iloc[0:2, 0:2]        # 前2行前2列

# 负索引
df.iloc[-1]              # 最后一行
df.iloc[:, -1]           # 最后一列
```

## 条件筛选

```python
# 单条件
df[df['age'] > 30]

# 多条件（& 与 | 或 ~ 非）
df[(df['age'] > 25) & (df['age'] < 40)]
df[(df['city'] == 'Beijing') | (df['city'] == 'Shanghai')]
df[~(df['city'] == 'Beijing')]

# isin 方法
df[df['city'].isin(['Beijing', 'Shanghai'])]

# between 方法
df[df['age'].between(25, 35)]

# 字符串方法
df[df['name'].str.startswith('A')]
df[df['name'].str.contains('li')]
```

## 多级索引（MultiIndex）

```python
# 创建多级索引
arrays = [
    ['A', 'A', 'B', 'B'],
    [1, 2, 1, 2]
]
index = pd.MultiIndex.from_arrays(arrays, names=['group', 'num'])
df = pd.DataFrame({'value': [10, 20, 30, 40]}, index=index)

# 选择
df.loc['A']           # 所有 A 组
df.loc['A', 1]        # A 组第1号
df.loc[('A', 1)]      # 等价写法

# 交叉选择
df.xs(1, level='num')  # 所有组的第1号
```

## 设置索引

```python
# 设置索引
df = df.set_index('name')

# 重置索引
df = df.reset_index()

# 排序索引
df = df.sort_index()
```

## 常见错误

1. **KeyError**：使用 loc 时标签不存在会报 KeyError
2. **IndexError**：使用 iloc 时位置越界会报 IndexError
3. **SettingWithCopyWarning**：在切片上赋值时出现，用 `.loc` 解决
4. **链式索引**：`df[][]` 是链式索引，应改为 `df.loc[]`
