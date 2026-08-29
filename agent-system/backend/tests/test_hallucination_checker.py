"""谬误检测器单元测试：断言启发式分类与分层抽样（纯函数，不依赖 LLM）。"""
import pytest

from app.metrics.hallucination_checker import HallucinationChecker, _ASSERTION_CATEGORIES


@pytest.fixture(scope="module")
def checker() -> HallucinationChecker:
    return HallucinationChecker()


class TestClassifyAssertion:
    """断言分类：数值型优先（含数字）→ 步骤型（流程词）→ 定义型"""

    def test_numeric(self, checker):
        assert checker._classify_assertion("主轴转速设定为 1200r/min") == "数值型"
        assert checker._classify_assertion("切削深度 2mm 到 3mm 之间") == "数值型"

    def test_numeric_overrides_step_keywords(self, checker):
        """分类顺序：含数字的断言即使带流程词也归为数值型"""
        assert checker._classify_assertion("首先将转速设为 800，然后进给") == "数值型"

    def test_step(self, checker):
        assert checker._classify_assertion("首先回参考点，然后完成对刀") == "步骤型"
        assert checker._classify_assertion("依次完成装夹、对刀、加工") == "步骤型"

    def test_definition(self, checker):
        assert checker._classify_assertion("工件坐标系是编程时使用的坐标系") == "定义型"

    def test_result_always_in_known_categories(self, checker):
        for a in ["转速 800", "首先对刀", "坐标系定义", ""]:
            assert checker._classify_assertion(a) in _ASSERTION_CATEGORIES


class TestStratifiedSample:
    """分层抽样：按类别比例分配名额，合计不超过 cap"""

    @staticmethod
    def _mixed_assertions(n_numeric=60, n_step=30, n_def=10):
        # 数值型必须含数字；步骤型/定义型不含数字（否则分类会归入数值型）
        numeric = [f"参数{chr(0x4e00 + i % 30)}{i} 设为 {i * 10}mm" for i in range(n_numeric)]
        step = [f"首先执行第{chr(0x4e00 + i)}项装夹操作" for i in range(n_step)]
        defin = [f"坐标系概念{chr(0x4e00 + i)}指编程基准" for i in range(n_def)]
        return numeric + step + defin

    def test_small_input_returns_all_in_order(self, checker):
        assertions = self._mixed_assertions(3, 3, 2)
        out = checker._stratified_sample(assertions, cap=20)
        assert out == assertions

    def test_cap_respected_and_no_duplicates(self, checker):
        assertions = self._mixed_assertions()
        out = checker._stratified_sample(assertions, cap=20)
        assert len(out) == 20
        assert len(set(out)) == 20
        assert set(out) <= set(assertions)

    def test_proportional_quota_per_category(self, checker):
        """60 数值 / 30 步骤 / 10 定义，cap=20 → 名额按比例 12 / 6 / 2"""
        assertions = self._mixed_assertions()
        out = checker._stratified_sample(assertions, cap=20)
        cats = [checker._classify_assertion(a) for a in out]
        assert cats.count("数值型") == 12
        assert cats.count("步骤型") == 6
        assert cats.count("定义型") == 2

    def test_tiny_cap_still_returns_samples(self, checker):
        assertions = self._mixed_assertions()
        out = checker._stratified_sample(assertions, cap=3)
        assert len(out) <= 3
        assert len(out) > 0
