"""Mock 知识库检索器：返回预设的 CNC 领域文档，不调用嵌入 API 和 ChromaDB。"""

import re


class MockDocument:
    """模拟 LangChain Document，提供 .page_content 和 .metadata 属性"""

    def __init__(self, content: str, metadata: dict):
        self.page_content = content
        self.metadata = metadata

    def __repr__(self):
        title = self.metadata.get("source_name", "?")
        return f"MockDocument({title[:30]}...)"


# ─── 6 篇预设的 CNC 知识库文档 ──────────────────────────────────────

_MOCK_DOCS = [
    MockDocument(
        content=(
            "G 代码（G-code）是数控机床最常用的编程语言，用于控制机床的运动轨迹、速度、加工方式等。"
            "G 代码由字母 G 后跟数字组成，称为准备功能指令。常用 G 代码包括：\n"
            "- G00：快速定位指令，刀具以最大速度移动到指定位置，不进行切削加工。运动轨迹不一定是直线。\n"
            "- G01：直线插补指令，刀具以指定进给速度 F 沿直线切削。格式为 G01 X_ Z_ F_。\n"
            "- G02：顺时针圆弧插补指令，G03 为逆时针圆弧插补。需要指定圆心增量 I/J/K 或半径 R。\n"
            "- G90：绝对坐标编程，G91 为增量坐标编程。\n"
            "- G20/G21：英制/公制单位设定。\n"
            "车床常用固定循环：G90（外圆切削循环）、G71（外圆粗车循环）、G92（螺纹切削循环）。\n"
            "铣床常用固定循环：G81（钻孔循环）、G83（深孔钻循环）、G80（取消固定循环）。\n"
            "刀具补偿：G41 左补偿、G42 右补偿、G40 取消补偿、G43 长度补偿、G49 取消长度补偿。"
        ),
        metadata={
            "source_type": "book",
            "source_name": "数控编程与操作",
            "author": "张明",
            "publisher": "机械工业出版社",
            "year": "2022",
            "chapter": "第3章 CNC编程基础",
        },
    ),
    MockDocument(
        content=(
            "FANUC 数控系统常用 G 代码参考：\n"
            "| 指令 | 功能 | 模态 |\n"
            "| G00 | 快速定位 | 模态 |\n"
            "| G01 | 直线插补 | 模态 |\n"
            "| G02 | 顺时针圆弧插补 | 模态 |\n"
            "| G03 | 逆时针圆弧插补 | 模态 |\n"
            "| G04 | 暂停 | 非模态 |\n"
            "| G17 | XY 平面选择 | 模态 |\n"
            "| G18 | XZ 平面选择 | 模态 |\n"
            "| G19 | YZ 平面选择 | 模态 |\n"
            "| G28 | 返回参考点 | 非模态 |\n"
            "| G40 | 取消刀具半径补偿 | 模态 |\n"
            "| G41 | 刀具半径左补偿 | 模态 |\n"
            "| G42 | 刀具半径右补偿 | 模态 |\n"
            "| G43 | 刀具长度正补偿 | 模态 |\n"
            "| G49 | 取消刀具长度补偿 | 模态 |\n"
            "| G54-G59 | 工件坐标系选择 | 模态 |\n"
            "| G90 | 绝对坐标编程 | 模态 |\n"
            "| G91 | 增量坐标编程 | 模态 |\n"
            "M 代码常用指令：M03 主轴正转、M04 主轴反转、M05 主轴停止、M08 切削液开、M09 切削液关、M30 程序结束。"
        ),
        metadata={
            "source_type": "book",
            "source_name": "FANUC数控系统编程手册",
            "publisher": "FANUC",
            "year": "2021",
            "chapter": "第5章 G代码详解",
        },
    ),
    MockDocument(
        content=(
            "切削参数的选择是数控加工工艺的核心内容，直接影响加工质量、刀具寿命和生产效率。\n\n"
            "1. 切削速度 Vc（m/min）：\n"
            "- 钢材粗加工：80-120 m/min\n"
            "- 钢材精加工：120-200 m/min\n"
            "- 铝合金加工：200-500 m/min\n"
            "- 铸铁加工：60-100 m/min\n\n"
            "2. 进给量 f（mm/r）：\n"
            "- 粗车外圆：0.2-0.5 mm/r\n"
            "- 精车外圆：0.05-0.15 mm/r\n"
            "- 铣削粗加工：0.1-0.3 mm/tooth\n"
            "- 铣削精加工：0.05-0.1 mm/tooth\n\n"
            "3. 切削深度 ap（mm）：\n"
            "- 粗加工：2-6 mm\n"
            "- 半精加工：0.5-2 mm\n"
            "- 精加工：0.1-0.5 mm\n\n"
            "4. 主轴转速 n（r/min）计算公式：n = 1000 × Vc / (π × D)，其中 D 为刀具或工件直径。\n"
            "5. 刀具材料选择：高速钢适合低速切削；硬质合金适合中高速切削；陶瓷和 CBN 适合高速干式切削。"
        ),
        metadata={
            "source_type": "book",
            "source_name": "金属切削原理与刀具",
            "author": "李强",
            "publisher": "清华大学出版社",
            "year": "2023",
            "chapter": "第7章 切削参数选择",
        },
    ),
    MockDocument(
        content=(
            "数控车床操作要点：\n\n"
            "1. 对刀操作：\n"
            "   - X 向对刀：手动切削外圆，测量直径，输入到刀具偏置寄存器\n"
            "   - Z 向对刀：手动切削端面，将 Z 轴归零\n"
            "   - 多刀对刀：每把刀分别对刀并存入对应的刀具偏置号\n\n"
            "2. 车削循环：\n"
            "   - G90 外圆/内孔切削循环：格式 G90 X(U)_ Z(W)_ F_\n"
            "   - G71 外圆粗车复合循环：需定义精加工轮廓（N10-N20）\n"
            "   - G92 螺纹切削循环：格式 G92 X_ Z_ F_（F 为螺距）\n\n"
            "3. 常见问题与排查：\n"
            "   - 表面粗糙度不达标 → 检查刀具磨损、切削参数、冷却液\n"
            "   - 尺寸超差 → 检查对刀精度、刀具补偿值、机床热变形\n"
            "   - 螺纹加工不良 → 检查主轴编码器、切削深度分配、刀具角度"
        ),
        metadata={
            "source_type": "book",
            "source_name": "数控车床操作指南",
            "author": "王伟",
            "publisher": "化学工业出版社",
            "year": "2022",
            "chapter": "第4章 车削循环",
        },
    ),
    MockDocument(
        content=(
            "数控铣床与加工中心操作要点：\n\n"
            "1. 铣削策略：\n"
            "   - 顺铣：刀具旋转方向与进给方向相同，适用于精加工，表面质量好\n"
            "   - 逆铣：刀具旋转方向与进给方向相反，适用于粗加工，刀具寿命长\n"
            "   - 摆线铣削：用于深槽加工，减小刀具负载\n\n"
            "2. 钻孔循环：\n"
            "   - G81 标准钻孔：格式 G81 X_ Y_ Z_ R_ F_\n"
            "   - G83 深孔钻（排屑式）：格式 G83 X_ Y_ Z_ R_ Q_ F_（Q 为每次进给深度）\n"
            "   - G84 攻丝循环：需配合主轴同步，格式 G84 X_ Y_ Z_ R_ F_\n\n"
            "3. 加工中心刀库管理：\n"
            "   - Txx M06：调用 xx 号刀具并换刀\n"
            "   - G43 Hxx：调用 xx 号长度补偿\n"
            "   - Dxx：调用 xx 号半径补偿值\n\n"
            "4. 安全操作规范：\n"
            "   - 程序运行前必须执行图形模拟或空运行\n"
            "   - 首次切削需使用单段执行 + 进给倍率调低\n"
            "   - 操作人员必须佩戴安全眼镜，禁止戴手套操作旋转设备"
        ),
        metadata={
            "source_type": "book",
            "source_name": "数控铣床与加工中心",
            "author": "陈刚",
            "publisher": "机械工业出版社",
            "year": "2023",
            "chapter": "第6章 铣削策略",
        },
    ),
    MockDocument(
        content=(
            "机械加工质量控制核心要点：\n\n"
            "1. 尺寸公差：\n"
            "   - IT5-IT7：精密级，适用于轴承配合、量规\n"
            "   - IT8-IT10：普通级，适用于一般机械零件\n"
            "   - IT11-IT14：粗级，适用于非配合面\n\n"
            "2. 表面粗糙度 Ra（μm）：\n"
            "   - Ra 0.8-1.6：精车/精铣/磨削可达\n"
            "   - Ra 3.2-6.3：半精加工\n"
            "   - Ra 12.5-25：粗加工\n\n"
            "3. 检测方法：\n"
            "   - 游标卡尺：精度 0.02mm，适用于 IT10 及以下精度\n"
            "   - 千分尺：精度 0.001mm，适用于 IT6-IT8 精度\n"
            "   - 三坐标测量机（CMM）：精度 0.001mm，适用于复杂形位公差检测\n"
            "   - 表面粗糙度仪：用于 Ra/Rz 参数测量\n\n"
            "4. 过程控制（SPC）：\n"
            "   - Xbar-R 控制图用于监控加工过程稳定性\n"
            "   - Cp ≥ 1.33 为过程能力充足，Cpk ≥ 1.33 为过程能力指数合格\n"
            "   - 首件检验 + 巡检 + 末件检验 三检制是基本质量控制流程"
        ),
        metadata={
            "source_type": "book",
            "source_name": "机械加工质量控制",
            "author": "周华",
            "publisher": "科学出版社",
            "year": "2021",
            "chapter": "第2章 尺寸公差与表面质量",
        },
    ),
]


class MockRetriever:
    """模拟知识库检索器。通过关键词匹配返回预设文档，不调用嵌入 API 和 ChromaDB。"""

    def __init__(self):
        self._docs = _MOCK_DOCS

    def _score(self, query: str, doc: MockDocument) -> float:
        """关键词重叠评分"""
        q_words = set(re.findall(r'[一-鿿\w]+', query.lower()))
        if not q_words:
            return 0.0
        text = doc.page_content + " " + " ".join(str(v) for v in doc.metadata.values())
        d_words = set(re.findall(r'[一-鿿\w]+', text.lower()))
        overlap = q_words & d_words
        return len(overlap) / len(q_words)

    def search(self, query: str, k: int = 5) -> list[MockDocument]:
        """关键词匹配搜索，返回前 k 篇文档"""
        scored = [(doc, self._score(query, doc)) for doc in self._docs]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, score in scored[:k] if score > 0] or self._docs[:k]

    def search_with_score(self, query: str, k: int = 5) -> list[tuple]:
        """带分数的搜索"""
        docs = self.search(query, k)
        return [(doc, 0.85) for doc in docs]
