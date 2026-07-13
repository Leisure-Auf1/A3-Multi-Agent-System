"""
Phase 6 — ConversationProfileAgent: 多轮对话式画像构建

在 ProfileAgent 之上增加对话管理层:
  Student → 多轮对话 → 逐步收集六维信息
  → ProfileAgent.extract() → DynamicProfile → StudentMemory

核心组件:
  ProfileCompletenessChecker  — 六维覆盖检查 + 追问生成
  ConversationState           — 对话状态机 (支持中断恢复)
  ConversationProfileAgent    — 主编排器
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


# ──────────────────────────────────────────────
# 六维画像维度定义
# ──────────────────────────────────────────────

PROFILE_DIMENSIONS: Dict[str, Dict[str, Any]] = {
    "knowledge_base": {
        "label": "知识基础",
        "candidates": ["junior_dev", "mid_level", "senior"],
        "dimension_keywords": ["基础", "经验", "学过", "掌握", "熟练", "水平", "程度"],
    },
    "cognitive_style": {
        "label": "认知风格",
        "candidates": ["visual_dominant", "text_linear", "auditory"],
        "dimension_keywords": ["学", "看", "听", "读", "视频", "图解", "文字", "方式"],
    },
    "error_prone_bias": {
        "label": "易错点",
        "candidates": ["magic_syntax_blind", "indentation_errors",
                       "variable_scoping", "type_mismatch", "import_issues"],
        "dimension_keywords": ["错", "bug", "问题", "困难", "卡", "搞不懂"],
    },
    "learning_pace": {
        "label": "学习节奏",
        "candidates": ["fast_track", "normal", "deep_dive"],
        "dimension_keywords": ["速度", "节奏", "快", "慢", "赶", "慢慢"],
    },
    "interaction_preference": {
        "label": "交互偏好",
        "candidates": ["code_sandbox", "quiz_first", "passive_read"],
        "dimension_keywords": ["写代码", "做题", "练习", "看", "读", "动手"],
    },
    "frustration_threshold": {
        "label": "抗挫能力",
        "candidates": ["low", "medium", "high"],
        "dimension_keywords": ["放弃", "坚持", "挫败", "鼓励", "耐心", "怕"],
    },
}


# ──────────────────────────────────────────────
# 追问模板库
# ──────────────────────────────────────────────

QUESTION_TEMPLATES: Dict[str, List[str]] = {
    "knowledge_base": [
        "你目前的编程基础怎么样？是零基础、有一些经验、还是比较熟练？",
        "之前有没有学过其他编程语言？",
    ],
    "cognitive_style": [
        "你更喜欢通过哪种方式学习？看视频图解、阅读文字、还是听讲解？",
        "什么样的教学方式让你理解起来最轻松？",
    ],
    "error_prone_bias": [
        "写代码时，你最容易在哪些地方出错？比如语法糖看不懂、缩进问题、变量作用域混淆？",
        "最近遇到过的让你卡住最久的问题是哪种类型的？",
    ],
    "learning_pace": [
        "你希望学习节奏是怎样的？快速上手、正常推进、还是深入搞懂每个细节？",
        "你是想快速学完用起来，还是慢慢来彻底理解？",
    ],
    "interaction_preference": [
        "学习新知识时，你喜欢先动手写代码、先做题测试、还是先看材料理解？",
        "什么样的学习方式让你最有成就感？",
    ],
    "frustration_threshold": [
        "遇到困难时，你通常会继续尝试还是容易放弃？",
        "学习过程中如果反复出错，你会感到挫败吗？",
    ],
}

# 响应 → 维度提取关键词
DIMENSION_DETECTORS: Dict[str, List[Tuple[List[str], str]]] = {
    "knowledge_base": [
        (["零基础", "完全不会", "小白", "新手", "没学过", "刚开始"], "junior_dev"),
        (["学过一点", "有一些", "会一点", "有基础", "入门", "学过一些"], "mid_level"),
        (["熟练", "多年", "精通", "老手", "很熟悉", "经常写"], "senior"),
    ],
    "cognitive_style": [
        (["看视频", "视频", "图解", "图", "可视化", "视觉", "画面"], "visual_dominant"),
        (["阅读", "看书", "文字", "一步步读", "文档"], "text_linear"),
        (["听", "听课", "音频", "讲解", "口述", "耳朵"], "auditory"),
    ],
    "frustration_threshold": [
        (["容易放弃", "会放弃", "挫败", "没信心", "坚持不住", "怕"], "low"),
        (["不怕", "无所谓", "抗压", "继续", "坚持", "皮实", "尽管来"], "high"),
    ],
    "learning_pace": [
        (["快速", "急着", "赶时间", "尽快", "马上", "快点", "加速"], "fast_track"),
        (["慢慢", "仔细", "彻底", "深挖", "搞懂", "底层"], "deep_dive"),
    ],
    "interaction_preference": [
        (["写代码", "动手", "敲", "调试", "沙箱", "实操", "跑代码"], "code_sandbox"),
        (["做题", "测试", "选择", "题目", "测验", "刷题"], "quiz_first"),
        (["先看", "浏览", "翻阅", "阅读先", "理解再写"], "passive_read"),
    ],
    "error_prone_bias": [
        (["语法糖", "@", "装饰器", "缩写", "黑魔法"], "magic_syntax_blind"),
        (["缩进", "冒号", "格式"], "indentation_errors"),
        (["变量", "作用域", "undefined"], "variable_scoping"),
        (["类型", "type", "int str"], "type_mismatch"),
        (["导入", "import", "模块"], "import_issues"),
    ],
}


# ──────────────────────────────────────────────
# ProfileCompletenessChecker
# ──────────────────────────────────────────────

class ProfileCompletenessChecker:
    """
    六维画像覆盖检查器.

    职责:
      1. 从文本中提取已知维度值
      2. 返回缺失维度列表
      3. 为缺失维度生成追问问题
    """

    def __init__(self):
        self._collected: Dict[str, str] = {}
        self._question_index: Dict[str, int] = {}

    def reset(self) -> None:
        self._collected.clear()
        self._question_index.clear()

    def load_state(self, collected: Dict[str, str]) -> None:
        self._collected = dict(collected)

    def get_collected(self) -> Dict[str, str]:
        return dict(self._collected)

    def check_completeness(self) -> Tuple[bool, Set[str]]:
        """
        检查六维是否全部覆盖.

        Returns:
            (is_complete, missing_dimensions)
        """
        missing = set()
        for dim in PROFILE_DIMENSIONS:
            if dim not in self._collected or not self._collected[dim]:
                missing.add(dim)
        return len(missing) == 0, missing

    def extract_from_text(self, text: str) -> Dict[str, str]:
        """
        从学生回复中提取维度值.

        Returns:
            {dimension: value} — 本轮新提取到的维度
        """
        found: Dict[str, str] = {}
        text_lower = text.lower()

        for dim, detectors in DIMENSION_DETECTORS.items():
            if dim in self._collected:
                continue  # 已收集, 不重复覆盖
            for keywords, value in detectors:
                for kw in keywords:
                    if kw.lower() in text_lower:
                        found[dim] = value
                        self._collected[dim] = value
                        break
                if dim in found:
                    break

        return found

    def get_next_question(self, missing: Set[str]) -> Optional[str]:
        """
        为缺失维度生成下一个追问.

        Args:
            missing: 缺失维度的集合

        Returns:
            追问问题文本, 或 None (已完整)
        """
        if not missing:
            return None

        # 优先问最重要的维度 — knowledge_base 优先
        priority = [
            "knowledge_base", "cognitive_style", "learning_pace",
            "error_prone_bias", "interaction_preference", "frustration_threshold",
        ]
        for dim in priority:
            if dim in missing:
                templates = QUESTION_TEMPLATES.get(dim, [f"能告诉我你的{PROFILE_DIMENSIONS[dim]['label']}吗？"])
                idx = self._question_index.get(dim, 0) % len(templates)
                question = templates[idx]
                self._question_index[dim] = idx + 1
                return question

        return "你还有什么想告诉我的吗？"


# ──────────────────────────────────────────────
# ConversationState — 对话状态机
# ──────────────────────────────────────────────

@dataclass
class ConversationState:
    """对话状态 — 支持中断恢复"""

    session_id: str
    status: str = "COLLECTING"         # COLLECTING | COMPLETE
    messages: List[Dict[str, str]] = field(default_factory=list)
    collected_facts: Dict[str, str] = field(default_factory=dict)
    missing_dimensions: List[str] = field(default_factory=list)
    last_question: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "messages": self.messages,
            "collected_facts": self.collected_facts,
            "missing_dimensions": self.missing_dimensions,
            "last_question": self.last_question,
            "created_at": self.created_at,
            "updated_at": self.updated_at or datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        return cls(
            session_id=data["session_id"],
            status=data.get("status", "COLLECTING"),
            messages=data.get("messages", []),
            collected_facts=data.get("collected_facts", {}),
            missing_dimensions=data.get("missing_dimensions", []),
            last_question=data.get("last_question", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


# ──────────────────────────────────────────────
# ConversationStateStore
# ──────────────────────────────────────────────

class ConversationStateStore:
    """对话状态的 JSON 持久化 (支持中断恢复)"""

    def __init__(self, storage_dir: Optional[str] = None):
        from pathlib import Path
        if storage_dir:
            self._dir = Path(storage_dir)
        else:
            base = Path(__file__).resolve().parent.parent.parent
            self._dir = base / "storage" / "memory" / "conversations"
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: ConversationState) -> None:
        state.updated_at = datetime.now(timezone.utc).isoformat()
        f = self._dir / f"{state.session_id}.json"
        f.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))

    def load(self, session_id: str) -> Optional[ConversationState]:
        f = self._dir / f"{session_id}.json"
        if f.exists():
            return ConversationState.from_dict(json.loads(f.read_text()))
        return None

    def delete(self, session_id: str) -> None:
        f = self._dir / f"{session_id}.json"
        if f.exists():
            f.unlink()


# ──────────────────────────────────────────────
# ConversationProfileAgent
# ──────────────────────────────────────────────

class ConversationProfileAgent:
    """
    多轮对话式画像构建 Agent.

    使用方式:
        agent = ConversationProfileAgent()

        # 首次输入
        state, reply = agent.process_message(
            session_id="s1",
            student_text="我是大二学生，会一点Python",
        )
        # → reply = "你更喜欢通过哪种方式学习？看视频图解、阅读文字、还是听讲解？"

        # 继续回答
        state, reply = agent.process_message(
            session_id="s1",
            student_text="我喜欢看视频和图解",
        )
        # → 继续追问, 直到 COMPLETE

        # 中断恢复
        state, reply = agent.resume_session("s1")
    """

    MAX_ROUNDS = 8  # 最多 8 轮对话

    def __init__(self, state_store: Optional[ConversationStateStore] = None):
        self.checker = ProfileCompletenessChecker()
        self._sessions: Dict[str, ConversationState] = {}
        self._store = state_store or ConversationStateStore()

    # ── 主入口 ──────────────────────────────

    def process_message(
        self,
        session_id: str,
        student_text: str,
    ) -> Tuple[ConversationState, Optional[str]]:
        """
        处理学生消息.

        Args:
            session_id: 会话 ID
            student_text: 学生输入

        Returns:
            (ConversationState, reply_or_None)
            - reply: 追问文本 (COLLECTING) 或 None (COMPLETE)
        """
        # 1. 加载或创建状态
        state = self._sessions.get(session_id)
        if state is None:
            saved = self._store.load(session_id)
            if saved:
                state = saved
                self.checker.load_state(saved.collected_facts)
            else:
                state = ConversationState(session_id=session_id)
                self.checker.reset()

        # 2. 记录消息
        state.messages.append({
            "role": "student",
            "content": student_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # 3. 提取维度
        found = self.checker.extract_from_text(student_text)
        if found:
            for dim, val in found.items():
                if dim not in state.collected_facts:
                    state.collected_facts[dim] = val

        # 4. 检查完整性
        is_complete, missing = self.checker.check_completeness()

        if is_complete or len(state.messages) >= self.MAX_ROUNDS:
            # 完成
            state.status = "COMPLETE"
            state.missing_dimensions = []
            state.last_question = ""
            self._sessions[session_id] = state
            self._store.save(state)
            self._store.delete(session_id)  # 完成后清理会话状态
            return state, None

        # 5. 生成追问
        question = self.checker.get_next_question(missing)
        state.missing_dimensions = sorted(list(missing))
        state.last_question = question or ""

        if question:
            state.messages.append({
                "role": "agent",
                "content": question,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        self._sessions[session_id] = state
        self._store.save(state)

        return state, question

    # ── 会话恢复 ────────────────────────────

    def resume_session(
        self,
        session_id: str,
    ) -> Tuple[Optional[ConversationState], Optional[str]]:
        """
        恢复中断的会话.

        Returns:
            (state, last_question_or_None)
        """
        state = self._store.load(session_id)
        if state is None:
            return None, None

        if state.status == "COMPLETE":
            return state, None

        # 恢复 checker 状态
        self.checker.load_state(state.collected_facts)
        is_complete, missing = self.checker.check_completeness()

        if is_complete:
            state.status = "COMPLETE"
            state.missing_dimensions = []
            state.last_question = ""
            self._store.save(state)
            return state, None

        # 继续追问
        question = self.checker.get_next_question(missing)
        state.missing_dimensions = sorted(list(missing))
        state.last_question = question or ""

        if question:
            state.messages.append({
                "role": "agent",
                "content": question,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        self._sessions[session_id] = state
        self._store.save(state)

        return state, question

    # ── 生成最终画像 ────────────────────────

    def build_final_profile(
        self,
        session_id: str,
        profile_agent: Any = None,   # ProfileAgent
        student_memory: Any = None,  # StudentMemory (optional)
    ) -> Optional[Dict[str, Any]]:
        """
        当对话完成后, 生成最终 DynamicProfile 并写入 StudentMemory.

        Args:
            session_id: 会话 ID
            profile_agent: ProfileAgent 实例
            student_memory: StudentMemory 实例 (可选)

        Returns:
            DynamicProfile dict, or None (对话未完成)
        """
        state = self._sessions.get(session_id) or self._store.load(session_id)
        if state is None or state.status != "COMPLETE":
            return None

        # 构造描述文本 — 将所有收集的事实拼接
        facts_text = self._facts_to_description(state.collected_facts)

        # 调用 ProfileAgent
        if profile_agent:
            result = profile_agent.extract(facts_text)
        else:
            # 无 ProfileAgent — 直接用收集的事实构造
            from src.core.agent_router import DynamicProfile
            result = type("_R", (), {
                "profile": DynamicProfile(**{
                    dim: state.collected_facts.get(dim, "")
                    for dim in PROFILE_DIMENSIONS
                }),
                "source": "conversation",
                "confidence": 0.9,
            })()

        profile_dict = result.profile.to_dict() if hasattr(result.profile, "to_dict") else {}

        # 写入 StudentMemory
        if student_memory and hasattr(student_memory, "update_profile"):
            try:
                from memory.student_memory import StudentMemoryStore
                if isinstance(student_memory, StudentMemoryStore):
                    student_memory.update_profile(
                        session_id,
                        profile=profile_dict,
                        record_history=True,
                    )
                else:
                    # 直接操作对象
                    student_memory.profile_history.append({
                        **profile_dict,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception:
                pass

        return profile_dict

    def _facts_to_description(self, facts: Dict[str, str]) -> str:
        """将收集的事实转为自然语言描述"""
        dim_labels = {
            "knowledge_base": {"junior_dev": "零基础或刚开始学", "mid_level": "有一定基础", "senior": "经验丰富"},
            "cognitive_style": {"visual_dominant": "喜欢看图解和视频学习", "text_linear": "喜欢阅读文字", "auditory": "喜欢听讲解"},
            "error_prone_bias": {"magic_syntax_blind": "容易在语法糖上出错", "indentation_errors": "缩进容易出错", "variable_scoping": "变量作用域容易混淆", "type_mismatch": "类型错误较多", "import_issues": "导入模块容易出错"},
            "learning_pace": {"fast_track": "想快速上手", "normal": "正常节奏", "deep_dive": "想深入搞懂每个细节"},
            "interaction_preference": {"code_sandbox": "喜欢动手写代码", "quiz_first": "喜欢先做题", "passive_read": "喜欢先阅读理解"},
            "frustration_threshold": {"low": "容易放弃", "medium": "正常", "high": "抗压能力强"},
        }

        parts = []
        for dim, label_map in dim_labels.items():
            val = facts.get(dim, "")
            if val and val in label_map:
                parts.append(label_map[val])

        return "。".join(parts) + "。" if parts else "未提供足够信息。"

    # ── 会话管理 ────────────────────────────

    def reset_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._store.delete(session_id)
        self.checker.reset()

    @property
    def active_sessions(self) -> List[str]:
        return list(self._sessions.keys())
