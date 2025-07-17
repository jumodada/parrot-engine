#!/bin/bash
# Python Persona Engine 安装脚本 (Linux/macOS)

set -e

echo "🎭 Python Persona Engine 安装脚本"
echo "=================================="

# 检查Python版本
echo "📋 检查Python版本..."
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.9"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo "✅ Python版本: $python_version (满足要求: >= $required_version)"
else
    echo "❌ Python版本过低: $python_version (需要: >= $required_version)"
    echo "请升级Python到3.9或更高版本"
    exit 1
fi

# 检查是否有GPU支持
echo "🔍 检查GPU支持..."
if command -v nvidia-smi &> /dev/null; then
    echo "✅ 检测到NVIDIA GPU"
    GPU_SUPPORT="true"
else
    echo "⚠️  未检测到NVIDIA GPU，将使用CPU模式"
    GPU_SUPPORT="false"
fi

# 创建虚拟环境
echo "📦 创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 虚拟环境已创建"
else
    echo "ℹ️  虚拟环境已存在"
fi

# 激活虚拟环境
echo "🔌 激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "⬆️  升级pip..."
pip install --upgrade pip

# 安装基础依赖
echo "📥 安装基础依赖..."
pip install -r requirements.txt

# 安装GPU支持（如果可用）
if [ "$GPU_SUPPORT" = "true" ]; then
    echo "🚀 安装GPU支持..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
fi

# 检查是否需要安装额外依赖
echo "🔧 检查系统依赖..."

# 检查espeak-ng
if ! command -v espeak-ng &> /dev/null; then
    echo "⚠️  未找到espeak-ng，请手动安装:"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "  Ubuntu/Debian: sudo apt-get install espeak-ng"
        echo "  Fedora/RHEL: sudo dnf install espeak-ng"
        echo "  Arch: sudo pacman -S espeak-ng"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  macOS: brew install espeak-ng"
    fi
else
    echo "✅ espeak-ng 已安装"
fi

# 检查ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  未找到ffmpeg，请手动安装:"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
        echo "  Fedora/RHEL: sudo dnf install ffmpeg"
        echo "  Arch: sudo pacman -S ffmpeg"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  macOS: brew install ffmpeg"
    fi
else
    echo "✅ ffmpeg 已安装"
fi

# 创建配置文件
echo "⚙️  设置配置文件..."
if [ ! -f "config/config.yaml" ]; then
    cp config/config.example.yaml config/config.yaml
    echo "✅ 已创建配置文件: config/config.yaml"
    echo "🔑 请编辑配置文件并设置您的API密钥"
else
    echo "ℹ️  配置文件已存在: config/config.yaml"
fi

# 创建启动脚本
echo "📝 创建启动脚本..."
cat > run.sh << 'EOF'
#!/bin/bash
# Python Persona Engine 启动脚本

# 激活虚拟环境
source venv/bin/activate

# 运行程序
python main.py "$@"
EOF

chmod +x run.sh
echo "✅ 启动脚本已创建: ./run.sh"

# 安装完成
echo ""
echo "🎉 安装完成！"
echo ""
echo "下一步:"
echo "1. 编辑配置文件: config/config.yaml"
echo "2. 设置您的API密钥 (OpenAI, Anthropic等)"
echo "3. 运行程序: ./run.sh 或 python main.py"
echo ""
echo "更多信息请查看 README.md"
echo ""

# 提示配置API密钥
echo "🔑 重要提醒:"
echo "请确保在config/config.yaml中设置正确的API密钥："
echo "  - OpenAI API密钥 (用于LLM)"
echo "  - 其他服务的API密钥 (如需要)"
echo ""
echo "没有正确的API密钥，引擎将无法正常工作。" 