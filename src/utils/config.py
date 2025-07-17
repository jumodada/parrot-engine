"""
配置管理模块
负责加载和管理所有配置参数
"""

import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger


@dataclass
class WindowConfig:
    width: int = 1920
    height: int = 1080
    title: str = "Python Persona Engine"
    fullscreen: bool = False


@dataclass
class LLMConfig:
    text_provider: str = "openai"
    text_api_key: str = ""
    text_model: str = "gpt-4"
    text_endpoint: str = "https://api.openai.com/v1"
    vision_provider: str = "openai"
    vision_api_key: str = ""
    vision_model: str = "gpt-4-vision-preview"
    vision_endpoint: str = "https://api.openai.com/v1"


@dataclass
class ASRConfig:
    model: str = "base"
    language: str = "zh"
    vad_threshold: float = 0.5
    vad_threshold_gap: float = 0.15
    min_speech_duration: int = 150
    min_silence_duration: int = 450
    device: str = "auto"


@dataclass
class MicrophoneConfig:
    device_name: str = ""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024


@dataclass
class CoquiTTSConfig:
    model_path: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    speaker_wav: str = ""


@dataclass
class ElevenLabsConfig:
    api_key: str = ""
    voice_id: str = ""


@dataclass
class AzureTTSConfig:
    api_key: str = ""
    region: str = ""
    voice_name: str = ""


@dataclass
class TTSConfig:
    engine: str = "coqui"
    voice: str = "en_custom_2"
    speed: float = 1.0
    sample_rate: int = 24000
    coqui: CoquiTTSConfig = field(default_factory=CoquiTTSConfig)
    elevenlabs: ElevenLabsConfig = field(default_factory=ElevenLabsConfig)
    azure: AzureTTSConfig = field(default_factory=AzureTTSConfig)


@dataclass
class SubtitleConfig:
    font: str = "Arial"
    font_size: int = 32
    color: str = "#FFFFFF"
    highlight_color: str = "#FF6B6B"
    bottom_margin: int = 100
    side_margin: int = 30
    max_visible_lines: int = 2
    animation_duration: float = 0.3
    stroke_thickness: int = 2
    width: int = 1080
    height: int = 200


@dataclass
class Live2DAnimationConfig:
    idle_blink_interval: float = 3.0
    emotion_duration: float = 2.0
    lipsync_strength: float = 1.0


@dataclass
class Live2DConfig:
    enabled: bool = True
    model_path: str = "resources/live2d/aria"
    model_name: str = "aria"
    width: int = 1080
    height: int = 1920
    scale: float = 1.0
    animation: Live2DAnimationConfig = field(default_factory=Live2DAnimationConfig)


@dataclass
class VisionConfig:
    enabled: bool = False
    window_title: str = ""
    capture_interval: int = 60
    min_pixels: int = 50176
    max_pixels: int = 4194304


@dataclass
class ConversationConfig:
    barge_in_enabled: bool = True
    barge_in_min_words: int = 3
    max_history_turns: int = 10
    system_prompt_file: str = "config/personality.txt"
    current_context: str = "你是一个友善的AI助手角色。"
    topics: list = field(default_factory=lambda: ["日常对话", "技术讨论"])


@dataclass
class AudioConfig:
    output_device: str = ""
    volume: float = 0.8
    sample_rate: int = 24000
    buffer_size: int = 1024


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_file: str = "logs/persona_engine.log"
    max_file_size: str = "10MB"
    backup_count: int = 5


@dataclass
class PerformanceConfig:
    max_workers: int = 4
    gpu_memory_fraction: float = 0.8
    enable_mixed_precision: bool = True


@dataclass
class UIConfig:
    theme: str = "dark"
    transparency: float = 0.95
    always_on_top: bool = False
    show_metrics: bool = True


@dataclass
class PluginsConfig:
    enabled: list = field(default_factory=list)


@dataclass
class Config:
    """主配置类"""
    window: WindowConfig = field(default_factory=WindowConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    microphone: MicrophoneConfig = field(default_factory=MicrophoneConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    subtitle: SubtitleConfig = field(default_factory=SubtitleConfig)
    live2d: Live2DConfig = field(default_factory=Live2DConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    conversation: ConversationConfig = field(default_factory=ConversationConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    plugins: PluginsConfig = field(default_factory=PluginsConfig)

    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """从YAML文件加载配置"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            return cls()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
            
            if not config_dict:
                logger.warning("配置文件为空，使用默认配置")
                return cls()
                
            return cls.from_dict(config_dict)
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return cls()

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Config':
        """从字典创建配置对象"""
        config = cls()
        
        # 递归更新配置
        def update_config(obj, data_dict):
            for key, value in data_dict.items():
                if hasattr(obj, key):
                    attr = getattr(obj, key)
                    if isinstance(value, dict) and hasattr(attr, '__dict__'):
                        # 递归处理嵌套配置
                        update_config(attr, value)
                    else:
                        setattr(obj, key, value)
        
        try:
            update_config(config, config_dict)
        except Exception as e:
            logger.error(f"解析配置数据失败: {e}")
            
        return config

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        def to_dict_recursive(obj) -> Any:
            if hasattr(obj, '__dict__'):
                return {k: to_dict_recursive(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [to_dict_recursive(item) for item in obj]
            else:
                return obj
                
        result = to_dict_recursive(self)
        return result if isinstance(result, dict) else {}

    def save_to_file(self, config_path: str):
        """保存配置到文件"""
        try:
            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True, indent=2)
                
            logger.info(f"配置已保存到: {config_path}")
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")

    def validate(self) -> bool:
        """验证配置的有效性"""
        errors = []
        
        # 验证LLM配置
        if not self.llm.text_api_key or self.llm.text_api_key == "sk-your-api-key-here":
            errors.append("LLM API密钥未设置")
        
        # 验证ASR模型名称
        valid_asr_models = ["tiny", "base", "small", "medium", "large"]
        if self.asr.model not in valid_asr_models:
            errors.append(f"无效的ASR模型: {self.asr.model}")
        
        # 验证TTS引擎
        valid_tts_engines = ["coqui", "espeak", "azure", "elevenlabs"]
        if self.tts.engine not in valid_tts_engines:
            errors.append(f"无效的TTS引擎: {self.tts.engine}")
        
        # 验证采样率
        if self.microphone.sample_rate <= 0:
            errors.append("麦克风采样率必须大于0")
            
        if self.audio.sample_rate <= 0:
            errors.append("音频输出采样率必须大于0")
        
        # 验证Live2D配置
        if self.live2d.enabled:
            model_path = Path(self.live2d.model_path)
            if not model_path.exists():
                errors.append(f"Live2D模型路径不存在: {self.live2d.model_path}")
        
        if errors:
            for error in errors:
                logger.error(f"配置验证失败: {error}")
            return False
            
        logger.info("配置验证通过")
        return True 