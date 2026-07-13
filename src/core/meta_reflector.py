"""
Phase 4 — MetaReflectorAgent + 自适应 Prompt 构建器
"""

from __future__ import annotations
import json, os, re, urllib.request, ssl
from pathlib import Path
from typing import Any, Dict, List, Optional
from .contracts import FailurePatternLesson, BUILTIN_LESSONS


class _LocalMemoryStore:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path or os.path.expanduser("~/.hermes/a3_memory.json"))
        self._data: List[Dict[str, Any]] = []
        self._load()
        if not self._data: self._seed()

    def _load(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists(): self._data = json.loads(self.db_path.read_text())
        else: self._data = []

    def _save(self):
        self.db_path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2))

    def _seed(self):
        for l in BUILTIN_LESSONS:
            self._data.append({"id": f"lesson_{l.node_id}_{l.error_type.lower().replace(' ','_')}", "document": l.semantic_anchor(), "metadata": {"doc_type": "failure_lessons", "source": l.source, "node_id": l.node_id, "error_type": l.error_type, "structured_data": l.to_json()}})
        self._save()

    def upsert(self, documents, metadatas, ids):
        for i, did in enumerate(ids):
            self._data = [d for d in self._data if d["id"] != did]
            self._data.append({"id": did, "document": documents[i], "metadata": metadatas[i]})
        self._save()

    def query(self, query_texts, n_results=2, where=None):
        results = [[], [], []]
        for qt in query_texts:
            qt_l = qt.lower()
            scored = []
            for item in self._data:
                meta = item.get("metadata", {})
                if where is None:
                    pass
                elif "$and" in where:
                    if not all(meta.get(k) == v for c in where["$and"] for k, v in c.items()):
                        continue
                elif not all(meta.get(k) == v for k, v in where.items()):
                    continue
                score = sum(1 for w in qt_l.split() if w.lower() in item.get("document", "").lower())
                scored.append((score, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:n_results]
            results[0].append([i["id"] for _, i in top])
            results[1].append([i["metadata"] for _, i in top])
            results[2].append([i["document"] for _, i in top])
        return {"ids": results[0] if results[0] else [[]], "metadatas": results[1] if results[1] else [[]], "documents": results[2] if results[2] else [[]]}

    def count(self): return len(self._data)

    def get_all_lessons(self):
        lessons = []
        for item in self._data:
            if item.get("metadata", {}).get("doc_type") == "failure_lessons":
                try: lessons.append(FailurePatternLesson.from_json(item["metadata"]["structured_data"]))
                except: pass
        return lessons


class MetaReflectorAgent:
    def __init__(self, db_client=None, api_key=None, base_url=None):
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
        self.collection = db_client or _LocalMemoryStore()

    def distill_accident(self, node_id, accident_payload):
        if self.api_key: return self._llm_distill(node_id, accident_payload)
        return self._rule_distill(node_id, accident_payload)

    def _llm_distill(self, node_id, payload):
        prompt = f"Analyze failure [{node_id}]. Return JSON: error_type,problem_context,root_cause_analysis,anti_pattern_code,golden_patch_code,abstract_lint_rule\nPayload:{json.dumps(payload,ensure_ascii=False)}"
        body = json.dumps({"model": os.environ.get("LLM_MODEL", "spark-pro"), "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "response_format": {"type": "json_object"}}).encode()
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=60) as r:
            data = json.loads(json.loads(r.read())["choices"][0]["message"]["content"])
            data["node_id"] = node_id
            return FailurePatternLesson.from_dict(data)

    def _rule_distill(self, node_id, payload):
        et = payload.get("error_type", payload.get("error", "Unknown"))
        root_map = {"SyntaxError":"代码未完成括号闭合或拼写错误","TypeError":"装饰器返回None而非callable","AttributeError":"None对象访问属性——缺少空值检查"}
        return FailurePatternLesson(
            error_type=et,
            problem_context=payload.get("context", payload.get("problem_context", f"Node {node_id} failure")),
            root_cause_analysis=payload.get("root_cause", root_map.get(et,"待分析")),
            anti_pattern_code=payload.get("anti_pattern",""), golden_patch_code=payload.get("fix",""),
            abstract_lint_rule=payload.get("rule", f"检查{et}相关约束"), node_id=node_id)

    def store_lesson(self, node_id, lesson):
        self.collection.upsert(documents=[lesson.semantic_anchor()], metadatas=[{"doc_type":"failure_lessons","node_id":node_id,"error_type":lesson.error_type,"structured_data":lesson.to_json()}], ids=[f"lesson_{node_id}_{lesson.error_type.lower().replace(' ','_')}"])
        # ── 同步写入 ExperienceMemory ──
        self._sync_to_experience(node_id, lesson)

    def _sync_to_experience(self, node_id, lesson):
        """同步教训到全局 ExperienceMemory"""
        if not hasattr(self, "_exp_store") or self._exp_store is None:
            return
        try:
            self._exp_store.add_lesson(
                problem=lesson.problem_context[:120],
                cause=lesson.root_cause_analysis[:120],
                context=f"node-{node_id} / {lesson.error_type}",
                solution=lesson.golden_patch_code[:200] or lesson.abstract_lint_rule,
                source="metareflector",
                node_id=node_id,
                severity=lesson.severity,
            )
        except Exception:
            pass  # 静默失败, 不阻塞主流程

    def set_experience_store(self, exp_store) -> None:
        """注入 ExperienceMemoryStore 实例"""
        self._exp_store = exp_store

    # ── Self-Reflection ────────────────────

    def reflect(
        self,
        node_id: str,
        failure_context: Dict[str, Any],
        concept: str = "",
        severity: str = "MEDIUM",
    ) -> Optional["ReflectionResult"]:
        """
        自我反思: 分析失败根因, 生成改进策略.

        Args:
            node_id: 节点 ID
            failure_context: {mistake, student_id, scores, attempts, profile_type}
            concept: 关联概念
            severity: 严重级别

        Returns:
            ReflectionResult (同时写入 ExperienceMemory)
        """
        from .decision_explainer import ReflectionResult

        mistake = failure_context.get("mistake", failure_context.get("problem", f"Node {node_id} failure"))
        student_id = failure_context.get("student_id", "")
        scores = failure_context.get("scores", [])
        attempts = failure_context.get("attempts", len(scores))

        # 根因分析
        if attempts >= 3:
            root_cause = f"学生连续 {attempts} 次未能通过 — 存在概念误解"
            improvement = "增加可视化讲解 + 分步拆解 + 类比引入"
            future_strategy = f"对 {concept or node_id} 相关节点, 优先使用图解和对比示例"
        elif attempts >= 2:
            root_cause = "学生两次尝试失败 — 可能缺少前置知识"
            improvement = "补充前置知识讲解 + 降低初始难度"
            future_strategy = f"在推荐 {concept or node_id} 之前, 先检查前置概念掌握度"
        else:
            root_cause = "单次失败 — 可能是偶发错误"
            improvement = "提供提示 + 允许重试"
            future_strategy = "监控该学生后续表现"

        result = ReflectionResult(
            mistake=mistake,
            root_cause=root_cause,
            improvement=improvement,
            future_strategy=future_strategy,
            severity=severity,
            concept=concept or node_id,
            node_id=node_id,
            affected_profiles=[student_id] if student_id else [],
        )

        # 写入 ExperienceMemory
        if hasattr(self, "_exp_store") and self._exp_store:
            try:
                entry = result.to_experience_entry()
                self._exp_store.add_lesson(**entry)
            except Exception:
                pass

        return result

    def recall_reflections(
        self,
        concept: str = "",
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """召回历史反思记录"""
        results = self.recall_lessons(concept, n_results=limit)
        return [
            {
                "mistake": getattr(l, "problem_context", ""),
                "root_cause": getattr(l, "root_cause_analysis", ""),
                "improvement": getattr(l, "abstract_lint_rule", ""),
                "severity": getattr(l, "severity", "MEDIUM"),
            }
            for l in results
        ]

    def recall_lessons(self, query, n_results=3):
        results = self.collection.query(query_texts=[query], n_results=n_results, where={"doc_type":"failure_lessons"})
        lessons = []
        if results.get("metadatas") and results["metadatas"][0]:
            for meta in results["metadatas"][0]:
                try: lessons.append(FailurePatternLesson.from_json(meta["structured_data"]))
                except: pass
        return lessons


def build_adaptive_system_prompt(base_prompt, target_concept, collection=None, max_lessons=3):
    if collection is None: collection = _LocalMemoryStore()
    try: results = collection.query(query_texts=[target_concept], n_results=max_lessons, where={"doc_type":"failure_lessons"})
    except: return base_prompt
    if not results or not results.get("metadatas") or not results["metadatas"] or not results["metadatas"][0]: return base_prompt

    parts = ["\n\n# ====== SYSTEM WRONG-QUESTION BOOK (LEARNED LESSONS) ======"]
    seen, count = set(), 0
    for meta in results["metadatas"][0]:
        if count >= max_lessons: break
        try:
            l = json.loads(meta["structured_data"])
            lid = f"{l.get('error_type','')}_{l.get('node_id','')}"
            if lid in seen: continue
            seen.add(lid); count += 1
            parts.extend([
                f"## 教训 {count}: [{l.get('error_type')}]",
                f"  根因: {l.get('root_cause_analysis','')[:120]}",
                f"  ❌ 反模式:\n```\n{l.get('anti_pattern_code','')}\n```",
                f"  ✅ 金修:\n```\n{l.get('golden_patch_code','')}\n```",
                f"  🔑 原则: {l.get('abstract_lint_rule','')}", ""
            ])
        except: continue
    parts.append("# ====== END ======\n")
    return base_prompt + "\n".join(parts)


def create_reflector(api_key=None, memory_path=None):
    return MetaReflectorAgent(db_client=_LocalMemoryStore(memory_path), api_key=api_key)
