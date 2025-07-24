"""
TTS 引擎模块 - 支持语音合成、音素时序生成和音频播放
"""

import asyncio
import logging
import numpy as np
import torch
import time
import re
import io
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass
from pathlib import Path
import threading

try:
    import onnxruntime as ort
    import librosa
    import soundfile as sf
    import phonemizer
    import espeak_ng
    import pyaudio
    from scipy.signal import resample
    import pygame
except ImportError:
    logging.warning("TTS 相关库未安装，语音合成功能将受限")


@dataclass
class AudioSegment:
    """音频段"""
    audio_data: np.ndarray
    sample_rate: int
    duration: float
    text: str
    phonemes: str = ""
    phoneme_timing: List[Tuple[float, str]] = None


@dataclass
class PhonemeTimestamp:
    """音素时间戳"""
    phoneme: str
    start_time: float
    end_time: float
    mouth_open_y: float = 0.0
    jaw_open: float = 0.0
    mouth_form: float = 0.0
    mouth_shrug: float = 0.0
    mouth_funnel: float = 0.0
    mouth_pucker_widen: float = 0.0
    mouth_press_lip: float = 0.0
    mouth_x: float = 0.0
    cheek_puff: float = 0.0


class TTSEngine:
    """
    TTS 引擎
    
    功能：
    1. 文本预处理和标准化
    2. 音素化 (G2P)
    3. ONNX 模型语音合成
    4. espeak-ng 回退合成
    5. VBridger 标准音素时序生成
    6. 音频播放和流处理
    """
    
    def __init__(self, voice: str = "default", speed: float = 1.0, device: str = "auto"):
        self.voice = voice
        self.speed = speed
        self.device = self._get_device(device)
        
        self.logger = logging.getLogger(__name__)
        
        # 模型相关
        self.synthesis_session: Optional[ort.InferenceSession] = None
        self.voice_embeddings: Dict[str, np.ndarray] = {}
        self.phoneme_to_id: Dict[str, int] = {}
        self.id_to_phoneme: Dict[int, str] = {}
        
        # 音素化相关
        self.phonemizer_backend: Optional[Any] = None
        self.espeak_fallback = True
        
        # 音频播放
        self.audio_player: Optional[Any] = None
        self.playback_thread: Optional[threading.Thread] = None
        self.playback_queue: asyncio.Queue = asyncio.Queue()
        self.is_playing = False
        self.stop_playback_flag = threading.Event()
        
        # 配置
        self.config = {
            "sample_rate": 24000,
            "hop_length": 256,
            "win_length": 1024,
            "n_mel": 80,
            "max_wav_value": 32767.0,
            "text_cleaners": ["english_cleaners"],
            "phoneme_language": "en-us",
            "add_blank": True,
            "normalize": True
        }
        
        # VBridger 音素映射
        self.vbridger_phoneme_map = {
            # 元音
            "a": {"mouth_open_y": 0.8, "jaw_open": 0.6, "mouth_form": 0.0},
            "e": {"mouth_open_y": 0.4, "jaw_open": 0.3, "mouth_form": 0.0},
            "i": {"mouth_open_y": 0.1, "jaw_open": 0.1, "mouth_form": 0.7, "mouth_pucker_widen": -0.9},
            "o": {"mouth_open_y": 0.6, "jaw_open": 0.4, "mouth_form": 0.0, "mouth_funnel": 0.6},
            "u": {"mouth_open_y": 0.3, "jaw_open": 0.2, "mouth_form": 0.0, "mouth_funnel": 0.8, "mouth_pucker_widen": 0.7},
            
            # 辅音
            "p": {"mouth_open_y": 0.0, "jaw_open": 0.0, "mouth_form": 0.0, "mouth_press_lip": -1.0},
            "b": {"mouth_open_y": 0.1, "jaw_open": 0.1, "mouth_form": 0.0, "mouth_press_lip": -0.5},
            "m": {"mouth_open_y": 0.0, "jaw_open": 0.0, "mouth_form": 0.0, "mouth_press_lip": -1.0},
            "f": {"mouth_open_y": 0.1, "jaw_open": 0.0, "mouth_form": 0.0, "mouth_press_lip": 0.3},
            "v": {"mouth_open_y": 0.2, "jaw_open": 0.1, "mouth_form": 0.0, "mouth_press_lip": 0.2},
            "t": {"mouth_open_y": 0.1, "jaw_open": 0.1, "mouth_form": 0.0, "mouth_press_lip": 0.5},
            "d": {"mouth_open_y": 0.2, "jaw_open": 0.1, "mouth_form": 0.0, "mouth_press_lip": 0.3},
            "n": {"mouth_open_y": 0.1, "jaw_open": 0.1, "mouth_form": 0.0, "mouth_press_lip": 0.2},
            "s": {"mouth_open_y": 0.1, "jaw_open": 0.0, "mouth_form": 0.0, "mouth_press_lip": 0.8},
            "z": {"mouth_open_y": 0.1, "jaw_open": 0.0, "mouth_form": 0.0, "mouth_press_lip": 0.6},
            "ʃ": {"mouth_open_y": 0.2, "jaw_open": 0.1, "mouth_form": 0.0, "mouth_funnel": 0.5, "mouth_pucker_widen": 0.3},
            "ʒ": {"mouth_open_y": 0.2, "jaw_open": 0.1, "mouth_form": 0.0, "mouth_funnel": 0.4, "mouth_pucker_widen": 0.2},
            "k": {"mouth_open_y": 0.3, "jaw_open": 0.2, "mouth_form": 0.0},
            "g": {"mouth_open_y": 0.3, "jaw_open": 0.2, "mouth_form": 0.0},
            "l": {"mouth_open_y": 0.3, "jaw_open": 0.2, "mouth_form": 0.0, "mouth_press_lip": 0.1},
            "r": {"mouth_open_y": 0.3, "jaw_open": 0.2, "mouth_form": 0.0, "mouth_pucker_widen": 0.2},
            "w": {"mouth_open_y": 0.2, "jaw_open": 0.1, "mouth_form": 0.0, "mouth_funnel": 0.7, "mouth_pucker_widen": 0.6},
            "j": {"mouth_open_y": 0.1, "jaw_open": 0.1, "mouth_form": 0.5},
            "h": {"mouth_open_y": 0.3, "jaw_open": 0.2, "mouth_form": 0.0},
            
            # 静音
            "sil": {"mouth_open_y": 0.0, "jaw_open": 0.0, "mouth_form": 0.0},
            "sp": {"mouth_open_y": 0.0, "jaw_open": 0.0, "mouth_form": 0.0},
        }
        
        # 统计信息
        self.stats = {
            "total_syntheses": 0,
            "total_synthesis_time": 0.0,
            "average_synthesis_time": 0.0,
            "characters_synthesized": 0,
            "audio_duration_generated": 0.0
        }
        
        # 回调函数
        self.on_synthesis_start: Optional[Callable[[str], None]] = None
        self.on_synthesis_complete: Optional[Callable[[AudioSegment], None]] = None
        self.on_playback_start: Optional[Callable[[], None]] = None
        self.on_playback_end: Optional[Callable[[], None]] = None
    
    def _get_device(self, device: str) -> str:
        """获取计算设备"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            else:
                return "cpu"
        return device
    
    async def initialize(self) -> bool:
        """初始化 TTS 引擎"""
        try:
            self.logger.info(f"初始化 TTS 引擎 - 语音: {self.voice}, 设备: {self.device}")
            
            # 初始化 ONNX 合成模型
            if not await self._load_synthesis_model():
                self.logger.warning("ONNX 合成模型加载失败，将使用 espeak 回退")
            
            # 初始化音素化器
            if not await self._initialize_phonemizer():
                return False
            
            # 初始化音频播放器
            if not await self._initialize_audio_player():
                return False
            
            # 加载语音嵌入
            await self._load_voice_embeddings()
            
            # 测试合成
            if not await self._test_synthesis():
                return False
            
            self.logger.info("TTS 引擎初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"TTS 引擎初始化失败: {e}")
            return False
    
    async def _load_synthesis_model(self) -> bool:
        """加载 ONNX 合成模型"""
        try:
            # 查找模型文件
            model_paths = [
                "models/tts/kokoro/model_slim.onnx",
                "resources/models/kokoro/model_slim.onnx",
                "./kokoro_model.onnx"
            ]
            
            model_path = None
            for path in model_paths:
                if Path(path).exists():
                    model_path = path
                    break
            
            if not model_path:
                self.logger.warning("未找到 ONNX TTS 模型文件")
                return False
            
            # 配置 ONNX Runtime
            providers = []
            if self.device == "cuda":
                providers.append("CUDAExecutionProvider")
            providers.append("CPUExecutionProvider")
            
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            session_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
            
            # 加载模型
            self.synthesis_session = ort.InferenceSession(
                model_path,
                providers=providers,
                sess_options=session_options
            )
            
            # 加载音素映射
            await self._load_phoneme_mapping()
            
            self.logger.info(f"成功加载 ONNX TTS 模型: {model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载 ONNX TTS 模型失败: {e}")
            return False
    
    async def _load_phoneme_mapping(self):
        """加载音素映射"""
        try:
            # 查找音素映射文件
            mapping_paths = [
                "models/tts/kokoro/phoneme_to_id.txt",
                "resources/models/kokoro/phoneme_to_id.txt"
            ]
            
            mapping_file = None
            for path in mapping_paths:
                if Path(path).exists():
                    mapping_file = path
                    break
            
            if mapping_file:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) == 2:
                            phoneme, phoneme_id = parts
                            self.phoneme_to_id[phoneme] = int(phoneme_id)
                            self.id_to_phoneme[int(phoneme_id)] = phoneme
                
                self.logger.info(f"加载音素映射: {len(self.phoneme_to_id)} 个音素")
            else:
                # 使用默认映射
                self._create_default_phoneme_mapping()
                
        except Exception as e:
            self.logger.error(f"加载音素映射失败: {e}")
            self._create_default_phoneme_mapping()
    
    def _create_default_phoneme_mapping(self):
        """创建默认音素映射"""
        default_phonemes = [
            "sil", "sp", "a", "e", "i", "o", "u", "p", "b", "m", "f", "v",
            "t", "d", "n", "s", "z", "ʃ", "ʒ", "k", "g", "l", "r", "w", "j", "h"
        ]
        
        for i, phoneme in enumerate(default_phonemes):
            self.phoneme_to_id[phoneme] = i
            self.id_to_phoneme[i] = phoneme
    
    async def _initialize_phonemizer(self) -> bool:
        """初始化音素化器"""
        try:
            # 尝试使用 phonemizer 库
            try:
                from phonemizer import phonemize
                from phonemizer.backend import EspeakBackend
                
                self.phonemizer_backend = EspeakBackend(
                    language=self.config["phoneme_language"],
                    preserve_punctuation=False,
                    with_stress=False,
                    tie=False
                )
                
                self.logger.info("使用 phonemizer 库进行音素化")
                return True
                
            except ImportError:
                self.logger.warning("phonemizer 库不可用")
            
            # 回退到 espeak-ng
            try:
                import espeak_ng
                self.espeak_fallback = True
                self.logger.info("使用 espeak-ng 进行音素化")
                return True
                
            except ImportError:
                self.logger.error("espeak-ng 不可用，无法进行音素化")
                return False
                
        except Exception as e:
            self.logger.error(f"初始化音素化器失败: {e}")
            return False
    
    async def _initialize_audio_player(self) -> bool:
        """初始化音频播放器"""
        try:
            # 尝试使用 pygame
            try:
                pygame.mixer.pre_init(
                    frequency=self.config["sample_rate"],
                    size=-16,
                    channels=1,
                    buffer=512
                )
                pygame.mixer.init()
                self.audio_player = "pygame"
                self.logger.info("使用 pygame 进行音频播放")
                return True
                
            except Exception:
                pass
            
            # 回退到 pyaudio
            try:
                import pyaudio
                self.audio_player = "pyaudio"
                self.logger.info("使用 pyaudio 进行音频播放")
                return True
                
            except ImportError:
                self.logger.warning("音频播放库不可用")
                return True  # 不阻止 TTS 功能
                
        except Exception as e:
            self.logger.error(f"初始化音频播放器失败: {e}")
            return True  # 不阻止 TTS 功能
    
    async def _load_voice_embeddings(self):
        """加载语音嵌入"""
        try:
            # 查找语音文件目录
            voice_dirs = [
                "models/tts/kokoro/voices",
                "resources/models/kokoro/voices"
            ]
            
            for voice_dir in voice_dirs:
                voice_path = Path(voice_dir)
                if voice_path.exists():
                    for voice_file in voice_path.glob("*.npy"):
                        voice_name = voice_file.stem
                        try:
                            embedding = np.load(voice_file)
                            self.voice_embeddings[voice_name] = embedding
                            self.logger.debug(f"加载语音嵌入: {voice_name}")
                        except Exception as e:
                            self.logger.warning(f"加载语音嵌入失败 {voice_name}: {e}")
                    break
            
            if not self.voice_embeddings:
                # 创建默认嵌入
                self.voice_embeddings["default"] = np.random.randn(256).astype(np.float32)
                self.logger.info("使用默认语音嵌入")
            else:
                self.logger.info(f"加载 {len(self.voice_embeddings)} 个语音嵌入")
                
        except Exception as e:
            self.logger.error(f"加载语音嵌入失败: {e}")
            self.voice_embeddings["default"] = np.random.randn(256).astype(np.float32)
    
    async def _test_synthesis(self) -> bool:
        """测试语音合成"""
        try:
            test_text = "Hello, this is a test."
            result = await self.synthesize(test_text)
            
            if result and len(result.audio_data) > 0:
                self.logger.debug("TTS 合成测试成功")
                return True
            else:
                self.logger.warning("TTS 合成测试返回空结果")
                return True  # 不阻止系统启动
                
        except Exception as e:
            self.logger.error(f"TTS 合成测试失败: {e}")
            return True  # 不阻止系统启动
    
    async def synthesize(self, text: str, voice: str = None) -> Optional[AudioSegment]:
        """合成语音"""
        start_time = time.time()
        
        try:
            if not text or not text.strip():
                return None
            
            # 触发开始回调
            if self.on_synthesis_start:
                self.on_synthesis_start(text)
            
            # 文本预处理
            cleaned_text = self._preprocess_text(text)
            
            # 音素化
            phonemes = await self._text_to_phonemes(cleaned_text)
            
            # 选择语音
            voice_name = voice or self.voice
            
            # 合成音频
            if self.synthesis_session and voice_name in self.voice_embeddings:
                audio_data = await self._synthesize_with_onnx(phonemes, voice_name)
            else:
                audio_data = await self._synthesize_with_espeak(cleaned_text)
            
            if audio_data is None or len(audio_data) == 0:
                return None
            
            # 应用速度调整
            if self.speed != 1.0:
                audio_data = self._adjust_speed(audio_data, self.speed)
            
            # 创建音频段
            duration = len(audio_data) / self.config["sample_rate"]
            segment = AudioSegment(
                audio_data=audio_data,
                sample_rate=self.config["sample_rate"],
                duration=duration,
                text=text,
                phonemes=phonemes
            )
            
            # 计算处理时间
            processing_time = time.time() - start_time
            
            # 更新统计
            self.stats["total_syntheses"] += 1
            self.stats["total_synthesis_time"] += processing_time
            self.stats["average_synthesis_time"] = (
                self.stats["total_synthesis_time"] / self.stats["total_syntheses"]
            )
            self.stats["characters_synthesized"] += len(text)
            self.stats["audio_duration_generated"] += duration
            
            # 触发完成回调
            if self.on_synthesis_complete:
                self.on_synthesis_complete(segment)
            
            self.logger.debug(f"合成完成: '{text}' (耗时: {processing_time:.2f}s)")
            return segment
            
        except Exception as e:
            self.logger.error(f"语音合成失败: {e}")
            return None
    
    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        try:
            # 移除多余空格
            text = re.sub(r'\s+', ' ', text.strip())
            
            # 处理数字
            text = self._expand_numbers(text)
            
            # 处理缩写
            text = self._expand_abbreviations(text)
            
            # 标准化标点
            text = self._normalize_punctuation(text)
            
            return text
            
        except Exception as e:
            self.logger.error(f"文本预处理失败: {e}")
            return text
    
    def _expand_numbers(self, text: str) -> str:
        """扩展数字"""
        # 简化的数字处理
        number_words = {
            "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
            "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
            "10": "ten", "11": "eleven", "12": "twelve", "13": "thirteen",
            "14": "fourteen", "15": "fifteen", "16": "sixteen", "17": "seventeen",
            "18": "eighteen", "19": "nineteen", "20": "twenty"
        }
        
        def replace_number(match):
            num = match.group()
            return number_words.get(num, num)
        
        return re.sub(r'\b\d+\b', replace_number, text)
    
    def _expand_abbreviations(self, text: str) -> str:
        """扩展缩写"""
        abbreviations = {
            "Dr.": "Doctor",
            "Mr.": "Mister", 
            "Mrs.": "Missus",
            "Ms.": "Miss",
            "Prof.": "Professor",
            "St.": "Street",
            "Ave.": "Avenue",
            "Blvd.": "Boulevard",
            "etc.": "etcetera",
            "vs.": "versus",
            "e.g.": "for example",
            "i.e.": "that is"
        }
        
        for abbr, full in abbreviations.items():
            text = text.replace(abbr, full)
        
        return text
    
    def _normalize_punctuation(self, text: str) -> str:
        """标准化标点符号"""
        # 移除多余的标点
        text = re.sub(r'[.]{2,}', '.', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # 确保句子结尾有标点
        if text and text[-1] not in '.!?':
            text += '.'
        
        return text
    
    async def _text_to_phonemes(self, text: str) -> str:
        """文本转音素"""
        try:
            if self.phonemizer_backend:
                # 使用 phonemizer
                loop = asyncio.get_event_loop()
                phonemes = await loop.run_in_executor(
                    None,
                    lambda: self.phonemizer_backend.phonemize([text], strip=True)[0]
                )
                return phonemes
            
            elif self.espeak_fallback:
                # 使用 espeak-ng
                import subprocess
                result = subprocess.run(
                    ['espeak-ng', '-q', '--ipa', text],
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    self.logger.warning(f"espeak-ng 音素化失败: {result.stderr}")
            
            # 回退到简单映射
            return self._simple_phonemize(text)
            
        except Exception as e:
            self.logger.error(f"音素化失败: {e}")
            return self._simple_phonemize(text)
    
    def _simple_phonemize(self, text: str) -> str:
        """简单音素化（回退方法）"""
        # 非常简化的英文音素映射
        simple_map = {
            'a': 'a', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u',
            'b': 'b', 'c': 'k', 'd': 'd', 'f': 'f', 'g': 'g',
            'h': 'h', 'j': 'j', 'k': 'k', 'l': 'l', 'm': 'm',
            'n': 'n', 'p': 'p', 'q': 'k', 'r': 'r', 's': 's',
            't': 't', 'v': 'v', 'w': 'w', 'x': 'k s', 'y': 'j',
            'z': 'z', ' ': 'sp'
        }
        
        result = []
        for char in text.lower():
            if char in simple_map:
                result.append(simple_map[char])
            elif char.isalpha():
                result.append('sil')
        
        return ' '.join(result)
    
    async def _synthesize_with_onnx(self, phonemes: str, voice_name: str) -> Optional[np.ndarray]:
        """使用 ONNX 模型合成"""
        try:
            # 转换音素为 ID
            phoneme_ids = self._phonemes_to_ids(phonemes)
            
            if not phoneme_ids:
                return None
            
            # 准备输入
            phoneme_tensor = np.array([phoneme_ids], dtype=np.int64)
            voice_embedding = self.voice_embeddings[voice_name].reshape(1, -1)
            
            # 运行推理
            loop = asyncio.get_event_loop()
            outputs = await loop.run_in_executor(
                None,
                lambda: self.synthesis_session.run(
                    None,
                    {
                        "phoneme_ids": phoneme_tensor,
                        "voice_embedding": voice_embedding
                    }
                )
            )
            
            # 提取音频
            if outputs and len(outputs) > 0:
                audio_data = outputs[0].flatten().astype(np.float32)
                
                # 标准化音频
                if np.max(np.abs(audio_data)) > 0:
                    audio_data = audio_data / np.max(np.abs(audio_data)) * 0.95
                
                return audio_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"ONNX 合成失败: {e}")
            return None
    
    def _phonemes_to_ids(self, phonemes: str) -> List[int]:
        """音素转 ID"""
        phoneme_list = phonemes.split()
        ids = []
        
        for phoneme in phoneme_list:
            if phoneme in self.phoneme_to_id:
                ids.append(self.phoneme_to_id[phoneme])
            else:
                # 未知音素使用静音
                ids.append(self.phoneme_to_id.get("sil", 0))
        
        return ids
    
    async def _synthesize_with_espeak(self, text: str) -> Optional[np.ndarray]:
        """使用 espeak 合成"""
        try:
            import subprocess
            import tempfile
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # 运行 espeak
            cmd = [
                'espeak-ng',
                '-w', tmp_path,
                '-s', str(int(150 * self.speed)),  # 语速
                '-a', '50',  # 音量
                text
            ]
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True)
            )
            
            if result.returncode == 0 and Path(tmp_path).exists():
                # 加载音频
                audio_data, sr = librosa.load(tmp_path, sr=self.config["sample_rate"], mono=True)
                
                # 清理临时文件
                Path(tmp_path).unlink()
                
                return audio_data
            else:
                self.logger.error(f"espeak 合成失败: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"espeak 合成失败: {e}")
            return None
    
    def _adjust_speed(self, audio_data: np.ndarray, speed: float) -> np.ndarray:
        """调整音频速度"""
        try:
            if speed == 1.0:
                return audio_data
            
            # 使用重采样调整速度
            new_length = int(len(audio_data) / speed)
            return resample(audio_data, new_length)
            
        except Exception as e:
            self.logger.error(f"调整音频速度失败: {e}")
            return audio_data
    
    async def get_phoneme_timing(self, text: str) -> List[PhonemeTimestamp]:
        """获取音素时序（用于唇形同步）"""
        try:
            # 获取音素
            phonemes = await self._text_to_phonemes(text)
            phoneme_list = phonemes.split()
            
            if not phoneme_list:
                return []
            
            # 估算每个音素的时长
            # 这是一个简化的实现，实际应该从 TTS 模型获取准确的时序
            estimated_duration = len(text) * 0.1  # 假设每个字符 100ms
            phoneme_duration = estimated_duration / len(phoneme_list)
            
            timestamps = []
            current_time = 0.0
            
            for phoneme in phoneme_list:
                # 获取 VBridger 参数
                vb_params = self.vbridger_phoneme_map.get(phoneme, {})
                
                timestamp = PhonemeTimestamp(
                    phoneme=phoneme,
                    start_time=current_time,
                    end_time=current_time + phoneme_duration,
                    mouth_open_y=vb_params.get("mouth_open_y", 0.0),
                    jaw_open=vb_params.get("jaw_open", 0.0),
                    mouth_form=vb_params.get("mouth_form", 0.0),
                    mouth_shrug=vb_params.get("mouth_shrug", 0.0),
                    mouth_funnel=vb_params.get("mouth_funnel", 0.0),
                    mouth_pucker_widen=vb_params.get("mouth_pucker_widen", 0.0),
                    mouth_press_lip=vb_params.get("mouth_press_lip", 0.0),
                    mouth_x=vb_params.get("mouth_x", 0.0),
                    cheek_puff=vb_params.get("cheek_puff", 0.0)
                )
                
                timestamps.append(timestamp)
                current_time += phoneme_duration
            
            return timestamps
            
        except Exception as e:
            self.logger.error(f"获取音素时序失败: {e}")
            return []
    
    async def play_audio(self, audio_data: np.ndarray) -> bool:
        """播放音频"""
        try:
            if self.audio_player == "pygame":
                return await self._play_with_pygame(audio_data)
            elif self.audio_player == "pyaudio":
                return await self._play_with_pyaudio(audio_data)
            else:
                self.logger.warning("没有可用的音频播放器")
                return False
                
        except Exception as e:
            self.logger.error(f"音频播放失败: {e}")
            return False
    
    async def _play_with_pygame(self, audio_data: np.ndarray) -> bool:
        """使用 pygame 播放音频"""
        try:
            # 转换为 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # 创建音频缓冲
            audio_bytes = audio_int16.tobytes()
            
            # 播放
            pygame.mixer.music.load(io.BytesIO(audio_bytes))
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            self.logger.error(f"pygame 播放失败: {e}")
            return False
    
    async def _play_with_pyaudio(self, audio_data: np.ndarray) -> bool:
        """使用 pyaudio 播放音频"""
        try:
            import pyaudio
            
            # 转换为 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # 创建 pyaudio 实例
            p = pyaudio.PyAudio()
            
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.config["sample_rate"],
                output=True
            )
            
            # 播放音频
            stream.write(audio_int16.tobytes())
            
            # 清理
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            return True
            
        except Exception as e:
            self.logger.error(f"pyaudio 播放失败: {e}")
            return False
    
    async def stop_playback(self):
        """停止播放"""
        try:
            self.stop_playback_flag.set()
            
            if self.audio_player == "pygame":
                pygame.mixer.music.stop()
            
            self.is_playing = False
            
            if self.on_playback_end:
                self.on_playback_end()
                
        except Exception as e:
            self.logger.error(f"停止播放失败: {e}")
    
    # 公共接口
    def set_voice(self, voice: str):
        """设置语音"""
        if voice in self.voice_embeddings:
            self.voice = voice
            self.logger.info(f"设置语音: {voice}")
        else:
            self.logger.warning(f"未找到语音: {voice}")
    
    def set_speed(self, speed: float):
        """设置语速"""
        self.speed = max(0.5, min(2.0, speed))
        self.logger.info(f"设置语速: {self.speed}")
    
    def get_available_voices(self) -> List[str]:
        """获取可用语音列表"""
        return list(self.voice_embeddings.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_syntheses": 0,
            "total_synthesis_time": 0.0,
            "average_synthesis_time": 0.0,
            "characters_synthesized": 0,
            "audio_duration_generated": 0.0
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 停止播放
            await self.stop_playback()
            
            # 清理 ONNX 会话
            if self.synthesis_session:
                self.synthesis_session = None
            
            # 清理 pygame
            if self.audio_player == "pygame":
                pygame.mixer.quit()
            
            # 清理缓存
            self.voice_embeddings.clear()
            
            self.logger.info("TTS 引擎资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理 TTS 资源失败: {e}") 