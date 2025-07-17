"""
音频管理器
负责音频输入输出、录制和播放功能
"""

import asyncio
import numpy as np
import pyaudio
import threading
import queue
from typing import Optional, Callable, List
from loguru import logger
import time
import wave
import io

from ...utils.config import AudioConfig, MicrophoneConfig


class AudioManager:
    """音频管理器"""
    
    def __init__(self, audio_config: AudioConfig, microphone_config: Optional[MicrophoneConfig] = None):
        self.audio_config = audio_config
        self.microphone_config = microphone_config or MicrophoneConfig()
        
        # PyAudio实例
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        
        # 输入流
        self.input_stream: Optional[pyaudio.Stream] = None
        self.recording = False
        self.audio_queue = queue.Queue()
        
        # 输出流
        self.output_stream: Optional[pyaudio.Stream] = None
        self.playing = False
        
        # 线程控制
        self._input_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 回调函数
        self.on_audio_data: Optional[Callable[[bytes], None]] = None
        
        logger.info("音频管理器初始化")

    async def initialize(self):
        """初始化音频管理器"""
        try:
            # 初始化PyAudio
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # 列出可用的音频设备
            self._list_audio_devices()
            
            # 初始化输入流
            await self._init_input_stream()
            
            # 初始化输出流
            await self._init_output_stream()
            
            logger.info("音频管理器初始化完成")
            
        except Exception as e:
            logger.error(f"音频管理器初始化失败: {e}")
            raise

    def _list_audio_devices(self):
        """列出可用的音频设备"""
        if not self.pyaudio_instance:
            return
            
        try:
            logger.info("可用音频设备:")
            for i in range(self.pyaudio_instance.get_device_count()):
                device_info = self.pyaudio_instance.get_device_info_by_index(i)
                logger.info(f"  {i}: {device_info['name']} - "
                           f"输入: {device_info['maxInputChannels']}, "
                           f"输出: {device_info['maxOutputChannels']}")
                           
        except Exception as e:
            logger.error(f"列出音频设备失败: {e}")

    async def _init_input_stream(self):
        """初始化音频输入流"""
        if not self.pyaudio_instance:
            raise RuntimeError("PyAudio未初始化")
            
        try:
            # 获取输入设备
            input_device_index = self._get_input_device_index()
            
            # 创建输入流
            self.input_stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=self.microphone_config.channels,
                rate=self.microphone_config.sample_rate,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=self.microphone_config.chunk_size,
                stream_callback=self._input_callback
            )
            
            logger.info(f"音频输入流初始化完成，设备: {input_device_index}")
            
        except Exception as e:
            logger.error(f"音频输入流初始化失败: {e}")
            raise

    async def _init_output_stream(self):
        """初始化音频输出流"""
        if not self.pyaudio_instance:
            raise RuntimeError("PyAudio未初始化")
            
        try:
            # 获取输出设备
            output_device_index = self._get_output_device_index()
            
            # 创建输出流
            self.output_stream = self.pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=1,  # 单声道输出
                rate=self.audio_config.sample_rate,
                output=True,
                output_device_index=output_device_index,
                frames_per_buffer=self.audio_config.buffer_size
            )
            
            logger.info(f"音频输出流初始化完成，设备: {output_device_index}")
            
        except Exception as e:
            logger.error(f"音频输出流初始化失败: {e}")
            raise

    def _get_input_device_index(self) -> Optional[int]:
        """获取输入设备索引"""
        if not self.pyaudio_instance:
            return None
            
        try:
            # 如果指定了设备名称，寻找匹配的设备
            if self.microphone_config.device_name:
                for i in range(self.pyaudio_instance.get_device_count()):
                    device_info = self.pyaudio_instance.get_device_info_by_index(i)
                    if (self.microphone_config.device_name.lower() in device_info['name'].lower() and
                        device_info['maxInputChannels'] > 0):
                        return i
                        
                logger.warning(f"未找到指定的输入设备: {self.microphone_config.device_name}")
            
            # 使用默认输入设备
            default_device = self.pyaudio_instance.get_default_input_device_info()
            return default_device['index']
            
        except Exception as e:
            logger.error(f"获取输入设备失败: {e}")
            return None

    def _get_output_device_index(self) -> Optional[int]:
        """获取输出设备索引"""
        if not self.pyaudio_instance:
            return None
            
        try:
            # 如果指定了设备名称，寻找匹配的设备
            if self.audio_config.output_device:
                for i in range(self.pyaudio_instance.get_device_count()):
                    device_info = self.pyaudio_instance.get_device_info_by_index(i)
                    if (self.audio_config.output_device.lower() in device_info['name'].lower() and
                        device_info['maxOutputChannels'] > 0):
                        return i
                        
                logger.warning(f"未找到指定的输出设备: {self.audio_config.output_device}")
            
            # 使用默认输出设备
            default_device = self.pyaudio_instance.get_default_output_device_info()
            return default_device['index']
            
        except Exception as e:
            logger.error(f"获取输出设备失败: {e}")
            return None

    def _input_callback(self, in_data, frame_count, time_info, status):
        """音频输入回调"""
        if self.recording and in_data:
            try:
                # 将音频数据放入队列
                self.audio_queue.put(in_data)
                
                # 触发回调
                if self.on_audio_data:
                    self.on_audio_data(in_data)
                    
            except Exception as e:
                logger.error(f"音频输入回调错误: {e}")
        
        return (in_data, pyaudio.paContinue)

    async def start_recording(self):
        """开始录音"""
        if not self.input_stream:
            logger.error("音频输入流未初始化")
            return
            
        try:
            if not self.recording:
                self.recording = True
                self.input_stream.start_stream()
                logger.info("开始录音")
                
        except Exception as e:
            logger.error(f"开始录音失败: {e}")

    async def stop_recording(self):
        """停止录音"""
        if not self.input_stream:
            return
            
        try:
            if self.recording:
                self.recording = False
                self.input_stream.stop_stream()
                logger.info("停止录音")
                
        except Exception as e:
            logger.error(f"停止录音失败: {e}")

    async def capture_audio(self, duration: float = 1.0) -> Optional[bytes]:
        """
        捕获指定时长的音频
        
        Args:
            duration: 录音时长（秒）
            
        Returns:
            音频数据字节流
        """
        try:
            # 清空队列
            while not self.audio_queue.empty():
                self.audio_queue.get()
            
            # 开始录音
            await self.start_recording()
            
            # 等待指定时长
            await asyncio.sleep(duration)
            
            # 停止录音
            await self.stop_recording()
            
            # 收集音频数据
            audio_data = b""
            while not self.audio_queue.empty():
                chunk = self.audio_queue.get()
                audio_data += chunk
            
            return audio_data if audio_data else None
            
        except Exception as e:
            logger.error(f"捕获音频失败: {e}")
            return None

    async def get_audio_chunk(self, timeout: float = 0.1) -> Optional[bytes]:
        """
        获取一个音频块
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            音频数据块
        """
        try:
            loop = asyncio.get_event_loop()
            chunk = await loop.run_in_executor(
                None,
                lambda: self.audio_queue.get(timeout=timeout) if not self.audio_queue.empty() else None
            )
            return chunk
            
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"获取音频块失败: {e}")
            return None

    async def play_audio(self, audio_data: bytes):
        """
        播放音频数据
        
        Args:
            audio_data: 音频数据字节流
        """
        if not self.output_stream or not audio_data:
            return
            
        try:
            self.playing = True
            
            # 在线程池中播放音频以避免阻塞
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._play_audio_sync, audio_data)
            
            self.playing = False
            logger.debug("音频播放完成")
            
        except Exception as e:
            logger.error(f"音频播放失败: {e}")
            self.playing = False

    def _play_audio_sync(self, audio_data: bytes):
        """同步播放音频"""
        try:
            if not self.output_stream:
                return
                
            # 调整音量
            if self.audio_config.volume != 1.0:
                # 转换为numpy数组进行音量调整
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                audio_array = (audio_array * self.audio_config.volume).astype(np.int16)
                audio_data = audio_array.tobytes()
            
            # 分块播放
            chunk_size = self.audio_config.buffer_size * 2  # 16位=2字节
            for i in range(0, len(audio_data), chunk_size):
                if not self.playing:
                    break
                chunk = audio_data[i:i + chunk_size]
                self.output_stream.write(chunk)
                
        except Exception as e:
            logger.error(f"同步音频播放失败: {e}")

    async def play_audio_file(self, file_path: str):
        """播放音频文件"""
        try:
            with wave.open(file_path, 'rb') as wf:
                audio_data = wf.readframes(wf.getnframes())
                await self.play_audio(audio_data)
                
        except Exception as e:
            logger.error(f"播放音频文件失败: {e}")

    async def save_audio(self, audio_data: bytes, file_path: str):
        """保存音频数据到文件"""
        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(self.microphone_config.channels)
                wf.setsampwidth(self.pyaudio_instance.get_sample_size(pyaudio.paInt16) if self.pyaudio_instance else 2)
                wf.setframerate(self.microphone_config.sample_rate)
                wf.writeframes(audio_data)
                
            logger.info(f"音频已保存到: {file_path}")
            
        except Exception as e:
            logger.error(f"保存音频失败: {e}")

    def get_audio_level(self, audio_data: bytes) -> float:
        """获取音频电平"""
        try:
            # 转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # 计算RMS
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            
            # 归一化到0-1范围
            max_level = 32768.0  # 16位音频的最大值
            normalized_level = min(rms / max_level, 1.0)
            
            return normalized_level
            
        except Exception as e:
            logger.error(f"计算音频电平失败: {e}")
            return 0.0

    def is_recording(self) -> bool:
        """检查是否正在录音"""
        return self.recording

    def is_playing(self) -> bool:
        """检查是否正在播放"""
        return self.playing

    async def get_device_list(self) -> List[dict]:
        """获取音频设备列表"""
        devices = []
        
        if not self.pyaudio_instance:
            return devices
            
        try:
            for i in range(self.pyaudio_instance.get_device_count()):
                device_info = self.pyaudio_instance.get_device_info_by_index(i)
                devices.append({
                    "index": i,
                    "name": device_info["name"],
                    "max_input_channels": device_info["maxInputChannels"],
                    "max_output_channels": device_info["maxOutputChannels"],
                    "default_sample_rate": device_info["defaultSampleRate"]
                })
                
        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            
        return devices

    async def test_audio_io(self) -> bool:
        """测试音频输入输出"""
        try:
            logger.info("开始音频I/O测试...")
            
            # 测试录音
            await self.start_recording()
            await asyncio.sleep(2.0)  # 录2秒
            await self.stop_recording()
            
            # 收集录音数据
            audio_data = b""
            while not self.audio_queue.empty():
                chunk = self.audio_queue.get()
                audio_data += chunk
            
            if not audio_data:
                logger.error("录音测试失败：没有捕获到音频")
                return False
            
            # 测试播放
            await self.play_audio(audio_data)
            
            logger.info("音频I/O测试成功")
            return True
            
        except Exception as e:
            logger.error(f"音频I/O测试失败: {e}")
            return False

    async def cleanup(self):
        """清理资源"""
        try:
            # 停止录音和播放
            await self.stop_recording()
            self.playing = False
            
            # 关闭流
            if self.input_stream:
                self.input_stream.stop_stream()
                self.input_stream.close()
                self.input_stream = None
                
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
                self.output_stream = None
            
            # 终止PyAudio
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
                self.pyaudio_instance = None
            
            # 清空队列
            while not self.audio_queue.empty():
                self.audio_queue.get()
            
            logger.info("音频管理器资源已清理")
            
        except Exception as e:
            logger.error(f"音频管理器清理失败: {e}")

    def update_volume(self, volume: float):
        """更新音量"""
        self.audio_config.volume = max(0.0, min(1.0, volume))
        logger.info(f"音量更新为: {self.audio_config.volume}")

    def get_audio_info(self) -> dict:
        """获取音频信息"""
        return {
            "recording": self.recording,
            "playing": self.playing,
            "input_sample_rate": self.microphone_config.sample_rate,
            "output_sample_rate": self.audio_config.sample_rate,
            "input_channels": self.microphone_config.channels,
            "volume": self.audio_config.volume,
            "buffer_size": self.audio_config.buffer_size
        } 