"""
Phase 9 — Offline Evaluation Pipeline

支持:
  - LLM-as-Judge: 用大模型评估输出质量
  - Rule-based Judge: 基于规则的快速评估
  - 批量跑 student cases

输出:
  EvaluationReport — profile accuracy, plan quality, recommendation relevance
"""

from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class EvaluationCase:
    """评估测试用例"""
    case_id: str
    profile: Dict[str, str]           # 学生画像
    history: str                      # 学生历史描述
    expected_behavior: Dict[str, Any] # 期望行为
    category: str = "general"         # beginner | intermediate | advanced | edge

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "profile": self.profile,
            "history": self.history,
            "expected_behavior": self.expected_behavior,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationCase":
        return cls(
            case_id=data["case_id"],
            profile=data["profile"],
            history=data["history"],
            expected_behavior=data.get("expected_behavior", {}),
            category=data.get("category", "general"),
        )


@dataclass
class EvaluationReport:
    """评估报告"""
    report_id: str
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    profile_accuracy: float = 0.0
    plan_quality: float = 0.0
    recommendation_relevance: float = 0.0
    scores: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "profile_accuracy": self.profile_accuracy,
            "plan_quality": self.plan_quality,
            "recommendation_relevance": self.recommendation_relevance,
            "scores": self.scores,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# Rule-based Judge
# ──────────────────────────────────────────────

class RuleBasedJudge:
    """基于规则的快速评估 (不需要 LLM)"""

    DIMENSIONS = [
        "knowledge_base", "cognitive_style", "error_prone_bias",
        "learning_pace", "interaction_preference", "frustration_threshold",
    ]

    VALID_VALUES = {
        "knowledge_base": {"junior_dev", "mid_level", "senior"},
        "cognitive_style": {"visual_dominant", "text_linear", "auditory"},
        "learning_pace": {"fast_track", "normal", "deep_dive"},
        "interaction_preference": {"code_sandbox", "quiz_first", "passive_read"},
        "frustration_threshold": {"low", "medium", "high"},
    }

    def score_profile(self, profile_dict: Dict[str, str], expected: Dict[str, Any]) -> float:
        """评估画像准确性"""
        if not profile_dict:
            return 0.0
        hits = 0
        total = 0
        for dim in self.DIMENSIONS:
            if dim in expected:
                total += 1
                if dim in self.VALID_VALUES and profile_dict.get(dim) in self.VALID_VALUES[dim]:
                    hits += 1
                elif profile_dict.get(dim):
                    hits += 0.5
        # bonus: all 6 dimensions present
        if all(d in profile_dict for d in self.DIMENSIONS):
            hits += 1
            total += 1
        return round(hits / max(total, 1), 2)

    def score_plan(self, plan: Any) -> float:
        """评估学习路径质量"""
        if plan is None:
            return 0.0
        score = 0.0
        try:
            nodes = getattr(plan, "nodes", [])
            if nodes:
                score += 0.3  # has nodes
            if getattr(plan, "strategy_rationale", ""):
                score += 0.2  # has rationale
            if getattr(plan, "total_minutes", 0) > 0:
                score += 0.2
            if getattr(plan, "alternative_paths", []):
                score += 0.15
            if len(nodes) >= 2:
                score += 0.15
        except Exception:
            pass
        return min(score, 1.0)

    def score_recommendations(self, resource_plan: Any) -> float:
        """评估推荐相关性"""
        if resource_plan is None:
            return 0.0
        score = 0.0
        try:
            resources = getattr(resource_plan, "recommended_resources", [])
            if resources and len(resources) >= 1:
                score += 0.4
            if getattr(resource_plan, "reasoning", ""):
                score += 0.2
            if getattr(resource_plan, "today_goal", ""):
                score += 0.2
            # 检查是否有可解释 reason
            explained = sum(1 for r in resources if getattr(r, "reason", ""))
            if explained >= len(resources) * 0.5:
                score += 0.2
        except Exception:
            pass
        return min(score, 1.0)


# ──────────────────────────────────────────────
# LLM-as-Judge
# ──────────────────────────────────────────────

class LLMJudge:
    """LLM 作为评估器 (需要 router)"""

    def __init__(self, router: Any = None):
        self.router = router

    def evaluate(
        self,
        case: EvaluationCase,
        actual_profile: Dict[str, str],
        actual_plan_summary: str,
        actual_recommendation_summary: str,
    ) -> Dict[str, float]:
        """LLM 评估输出质量"""
        if not self.router:
            return {"profile_accuracy": 0.0, "plan_quality": 0.0, "recommendation_relevance": 0.0}

        prompt = f"""你是一个教育质量评估专家。请评估以下教学系统的输出质量。

学生情况: {case.history[:200]}
期望画像: {json.dumps(case.profile, ensure_ascii=False)}
实际画像: {json.dumps(actual_profile, ensure_ascii=False)}
学习路径: {actual_plan_summary[:200]}
资源推荐: {actual_recommendation_summary[:200]}

请输出 JSON:
{{"profile_accuracy": 0.0-1.0, "plan_quality": 0.0-1.0, "recommendation_relevance": 0.0-1.0, "comments": "一句话评论"}}
只输出 JSON。"""

        try:
            payload = {
                "model": os.environ.get("LLM_MODEL", "spark-pro"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }
            response = self.router.route_request("MetaReflector", payload)
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            data = json.loads(content)
            return {
                "profile_accuracy": float(data.get("profile_accuracy", 0)),
                "plan_quality": float(data.get("plan_quality", 0)),
                "recommendation_relevance": float(data.get("recommendation_relevance", 0)),
            }
        except Exception:
            return {"profile_accuracy": 0.0, "plan_quality": 0.0, "recommendation_relevance": 0.0}


# ──────────────────────────────────────────────
# EvaluationRunner
# ──────────────────────────────────────────────

class EvaluationRunner:
    """
    批量评估运行器.

    使用:
        runner = EvaluationRunner(profile_agent, planner, recommender)
        report = runner.run_benchmark("datasets/students/benchmark.json")
        print(report.to_json())
    """

    def __init__(
        self,
        profile_agent: Any,
        planner: Any,
        recommender: Any,
        memory_manager: Any = None,
        llm_judge: Optional[LLMJudge] = None,
    ):
        self.profile_agent = profile_agent
        self.planner = planner
        self.recommender = recommender
        self.memory = memory_manager
        self.rule_judge = RuleBasedJudge()
        self.llm_judge = llm_judge or LLMJudge()

    def load_cases(self, path: str) -> List[EvaluationCase]:
        """加载测试用例"""
        data = json.loads(Path(path).read_text())
        return [EvaluationCase.from_dict(c) for c in data.get("cases", [])]

    def run_case(self, case: EvaluationCase) -> Dict[str, Any]:
        """运行单个评估用例"""
        result = {
            "case_id": case.case_id,
            "profile_accuracy": 0.0,
            "plan_quality": 0.0,
            "recommendation_relevance": 0.0,
            "error": None,
        }

        try:
            # 1. Profile
            profile_result = self.profile_agent.extract(case.history)
            profile_dict = profile_result.profile.to_dict()
            result["profile_accuracy"] = self.rule_judge.score_profile(profile_dict, case.profile)

            # 2. Plan
            from src.core.agent_router import DynamicProfile
            plan = self.planner.plan(
                DynamicProfile(**profile_dict),
                course_id="python_advanced",
            )
            plan_summary = f"nodes={len(plan.nodes)}, minutes={plan.total_minutes}"
            result["plan_quality"] = self.rule_judge.score_plan(plan)

            # 3. Recommendations
            if self.memory:
                mem = self.memory.get_student_memory(case.case_id)
                res_plan = self.recommender.recommend(case.case_id, mem)
                result["recommendation_relevance"] = self.rule_judge.score_recommendations(res_plan)

            # Optional: LLM judge
            if self.llm_judge.router:
                llm_scores = self.llm_judge.evaluate(
                    case, profile_dict, plan_summary, str(res_plan.recommended_resources[:2]) if 'res_plan' in dir() else "",
                )
                # 与规则评分取平均
                result["profile_accuracy"] = (result["profile_accuracy"] + llm_scores["profile_accuracy"]) / 2
                result["plan_quality"] = (result["plan_quality"] + llm_scores["plan_quality"]) / 2

        except Exception as e:
            result["error"] = str(e)

        return result

    def run_benchmark(self, dataset_path: str) -> EvaluationReport:
        """运行完整基准测试"""
        cases = self.load_cases(dataset_path)
        report = EvaluationReport(
            report_id=f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            total_cases=len(cases),
        )

        for case in cases:
            score_entry = self.run_case(case)
            report.scores.append(score_entry)
            if score_entry.get("error"):
                report.failed += 1
                report.errors.append(f"{case.case_id}: {score_entry['error']}")
            else:
                report.passed += 1

        # 汇总
        if report.total_cases > 0:
            report.profile_accuracy = round(
                sum(s["profile_accuracy"] for s in report.scores) / report.total_cases, 2
            )
            report.plan_quality = round(
                sum(s["plan_quality"] for s in report.scores) / report.total_cases, 2
            )
            report.recommendation_relevance = round(
                sum(s["recommendation_relevance"] for s in report.scores) / report.total_cases, 2
            )

        return report


# ──────────────────────────────────────────────
# 预置 Benchmark Dataset 生成
# ──────────────────────────────────────────────

def generate_benchmark_dataset(output_path: str) -> None:
    """生成 20 个模拟学生的基准数据集"""
    cases = [
        # ── Beginners (8) ──
        {
            "case_id": "beginner_01", "category": "beginner",
            "profile": {"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant", "learning_pace": "fast_track"},
            "history": "我是大一新生，完全零基础，喜欢看视频和图解学习。想快速学会Python。",
            "expected_behavior": {"should_detect_knowledge": "junior_dev", "should_detect_style": "visual_dominant"},
        },
        {
            "case_id": "beginner_02", "category": "beginner",
            "profile": {"knowledge_base": "junior_dev", "cognitive_style": "text_linear", "learning_pace": "deep_dive"},
            "history": "编程小白，没学过任何编程语言。喜欢慢慢看书，一步步理解每个概念。",
            "expected_behavior": {"should_detect_knowledge": "junior_dev", "should_detect_style": "text_linear"},
        },
        {
            "case_id": "beginner_03", "category": "beginner",
            "profile": {"knowledge_base": "junior_dev", "cognitive_style": "auditory", "frustration_threshold": "low"},
            "history": "刚开始接触编程，更喜欢听课和听讲解来学习。很容易放弃，需要多鼓励。",
            "expected_behavior": {"should_detect_knowledge": "junior_dev", "should_detect_frustration": "low"},
        },
        {
            "case_id": "beginner_04", "category": "beginner",
            "profile": {"knowledge_base": "junior_dev", "interaction_preference": "code_sandbox"},
            "history": "新手，但是喜欢自己动手敲代码，边写边学效率最高。",
            "expected_behavior": {"should_detect_interaction": "code_sandbox"},
        },
        {
            "case_id": "beginner_05", "category": "beginner",
            "profile": {"knowledge_base": "junior_dev", "error_prone_bias": "magic_syntax_blind"},
            "history": "Python小白，看到@装饰器这种黑魔法就完全懵了。",
            "expected_behavior": {"should_detect_error_bias": "magic_syntax_blind"},
        },
        {
            "case_id": "beginner_06", "category": "beginner",
            "profile": {"knowledge_base": "junior_dev", "learning_pace": "fast_track", "frustration_threshold": "low"},
            "history": "零基础急着学Python找工作，容易焦虑放弃。",
            "expected_behavior": {"should_detect_pace": "fast_track", "should_detect_frustration": "low"},
        },
        {
            "case_id": "beginner_07", "category": "beginner",
            "profile": {"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant", "interaction_preference": "quiz_first"},
            "history": "刚学编程，喜欢先做题测试自己理解没有，配合视频学习。",
            "expected_behavior": {"should_detect_interaction": "quiz_first"},
        },
        {
            "case_id": "beginner_08", "category": "beginner",
            "profile": {"knowledge_base": "junior_dev", "error_prone_bias": "indentation_errors"},
            "history": "刚开始学Python，缩进老是出错，冒号总忘。",
            "expected_behavior": {"should_detect_error_bias": "indentation_errors"},
        },

        # ── Intermediate (6) ──
        {
            "case_id": "intermediate_01", "category": "intermediate",
            "profile": {"knowledge_base": "mid_level", "cognitive_style": "visual_dominant", "learning_pace": "normal"},
            "history": "学了一段时间Python，会写基本函数和类。喜欢看视频和图解深入学习。",
            "expected_behavior": {"should_detect_knowledge": "mid_level"},
        },
        {
            "case_id": "intermediate_02", "category": "intermediate",
            "profile": {"knowledge_base": "mid_level", "interaction_preference": "code_sandbox", "learning_pace": "deep_dive"},
            "history": "有Python基础，喜欢通过实际项目学习，想深入搞懂底层原理。",
            "expected_behavior": {"should_detect_knowledge": "mid_level", "should_detect_pace": "deep_dive"},
        },
        {
            "case_id": "intermediate_03", "category": "intermediate",
            "profile": {"knowledge_base": "mid_level", "error_prone_bias": "type_mismatch"},
            "history": "写过一段时间Python，经常遇到类型报错，int和str搞混。",
            "expected_behavior": {"should_detect_error_bias": "type_mismatch"},
        },
        {
            "case_id": "intermediate_04", "category": "intermediate",
            "profile": {"knowledge_base": "mid_level", "cognitive_style": "text_linear", "frustration_threshold": "high"},
            "history": "有一定基础，喜欢通过文档和书籍系统学习，不怕困难。",
            "expected_behavior": {"should_detect_frustration": "high"},
        },
        {
            "case_id": "intermediate_05", "category": "intermediate",
            "profile": {"knowledge_base": "mid_level", "interaction_preference": "quiz_first"},
            "history": "学过Python基础，喜欢通过刷题和测验来检验学习效果。",
            "expected_behavior": {"should_detect_interaction": "quiz_first"},
        },
        {
            "case_id": "intermediate_06", "category": "intermediate",
            "profile": {"knowledge_base": "mid_level", "error_prone_bias": "import_issues"},
            "history": "有一定经验，但导入模块经常找不到路径，import出错很多。",
            "expected_behavior": {"should_detect_error_bias": "import_issues"},
        },

        # ── Advanced (4) ──
        {
            "case_id": "advanced_01", "category": "advanced",
            "profile": {"knowledge_base": "senior", "cognitive_style": "text_linear", "learning_pace": "deep_dive"},
            "history": "多年Python开发经验，熟练掌握各种框架。喜欢通过文档深入学习，想彻底搞懂底层。",
            "expected_behavior": {"should_detect_knowledge": "senior"},
        },
        {
            "case_id": "advanced_02", "category": "advanced",
            "profile": {"knowledge_base": "senior", "interaction_preference": "code_sandbox", "frustration_threshold": "high"},
            "history": "资深开发者，经常写项目，抗压能力强，喜欢挑战。",
            "expected_behavior": {"should_detect_frustration": "high"},
        },
        {
            "case_id": "advanced_03", "category": "advanced",
            "profile": {"knowledge_base": "senior", "cognitive_style": "visual_dominant"},
            "history": "老手程序员，但喜欢通过架构图和可视化理解复杂系统。",
            "expected_behavior": {"should_detect_knowledge": "senior", "should_detect_style": "visual_dominant"},
        },
        {
            "case_id": "advanced_04", "category": "advanced",
            "profile": {"knowledge_base": "senior", "error_prone_bias": "variable_scoping"},
            "history": "经验丰富但偶尔在闭包和作用域上踩坑，变量作用域容易混淆。",
            "expected_behavior": {"should_detect_error_bias": "variable_scoping"},
        },

        # ── Edge cases (2) ──
        {
            "case_id": "edge_01", "category": "edge",
            "profile": {"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant"},
            "history": "想学Python。",  # 极简信息
            "expected_behavior": {"should_not_crash": True, "should_return_defaults": True},
        },
        {
            "case_id": "edge_02", "category": "edge",
            "profile": {"knowledge_base": "junior_dev"},
            "history": "",  # 空输入
            "expected_behavior": {"should_not_crash": True},
        },
    ]

    dataset = {
        "name": "A3 Benchmark Dataset v1",
        "description": "20 个模拟学生, 覆盖 beginner/intermediate/advanced/edge",
        "total_cases": len(cases),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases": cases,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(dataset, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import sys as _sys
    out = _sys.argv[1] if len(_sys.argv) > 1 else "datasets/students/benchmark.json"
    generate_benchmark_dataset(out)
    print(f"Generated {out} with benchmark dataset")
