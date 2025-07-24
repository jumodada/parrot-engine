"""
Virtual Avatar Engine - 虚拟数字人核心引擎

基于 HandCrafted Persona Engine 的 Python 实现，集成 Live2D、语音处理、对话管理和推流功能。
"""

import asyncio
import logging
import threading
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import time

from .conversation_manager import ConversationManager
from .config_manager import ConfigManager
from ..modules.live2d.live2d_manager import Live2DManager
from ..modules.asr.whisper_asr import WhisperASR
from ..modules.tts.tts_engine import TTSEngine
from ..modules.llm.llm_client import LLMClient
from ..modules.audio.audio_manager import AudioManager
from ..rendering.spout_streamer import SpoutStreamer
from ..ui.control_panel import ControlPanel


class EngineState(Enum):
    """引擎状态枚举"""
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class EngineConfig:
    """引擎配置"""
    # Live2D 配置
    live2d_model_path: str = "src/modules/live2d/Models/Hiyori"
    live2d_model_name: str = "Hiyori"
    
    # 音频配置
    sample_rate: int = 16000
    chunk_size: int = 1024
    audio_device_index: Optional[int] = None
    
    # ASR 配置
    whisper_model: str = "base"
    vad_threshold: float = 0.5
    
    # TTS 配置
    tts_voice: str = "default"
    tts_speed: float = 1.0
    
    # LLM 配置
    llm_model: str = "gpt-3.5-turbo"
    llm_api_key: str = ""
    llm_endpoint: str = "https://api.openai.com/v1"
    
    # 推流配置
    enable_obs_streaming: bool = True
    obs_host: str = "localhost"
    obs_port: int = 4444
    obs_password: str = ""
    
    # 渲染配置
    render_width: int = 1080
    render_height: int = 1920
    target_fps: int = 60


class AvatarEngine:
    """
    虚拟数字人引擎主类
    
    负责协调和管理所有子系统，包括：
    - Live2D 渲染
    - 语音识别和合成
    - 大语言模型对话
    - 推流输出
    - 用户界面
    """
    
    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        self.state = EngineState.STOPPED
        self.logger = logging.getLogger(__name__)
        
        # 核心组件
        self.config_manager: Optional[ConfigManager] = None
        self.conversation_manager: Optional[ConversationManager] = None
        self.live2d_manager: Optional[Live2DManager] = None
        self.asr: Optional[WhisperASR] = None
        self.tts: Optional[TTSEngine] = None
        self.llm: Optional[LLMClient] = None
        self.audio_manager: Optional[AudioManager] = None
        self.spout_streamer: Optional[SpoutStreamer] = None
        self.control_panel: Optional[ControlPanel] = None
        
        # 内部状态
        self._render_thread: Optional[threading.Thread] = None
        self._audio_thread: Optional[threading.Thread] = None
        self._conversation_task: Optional[asyncio.Task] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 事件回调
        self.on_state_changed: Optional[Callable[[EngineState], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_speech_detected: Optional[Callable[[str], None]] = None
        self.on_response_generated: Optional[Callable[[str], None]] = None
    
    async def initialize(self) -> bool:
        """
        初始化引擎和所有子系统
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            self._set_state(EngineState.INITIALIZING)
            self.logger.info("正在初始化虚拟数字人引擎...")
            
            # 初始化配置管理器
            self.config_manager = ConfigManager()
            await self.config_manager.load_config()
            
            # 初始化 Live2D 管理器
            self.logger.info("初始化 Live2D 管理器...")
            self.live2d_manager = Live2DManager(
                model_path=self.config.live2d_model_path,
                model_name=self.config.live2d_model_name,
                width=self.config.render_width,
                height=self.config.render_height
            )
            await self.live2d_manager.initialize()
            
            # 初始化音频管理器
            self.logger.info("初始化音频管理器...")
            self.audio_manager = AudioManager(
                sample_rate=self.config.sample_rate,
                chunk_size=self.config.chunk_size,
                device_index=self.config.audio_device_index
            )
            await self.audio_manager.initialize()
            
            # 初始化 ASR
            self.logger.info("初始化语音识别...")
            self.asr = WhisperASR(
                model_name=self.config.whisper_model,
                vad_threshold=self.config.vad_threshold
            )
            await self.asr.initialize()
            
            # 初始化 TTS
            self.logger.info("初始化语音合成...")
            self.tts = TTSEngine(
                voice=self.config.tts_voice,
                speed=self.config.tts_speed
            )
            await self.tts.initialize()
            
            # 初始化 LLM
            self.logger.info("初始化大语言模型...")
            self.llm = LLMClient(
                model=self.config.llm_model,
                api_key=self.config.llm_api_key,
                endpoint=self.config.llm_endpoint
            )
            await self.llm.initialize()
            
            # 初始化对话管理器
            self.logger.info("初始化对话管理器...")
            self.conversation_manager = ConversationManager(
                asr=self.asr,
                tts=self.tts,
                llm=self.llm,
                live2d_manager=self.live2d_manager
            )
            
            # 初始化推流器
            if self.config.enable_obs_streaming:
                self.logger.info("初始化 OBS 推流...")
                self.spout_streamer = SpoutStreamer(
                    host=self.config.obs_host,
                    port=self.config.obs_port,
                    password=self.config.obs_password
                )
                await self.spout_streamer.initialize()
            
            # 初始化控制面板
            self.logger.info("初始化控制面板...")
            self.control_panel = ControlPanel(engine=self)
            
            self.logger.info("引擎初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"引擎初始化失败: {e}")
            self._set_state(EngineState.ERROR)
            if self.on_error:
                self.on_error(e)
            return False
    
    async def start(self) -> bool:
        """
        启动引擎
        
        Returns:
            bool: 启动是否成功
        """
        try:
            if self.state != EngineState.INITIALIZING:
                self.logger.error("引擎必须先初始化才能启动")
                return False
            
            self.logger.info("启动虚拟数字人引擎...")
            self._running = True
            self._loop = asyncio.get_event_loop()
            
            # 启动渲染线程
            self._render_thread = threading.Thread(target=self._render_loop, daemon=True)
            self._render_thread.start()
            
            # 启动音频处理线程
            self._audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
            self._audio_thread.start()
            
            # 启动对话管理器
            self._conversation_task = asyncio.create_task(
                self.conversation_manager.start_conversation_loop()
            )
            
            # 启动推流
            if self.spout_streamer:
                await self.spout_streamer.start_streaming()
            
            # 启动控制面板
            if self.control_panel:
                await self.control_panel.start()
            
            self._set_state(EngineState.RUNNING)
            self.logger.info("引擎启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"引擎启动失败: {e}")
            self._set_state(EngineState.ERROR)
            if self.on_error:
                self.on_error(e)
            return False
    
    async def stop(self):
        """停止引擎"""
        try:
            self.logger.info("正在停止虚拟数字人引擎...")
            self._running = False
            
            # 停止对话管理器
            if self._conversation_task:
                self._conversation_task.cancel()
                try:
                    await self._conversation_task
                except asyncio.CancelledError:
                    pass
            
            # 停止推流
            if self.spout_streamer:
                await self.spout_streamer.stop_streaming()
            
            # 停止控制面板
            if self.control_panel:
                await self.control_panel.stop()
            
            # 等待线程结束
            if self._render_thread and self._render_thread.is_alive():
                self._render_thread.join(timeout=5.0)
            
            if self._audio_thread and self._audio_thread.is_alive():
                self._audio_thread.join(timeout=5.0)
            
            # 清理资源
            await self._cleanup()
            
            self._set_state(EngineState.STOPPED)
            self.logger.info("引擎已停止")
            
        except Exception as e:
            self.logger.error(f"停止引擎时出错: {e}")
            if self.on_error:
                self.on_error(e)
    
    def _render_loop(self):
        """渲染循环（在独立线程中运行）"""
        target_frame_time = 1.0 / self.config.target_fps
        
        while self._running:
            start_time = time.time()
            
            try:
                # 更新 Live2D 模型
                if self.live2d_manager:
                    delta_time = target_frame_time
                    self.live2d_manager.update(delta_time)
                    frame = self.live2d_manager.render()
                    
                    # 发送帧到推流器
                    if self.spout_streamer and frame is not None:
                        self.spout_streamer.send_frame(frame)
                
            except Exception as e:
                self.logger.error(f"渲染循环错误: {e}")
            
            # 控制帧率
            elapsed = time.time() - start_time
            if elapsed < target_frame_time:
                time.sleep(target_frame_time - elapsed)
    
    def _audio_loop(self):
        """音频处理循环（在独立线程中运行）"""
        while self._running:
            try:
                if self.audio_manager and self.conversation_manager:
                    # 获取音频数据
                    audio_data = self.audio_manager.get_audio_chunk()
                    if audio_data is not None:
                        # 异步处理音频
                        if self._loop:
                            asyncio.run_coroutine_threadsafe(
                                self.conversation_manager.process_audio(audio_data),
                                self._loop
                            )
                
            except Exception as e:
                self.logger.error(f"音频处理循环错误: {e}")
            
            time.sleep(0.01)  # 10ms 间隔
    
    async def _cleanup(self):
        """清理资源"""
        try:
            if self.live2d_manager:
                await self.live2d_manager.cleanup()
            
            if self.audio_manager:
                await self.audio_manager.cleanup()
            
            if self.asr:
                await self.asr.cleanup()
            
            if self.tts:
                await self.tts.cleanup()
            
            if self.llm:
                await self.llm.cleanup()
            
            if self.spout_streamer:
                await self.spout_streamer.cleanup()
                
        except Exception as e:
            self.logger.error(f"清理资源时出错: {e}")
    
    def _set_state(self, new_state: EngineState):
        """设置引擎状态"""
        if self.state != new_state:
            self.state = new_state
            self.logger.info(f"引擎状态变更: {new_state.value}")
            if self.on_state_changed:
                self.on_state_changed(new_state)
    
    # 公共接口方法
    async def send_message(self, message: str) -> str:
        """
        发送消息给虚拟人
        
        Args:
            message: 要发送的消息
            
        Returns:
            str: 虚拟人的回复
        """
        if self.conversation_manager:
            return await self.conversation_manager.process_text_input(message)
        return ""
    
    def set_emotion(self, emotion: str):
        """
        设置虚拟人情感
        
        Args:
            emotion: 情感标识符（如 "😊", "😢" 等）
        """
        if self.live2d_manager:
            self.live2d_manager.set_emotion(emotion)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取引擎状态信息
        
        Returns:
            Dict[str, Any]: 包含各子系统状态的字典
        """
        return {
            "engine_state": self.state.value,
            "live2d_initialized": self.live2d_manager is not None,
            "audio_initialized": self.audio_manager is not None,
            "asr_initialized": self.asr is not None,
            "tts_initialized": self.tts is not None,
            "llm_initialized": self.llm is not None,
            "streaming_enabled": self.spout_streamer is not None,
            "running": self._running
        }
    
    async def update_config(self, new_config: Dict[str, Any]):
        """
        更新配置
        
        Args:
            new_config: 新的配置参数
        """
        if self.config_manager:
            await self.config_manager.update_config(new_config)
            # 根据需要重新初始化相关组件
            # TODO: 实现热更新逻辑 