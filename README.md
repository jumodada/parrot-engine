# Parrot Engine

一个基于 Python 的智能对话引擎，集成了语音识别、大语言模型、语音合成和 Live2D 虚拟形象功能。

## 🚀 快速开始

### 环境要求
- **Python 3.11+**
- **OpenGL 支持** (用于 Live2D 渲染)
- **系统要求**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd parrot-engine
```

2. **创建虚拟环境**
```bash
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置设置**
```bash
cp config/config.example.yaml config/config.yaml
# 编辑 config.yaml 添加你的 API 密钥
```

5. **运行测试**
```bash
python test_integration.py
```

### 启动选项

- **完整系统**: `python main.py` (推荐，需要配置 API)
- **简单演示**: `python run_example.py` (无需 API 配置)
- **功能测试**: `python test_integration.py`

## ✨ 功能特性

### 🎭 Live2D 渲染引擎
- **Hiyori 模型支持**: 完整的 Live2D Cubism SDK 集成
- **实时表情控制**: 基于情感标签的动态表情切换（18+ 种表情）
- **参数化动画**: 精确的参数控制和平滑过渡
- **VBridger 唇形同步**: 高精度的嘴型同步

### 🎤 智能语音处理
- **Whisper ASR**: 高精度多语言语音识别
- **实时音频处理**: PyAudio 驱动的音频输入输出
- **VAD 检测**: 智能语音活动检测

### 🗣️ 自然语音合成
- **多引擎 TTS**: 支持多种 TTS 引擎
- **情感语音**: 根据情感状态调整语音表现
- **实时播放**: 低延迟音频播放系统

### 🤖 对话管理系统
- **LLM 集成**: 支持 OpenAI、Anthropic 等多种 API
- **情感识别**: 自动识别和解析对话中的情感标签
- **状态管理**: 完整的对话状态机实现

### 📺 专业推流系统
- **OBS Studio 集成**: WebSocket 控制和 Spout 输出
- **虚拟摄像头**: 直接输出到系统虚拟摄像头
- **实时渲染**: 60fps 高帧率渲染输出

## 📁 项目架构

```
parrot-engine/
├── main.py                 # 主程序入口
├── run_example.py          # 简单演示程序
├── test_integration.py     # 集成测试
├── requirements.txt        # 依赖文件
├── config/                 # 配置文件
│   ├── config.example.yaml
│   ├── hiyori_config.yaml
│   └── personality.txt
├── src/                    # 源代码
│   ├── core/               # 核心引擎
│   ├── modules/            # 功能模块
│   │   ├── asr/            # 语音识别
│   │   ├── tts/            # 文本转语音
│   │   ├── llm/            # 大语言模型
│   │   ├── live2d/         # Live2D 渲染
│   │   └── audio/          # 音频处理
│   ├── rendering/          # 渲染和推流
│   ├── ui/                 # 用户界面
│   └── utils/              # 工具函数
└── docs/                   # 技术文档
```

## ⚙️ 配置说明

### 主配置文件 (`config/config.yaml`)

```yaml
# LLM 设置
llm:
  provider: "openai"
  api_key: "your-api-key-here"  # 必须配置
  model: "gpt-4"
  endpoint: "https://api.openai.com/v1"

# TTS 设置
tts:
  provider: "openai"
  voice: "alloy"

# ASR 设置
asr:
  provider: "whisper"
  model: "base"

# Live2D 设置
live2d:
  model_path: "src/modules/live2d/Models/Hiyori"
  model_name: "Hiyori"
```

### Hiyori 模型配置 (`config/hiyori_config.yaml`)

Live2D 模型的详细配置，包括表情映射、动作设置等。

## 🔧 开发指南

### 虚拟环境管理
- 使用标准的 `venv` 目录名
- 虚拟环境目录已在 `.gitignore` 中忽略
- 不要提交虚拟环境到 git

### 依赖管理
- 新增依赖时，更新 `requirements.txt`
- 使用 `pip freeze > requirements.txt` 更新版本

### Live2D 功能测试
```bash
# 安全测试 (不需要 OpenGL)
python test_hiyori_safe.py

# 完整测试 (需要 OpenGL 上下文)
python test_hiyori_complete.py
```

## 🆘 故障排除

### 常见问题

1. **导入错误**
   - 确保在项目根目录
   - 确保虚拟环境已激活

2. **API 调用失败**
   - 检查 `config.yaml` 中的 API 密钥
   - 确保网络连接正常
   - 验证 API 额度

3. **Live2D 段错误**
   - 确保在支持 OpenGL 的环境中运行
   - 检查 live2d-py 版本兼容性

4. **音频功能异常**
   ```bash
   # macOS 安装 portaudio
   brew install portaudio
   ```

### 系统要求
- **硬件**: 4GB+ RAM, 独立显卡推荐（OpenGL 3.3+）
- **软件**: FFmpeg, OBS Studio（推流功能）

## 📚 技术文档

详细的技术文档请参考 `docs/` 目录：
- [架构分析](docs/architecture_analysis.md)

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

### 代码规范
- 使用 Python 3.11+ 语法
- 遵循 PEP 8 代码风格
- 添加适当的类型注解
- 编写单元测试

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

🎉 **开始探索 Parrot Engine 的强大功能吧！**