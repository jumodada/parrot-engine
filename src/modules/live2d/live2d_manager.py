"""
Live2D管理器
负责加载Live2D模型、动画控制和渲染
"""

import asyncio
import json
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from loguru import logger
import time
import threading
from pathlib import Path

from ...utils.config import Live2DConfig


class Live2DManager:
    """Live2D管理器"""
    
    def __init__(self, config: Live2DConfig):
        self.config = config
        self._initialized = False
        
        # 模型相关
        self.model_data: Optional[Dict] = None
        self.model_path: Optional[Path] = None
        
        # 动画状态
        self.current_emotion = "neutral"
        self.current_motion = None
        self.is_speaking = False
        self.last_blink_time = time.time()
        
        # 参数映射
        self.parameter_map = {
            # 基础参数
            "ParamAngleX": 0.0,  # 头部左右转动
            "ParamAngleY": 0.0,  # 头部上下转动
            "ParamAngleZ": 0.0,  # 头部倾斜
            "ParamEyeLOpen": 1.0,  # 左眼开合
            "ParamEyeROpen": 1.0,  # 右眼开合
            "ParamEyeBallX": 0.0,  # 眼球X轴
            "ParamEyeBallY": 0.0,  # 眼球Y轴
            "ParamMouthOpenY": 0.0,  # 嘴巴开合
            "ParamMouthForm": 0.0,  # 嘴形
            "ParamBodyAngleX": 0.0,  # 身体X轴
            "ParamBodyAngleY": 0.0,  # 身体Y轴
            "ParamBodyAngleZ": 0.0,  # 身体Z轴
            "ParamBreath": 0.0,  # 呼吸
        }
        
        # 表情映射
        self.emotion_params = {
            "happy": {
                "ParamMouthForm": 1.0,
                "ParamEyeForm": 1.0
            },
            "sad": {
                "ParamMouthForm": -0.8,
                "ParamEyeForm": -0.5
            },
            "surprised": {
                "ParamMouthOpenY": 0.8,
                "ParamEyeLOpen": 1.2,
                "ParamEyeROpen": 1.2
            },
            "angry": {
                "ParamMouthForm": -0.5,
                "ParamEyeForm": -1.0,
                "ParamEyebrowForm": -1.0
            },
            "thinking": {
                "ParamAngleY": 10.0,
                "ParamEyeBallX": 0.3
            },
            "shy": {
                "ParamAngleY": -15.0,
                "ParamMouthForm": 0.3
            }
        }
        
        # 动画控制
        self._animation_lock = threading.Lock()
        self._update_task: Optional[asyncio.Task] = None
        
        logger.info(f"Live2D管理器初始化，模型: {config.model_name}")

    async def initialize(self):
        """初始化Live2D管理器"""
        if self._initialized:
            return
            
        try:
            # 验证模型路径
            self.model_path = Path(self.config.model_path)
            if not self.model_path.exists():
                logger.warning(f"Live2D模型路径不存在: {self.model_path}")
                # 创建占位符数据
                self._create_placeholder_model()
            else:
                # 加载模型数据
                await self._load_model()
            
            # 启动更新循环
            self._update_task = asyncio.create_task(self._update_loop())
            
            self._initialized = True
            logger.info("Live2D管理器初始化完成")
            
        except Exception as e:
            logger.error(f"Live2D管理器初始化失败: {e}")
            raise

    def _create_placeholder_model(self):
        """创建占位符模型数据"""
        self.model_data = {
            "name": self.config.model_name,
            "version": "placeholder",
            "parameters": list(self.parameter_map.keys()),
            "parts": ["Head", "Body", "LeftEye", "RightEye", "Mouth"],
            "motions": {
                "idle": ["idle_01", "idle_02"],
                "happy": ["happy_01"],
                "sad": ["sad_01"]
            }
        }
        logger.info("已创建占位符Live2D模型数据")

    async def _load_model(self):
        """加载Live2D模型"""
        try:
            # 确保model_path存在且不为None
            if not self.model_path or not self.model_path.exists():
                logger.warning(f"模型路径不存在或无效: {self.model_path}")
                self._create_placeholder_model()
                return
            
            # 查找model3.json文件
            model_files = list(self.model_path.glob("*.model3.json"))
            if not model_files:
                logger.warning("未找到model3.json文件，使用占位符")
                self._create_placeholder_model()
                return
            
            model_file = model_files[0]
            
            # 在线程池中加载模型文件
            loop = asyncio.get_event_loop()
            model_data = await loop.run_in_executor(
                None, 
                self._load_model_file, 
                model_file
            )
            
            self.model_data = model_data
            logger.info(f"Live2D模型加载完成: {model_file.name}")
            
        except Exception as e:
            logger.error(f"Live2D模型加载失败: {e}")
            self._create_placeholder_model()

    def _load_model_file(self, model_file: Path) -> Dict:
        """在后台线程中加载模型文件"""
        try:
            with open(model_file, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
            
            # 解析模型信息
            parsed_data = {
                "name": model_data.get("FileReferences", {}).get("Moc", "unknown"),
                "version": model_data.get("Version", 3),
                "parameters": [],
                "parts": [],
                "motions": {}
            }
            
            # 提取参数信息
            if "Groups" in model_data:
                for group in model_data["Groups"]:
                    if "Ids" in group:
                        parsed_data["parameters"].extend(group["Ids"])
            
            # 提取动作信息
            if "FileReferences" in model_data and "Motions" in model_data["FileReferences"]:
                motions = model_data["FileReferences"]["Motions"]
                for motion_type, motion_list in motions.items():
                    parsed_data["motions"][motion_type] = [
                        motion.get("File", "") for motion in motion_list
                    ]
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"解析模型文件失败: {e}")
            return {}

    async def _update_loop(self):
        """模型更新循环"""
        logger.info("Live2D更新循环开始")
        
        try:
            while self._initialized:
                # 更新呼吸动画
                self._update_breathing()
                
                # 更新眨眼动画
                self._update_blinking()
                
                # 更新物理效果
                self._update_physics()
                
                # 等待下一帧
                await asyncio.sleep(1.0 / 60.0)  # 60FPS
                
        except asyncio.CancelledError:
            logger.info("Live2D更新循环被取消")
        except Exception as e:
            logger.error(f"Live2D更新循环出错: {e}")

    def _update_breathing(self):
        """更新呼吸动画"""
        try:
            # 简单的呼吸动画
            current_time = time.time()
            breath_cycle = 3.0  # 3秒一个呼吸周期
            breath_phase = (current_time % breath_cycle) / breath_cycle * 2 * np.pi
            breath_value = np.sin(breath_phase) * 0.1
            
            with self._animation_lock:
                self.parameter_map["ParamBreath"] = breath_value
                
        except Exception as e:
            logger.error(f"更新呼吸动画失败: {e}")

    def _update_blinking(self):
        """更新眨眼动画"""
        try:
            current_time = time.time()
            
            # 检查是否应该眨眼
            if current_time - self.last_blink_time > self.config.animation.idle_blink_interval:
                # 执行眨眼动画
                blink_progress = (current_time - self.last_blink_time - self.config.animation.idle_blink_interval) / 0.15
                
                if blink_progress <= 1.0:
                    # 眨眼中
                    blink_value = 1.0 - (np.sin(blink_progress * np.pi) * 0.8)
                    
                    with self._animation_lock:
                        self.parameter_map["ParamEyeLOpen"] = blink_value
                        self.parameter_map["ParamEyeROpen"] = blink_value
                else:
                    # 眨眼完成，重置时间
                    self.last_blink_time = current_time + np.random.uniform(1.0, 3.0)
                    
                    with self._animation_lock:
                        self.parameter_map["ParamEyeLOpen"] = 1.0
                        self.parameter_map["ParamEyeROpen"] = 1.0
                        
        except Exception as e:
            logger.error(f"更新眨眼动画失败: {e}")

    def _update_physics(self):
        """更新物理效果（简化实现）"""
        try:
            # 简单的头发摆动效果
            current_time = time.time()
            sway_phase = current_time * 0.5
            sway_value = np.sin(sway_phase) * 2.0
            
            with self._animation_lock:
                self.parameter_map["ParamAngleZ"] = sway_value
                
        except Exception as e:
            logger.error(f"更新物理效果失败: {e}")

    async def set_emotion(self, emotion: str):
        """
        设置表情
        
        Args:
            emotion: 表情名称（happy, sad, surprised, angry, thinking, shy）
        """
        if emotion not in self.emotion_params:
            logger.warning(f"未知的表情: {emotion}")
            return
            
        try:
            self.current_emotion = emotion
            emotion_data = self.emotion_params[emotion]
            
            # 应用表情参数
            with self._animation_lock:
                for param_name, param_value in emotion_data.items():
                    if param_name in self.parameter_map:
                        self.parameter_map[param_name] = param_value
            
            # 计划在一定时间后恢复默认表情
            asyncio.create_task(self._reset_emotion_after_delay())
            
            logger.info(f"设置表情: {emotion}")
            
        except Exception as e:
            logger.error(f"设置表情失败: {e}")

    async def _reset_emotion_after_delay(self):
        """延迟后重置表情"""
        try:
            await asyncio.sleep(self.config.animation.emotion_duration)
            
            # 重置表情参数
            with self._animation_lock:
                for param_name in ["ParamMouthForm", "ParamEyeForm", "ParamEyebrowForm"]:
                    if param_name in self.parameter_map:
                        self.parameter_map[param_name] = 0.0
            
            self.current_emotion = "neutral"
            logger.debug("表情已重置为默认")
            
        except Exception as e:
            logger.error(f"重置表情失败: {e}")

    async def sync_lipsync(self, phonemes: List[Tuple[str, float]], audio_duration: float):
        """
        同步口型动画
        
        Args:
            phonemes: 音素列表 [(phoneme, duration), ...]
            audio_duration: 音频总时长
        """
        try:
            self.is_speaking = True
            
            # 在后台执行口型同步
            asyncio.create_task(self._perform_lipsync(phonemes, audio_duration))
            
            logger.debug(f"开始口型同步，时长: {audio_duration:.2f}s")
            
        except Exception as e:
            logger.error(f"口型同步失败: {e}")

    async def _perform_lipsync(self, phonemes: List[Tuple[str, float]], audio_duration: float):
        """执行口型同步动画"""
        try:
            start_time = time.time()
            
            for phoneme, duration in phonemes:
                if not self.is_speaking:
                    break
                    
                # 根据音素设置嘴部参数
                mouth_value = self._get_mouth_value_for_phoneme(phoneme)
                
                with self._animation_lock:
                    self.parameter_map["ParamMouthOpenY"] = mouth_value
                
                # 等待音素持续时间
                await asyncio.sleep(duration)
            
            # 重置嘴部参数
            with self._animation_lock:
                self.parameter_map["ParamMouthOpenY"] = 0.0
                
            self.is_speaking = False
            logger.debug("口型同步完成")
            
        except Exception as e:
            logger.error(f"执行口型同步失败: {e}")
            self.is_speaking = False

    def _get_mouth_value_for_phoneme(self, phoneme: str) -> float:
        """根据音素获取嘴部开合值"""
        # 简化的音素映射
        phoneme_map = {
            "a": 0.8, "o": 0.6, "u": 0.4,
            "i": 0.2, "e": 0.3,
            "m": 0.0, "p": 0.0, "b": 0.0,
            "n": 0.1, "t": 0.1, "d": 0.1,
            "k": 0.2, "g": 0.2,
            "s": 0.1, "z": 0.1,
            "f": 0.1, "v": 0.1,
            "th": 0.1, "r": 0.3, "l": 0.2
        }
        
        # 默认值和随机变化
        base_value = phoneme_map.get(phoneme.lower(), 0.3)
        variation = np.random.uniform(-0.1, 0.1)
        
        return max(0.0, min(1.0, base_value + variation))

    async def play_motion(self, motion_name: str):
        """
        播放指定动作
        
        Args:
            motion_name: 动作名称
        """
        try:
            if not self.model_data or "motions" not in self.model_data:
                logger.warning("模型数据中没有动作信息")
                return
                
            # 查找动作
            motion_found = False
            for motion_type, motion_list in self.model_data["motions"].items():
                if motion_name in motion_list:
                    motion_found = True
                    break
                    
            if not motion_found:
                logger.warning(f"未找到动作: {motion_name}")
                return
            
            self.current_motion = motion_name
            logger.info(f"播放动作: {motion_name}")
            
            # 这里可以添加具体的动作播放逻辑
            # 实际实现中需要加载.motion3.json文件并应用关键帧
            
        except Exception as e:
            logger.error(f"播放动作失败: {e}")

    def get_parameter_value(self, param_name: str) -> float:
        """获取参数值"""
        with self._animation_lock:
            return self.parameter_map.get(param_name, 0.0)

    def set_parameter_value(self, param_name: str, value: float):
        """设置参数值"""
        with self._animation_lock:
            if param_name in self.parameter_map:
                self.parameter_map[param_name] = value
            else:
                logger.warning(f"未知参数: {param_name}")

    def get_all_parameters(self) -> Dict[str, float]:
        """获取所有参数值"""
        with self._animation_lock:
            return self.parameter_map.copy()

    async def update_look_direction(self, x: float, y: float):
        """
        更新视线方向
        
        Args:
            x: X轴方向 (-1.0 到 1.0)
            y: Y轴方向 (-1.0 到 1.0)
        """
        try:
            with self._animation_lock:
                self.parameter_map["ParamEyeBallX"] = max(-1.0, min(1.0, x))
                self.parameter_map["ParamEyeBallY"] = max(-1.0, min(1.0, y))
                
        except Exception as e:
            logger.error(f"更新视线方向失败: {e}")

    async def update_head_rotation(self, angle_x: float, angle_y: float, angle_z: float):
        """
        更新头部旋转
        
        Args:
            angle_x: X轴旋转角度
            angle_y: Y轴旋转角度  
            angle_z: Z轴旋转角度
        """
        try:
            with self._animation_lock:
                self.parameter_map["ParamAngleX"] = max(-30.0, min(30.0, angle_x))
                self.parameter_map["ParamAngleY"] = max(-30.0, min(30.0, angle_y))
                self.parameter_map["ParamAngleZ"] = max(-30.0, min(30.0, angle_z))
                
        except Exception as e:
            logger.error(f"更新头部旋转失败: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "name": self.config.model_name,
            "model_path": str(self.model_path) if self.model_path else None,
            "initialized": self._initialized,
            "current_emotion": self.current_emotion,
            "current_motion": self.current_motion,
            "is_speaking": self.is_speaking,
            "model_data": self.model_data,
            "parameter_count": len(self.parameter_map)
        }

    async def cleanup(self):
        """清理资源"""
        try:
            self._initialized = False
            
            # 取消更新任务
            if self._update_task:
                self._update_task.cancel()
                try:
                    await self._update_task
                except asyncio.CancelledError:
                    pass
                    
            # 清理模型数据
            self.model_data = None
            self.is_speaking = False
            
            logger.info("Live2D管理器资源已清理")
            
        except Exception as e:
            logger.error(f"Live2D管理器清理失败: {e}")

    # 调试和开发方法
    async def export_parameters(self) -> Dict[str, float]:
        """导出当前参数状态（用于调试）"""
        return self.get_all_parameters()

    async def import_parameters(self, parameters: Dict[str, float]):
        """导入参数状态（用于调试）"""
        with self._animation_lock:
            for param_name, param_value in parameters.items():
                if param_name in self.parameter_map:
                    self.parameter_map[param_name] = param_value 