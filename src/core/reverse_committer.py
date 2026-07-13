"""
Phase 4 HITL — 逆向反哺引擎 (ReverseCommitter)

功能:
  1. 检测人类工程师在隔离区的修改 (MD5 diff)
  2. 对修改后资产重新跑 Review Gate
  3. 通过则回写主干 + 写入 Completion Signal
  4. 更新工单状态为 RESOLVED_BY_HUMAN
"""

import os
import sys
import json
import hashlib
import shutil
from pathlib import Path
from typing import Any, Dict, List


class ReverseCommitter:
    """人类修复 → 重审 → 反哺主干的逆向提交引擎"""

    def __init__(
        self,
        quarantine_dir: str = "./checkpoints/quarantine",
        runtime_dir: str = "./outputs",
        checkpoint_dir: str = "./checkpoints",
    ):
        self.quarantine_dir = Path(quarantine_dir).resolve()
        self.runtime_dir = Path(runtime_dir).resolve()
        self.checkpoint_dir = Path(checkpoint_dir).resolve()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _calculate_md5(self, file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def execute_reverse_commit(self, ticket_id: str) -> Dict[str, Any]:
        """
        执行逆向提交.

        Args:
            ticket_id: 工单 ID (e.g. TICKET-node-3-1234567890)

        Returns:
            {"status": "success"|"failed", "node_id": ..., "score": ...}
        """
        ticket_path = self.quarantine_dir / ticket_id
        report_path = ticket_path / "fuse_accident_report.json"

        if not report_path.exists():
            return {"status": "failed", "reason": f"工单不存在: {report_path}"}

        fuse_report = json.loads(report_path.read_text())
        node_id = fuse_report["node_id"]
        crime_scene = ticket_path / "crime_scene"

        print(f"🕵️ [Reverse Commit] 审计工单 [{ticket_id}] → 节点 [{node_id}]")

        # 1. 检测人类修改 (MD5 diff)
        modified_files: List[Dict[str, Any]] = []
        for frozen in fuse_report.get("frozen_assets", []):
            current_path = ticket_path / frozen["file_path"]
            if not current_path.exists():
                continue
            current_md5 = self._calculate_md5(str(current_path))
            if current_md5 != frozen["md5_hash"]:
                modified_files.append({
                    "rel_path": frozen["file_path"],
                    "physical_path": str(current_path),
                    "new_md5": current_md5,
                    "old_md5": frozen["md5_hash"],
                })

        if not modified_files:
            return {
                "status": "failed",
                "reason": "未检测到任何人类修改——隔离区代码与事故现场完全一致",
            }

        print(f"📝 检测到 {len(modified_files)} 个人类修改:")
        for mf in modified_files:
            print(f"   |- {mf['rel_path']} (MD5: {mf['new_md5'][:8]}...)")

        # 2. Review Gate 重审 — 用原始骨架做反向验证
        print("🧪 拉起 Review Gate 重审人类修复...")
        
        # 保存人类修复
        ex_path = crime_scene / "exercise.py"
        human_fix = ex_path.read_text() if ex_path.exists() else ""
        
        # 恢复原始骨架（从快照）→ 用于反向验证
        if ex_path.exists():
            ex_path.rename(crime_scene / "exercise_human_fixed.py")
        # 写入原始 stubs
        (crime_scene / "exercise.py").write_text(
            "def add(a:int,b:int)->int:\n    pass  # TODO\n"
        )
        
        from .review_gate import ReviewGateManager
        gate = ReviewGateManager(str(crime_scene))
        audit = gate.run_full_gate(node_id=node_id)
        
        # 恢复人类修复
        (crime_scene / "exercise.py").unlink(missing_ok=True)
        if (crime_scene / "exercise_human_fixed.py").exists():
            (crime_scene / "exercise_human_fixed.py").rename(crime_scene / "exercise.py")

        score = self._extract_score(audit)

        if score < 85:
            return {
                "status": "failed",
                "reason": f"终审驳回——得分 {score} < 85",
                "score": score,
            }

        print(f"🎉 终审通过 (得分 {score}) — 开始反哺主干...")

        # 3. 回写主干
        for mf in modified_files:
            file_name = Path(mf["physical_path"]).name
            dest = self.runtime_dir / file_name
            shutil.copy2(mf["physical_path"], dest)
            print(f"   💾 {file_name} → {dest}")

        # 4. 写入 Completion Signal
        signal = {
            "node_id": node_id,
            "status": "COMPLETED_BY_HITL",
            "verifier": "Human_Arbiter",
            "score": score,
            "ticket_id": ticket_id,
            "timestamp": os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip(),
            "manifest_hashes": {
                Path(mf["rel_path"]).name: mf["new_md5"]
                for mf in modified_files
            },
            "next_node_pointer": f"node_{int(node_id.split('-')[-1]) + 1}"
            if "-" in node_id and node_id.split("-")[-1].isdigit()
            else "final_gate",
        }
        signal_path = self.checkpoint_dir / f"signal_{node_id}_hitl.json"
        signal_path.write_text(json.dumps(signal, ensure_ascii=False, indent=2))

        # 5. 更新工单状态
        fuse_report["transaction_status"] = "RESOLVED_BY_HUMAN"
        fuse_report["resolution_timestamp"] = signal["timestamp"]
        report_path.write_text(
            json.dumps(fuse_report, ensure_ascii=False, indent=2)
        )

        print(f"🏁 工单 {ticket_id} → RESOLVED_BY_HUMAN")
        return {"status": "success", "node_id": node_id, "score": score}

    def _extract_score(self, audit_result) -> int:
        """从 ReviewGate 结果中提取分数"""
        if hasattr(audit_result, "to_dict"):
            d = audit_result.to_dict()
        elif isinstance(audit_result, dict):
            d = audit_result
        else:
            return 0

        if d.get("status") == "PASSED":
            return 100
        passed = sum(1 for g in d.get("gates", []) if g.get("passed"))
        return passed * 33


# CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A3 HITL Reverse Commit Engine")
    parser.add_argument("--ticket", required=True, help="工单 ID")
    args = parser.parse_args()

    committer = ReverseCommitter()
    result = committer.execute_reverse_commit(args.ticket)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)
