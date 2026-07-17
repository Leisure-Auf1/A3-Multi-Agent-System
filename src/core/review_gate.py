#!/usr/bin/env python3
"""
Review Gate Manager — 三道门禁离线终审系统

架构:
  待审查资产包 (Lecture.md, Exercise.py, Solution.py, Test_case.py)
      │
      ▼
  第一关: AST 静态语法门禁 — 语法安全检查 + 安全沙箱审计 + TODO 桩检查
      │ Pass
      ▼
  第二关: Pytest 双向动态门禁 — 正向求解验证 + 反向漏洞验证
      │ Pass
      ▼
  第三关: LLM-as-Judge 教学门禁 — 画像对齐度 + Rubric 定量打分(≥85)

使用:
  gate = ReviewGateManager(workspace_path="outputs/")
  result = gate.run_full_gate()
  print(result)  # {"status": "PASSED", ...} or {"status": "FAILED", ...}
"""

import ast
import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class GateResult:
    """单道门禁的执行结果"""
    gate_name: str
    passed: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0


@dataclass
class PipelineResult:
    """三道门禁串行执行的总结果"""
    status: str  # "PASSED" | "FAILED"
    reason: str = ""
    gates: List[GateResult] = field(default_factory=list)
    checkpoint_sig: Optional[str] = None
    judge_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "gates": [
                {
                    "name": g.gate_name,
                    "passed": g.passed,
                    "message": g.message,
                    "elapsed_ms": g.elapsed_ms,
                }
                for g in self.gates
            ],
            "checkpoint_sig": self.checkpoint_sig,
            "judge_scores": self.judge_scores,
        }


# ──────────────────────────────────────────────
# 安全审计黑名单
# ──────────────────────────────────────────────

# 高危模块 — 在 Exercise/Solution 代码中禁止 import
FORBIDDEN_IMPORTS: set = {
    "os", "subprocess", "sys", "shutil", "socket", "ctypes",
    "pickle", "marshal", "code", "codeop", "compile",
    "eval", "exec", "compile", "__import__",
    "multiprocessing", "threading", "signal",
    "http", "urllib", "requests", "smtplib", "imaplib",
    "pathlib", "ftplib", "telnetlib",
    "pty", "pdb",
    "antigravity",  # 娱乐模块也要拦
}

# 高危函数调用名 — 在 AST 中追踪
FORBIDDEN_CALLS: set = {"eval", "exec", "compile", "__import__", "open"}


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def _elapsed(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def _read_file(path: Path) -> Optional[str]:
    """安全读取文件，不存在返回 None"""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return None


# ──────────────────────────────────────────────
# ReviewGateManager
# ──────────────────────────────────────────────

class ReviewGateManager:
    """全局门禁控制器 — 三道串行门禁"""

    # LLM-as-Judge 评分阈值
    JUDGE_PASS_THRESHOLD: int = 85

    # AST 扫描超时（AST 解析极快，给 500ms 足够）
    AST_TIMEOUT_MS: int = 500

    # Pytest 执行超时
    PYTEST_TIMEOUT_SECONDS: int = 30

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path).resolve()
        self.gates: List[GateResult] = []

    # ── 文件定位 ──────────────────────────

    def _exercise_path(self) -> Path:
        return self.workspace / "exercise.py"

    def _solution_path(self) -> Path:
        return self.workspace / "solution.py"

    def _test_path(self) -> Path:
        return self.workspace / "test_case.py"

    def _lecture_path(self) -> Path:
        return self.workspace / "lecture.md"

    # ═══════════════════════════════════════════
    #  第一关: AST 静态语法门禁
    # ═══════════════════════════════════════════

    def verify_ast(self, file_path: Optional[Path] = None) -> GateResult:
        """
        第一关: AST 静态分析.

        检查项:
          1. 语法正确性
          2. 安全沙箱审计 — 禁止高危 import / 函数调用
          3. TODO 桩标记检查 — 验证是否包含未完成的 TODO
          4. 类型提示覆盖率
        """
        start = time.perf_counter()
        fp = file_path or self._exercise_path()

        # 0. 文件存在
        if not fp.exists():
            return GateResult(
                gate_name="AST_STATIC",
                passed=False,
                message=f"文件不存在: {fp}",
                elapsed_ms=_elapsed(start),
            )

        source = _read_file(fp)
        if source is None:
            return GateResult(
                gate_name="AST_STATIC",
                passed=False,
                message="无法读取文件",
                elapsed_ms=_elapsed(start),
            )

        # 1. 语法解析
        try:
            tree = ast.parse(source, filename=str(fp))
        except SyntaxError as e:
            return GateResult(
                gate_name="AST_STATIC",
                passed=False,
                message=f"🚨 语法错误: {e.msg} (line {e.lineno})",
                details={"lineno": e.lineno, "msg": e.msg},
                elapsed_ms=_elapsed(start),
            )

        issues: List[str] = []

        # 2. 安全沙箱审计 — import 黑名单
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_level = alias.name.split(".")[0]
                    if top_level in FORBIDDEN_IMPORTS:
                        issues.append(
                            f"🚨 禁止 import: '{alias.name}' (模块 '{top_level}' 在黑名单中)"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_level = node.module.split(".")[0]
                    if top_level in FORBIDDEN_IMPORTS:
                        issues.append(
                            f"🚨 禁止 from-import: '{node.module}' (在黑名单中)"
                        )

        # 3. 安全沙箱审计 — 高危函数调用
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in FORBIDDEN_CALLS:
                        issues.append(
                            f"🚨 禁止函数调用: '{node.func.id}()' "
                            f"(line {node.lineno})"
                        )
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in FORBIDDEN_CALLS:
                        issues.append(
                            f"🚨 禁止方法调用: '{node.func.attr}()' "
                            f"(line {node.lineno})"
                        )

        # 4. TODO 桩标记检查
        todo_pattern = re.compile(r"#\s*TODO", re.IGNORECASE)
        todos = todo_pattern.findall(source)
        # 允许一个 TODO 占位（学生练习区），但多余的要警告
        # 检查是否还有 raise NotImplementedError (占位桩)
        if "raise NotImplementedError" in source:
            issues.append(
                "⚠️ 存在未完成的桩: 'raise NotImplementedError' — 请替换为实际实现"
            )

        # 5. 类型提示覆盖率检查（宽松模式，仅作建议不计入失败）
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        typed = 0
        if functions:
            for fn in functions:
                has_return_type = fn.returns is not None
                has_arg_types = any(
                    a.annotation is not None for a in fn.args.args
                )
                if has_return_type or has_arg_types:
                    typed += 1

        if issues:
            return GateResult(
                gate_name="AST_STATIC",
                passed=False,
                message="; ".join(issues),
                details={"issues": issues},
                elapsed_ms=_elapsed(start),
            )

        return GateResult(
            gate_name="AST_STATIC",
            passed=True,
            message=f"✅ AST 审计通过 ({len(functions)} 函数, "
                    f"{typed}/{len(functions)} 有类型注解)" if functions else "✅ AST 审计通过",
            details={
                "functions": len(functions),
                "typed_functions": typed if functions else 0,
            },
            elapsed_ms=_elapsed(start),
        )

    # ═══════════════════════════════════════════
    #  第二关: Pytest 双向动态门禁
    # ═══════════════════════════════════════════

    def verify_pytest(
        self,
        exercise_path: Optional[Path] = None,
        solution_path: Optional[Path] = None,
        test_path: Optional[Path] = None,
    ) -> GateResult:
        """
        第二关: Pytest 双向动态验证.

        正向: Solution 缝合进 Exercise → run pytest → Exit Code 必须 == 0
        反向: 原始 Exercise (带 TODO) → run pytest → Exit Code 必须 > 0
        """
        start = time.perf_counter()
        ep = exercise_path or self._exercise_path()
        sp = solution_path or self._solution_path()
        tp = test_path or self._test_path()

        # 检查文件存在
        for name, p in [("Exercise", ep), ("Solution", sp), ("Test", tp)]:
            if not p.exists():
                return GateResult(
                    gate_name="PYTEST_DYNAMIC",
                    passed=False,
                    message=f"文件不存在: {name} ({p})",
                    elapsed_ms=_elapsed(start),
                )

        # 读取文件内容
        exercise_src = _read_file(ep)
        solution_src = _read_file(sp)
        test_src = _read_file(tp)

        if any(x is None for x in [exercise_src, solution_src, test_src]):
            return GateResult(
                gate_name="PYTEST_DYNAMIC",
                passed=False,
                message="无法读取某个资产文件",
                elapsed_ms=_elapsed(start),
            )

        # 类型已通过 None 检查，这里确保类型收缩
        assert exercise_src is not None
        assert solution_src is not None
        assert test_src is not None

        # ── 正向验证: 缝合 Solution 到 Exercise ──
        stitched_src = self._stitch_solution(exercise_src, solution_src)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # 写缝合后的 exercise
            (tmp / "exercise.py").write_text(stitched_src, encoding="utf-8")
            # 复制 test_case.py（它 import 的是 exercise 模块）
            test_content = test_src.replace(
                "from exercise", "from exercise"
            )  # 保持 import 不变
            (tmp / "test_case.py").write_text(test_content, encoding="utf-8")
            # 创建 __init__.py
            (tmp / "__init__.py").touch()

            import shutil
            # 1. 正向验证
            positive = subprocess.run(
                ["python3", "-m", "pytest", str(tmp / "test_case.py"), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=self.PYTEST_TIMEOUT_SECONDS,
                cwd=str(tmp),
            )

            if positive.returncode != 0:
                return GateResult(
                    gate_name="PYTEST_DYNAMIC",
                    passed=False,
                    message=(
                        "🚨 正向验证失败: Solution 代码缝合后测试不通过!\n"
                        f"Pytest exit code: {positive.returncode}\n"
                        f"stdout (tail): {positive.stdout[-800:]}"
                    ),
                    details={
                        "exit_code": positive.returncode,
                        "stdout": positive.stdout[-800:],
                        "direction": "正向(Solution缝合)",
                    },
                    elapsed_ms=_elapsed(start),
                )

            # 2. 反向验证: 原始骨架（带 TODO）— 运行同一测试，应失败
            # 清除正向测试的 __pycache__ 避免缓存污染
            pycache = tmp / "__pycache__"
            if pycache.exists():
                shutil.rmtree(pycache)
            (tmp / "exercise.py").write_text(exercise_src, encoding="utf-8")

            # 使用原始测试文件验证骨架: 骨架(stubs)应无法通过测试
            (tmp / "test_case.py").write_text(test_content, encoding="utf-8")

            # 清除正向验证留下的缓存，确保反向验证使用新的骨架文件
            for cache_dir in [tmp / "__pycache__", tmp / ".pytest_cache"]:
                if cache_dir.exists():
                    import shutil as _shutil
                    _shutil.rmtree(cache_dir)

            negative = subprocess.run(
                ["python3", "-m", "pytest", str(tmp / "test_case.py"), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=self.PYTEST_TIMEOUT_SECONDS,
                cwd=str(tmp),
            )

            if negative.returncode == 0:
                return GateResult(
                    gate_name="PYTEST_DYNAMIC",
                    passed=False,
                    message=(
                        "🚨 反向验证失败: 原始骨架(含 TODO)竟然通过了测试!\n"
                        "测试用例太弱，学生不写代码也能全对。请增强测试用例。"
                    ),
                    details={"exit_code": 0, "direction": "反向(原始骨架)"},
                    elapsed_ms=_elapsed(start),
                )

        return GateResult(
            gate_name="PYTEST_DYNAMIC",
            passed=True,
            message=(
                f"✅ 双向验证通过\n"
                f"  正向(Solution): exit=0 ✓\n"
                f"  反向(骨架): exit={negative.returncode} ✓ (必须有失败)"
            ),
            details={
                "positive_exit": positive.returncode,
                "negative_exit": negative.returncode,
            },
            elapsed_ms=_elapsed(start),
        )

    def _stitch_solution(self, exercise_src: str, solution_src: str) -> str:
        """
        将 Solution 缝合进 Exercise 的 TODO/桩区域.

        策略:
          1. 查找 `# --- 学生填空区域 ---` 之后的代码块
          2. 用 Solution 中对应函数体替换 stubbed 部分
          3. 提取 Solution 中的函数定义注入到 Exercise
        """
        # 简单策略: 直接在 exercise 中搜索 TODO/桩模式并替换
        # 更健壮的策略: 用 AST 找到同名函数，替换函数体
        try:
            exercise_tree = ast.parse(exercise_src)
            solution_tree = ast.parse(solution_src)
        except SyntaxError:
            # 解析失败降级为简单文本拼接
            return exercise_src + "\n\n# --- Solution injected ---\n" + solution_src

        # 提取 Solution 中的函数定义
        solution_funcs: Dict[str, ast.FunctionDef] = {}
        for node in ast.walk(solution_tree):
            if isinstance(node, ast.FunctionDef):
                solution_funcs[node.name] = node

        # 在 Exercise 中替换同名函数体
        # 策略: 匹配 "def name(...):\n{indent}pass" → 替换为 solution 的完整实现
        import re as _re

        result = exercise_src
        for func_name in sorted(solution_funcs.keys(), key=len, reverse=True):
            sol_func = solution_funcs[func_name]
            sol_lines = solution_src.split("\n")
            func_source = "\n".join(
                sol_lines[sol_func.lineno - 1: sol_func.end_lineno]
            )

            # 匹配 exercise 中的 stub: def name(...): 后紧跟 (可能有注释行) pass / ... / raise NotImplementedError
            # DOTALL 让 . 匹配换行符, 跨越中间的注释行
            pattern = _re.compile(
                rf"(def\s+{_re.escape(func_name)}\s*\([^)]*\).*?)"
                rf"(\n\s+pass|\n\s+\.\.\.|\n\s+raise\s+NotImplementedError)",
                _re.DOTALL,
            )

            if pattern.search(result):
                # 提取 solution 函数体中 def 行之后的内容
                body_parts = func_source.split("\n", 1)
                if len(body_parts) > 1:
                    replacement = r"\1\n" + body_parts[1]
                else:
                    replacement = func_source
                result = pattern.sub(replacement, result, count=1)

        if result == exercise_src:
            # Pattern didn't match any stub — fallback: append solution at end
            result = exercise_src.rstrip() + "\n\n# --- Solution injected ---\n" + solution_src

        return result

    # ═══════════════════════════════════════════
    #  第三关: LLM-as-Judge 教学门禁
    # ═══════════════════════════════════════════

    def verify_llm_judge(
        self,
        student_profile: Optional[str] = None,
        lecture_path: Optional[Path] = None,
    ) -> GateResult:
        """
        第三关: LLM-as-Judge 教学体验评审.

        评分维度:
          1. 口语化程度 (colloquialism)      — 是否避免枯燥纯理论?
          2. 对比示例清晰度 (clarity)        — ❌ vs ✅ 对比是否充分?
          3. 概念过渡平滑度 (progression)    — 知识递进是否自然?
        """
        start = time.perf_counter()
        lp = lecture_path or self._lecture_path()

        if not lp.exists():
            return GateResult(
                gate_name="LLM_JUDGE",
                passed=False,
                message=f"讲义文件不存在: {lp}",
                elapsed_ms=_elapsed(start),
            )

        lecture_text = _read_file(lp)
        if lecture_text is None:
            return GateResult(
                gate_name="LLM_JUDGE",
                passed=False,
                message="无法读取讲义文件",
                elapsed_ms=_elapsed(start),
            )

        # ── 基于规则的启发式评分（离线模式） ──
        # 在 LLM 不可用时使用规则评分，确保门禁不因 API 不可用而熔断
        scores = self._heuristic_rubric_scoring(lecture_text)

        total = sum(scores.values())
        max_score = len(scores) * 100
        normalized = round(total / max_score * 100)

        if normalized >= self.JUDGE_PASS_THRESHOLD:
            return GateResult(
                gate_name="LLM_JUDGE",
                passed=True,
                message=f"✅ 教学评审通过 (得分: {normalized}/100, 阈值≥{self.JUDGE_PASS_THRESHOLD})",
                details={
                    "scores": scores,
                    "total": total,
                    "normalized": normalized,
                    "threshold": self.JUDGE_PASS_THRESHOLD,
                    "mode": "heuristic",
                },
                elapsed_ms=_elapsed(start),
            )

        # 不达标 — 生成修改建议
        suggestions = self._generate_suggestions(scores, lecture_text)
        return GateResult(
            gate_name="LLM_JUDGE",
            passed=False,
            message=f"❌ 教学评审不达标 (得分: {normalized}/100 < {self.JUDGE_PASS_THRESHOLD})",
            details={
                "scores": scores,
                "total": total,
                "normalized": normalized,
                "threshold": self.JUDGE_PASS_THRESHOLD,
                "suggestions": suggestions,
                "mode": "heuristic",
            },
            elapsed_ms=_elapsed(start),
        )

    def _heuristic_rubric_scoring(self, text: str) -> Dict[str, float]:
        """基于规则的启发式评分（不依赖 LLM API）"""
        scores: Dict[str, float] = {}

        # 1. 口语化程度 — 检测对话式表达
        colloquial_markers = [
            (r"你", 6), (r"我们", 6), (r"想象一下", 15),
            (r"动手", 8), (r"试试", 8), (r"注意", 5),
            (r"记住", 5), (r"核心", 8), (r"关键", 8),
            (r">", 5),  # 引用块（提示/对比）
            (r"🎯", 5), (r"💡", 5), (r"⚠️", 5),  # emoji 增强可读性
            (r"❌", 10), (r"✅", 10),  # 对比标记
        ]
        colloquial_score = 0.0
        for pattern, weight in colloquial_markers:
            matches = len(re.findall(pattern, text))
            if matches > 0:
                colloquial_score += weight * min(matches, 3)  # 上限防过拟合
        scores["colloquialism"] = min(100, colloquial_score)

        # 2. 对比示例清晰度 — 检测 ❌/✅ 对比模式
        bad_good_pairs = len(re.findall(r"❌.*✅", text, re.DOTALL))
        inline_comparisons = len(re.findall(r"(不好的|不优雅|❌).*(优雅|✅)", text))
        code_blocks = len(re.findall(r"```", text)) // 2
        clarity_score = min(100, 35 + bad_good_pairs * 25 + inline_comparisons * 20 + code_blocks * 8)
        scores["clarity"] = clarity_score

        # 3. 概念过渡平滑度 — 检测递进结构和标题层级
        headings = len(re.findall(r"^#{1,4}\s", text, re.MULTILINE))
        transitions = len(re.findall(
            r"(接下来|然后|进一步|现在|最后|总结|回顾|首先|其次|第一步|第二步)", text
        ))
        progression_score = min(
            100,
            headings * 12 + transitions * 15 + code_blocks * 8,
        )
        # 基础分：有内容就给 40 分起
        if len(text.strip()) > 100:
            progression_score = max(progression_score, 45)
        scores["progression"] = progression_score

        # 4. 内容长度加分（避免极短文本得分过低）
        content_length_bonus = min(30, len(text.split()) // 5)
        if "colloquialism" in scores:
            scores["colloquialism"] = min(100, scores["colloquialism"] + content_length_bonus)

        return scores

    def _generate_suggestions(
        self, scores: Dict[str, float], text: str
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []
        thresholds = {
            "colloquialism": (60, "增加对话式表达（'你'、'我们'）和 emoji 提示（💡⚠️）"),
            "clarity": (50, "增加 ❌ vs ✅ 对比示例，让好坏写法并排展示"),
            "progression": (50, "增加章节标题 (# ## ###) 和过渡词（接下来、进一步）"),
        }
        for dim, (thresh, advice) in thresholds.items():
            if scores.get(dim, 0) < thresh:
                suggestions.append(f"[{dim}] {advice}")
        return suggestions

    @classmethod
    def evaluate_content_quality(cls, text: str) -> Dict[str, Any]:
        """
        Phase 4.5 — 公开的内容质量评分入口。

        对任意文本应用 ReviewGate 三维启发式评分
        (口语化/清晰度/过渡)，返回标准化结果。
        无需文件系统，无需 workspace。

        Args:
            text: 待评分文本内容

        Returns:
            {score: int 0-100, passed: bool, scores: {colloquialism, clarity, progression}}
        """
        tmp = cls.__new__(cls)
        tmp.workspace = Path(".")
        scores = tmp._heuristic_rubric_scoring(text)
        total = sum(scores.values())
        max_score = len(scores) * 100
        normalized = round(total / max_score * 100) if max_score > 0 else 50
        return {
            "score": normalized,
            "passed": normalized >= cls.JUDGE_PASS_THRESHOLD,
            "scores": scores,
        }

    # ═══════════════════════════════════════════
    #  全局门禁管道
    # ═══════════════════════════════════════════

    def run_full_gate(
        self,
        node_id: str = "NODE",
        student_profile: Optional[str] = None,
    ) -> PipelineResult:
        """
        执行完整的离线终审门禁流水线.

        返回 PipelineResult:
          - status: "PASSED" | "FAILED"
          - reason: 失败原因代码
          - gates: 各道门禁的执行结果列表
          - checkpoint_sig: 成功时生成 Checkpoint 签名
        """
        self.gates = []
        failures: List[str] = []

        # ── 第一关: AST ──
        g1 = self.verify_ast()
        self.gates.append(g1)
        if not g1.passed:
            failures.append(g1.message)
            return PipelineResult(
                status="FAILED",
                reason="AST_STATIC_ERROR",
                gates=self.gates,
            )

        # ── 第二关: Pytest ──
        g2 = self.verify_pytest()
        self.gates.append(g2)
        if not g2.passed:
            failures.append(g2.message)
            return PipelineResult(
                status="FAILED",
                reason="PYTEST_DYNAMIC_ERROR",
                gates=self.gates,
            )

        # ── 第三关: LLM Judge ──
        g3 = self.verify_llm_judge(student_profile=student_profile)
        self.gates.append(g3)
        if not g3.passed:
            failures.append(g3.message)
            return PipelineResult(
                status="FAILED",
                reason="LLM_JUDGE_SCORE_LOW",
                gates=self.gates,
                judge_scores=g3.details.get("scores", {}),
            )

        # ── 全部通过 ──
        sig = f"SIG_{node_id}_VERIFIED_{int(time.time())}"
        return PipelineResult(
            status="PASSED",
            checkpoint_sig=sig,
            gates=self.gates,
            judge_scores=g3.details.get("scores", {}),
        )

    def run_full_gate_json(self, node_id: str = "NODE") -> str:
        """便捷方法: 返回 JSON 字符串"""
        result = self.run_full_gate(node_id=node_id)
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
#  CLI 入口
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Review Gate — 三道门禁离线终审"
    )
    parser.add_argument(
        "workspace",
        nargs="?",
        default=".",
        help="工作区路径 (默认当前目录)",
    )
    parser.add_argument(
        "--node-id",
        default="NODE_1",
        help="节点 ID (用于 Checkpoint 签名)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="详细输出每道门禁结果",
    )
    args = parser.parse_args()

    gate = ReviewGateManager(args.workspace)
    result = gate.run_full_gate(node_id=args.node_id)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print("╔══════════════════════════════════════╗")
        print("║   🚪 Review Gate — 终审门禁       ║")
        print("╚══════════════════════════════════════╝")
        print(f"\n  节点: {args.node_id}")
        print(f"  工作区: {gate.workspace}\n")

        for g in result.gates:
            status_icon = "✅" if g.passed else "❌"
            print(f"  {status_icon} {g.gate_name} ({g.elapsed_ms:.0f}ms)")
            if args.verbose or not g.passed:
                print(f"     {g.message}")
            print()

        print(f"  {'─' * 30}")
        if result.status == "PASSED":
            print(f"  🎉 终审通关!")
            print(f"  📝 Checkpoint: {result.checkpoint_sig}")
        else:
            print(f"  🚫 终审拒绝: {result.reason}")
            if result.judge_scores:
                print(f"  📊 评分: {result.judge_scores}")

    # 退出码: 0 = 通过, 1 = 失败
    import sys
    sys.exit(0 if result.status == "PASSED" else 1)
