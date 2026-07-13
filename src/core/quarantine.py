"""
Phase 4 HITL — 冷冻隔离管理器 (QuarantineManager)

功能:
  - freeze_scene: 物理克隆犯罪现场 + MD5哈希闭锁 + 一键复现脚本
  - 工单存放于 checkpoints/quarantine/TICKET-{node}-{timestamp}/
"""

import os
import time
import hashlib
import shutil
import json
from pathlib import Path
from typing import Dict, Any

from .contracts import FuseReport, FileMetadata


class QuarantineManager:
    """熔断现场冷冻隔离管理器"""

    def __init__(self, base_quarantine_dir: str = "./checkpoints/quarantine"):
        self.base_dir = Path(base_quarantine_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _calculate_md5(self, file_path: str) -> str:
        """计算文件 MD5 哈希"""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def freeze_scene(
        self, node_id: str, workspace_path: str, report_data: Dict[str, Any]
    ) -> str:
        """
        冷冻犯罪现场.

        Args:
            node_id: 节点 ID
            workspace_path: 运行时目录 (e.g. outputs/)
            report_data: 熔断信息 {score, stage, traceback, blindspot}

        Returns:
            ticket_id: 工单唯一编号
        """
        ticket_id = f"TICKET-{node_id}-{int(time.time())}"
        ticket_dir = self.base_dir / ticket_id
        ticket_dir.mkdir(parents=True, exist_ok=True)

        # 1. 物理克隆现场
        src_dir = Path(workspace_path)
        dest_dir = ticket_dir / "crime_scene"
        if src_dir.exists():
            # 只克隆代码文件, 跳过快照/缓存/venv
            dest_dir.mkdir(exist_ok=True)
            for item in src_dir.iterdir():
                if item.name.startswith("_") or item.name.startswith("."):
                    continue
                if item.is_file():
                    shutil.copy2(item, dest_dir / item.name)

        # 2. 计算冻结资产的 MD5 账本
        frozen_files: list[FileMetadata] = []
        if dest_dir.exists():
            for root, _, files in os.walk(dest_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, ticket_dir)
                    frozen_files.append(FileMetadata(
                        file_path=rel_path,
                        md5_hash=self._calculate_md5(full_path),
                        file_size_bytes=os.path.getsize(full_path),
                    ))

        # 3. 写入熔断报告
        report = FuseReport(
            ticket_id=ticket_id,
            node_id=node_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            final_score=float(report_data.get("score", 0.0)),
            exhausted_rounds=report_data.get("rounds", 3),
            failure_stage=report_data.get("stage", "UNKNOWN"),
            raw_error_traceback=report_data.get("traceback", ""),
            agent_cognitive_blindspot=report_data.get("blindspot", ""),
            frozen_assets=frozen_files,
            transaction_status="PENDING_HITL",
        )
        (ticket_dir / "fuse_accident_report.json").write_text(
            report.to_json(), encoding="utf-8"
        )

        # 4. 生成一键复现脚本
        self._generate_reproduce_script(ticket_dir, node_id)

        return ticket_id

    def _generate_reproduce_script(self, ticket_dir: Path, node_id: str):
        """生成可执行复现脚本"""
        script_path = ticket_dir / "reproduce.sh"
        script = f"""#!/bin/bash
set -e
echo "====== 🧪 A3 HITL: 原地复现节点 [{node_id}] 熔断现场 ======"
echo "📋 冷冻资产 MD5 校验:"
python3 -c "
import json
with open('{ticket_dir}/fuse_accident_report.json') as f:
    data = json.load(f)
    for fa in data['frozen_assets']:
        print(f'  |- {{fa[\"file_path\"]}}: {{fa[\"md5_hash\"]}}')
"
echo "──────────────────────────────────────"
echo "🚀 拉起 Review Gate 进行无污染复现..."
if [ -f "{ticket_dir}/crime_scene/test_case.py" ]; then
    python3 -m pytest {ticket_dir}/crime_scene/test_case.py -v --tb=short 2>&1 | tail -20
else
    echo "❌ 未找到 test_case.py"
fi
"""
        script_path.write_text(script)
        os.chmod(script_path, 0o755)

    def list_tickets(self) -> list[Dict[str, Any]]:
        """列出所有工单"""
        tickets = []
        if self.base_dir.exists():
            for d in sorted(self.base_dir.iterdir(), reverse=True):
                if d.is_dir() and d.name.startswith("TICKET-"):
                    report_path = d / "fuse_accident_report.json"
                    if report_path.exists():
                        try:
                            data = json.loads(report_path.read_text())
                            tickets.append({
                                "ticket_id": data["ticket_id"],
                                "status": data.get("transaction_status", "UNKNOWN"),
                                "node": data.get("node_id", ""),
                                "score": data.get("final_score", 0),
                            })
                        except Exception:
                            pass
        return tickets
