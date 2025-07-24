"""
Whisper ASR 模块 - 基于 Whisper 的语音识别和语音活动检测
"""

import asyncio
import logging
import numpy as np
import torch
import threading
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import io

try:
    import whisper
    import transformers
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    import silero_vad
    import librosa
    import soundfile as sf
except ImportError:
    logging.warning("语音识别相关库未安装，ASR 功能将受限")


@dataclass 
class TranscriptionResult:
    """转录结果"""
    text: str
    confidence: float
    segments: List[Dict[str, Any]]
    language: str
    processing_time: float


@dataclass
class VADResult:
    """语音活动检测结果"""
    is_speech: bool
    confidence: float
    start_time: float
    end_time: float


class WhisperASR:
    """
    Whisper ASR 语音识别器
    
    功能：
    1. 基于 Whisper 的语音识别
    2. Silero VAD 语音活动检测
    3. 支持实时和批量处理
    4. 多语言支持
    5. 中断检测（用于对话管理）
    """
    
    def __init__(self, model_name: str = "base", vad_threshold: float = 0.5, device: str = "auto"):
        self.model_name = model_name
        self.vad_threshold = vad_threshold
        self.device = self._get_device(device)
        
        self.logger = logging.getLogger(__name__)
        
        # 模型相关
        self.whisper_model: Optional[Any] = None
        self.vad_model: Optional[Any] = None
        self.processor: Optional[Any] = None
        self.asr_pipeline: Optional[Any] = None
        
        # VAD 相关
        self.vad_sample_rate = 16000
        self.vad_window_size = 512  # 32ms at 16kHz
        self.vad_hop_length = 256   # 16ms at 16kHz
        
        # 缓冲区
        self.audio_buffer: List[np.ndarray] = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_duration = 30.0  # 最大缓冲30秒
        
        # 实时处理
        self.is_processing = False
        self.processing_task: Optional[asyncio.Task] = None
        
        # 配置
        self.config = {
            "sample_rate": 16000,
            "language": "auto",  # 自动检测语言
            "return_timestamps": True,
            "return_language": True,
            "beam_size": 1,  # 快速模式
            "patience": 1.0,
            "temperature": 0.0,
            "compression_ratio_threshold": 2.4,
            "logprob_threshold": -1.0,
            "no_speech_threshold": 0.6,
            "condition_on_previous_text": False
        }
        
        # 语言映射
        self.language_mapping = {
            "zh": "chinese",
            "en": "english", 
            "ja": "japanese",
            "ko": "korean",
            "auto": "auto"
        }
        
        # 统计信息
        self.stats = {
            "total_transcriptions": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "vad_detections": 0,
            "false_positives": 0
        }
        
        # 回调函数
        self.on_speech_detected: Optional[Callable[[np.ndarray], None]] = None
        self.on_speech_ended: Optional[Callable[[], None]] = None
        self.on_transcription_ready: Optional[Callable[[TranscriptionResult], None]] = None
    
    def _get_device(self, device: str) -> str:
        """获取计算设备"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device
    
    async def initialize(self) -> bool:
        """初始化 ASR 系统"""
        try:
            self.logger.info(f"初始化 Whisper ASR - 模型: {self.model_name}, 设备: {self.device}")
            
            # 初始化 Whisper 模型
            if not await self._load_whisper_model():
                return False
            
            # 初始化 VAD 模型
            if not await self._load_vad_model():
                return False
            
            # 测试模型
            if not await self._test_models():
                return False
            
            self.logger.info("Whisper ASR 初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"Whisper ASR 初始化失败: {e}")
            return False
    
    async def _load_whisper_model(self) -> bool:
        """加载 Whisper 模型"""
        try:
            self.logger.info(f"加载 Whisper 模型: {self.model_name}")
            
            # 使用 transformers 库加载模型（更好的 GPU 支持）
            if self.device == "cuda":
                model_id = f"openai/whisper-{self.model_name}"
                
                # 加载模型和处理器
                model = AutoModelForSpeechSeq2Seq.from_pretrained(
                    model_id,
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True,
                    use_safetensors=True
                )
                model.to(self.device)
                
                processor = AutoProcessor.from_pretrained(model_id)
                
                # 创建 pipeline
                self.asr_pipeline = pipeline(
                    "automatic-speech-recognition",
                    model=model,
                    tokenizer=processor.tokenizer,
                    feature_extractor=processor.feature_extractor,
                    max_new_tokens=128,
                    torch_dtype=torch.float16,
                    device=self.device,
                    return_timestamps=self.config["return_timestamps"]
                )
                
                self.logger.info("使用 transformers pipeline 加载 Whisper 模型")
            
            else:
                # CPU 或 MPS 使用原始 whisper 库
                self.whisper_model = whisper.load_model(self.model_name, device=self.device)
                self.logger.info("使用原始 whisper 库加载模型")
            
            return True
            
        except Exception as e:
            self.logger.error(f"加载 Whisper 模型失败: {e}")
            return False
    
    async def _load_vad_model(self) -> bool:
        """加载 VAD 模型"""
        try:
            self.logger.info("加载 Silero VAD 模型")
            
            # 加载预训练的 Silero VAD 模型
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            
            self.vad_model = model
            self.vad_utils = utils
            
            # 移动到指定设备
            self.vad_model.to(self.device)
            self.vad_model.eval()
            
            self.logger.info("Silero VAD 模型加载完成")
            return True
            
        except Exception as e:
            self.logger.error(f"加载 VAD 模型失败: {e}")
            # VAD 失败不阻止整个系统
            self.vad_model = None
            return True
    
    async def _test_models(self) -> bool:
        """测试模型"""
        try:
            # 创建测试音频（1秒静音）
            test_audio = np.zeros(self.config["sample_rate"], dtype=np.float32)
            
            # 测试 VAD
            if self.vad_model:
                vad_result = await self.detect_voice_activity(test_audio)
                self.logger.debug(f"VAD 测试结果: {vad_result.is_speech}")
            
            # 测试 Whisper
            transcription = await self.transcribe(test_audio)
            self.logger.debug(f"Whisper 测试结果: '{transcription.text}'")
            
            return True
            
        except Exception as e:
            self.logger.error(f"模型测试失败: {e}")
            return False
    
    async def detect_voice_activity(self, audio_data: np.ndarray) -> VADResult:
        """检测语音活动"""
        try:
            if self.vad_model is None:
                # 没有 VAD 模型时的简单能量检测
                energy = np.mean(audio_data ** 2)
                is_speech = energy > (self.vad_threshold * 0.01)
                
                return VADResult(
                    is_speech=is_speech,
                    confidence=min(energy * 100, 1.0),
                    start_time=0.0,
                    end_time=len(audio_data) / self.config["sample_rate"]
                )
            
            # 确保音频格式正确
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)  # 转换为单声道
            
            # 重采样到 VAD 要求的采样率
            if len(audio_data) == 0:
                return VADResult(False, 0.0, 0.0, 0.0)
            
            # 转换为 tensor
            audio_tensor = torch.from_numpy(audio_data).float().to(self.device)
            
            # 使用 VAD 模型检测
            with torch.no_grad():
                speech_probs = self.vad_model(audio_tensor, self.vad_sample_rate)
            
            # 计算置信度
            if isinstance(speech_probs, torch.Tensor):
                confidence = float(speech_probs.max().cpu())
            else:
                confidence = float(speech_probs)
            
            is_speech = confidence > self.vad_threshold
            duration = len(audio_data) / self.vad_sample_rate
            
            # 更新统计
            self.stats["vad_detections"] += 1
            
            return VADResult(
                is_speech=is_speech,
                confidence=confidence,
                start_time=0.0,
                end_time=duration
            )
            
        except Exception as e:
            self.logger.error(f"语音活动检测失败: {e}")
            return VADResult(False, 0.0, 0.0, 0.0)
    
    async def transcribe(self, audio_data: np.ndarray, language: str = "auto") -> TranscriptionResult:
        """转录音频"""
        start_time = time.time()
        
        try:
            # 预处理音频
            processed_audio = self._preprocess_audio(audio_data)
            
            if len(processed_audio) == 0:
                return TranscriptionResult("", 0.0, [], "en", 0.0)
            
            # 选择转录方法
            if self.asr_pipeline:
                result = await self._transcribe_with_pipeline(processed_audio, language)
            else:
                result = await self._transcribe_with_whisper(processed_audio, language)
            
            # 计算处理时间
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            
            # 更新统计
            self.stats["total_transcriptions"] += 1
            self.stats["total_processing_time"] += processing_time
            self.stats["average_processing_time"] = (
                self.stats["total_processing_time"] / self.stats["total_transcriptions"]
            )
            
            # 触发回调
            if self.on_transcription_ready:
                self.on_transcription_ready(result)
            
            self.logger.debug(f"转录完成: '{result.text}' (耗时: {processing_time:.2f}s)")
            return result
            
        except Exception as e:
            self.logger.error(f"音频转录失败: {e}")
            return TranscriptionResult("", 0.0, [], "en", time.time() - start_time)
    
    def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """预处理音频数据"""
        try:
            # 确保是单声道
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # 标准化音频
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data))
            
            # 移除静音段
            # 简单的能量阈值方法
            energy_threshold = 0.01
            frame_length = 1024
            hop_length = 512
            
            # 计算每帧能量
            frames = []
            for i in range(0, len(audio_data) - frame_length, hop_length):
                frame = audio_data[i:i + frame_length]
                energy = np.mean(frame ** 2)
                
                if energy > energy_threshold:
                    frames.extend(frame)
            
            if len(frames) == 0:
                return np.array([], dtype=np.float32)
            
            return np.array(frames, dtype=np.float32)
            
        except Exception as e:
            self.logger.error(f"音频预处理失败: {e}")
            return audio_data
    
    async def _transcribe_with_pipeline(self, audio_data: np.ndarray, language: str) -> TranscriptionResult:
        """使用 transformers pipeline 转录"""
        try:
            # 准备输入
            inputs = {
                "raw": audio_data,
                "sampling_rate": self.config["sample_rate"]
            }
            
            # 设置生成参数
            generate_kwargs = {
                "max_new_tokens": 128,
                "num_beams": self.config["beam_size"],
                "do_sample": False,
                "temperature": self.config["temperature"],
                "return_timestamps": self.config["return_timestamps"]
            }
            
            # 在线程池中运行推理
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.asr_pipeline(inputs, generate_kwargs=generate_kwargs)
            )
            
            # 解析结果
            text = result.get("text", "").strip()
            
            # 处理时间戳信息
            segments = []
            if "chunks" in result:
                for chunk in result["chunks"]:
                    segments.append({
                        "text": chunk.get("text", ""),
                        "start": chunk.get("timestamp", [0, 0])[0],
                        "end": chunk.get("timestamp", [0, 0])[1]
                    })
            
            return TranscriptionResult(
                text=text,
                confidence=0.9,  # Pipeline 不返回置信度
                segments=segments,
                language=language if language != "auto" else "auto",
                processing_time=0.0  # 在外部计算
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline 转录失败: {e}")
            raise
    
    async def _transcribe_with_whisper(self, audio_data: np.ndarray, language: str) -> TranscriptionResult:
        """使用原始 Whisper 模型转录"""
        try:
            # 准备 Whisper 选项
            options = {
                "language": None if language == "auto" else language,
                "beam_size": self.config["beam_size"],
                "patience": self.config["patience"],
                "temperature": self.config["temperature"],
                "compression_ratio_threshold": self.config["compression_ratio_threshold"],
                "logprob_threshold": self.config["logprob_threshold"],
                "no_speech_threshold": self.config["no_speech_threshold"],
                "condition_on_previous_text": self.config["condition_on_previous_text"]
            }
            
            # 在线程池中运行推理
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.whisper_model.transcribe(audio_data, **options)
            )
            
            # 解析结果
            text = result.get("text", "").strip()
            language_detected = result.get("language", "en")
            
            # 处理分段信息
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "text": segment.get("text", ""),
                    "start": segment.get("start", 0.0),
                    "end": segment.get("end", 0.0)
                })
            
            # 计算平均置信度
            avg_confidence = 0.0
            if segments:
                confidences = [seg.get("avg_logprob", 0.0) for seg in result.get("segments", [])]
                if confidences:
                    # 将 log 概率转换为置信度 (简化)
                    avg_confidence = np.exp(np.mean(confidences))
            
            return TranscriptionResult(
                text=text,
                confidence=max(0.0, min(1.0, avg_confidence)),
                segments=segments,
                language=language_detected,
                processing_time=0.0  # 在外部计算
            )
            
        except Exception as e:
            self.logger.error(f"Whisper 转录失败: {e}")
            raise
    
    async def process_audio_stream(self, audio_chunk: np.ndarray) -> Optional[TranscriptionResult]:
        """处理音频流（实时处理）"""
        try:
            # 添加到缓冲区
            with self.buffer_lock:
                self.audio_buffer.append(audio_chunk)
                
                # 限制缓冲区大小
                total_duration = sum(len(chunk) for chunk in self.audio_buffer) / self.config["sample_rate"]
                
                while total_duration > self.max_buffer_duration and len(self.audio_buffer) > 1:
                    removed_chunk = self.audio_buffer.pop(0)
                    total_duration -= len(removed_chunk) / self.config["sample_rate"]
            
            # 检测语音活动
            vad_result = await self.detect_voice_activity(audio_chunk)
            
            if vad_result.is_speech:
                if self.on_speech_detected:
                    self.on_speech_detected(audio_chunk)
                
                # 如果还没有在处理，开始处理
                if not self.is_processing:
                    self.is_processing = True
                    self.processing_task = asyncio.create_task(self._process_buffered_audio())
            
            else:
                # 语音结束
                if self.is_processing:
                    if self.on_speech_ended:
                        self.on_speech_ended()
            
            return None
            
        except Exception as e:
            self.logger.error(f"处理音频流失败: {e}")
            return None
    
    async def _process_buffered_audio(self):
        """处理缓冲的音频"""
        try:
            # 等待一段时间收集更多音频
            await asyncio.sleep(0.5)
            
            # 合并缓冲区中的音频
            with self.buffer_lock:
                if not self.audio_buffer:
                    self.is_processing = False
                    return
                
                combined_audio = np.concatenate(self.audio_buffer)
                self.audio_buffer.clear()
            
            # 进行转录
            if len(combined_audio) > 0:
                result = await self.transcribe(combined_audio)
                
                if result.text.strip():
                    return result
            
        except Exception as e:
            self.logger.error(f"处理缓冲音频失败: {e}")
        
        finally:
            self.is_processing = False
    
    # 公共接口
    async def transcribe_file(self, file_path: str, language: str = "auto") -> TranscriptionResult:
        """转录音频文件"""
        try:
            # 使用 librosa 加载音频
            audio_data, sr = librosa.load(file_path, sr=self.config["sample_rate"], mono=True)
            return await self.transcribe(audio_data, language)
            
        except Exception as e:
            self.logger.error(f"转录文件失败 {file_path}: {e}")
            return TranscriptionResult("", 0.0, [], "en", 0.0)
    
    def set_language(self, language: str):
        """设置识别语言"""
        if language in self.language_mapping:
            self.config["language"] = language
            self.logger.info(f"设置识别语言: {language}")
        else:
            self.logger.warning(f"不支持的语言: {language}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_transcriptions": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "vad_detections": 0,
            "false_positives": 0
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 停止处理任务
            if self.processing_task and not self.processing_task.done():
                self.processing_task.cancel()
                try:
                    await self.processing_task
                except asyncio.CancelledError:
                    pass
            
            # 清理模型
            if hasattr(self, 'whisper_model') and self.whisper_model:
                del self.whisper_model
            
            if hasattr(self, 'vad_model') and self.vad_model:
                del self.vad_model
            
            if hasattr(self, 'asr_pipeline') and self.asr_pipeline:
                del self.asr_pipeline
            
            # 清理缓冲区
            with self.buffer_lock:
                self.audio_buffer.clear()
            
            # 强制垃圾回收
            import gc
            gc.collect()
            
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            self.logger.info("Whisper ASR 资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理 ASR 资源失败: {e}") 