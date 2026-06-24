---
title: Python代码审查规范
source_type: standard
source_name: Python代码质量规范
author: Python Software Foundation
publisher: O'Reilly Media
year: 2023
url: https://peps.python.org/pep-0008/
---

# Python代码审查规范

## 概述

代码审查是保障代码质量、促进知识共享、防范潜在风险的关键实践。本规范基于PEP 8风格指南和Python最佳实践，定义了数据分析代码的审查标准，涵盖代码风格、命名规范、注释文档、测试覆盖等核心维度。数据分析代码往往具有探索性强、迭代频繁的特点，但良好的代码规范能够提升可维护性、可复用性和团队协作效率。通过系统化的代码审查流程，可以及早发现潜在问题，统一团队编码风格，降低技术债务积累。

## 核心规范

### PEP 8风格规范

遵循PEP 8官方风格指南，主要包括：缩进使用4个空格、行宽不超过120字符、函数间空两行、类方法间空一行。使用flake8、black等工具自动化检查和格式化。

```python
# Good: 符合PEP 8规范
def calculate_conversion_rate(visits: int, orders: int) -> float:
    """计算转化率"""
    if visits <= 0:
        raise ValueError("访问次数必须大于0")
    return round(orders / visits * 100, 2)

# Bad: 不符合PEP 8规范
def calcConversionRate(visits,orders):
    return round(orders/visits*100,2)
```

### 命名规范（Naming Convention）

采用有意义的命名，变量和函数使用snake_case，类名使用CamelCase，常量使用UPPER_SNAKE_CASE。避免单字母变量（循环计数器除外），名称应体现业务含义。

### 注释文档（Documentation）

公共函数必须添加docstring，说明功能、参数、返回值和异常。复杂逻辑添加行内注释，解释"为什么"而非"是什么"。推荐使用Google或NumPy docstring风格。

### 测试覆盖（Test Coverage）

核心分析函数必须编写单元测试，测试覆盖率不低于80%。测试用例应覆盖正常路径、边界条件和异常情况。使用pytest框架，配合fixtures管理测试数据。

## 检查清单

- [ ] 通过flake8/pylint静态检查
- [ ] 使用black/isort格式化代码
- [ ] 函数和类添加完整docstring
- [ ] 变量命名清晰且符合规范
- [ ] 核心逻辑添加单元测试
- [ ] 避免hardcode魔法数字
- [ ] 处理可能的异常情况

## 案例说明

1. 正例：某数据团队实施严格的代码审查流程，要求所有PR必须通过flake8检查、包含docstring和测试用例。半年内代码缺陷率下降60%，新成员上手时间缩短40%。

2. 反例：某分析师编写的特征工程脚本使用大量单字母变量和硬编码参数，无注释无测试。项目交接时新接手人员花费两周时间理解代码逻辑，期间多次引入回归缺陷。
