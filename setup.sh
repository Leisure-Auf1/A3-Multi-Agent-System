#!/bin/bash
# A3 多智能体系统开发环境快速设置
# 用法: bash setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=== A3 多智能体系统 - 环境设置 ==="

# 1. 创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# 2. 升级 pip
pip install --upgrade pip setuptools wheel -q

# 3. 安装 PyTorch
echo "安装 PyTorch (CUDA 13.2)..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu132

# 4. 安装核心依赖
echo "安装核心依赖..."
pip install \
    transformers accelerate sentencepiece \
    fastapi uvicorn loguru python-dotenv \
    openai anthropic \
    langchain langchain-community langgraph \
    gradio streamlit jupyter \
    numpy pandas matplotlib seaborn scikit-learn \
    datasets tokenizers \
    httpx aiohttp websockets \
    rich tqdm pyyaml

# 5. 设置 CUDA 环境
export PATH="/opt/cuda/bin:$PATH"
export LD_LIBRARY_PATH="/opt/cuda/lib64:$LD_LIBRARY_PATH"

# 6. 验证
echo ""
echo "=== 验证 ==="
python3 -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')
"
echo ""
echo "✅ 环境设置完成!"
echo "运行: source projects/a3-multi-agent-system/activate.sh"
