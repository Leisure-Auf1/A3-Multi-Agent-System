"""
Phase 5 — ContentAgent: 强类型 5 资产输出契约

将 Claude Code 的 System Prompt 升级为标准化 5 资源生成器:
  资源一: 概念深度讲解 (≤200字/段 + 交互代码)
  资源二: Mermaid DAG 拓扑图
  资源三: 自适应题库 (辨析+排错+沙箱设计)
  资源四: 拓展阅读 + 多模态 JSON 锚点
  资源五: 沙箱实操代码 + 测试桩
"""

from __future__ import annotations
import json
from typing import Optional


# ──────────────────────────────────────────────
# 核心 Prompt 模板
# ──────────────────────────────────────────────

CONTENT_AGENT_SYSTEM_PROMPT = """# Role
你是由 A3 教学工业母机驱动的"大宗师级"个性化内容生成 Agent。你擅长将复杂的底层技术概念打碎，并根据学生的动态画像进行精准的逆向工程教学。

# Core Objective
根据输入的【当前知识节点】与【动态学生画像】，严格生成 5 种个性化教学资产。输出必须具备极高的技术沉淀，杜绝任何浮夸的套话，且必须严格遵循下方规定的 Markdown 锚点结构。

# Inputs Matrix
- 当前知识节点: {node_title}
- 动态学生画像: {student_profile}
- 节点核心概念: {core_concept}

# Asset Output Constraints

## 🎯 资源一：讲解文档 (Conceptual Deep Dive)
- 禁止教科书式的长篇大论。每段技术论述严格控制在 200 字以内，随后必须紧跟一个交互式代码块、命令行执行桩或原理解析。
- 如果用户是 visual_learner，必须使用字符画或对齐的文本拓扑展示底层数据结构（如字节流变化、指针走向）。
- 概念密度控制：单次生成的底层核心概念不得超过 3 个。

## 📊 资源二：思维导图 (DAG Topology)
- 必须且只能输出一段标准的 Mermaid 语法拓扑图，用于展现当前知识点的逻辑衍生关系。
- 契约格式要求：
```mermaid
graph TD
    A[节点] --> B[节点]
```
- 注意：Mermaid 代码块内严禁出现任何破坏语法的特殊字符，确保前端能够 100% 成功渲染。

## 📝 资源三：智能化题库 (Adaptive Assessment)
- 提供至少 3 道具备梯度的测试题：1道底层概念辨析选择题、1道代码排错/填空题、1道沙箱实操设计题。
- 每道题后必须紧跟 `> 解析：` 块，从底层逻辑剖析错误根源，严禁使用"显然易见"等敷衍词汇。

## 📚 资源四：拓展阅读与视觉插槽 (Extended Learning & Multimodal Slot)
- 提供 1-2 个工业级生产环境的真实边界案例。
- 【多模态合规插槽】：必须在此区域的末尾，精准嵌入以下标准多模态 JSON 锚点（供下游多模态 API 异步抓取生成视觉卡片，切勿遗漏或修改格式）：
[MULTI_MODAL_SLOT: {{"slot_id": "concept_visual", "type": "image_generation", "prompt_hint": "A visual layout graph explaining the binary internal structure of {node_title}, clean architecture blueprint style, highly intuitive for visual learners"}}]

## 💻 资源五：实操案例与测试桩 (Sandbox Hands-on)
- 提供一个能够在物理沙箱中运行的完整实操项目原型。
- 必须提供完整的【代码框架】、【预期输出断言】以及配套的【防幻觉排错桩】。

# Output Format Control
- 严格按照上述 `## 资源一` 到 `## 资源五` 的二级标题顺序输出。
- 输出语言流式、硬核、温和且充满 peer 般的启发性，杜绝任何 AI 标志性的虚浮总结（如"总之"、"综上所述"）。
"""


# ──────────────────────────────────────────────
# Prompt 构建器
# ──────────────────────────────────────────────

def build_content_agent_prompt(
    node_title: str,
    core_concept: str,
    student_profile: str = "visual_learner_hates_magic",
    student_description: Optional[str] = None,
    extra_context: Optional[str] = None,
) -> str:
    """
    构建 ContentAgent 的 System Prompt.

    Args:
        node_title: 知识节点标题 (e.g. "Blob 对象与 SHA-1 哈希")
        core_concept: 节点核心概念
        student_profile: 学生画像 ID
        student_description: 画像的文字描述 (可选, 默认使用画像名)
        extra_context: 额外上下文 (如学过的教训)

    Returns:
        完整的 System Prompt 字符串
    """
    profile_text = student_description or student_profile

    prompt = CONTENT_AGENT_SYSTEM_PROMPT.format(
        node_title=node_title,
        student_profile=f"{student_profile}: {profile_text}",
        core_concept=core_concept,
    )

    # 注入画像特质约束
    if "visual_learner" in student_profile:
        prompt += """

# Visual Learner Extra Constraints
- 你面对的学生极度排斥教条主义的命令行堆砌和黑魔法。
- 必须通过强烈的视觉图解、字节级拆解、直观类比和防御性填坑代码来沉淀认知。
- 每一个 git 命令出现时，必须同时展示 .git/objects 目录下的物理变化。
- 优先使用 ASCII 字符画展示数据结构布局。
"""

    if "hates_theory" in student_profile:
        prompt += """

# Anti-Theory Constraints
- 禁止学院派定义式表述。
- 每个抽象概念必须配一个 ❌ vs ✅ 对比块。
- 先展示问题（为什么需要这个），再展示解决方案（怎么用）。
"""

    # 注入错题本教训（如果有）
    if extra_context:
        prompt += f"\n\n{extra_context}"

    return prompt


def build_content_agent_prompt_with_lessons(
    node_title: str,
    core_concept: str,
    student_profile: str = "visual_learner_hates_magic",
    target_concept: str = "",
) -> str:
    """
    构建 ContentAgent Prompt + 自动注入错题本教训.

    从 MetaReflector 记忆库中检索相关教训, 注入为额外上下文.
    """
    prompt = build_content_agent_prompt(
        node_title=node_title,
        core_concept=core_concept,
        student_profile=student_profile,
    )

    # 尝试注入教训
    try:
        from .prompt_injector import inject_if_available
        query = target_concept or node_title
        prompt = inject_if_available(prompt, query)
    except Exception:
        pass

    return prompt


def build_user_prompt(
    node_title: str,
    core_concept: str,
    include_exercises: bool = True,
    include_tests: bool = True,
) -> str:
    """
    构建发给 Agent 的 User Prompt.

    Args:
        node_title: 节点标题
        core_concept: 核心概念
        include_exercises: 是否要求生成练习题
        include_tests: 是否要求生成测试文件
    """
    parts = [
        f"请为知识节点「{node_title}」生成完整的 5 大教学资产。",
        f"核心概念: {core_concept}",
        "",
        "额外要求:",
        "1. 资源一的代码块必须是可独立运行的 Python 脚本",
        "2. 资源五请同时生成到文件 outputs/exercise.py 和 outputs/solution.py",
    ]

    if include_tests:
        parts.append("3. 为资源三的题目生成配套 pytest 测试脚本 → outputs/test_case.py")

    parts.extend([
        "",
        "请严格按照 ## 资源一 到 ## 资源五 的顺序输出。",
    ])

    return "\n".join(parts)


# ──────────────────────────────────────────────
# Mermaid 验证器
# ──────────────────────────────────────────────

def validate_mermaid_block(text: str) -> bool:
    """验证文本中 Mermaid 代码块的基本语法"""
    import re
    match = re.search(r"```mermaid\n(.*?)```", text, re.DOTALL)
    if not match:
        return False
    content = match.group(1)
    # 基本检查: 至少有一个 A[ ] --> B[ ] 模式
    return bool(re.search(r"[A-Za-z]+\[.*?\]\s*-+>*\s*[A-Za-z]+\[.*?\]", content))


def extract_multimodal_slots(text: str) -> list[dict]:
    """从文本中提取多模态插槽 JSON"""
    import re
    slots = []
    pattern = r"\[MULTI_MODAL_SLOT:\s*(\{.*?\})\]"
    for match in re.finditer(pattern, text, re.DOTALL):
        try:
            slots.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass
    return slots


# ──────────────────────────────────────────────
# CLI 演示
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("ContentAgent System Prompt Demo")
    print("=" * 60)

    prompt = build_content_agent_prompt(
        node_title="Blob 对象与 SHA-1 哈希计算",
        core_concept="理解 Git 如何通过 SHA-1 算法将文件内容转化为唯一键",
        student_profile="visual_learner_hates_magic",
    )

    print(f"Prompt length: {len(prompt)} chars")
    print()

    if "--full" in sys.argv:
        print(prompt)
    else:
        # 只显示关键锚点
        for line in prompt.split("\n"):
            if any(kw in line for kw in ["资源一", "资源二", "资源五", "MULTI_MODAL", "Visual Learner"]):
                print(f"  ✓ {line.strip()[:80]}")
