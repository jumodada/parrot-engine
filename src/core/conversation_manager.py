"""
对话管理器 - 协调语音识别、LLM 对话、语音合成和 Live2D 动画
"""

import asyncio
import logging
import re
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum


class ConversationState(Enum):
    """对话状态"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class ConversationTurn:
    """对话轮次"""
    user_input: str
    assistant_response: str
    timestamp: float
    asr_latency: float = 0.0
    llm_latency: float = 0.0
    tts_latency: float = 0.0
    total_latency: float = 0.0
    emotion_detected: Optional[str] = None


class ConversationManager:
    """
    对话管理器
    
    负责协调和管理整个对话流程：
    1. 语音监听和识别
    2. 情感分析和解析
    3. LLM 对话生成
    4. 语音合成
    5. Live2D 动画同步
    """
    
    def __init__(self, asr, tts, llm, live2d_manager):
        self.asr = asr
        self.tts = tts
        self.llm = llm
        self.live2d_manager = live2d_manager
        
        self.logger = logging.getLogger(__name__)
        self.state = ConversationState.IDLE
        
        # 对话历史
        self.conversation_history: List[ConversationTurn] = []
        self.max_history_turns = 10
        
        # 实时状态
        self._current_turn: Optional[ConversationTurn] = None
        self._listening_task: Optional[asyncio.Task] = None
        self._processing_task: Optional[asyncio.Task] = None
        self._speaking_task: Optional[asyncio.Task] = None
        
        # 配置
        self.voice_threshold = 0.5
        self.silence_timeout = 2.0  # 静音超时秒数
        self.max_speech_duration = 30.0  # 最大语音时长
        
        # 情感映射
        self.emotion_mapping = {
            "😊": {"expression": "happy", "motion_group": "Happy"},
            "🤩": {"expression": "excited_star", "motion_group": "Excited"},
            "😎": {"expression": "cool", "motion_group": "Confident"},
            "😏": {"expression": "smug", "motion_group": "Confident"},
            "💪": {"expression": "determined", "motion_group": "Confident"},
            "😳": {"expression": "embarrassed", "motion_group": "Nervous"},
            "😲": {"expression": "shocked", "motion_group": "Surprised"},
            "🤔": {"expression": "thinking", "motion_group": "Thinking"},
            "👀": {"expression": "suspicious", "motion_group": "Thinking"},
            "😤": {"expression": "frustrated", "motion_group": "Angry"},
            "😢": {"expression": "sad", "motion_group": "Sad"},
            "😅": {"expression": "awkward", "motion_group": "Nervous"},
            "🙄": {"expression": "dismissive", "motion_group": "Annoyed"},
            "💕": {"expression": "adoring", "motion_group": "Happy"},
            "😂": {"expression": "laughing", "motion_group": "Happy"},
            "🔥": {"expression": "passionate", "motion_group": "Excited"},
            "✨": {"expression": "sparkle", "motion_group": "Happy"},
        }
        
        # 事件回调
        self.on_state_changed: Optional[Callable[[ConversationState], None]] = None
        self.on_user_speech: Optional[Callable[[str], None]] = None
        self.on_assistant_response: Optional[Callable[[str], None]] = None
        self.on_emotion_detected: Optional[Callable[[str], None]] = None
        self.on_turn_completed: Optional[Callable[[ConversationTurn], None]] = None
    
    async def start_conversation_loop(self):
        """启动对话循环"""
        self.logger.info("启动对话管理器")
        self._set_state(ConversationState.IDLE)
        
        while True:
            try:
                if self.state == ConversationState.IDLE:
                    # 开始监听
                    self._set_state(ConversationState.LISTENING)
                    self._listening_task = asyncio.create_task(self._listen_for_speech())
                    await self._listening_task
                
                elif self.state == ConversationState.PROCESSING:
                    # 处理语音输入
                    if self._current_turn:
                        self._processing_task = asyncio.create_task(
                            self._process_conversation_turn(self._current_turn)
                        )
                        await self._processing_task
                
                elif self.state == ConversationState.SPEAKING:
                    # 等待语音播放完成
                    await asyncio.sleep(0.1)
                
                else:
                    await asyncio.sleep(0.1)
                    
            except asyncio.CancelledError:
                self.logger.info("对话循环被取消")
                break
            except Exception as e:
                self.logger.error(f"对话循环出错: {e}")
                self._set_state(ConversationState.ERROR)
                await asyncio.sleep(1.0)  # 错误恢复等待
                self._set_state(ConversationState.IDLE)
    
    async def _listen_for_speech(self):
        """监听语音输入"""
        self.logger.debug("开始监听语音...")
        
        # 设置空闲动画
        if self.live2d_manager:
            await self.live2d_manager.set_idle_animation()
        
        speech_detected = False
        speech_buffer = []
        silence_start = None
        speech_start = None
        
        try:
            while self.state == ConversationState.LISTENING:
                # 这里应该从音频管理器获取实时音频块
                # 暂时使用模拟的等待
                await asyncio.sleep(0.1)
                
                # TODO: 实际的音频处理逻辑
                # audio_chunk = await self.audio_manager.get_audio_chunk()
                # has_speech = await self.asr.detect_voice_activity(audio_chunk)
                
                # 模拟语音活动检测
                has_speech = False  # 这里需要实际的 VAD 检测
                
                if has_speech:
                    if not speech_detected:
                        # 开始说话
                        speech_detected = True
                        speech_start = time.time()
                        self.logger.debug("检测到语音活动")
                    
                    silence_start = None
                    # speech_buffer.append(audio_chunk)
                    
                    # 检查最大语音时长
                    if speech_start and (time.time() - speech_start) > self.max_speech_duration:
                        self.logger.warning("语音输入超时，强制结束")
                        break
                
                elif speech_detected:
                    # 说话中的静音
                    if silence_start is None:
                        silence_start = time.time()
                    elif (time.time() - silence_start) > self.silence_timeout:
                        # 静音超时，结束语音输入
                        self.logger.debug("检测到语音结束")
                        break
            
            # 处理收集到的语音数据
            if speech_detected and speech_buffer:
                await self._handle_speech_input(speech_buffer)
            
        except asyncio.CancelledError:
            self.logger.debug("语音监听被取消")
        except Exception as e:
            self.logger.error(f"语音监听出错: {e}")
            self._set_state(ConversationState.ERROR)
    
    async def _handle_speech_input(self, speech_buffer):
        """处理语音输入"""
        try:
            # 合并音频块
            combined_audio = b''.join(speech_buffer)
            
            # 启动新的对话轮次
            turn_start = time.time()
            
            # 语音识别
            asr_start = time.time()
            recognized_text = await self.asr.transcribe(combined_audio)
            asr_time = time.time() - asr_start
            
            if not recognized_text or recognized_text.strip() == "":
                self.logger.debug("未识别到有效文本")
                self._set_state(ConversationState.IDLE)
                return
            
            self.logger.info(f"识别到语音: {recognized_text}")
            
            # 创建对话轮次
            self._current_turn = ConversationTurn(
                user_input=recognized_text,
                assistant_response="",
                timestamp=turn_start,
                asr_latency=asr_time
            )
            
            # 触发回调
            if self.on_user_speech:
                self.on_user_speech(recognized_text)
            
            # 切换到处理状态
            self._set_state(ConversationState.PROCESSING)
            
        except Exception as e:
            self.logger.error(f"处理语音输入失败: {e}")
            self._set_state(ConversationState.ERROR)
    
    async def _process_conversation_turn(self, turn: ConversationTurn):
        """处理完整的对话轮次"""
        try:
            self.logger.info(f"处理用户输入: {turn.user_input}")
            
            # LLM 生成回应
            llm_start = time.time()
            response_text = await self._generate_llm_response(turn.user_input)
            turn.llm_latency = time.time() - llm_start
            
            if not response_text:
                self.logger.warning("LLM 未生成有效回应")
                self._set_state(ConversationState.IDLE)
                return
            
            # 解析情感标签
            emotion, clean_text = self._parse_emotion_tags(response_text)
            turn.assistant_response = clean_text
            turn.emotion_detected = emotion
            
            self.logger.info(f"生成回应: {clean_text}")
            if emotion:
                self.logger.info(f"检测到情感: {emotion}")
            
            # 触发回调
            if self.on_assistant_response:
                self.on_assistant_response(clean_text)
            if emotion and self.on_emotion_detected:
                self.on_emotion_detected(emotion)
            
            # 设置情感动画
            if emotion and self.live2d_manager:
                await self._set_emotion_animation(emotion)
            
            # 语音合成
            self._set_state(ConversationState.RESPONDING)
            tts_start = time.time()
            audio_data = await self.tts.synthesize(clean_text)
            turn.tts_latency = time.time() - tts_start
            
            if audio_data:
                # 播放语音并同步动画
                self._set_state(ConversationState.SPEAKING)
                await self._play_speech_with_animation(audio_data, clean_text)
            
            # 计算总延迟
            turn.total_latency = time.time() - turn.timestamp
            
            # 添加到历史记录
            self.conversation_history.append(turn)
            if len(self.conversation_history) > self.max_history_turns:
                self.conversation_history = self.conversation_history[-self.max_history_turns:]
            
            # 触发回调
            if self.on_turn_completed:
                self.on_turn_completed(turn)
            
            self.logger.info(f"对话轮次完成，总延迟: {turn.total_latency:.2f}s")
            
            # 返回空闲状态
            self._current_turn = None
            self._set_state(ConversationState.IDLE)
            
        except Exception as e:
            self.logger.error(f"处理对话轮次失败: {e}")
            self._set_state(ConversationState.ERROR)
    
    async def _generate_llm_response(self, user_input: str) -> str:
        """生成 LLM 回应"""
        try:
            # 构建对话上下文
            messages = self._build_conversation_context(user_input)
            
            # 调用 LLM
            response = await self.llm.chat_completion(messages)
            return response
            
        except Exception as e:
            self.logger.error(f"LLM 生成回应失败: {e}")
            return ""
    
    def _build_conversation_context(self, user_input: str) -> List[Dict[str, str]]:
        """构建对话上下文"""
        messages = []
        
        # 系统提示 - Hiyori 角色设定
        system_prompt = """你是 Hiyori，一个活泼可爱的虚拟数字人。你具有以下特点：

1. 性格：开朗、友善、充满活力，偶尔会有点调皮
2. 说话风格：亲切自然，喜欢使用表情符号表达情感
3. 情感表达：通过 [EMOTION:emoji] 标签来表达情感，比如：
   - 开心时使用 [EMOTION:😊]
   - 思考时使用 [EMOTION:🤔]
   - 兴奋时使用 [EMOTION:🤩]
   - 难过时使用 [EMOTION:😢]

请根据对话内容适当使用情感标签，让交流更加生动有趣。"""
        
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加历史对话
        for turn in self.conversation_history[-5:]:  # 只保留最近5轮对话
            messages.append({"role": "user", "content": turn.user_input})
            messages.append({"role": "assistant", "content": turn.assistant_response})
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _parse_emotion_tags(self, text: str) -> tuple[Optional[str], str]:
        """解析情感标签"""
        # 查找情感标签
        emotion_pattern = r'\[EMOTION:([^\]]+)\]'
        matches = re.findall(emotion_pattern, text)
        
        # 清理文本
        clean_text = re.sub(emotion_pattern, '', text).strip()
        
        # 返回最后一个情感标签（如果有多个）
        emotion = matches[-1] if matches else None
        
        return emotion, clean_text
    
    async def _set_emotion_animation(self, emotion: str):
        """设置情感动画"""
        try:
            if emotion in self.emotion_mapping:
                mapping = self.emotion_mapping[emotion]
                
                # 设置表情
                if mapping.get("expression"):
                    await self.live2d_manager.set_expression(mapping["expression"])
                
                # 播放动作
                if mapping.get("motion_group"):
                    await self.live2d_manager.play_motion(mapping["motion_group"])
                    
                self.logger.debug(f"应用情感动画: {emotion}")
            else:
                self.logger.warning(f"未知的情感标签: {emotion}")
                
        except Exception as e:
            self.logger.error(f"设置情感动画失败: {e}")
    
    async def _play_speech_with_animation(self, audio_data: bytes, text: str):
        """播放语音并同步动画"""
        try:
            # 获取音素时序信息用于唇形同步
            phoneme_timing = await self.tts.get_phoneme_timing(text)
            
            # 启动唇形同步任务
            lipsync_task = None
            if self.live2d_manager and phoneme_timing:
                lipsync_task = asyncio.create_task(
                    self.live2d_manager.sync_lipsync(phoneme_timing)
                )
            
            # 播放音频
            await self.tts.play_audio(audio_data)
            
            # 等待唇形同步完成
            if lipsync_task:
                await lipsync_task
                
        except Exception as e:
            self.logger.error(f"播放语音和动画失败: {e}")
    
    async def process_audio(self, audio_data: bytes):
        """处理音频数据（从外部调用）"""
        if self.state == ConversationState.LISTENING:
            # 这里可以累积音频数据进行 VAD 检测
            # 如果检测到语音，则切换状态
            pass
    
    async def process_text_input(self, text: str) -> str:
        """处理文本输入（用于调试或文本聊天）"""
        try:
            # 创建临时对话轮次
            turn = ConversationTurn(
                user_input=text,
                assistant_response="",
                timestamp=time.time()
            )
            
            # 生成回应
            response = await self._generate_llm_response(text)
            emotion, clean_response = self._parse_emotion_tags(response)
            
            turn.assistant_response = clean_response
            turn.emotion_detected = emotion
            
            # 设置情感动画
            if emotion and self.live2d_manager:
                await self._set_emotion_animation(emotion)
            
            # 添加到历史
            self.conversation_history.append(turn)
            if len(self.conversation_history) > self.max_history_turns:
                self.conversation_history = self.conversation_history[-self.max_history_turns:]
            
            return clean_response
            
        except Exception as e:
            self.logger.error(f"处理文本输入失败: {e}")
            return "抱歉，我暂时无法回应。"
    
    def _set_state(self, new_state: ConversationState):
        """设置对话状态"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self.logger.debug(f"对话状态变更: {old_state.value} -> {new_state.value}")
            
            if self.on_state_changed:
                self.on_state_changed(new_state)
    
    # 公共接口
    def get_conversation_history(self) -> List[ConversationTurn]:
        """获取对话历史"""
        return self.conversation_history.copy()
    
    def get_current_state(self) -> ConversationState:
        """获取当前状态"""
        return self.state
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        self.logger.info("对话历史已清空")
    
    async def interrupt_current_turn(self):
        """中断当前对话轮次"""
        try:
            # 取消当前任务
            if self._listening_task and not self._listening_task.done():
                self._listening_task.cancel()
            
            if self._processing_task and not self._processing_task.done():
                self._processing_task.cancel()
            
            if self._speaking_task and not self._speaking_task.done():
                self._speaking_task.cancel()
            
            # 停止音频播放
            if self.tts:
                await self.tts.stop_playback()
            
            # 重置状态
            self._current_turn = None
            self._set_state(ConversationState.IDLE)
            
            self.logger.info("当前对话轮次已中断")
            
        except Exception as e:
            self.logger.error(f"中断对话轮次失败: {e}") 