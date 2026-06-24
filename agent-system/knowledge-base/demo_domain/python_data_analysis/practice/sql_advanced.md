---
title: SQL 高级查询
source_type: practice
source_name: SQL高级查询实战
author: 周杰
publisher: 电子工业出版社
year: 2022
chapter: 实战指南
---

# SQL 高级查询

## 概述

掌握SQL高级查询技巧是数据分析师的核心技能。本文重点介绍窗口函数、公共表表达式(CTE)、子查询优化三大进阶技术，帮助处理复杂的数据分析需求。

## 实操步骤

### 步骤1：窗口函数

窗口函数在不减少结果集行数的情况下进行聚合计算：

```sql
-- 基本语法
-- 函数() OVER (PARTITION BY 分组列 ORDER BY 排序列 ROWS/RANGE 范围)

-- 1. 排名函数
SELECT
    employee_name,
    department,
    salary,
    ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS row_num,
    RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rank_num,
    DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dense_rank_num
FROM employees;

-- 2. 聚合窗口函数
SELECT
    order_id,
    customer_id,
    amount,
    SUM(amount) OVER (PARTITION BY customer_id) AS customer_total,
    AVG(amount) OVER (PARTITION BY customer_id) AS customer_avg,
    amount / SUM(amount) OVER (PARTITION BY customer_id) AS pct_of_customer
FROM orders;

-- 3. 偏移函数（同比环比分析）
SELECT
    month,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY month) AS prev_month,
    LEAD(revenue, 1) OVER (ORDER BY month) AS next_month,
    (revenue - LAG(revenue, 1) OVER (ORDER BY month)) /
    LAG(revenue, 1) OVER (ORDER BY month) * 100 AS mom_growth
FROM monthly_sales;

-- 4. 累计计算
SELECT
    order_date,
    daily_sales,
    SUM(daily_sales) OVER (ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_sales,
    AVG(daily_sales) OVER (ORDER BY order_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7d
FROM daily_summary;
```

### 步骤2：公共表表达式(CTE)

CTE提高查询可读性，支持递归查询：

```sql
-- 1. 基本CTE
WITH regional_sales AS (
    SELECT
        region,
        SUM(amount) AS total_sales
    FROM orders
    GROUP BY region
),
top_regions AS (
    SELECT region
    FROM regional_sales
    WHERE total_sales > (SELECT AVG(total_sales) FROM regional_sales)
)
SELECT
    o.order_id,
    o.customer_id,
    o.amount,
    o.region
FROM orders o
JOIN top_regions t ON o.region = t.region;

-- 2. 递归CTE（组织架构层级）
WITH RECURSIVE org_chart AS (
    -- 锚点：顶级管理者
    SELECT employee_id, name, manager_id, 1 AS level,
           CAST(name AS VARCHAR(1000)) AS path
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- 递归部分
    SELECT e.employee_id, e.name, e.manager_id, oc.level + 1,
           CONCAT(oc.path, ' -> ', e.name)
    FROM employees e
    JOIN org_chart oc ON e.manager_id = oc.employee_id
)
SELECT * FROM org_chart ORDER BY level, path;

-- 3. CTE用于数据透视
WITH monthly_pivot AS (
    SELECT
        product_id,
        SUM(CASE WHEN MONTH(order_date) = 1 THEN amount ELSE 0 END) AS jan,
        SUM(CASE WHEN MONTH(order_date) = 2 THEN amount ELSE 0 END) AS feb,
        SUM(CASE WHEN MONTH(order_date) = 3 THEN amount ELSE 0 END) AS mar
    FROM orders
    WHERE YEAR(order_date) = 2023
    GROUP BY product_id
)
SELECT * FROM monthly_pivot;
```

### 步骤3：子查询优化

```sql
-- 1. EXISTS替代IN（大数据量时更高效）
-- 低效
SELECT * FROM customers
WHERE customer_id IN (SELECT customer_id FROM orders WHERE amount > 1000);

-- 高效
SELECT * FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id AND o.amount > 1000);

-- 2. 关联子查询 vs JOIN
-- 关联子查询（逐行执行，较慢）
SELECT product_name,
       (SELECT COUNT(*) FROM orders o WHERE o.product_id = p.product_id) AS order_count
FROM products p;

-- JOIN方式（通常更快）
SELECT p.product_name, COUNT(o.order_id) AS order_count
FROM products p
LEFT JOIN orders o ON p.product_id = o.product_id
GROUP BY p.product_name;

-- 3. 派生表优化
SELECT
    category,
    avg_price,
    product_count
FROM (
    SELECT
        category,
        AVG(price) AS avg_price,
        COUNT(*) AS product_count
    FROM products
    GROUP BY category
) AS category_stats
WHERE product_count > 10;
```

### 步骤4：性能优化技巧

```sql
-- 1. 避免SELECT *
SELECT customer_id, order_date, amount FROM orders;  -- 只选择需要的列

-- 2. 合理使用索引
CREATE INDEX idx_orders_customer ON orders(customer_id, order_date);

-- 3. 避免在WHERE中使用函数
-- 低效
SELECT * FROM orders WHERE YEAR(order_date) = 2023;
-- 高效
SELECT * FROM orders
WHERE order_date >= '2023-01-01' AND order_date < '2024-01-01';

-- 4. 使用EXPLAIN分析执行计划
EXPLAIN ANALYZE
SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id;
```

## 常见问题与解决方案

1. **问题**：窗口函数排序不稳定 **解决**：添加唯一键作为排序依据，确保结果确定性
2. **问题**：递归CTE无限循环 **解决**：设置MAXRECURSION选项或添加终止条件
3. **问题**：子查询性能差 **解决**：改用JOIN或EXISTS，确保关联字段有索引

## 最佳实践

1. 复杂查询优先使用CTE提高可读性，便于调试和维护
2. 窗口函数替代自连接，减少表扫描次数
3. 大数据量场景避免NOT IN，使用NOT EXISTS或LEFT JOIN
4. 定期分析慢查询日志，优化高频执行的SQL
