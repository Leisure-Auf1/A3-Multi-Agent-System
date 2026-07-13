#!/bin/bash
# A3 多智能体系统开发环境激活脚本
# Source this file: source projects/A3-Multi-Agent-System/activate.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    export PATH="/opt/cuda/bin:$PATH"
    export LD_LIBRARY_PATH="/opt/cuda/lib64:$LD_LIBRARY_PATH"
    echo "✅ A3 开发环境已激活 (PyTorch CUDA ready)"
    echo "   Python: $(python3 --version)"
    echo "   CUDA:   $(nvcc --version 2>/dev/null | grep 'release' | awk '{print $6}')"
else
    echo "❌ 虚拟环境不存在，请先运行 setup.sh"
fi
