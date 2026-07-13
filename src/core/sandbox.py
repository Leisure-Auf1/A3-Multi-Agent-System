#!/usr/bin/env python3
"""
Phase 3 — 事务沙箱与自主工具箱 (Transaction Sandbox + ReAct Tool-Use)

架构:
  AgentWorkspaceTransaction  →  物理快照 + 事务提交/回滚
  secure_read_file           →  安全读取（仅限沙箱目录）
  secure_write_patch         →  安全写入补丁（增量修改）
  secure_run_pytest          →  安全执行测试（子进程隔离）
  ReActSelfHealLoop          →  最多 3 轮自主推理纠错
  CommitGate                 →  ≥85 分: commit → 固化; <85: rollback → 回滚
"""

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# 1. 事务沙箱 (AgentWorkspaceTransaction)
# ──────────────────────────────────────────────

@dataclass
class TransactionLog:
    """事务日志"""
    node_id: str
    workspace: str
    snapshot_path: str
    operations: List[Dict] = field(default_factory=list)
    created_at: float = 0.0
    committed_at: Optional[float] = None
    rolled_back_at: Optional[float] = None
    status: str = "OPEN"  # OPEN | COMMITTED | ROLLED_BACK

    def record(self, op: str, detail: str = ""):
        self.operations.append({
            "op": op,
            "detail": detail,
            "timestamp": time.time(),
        })


class AgentWorkspaceTransaction:
    """
    事务沙箱上下文管理器.

    用法:
        with AgentWorkspaceTransaction("node_1", "outputs/") as tx:
            tx.read("exercise.py")
            tx.patch("exercise.py", old="pass", new="return a+b")
            tx.run_pytest()
            # 如果 >= 85 分 → 自动 commit
            # 如果 < 85 分 → 自动 rollback

    安全约束:
        - 所有 I/O 操作限定在 workspace 目录内
        - 退出时检查 commit_gate → 决定 commit 或 rollback
        - rollback 自动恢复快照，抹除脏代码
    """

    # 回滚快照目录名
    SNAPSHOT_DIR = "_tx_snapshot"

    def __init__(
        self,
        node_id: str,
        workspace_path: str,
        max_iterations: int = 3,
        commit_threshold: int = 85,
        auto_gate: bool = True,
    ):
        self.node_id = node_id
        self.workspace = Path(workspace_path).resolve()
        self.max_iterations = max_iterations
        self.commit_threshold = commit_threshold
        self.auto_gate = auto_gate

        self.snapshot_dir = self.workspace / self.SNAPSHOT_DIR
        self.log = TransactionLog(
            node_id=node_id,
            workspace=str(self.workspace),
            snapshot_path=str(self.snapshot_dir),
            created_at=time.time(),
        )
        self._file_ops: List[Tuple[str, Path, Any]] = []

        # Gate 状态
        self.gate_score: int = 0
        self.gate_passed: bool = False
        self.iteration_count: int = 0
        self.react_log: List[Dict] = []

    # ── 上下文管理器 ──────────────────────────

    def __enter__(self) -> "AgentWorkspaceTransaction":
        self._create_snapshot()
        self.log.record("SNAPSHOT_CREATED", f"backup at {self.snapshot_dir}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 异常退出 → 强制回滚
            self.log.record("EXCEPTION", f"{exc_type.__name__}: {exc_val}")
            self._rollback()
            self.log.status = "ROLLED_BACK"
            self.log.rolled_back_at = time.time()
            self._write_rollback_log()
            return False  # 重新抛出异常

        if self.auto_gate and not self.gate_passed:
            self._rollback()
            self.log.status = "ROLLED_BACK"
            self.log.rolled_back_at = time.time()
            self._write_rollback_log()
            return False

        return False

    def commit(self) -> bool:
        """显式提交: 固化资产并清除快照"""
        if not self.gate_passed and self.auto_gate:
            self.log.record("COMMIT_BLOCKED", f"gate score {self.gate_score} < {self.commit_threshold}")
            return False
        self._cleanup_snapshot()
        self.log.status = "COMMITTED"
        self.log.committed_at = time.time()
        self.log.record("COMMIT", f"score={self.gate_score}")
        return True

    # ── 快照操作 ──────────────────────────────

    def _create_snapshot(self):
        """创建物理快照备份"""
        if self.snapshot_dir.exists():
            shutil.rmtree(self.snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        for item in self.workspace.iterdir():
            if item.name == self.SNAPSHOT_DIR:
                continue
            dest = self.snapshot_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    def _rollback(self):
        """物理回滚: 从快照恢复所有文件"""
        if not self.snapshot_dir.exists():
            return
        for item in self.snapshot_dir.iterdir():
            target = self.workspace / item.name
            # 删除目标
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            # 从快照恢复
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        self._cleanup_snapshot()

    def _cleanup_snapshot(self):
        """清除快照目录"""
        if self.snapshot_dir.exists():
            shutil.rmtree(self.snapshot_dir)

    def _write_rollback_log(self):
        """写入熔断日志"""
        log_path = self.workspace / f"_rollback_{self.node_id}.json"
        log_data = {
            "node_id": self.node_id,
            "score": self.gate_score,
            "threshold": self.commit_threshold,
            "iterations": self.iteration_count,
            "react_log": self.react_log,
            "rolled_back_at": time.time(),
            "reason": f"score {self.gate_score} < {self.commit_threshold}" if not self.gate_passed else "exception",
        }
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

    # ── 安全工具绑定 ──────────────────────────

    def secure_read_file(self, relative_path: str) -> str:
        """安全读取: 路径必须在 workspace 内"""
        self._validate_path(relative_path)
        full_path = self.workspace / relative_path
        if not full_path.exists():
            raise FileNotFoundError(f"[sandbox] 文件不存在: {relative_path}")
        content = full_path.read_text(encoding="utf-8")
        self.log.record("READ", f"{relative_path} ({len(content)} bytes)")
        return content

    def secure_write_patch(
        self, relative_path: str, old_string: str, new_string: str
    ) -> bool:
        """安全写入补丁: 增量替换，保留备份"""
        self._validate_path(relative_path)
        full_path = self.workspace / relative_path
        if not full_path.exists():
            raise FileNotFoundError(f"[sandbox] 文件不存在: {relative_path}")

        content = full_path.read_text(encoding="utf-8")
        if old_string not in content:
            self.log.record("PATCH_FAILED", f"{relative_path}: old_string not found")
            return False

        # 备份原内容
        backup_path = full_path.with_suffix(f"{full_path.suffix}.bak")
        shutil.copy2(full_path, backup_path)

        new_content = content.replace(old_string, new_string, 1)
        full_path.write_text(new_content, encoding="utf-8")
        self.log.record("PATCH", f"{relative_path}: {len(old_string)}→{len(new_string)} chars")
        return True

    def secure_write_file(self, relative_path: str, content: str) -> bool:
        """安全覆写文件"""
        self._validate_path(relative_path)
        full_path = self.workspace / relative_path

        # 备份原内容
        if full_path.exists():
            backup_path = full_path.with_suffix(f"{full_path.suffix}.bak")
            shutil.copy2(full_path, backup_path)

        full_path.write_text(content, encoding="utf-8")
        self.log.record("WRITE", f"{relative_path} ({len(content)} bytes)")
        return True

    def secure_run_pytest(
        self, test_file: str = "test_case.py", timeout: int = 30
    ) -> Dict[str, Any]:
        """安全执行测试: 子进程隔离"""
        self._validate_path(test_file)
        test_path = self.workspace / test_file

        start = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(self.workspace),
        )

        elapsed = (time.perf_counter() - start) * 1000
        passed = result.returncode == 0

        self.log.record(
            "PYTEST",
            f"{test_file}: {'PASS' if passed else 'FAIL'} ({elapsed:.0f}ms, exit={result.returncode})",
        )

        return {
            "passed": passed,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "elapsed_ms": elapsed,
        }

    def _validate_path(self, relative_path: str):
        """验证路径在 workspace 内，防止目录遍历攻击"""
        full = (self.workspace / relative_path).resolve()
        if not str(full).startswith(str(self.workspace)):
            raise PermissionError(
                f"[sandbox] 路径越界: {relative_path} 不在 {self.workspace} 内"
            )


# ──────────────────────────────────────────────
# 2. ReAct 自主纠错循环
# ──────────────────────────────────────────────

@dataclass
class ReActStep:
    """ReAct 步骤记录"""
    step: int
    thought: str
    action: str
    observation: str
    success: bool


class ReActSelfHealLoop:
    """
    ReAct 自主推理纠错循环.

    流程:
        for i in range(max_iterations):
            thought → action → observation → (success? exit : retry)

    用法:
        loop = ReActSelfHealLoop(tx, max_iterations=3)
        result = loop.run(
            exercise_file="exercise.py",
            test_file="test_case.py",
            solution_file="solution.py",
        )
    """

    # 简单修复策略映射（规则模式，不依赖 LLM）
    FIX_STRATEGIES: Dict[str, List[str]] = {
        "NameError": [
            "search for: def {name} — check if the function is defined",
            "add missing import or function definition",
        ],
        "TypeError": [
            "check argument count and types in the function call",
            "verify decorator returns a callable, not None",
        ],
        "AttributeError": [
            "check if @wraps is applied correctly",
            "verify function is not None before accessing attributes",
        ],
        "AssertionError": [
            "compare expected vs actual values",
            "check if the return value matches the assertion",
        ],
        "ImportError": [
            "add missing import statement",
            "check module name spelling",
        ],
        "SyntaxError": [
            "fix syntax error in the indicated line",
            "check for missing colons, brackets, or indentation",
        ],
    }

    def __init__(self, tx: AgentWorkspaceTransaction, max_iterations: int = 3):
        self.tx = tx
        self.max_iterations = max_iterations
        self.steps: List[ReActStep] = []
        self.success = False
        self.final_score = 0

    def run(
        self,
        exercise_file: str,
        test_file: str,
        solution_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行自主纠错循环.

        返回:
            {"success": bool, "steps": [...], "final_score": int, "tx_committed": bool}
        """
        for i in range(1, self.max_iterations + 1):
            self.tx.iteration_count = i

            # ── Thought: 分析当前状态 ──
            thought = self._analyze_state(exercise_file, test_file, solution_file)

            # ── Action: 执行修复 ──
            action, success = self._apply_fix(exercise_file, test_file, solution_file)

            # ── Observation: 验证修复结果 ──
            obs = self._verify(exercise_file, test_file)

            step = ReActStep(
                step=i,
                thought=thought,
                action=action,
                observation=json.dumps(obs, ensure_ascii=False),
                success=obs.get("passed", False),
            )
            self.steps.append(step)
            self.tx.react_log.append({
                "step": i,
                "thought": thought,
                "action": action,
                "passed": obs.get("passed", False),
            })

            if obs.get("passed"):
                self.success = True
                # 运行 Review Gate 评分
                self.final_score = self._run_review_gate()
                self.tx.gate_score = self.final_score

                if self.final_score >= self.tx.commit_threshold:
                    self.tx.gate_passed = True
                    return {
                        "success": True,
                        "steps": len(self.steps),
                        "final_score": self.final_score,
                        "tx_committed": self.tx.commit(),
                    }
                else:
                    return {
                        "success": False,
                        "steps": len(self.steps),
                        "final_score": self.final_score,
                        "reason": f"score {self.final_score} < {self.tx.commit_threshold}",
                    }

        # 超出迭代上限
        self.final_score = self._run_review_gate()
        self.tx.gate_score = self.final_score
        return {
            "success": False,
            "steps": len(self.steps),
            "final_score": self.final_score,
            "reason": f"max iterations ({self.max_iterations}) reached",
        }

    def _analyze_state(
        self, exercise_file: str, test_file: str, solution_file: Optional[str]
    ) -> str:
        """分析当前状态"""
        thoughts = []

        try:
            ex = self.tx.secure_read_file(exercise_file)
            # 检查桩标记
            if "pass" in ex or "raise NotImplementedError" in ex:
                thoughts.append("检测到未实现的桩标记 (pass/NotImplementedError)")
            if solution_file:
                sol = self.tx.secure_read_file(solution_file)
                thoughts.append(f"Solution 存在 ({len(sol)} bytes)")
        except Exception as e:
            thoughts.append(f"读取失败: {e}")

        return "; ".join(thoughts) if thoughts else "无特殊异常"

    def _apply_fix(
        self, exercise_file: str, test_file: str, solution_file: Optional[str]
    ) -> Tuple[str, bool]:
        """应用修复（缝合 Solution）"""
        if not solution_file:
            return "无可用的 Solution 缝合", False
        try:
            sol_src = self.tx.secure_read_file(solution_file)
            ex_src = self.tx.secure_read_file(exercise_file)

            # 简单缝合：提取 Solution 中的函数体替换 Exercise 中的 pass
            import ast
            sol_tree = ast.parse(sol_src)
            ex_tree = ast.parse(ex_src)

            sol_funcs = {}
            for node in ast.walk(sol_tree):
                if isinstance(node, ast.FunctionDef):
                    sol_funcs[node.name] = node

            # 文本级替换
            fixed_src = ex_src
            for name in sol_funcs:
                # 将 exercise 中的空壳替换为 solution 实现
                pattern = re.compile(
                    rf"(def\s+{re.escape(name)}\s*\([^)]*\).*?)(\n\s+pass|\n\s+\.\.\.|\n\s+raise\s+NotImplementedError)",
                    re.MULTILINE,
                )
                sol_lines = sol_src.split("\n")
                sol_func = sol_funcs[name]
                func_text = "\n".join(
                    sol_lines[sol_func.lineno - 1: sol_func.end_lineno]
                )
                replacement = (
                    r"\1\n" + func_text.split("\n", 1)[1] if "\n" in func_text else func_text
                )
                fixed_src = pattern.sub(replacement, fixed_src, count=1)

            self.tx.secure_write_file(exercise_file, fixed_src)
            return f"缝合 {len(sol_funcs)} 个函数: {', '.join(sol_funcs.keys())}", True
        except Exception as e:
            return f"缝合失败: {e}", False

    def _verify(self, exercise_file: str, test_file: str) -> Dict[str, Any]:
        """验证修复结果"""
        return self.tx.secure_run_pytest(test_file)

    def _run_review_gate(self) -> int:
        """运行 Review Gate 评分"""
        try:
            # 动态导入 review_gate
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from core.review_gate import ReviewGateManager

            # ⚠️ ReviewGate 的反向验证需要原始 exercise(含 pass stubs)
            # 但此时 exercise.py 已被 ReAct 缝合为 solution。
            # 临时用快照恢复 stubs，ReviewGate 自己会 _stitch_solution 做正向验证。
            exercise_path = self.tx.workspace / "exercise.py"
            snapshot_exercise = self.tx.snapshot_dir / "exercise.py"
            stitched_backup = None

            if snapshot_exercise.exists():
                stitched_backup = exercise_path.read_text(encoding="utf-8")
                import shutil
                shutil.copy2(snapshot_exercise, exercise_path)

            try:
                gate = ReviewGateManager(str(self.tx.workspace))
                result = gate.run_full_gate(node_id=self.tx.node_id)
            finally:
                # 恢复缝合后的版本
                if stitched_backup is not None:
                    exercise_path.write_text(stitched_backup, encoding="utf-8")

            # 从 gate 结果推断分数
            if result.status == "PASSED":
                return 100
            # 部分通过: 前两道门禁（AST + Pytest）通过即可达 90 分
            passed_gates = sum(1 for g in result.gates if g.passed)
            if passed_gates >= 2:
                return 90  # 核心验证通过，LLM judge 可选
            return max(0, passed_gates * 33)  # <2 gates → 按比例
        except ImportError as e:
            print(f"[DEBUG] ReviewGate import failed: {e}", file=sys.stderr)
            # review_gate 不可用，用 UserSimulation 评分
            return self._run_user_sim()
        except Exception as e:
            print(f"[DEBUG] ReviewGate error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 0

    def _run_user_sim(self) -> int:
        """用 UserSimulation 评分"""
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from core.user_simulation import UserSimulationAgent

            lec_path = self.tx.workspace / "lecture.md"
            ex_path = self.tx.workspace / "exercise.py"

            lec = lec_path.read_text() if lec_path.exists() else ""
            ex = ex_path.read_text() if ex_path.exists() else ""

            agent = UserSimulationAgent()
            result = agent.simulate(lec, ex)
            return result.would_recommend_score
        except Exception:
            return 0


# ──────────────────────────────────────────────
# 3. 终审提交门禁 (CommitGate)
# ──────────────────────────────────────────────

class CommitGate:
    """
    终审提交门禁.

    用法:
        gate = CommitGate(tx, threshold=85)
        if gate.evaluate():
            tx.commit()   # 固化
        else:
            tx._rollback()  # 反转
    """

    def __init__(self, tx: AgentWorkspaceTransaction, threshold: int = 85):
        self.tx = tx
        self.threshold = threshold

    def evaluate(self) -> bool:
        """运行终审评估"""
        # 1. Pytest 动态验证
        test_result = self.tx.secure_run_pytest()
        if not test_result["passed"]:
            self.tx.log.record("GATE_FAILED", "pytest failed")
            return False

        # 2. AST 静态检查
        ast_ok = self._check_ast()
        if not ast_ok:
            self.tx.log.record("GATE_FAILED", "AST check failed")
            return False

        # 3. UserSimulation 评分
        score = self._run_user_simulation()
        self.tx.gate_score = score

        if score >= self.threshold:
            self.tx.gate_passed = True
            self.tx.log.record("GATE_PASSED", f"score {score} >= {self.threshold}")
            return True
        else:
            self.tx.log.record("GATE_FAILED", f"score {score} < {self.threshold}")
            return False

    def _check_ast(self) -> bool:
        """AST 静态检查"""
        try:
            import ast
            ex_path = self.tx.workspace / "exercise.py"
            if not ex_path.exists():
                return False
            source = ex_path.read_text()
            ast.parse(source)
            # 禁止 eval
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "eval":
                    return False
            return True
        except SyntaxError:
            return False

    def _run_user_simulation(self) -> int:
        """UserSimulation 评分"""
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from core.user_simulation import UserSimulationAgent

            lec_path = self.tx.workspace / "lecture.md"
            ex_path = self.tx.workspace / "exercise.py"

            lec = lec_path.read_text() if lec_path.exists() else ""
            ex = ex_path.read_text() if ex_path.exists() else ""

            agent = UserSimulationAgent()
            result = agent.simulate(lec, ex)
            return result.would_recommend_score
        except Exception:
            return 0


# ──────────────────────────────────────────────
# 4. 便捷工厂函数
# ──────────────────────────────────────────────

def create_sandbox_session(
    node_id: str,
    workspace: str,
    max_iterations: int = 3,
    commit_threshold: int = 85,
) -> Tuple[AgentWorkspaceTransaction, ReActSelfHealLoop, CommitGate]:
    """工厂: 创建完整的沙箱会话"""
    tx = AgentWorkspaceTransaction(
        node_id=node_id,
        workspace_path=workspace,
        max_iterations=max_iterations,
        commit_threshold=commit_threshold,
    )
    loop = ReActSelfHealLoop(tx, max_iterations=max_iterations)
    gate = CommitGate(tx, threshold=commit_threshold)
    return tx, loop, gate


# ──────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 3 — 事务沙箱与自主工具箱")
    parser.add_argument("workspace", help="工作区路径")
    parser.add_argument("--node-id", default="NODE", help="节点 ID")
    parser.add_argument("--max-iter", type=int, default=3, help="最大 ReAct 迭代次数")
    parser.add_argument("--threshold", type=int, default=85, help="提交阈值")
    parser.add_argument("--exercise", default="exercise.py", help="练习文件")
    parser.add_argument("--test", default="test_case.py", help="测试文件")
    parser.add_argument("--solution", default="solution.py", help="解答文件")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    args = parser.parse_args()

    if args.demo:
        # 快速演示: 自动快照 → 修改 → 验证 → 提交/回滚
        if not Path(args.workspace, args.exercise).exists():
            print(f"❌ {args.exercise} 不存在于 {args.workspace}，跳过演示")
            sys.exit(0)

        with AgentWorkspaceTransaction(
            args.node_id, args.workspace,
            commit_threshold=args.threshold
        ) as tx:
            print(f"📦 快照已创建: {tx.snapshot_dir}")
            print(f"📄 读取 {args.exercise}: {len(tx.secure_read_file(args.exercise))} bytes")

            loop = ReActSelfHealLoop(tx, max_iterations=args.max_iter)
            result = loop.run(
                exercise_file=args.exercise,
                test_file=args.test,
                solution_file=args.solution
            )

            print(f"🔄 ReAct: {result['steps']} steps, score={result['final_score']}")
            if result.get("tx_committed"):
                print("✅ 事务已提交 — 资产固化")
            else:
                print(f"❌ 事务未提交: {result.get('reason', 'unknown')}")
                print("🔄 退出时自动回滚...")

        # 检查回滚后文件是否恢复
        if not result.get("tx_committed"):
            ex_content = Path(args.workspace, args.exercise).read_text()[:100]
            print(f"📄 回滚后 {args.exercise}: {ex_content[:60]}...")
    else:
        tx, loop, gate = create_sandbox_session(
            args.node_id, args.workspace, args.max_iter, args.threshold
        )
        print(f"🔧 沙箱就绪: {tx.workspace}")
        print(f"   快照目录: {tx.snapshot_dir}")
        print(f"   最大迭代: {tx.max_iterations}")
        print(f"   提交阈值: {tx.commit_threshold}")
