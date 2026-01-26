#!/bin/bash
# 游戏中心Bot启动脚本 (Linux/Ubuntu)

echo "正在启动游戏中心Bot..."

# 检查Python版本
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "错误: 未找到Python，请先安装Python 3.8+"
    exit 1
fi

# 检查Python版本是否满足要求
PYTHON_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "检测到Python版本: $PYTHON_VERSION"

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 检查依赖是否安装
if ! $PYTHON -c "import discord" &> /dev/null; then
    echo "正在安装依赖..."
    $PYTHON -m pip install -r requirements.txt
fi

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "警告: 未找到.env文件，请复制.env.example并配置BOT_TOKEN"
    echo "运行: cp .env.example .env"
    exit 1
fi

# 启动Bot
$PYTHON bot.py