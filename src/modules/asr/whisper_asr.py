"""
基于OpenAI Whisper的语音识别模块
"""

import asyncio
import numpy as np
import torch
import whisper
from typing import Optional, Union, List
from loguru import logger
import threading
import time

from ...utils.config import ASRConfig


class WhisperASR:
    """Whisper语音识别引擎"""
    
    def __init__(self, config: ASRConfig):
        self.config = config
        self.model: Optional[whisper.Whisper] = None
        self.device = self._get_device()
        self._initialized = False
        self._lock = threading.Lock()
        
        # VAD相关
        self._vad_threshold = config.vad_threshold
        self._vad_threshold_gap = config.vad_threshold_gap
        self._min_speech_duration = config.min_speech_duration
        self._min_silence_duration = config.min_silence_duration
        
        logger.info(f"Whisper ASR初始化，模型: {config.model}, 设备: {self.device}")

    def _get_device(self) -> str:
        """获取计算设备"""
        if self.config.device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            else:
                return "cpu"
        return self.config.device

    async def initialize(self):
        """初始化Whisper模型"""
        if self._initialized:
            return
            
        try:
            # 在线程池中加载模型以避免阻塞
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, 
                self._load_model
            )
            
            self._initialized = True
            logger.info(f"Whisper模型加载完成: {self.config.model}")
            
        except Exception as e:
            logger.error(f"Whisper模型加载失败: {e}")
            raise

    def _load_model(self) -> whisper.Whisper:
        """在后台线程中加载模型"""
        return whisper.load_model(
            self.config.model,
            device=self.device
        )

    async def detect_speech(self, audio_data: Union[bytes, np.ndarray]) -> bool:
        """
        检测音频中是否包含语音
        这是一个简化的VAD实现，实际使用中可以集成专门的VAD模型
        """
        try:
            # 转换音频数据
            audio_array = self._prepare_audio(audio_data)
            
            if audio_array is None or len(audio_array) == 0:
                return False
            
            # 计算音频能量
            energy = np.sqrt(np.mean(audio_array ** 2))
            
            # 简单的能量阈值检测
            has_speech = energy > self._vad_threshold
            
            logger.debug(f"音频能量: {energy:.4f}, 阈值: {self._vad_threshold}, 检测到语音: {has_speech}")
            
            return has_speech
            
        except Exception as e:
            logger.error(f"语音检测失败: {e}")
            return False

    async def transcribe(self, audio_data: Union[bytes, np.ndarray]) -> str:
        """
        转录音频为文本
        """
        if not self._initialized or self.model is None:
            logger.error("Whisper模型未初始化")
            return ""
            
        try:
            # 准备音频数据
            audio_array = self._prepare_audio(audio_data)
            
            if audio_array is None or len(audio_array) == 0:
                return ""
            
            # 在线程池中执行转录以避免阻塞
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._transcribe_sync,
                audio_array
            )
            
            text = result.get("text", "").strip()
            logger.info(f"转录结果: {text}")
            
            return text
            
        except Exception as e:
            logger.error(f"语音转录失败: {e}")
            return ""

    def _transcribe_sync(self, audio_array: np.ndarray) -> dict:
        """同步转录方法"""
        with self._lock:
            # 设置转录选项
            options = {
                "language": self.config.language if self.config.language != "auto" else None,
                "task": "transcribe",
                "fp16": self.device == "cuda",
                "no_speech_threshold": 0.6,
                "logprob_threshold": -1.0,
                "compression_ratio_threshold": 2.4,
                "condition_on_previous_text": False
            }
            
            # 执行转录
            result = self.model.transcribe(audio_array, **options)
            return result

    def _prepare_audio(self, audio_data: Union[bytes, np.ndarray]) -> Optional[np.ndarray]:
        """准备音频数据供Whisper处理"""
        try:
            if isinstance(audio_data, bytes):
                # 假设是16位PCM数据
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                # 归一化到[-1, 1]范围
                audio_array = audio_array.astype(np.float32) / 32768.0
            elif isinstance(audio_data, np.ndarray):
                audio_array = audio_data.astype(np.float32)
                # 如果是整数类型，进行归一化
                if audio_array.dtype == np.int16:
                    audio_array = audio_array / 32768.0
                elif audio_array.dtype == np.int32:
                    audio_array = audio_array / 2147483648.0
            else:
                logger.error(f"不支持的音频数据类型: {type(audio_data)}")
                return None
            
            # 确保音频长度足够
            min_length = int(0.1 * 16000)  # 至少100ms的音频
            if len(audio_array) < min_length:
                logger.debug("音频太短，跳过处理")
                return None
            
            # Whisper期望16kHz的采样率
            if hasattr(self, '_resample_if_needed'):
                audio_array = self._resample_if_needed(audio_array)
            
            return audio_array
            
        except Exception as e:
            logger.error(f"音频数据准备失败: {e}")
            return None

    def _resample_if_needed(self, audio_array: np.ndarray, 
                           original_sr: int = 16000, 
                           target_sr: int = 16000) -> np.ndarray:
        """如果需要，重新采样音频到目标采样率"""
        if original_sr == target_sr:
            return audio_array
            
        try:
            import librosa
            resampled = librosa.resample(
                audio_array, 
                orig_sr=original_sr, 
                target_sr=target_sr
            )
            return resampled
        except ImportError:
            logger.warning("librosa未安装，无法重采样音频")
            return audio_array
        except Exception as e:
            logger.error(f"音频重采样失败: {e}")
            return audio_array

    async def transcribe_batch(self, audio_chunks: List[Union[bytes, np.ndarray]]) -> List[str]:
        """批量转录多个音频块"""
        if not self._initialized or self.model is None:
            logger.error("Whisper模型未初始化")
            return [""] * len(audio_chunks)
        
        try:
            tasks = []
            for chunk in audio_chunks:
                task = self.transcribe(chunk)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果，将异常转换为空字符串
            transcriptions = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"批量转录中的错误: {result}")
                    transcriptions.append("")
                else:
                    transcriptions.append(result)
            
            return transcriptions
            
        except Exception as e:
            logger.error(f"批量转录失败: {e}")
            return [""] * len(audio_chunks)

    def get_model_info(self) -> dict:
        """获取模型信息"""
        if not self._initialized or self.model is None:
            return {"status": "not_initialized"}
            
        return {
            "status": "initialized",
            "model_name": self.config.model,
            "device": self.device,
            "language": self.config.language,
            "parameters": {
                "vad_threshold": self._vad_threshold,
                "min_speech_duration": self._min_speech_duration,
                "min_silence_duration": self._min_silence_duration
            }
        }

    async def cleanup(self):
        """清理资源"""
        try:
            if self.model is not None:
                # Whisper模型的清理
                del self.model
                self.model = None
                
            # 清理GPU缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            self._initialized = False
            logger.info("Whisper ASR资源已清理")
            
        except Exception as e:
            logger.error(f"Whisper ASR清理失败: {e}")

    # 配置动态更新方法
    def update_vad_threshold(self, threshold: float):
        """更新VAD阈值"""
        self._vad_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"VAD阈值更新为: {self._vad_threshold}")

    def update_language(self, language: str):
        """更新识别语言"""
        self.config.language = language
        logger.info(f"识别语言更新为: {language}")

    async def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return [
            "auto", "zh", "en", "ja", "ko", "es", "fr", "de", "it", "pt", "ru",
            "ar", "hi", "th", "vi", "id", "ms", "tl", "tr", "pl", "nl", "sv"
        ]

    async def estimate_processing_time(self, audio_duration: float) -> float:
        """估算处理时间"""
        # 基于经验的处理时间估算
        if self.device == "cuda":
            # GPU通常比实时快5-10倍
            return audio_duration / 7.0
        else:
            # CPU通常接近实时或稍慢
            return audio_duration * 1.2 