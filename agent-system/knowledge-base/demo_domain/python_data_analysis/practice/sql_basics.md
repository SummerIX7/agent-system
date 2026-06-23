# SQL 查询基础

## 基本查询

### SELECT 语句

```sql
-- 查询所有列
SELECT * FROM users;

-- 查询指定列
SELECT name, age, email FROM users;

-- 别名
SELECT name AS 姓名, age AS 年龄 FROM users;

-- 去重
SELECT DISTINCT city FROM users;

-- 限制结果
SELECT * FROM users LIMIT 10;
SELECT * FROM users LIMIT 10 OFFSET 20;  -- 跳过前20条，取10条
```

### WHERE 条件

```sql
-- 比较运算
SELECT * FROM users WHERE age > 25;
SELECT * FROM users WHERE city = 'Beijing';
SELECT * FROM users WHERE age != 30;

-- 逻辑运算
SELECT * FROM users WHERE age > 25 AND city = 'Beijing';
SELECT * FROM users WHERE age < 25 OR age > 50;
SELECT * FROM users WHERE NOT city = 'Shanghai';

-- BETWEEN
SELECT * FROM users WHERE age BETWEEN 25 AND 35;

-- IN
SELECT * FROM users WHERE city IN ('Beijing', 'Shanghai', 'Guangzhou');

-- LIKE（模糊匹配）
SELECT * FROM users WHERE name LIKE 'A%';      -- 以 A 开头
SELECT * FROM users WHERE name LIKE '%li%';    -- 包含 li
SELECT * FROM users WHERE name LIKE 'A___';    -- A 开头 + 3个字符

-- NULL 判断
SELECT * FROM users WHERE email IS NULL;
SELECT * FROM users WHERE email IS NOT NULL;
```

## 聚合函数

```sql
-- 常用聚合函数
SELECT COUNT(*) FROM users;              -- 行数
SELECT COUNT(DISTINCT city) FROM users;  -- 不同城市数
SELECT AVG(age) FROM users;              -- 平均年龄
SELECT SUM(salary) FROM employees;       -- 工资总和
SELECT MAX(age) FROM users;              -- 最大年龄
SELECT MIN(age) FROM users;              -- 最小年龄

-- GROUP BY 分组
SELECT city, COUNT(*) AS user_count
FROM users
GROUP BY city;

-- HAVING 过滤分组
SELECT city, AVG(age) AS avg_age
FROM users
GROUP BY city
HAVING AVG(age) > 30;
```

## 排序

```sql
-- 单列排序
SELECT * FROM users ORDER BY age ASC;   -- 升序
SELECT * FROM users ORDER BY age DESC;  -- 降序

-- 多列排序
SELECT * FROM users ORDER BY city ASC, age DESC;
```

## 连接查询（JOIN）

```sql
-- INNER JOIN（内连接）
SELECT u.name, o.order_id, o.amount
FROM users u
INNER JOIN orders o ON u.user_id = o.user_id;

-- LEFT JOIN（左连接）
SELECT u.name, o.order_id
FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id;
-- 即使没有订单，用户也会显示

-- RIGHT JOIN（右连接）
SELECT u.name, o.order_id
FROM users u
RIGHT JOIN orders o ON u.user_id = o.user_id;

-- 多表连接
SELECT u.name, o.order_id, p.product_name
FROM users u
INNER JOIN orders o ON u.user_id = o.user_id
INNER JOIN products p ON o.product_id = p.product_id;
```

## 子查询

```sql
-- WHERE 中的子查询
SELECT * FROM users
WHERE user_id IN (
    SELECT DISTINCT user_id FROM orders WHERE amount > 1000
);

-- FROM 中的子查询
SELECT city, avg_age
FROM (
    SELECT city, AVG(age) AS avg_age
    FROM users
    GROUP BY city
) AS city_stats
WHERE avg_age > 30;

-- EXISTS
SELECT * FROM users u
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.user_id = u.user_id
);
```

## 窗口函数

```sql
-- ROW_NUMBER
SELECT name, age, city,
       ROW_NUMBER() OVER (PARTITION BY city ORDER BY age DESC) AS rank
FROM users;

-- RANK（有并列）
SELECT name, score,
       RANK() OVER (ORDER BY score DESC) AS rank
FROM students;

-- DENSE_RANK（无间隔）
SELECT name, score,
       DENSE_RANK() OVER (ORDER BY score DESC) AS dense_rank
FROM students;

-- 累计求和
SELECT order_date, amount,
       SUM(amount) OVER (ORDER BY order_date) AS cumulative_amount
FROM orders;

-- 移动平均
SELECT order_date, amount,
       AVG(amount) OVER (ORDER BY order_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7d
FROM orders;
```

## 常见面试题

```sql
-- 1. 查询每个部门工资最高的员工
SELECT * FROM employees e
WHERE salary = (
    SELECT MAX(salary) FROM employees
    WHERE department_id = e.department_id
);

-- 2. 连续登录 7 天的用户
SELECT user_id
FROM (
    SELECT user_id, login_date,
           DATE_SUB(login_date, INTERVAL ROW_NUMBER() OVER (
               PARTITION BY user_id ORDER BY login_date
           ) DAY) AS grp
    FROM login_log
) t
GROUP BY user_id, grp
HAVING COUNT(*) >= 7;

-- 3. 同比增长率
SELECT month,
       revenue,
       LAG(revenue, 12) OVER (ORDER BY month) AS last_year_revenue,
       (revenue - LAG(revenue, 12) OVER (ORDER BY month)) /
       LAG(revenue, 12) OVER (ORDER BY month) * 100 AS yoy_growth
FROM monthly_revenue;
```
