# 🎭 Parrot Engine - 虚拟数字人引擎

**Parrot Engine** 是一个完整的 Python 虚拟数字人系统，集成了 Live2D 模型渲染、语音识别、文本转语音、大语言模型对话和实时推流等功能，打造沉浸式的数字人交互体验。

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Live2D](https://img.shields.io/badge/Live2D-Hiyori-pink.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

## ✨ 核心特性

### 🎭 Live2D 渲染引擎
- **Hiyori 模型支持**: 完整的 Live2D Cubism SDK 集成
- **实时表情控制**: 基于情感标签的动态表情切换（18+ 种表情）
- **参数化动画**: 精确的参数控制和平滑过渡
- **呼吸和眼部闪烁**: 自然的生命感动画效果
- **VBridger 唇形同步**: 高精度的嘴型同步

### 🎤 智能语音处理
- **Whisper ASR**: 高精度多语言语音识别
- **实时音频处理**: PyAudio 驱动的音频输入输出
- **VAD 检测**: 智能语音活动检测
- **音频设备管理**: 自动设备检测和配置

### 🗣️ 自然语音合成
- **多引擎 TTS**: 支持多种 TTS 引擎
- **情感语音**: 根据情感状态调整语音表现
- **实时播放**: 低延迟音频播放系统

### 🤖 对话管理系统
- **LLM 集成**: 支持 OpenAI、Anthropic 等多种 API
- **情感识别**: 自动识别和解析对话中的情感标签
- **状态管理**: 完整的对话状态机实现
- **上下文维护**: 智能对话历史管理

### 📺 专业推流系统
- **OBS Studio 集成**: WebSocket 控制和 Spout 输出
- **虚拟摄像头**: 直接输出到系统虚拟摄像头
- **实时渲染**: 60fps 高帧率渲染输出
- **多平台支持**: Windows、macOS、Linux 兼容

### 🎨 Hiyori 模型专门优化
- **完整配置系统**: YAML 配置文件管理
- **表情映射**: 详细的情感表情预设
- **动作控制**: 智能动作选择和播放
- **性能优化**: 针对 Hiyori 模型的专门优化

## 🚀 快速开始

### 环境要求

- **Python 3.9+**
- **系统要求**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **硬件要求**: 
  - 4GB+ RAM
  - 独立显卡推荐（支持 OpenGL 3.3+）
  - 音频输入/输出设备
- **依赖软件**:
  - FFmpeg
  - OBS Studio（推流功能）

### 安装步骤

1. **克隆仓库**:
```bash
git clone https://github.com/your-repo/parrot-engine.git
cd parrot-engine
```

2. **创建虚拟环境**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows
```

3. **安装依赖**:
```bash
# 首先安装系统依赖 (macOS)
brew install portaudio

# 一次性安装所有Python依赖
pip install -r requirements.txt
```

> **注意**: 已修复所有依赖冲突问题。如果遇到问题，请查看 `INSTALL_STATUS.md` 了解详细信息。

4. **配置系统**:
```bash
cp config/config.example.yaml config/config.yaml
# 编辑配置文件，设置 API 密钥等参数
```

5. **配置 Hiyori 模型**:
```bash
# Hiyori 配置文件已预设，可根据需要调整
cp config/hiyori_config.yaml config/hiyori_config.yaml
```

6. **运行系统**:
```bash
python main.py
```

### 快速测试

运行集成测试验证系统功能：
```bash
python test_integration.py
```

运行性能优化分析：
```bash
python optimize_performance.py
```

## 📁 项目架构

```
parrot-engine/
├── src/
│   ├── core/                 # 核心引擎
│   │   └── avatar_engine.py  # 主引擎类
│   ├── modules/              # 功能模块
│   │   ├── asr/              # 语音识别
│   │   │   └── whisper_asr.py
│   │   ├── tts/              # 文本转语音
│   │   │   └── tts_engine.py
│   │   ├── llm/              # 大语言模型
│   │   │   └── llm_client.py
│   │   ├── live2d/           # Live2D 渲染
│   │   │   ├── live2d_manager.py
│   │   │   ├── hiyori_config.py
│   │   │   └── Models/Hiyori/  # Hiyori 模型文件
│   │   └── audio/            # 音频处理
│   │       └── audio_manager.py
│   ├── rendering/            # 渲染和推流
│   │   └── spout_streamer.py
│   ├── ui/                   # 用户界面
│   │   └── control_panel.py
│   └── utils/                # 工具函数
│       ├── config.py
│       └── event_bus.py
├── config/                   # 配置文件
│   ├── config.example.yaml
│   └── hiyori_config.yaml
├── docs/                     # 文档
│   └── architecture_analysis.md
├── test_integration.py       # 集成测试
├── optimize_performance.py   # 性能优化
└── main.py                  # 主入口
```

## ⚙️ 配置说明

### 主配置文件 (`config/config.yaml`)

```yaml
# LLM 设置
llm:
  provider: "openai"
  api_key: "your-api-key-here"
  model: "gpt-4"
  endpoint: "https://api.openai.com/v1"

# TTS 设置
tts:
  engine: "default"
  voice: "zh-CN"
  speed: 1.0
  volume: 0.8

# ASR 设置
asr:
  model: "base"
  language: "zh"
  vad_threshold: 0.5

# 音频设置
audio:
  sample_rate: 16000
  buffer_size: 1024
  input_device: null
  output_device: null

# Live2D 设置
live2d:
  model_path: "src/modules/live2d/Models/Hiyori"
  model_name: "Hiyori"
  width: 1080
  height: 1920

# 推流设置
streaming:
  enable_obs: true
  obs_host: "localhost"
  obs_port: 4444
  obs_password: ""
  target_fps: 60
```

### Hiyori 模型配置 (`config/hiyori_config.yaml`)

包含详细的表情映射、动作控制、参数范围等配置。支持：

- **18+ 种情感表情**: happy, excited, cool, smug, determined, embarrassed, shocked, thinking, suspicious, frustrated, sad, awkward, dismissive, adoring, laughing, passionate, sparkle, neutral
- **参数化控制**: 嘴部、眼部、头部、眉毛等精确参数控制
- **动画效果**: 眼部闪烁、呼吸效果、平滑过渡
- **性能优化**: FPS 控制、参数平滑、内存优化

## 🎮 使用说明

### 基本使用

1. **启动系统**: 运行 `python main.py`
2. **语音交互**: 对着麦克风说话，系统会自动识别并回应
3. **表情控制**: 系统会根据对话内容自动切换表情
4. **推流输出**: 在 OBS 中添加 Spout 源查看虚拟数字人

### 高级功能

#### 手动控制表情
```python
from src.core.avatar_engine import AvatarEngine

engine = AvatarEngine()
await engine.initialize()

# 设置表情
await engine.live2d_manager.set_expression("happy")
await engine.live2d_manager.set_expression("thinking")
```

#### 自定义配置
```python
from src.modules.live2d.hiyori_config import HiyoriConfig

config = HiyoriConfig()
config.load_config()

# 修改表情参数
config.update_expression("custom_happy", {
    "ParamMouthForm": 0.8,
    "ParamEyeLOpen": 1.0,
    "ParamEyeROpen": 1.0
})
config.save_config()
```

## 🔧 开发指南

### 添加新表情

1. 在 `config/hiyori_config.yaml` 中添加表情定义
2. 配置相应的参数值
3. 重新加载配置

### 集成新的 LLM

1. 在 `src/modules/llm/` 中创建新的客户端类
2. 实现统一的接口
3. 在配置文件中添加相应设置

### 自定义 Live2D 模型

1. 将模型文件放入 `src/modules/live2d/Models/`
2. 创建相应的配置文件
3. 更新模型路径设置

## 📊 性能优化

系统提供了完整的性能分析和优化工具：

```bash
# 运行性能分析
python optimize_performance.py
```

优化建议：
- **内存优化**: 定期垃圾回收，监控内存使用
- **渲染优化**: 根据需求调整 FPS 和分辨率
- **音频优化**: 合理设置缓冲区大小
- **网络优化**: 优化 LLM API 调用

## 🧪 测试

### 运行测试
```bash
# 集成测试
python test_integration.py

# 性能测试
python optimize_performance.py
```

### 测试覆盖
- ✅ 配置加载测试
- ✅ 引擎初始化测试
- ✅ Live2D 模块测试
- ✅ 音频模块测试
- ✅ 推流模块测试
- ✅ 完整工作流程测试

## 🤝 贡献指南

我们欢迎各种形式的贡献！

1. **Fork** 本仓库
2. **创建** 功能分支 (`git checkout -b feature/AmazingFeature`)
3. **提交** 更改 (`git commit -m 'Add some AmazingFeature'`)
4. **推送** 到分支 (`git push origin feature/AmazingFeature`)
5. **打开** Pull Request

### 代码规范
- 遵循 PEP 8 Python 代码规范
- 添加适当的注释和文档字符串
- 为新功能编写测试

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- **原版项目**: [handcrafted-persona-engine](https://github.com/fagenorn/handcrafted-persona-engine)
- **Live2D**: Live2D Cubism SDK
- **OpenAI**: Whisper ASR 和 GPT 模型
- **音频处理**: PyAudio, librosa
- **图形渲染**: OpenGL, PIL
- **Hiyori 模型**: Live2D 官方示例模型

## 📞 支持

如有问题或建议，请：
1. 查看 [文档](docs/)
2. 提交 [Issue](https://github.com/your-repo/parrot-engine/issues)
3. 加入讨论区

---

**让我们一起打造更好的虚拟数字人体验！** 🎭✨ 