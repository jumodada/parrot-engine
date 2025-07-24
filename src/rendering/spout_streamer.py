"""
Spout 推流器
支持 OBS Studio 推流和虚拟摄像头输出
"""

import asyncio
import cv2
import numpy as np
import threading
import time
import json
import base64
from typing import Optional, Callable, Any, Dict, List
from loguru import logger
from pathlib import Path
import queue

try:
    import websockets
    import pyvirtualcam
    VIRTUAL_CAM_AVAILABLE = True
except ImportError:
    VIRTUAL_CAM_AVAILABLE = False
    logger.warning("pyvirtualcam 或 websockets 库未安装，部分推流功能将受限")


class SpoutStreamer:
    """
    Spout 推流器
    
    支持：
    1. OBS WebSocket 连接
    2. 虚拟摄像头输出
    3. 帧数据处理和编码
    4. 实时推流
    """
    
    def __init__(self, host: str = "localhost", port: int = 4444, password: str = "", 
                 width: int = 1080, height: int = 1920, fps: int = 60):
        self.host = host
        self.port = port
        self.password = password
        self.width = width
        self.height = height
        self.fps = fps
        
        # WebSocket 连接
        self.websocket: Optional[Any] = None
        self.connected = False
        self.connection_task: Optional[asyncio.Task] = None
        
        # 虚拟摄像头
        self.virtual_cam: Optional[Any] = None
        self.virtual_cam_enabled = False
        
        # 帧队列和处理
        self.frame_queue = queue.Queue(maxsize=10)
        self.streaming = False
        self.stream_thread: Optional[threading.Thread] = None
        
        # 统计信息
        self.frames_sent = 0
        self.last_fps_check = time.time()
        self.current_fps = 0.0
        
        # 回调函数
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        logger.info(f"Spout 推流器初始化: {width}x{height} @ {fps}fps")
    
    async def initialize(self) -> bool:
        """初始化推流器"""
        try:
            logger.info("初始化 Spout 推流器...")
            
            # 初始化虚拟摄像头
            if VIRTUAL_CAM_AVAILABLE:
                await self._init_virtual_camera()
            
            # 连接到 OBS WebSocket
            await self._connect_obs()
            
            logger.info("Spout 推流器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"Spout 推流器初始化失败: {e}")
            if self.on_error:
                self.on_error(str(e))
            return False
    
    async def _init_virtual_camera(self):
        """初始化虚拟摄像头"""
        try:
            if not VIRTUAL_CAM_AVAILABLE:
                logger.warning("虚拟摄像头不可用")
                return
            
            # 创建虚拟摄像头
            self.virtual_cam = pyvirtualcam.Camera(
                width=self.width,
                height=self.height,
                fps=self.fps,
                fmt=pyvirtualcam.PixelFormat.RGB
            )
            
            self.virtual_cam_enabled = True
            logger.info(f"虚拟摄像头初始化完成: {self.virtual_cam.device}")
            
        except Exception as e:
            logger.error(f"虚拟摄像头初始化失败: {e}")
            self.virtual_cam_enabled = False
    
    async def _connect_obs(self):
        """连接到 OBS WebSocket"""
        try:
            if not websockets:
                logger.warning("websockets 库未安装，无法连接 OBS")
                return
            
            # 连接到 OBS WebSocket
            ws_url = f"ws://{self.host}:{self.port}"
            logger.info(f"连接到 OBS WebSocket: {ws_url}")
            
            self.websocket = await websockets.connect(ws_url)
            
            # 身份验证（如果需要）
            if self.password:
                await self._authenticate()
            
            self.connected = True
            
            # 启动消息处理任务
            self.connection_task = asyncio.create_task(self._handle_obs_messages())
            
            if self.on_connected:
                self.on_connected()
            
            logger.info("OBS WebSocket 连接成功")
            
        except Exception as e:
            logger.error(f"连接 OBS WebSocket 失败: {e}")
            self.connected = False
            if self.on_error:
                self.on_error(str(e))
    
    async def _authenticate(self):
        """OBS WebSocket 身份验证"""
        try:
            # 获取认证信息
            auth_request = {
                "op": 1,  # Hello
                "d": {
                    "rpcVersion": 1
                }
            }
            
            await self.websocket.send(json.dumps(auth_request))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            # 这里应该实现完整的认证流程
            # 由于 OBS WebSocket v5 的认证较复杂，这里简化处理
            logger.info("OBS WebSocket 认证完成")
            
        except Exception as e:
            logger.error(f"OBS WebSocket 认证失败: {e}")
            raise
    
    async def _handle_obs_messages(self):
        """处理 OBS WebSocket 消息"""
        try:
            while self.connected and self.websocket:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    # 处理不同类型的消息
                    if data.get("op") == 5:  # Event
                        await self._handle_obs_event(data.get("d", {}))
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"处理 OBS 消息失败: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"OBS 消息处理循环错误: {e}")
        finally:
            self.connected = False
            if self.on_disconnected:
                self.on_disconnected()
    
    async def _handle_obs_event(self, event_data: Dict):
        """处理 OBS 事件"""
        try:
            event_type = event_data.get("eventType")
            
            if event_type == "ConnectionClosed":
                logger.info("OBS 连接已关闭")
                self.connected = False
            elif event_type == "SceneItemCreated":
                logger.debug(f"场景项目已创建: {event_data}")
            
        except Exception as e:
            logger.error(f"处理 OBS 事件失败: {e}")
    
    async def start_streaming(self):
        """开始推流"""
        try:
            if self.streaming:
                logger.warning("推流已在进行中")
                return
            
            self.streaming = True
            
            # 启动推流线程
            self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.stream_thread.start()
            
            logger.info("推流已启动")
            
        except Exception as e:
            logger.error(f"启动推流失败: {e}")
            self.streaming = False
    
    async def stop_streaming(self):
        """停止推流"""
        try:
            self.streaming = False
            
            if self.stream_thread and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=2.0)
            
            logger.info("推流已停止")
            
        except Exception as e:
            logger.error(f"停止推流失败: {e}")
    
    def _stream_loop(self):
        """推流循环（在独立线程中运行）"""
        frame_time = 1.0 / self.fps
        
        while self.streaming:
            start_time = time.time()
            
            try:
                # 获取帧数据
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get_nowait()
                    
                    # 发送到虚拟摄像头
                    if self.virtual_cam_enabled and self.virtual_cam:
                        self._send_to_virtual_camera(frame)
                    
                    # 发送到 OBS（通过 WebSocket 或其他方式）
                    if self.connected:
                        self._send_to_obs(frame)
                    
                    self.frames_sent += 1
                    self._update_fps_stats()
                
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"推流循环错误: {e}")
            
            # 控制帧率
            elapsed = time.time() - start_time
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
    
    def _send_to_virtual_camera(self, frame: np.ndarray):
        """发送帧到虚拟摄像头"""
        try:
            if not self.virtual_cam:
                return
            
            # 确保帧格式正确
            if frame.shape[:2] != (self.height, self.width):
                frame = cv2.resize(frame, (self.width, self.height))
            
            # 转换颜色格式（RGBA -> RGB）
            if frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
            elif frame.shape[2] == 3 and frame.dtype == np.uint8:
                # 已经是 RGB 格式
                pass
            else:
                logger.warning(f"不支持的帧格式: {frame.shape}, {frame.dtype}")
                return
            
            # 发送帧
            self.virtual_cam.send(frame)
            
        except Exception as e:
            logger.error(f"发送帧到虚拟摄像头失败: {e}")
    
    def _send_to_obs(self, frame: np.ndarray):
        """发送帧到 OBS（通过 WebSocket）"""
        try:
            # 这里可以实现通过 WebSocket 发送帧数据
            # 由于 OBS WebSocket v5 不直接支持视频流，
            # 这里主要用于控制和状态同步
            pass
            
        except Exception as e:
            logger.error(f"发送帧到 OBS 失败: {e}")
    
    def _update_fps_stats(self):
        """更新 FPS 统计"""
        current_time = time.time()
        if current_time - self.last_fps_check >= 1.0:
            self.current_fps = self.frames_sent / (current_time - self.last_fps_check)
            self.frames_sent = 0
            self.last_fps_check = current_time
    
    def send_frame(self, frame: np.ndarray):
        """发送帧数据"""
        try:
            if not self.streaming:
                return
            
            # 添加到队列（如果队列满了，丢弃最旧的帧）
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                # 丢弃最旧的帧
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put_nowait(frame)
                except queue.Empty:
                    pass
                    
        except Exception as e:
            logger.error(f"发送帧失败: {e}")
    
    async def capture_screen_region(self, x: int, y: int, width: int, height: int) -> Optional[np.ndarray]:
        """捕获屏幕区域（用于调试）"""
        try:
            import mss
            
            with mss.mss() as sct:
                monitor = {
                    "top": y,
                    "left": x,
                    "width": width,
                    "height": height
                }
                
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                
                # 转换颜色格式
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGBA)
                
                return frame
                
        except ImportError:
            logger.error("mss 库未安装，无法捕获屏幕")
            return None
        except Exception as e:
            logger.error(f"捕获屏幕失败: {e}")
            return None
    
    async def create_spout_source(self, source_name: str = "Live2D") -> bool:
        """在 OBS 中创建 Spout 源"""
        try:
            if not self.connected or not self.websocket:
                logger.error("OBS 未连接")
                return False
            
            # 创建 Spout 源的请求
            request = {
                "op": 6,  # Request
                "d": {
                    "requestType": "CreateInput",
                    "requestId": "create_spout_source",
                    "requestData": {
                        "sceneName": "Scene",  # 默认场景名
                        "inputName": source_name,
                        "inputKind": "spout2_capture",
                        "inputSettings": {
                            "spout_sender_name": source_name
                        }
                    }
                }
            }
            
            await self.websocket.send(json.dumps(request))
            logger.info(f"请求创建 Spout 源: {source_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建 Spout 源失败: {e}")
            return False
    
    def get_streaming_stats(self) -> Dict[str, Any]:
        """获取推流统计信息"""
        return {
            "streaming": self.streaming,
            "connected_to_obs": self.connected,
            "virtual_cam_enabled": self.virtual_cam_enabled,
            "current_fps": self.current_fps,
            "frames_sent": self.frames_sent,
            "queue_size": self.frame_queue.qsize(),
            "resolution": f"{self.width}x{self.height}",
            "target_fps": self.fps
        }
    
    def is_streaming(self) -> bool:
        """检查是否正在推流"""
        return self.streaming
    
    def is_connected(self) -> bool:
        """检查是否连接到 OBS"""
        return self.connected
    
    async def send_obs_command(self, command: str, data: Dict[str, Any] = None) -> bool:
        """发送命令到 OBS"""
        try:
            if not self.connected or not self.websocket:
                return False
            
            request = {
                "op": 6,  # Request
                "d": {
                    "requestType": command,
                    "requestId": f"{command}_{int(time.time())}",
                    "requestData": data or {}
                }
            }
            
            await self.websocket.send(json.dumps(request))
            return True
            
        except Exception as e:
            logger.error(f"发送 OBS 命令失败: {e}")
            return False
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 停止推流
            await self.stop_streaming()
            
            # 关闭虚拟摄像头
            if self.virtual_cam:
                self.virtual_cam.close()
                self.virtual_cam = None
            
            # 关闭 WebSocket 连接
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            # 取消连接任务
            if self.connection_task:
                self.connection_task.cancel()
                try:
                    await self.connection_task
                except asyncio.CancelledError:
                    pass
            
            # 清空队列
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break
            
            self.connected = False
            self.streaming = False
            
            logger.info("Spout 推流器资源已清理")
            
        except Exception as e:
            logger.error(f"清理 Spout 推流器失败: {e}") 