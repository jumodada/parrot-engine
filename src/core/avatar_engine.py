"""
核心虚拟角色引擎
负责协调所有模块的运行和交互
"""

import asyncio
import threading
import time
from typing import Optional, Dict, Any, Callable
from loguru import logger
from enum import Enum

from ..utils.config import Config
from ..modules.asr.whisper_asr import WhisperASR
from ..modules.tts.tts_engine import TTSEngine
from ..modules.llm.llm_client import LLMClient
from ..modules.live2d.live2d_manager import Live2DManager
from ..modules.audio.audio_manager import AudioManager
from ..utils.event_bus import EventBus, Event


class EngineState(Enum):
    """引擎状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    LISTENING = "listening" 
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


class AvatarEngine:
    """虚拟角色引擎主类"""
    
    def __init__(self, config: Config):
        self.config = config
        self.state = EngineState.STOPPED
        self.event_bus = EventBus()
        
        # 核心模块
        self.asr: Optional[WhisperASR] = None
        self.tts: Optional[TTSEngine] = None
        self.llm: Optional[LLMClient] = None
        self.live2d: Optional[Live2DManager] = None
        self.audio: Optional[AudioManager] = None
        
        # 运行控制
        self._running = False
        self._main_loop_task: Optional[asyncio.Task] = None
        self._conversation_history = []
        
        # 性能监控
        self.metrics = {
            "asr_latency": 0.0,
            "llm_latency": 0.0,
            "tts_latency": 0.0,
            "total_latency": 0.0,
            "interactions_count": 0
        }
        
        # 回调函数
        self.on_state_changed: Optional[Callable[[EngineState], None]] = None
        self.on_text_recognized: Optional[Callable[[str], None]] = None
        self.on_response_generated: Optional[Callable[[str], None]] = None
        self.on_audio_playing: Optional[Callable[[bytes], None]] = None
        
        logger.info("虚拟角色引擎已初始化")

    async def initialize(self) -> bool:
        """初始化所有模块"""
        try:
            self._set_state(EngineState.STARTING)
            
            # 初始化事件监听
            self._setup_event_handlers()
            
            # 初始化音频管理器
            self.audio = AudioManager(self.config.audio)
            await self.audio.initialize()
            logger.info("音频管理器初始化完成")
            
            # 初始化ASR
            self.asr = WhisperASR(self.config.asr)
            await self.asr.initialize()
            logger.info("语音识别模块初始化完成")
            
            # 初始化TTS
            self.tts = TTSEngine(self.config.tts)
            await self.tts.initialize()
            logger.info("文本转语音模块初始化完成")
            
            # 初始化LLM
            self.llm = LLMClient(self.config.llm)
            await self.llm.initialize()
            logger.info("大语言模型模块初始化完成")
            
            # 初始化Live2D (可选)
            if self.config.live2d.enabled:
                self.live2d = Live2DManager(self.config.live2d)
                await self.live2d.initialize()
                logger.info("Live2D模块初始化完成")
            
            self._set_state(EngineState.LISTENING)
            logger.info("引擎初始化完成，所有模块已就绪")
            return True
            
        except Exception as e:
            logger.error(f"引擎初始化失败: {e}")
            self._set_state(EngineState.ERROR)
            return False

    async def start(self):
        """启动引擎"""
        if self._running:
            logger.warning("引擎已在运行中")
            return
            
        if self.state == EngineState.STOPPED:
            if not await self.initialize():
                return
                
        self._running = True
        self._main_loop_task = asyncio.create_task(self._main_loop())
        logger.info("引擎已启动")

    async def stop(self):
        """停止引擎"""
        self._running = False
        
        if self._main_loop_task:
            self._main_loop_task.cancel()
            try:
                await self._main_loop_task
            except asyncio.CancelledError:
                pass
                
        # 清理资源
        await self._cleanup()
        self._set_state(EngineState.STOPPED)
        logger.info("引擎已停止")

    async def _main_loop(self):
        """主事件循环"""
        logger.info("主事件循环开始")
        
        try:
            while self._running:
                if self.state == EngineState.LISTENING:
                    await self._listen_for_speech()
                elif self.state == EngineState.PROCESSING:
                    # 处理状态通常由事件驱动，这里只需等待
                    await asyncio.sleep(0.1)
                elif self.state == EngineState.SPEAKING:
                    # 同样由事件驱动
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            logger.info("主循环被取消")
        except Exception as e:
            logger.error(f"主循环出错: {e}")
            self._set_state(EngineState.ERROR)

    async def _listen_for_speech(self):
        """监听语音输入"""
        try:
            # 从麦克风获取音频数据
            audio_data = await self.audio.capture_audio()
            
            if audio_data and len(audio_data) > 0:
                # 检测是否有语音活动
                if await self.asr.detect_speech(audio_data):
                    self._set_state(EngineState.PROCESSING)
                    
                    # 异步处理语音识别
                    asyncio.create_task(self._process_speech(audio_data))
                    
        except Exception as e:
            logger.error(f"语音监听出错: {e}")

    async def _process_speech(self, audio_data: bytes):
        """处理语音输入的完整流程"""
        start_time = time.time()
        
        try:
            # 1. 语音识别
            asr_start = time.time()
            recognized_text = await self.asr.transcribe(audio_data)
            asr_time = time.time() - asr_start
            
            if not recognized_text or recognized_text.strip() == "":
                self._set_state(EngineState.LISTENING)
                return
                
            logger.info(f"识别到语音: {recognized_text}")
            self._trigger_callback(self.on_text_recognized, recognized_text)
            
            # 2. 大语言模型生成回应
            llm_start = time.time()
            response_text = await self._generate_response(recognized_text)
            llm_time = time.time() - llm_start
            
            if not response_text:
                self._set_state(EngineState.LISTENING)
                return
                
            logger.info(f"生成回应: {response_text}")
            self._trigger_callback(self.on_response_generated, response_text)
            
            # 3. 处理表情命令
            emotion = self._extract_emotion(response_text)
            clean_text = self._clean_response_text(response_text)
            
            if emotion and self.live2d:
                await self.live2d.set_emotion(emotion)
            
            # 4. 文本转语音
            self._set_state(EngineState.SPEAKING)
            tts_start = time.time()
            audio_data = await self.tts.synthesize(clean_text)
            tts_time = time.time() - tts_start
            
            # 5. 播放音频和同步动画
            if audio_data:
                # 触发播放回调
                self._trigger_callback(self.on_audio_playing, audio_data)
                
                # 播放音频
                await self.audio.play_audio(audio_data)
                
                # 同步口型动画
                if self.live2d:
                    phonemes = await self.tts.get_phonemes(clean_text)
                    await self.live2d.sync_lipsync(phonemes, len(audio_data))
            
            # 更新性能指标
            total_time = time.time() - start_time
            self._update_metrics(asr_time, llm_time, tts_time, total_time)
            
            # 返回监听状态
            self._set_state(EngineState.LISTENING)
            
        except Exception as e:
            logger.error(f"语音处理流程出错: {e}")
            self._set_state(EngineState.ERROR)

    async def _generate_response(self, user_input: str) -> str:
        """生成LLM回应"""
        try:
            # 构建对话历史
            messages = self._build_conversation_context(user_input)
            
            # 调用LLM
            response = await self.llm.chat_completion(messages)
            
            # 更新对话历史
            self._conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": time.time()
            })
            self._conversation_history.append({
                "role": "assistant", 
                "content": response,
                "timestamp": time.time()
            })
            
            # 限制历史长度
            max_turns = self.config.conversation.max_history_turns
            if len(self._conversation_history) > max_turns * 2:
                self._conversation_history = self._conversation_history[-(max_turns * 2):]
            
            return response
            
        except Exception as e:
            logger.error(f"LLM生成回应失败: {e}")
            return ""

    def _build_conversation_context(self, user_input: str) -> list:
        """构建对话上下文"""
        messages = []
        
        # 系统提示
        if self.config.conversation.system_prompt_file:
            try:
                with open(self.config.conversation.system_prompt_file, 'r', encoding='utf-8') as f:
                    system_prompt = f.read()
                messages.append({"role": "system", "content": system_prompt})
            except Exception as e:
                logger.warning(f"无法读取系统提示文件: {e}")
        
        # 添加对话历史
        messages.extend(self._conversation_history)
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})
        
        return messages

    def _extract_emotion(self, text: str) -> Optional[str]:
        """从回应文本中提取表情标签"""
        import re
        emotion_pattern = r'\[EMOTION:(\w+)\]'
        match = re.search(emotion_pattern, text)
        return match.group(1) if match else None

    def _clean_response_text(self, text: str) -> str:
        """清理回应文本，移除表情标签"""
        import re
        return re.sub(r'\[EMOTION:\w+\]', '', text).strip()

    def _setup_event_handlers(self):
        """设置事件处理器"""
        self.event_bus.subscribe("audio_chunk_received", self._on_audio_chunk)
        self.event_bus.subscribe("speech_detected", self._on_speech_detected)
        self.event_bus.subscribe("speech_ended", self._on_speech_ended)

    def _set_state(self, new_state: EngineState):
        """更新引擎状态"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            logger.info(f"引擎状态变更: {old_state.value} -> {new_state.value}")
            self._trigger_callback(self.on_state_changed, new_state)

    def _trigger_callback(self, callback: Optional[Callable], *args):
        """安全地触发回调函数"""
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(*args))
                else:
                    callback(*args)
            except Exception as e:
                logger.error(f"回调函数执行失败: {e}")

    def _update_metrics(self, asr_time: float, llm_time: float, tts_time: float, total_time: float):
        """更新性能指标"""
        self.metrics["asr_latency"] = asr_time
        self.metrics["llm_latency"] = llm_time  
        self.metrics["tts_latency"] = tts_time
        self.metrics["total_latency"] = total_time
        self.metrics["interactions_count"] += 1

    async def _on_audio_chunk(self, event: Event):
        """处理音频块事件"""
        pass

    async def _on_speech_detected(self, event: Event):
        """处理检测到语音事件"""
        logger.debug("检测到语音活动")

    async def _on_speech_ended(self, event: Event):
        """处理语音结束事件"""
        logger.debug("语音活动结束")

    async def _cleanup(self):
        """清理资源"""
        try:
            if self.audio:
                await self.audio.cleanup()
            if self.asr:
                await self.asr.cleanup()
            if self.tts:
                await self.tts.cleanup()
            if self.llm:
                await self.llm.cleanup()
            if self.live2d:
                await self.live2d.cleanup()
        except Exception as e:
            logger.error(f"资源清理失败: {e}")

    # 公共接口方法
    def get_state(self) -> EngineState:
        """获取当前状态"""
        return self.state

    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.metrics.copy()

    def get_conversation_history(self) -> list:
        """获取对话历史"""
        return self._conversation_history.copy()

    async def send_text_message(self, text: str) -> str:
        """发送文本消息 (不通过语音)"""
        if self.state not in [EngineState.LISTENING, EngineState.SPEAKING]:
            raise RuntimeError("引擎当前状态不允许处理消息")
            
        response = await self._generate_response(text)
        return response

    async def set_system_prompt(self, prompt: str):
        """动态设置系统提示"""
        # 可以实现动态修改角色设定的功能
        pass 