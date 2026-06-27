# CNC 领域迁移计划

> 将项目从「Python 数据分析」切换到「CNC 数控加工」领域

---

## 一、迁移背景

当前系统的知识库是 Python 数据分析领域，内容过于入门，缺乏垂直领域的深度。CNC 数控加工是一个：
- **技术门槛高**：涉及机械加工、数控编程、材料科学等多学科交叉
- **标准化程度高**：有明确的国家标准（GB）、行业标准（ISO）
- **实践性强**：需要实际操作经验，适合 AI 辅助学习
- **市场需求大**：制造业转型升级，数控人才缺口大

---

## 二、领域耦合点分析

经过代码审查，以下是需要修改的领域耦合点：

### 2.1 前端耦合点

| 文件 | 耦合内容 | 修改方式 |
|------|----------|----------|
| `frontend/pages/profile.vue:132-141` | `skillOptions` 硬编码了 Python 技能 | 替换为 CNC 技能选项 |
| `frontend/pages/practice.vue:225` | 默认主题 `'Python 数据分析'` | 替换为 CNC 默认主题 |

### 2.2 后端耦合点

| 文件 | 耦合内容 | 修改方式 |
|------|----------|----------|
| `backend/app/agents/diagnosis.py:30-35` | 难度判定标准提到"编程基础"、"Python/SQL" | 改为 CNC 领域的难度标准 |
| `backend/app/agents/generation.py:53` | "Python 代码用 ```python 包裹" | 改为"G 代码 / 操作步骤" |
| `backend/app/agents/generation.py:97` | "步骤清晰，每步都有代码示例" | 改为"步骤清晰，每步都有操作说明" |
| `backend/app/agents/generation.py:136-137` | "完整代码"、"matplotlib 生成图表" | 改为"完整工艺流程"、"加工示意图" |

### 2.3 知识库

| 目录 | 说明 | 修改方式 |
|------|------|----------|
| `knowledge-base/demo_domain/python_data_analysis/` | Python 数据分析知识 | **保留不动**，作为通用示例 |
| `knowledge-base/cnc_domain/` | CNC 数控加工知识 | **新建独立目录** |

---

## 三、CNC 知识库设计

### 3.1 知识体系结构

```
knowledge-base/
├── demo_domain/                          # 原有目录（保留不动）
│   └── python_data_analysis/
│       ├── theory/
│       ├── practice/
│       └── standards/
│
└── cnc_domain/                           # 新建 CNC 独立目录
    ├── theory/                           # 理论基础
    │   ├── cnc_basics.md                 # 数控基础概念
    │   ├── coordinate_system.md          # 坐标系与运动轴
    │   ├── g_code_basics.md              # G 代码基础
    │   ├── m_code_basics.md              # M 代码基础
    │   ├── cutting_theory.md             # 切削原理
    │   ├── material_science.md           # 材料科学基础
    │   ├── tolerance_fits.md             # 公差与配合
    │   └── surface_finish.md             # 表面粗糙度
    │
    ├── practice/                         # 实操技能
    │   ├── lathe_programming.md          # 数控车床编程
    │   ├── mill_programming.md           # 数控铣床编程
    │   ├── machining_center.md           # 加工中心操作
    │   ├── cam_software.md               # CAM 软件应用
    │   ├── tool_selection.md             # 刀具选择与管理
    │   ├── fixture_design.md             # 夹具设计基础
    │   ├── cutting_parameters.md         # 切削参数优化
    │   └── measurement.md                # 测量与检测
    │
    └── standards/                        # 行业标准
        ├── gb_standards.md               # 国家标准汇编
        ├── iso_standards.md              # ISO 标准
        ├── safety_regulations.md         # 安全操作规程
        ├── quality_control.md            # 质量控制标准
        └── process_planning.md           # 工艺规程制定
```

### 3.2 知识文件格式（保持不变）

每个知识文件保持现有的 frontmatter 格式：

```markdown
---
title: 数控编程基础
source_type: book
source_name: 数控编程技术
author: 张明
publisher: 机械工业出版社
year: 2023
chapter: 第3章
---

# 数控编程基础

## 概述
...

## 核心知识点
...

## 实例代码
```gcode
G00 X0 Z0
G01 X50 Z-20 F0.2
```
```

### 3.3 知识内容规划

#### theory/（理论基础 - 8 个文件）

| 文件 | 内容 | 字数 | 参考来源 |
|------|------|------|----------|
| `cnc_basics.md` | 数控机床分类、组成、工作原理 | 2000+ | 《数控技术》刘战术 |
| `coordinate_system.md` | 机床坐标系、工件坐标系、绝对/增量编程 | 1500+ | 《数控编程》王爱玲 |
| `g_code_basics.md` | G00/G01/G02/G03/G90/G91 等常用指令 | 2500+ | GB/T 8870 |
| `m_code_basics.md` | M03/M04/M05/M06/M08/M09 等辅助指令 | 1500+ | GB/T 8870 |
| `cutting_theory.md` | 切削三要素、切削力、切削热 | 2000+ | 《金属切削原理》陈日曜 |
| `material_science.md` | 常见加工材料特性（钢、铝、铸铁、钛合金） | 1800+ | 《工程材料》王章忠 |
| `tolerance_fits.md` | 尺寸公差、形位公差、配合制度 | 1500+ | GB/T 1800 |
| `surface_finish.md` | 表面粗糙度参数、标注方法、加工方法对应 | 1200+ | GB/T 1031 |

#### practice/（实操技能 - 8 个文件）

| 文件 | 内容 | 字数 | 参考来源 |
|------|------|------|----------|
| `lathe_programming.md` | 数控车床编程实例（轴类、盘类零件） | 2500+ | 《数控车床编程与操作》 |
| `mill_programming.md` | 数控铣床编程实例（平面、轮廓、型腔） | 2500+ | 《数控铣床编程与操作》 |
| `machining_center.md` | 加工中心多工序复合加工 | 2000+ | 《加工中心编程与操作》 |
| `cam_software.md` | MasterCAM/UG NX/CATIA 基础操作 | 2000+ | 软件官方教程 |
| `tool_selection.md` | 刀具类型、材料、涂层、选用原则 | 1800+ | 《数控刀具选用手册》 |
| `fixture_design.md` | 夹具类型、定位原理、夹紧方式 | 1500+ | 《机床夹具设计》 |
| `cutting_parameters.md` | 主轴转速、进给速度、切削深度优化 | 1800+ | 《切削用量简明手册》 |
| `measurement.md` | 游标卡尺、千分尺、三坐标测量 | 1500+ | 《机械测量技术》 |

#### standards/（行业标准 - 5 个文件）

| 文件 | 内容 | 字数 | 参考来源 |
|------|------|------|----------|
| `gb_standards.md` | GB/T 8870（数控程序格式）、GB/T 1800（公差）等 | 2000+ | 国家标准全文公开系统 |
| `iso_standards.md` | ISO 6983（G 代码）、ISO 14649（STEP-NC）等 | 1500+ | ISO 官网 |
| `safety_regulations.md` | 机床安全操作规程、个人防护 | 1500+ | GB 15760 |
| `quality_control.md` | SPC 统计过程控制、Cpk 过程能力指数 | 1800+ | 《统计质量控制》 |
| `process_planning.md` | 工艺路线制定、工序安排、工时计算 | 2000+ | 《机械制造工艺学》 |

---

## 四、前端修改方案

### 4.1 profile.vue 技能自评选项

**修改位置**：`frontend/pages/profile.vue:132-141`

**原代码**：
```javascript
const skillOptions = [
  'Python 基础',
  'NumPy',
  'Pandas',
  'Matplotlib',
  '统计学基础',
  'SQL 数据库',
  '数据清洗',
  '机器学习基础',
]
```

**新代码**：
```javascript
const skillOptions = [
  '机械制图基础',
  'G 代码编程',
  '数控车床操作',
  '数控铣床操作',
  'CAM 软件应用',
  '刀具选择与管理',
  '切削参数优化',
  '测量与检测',
]
```

### 4.2 practice.vue 默认主题

**修改位置**：`frontend/pages/practice.vue:225`

**原代码**：
```javascript
topic: currentQuestion.value.topic || 'Python 数据分析',
```

**新代码**：
```javascript
topic: currentQuestion.value.topic || 'CNC 数控编程',
```

### 4.3 profile.vue 专业方向 placeholder

**修改位置**：`frontend/pages/profile.vue:28`

**原代码**：
```html
<UInput v-model="formState.major" placeholder="如：计算机科学、数据科学" />
```

**新代码**：
```html
<UInput v-model="formState.major" placeholder="如：机械工程、数控技术、模具设计" />
```

---

## 五、后端修改方案

### 5.1 diagnosis.py 难度判定标准

**修改位置**：`backend/app/agents/diagnosis.py:30-35`

**原代码**：
```python
[难度判定标准]
- beginner：完全零编程基础，非理工科背景，从未写过代码
- intermediate：有编程基础（如 Python/SQL 熟练），或理工科专业，但数据分析经验较少
- advanced：有丰富的编程和数据分析经验（3年以上），能独立完成数据项目
- expert：统计学/数据科学专业背景，5年以上数据分析经验，熟悉机器学习

注意：如果学习者有编程基础（如 Python 熟练、计算机专业），即使数据分析技能较弱，也应判定为 intermediate，因为编程基础意味着学习曲线更陡。
```

**新代码**：
```python
[难度判定标准]
- beginner：零机械加工基础，非工科背景，从未接触过数控机床
- intermediate：有机械基础（如机械制图、普通机床操作经验），或工科专业背景，但数控经验较少
- advanced：有丰富的数控加工经验（3年以上），能独立完成复杂零件编程与加工
- expert：数控编程专家，5年以上经验，精通多轴加工、工艺优化、CAM 编程

注意：如果学习者有机械加工基础（如普通车床/铣床操作经验），即使数控技能较弱，也应判定为 intermediate，因为机械加工基础意味着更容易理解数控原理。
```

### 5.2 generation.py 生成要求

**修改位置**：`backend/app/agents/generation.py:53`

**原代码**：
```
3. 包含实际可运行的代码示例（Python 代码用 ```python 包裹）
```

**新代码**：
```
3. 包含完整的 G 代码示例（用 ```gcode 包裹）和操作步骤说明
```

**修改位置**：`backend/app/agents/generation.py:97`

**原代码**：
```
2. 步骤清晰，每步都有代码示例（用 ```python 包裹）
```

**新代码**：
```
2. 步骤清晰，每步都有操作说明和 G 代码示例（用 ```gcode 包裹）
```

**修改位置**：`backend/app/agents/generation.py:136-137`

**原代码**：
```
3. 完整的实现代码（带注释，用 ```python 包裹）
4. 关键步骤的原理解释
5. 结果分析和可视化（用 matplotlib 生成图表）
```

**新代码**：
```
3. 完整的加工工艺流程和 G 代码（带注释，用 ```gcode 包裹）
4. 关键步骤的工艺原理和注意事项
5. 加工结果分析和质量检测要求
```

---

## 六、知识库构建方案

### 6.1 目录结构调整

**操作步骤**：

```bash
# 创建 CNC 知识库独立目录结构（保留原有 demo_domain 不动）
mkdir -p agent-system/knowledge-base/cnc_domain/theory
mkdir -p agent-system/knowledge-base/cnc_domain/practice
mkdir -p agent-system/knowledge-base/cnc_domain/standards
```

**配置调整**：

需要修改后端配置，让系统加载新的知识库目录。修改 `backend/app/core/config.py`：

```python
# 新增配置项
KNOWLEDGE_BASE_DIR: str = "./knowledge-base/cnc_domain"  # CNC 领域知识库路径
```

或者修改知识检索器，支持多知识库目录。

### 6.2 知识文件编写规范

每个知识文件必须包含：

1. **Frontmatter 元数据**（用于知识溯源）
   - `title`：知识点标题
   - `source_type`：来源类型（book / paper / standard / website）
   - `source_name`：来源名称（书名/论文名/标准号）
   - `author`：作者
   - `publisher`：出版社
   - `year`：出版年份
   - `chapter`：章节

2. **正文结构**
   - 概述：简要介绍知识点
   - 核心知识点：详细讲解（带来源引用）
   - 实例/代码：G 代码示例或操作步骤
   - 常见问题：初学者易犯错误
   - 总结：关键要点回顾

3. **字数要求**
   - 理论文件：1500-2500 字
   - 实操文件：2000-2500 字
   - 标准文件：1500-2000 字

### 6.3 知识内容示例

**示例文件**：`theory/g_code_basics.md`

```markdown
---
title: G 代码基础
source_type: book
source_name: 数控编程技术
author: 张明
publisher: 机械工业出版社
year: 2023
chapter: 第3章
---

# G 代码基础

## 概述

G 代码（G-code）是数控机床最常用的编程语言，用于控制机床的运动轨迹、速度、加工方式等。掌握 G 代码是数控编程的基础。

## 核心知识点

### 快速定位指令 G00

G00 指令用于刀具快速移动到指定位置，不进行切削加工。

📚 来源：《数控编程技术》(张明, 2023) 第3章第2节

**格式**：
```gcode
G00 X_ Z_  // 车床
G00 X_ Y_ Z_  // 铣床/加工中心
```

**示例**：
```gcode
G00 X100 Z50  // 快速移动到 X100 Z50 位置
```

**注意事项**：
- G00 运动速度由机床参数设定，不可用 F 指令控制
- 运动轨迹不一定是直线，可能是折线，需注意避免碰撞

### 直线插补指令 G01

G01 指令用于刀具以指定速度进行直线切削。

📚 来源：《数控编程技术》(张明, 2023) 第3章第3节

**格式**：
```gcode
G01 X_ Z_ F_  // 车床
G01 X_ Y_ Z_ F_  // 铣床/加工中心
```

**示例**：
```gcode
G01 X50 Z-20 F0.2  // 直线切削到 X50 Z-20，进给速度 0.2mm/r
```

**参数说明**：
- `F`：进给速度，车床单位为 mm/r，铣床单位为 mm/min

### 圆弧插补指令 G02/G03

- G02：顺时针圆弧插补
- G03：逆时针圆弧插补

📚 来源：《数控编程技术》(张明, 2023) 第3章第4节

**格式（圆心方式）**：
```gcode
G02 X_ Z_ I_ K_ F_  // 车床
G02 X_ Y_ I_ J_ F_  // 铣床
```

**格式（半径方式）**：
```gcode
G02 X_ Z_ R_ F_
```

**示例**：
```gcode
G02 X100 Z-50 R30 F0.15  // 顺时针圆弧，半径 R30
```

## 常见问题

1. **G02/G03 方向判断错误**
   - 错误表现：加工出的圆弧方向相反
   - 解决方法：站在第三轴正方向观察，顺时针为 G02，逆时针为 G03

2. **进给速度单位混淆**
   - 错误表现：车床用 mm/min，铣床用 mm/r
   - 解决方法：车床 G98 为 mm/min、G99 为 mm/r；铣床 G94 为 mm/min、G95 为 mm/r

## 总结

- G00：快速定位，不切削
- G01：直线切削，需指定 F
- G02/G03：圆弧切削，注意方向判断
- 进给速度单位因机床类型而异
```

---

## 七、开发指导文档更新

### 7.1 文档位置

`docs/开发指导文档.md`

### 7.2 需要更新的章节

1. **项目概述**：更新系统定位为 CNC 数控加工领域
2. **核心指标**：保持不变（幻觉率 < 5%、匹配准确率 ≥ 85%、覆盖率 ≥ 90%）
3. **Agent 角色定义**：更新各 Agent 的职责描述
4. **技术栈选型**：保持不变
5. **评分权重**：保持不变

---

## 八、实施步骤

### 阶段一：知识库构建（预计 3-5 天）

| 步骤 | 任务 | 产出 | 负责 |
|------|------|------|------|
| 1.1 | 创建 `knowledge-base/cnc_domain/` 目录结构 | 目录结构 | - |
| 1.2 | 收集 CNC 领域参考资料 | 参考书目清单 | - |
| 1.3 | 编写 theory/ 目录下 8 个知识文件 | 8 个 .md 文件 | - |
| 1.4 | 编写 practice/ 目录下 8 个知识文件 | 8 个 .md 文件 | - |
| 1.5 | 编写 standards/ 目录下 5 个知识文件 | 5 个 .md 文件 | - |
| 1.6 | 知识文件审核与校对 | 审核通过的文件 | - |

### 阶段二：后端修改（预计 1 天）

| 步骤 | 任务 | 产出 | 负责 |
|------|------|------|------|
| 2.1 | 修改 config.py 新增知识库路径配置 | 更新后的配置 | - |
| 2.2 | 修改 retriever.py 支持新知识库目录 | 更新后的检索器 | - |
| 2.3 | 修改 diagnosis.py 难度判定标准 | 更新后的文件 | - |
| 2.4 | 修改 generation.py 生成要求 | 更新后的文件 | - |
| 2.5 | 测试后端 Agent 功能 | 测试报告 | - |

### 阶段三：前端修改（预计 0.5 天）

| 步骤 | 任务 | 产出 | 负责 |
|------|------|------|------|
| 3.1 | 修改 profile.vue 技能选项 | 更新后的文件 | - |
| 3.2 | 修改 practice.vue 默认主题 | 更新后的文件 | - |
| 3.3 | 测试前端功能 | 测试报告 | - |

### 阶段四：集成测试（预计 1 天）

| 步骤 | 任务 | 产出 | 负责 |
|------|------|------|------|
| 4.1 | 构建 CNC 知识库向量索引 | ChromaDB 索引 | - |
| 4.2 | 端到端功能测试 | 测试报告 | - |
| 4.3 | 生成样例资源质量评估 | 评估报告 | - |

---

## 九、验收标准

### 9.1 知识库验收

- [ ] `knowledge-base/cnc_domain/` 目录结构创建完成
- [ ] 21 个知识文件全部编写完成
- [ ] 每个文件包含完整的 frontmatter 元数据
- [ ] 知识内容准确，引用来源真实可查
- [ ] 文件格式符合规范（Markdown + G 代码示例）

### 9.2 配置验收

- [ ] config.py 新增 `KNNOWLEDGE_BASE_DIR` 配置项
- [ ] retriever.py 支持加载新知识库目录
- [ ] 原有 `demo_domain/python_data_analysis/` 保留不动

### 9.3 功能验收

- [ ] 学习者画像输入正常（技能选项为 CNC 相关）
- [ ] 学情诊断 Agent 正常工作（难度判定标准正确）
- [ ] 知识生成 Agent 正常工作（生成 CNC 相关内容）
- [ ] 试题生成 Agent 正常工作（生成 CNC 相关题目）
- [ ] 辩论审核机制正常运行

### 9.4 质量验收

- [ ] 专业知识幻觉率 < 5%
- [ ] 学习者画像-资源难度匹配准确率 ≥ 85%
- [ ] 知识点覆盖率 ≥ 90%
- [ ] 知识溯源标注完整（每条知识点有来源）

---

## 十、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| CNC 专业知识准确性 | 幻觉率超标 | 严格引用权威教材和国家标准，审核环节加强 |
| 知识库覆盖不全 | 覆盖率不达标 | 分阶段补充，优先覆盖核心知识点 |
| G 代码格式多样性 | 生成内容格式错误 | 在 prompt 中明确 G 代码格式规范 |
| 前端交互适配 | 用户体验下降 | 保持现有交互逻辑，仅替换领域内容 |

---

## 十一、附录

### 11.1 参考资料

| 类型 | 名称 | 用途 |
|------|------|------|
| 教材 | 《数控编程技术》张明 | 理论知识 |
| 教材 | 《数控车床编程与操作》 | 实操技能 |
| 教材 | 《数控铣床编程与操作》 | 实操技能 |
| 教材 | 《金属切削原理》陈日曜 | 切削理论 |
| 标准 | GB/T 8870 | 数控程序格式 |
| 标准 | GB/T 1800 | 公差与配合 |
| 标准 | ISO 6983 | G 代码标准 |

### 11.2 文件变更清单

**新增文件**（21 个）：
- `knowledge-base/cnc_domain/theory/*.md`（8 个）
- `knowledge-base/cnc_domain/practice/*.md`（8 个）
- `knowledge-base/cnc_domain/standards/*.md`（5 个）

**修改文件**（6 个）：
- `frontend/pages/profile.vue`（技能选项 + placeholder）
- `frontend/pages/practice.vue`（默认主题）
- `backend/app/core/config.py`（新增知识库路径配置）
- `backend/app/knowledge/retriever.py`（支持新知识库目录）
- `backend/app/agents/diagnosis.py`（难度判定标准）
- `backend/app/agents/generation.py`（生成要求）

**保留不动**：
- `knowledge-base/demo_domain/python_data_analysis/`（原有 Python 数据分析知识库）

---

**计划制定日期**：2026-06-26

**预计完成日期**：2026-07-02（约 6 个工作日）
