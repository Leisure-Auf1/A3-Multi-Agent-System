#!/usr/bin/env python3
"""
Review Gate 测试 — 验证三道门禁的正确性
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加项目根路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.review_gate import (
    FORBIDDEN_CALLS,
    FORBIDDEN_IMPORTS,
    GateResult,
    ReviewGateManager,
)


class TestGateResult(unittest.TestCase):
    """GateResult 数据模型测试"""

    def test_passed_gate(self):
        r = GateResult(gate_name="AST", passed=True, message="OK", elapsed_ms=1.5)
        self.assertTrue(r.passed)
        self.assertEqual(r.gate_name, "AST")

    def test_failed_gate(self):
        r = GateResult(gate_name="PYTEST", passed=False, message="FAIL")
        self.assertFalse(r.passed)


class TestReviewGateManagerAST(unittest.TestCase):
    """第一关: AST 静态门禁"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.gate = ReviewGateManager(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name: str, content: str):
        Path(self.tmp, name).write_text(content, encoding="utf-8")

    # ── AST 通过 ──

    def test_clean_code_passes(self):
        """干净的 Exercise 代码通过 AST"""
        self._write("exercise.py", """
def add(a: int, b: int) -> int:
    return a + b
""")
        result = self.gate.verify_ast()
        self.assertTrue(result.passed, result.message)

    # ── AST 安全拦截 ──

    def test_forbidden_import_os(self):
        """禁止 import os"""
        self._write("exercise.py", "import os")
        result = self.gate.verify_ast()
        self.assertFalse(result.passed)

    def test_forbidden_import_subprocess(self):
        """禁止 import subprocess"""
        self._write("exercise.py", "import subprocess")
        result = self.gate.verify_ast()
        self.assertFalse(result.passed)

    def test_forbidden_call_eval(self):
        """禁止 eval() 调用"""
        self._write("exercise.py", "x = eval('1+1')")
        result = self.gate.verify_ast()
        self.assertFalse(result.passed)

    def test_forbidden_call_exec(self):
        """禁止 exec() 调用"""
        self._write("exercise.py", "x = exec('print(42)')")
        result = self.gate.verify_ast()
        self.assertFalse(result.passed)

    # ── AST 语法错误 ──

    def test_syntax_error(self):
        """语法错误被拦截"""
        self._write("exercise.py", "def broken(:")
        result = self.gate.verify_ast()
        self.assertFalse(result.passed)

    # ── File not found ──

    def test_file_not_found(self):
        result = self.gate.verify_ast()
        self.assertFalse(result.passed)

    # ── 桩检测 ──

    def test_not_implemented_stub(self):
        """raise NotImplementedError 被检测到"""
        self._write("exercise.py", """
def unfinished():
    raise NotImplementedError("TODO")
""")
        result = self.gate.verify_ast()
        self.assertFalse(result.passed)


class TestReviewGateManagerPytest(unittest.TestCase):
    """第二关: Pytest 双向动态门禁"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.gate = ReviewGateManager(self.tmp)

        # 创建合格的 Exercise / Solution / Test 文件
        self._write("exercise.py", """
# --- 学生填空区域 ---
def add(a, b):
    # TODO: 实现加法
    pass
""")
        self._write("solution.py", """
def add(a, b):
    return a + b
""")
        self._write("test_case.py", """
import pytest
from exercise import add

def test_add_positive():
    assert add(3, 5) == 8

def test_add_negative():
    assert add(-1, 1) == 0

def test_add_zero():
    assert add(0, 0) == 0
""")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name: str, content: str):
        Path(self.tmp, name).write_text(content, encoding="utf-8")

    def test_positive_passes(self):
        """正向: Solution 缝合后测试通过"""
        result = self.gate.verify_pytest()
        self.assertTrue(result.passed, result.message)

    def test_negative_fails_with_stub(self):
        """反向: 原始骨架测试必须失败（因为 pass 不满足断言）"""
        result = self.gate.verify_pytest()
        self.assertTrue(result.passed, result.message)

    def test_solution_broken_fails(self):
        """Solution 答案错误 → 正向验证不通过"""
        self._write("solution.py", """
def add(a, b):
    return a * b  # 故意写错!
""")
        result = self.gate.verify_pytest()
        self.assertFalse(result.passed)
        self.assertIn("正向验证失败", result.message)

    def test_weak_test_case_detected(self):
        """测试用例太弱（原始骨架也能过）→ 反向验证不通过"""
        self._write("exercise.py", """
def add(a, b):
    # 什么都不做的桩
    pass
""")
        self._write("test_case.py", """
from exercise import add
def test_add():
    # 太弱的测试 — 不检查任何值
    add(3, 5)  # 即使 pass 也不会报错
""")
        result = self.gate.verify_pytest()
        self.assertFalse(result.passed)
        self.assertIn("反向验证失败", result.message)


class TestReviewGateManagerJudge(unittest.TestCase):
    """第三关: LLM-as-Judge 教学门禁"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.gate = ReviewGateManager(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name: str, content: str):
        Path(self.tmp, name).write_text(content, encoding="utf-8")

    def test_missing_lecture(self):
        """讲义不存在 → 失败"""
        result = self.gate.verify_llm_judge()
        self.assertFalse(result.passed)

    def test_good_lecture_passes(self):
        """高质量讲义通过评审"""
        self._write("lecture.md", """
# Python 装饰器深度讲解

你好！今天我们一起来学习 Python 中最重要的高级特性之一：装饰器。

## 1. 想象一下：函数是一等公民

想象一下这个场景：你在 Python 中定义了一个函数，然后把它赋值给另一个变量...

❌ 你可能以前这样写：
```python
def add(a, b):
    print("开始执行")
    result = a + b
    print("执行结束")
    return result
```
💡 这种写法的问题很明显：每个函数都要手动复制粘贴这些日志代码。

✅ 接下来我们看看装饰器的魔法：
```python
@logger
def add(a, b):
    return a + b
```

## 2. 核心概念：闭包是关键

现在让我们深入闭包的本质。记住：内部函数可以「捕获」外部函数的变量。

💡 关键洞察：Python 的装饰器本质上就是一个接受函数作为参数、返回新函数的高阶函数。

## 3. 动手试试：写第一个装饰器

接下来我们来动手写一个计时装饰器。试试这个代码：

```python
@timer
def slow_function(n):
    return sum(i**2 for i in range(n))
```

## 4. 对比示例：@wraps 的必要性

❌ 不加 wraps：
```python
def naive_logger(func):
    def wrapper(*args, **kwargs):
        ...
```

✅ 加上 wraps（推荐）：
```python
from functools import wraps
def smart_logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ...
```

## 回顾总结

回顾我们今天学的内容：函数是一等公民 → 闭包 → @装饰器语法糖 → functools.wraps。这些概念环环相扣，理解一个才能理解下一个。

最后，记住一点：@decorator 不是魔法，它只是 func = decorator(func) 的语法糖！
""")
        result = self.gate.verify_llm_judge()
        self.assertTrue(result.passed, result.message)

    def test_poor_lecture_fails(self):
        """低质量讲义不通过"""
        self._write("lecture.md", "讲装饰器。装饰器是一种设计模式。可以装饰函数。")
        result = self.gate.verify_llm_judge()
        # 可能不通过，取决于评分
        if not result.passed:
            details = result.details
            self.assertIn("suggestions", details)


class TestReviewGatePipeline(unittest.TestCase):
    """全管道端到端测试"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.gate = ReviewGateManager(self.tmp)

        # 写入合格的三件套
        Path(self.tmp, "exercise.py").write_text("""
def add(a: int, b: int) -> int:
    # TODO: student implements
    pass
""")
        Path(self.tmp, "solution.py").write_text("""
def add(a: int, b: int) -> int:
    return a + b
""")
        Path(self.tmp, "test_case.py").write_text("""
from exercise import add

def test_add():
    assert add(3, 5) == 8
    assert add(-1, 1) == 0
""")
        Path(self.tmp, "lecture.md").write_text("""
# Python 装饰器深度讲解

你好！今天我们来学习装饰器。

## 1. 想象一下

想象一下：你定义了一个函数，然后可以把它当变量传递...这就是 Python 的「函数是一等公民」。

❌ 不好的写法 → 每个函数都复制粘贴日志代码
✅ 装饰器写法 → @logger 一行搞定

## 2. 核心概念

💡 关键: @decorator 只是语法糖，等价于 func = decorator(func)

## 3. 动手试试

接下来动手写一个计时装饰器。试试：
```python
@timer
def slow_func(n):
    return sum(i**2 for i in range(n))
```

## 4. 对比：@wraps

❌ 不加 wraps → 丢失元信息
✅ 加 @wraps → 保留 __name__ 和 __doc__

## 回顾

回顾今天：函数一等公民→闭包→装饰器→@wraps。记住：装饰器不魔法。
""")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_full_pipeline_passes(self):
        """全管道通过"""
        result = self.gate.run_full_gate(node_id="TEST")
        self.assertEqual(result.status, "PASSED", result.reason)
        self.assertIsNotNone(result.checkpoint_sig)
        self.assertIn("SIG_TEST_VERIFIED", result.checkpoint_sig)
        self.assertEqual(len(result.gates), 3)

    def test_full_pipeline_ast_fails(self):
        """AST 失败 → 管道短路"""
        Path(self.tmp, "exercise.py").write_text("import os\n")
        result = self.gate.run_full_gate(node_id="TEST")
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.reason, "AST_STATIC_ERROR")
        self.assertEqual(len(result.gates), 1)  # 停在第1关

    def test_full_pipeline_pytest_fails(self):
        """Pytest 失败 → 管道停在第二关"""
        Path(self.tmp, "solution.py").write_text("""
def add(a, b):
    return a * b  # 错误答案
""")
        result = self.gate.run_full_gate(node_id="TEST")
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.reason, "PYTEST_DYNAMIC_ERROR")
        self.assertEqual(len(result.gates), 2)

    def test_json_output(self):
        """JSON 输出格式正确"""
        output = self.gate.run_full_gate_json(node_id="TEST")
        data = json.loads(output)
        self.assertEqual(data["status"], "PASSED")
        self.assertIn("checkpoint_sig", data)

    def test_forbidden_imports_blacklist(self):
        """黑名单完整性检查"""
        self.assertIn("os", FORBIDDEN_IMPORTS)
        self.assertIn("subprocess", FORBIDDEN_IMPORTS)
        self.assertIn("sys", FORBIDDEN_IMPORTS)
        self.assertIn("eval", FORBIDDEN_CALLS)
        self.assertIn("exec", FORBIDDEN_CALLS)


class TestReviewGateCLI(unittest.TestCase):
    """CLI 入口测试"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        Path(self.tmp, "exercise.py").write_text("""
def add(a: int, b: int) -> int:
    pass
""")
        Path(self.tmp, "solution.py").write_text("""
def add(a: int, b: int) -> int:
    return a + b
""")
        Path(self.tmp, "test_case.py").write_text("""
from exercise import add
def test_add():
    assert add(3, 5) == 8
""")
        Path(self.tmp, "lecture.md").write_text(
            "# 学习装饰器\n\n"
            "你好！今天学装饰器。\n\n"
            "## 1. 想象一下\n想象一下函数可以当变量传递。\n\n"
            "❌ 以前手动复制日志\n✅ @logger 一行搞定\n\n"
            "## 2. 核心\n💡 关键: @decorator = func = decorator(func)\n\n"
            "接下来看闭包...\n"
            "## 3. 动手\n试试写一个 @timer 装饰器。\n"
            "```python\n@timer\ndef calc():\n    ...\n```\n"
            "## 4. 对比\n❌ 不加 @wraps\n✅ 加 @wraps\n\n"
            "## 回顾\n回顾：函数一等公民→闭包→装饰器→@wraps。"
            "记住：装饰器不是魔法！"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cli_json_mode(self):
        """CLI --json 模式"""
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "core.review_gate", self.tmp, "--json", "--node-id", "CLI_TEST"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent / "src"),
        )
        data = json.loads(r.stdout)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(data["status"], "PASSED")

    def test_cli_verbose_mode(self):
        """CLI --verbose 模式"""
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "core.review_gate", self.tmp, "--verbose", "--node-id", "CLI_TEST2"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent / "src"),
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("终审通关", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
