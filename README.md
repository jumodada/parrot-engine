# 🎭 Parrot Engine


一个使用AI驱动的交互式虚拟角色引擎，支持语音识别、大语言模型对话、文本转语音和Live2D动画。

## ✨ 主要功能

- 🎤 **语音识别 (ASR)**: 使用OpenAI Whisper进行实时语音转文字
- 🧠 **大语言模型集成**: 支持OpenAI、Anthropic等API
- 🗣️ **文本转语音 (TTS)**: 自然语音合成
- 🎭 **Live2D动画**: 支持表情和动作控制
- 🎮 **实时交互**: 支持打断检测和自然对话流程
- 🖥️ **现代UI**: 基于CustomTkinter的控制界面
- ⚙️ **灵活配置**: 完全可配置的系统参数

## 🚀 快速开始

### 系统要求

- Python 3.9+
- 支持CUDA的NVIDIA GPU (推荐)
- 麦克风和扬声器
- 4GB+ RAM

### 安装

1. 克隆仓库:
```bash
git clone <repository-url>
cd python-persona-engine
```

2. 创建虚拟环境:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows
```

3. 安装依赖:
```bash
pip install -r requirements.txt
```

4. 配置设置:
```bash
cp config/config.example.yaml config/config.yaml
# 编辑 config.yaml 设置API密钥等参数
```

5. 运行:
```bash
python main.py
```

## 📁 项目结构

```
python-persona-engine/
├── src/
│   ├── core/           # 核心引擎逻辑
│   ├── modules/        # 功能模块
│   │   ├── asr/        # 语音识别
│   │   ├── tts/        # 文本转语音  
│   │   ├── llm/        # 大语言模型
│   │   ├── live2d/     # Live2D动画
│   │   └── audio/      # 音频处理
│   ├── ui/             # 用户界面
│   └── utils/          # 工具函数
├── config/             # 配置文件
├── resources/          # 资源文件
│   ├── models/         # AI模型
│   ├── live2d/         # Live2D模型
│   └── sounds/         # 音频资源
└── main.py            # 主入口
```

## 🔧 配置说明

编辑 `config/config.yaml` 来配置系统:

```yaml
# LLM设置
llm:
  provider: "openai"  # openai, anthropic, local
  api_key: "your-api-key"
  model: "gpt-4"
  endpoint: "https://api.openai.com/v1"

# TTS设置  
tts:
  engine: "coqui"     # coqui, espeak
  voice: "en_custom"
  speed: 1.0

# ASR设置
asr:
  model: "base"       # tiny, base, small, medium, large
  language: "zh"      # zh, en, auto

# Live2D设置
live2d:
  model_path: "resources/live2d/aria"
  width: 1080
  height: 1920
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- 原版项目: [handcrafted-persona-engine](https://github.com/fagenorn/handcrafted-persona-engine)
- OpenAI Whisper
- Coqui TTS
- Live2D SDK 