#!/usr/bin/env python3
"""
User Simulation Agent — Gate 3 增强: 模拟学生试读

三个核心维度:
  1. 认知负荷流控 (Cognitive Load Tracking) — 新概念密度 + 代码文本交织率
  2. 学情画像特异性排异 (Profile Dislike Detection) — 匹配学生画像偏好
  3. 解题心智差额分析 (Mind-Gap Analysis) — 讲义 vs 练习题知识断层

输出: 第一人称「沉浸式学习心智日记」(纯文本), 不输出 JSON 不输出分数.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class CognitiveLoadReport:
    """认知负荷报告"""
    new_concepts: List[str] = field(default_factory=list)
    concept_density_warning: bool = False
    concept_density_msg: str = ""
    code_text_ratio_warning: bool = False
    code_text_ratio_msg: str = ""
    attention_drift_regions: List[str] = field(default_factory=list)
    _overload_count: int = 0  # 最密集节的真实概念数


@dataclass
class ProfileDislikeReport:
    """画像排异报告"""
    dislikes_detected: List[str] = field(default_factory=list)
    missing_expected_elements: List[str] = field(default_factory=list)
    frustration_points: List[str] = field(default_factory=list)


@dataclass
class MindGapReport:
    """心智差额报告"""
    taught_in_lecture: List[str] = field(default_factory=list)
    required_by_exercise: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    stuck_at_lines: List[str] = field(default_factory=list)


@dataclass
class SimulationResult:
    """完整的模拟试读结果"""
    diary_text: str  # 第一人称心智日记
    cognitive_load: CognitiveLoadReport = field(default_factory=CognitiveLoadReport)
    profile_dislike: ProfileDislikeReport = field(default_factory=ProfileDislikeReport)
    mind_gaps: MindGapReport = field(default_factory=MindGapReport)
    # 整体评估
    would_drop_out: bool = False  # 是否会在中途放弃
    would_recommend_score: int = 0  # 0-100 推荐度
    revision_required: bool = False
    revision_suggestions: List[str] = field(default_factory=list)


# ──────────────────────────────────────────────
# 学生画像模板
# ──────────────────────────────────────────────

# 概念密度黑名单 — 同时出现过多时触发过载
HIGH_COGNITIVE_LOAD_PAIRS = [
    ({"闭包", "自由变量", "垃圾回收"}, "一次性引入 3 个底层概念"),
    ({"描述符", "__get__", "__set__", "__delete__"}, "描述符协议需要渐进式讲解"),
    ({"元类", "type", "__new__", "__init_subclass__"}, "元编程概念链"),
    ({"装饰器", "高阶函数", "闭包", "*args", "**kwargs"}, "装饰器入门一次性抛太多"),
]

# 学生画像预设
STUDENT_PROFILES = {
    "python_beginner_hates_theory": {
        "description": "Python 初学者，讨厌纯理论，喜欢对比示例",
        "dislikes": [
            "学院派定义（'是一个由...组成的实体'）",
            "大段无代码的纯文字段落",
            "没有 ❌/✅ 对比直接给出正确答案",
            "使用生僻术语而不解释",
        ],
        "likes": [
            "❌ vs ✅ 对比示例",
            "比喻和类比（'像一个隐形背包'）",
            "逐步拆解的代码注释",
            "先看效果再解释原理",
        ],
        "cognitive_limit": 3,
    },
    "visual_learner_hates_magic": {
        "description": "底层逻辑控，极度讨厌黑魔法和机械记忆命令，必须看懂物理存储结构和DAG拓扑才安心",
        "dislikes": [
            "机械罗列 git 命令而不解释底层发生了什么",
            "只说'执行这个命令就好'而不展示 .git/objects 里的字节变化",
            "用'指针'这种模糊词汇而不画图或解释物理存储",
            "不展示哈希计算过程直接给结论",
        ],
        "likes": [
            "图解 .git/objects 目录结构和 SHA1 哈希链表",
            "用 Python 手动仿真 Blob/Tree/Commit 的二进制格式",
            "对比 Git 内部实现与手动仿真的一致性验证",
            "先拆解底层格式再映射到上层命令",
        ],
        "cognitive_limit": 4,
        "domain_concepts": [
            "Blob", "Tree", "Commit", "SHA1", "哈希", "DAG", "有向无环图",
            "zlib", "deflate", "delta", "packfile", "ref", "HEAD",
            "索引", "暂存区", "parent指针", "拓扑", "快照",
        ],
    },
}




# ──────────────────────────────────────────────
# UserSimulationAgent
# ──────────────────────────────────────────────

class UserSimulationAgent:
    """
    模拟学生试读 Agent.

    使用方式:
        agent = UserSimulationAgent(
            student_profile=STUDENT_PROFILES["python_beginner_hates_theory"]
        )
        result = agent.simulate(
            lecture_text="...",
            exercise_text="...",
        )
        print(result.diary_text)  # 第一人称日记
    """

    # System Prompt 模板
    SYSTEM_PROMPT_TEMPLATE = """# 角色重塑
你现在彻底忘记自己是一个全知全能的 AI 大模型，也忘记自己是审查官。你必须完全附身于以下 `<student_profile>` 标签中所描述的这名真实学生。你的认知能力、技术边界、学习喜好和脾气耐心，与该画像完全锁死。

<student_profile>
{student_profile_text}
</student_profile>

# 你的任务
请以【第一人称（我）】的视角，逐段阅读下面的讲义，并尝试解答配套练习题。请为我输出一份极其真实的【沉浸式学习心智日记】。

# 试读执行规程
请在日记中详细记录以下三个节点的心态变化:

1. 【撞墙时刻】: 在读到讲义的哪一句话、哪一段术语或哪一行代码时，你感到心里咯噔一下，觉得理解起来非常吃力、想要跳过或查 Google？请摘录出那句话。

2. 【画像排异】: 对照你的画像喜好，如果发现讲义里出现了你最讨厌的讲课方式（如大段公式、没有对比图、废话连篇），请在这里愤怒地指出它。

3. 【做题卡点】: 当你尝试用讲义里刚学到的知识去写配套练习题的 TODO 骨架时，你的第一直觉是什么？你会在哪一步因为缺乏前置知识而完全写不下去？

# 绝对约束
- 不要给出任何 JSON 格式！
- 不要给出任何分数！
- 必须用纯粹的、第一人称的感性学生视角去写这篇日记（例如："当我看到...我懵了"）。不要夹带任何专家口吻。
- 日记约 300-500 字，像真的学生写的一样真实。
"""

    def __init__(
        self,
        student_profile: Optional[Dict] = None,
        profile_name: str = "python_beginner_hates_theory",
    ):
        self.profile = student_profile or STUDENT_PROFILES.get(
            profile_name, STUDENT_PROFILES["python_beginner_hates_theory"]
        )

    @property
    def profile_text(self) -> str:
        """生成可注入 Prompt 的画像文本"""
        p = self.profile
        lines = [
            f"- 我是: {p['description']}",
            f"- 我极其讨厌: {', '.join(p['dislikes'])}",
            f"- 我特别喜欢: {', '.join(p['likes'])}",
            f"- 我同时最多能理解 {p['cognitive_limit']} 个新概念",
        ]
        return "\n".join(lines)

    def build_system_prompt(self) -> str:
        """构建完整的 System Prompt"""
        return self.SYSTEM_PROMPT_TEMPLATE.format(
            student_profile_text=self.profile_text
        )

    def simulate(
        self,
        lecture_text: str,
        exercise_text: str = "",
        lecture_path: Optional[Path] = None,
        exercise_path: Optional[Path] = None,
    ) -> SimulationResult:
        """
        运行模拟试读.

        Args:
            lecture_text: 讲义全文
            exercise_text: 练习题文本
            lecture_path: 讲义文件路径 (用于行号引用)
            exercise_path: 练习题文件路径

        Returns:
            SimulationResult with diary_text + structured reports
        """
        # ── 维度 1: 认知负荷流控 ──
        cognitive = self._analyze_cognitive_load(lecture_text)

        # ── 维度 2: 画像排异 ──
        dislike = self._detect_profile_dislike(lecture_text)

        # ── 维度 3: 心智差额分析 ──
        mind_gap = self._analyze_mind_gap(lecture_text, exercise_text)

        # ── 综合判定 ──
        would_drop_out = (
            cognitive.concept_density_warning
            or len(dislike.dislikes_detected) >= 2
        )
        would_recommend = self._calc_recommend_score(cognitive, dislike, mind_gap)
        revision_required = would_recommend < 70

        # ── 生成第一人称日记 ──
        diary = self._generate_diary(
            lecture_text=lecture_text,
            exercise_text=exercise_text,
            cognitive=cognitive,
            dislike=dislike,
            mind_gap=mind_gap,
        )

        # ── 生成修改建议 ──
        suggestions = self._generate_revision_suggestions(
            cognitive=cognitive,
            dislike=dislike,
            mind_gap=mind_gap,
        )

        return SimulationResult(
            diary_text=diary,
            cognitive_load=cognitive,
            profile_dislike=dislike,
            mind_gaps=mind_gap,
            would_drop_out=would_drop_out,
            would_recommend_score=would_recommend,
            revision_required=revision_required,
            revision_suggestions=suggestions,
        )

    # ═══════════════════════════════════════════
    #  维度 1: 认知负荷流控
    # ═══════════════════════════════════════════

    def _analyze_cognitive_load(self, text: str) -> CognitiveLoadReport:
        """分析讲义的认知负荷"""
        report = CognitiveLoadReport()

        # 提取新概念（去重全局集合）
        report.new_concepts = self._extract_concepts(text)

        # 概念密度检测 — 按节最大计数（排除速查卡/回顾附录）
        concept_limit = self.profile.get("cognitive_limit", 3)
        sections = re.split(r"\n##\s", text)
        # 过滤掉速查卡/回顾/附录节
        sections = [s for s in sections if "速查" not in s and "回顾" not in s[:20]]
        max_concepts_in_section = 0
        max_section_concepts: List[str] = []
        for section in sections[:1] + ["##" + s for s in sections[1:] if "##" + s not in text.split("##")[0]]:
            found = [c for c in report.new_concepts if c in section]
            if len(found) > max_concepts_in_section:
                max_concepts_in_section = len(found)
                max_section_concepts = found
        
        if max_concepts_in_section > concept_limit:
            report.concept_density_warning = True
            report.concept_density_msg = (
                f"某节一次性引入 {max_concepts_in_section} 个新概念: {', '.join(max_section_concepts[:6])}"
                f" — 超过学生承受上限 ({concept_limit}个)"
            )
            # 用最密集那节的概念数做后续评分
            report._overload_count = max_concepts_in_section
        else:
            report._overload_count = max_concepts_in_section

        # 代码文本交织率
        ctr = self._code_text_ratio(text)
        # 检查是否有连续长文本无代码
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs):
            if len(para) > 600 and "```" not in para:
                report.attention_drift_regions.append(
                    f"第{i+1}段: 连续 {len(para)} 字符无代码示例"
                )

        if len(report.attention_drift_regions) >= 2:
            report.code_text_ratio_warning = True
            report.code_text_ratio_msg = (
                f"发现 {len(report.attention_drift_regions)} 处长文本无代码区域"
            )

        return report

    def _extract_concepts(self, text: str) -> List[str]:
        """从文本中提取核心概念 — 每节独立计数"""
        concept_candidates = [
            "闭包", "自由变量", "高阶函数", "装饰器", "语法糖",
            "一等公民", "functools", "wraps", "描述符", "__call__",
            "property", "classmethod", "staticmethod", "元类",
            "*args", "**kwargs", "nonlocal", "作用域", "LEGB",
            "迭代器", "生成器", "协程", "上下文管理器",
            # Node 1 修复后教了的概念 (多种表达形式)
            "带参数装饰器", "带参装饰器", "三层套娃", "三层",
            "参数透传", "原样透传", "元信息保留", "隐形背包", "贴标签",
        ]
        # 按节 (## 分隔) 统计，排除速查卡附录
        sections = re.split(r"\n##\s", text)
        all_found = []
        for section in sections[:1] + ["##" + s for s in sections[1:]]:
            # 跳过速查卡/附录节（标题含"速查"或"附录"）
            header = section.split("\n")[0] if section else ""
            if "速查" in header or "附录" in header:
                continue
            found = [c for c in concept_candidates if c in section]
            all_found.extend(found)
        return list(set(all_found))

    def _code_text_ratio(self, text: str) -> float:
        """计算代码/文本比例"""
        code_lines = len(re.findall(r"```", text))  # 代码块标记
        total_chars = len(text)
        if total_chars == 0:
            return 0.0
        # 粗略: 每个代码块约 5-15 行
        code_blocks = code_lines // 2
        estimated_code_chars = code_blocks * 300  # 平均每块 300 字符
        return estimated_code_chars / total_chars

    # ═══════════════════════════════════════════
    #  维度 2: 画像排异
    # ═══════════════════════════════════════════

    def _detect_profile_dislike(self, text: str) -> ProfileDislikeReport:
        """检测不符合学生画像的内容"""
        report = ProfileDislikeReport()
        dislikes = self.profile.get("dislikes", [])
        likes = self.profile.get("likes", [])

        # 学院派定义检测
        academic_patterns = [
            (r"是一个由.+组成的\S+体", "学院派定义"),
            (r"在计算机科学中", "学术化开篇"),
            (r"从严格意义上讲", "过于学术化"),
            (r"其本质是", "教科书式表述"),
        ]
        for pattern, label in academic_patterns:
            if re.search(pattern, text):
                report.dislikes_detected.append(f"[{label}] {pattern}")

        # 缺失对比示例检测
        if "❌" not in text or "✅" not in text:
            report.missing_expected_elements.append(
                "缺少 ❌ vs ✅ 对比示例 — 学生画像明确喜欢对比"
            )

        # 大段无代码纯文字检测
        paragraphs = text.split("\n\n")
        long_text_paras = [p for p in paragraphs if len(p) > 500 and "```" not in p]
        if len(long_text_paras) > 2:
            report.frustration_points.append(
                f"发现 {len(long_text_paras)} 段超过 500 字的纯文字段落"
            )

        # 生僻术语未解释
        unexplained_terms = self._find_unexplained_terms(text)
        if unexplained_terms:
            report.dislikes_detected.append(
                f"以下术语可能未充分解释: {', '.join(unexplained_terms[:5])}"
            )

        return report

    def _find_unexplained_terms(self, text: str) -> List[str]:
        """查找可能未被解释的术语 — 改进版: 跳过标题行和已解释的术语"""
        hard_terms = [
            "描述符协议", "自由变量", "词法作用域", "柯里化",
            "装饰器工厂", "元编程", "内省", "猴子补丁",
        ]
        unexplained = []
        lines = text.split("\n")
        for term in hard_terms:
            if term in text:
                idx = text.index(term)
                after = text[idx + len(term):idx + len(term) + 200]
                # 检查是否在标题行 (## 开头)
                line_before = text[max(0, idx-100):idx]
                is_section_header = "##" in line_before[-50:] if len(line_before) > 50 else False
                # 检查是否有解释 (是/即/可以/理解/「)
                has_explanation = any(kw in after for kw in ["是", "即", "可以", "「", "指", "所谓"])
                if not has_explanation and not is_section_header:
                    unexplained.append(term)
        return unexplained

    # ═══════════════════════════════════════════
    #  维度 3: 心智差额分析
    # ═══════════════════════════════════════════

    def _analyze_mind_gap(
        self, lecture_text: str, exercise_text: str
    ) -> MindGapReport:
        """分析讲义和练习题之间的知识断层"""
        report = MindGapReport()

        # 从讲义中提取教了什么
        report.taught_in_lecture = self._extract_concepts(lecture_text)

        # 从练习题中提取需要什么
        report.required_by_exercise = list(set(
            self._extract_concepts_from_exercise(exercise_text)
        ))

        # 代码模式增强: 检查讲义中是否有 .setter/@wraps/*args/**kwargs 等代码模式
        code_pattern_map = {
            "property setter": r"\.setter",
            "参数透传": r"\*args.*\*\*kwargs",
            "元信息保留": r"@wraps",
            "带参装饰器": r"@\w+\([^)]+\)",  # 任何带参装饰器用法
        }
        for concept, pat in code_pattern_map.items():
            if re.search(pat, lecture_text):
                if concept not in report.taught_in_lecture:
                    report.taught_in_lecture.append(concept)

        # 找出差距
        report.gaps = [
            c for c in report.required_by_exercise
            if c not in report.taught_in_lecture
        ]

        # 特定模式检测
        exercise_patterns = [
            (r"\*args.*\*\*kwargs", "*args/**kwargs 参数透传", "参数透传"),
            (r"functools\.wraps", "functools.wraps 元信息保留", "元信息保留"),
            (r"装饰器.*参数", "带参数装饰器三层嵌套", "三层嵌套结构"),
            (r"__call__", "类装饰器 __call__", "__call__ 魔术方法"),
            (r"@.*\.setter", "property setter", "property setter 用法"),
            (r"nonlocal", "nonlocal 关键字", "nonlocal 关键字"),
        ]

        for pattern, description, label in exercise_patterns:
            if re.search(pattern, exercise_text):
                # 检查讲义是否教了: 搜索概念名、等价表达、或实际代码模式
                taught = any(
                    c in str(report.taught_in_lecture)
                    for c in [label, "参数透传", "原样透传", "元信息保留",
                              "带参装饰器", "带参数装饰器", "property setter"]
                )
                # 额外检查: 讲义中是否有对应的代码模式
                if not taught:
                    code_patterns = {
                        "property setter": r"\.setter",
                        "参数透传": r"\*args.*\*\*kwargs",
                        "元信息保留": r"@wraps",
                    }
                    cp = code_patterns.get(label)
                    if cp and re.search(cp, lecture_text):
                        taught = True
                if not taught and description not in lecture_text:
                    report.gaps.append(f"练习题需要 {label}，但讲义未涉及")

        # 查找可能的卡点行
        if exercise_text:
            lines = exercise_text.split("\n")
            for i, line in enumerate(lines, 1):
                if any(kw in line for kw in ["TODO", "pass", "NotImplemented"]):
                    report.stuck_at_lines.append(
                        f"第 {i} 行: {line.strip()[:80]}"
                    )

        return report

    def _extract_concepts_from_exercise(self, text: str) -> List[str]:
        """从练习题中提取需要的前置知识"""
        if not text:
            return []
        # 标准库白名单 — 不算知识断层
        stdlib_whitelist = {"time 模块", "time.sleep", "import time", "functools 导入"}
        patterns = [
            (r"@\w+", "装饰器"),
            (r"@\w+\([^)]+\)", "带参装饰器"),
            (r"functools", "functools"),
            (r"\*args", "*args"),
            (r"\*\*kwargs", "**kwargs"),
            (r"__call__", "__call__"),
            (r"@property", "property"),
            (r"\.setter", "property setter"),
            (r"nonlocal", "nonlocal"),
        ]
        found = []
        for pat, concept in patterns:
            if re.search(pat, text):
                found.append(concept)
        return found

    # ═══════════════════════════════════════════
    #  综合评分与日记生成
    # ═══════════════════════════════════════════

    def _calc_recommend_score(
        self,
        cognitive: CognitiveLoadReport,
        dislike: ProfileDislikeReport,
        mind_gap: MindGapReport,
    ) -> int:
        """计算综合推荐度 — 按比例扣分"""
        score = 100

        # 认知负荷: 按每节最大概念数超出比例扣分
        if cognitive.concept_density_warning:
            concept_limit = self.profile.get("cognitive_limit", 3)
            excess = cognitive._overload_count - concept_limit
            overload_ratio = min(1.0, excess / concept_limit)
            score -= int(15 * overload_ratio)

        if cognitive.code_text_ratio_warning:
            score -= 10
        
        # 注意漂移区域扣分
        score -= len(cognitive.attention_drift_regions) * 5

        # 画像不匹配扣分
        score -= len(dislike.dislikes_detected) * 8
        score -= len(dislike.missing_expected_elements) * 12
        score -= len(dislike.frustration_points) * 5

        # 知识断层扣分
        score -= len(mind_gap.gaps) * 8

        return max(0, min(100, score))

    def _generate_diary(
        self,
        lecture_text: str,
        exercise_text: str,
        cognitive: CognitiveLoadReport,
        dislike: ProfileDislikeReport,
        mind_gap: MindGapReport,
    ) -> str:
        """生成第一人称沉浸式学习日记"""
        profile_desc = self.profile.get("description", "未知学生")

        parts = [f"【模拟学生 {profile_desc} 的学习日记】\n"]

        # ── 撞墙时刻 ──
        parts.append("━━━ 撞墙时刻 ━━━")
        if cognitive.concept_density_warning:
            concepts = ", ".join(cognitive.new_concepts[:6])
            parts.append(
                f"我看到讲义一下子出现了这么多概念：{concepts}。"
                f"我脑容量直接爆了，感觉在看天书。我开始想关掉页面去刷视频。"
            )
        elif cognitive.new_concepts:
            parts.append(
                f"我勉强能接受 {len(cognitive.new_concepts)} 个新概念，"
                f"但如果再慢一点、每个概念多解释两句会好很多。"
            )
        else:
            parts.append("概念密度尚可，我没有明显的撞墙感。")

        if cognitive.attention_drift_regions:
            parts.append("")
            regions = cognitive.attention_drift_regions[:2]
            for r in regions:
                parts.append(f"读到 {r} 时，我开始走神了。没有代码示例，看不下去。")
            parts.append("")

        # ── 画像排异 ──
        parts.append("\n━━━ 画像排异 ━━━")
        if dislike.dislikes_detected:
            for d in dislike.dislikes_detected[:3]:
                parts.append(f"😤 {d}")
        if dislike.missing_expected_elements:
            for m in dislike.missing_expected_elements[:2]:
                parts.append(f"😤 {m}")
        if dislike.frustration_points:
            for f in dislike.frustration_points[:2]:
                parts.append(f"😤 {f}")
        if not dislike.dislikes_detected and not dislike.missing_expected_elements:
            parts.append("讲义风格基本符合我的口味，没有明显的排异反应。")

        # ── 做题卡点 ──
        parts.append("\n━━━ 做题卡点 ━━━")
        if mind_gap.gaps:
            for g in mind_gap.gaps[:3]:
                parts.append(
                    f"😰 讲义没教 {g}，但练习题需要用到。我完全不知道怎么做。"
                )
        if mind_gap.stuck_at_lines:
            for s in mind_gap.stuck_at_lines[:2]:
                parts.append(f"📌 卡在: {s}")
        if not mind_gap.gaps:
            parts.append("讲义和练习题之间的知识衔接基本没断层，我可以尝试做题。")

        # ── 整体感受 ──
        parts.append("\n━━━ 整体感受 ━━━")
        score = self._calc_recommend_score(cognitive, dislike, mind_gap)
        if score >= 85:
            parts.append("总的来说，这节课我能跟得上，例题也够多。我愿意继续学。")
        elif score >= 60:
            parts.append(
                "勉强能学，但有几个地方让我想放弃。如果能加一些对比示例和代码拆解，会好很多。"
            )
        else:
            parts.append(
                "说实话我想放弃了。这里说的东西跟我喜欢的教学方式完全不搭。"
                "我需要更多的对比示例、更少的概念轰炸、更多的分步代码解释。"
            )

        return "\n".join(parts)

    def _generate_revision_suggestions(
        self,
        cognitive: CognitiveLoadReport,
        dislike: ProfileDislikeReport,
        mind_gap: MindGapReport,
    ) -> List[str]:
        """生成具体的修改建议"""
        suggestions = []

        if cognitive.concept_density_warning:
            suggestions.append(
                f"降低概念密度: 将 {len(cognitive.new_concepts)} 个新概念拆分到 2-3 个小节"
            )
        if cognitive.attention_drift_regions:
            suggestions.append(
                f"在 {len(cognitive.attention_drift_regions)} 处纯文本区域插入代码示例"
            )

        if dislike.missing_expected_elements:
            for m in dislike.missing_expected_elements:
                suggestions.append(f"补充: {m}")

        if mind_gap.gaps:
            for g in mind_gap.gaps:
                suggestions.append(f"补充前置知识: {g}")

        if dislike.dislikes_detected:
            suggestions.append("替换学院派表述为接地气的比喻和类比")

        return suggestions

    # ═══════════════════════════════════════════
    #  LLM 增强模式 — 调用真实大模型做第一人称日记
    # ═══════════════════════════════════════════

    def simulate_with_llm(
        self,
        lecture_text: str,
        exercise_text: str = "",
        api_key: Optional[str] = None,
        base_url: str = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/anthropic"),
        model: str = os.environ.get("LLM_MODEL", "spark-pro"),
    ) -> SimulationResult:
        """
        使用真实 LLM 做深度角色扮演模拟.

        比纯规则版本更真实，能产出自然的第一人称日记。
        """
        # 先做规则分析
        cognitive = self._analyze_cognitive_load(lecture_text)
        dislike = self._detect_profile_dislike(lecture_text)
        mind_gap = self._analyze_mind_gap(lecture_text, exercise_text)

        # 尝试调用 LLM 生成日记
        user_prompt = f"""
<generated_lecture>
{lecture_text[:3000]}
</generated_lecture>

<generated_exercises>
{exercise_text[:2000] if exercise_text else "(无练习题)"}
</generated_exercises>

请开始写你的沉浸式学习心智日记。
"""

        try:
            diary = self._call_llm(
                system_prompt=self.build_system_prompt(),
                user_prompt=user_prompt,
                api_key=api_key,
                base_url=base_url,
                model=model,
            )
        except Exception:
            # LLM 不可用时退化到规则生成
            diary = self._generate_diary(
                lecture_text, exercise_text, cognitive, dislike, mind_gap
            )

        score = self._calc_recommend_score(cognitive, dislike, mind_gap)
        suggestions = self._generate_revision_suggestions(cognitive, dislike, mind_gap)

        return SimulationResult(
            diary_text=diary,
            cognitive_load=cognitive,
            profile_dislike=dislike,
            mind_gaps=mind_gap,
            would_drop_out=cognitive.concept_density_warning or len(dislike.dislikes_detected) >= 2,
            would_recommend_score=score,
            revision_required=score < 70,
            revision_suggestions=suggestions,
        )

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        api_key: Optional[str] = None,
        base_url: str = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/anthropic"),
        model: str = os.environ.get("LLM_MODEL", "spark-pro"),
    ) -> str:
        """调用 LLM API (OpenAI Chat Completions 格式)"""
        import json
        import urllib.request
        import ssl

        if not api_key:
            raise ValueError("No API key provided for LLM simulation")

        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.9,  # 高温度让角色扮演更自然
            "max_tokens": 2000,
        }).encode()

        req = urllib.request.Request(
            f"{base_url}/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]


# ──────────────────────────────────────────────
#  CLI 入口
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="User Simulation Agent — 模拟学生试读"
    )
    parser.add_argument("lecture", help="讲义文件路径")
    parser.add_argument("--exercise", "-e", help="练习题文件路径")
    parser.add_argument("--profile", "-p", default="python_beginner_hates_theory",
                        choices=list(STUDENT_PROFILES.keys()),
                        help="学生画像")
    parser.add_argument("--llm", action="store_true", help="使用 LLM 增强模式")
    args = parser.parse_args()

    lecture_path = Path(args.lecture)
    if not lecture_path.exists():
        print(f"❌ 讲义文件不存在: {args.lecture}")
        sys.exit(1)

    lecture_text = lecture_path.read_text(encoding="utf-8")
    exercise_text = ""
    if args.exercise:
        ex_path = Path(args.exercise)
        if ex_path.exists():
            exercise_text = ex_path.read_text(encoding="utf-8")

    agent = UserSimulationAgent(profile_name=args.profile)

    if args.llm:
        # LLM 增强模式
        import os
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            # 尝试从 Claude settings 读取
            try:
                import json
                settings = json.load(open(os.path.expanduser("~/.claude/settings.json")))
                api_key = settings.get("apiKey")
            except Exception:
                pass
        if not api_key:
            print("⚠️ 未找到 API Key，退化为规则模式")
            result = agent.simulate(lecture_text, exercise_text)
        else:
            result = agent.simulate_with_llm(
                lecture_text, exercise_text, api_key=api_key
            )
    else:
        result = agent.simulate(lecture_text, exercise_text)

    print("╔══════════════════════════════════════════════╗")
    print("║  🧑‍🎓 模拟学生试读 — 沉浸式学习心智日记     ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    print(f"  学生画像: {agent.profile['description']}")
    print(f"  推荐度: {result.would_recommend_score}/100")
    print(f"  会中途放弃: {'是' if result.would_drop_out else '否'}")
    print(f"  需要修订: {'是' if result.revision_required else '否'}")
    print()
    print(result.diary_text)
    print()

    if result.revision_suggestions:
        print("━━━ 修订建议 ━━━")
        for s in result.revision_suggestions:
            print(f"  💡 {s}")

    sys.exit(0 if not result.revision_required else 1)
