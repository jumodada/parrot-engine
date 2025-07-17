# 🚀 Python Persona Engine 快速开始指南

## 方式一：快速体验（推荐新手）

如果你只想快速体验项目功能，无需复杂配置：

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd python-persona-engine

# 2. 安装基础依赖
pip install loguru asyncio

# 3. 运行演示
python run_example.py
```

## 方式二：完整安装（完整功能）

### Windows 用户

1. **运行自动安装脚本**：
   ```cmd
   # 双击运行或在命令行执行
   scripts\install.bat
   ```

2. **配置API密钥**：
   - 编辑 `config\config.yaml`
   - 设置你的OpenAI API密钥：
     ```yaml
     llm:
       text_api_key: "sk-your-actual-api-key-here"
     ```

3. **运行程序**：
   ```cmd
   run.bat
   ```

### Linux/Mac 用户

1. **运行自动安装脚本**：
   ```bash
   chmod +x scripts/install.sh
   ./scripts/install.sh
   ```

2. **配置API密钥**：
   ```bash
   # 编辑配置文件
   nano config/config.yaml
   # 设置你的API密钥
   ```

3. **运行程序**：
   ```bash
   ./run.sh
   # 或者
   python main.py
   ```

## 方式三：手动安装（开发者）

### 1. 环境准备

```bash
# 检查Python版本（需要3.9+）
python --version

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 2. 安装依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装基础依赖
pip install -r requirements.txt

# （可选）安装开发依赖
pip install -r requirements-dev.txt

# （可选）GPU支持
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 3. 系统依赖

**Windows**：
- 下载并安装 [espeak-ng](https://github.com/espeak-ng/espeak-ng/releases)

**Ubuntu/Debian**：
```bash
sudo apt-get install espeak-ng ffmpeg portaudio19-dev
```

**macOS**：
```bash
brew install espeak-ng ffmpeg portaudio
```

### 4. 配置设置

```bash
# 复制配置模板
cp config/config.example.yaml config/config.yaml

# 编辑配置文件
# 至少需要设置 LLM API密钥
```

### 5. 运行程序

```bash
# UI模式（推荐）
python main.py

# 命令行模式
python main.py --no-ui

# 自定义配置
python main.py --config my_config.yaml

# 调试模式
python main.py --debug
```

## 🔑 必需的API密钥

为了完整体验功能，你需要：

1. **OpenAI API密钥** (必需)
   - 访问：https://platform.openai.com/api-keys
   - 用于：大语言模型对话

2. **其他可选API密钥**：
   - Anthropic (Claude)
   - ElevenLabs (高质量TTS)
   - Azure Speech Services

## 📱 使用界面

程序启动后会显示控制面板，包含：

- **状态监控**：引擎状态、性能指标
- **控制按钮**：启动/停止引擎、测试功能
- **聊天界面**：文本对话测试
- **参数调节**：音量、语速等

## 🎤 语音交互

1. 点击"启动引擎"
2. 对着麦克风说话
3. AI会自动：
   - 识别你的语音
   - 生成回复
   - 播放语音回应
   - 显示Live2D动画（如果启用）

## 🎭 Live2D支持

如果要使用Live2D功能：

1. 将Live2D模型放在 `resources/live2d/` 目录
2. 在配置文件中设置：
   ```yaml
   live2d:
     enabled: true
     model_path: "resources/live2d/your_model"
   ```

## ❗ 常见问题

**Q: 程序启动失败**
- 检查Python版本（需要3.9+）
- 确保安装了所有依赖
- 查看日志文件：`logs/persona_engine.log`

**Q: 语音识别不工作**
- 检查麦克风权限
- 确保麦克风未被其他程序占用
- 尝试在配置中指定麦克风设备

**Q: API调用失败**
- 检查API密钥是否正确
- 确保网络连接正常
- 检查API配额是否用完

**Q: 音频播放问题**
- 检查扬声器/耳机连接
- 尝试调整音量设置
- 检查音频设备权限

## 📞 获取帮助

如果遇到问题：

1. 查看 `logs/persona_engine.log` 日志文件
2. 运行 `python main.py --debug` 获取详细信息
3. 查看项目README.md
4. 提交Issue到项目仓库

祝你使用愉快！🎉 