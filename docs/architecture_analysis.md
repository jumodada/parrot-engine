# HandCrafted Persona Engine - Python 实现架构分析

## 原项目架构概览

HandCrafted Persona Engine 是一个基于 C# 的虚拟数字人系统，主要组件包括：

### 1. Live2D 渲染系统
- **Live2DManager**: 核心管理器，负责模型加载和渲染
- **动画服务系统**:
  - `EmotionAnimationService`: 情感驱动的表情和动作
  - `VBridgerLipSyncService`: VBridger 标准唇形同步
  - `IdleBlinkingAnimationService`: 空闲动画和眼部闪烁
- **参数控制**: 支持实时参数调整和状态管理

### 2. 音频处理链
- **ASR**: Whisper.NET 语音识别，支持实时转录
- **TTS**: Kokoro ONNX 模型 + espeak-ng 回退
- **RVC**: 可选的实时语音克隆 (ONNX)
- **VAD**: Silero 语音活动检测
- **音频流**: PortAudio 输入输出管理

### 3. 对话管理
- **状态机**: 管理对话流程 (空闲→听取→思考→回应→播放)
- **LLM 集成**: OpenAI 兼容接口
- **情感解析**: 从文本中提取情感标签触发动画

### 4. 渲染输出
- **Spout 推流**: 直接推送到 OBS Studio
- **字幕系统**: 实时字幕渲染
- **OpenGL 渲染**: 高性能图形渲染

## Python 实现架构设计

### 核心模块结构

```
src/
├── core/
│   ├── __init__.py
│   ├── avatar_engine.py          # 主引擎类
│   ├── conversation_manager.py   # 对话状态管理
│   └── config_manager.py         # 配置管理
├── modules/
│   ├── live2d/
│   │   ├── __init__.py
│   │   ├── live2d_manager.py     # Live2D 核心管理
│   │   ├── animation_services.py  # 动画服务
│   │   ├── emotion_mapper.py     # 情感映射
│   │   └── vbridger_lipsync.py   # 唇形同步
│   ├── asr/
│   │   ├── __init__.py
│   │   ├── whisper_asr.py        # Whisper 语音识别
│   │   └── vad_detector.py       # 语音活动检测
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── tts_engine.py         # TTS 引擎
│   │   └── voice_cloning.py      # RVC 语音克隆
│   ├── llm/
│   │   ├── __init__.py
│   │   └── llm_client.py         # LLM 接口
│   └── audio/
│       ├── __init__.py
│       ├── audio_manager.py      # 音频管理
│       └── stream_processor.py   # 音频流处理
├── rendering/
│   ├── __init__.py
│   ├── spout_streamer.py         # OBS 推流
│   ├── subtitle_renderer.py      # 字幕渲染
│   └── opengl_renderer.py        # OpenGL 渲染
└── ui/
    ├── __init__.py
    ├── control_panel.py          # 控制面板
    └── config_editor.py          # 配置编辑器
```

### 技术栈选择

#### Live2D 集成
- **CubismSDK Python 绑定**: 使用 ctypes 或 pybind11 创建 Python 绑定
- **OpenGL 渲染**: PyOpenGL + GLFW/SDL2
- **模型加载**: 支持 .model3.json 格式

#### 音频处理
- **ASR**: transformers + openai-whisper
- **TTS**: ONNX Runtime + espeak-python
- **VAD**: silero-vad
- **音频 I/O**: pyaudio 或 sounddevice
- **RVC**: ONNX Runtime + custom pipeline

#### 推流和渲染
- **OBS 推流**: obs-websocket-py + virtual camera
- **视频编码**: OpenCV + FFmpeg Python 绑定
- **字幕渲染**: Cairo/Skia Python 绑定

#### 对话管理
- **LLM**: openai + custom providers
- **状态管理**: python-statemachine
- **并发处理**: asyncio

### 关键设计决策

#### 1. Live2D 集成策略
```python
# 使用 ctypes 包装 CubismSDK
class CubismModel:
    def __init__(self, model_path):
        self._lib = ctypes.CDLL("./CubismCore.so")
        self._model = self._load_model(model_path)
    
    def set_parameter(self, param_id: str, value: float):
        """设置模型参数"""
        
    def update(self, delta_time: float):
        """更新模型状态"""
        
    def render(self):
        """渲染模型"""
```

#### 2. 情感动画映射
```python
# 情感标签到动画的映射系统
EMOTION_MAPPING = {
    "😊": {"expression": "happy", "motion_group": "Happy"},
    "😤": {"expression": "frustrated", "motion_group": "Angry"},
    "🤔": {"expression": "thinking", "motion_group": "Thinking"},
    # ... 更多映射
}
```

#### 3. 音频处理管道
```python
# 异步音频处理链
async def audio_pipeline():
    async for audio_chunk in microphone_stream():
        if vad_detector.is_speech(audio_chunk):
            text = await whisper_asr.transcribe(audio_chunk)
            response = await llm_client.chat(text)
            audio = await tts_engine.synthesize(response)
            await audio_player.play(audio)
```

#### 4. OBS 推流集成
```python
# 使用 OpenCV 和 OBS WebSocket
class SpoutStreamer:
    def __init__(self):
        self.obs_client = obsws_python.ReqClient()
        
    def stream_frame(self, frame):
        # 将 OpenGL 帧缓冲转换为 OpenCV 格式
        # 推送到 OBS 虚拟摄像头
```

### Hiyori 模型集成

#### 模型配置
```yaml
# config/hiyori_config.yaml
live2d:
  model_path: "src/modules/live2d/Models/Hiyori"
  model_name: "Hiyori"
  
  # VBridger 参数映射
  vbridger_params:
    mouth_open_y: "ParamMouthOpenY"
    jaw_open: "ParamJawOpen"
    mouth_form: "ParamMouthForm"
    # ... 更多参数
    
  # 情感表情映射
  expressions:
    happy: "happy"
    sad: "sad"
    angry: "angry"
    # ... 更多表情
    
  # 动作组配置
  motion_groups:
    Idle: ["Hiyori_m01", "Hiyori_m02"]
    Happy: ["Hiyori_m03", "Hiyori_m04"]
    # ... 更多动作组
```

### 性能优化策略

1. **多线程处理**: 音频、渲染、AI 推理分离
2. **GPU 加速**: CUDA/OpenCL 用于 AI 模型推理
3. **内存池**: 减少音频数据分配开销
4. **帧率控制**: 60fps 渲染，合理的音频缓冲
5. **异步 I/O**: 网络请求和文件操作异步化

### 依赖关系

```
主要依赖:
- OpenGL/PyOpenGL (渲染)
- ONNX Runtime (AI 模型)
- OpenCV (图像处理)
- PyAudio/sounddevice (音频)
- asyncio (并发)
- transformers (Whisper)
- openai (LLM 接口)

Live2D 相关:
- ctypes (SDK 绑定)
- numpy (数值计算)
- Pillow (纹理加载)

推流相关:
- obs-websocket-py (OBS 集成)
- ffmpeg-python (视频编码)
```

### 开发里程碑

1. **阶段 1**: 基础框架 + Live2D 渲染
2. **阶段 2**: 音频处理链集成
3. **阶段 3**: 对话管理和情感动画
4. **阶段 4**: OBS 推流和字幕
5. **阶段 5**: Hiyori 模型优化和性能调优

这个架构设计保持了原项目的核心功能，同时充分利用了 Python 生态系统的优势，为快速开发和迭代提供了良好的基础。 