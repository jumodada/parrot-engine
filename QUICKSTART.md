# 🎭 Python Persona Engine 快速入门指南

这是一个简明的入门指南，帮助您快速设置并运行 Python Persona Engine。

## 🖥️ 系统要求

- **Python**: 3.9 或更高版本
- **操作系统**: Windows 10/11, macOS, Linux (Ubuntu 20.04+推荐)
- **硬件**: 
  - **CPU模式**: 4GB+ RAM (基础功能，性能有限)
  - **GPU模式** (推荐): NVIDIA GPU + CUDA 11.8+ (8GB+ VRAM)

## 🚀 快速体验

如果您想快速体验基本功能，可以运行示例脚本：

```bash
python run_example.py
```

这将启动一个简单的聊天界面，展示基本功能。不需要API密钥或完整配置。

## 📦 完整安装

### Windows

1. 双击 `scripts/install.bat`，自动化脚本将完成下列操作：
   - 检查Python版本
   - 创建虚拟环境
   - 安装依赖
   - 创建配置文件
   - 生成启动脚本

2. 安装系统依赖：
   - 下载并安装 [espeak-ng](https://github.com/espeak-ng/espeak-ng/releases)
   - 下载并安装 [ffmpeg](https://ffmpeg.org/download.html)

### Linux/macOS

1. 运行安装脚本：
   ```bash
   chmod +x scripts/install.sh
   ./scripts/install.sh
   ```

2. 安装系统依赖：
   - Ubuntu/Debian: `sudo apt-get install espeak-ng ffmpeg`
   - macOS: `brew install espeak-ng ffmpeg`

## 🔧 手动安装

如果自动化脚本不适用于您的环境，可以按照以下步骤手动安装：

### 1. 创建虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 2. 安装Python依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 安装系统依赖

- **espeak-ng**: 用于基础的文本转语音 (TTS)
- **ffmpeg**: 用于音频处理

### 4. 配置

1. 复制示例配置文件：
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```
2. 编辑 `config/config.yaml`，设置API密钥和其他选项。

## 🔑 API密钥

完整功能需要以下API密钥（至少需要其中一个）：

- **OpenAI API密钥**: 用于GPT模型和Whisper ASR
- **Anthropic API密钥**: 用于Claude模型
- **本地替代方案**: 
  - Ollama: 运行本地LLM
  - Whisper.cpp: 本地ASR

## 🖱️ 使用界面

启动控制面板：

```bash
python main.py
# 或使用生成的脚本
./run.sh  # Linux/macOS
run.bat   # Windows
```

控制面板功能：
- 启动/停止引擎
- 监控状态和性能
- 调整音量和速度
- 查看对话历史记录

## 🎙️ 语音交互

1. 确保麦克风配置正确
2. 在控制面板中点击"启动"
3. 开始对话
4. 可通过设置调整灵敏度和响应阈值

## 🎭 Live2D支持

要使用Live2D角色：

1. 获取Live2D模型（.model3.json和相关文件）
2. 将模型文件放在 `resources/live2d/模型名称/` 目录下
3. 在配置文件中设置相应的路径
4. 重启引擎

## ❓ 常见问题

### 安装问题

- **依赖安装失败**:
  - 检查Python版本（3.9+）
  - 尝试逐个安装依赖以识别具体错误
  - 确保系统依赖已安装（espeak-ng, ffmpeg）

- **GPU相关错误**:
  - 确保安装了兼容的CUDA版本
  - 检查GPU驱动是否最新
  - 尝试使用CPU模式（在配置文件中设置`asr.device: "cpu"`）

### 运行问题

- **引擎启动失败**:
  - 检查配置文件是否正确
  - 查看日志文件获取详细错误信息（logs目录）
  - 确保所有API密钥都有效

- **音频问题**:
  - 检查麦克风和扬声器设置
  - 尝试在配置中指定设备名称
  - 调整音量和录音阈值 