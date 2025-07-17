"""
文本转语音引擎
支持多种TTS后端：Coqui TTS, ElevenLabs, Azure等
"""

import asyncio
import numpy as np
from typing import Optional, List, Dict, Tuple, Any
from loguru import logger
import io
import re
import tempfile
import os

from ...utils.config import TTSConfig


class TTSEngine:
    """文本转语音引擎"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.engine = None
        self._initialized = False
        self._phoneme_cache = {}
        
        logger.info(f"TTS引擎初始化，后端: {config.engine}")

    async def initialize(self):
        """初始化TTS引擎"""
        if self._initialized:
            return
            
        try:
            if self.config.engine == "coqui":
                await self._init_coqui()
            elif self.config.engine == "espeak":
                await self._init_espeak()
            elif self.config.engine == "elevenlabs":
                await self._init_elevenlabs()
            elif self.config.engine == "azure":
                await self._init_azure()
            else:
                raise ValueError(f"不支持的TTS引擎: {self.config.engine}")
                
            self._initialized = True
            logger.info(f"TTS引擎初始化完成: {self.config.engine}")
            
        except Exception as e:
            logger.error(f"TTS引擎初始化失败: {e}")
            raise

    async def _init_coqui(self):
        """初始化Coqui TTS"""
        try:
            from TTS.api import TTS
            
            # 在线程池中初始化以避免阻塞
            loop = asyncio.get_event_loop()
            self.engine = await loop.run_in_executor(
                None,
                self._load_coqui_model
            )
            
        except ImportError:
            logger.error("Coqui TTS未安装，请运行: pip install TTS")
            raise
        except Exception as e:
            logger.error(f"Coqui TTS初始化失败: {e}")
            raise

    def _load_coqui_model(self):
        """加载Coqui TTS模型"""
        from TTS.api import TTS
        
        # 根据配置选择模型
        model_path = self.config.coqui.model_path
        
        # 检查是否是预训练模型名称
        if not os.path.exists(model_path):
            # 使用预训练模型
            tts = TTS(model_name=model_path)
        else:
            # 使用本地模型
            tts = TTS(model_path=model_path)
            
        return tts

    async def _init_espeak(self):
        """初始化eSpeak-ng"""
        try:
            import espeak
            self.engine = espeak
            
        except ImportError:
            logger.error("eSpeak库未安装")
            raise

    async def _init_elevenlabs(self):
        """初始化ElevenLabs"""
        try:
            import elevenlabs
            
            if not self.config.elevenlabs.api_key:
                raise ValueError("ElevenLabs API密钥未设置")
                
            elevenlabs.set_api_key(self.config.elevenlabs.api_key)
            self.engine = elevenlabs
            
        except ImportError:
            logger.error("ElevenLabs库未安装")
            raise

    async def _init_azure(self):
        """初始化Azure TTS"""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            if not self.config.azure.api_key or not self.config.azure.region:
                raise ValueError("Azure TTS配置不完整")
                
            speech_config = speechsdk.SpeechConfig(
                subscription=self.config.azure.api_key,
                region=self.config.azure.region
            )
            speech_config.speech_synthesis_voice_name = self.config.azure.voice_name
            
            self.engine = speechsdk.SpeechSynthesizer(speech_config=speech_config)
            
        except ImportError:
            logger.error("Azure Speech SDK未安装")
            raise

    async def synthesize(self, text: str) -> Optional[bytes]:
        """
        将文本合成为语音
        
        Args:
            text: 要合成的文本
            
        Returns:
            音频数据字节流，如果失败则返回None
        """
        if not self._initialized:
            logger.error("TTS引擎未初始化")
            return None
            
        if not text or text.strip() == "":
            logger.warning("输入文本为空")
            return None
            
        try:
            # 文本预处理
            processed_text = self._preprocess_text(text)
            
            if self.config.engine == "coqui":
                return await self._synthesize_coqui(processed_text)
            elif self.config.engine == "espeak":
                return await self._synthesize_espeak(processed_text)
            elif self.config.engine == "elevenlabs":
                return await self._synthesize_elevenlabs(processed_text)
            elif self.config.engine == "azure":
                return await self._synthesize_azure(processed_text)
            else:
                logger.error(f"不支持的TTS引擎: {self.config.engine}")
                return None
                
        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            return None

    async def _synthesize_coqui(self, text: str) -> Optional[bytes]:
        """使用Coqui TTS合成语音"""
        try:
            loop = asyncio.get_event_loop()
            
            # 在线程池中执行合成
            audio_data = await loop.run_in_executor(
                None,
                self._coqui_synthesize_sync,
                text
            )
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Coqui TTS合成失败: {e}")
            return None

    def _coqui_synthesize_sync(self, text: str) -> bytes:
        """Coqui TTS同步合成"""
        try:
            # 生成音频
            if self.config.coqui.speaker_wav:
                # 使用说话者音频进行声音克隆
                audio_array = self.engine.tts(
                    text=text,
                    speaker_wav=self.config.coqui.speaker_wav
                )
            else:
                # 使用默认声音
                audio_array = self.engine.tts(text=text)
            
            # 转换为字节流
            if isinstance(audio_array, np.ndarray):
                # 确保是16位整数格式
                if audio_array.dtype != np.int16:
                    audio_array = (audio_array * 32767).astype(np.int16)
                return audio_array.tobytes()
            else:
                logger.error("Coqui TTS返回了意外的音频格式")
                return b""
                
        except Exception as e:
            logger.error(f"Coqui TTS同步合成失败: {e}")
            return b""

    async def _synthesize_espeak(self, text: str) -> Optional[bytes]:
        """使用eSpeak合成语音"""
        try:
            loop = asyncio.get_event_loop()
            
            audio_data = await loop.run_in_executor(
                None,
                self._espeak_synthesize_sync,
                text
            )
            
            return audio_data
            
        except Exception as e:
            logger.error(f"eSpeak合成失败: {e}")
            return None

    def _espeak_synthesize_sync(self, text: str) -> bytes:
        """eSpeak同步合成"""
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # 使用eSpeak命令行工具
            import subprocess
            
            cmd = [
                'espeak-ng',
                '-s', str(int(self.config.speed * 175)),  # 语速
                '-v', self.config.voice,
                '-w', tmp_path,
                text
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # 读取生成的音频文件
            with open(tmp_path, 'rb') as f:
                audio_data = f.read()
            
            # 清理临时文件
            os.unlink(tmp_path)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"eSpeak同步合成失败: {e}")
            return b""

    async def _synthesize_elevenlabs(self, text: str) -> Optional[bytes]:
        """使用ElevenLabs合成语音"""
        try:
            loop = asyncio.get_event_loop()
            
            audio_data = await loop.run_in_executor(
                None,
                self._elevenlabs_synthesize_sync,
                text
            )
            
            return audio_data
            
        except Exception as e:
            logger.error(f"ElevenLabs合成失败: {e}")
            return None

    def _elevenlabs_synthesize_sync(self, text: str) -> bytes:
        """ElevenLabs同步合成"""
        try:
            audio = self.engine.generate(
                text=text,
                voice=self.config.elevenlabs.voice_id,
                model="eleven_multilingual_v2"
            )
            
            # 将生成器转换为字节
            audio_bytes = b"".join(audio)
            return audio_bytes
            
        except Exception as e:
            logger.error(f"ElevenLabs同步合成失败: {e}")
            return b""

    async def _synthesize_azure(self, text: str) -> Optional[bytes]:
        """使用Azure TTS合成语音"""
        try:
            loop = asyncio.get_event_loop()
            
            audio_data = await loop.run_in_executor(
                None,
                self._azure_synthesize_sync,
                text
            )
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Azure TTS合成失败: {e}")
            return None

    def _azure_synthesize_sync(self, text: str) -> bytes:
        """Azure TTS同步合成"""
        try:
            result = self.engine.speak_text_async(text).get()
            
            if result.reason == result.reason.SynthesizingAudioCompleted:
                return result.audio_data
            else:
                logger.error(f"Azure TTS合成失败: {result.reason}")
                return b""
                
        except Exception as e:
            logger.error(f"Azure TTS同步合成失败: {e}")
            return b""

    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 移除特殊标记
        text = re.sub(r'\[EMOTION:\w+\]', '', text)
        
        # 替换常见缩写
        text = text.replace("&", "和")
        text = text.replace("@", "at")
        text = text.replace("#", "hashtag")
        
        # 处理数字
        # 这里可以添加数字到文字的转换
        
        # 处理标点符号
        text = re.sub(r'[^\w\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff,.!?;:]', '', text)
        
        return text.strip()

    async def get_phonemes(self, text: str) -> List[Tuple[str, float]]:
        """
        获取文本的音素信息，用于口型同步
        
        Returns:
            [(phoneme, duration), ...] 音素和持续时间的列表
        """
        try:
            # 检查缓存
            if text in self._phoneme_cache:
                return self._phoneme_cache[text]
            
            # 这里实现音素提取逻辑
            # 可以使用专门的音素提取库，如montreal-forced-alignment
            phonemes = await self._extract_phonemes(text)
            
            # 缓存结果
            self._phoneme_cache[text] = phonemes
            
            return phonemes
            
        except Exception as e:
            logger.error(f"音素提取失败: {e}")
            return []

    async def _extract_phonemes(self, text: str) -> List[Tuple[str, float]]:
        """提取音素（简化实现）"""
        # 这是一个简化的实现，实际应用中需要使用专业的音素提取工具
        words = text.split()
        phonemes = []
        
        for word in words:
            # 简单估算每个单词的持续时间
            duration = len(word) * 0.1  # 每个字符100ms
            phonemes.append((word, duration))
        
        return phonemes

    async def get_supported_voices(self) -> List[str]:
        """获取支持的声音列表"""
        if self.config.engine == "coqui":
            return ["en_custom_1", "en_custom_2", "zh_custom"]
        elif self.config.engine == "espeak":
            return ["en", "zh", "en+f3", "en+m3"]
        elif self.config.engine == "elevenlabs":
            # 这里需要调用ElevenLabs API获取声音列表
            return ["voice1", "voice2"]
        elif self.config.engine == "azure":
            return ["zh-CN-XiaoxiaoNeural", "en-US-AriaNeural"]
        else:
            return []

    def update_config(self, **kwargs):
        """动态更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"TTS配置更新: {key} = {value}")

    async def test_synthesis(self) -> bool:
        """测试TTS功能"""
        try:
            test_text = "这是一个测试。" if self.config.voice.startswith("zh") else "This is a test."
            audio_data = await self.synthesize(test_text)
            
            if audio_data and len(audio_data) > 0:
                logger.info("TTS测试成功")
                return True
            else:
                logger.warning("TTS测试失败：没有生成音频")
                return False
                
        except Exception as e:
            logger.error(f"TTS测试失败: {e}")
            return False

    async def cleanup(self):
        """清理资源"""
        try:
            if self.engine:
                # 根据不同引擎进行相应的清理
                if hasattr(self.engine, 'cleanup'):
                    await self.engine.cleanup()
                    
            self._phoneme_cache.clear()
            self._initialized = False
            
            logger.info("TTS引擎资源已清理")
            
        except Exception as e:
            logger.error(f"TTS引擎清理失败: {e}")

    def get_engine_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            "engine": self.config.engine,
            "voice": self.config.voice,
            "speed": self.config.speed,
            "sample_rate": self.config.sample_rate,
            "initialized": self._initialized,
            "cache_size": len(self._phoneme_cache)
        } 