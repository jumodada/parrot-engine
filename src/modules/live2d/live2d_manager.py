"""
Live2D 管理器 - 负责 Live2D 模型的加载、渲染和动画控制
"""

import ctypes
import logging
import asyncio
import numpy as np
import time
import math
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path

try:
    import OpenGL.GL as gl
    from OpenGL.arrays import vbo
    from PIL import Image
except ImportError:
    logging.warning("OpenGL 或 PIL 库未安装，Live2D 功能将受限")

from .hiyori_config import HiyoriConfig


class AnimationPriority(Enum):
    """动画优先级"""
    IDLE = 0
    NORMAL = 1
    FORCE = 2


@dataclass
class MotionEntry:
    """动作条目"""
    file_path: str
    fade_in_time: float = 0.5
    fade_out_time: float = 0.5
    sound_file: Optional[str] = None


@dataclass
class ExpressionEntry:
    """表情条目"""
    name: str
    file_path: str
    fade_in_time: float = 0.5
    fade_out_time: float = 0.5


@dataclass
class PhonemeFrame:
    """音素帧"""
    time: float
    phoneme: str
    mouth_open_y: float
    jaw_open: float
    mouth_form: float
    mouth_shrug: float = 0.0
    mouth_funnel: float = 0.0
    mouth_pucker_widen: float = 0.0
    mouth_press_lip: float = 0.0
    mouth_x: float = 0.0
    cheek_puff: float = 0.0


class Live2DManager:
    """
    Live2D 管理器
    
    负责：
    1. 加载和管理 Live2D 模型（Hiyori）
    2. 渲染模型到帧缓冲
    3. 控制表情和动作
    4. VBridger 标准唇形同步
    5. 空闲动画和眼部闪烁
    """
    
    def __init__(self, model_path: str = None, model_name: str = None, 
                 width: int = None, height: int = None, config_path: str = None):
        # 加载 Hiyori 配置
        self.hiyori_config = HiyoriConfig(config_path)
        if not self.hiyori_config.load_config():
            raise RuntimeError("无法加载 Hiyori 配置")
        
        # 使用配置中的值，或者使用传入的参数作为覆盖
        self.model_path = Path(model_path or self.hiyori_config.get_model_path())
        self.model_name = model_name or self.hiyori_config.get_model_name()
        render_width, render_height = self.hiyori_config.get_render_size()
        self.width = width or render_width
        self.height = height or render_height
        
        self.logger = logging.getLogger(__name__)
        
        # CubismSDK 相关
        self._cubism_lib: Optional[ctypes.CDLL] = None
        self._model_handle: Optional[ctypes.c_void_p] = None
        self._allocated_model = None
        
        # 模型配置
        self.model_config: Optional[Dict] = None
        self.expressions: Dict[str, ExpressionEntry] = {}
        self.motion_groups: Dict[str, List[MotionEntry]] = {}
        self.parameters: Dict[str, int] = {}  # 参数名 -> 参数索引
        self.parameter_values: Dict[str, float] = {}  # 当前参数值
        self.parameter_targets: Dict[str, float] = {}  # 目标参数值（用于平滑过渡）
        
        # 渲染相关
        self.texture_handles: List[int] = []
        self.shader_program: Optional[int] = None
        self.vertex_buffer: Optional[int] = None
        self.frame_buffer: Optional[int] = None
        self.color_texture: Optional[int] = None
        
        # 动画状态
        self.current_expression: Optional[str] = None
        self.current_motion: Optional[str] = None
        self.motion_queue: List[Tuple[str, AnimationPriority]] = []
        
        # 时间和帧率
        self.last_update_time = 0.0
        self.user_time_seconds = 0.0
        
        # 眼部闪烁（使用配置）
        blink_config = self.hiyori_config.blinking
        self.blink_enabled = blink_config.enabled
        self.last_blink_time = 0.0
        self.next_blink_interval = np.random.uniform(blink_config.interval_min, blink_config.interval_max)
        self.blink_state = 0  # 0: 睁眼, 1: 闭眼中, 2: 睁眼中
        self.blink_timer = 0.0
        self.blink_close_duration = blink_config.close_duration
        self.blink_open_duration = blink_config.open_duration
        
        # 呼吸效果
        breathing_config = self.hiyori_config.breathing
        self.breathing_enabled = breathing_config.enabled
        self.breathing_parameters = breathing_config.parameters
        self.breathing_time = 0.0
        
        # 唇形同步
        self.phoneme_queue: List[PhonemeFrame] = []
        self.current_phoneme_time = 0.0
        self.lipsync_enabled = True
        
        # VBridger 参数映射
        self.vbridger_params = {
            "ParamMouthOpenY": -1,
            "ParamJawOpen": -1,
            "ParamMouthForm": -1,
            "ParamMouthShrug": -1,
            "ParamMouthFunnel": -1,
            "ParamMouthPuckerWiden": -1,
            "ParamMouthPressLipOpen": -1,
            "ParamMouthX": -1,
            "ParamCheekPuffC": -1,
            "ParamEyeLOpen": -1,
            "ParamEyeROpen": -1,
            "ParamAngleX": -1,
            "ParamAngleY": -1,
            "ParamAngleZ": -1,
            "ParamBodyAngleX": -1,
            "ParamEyeBallX": -1,
            "ParamEyeBallY": -1,
        }
        
        # 表情和动作映射（与对话管理器对应）
        self.expression_mapping = {
            "happy": "happy",
            "excited_star": "excited", 
            "cool": "cool",
            "smug": "smug",
            "determined": "determined",
            "embarrassed": "embarrassed",
            "shocked": "shocked",
            "thinking": "thinking",
            "suspicious": "suspicious",
            "frustrated": "frustrated",
            "sad": "sad",
            "awkward": "awkward",
            "dismissive": "dismissive",
            "adoring": "adoring",
            "laughing": "laughing",
            "passionate": "passionate",
            "sparkle": "sparkle",
            "neutral": "neutral"
        }
        
        self.motion_group_mapping = {
            "Happy": "Happy",
            "Excited": "Excited", 
            "Confident": "Confident",
            "Nervous": "Nervous",
            "Surprised": "Surprised",
            "Thinking": "Thinking",
            "Angry": "Angry",
            "Sad": "Sad",
            "Annoyed": "Annoyed",
            "Idle": "Idle",
            "Talking": "Talking"
        }
    
    async def initialize(self) -> bool:
        """初始化 Live2D 管理器"""
        try:
            self.logger.info(f"初始化 Live2D 管理器 - 模型: {self.model_name}")
            
            # 加载 CubismSDK
            if not self._load_cubism_sdk():
                return False
            
            # 加载模型配置
            if not await self._load_model_config():
                return False
            
            # 初始化 OpenGL 资源
            if not self._initialize_opengl():
                return False
            
            # 加载模型
            if not await self._load_model():
                return False
            
            # 加载纹理
            if not await self._load_textures():
                return False
            
            # 初始化参数映射
            self._initialize_parameter_mapping()
            
            # 加载表情和动作
            await self._load_expressions()
            await self._load_motions()
            
            # 设置初始状态
            await self.set_idle_animation()
            
            self.logger.info("Live2D 管理器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"Live2D 管理器初始化失败: {e}")
            return False
    
    def _load_cubism_sdk(self) -> bool:
        """加载 CubismSDK 动态库"""
        try:
            # 根据系统选择合适的动态库
            import platform
            system = platform.system()
            
            if system == "Windows":
                lib_name = "Live2DCubismCore.dll"
            elif system == "Darwin":  # macOS
                lib_name = "libLive2DCubismCore.dylib"
            else:  # Linux
                lib_name = "libLive2DCubismCore.so"
            
            # 查找库文件
            possible_paths = [
                f"./libs/{lib_name}",
                f"../libs/{lib_name}",
                f"./resources/live2d/{lib_name}",
                lib_name  # 系统路径
            ]
            
            for path in possible_paths:
                try:
                    self._cubism_lib = ctypes.CDLL(path)
                    self.logger.info(f"成功加载 CubismSDK: {path}")
                    break
                except OSError:
                    continue
            
            if not self._cubism_lib:
                self.logger.error("无法找到 CubismSDK 动态库")
                return False
            
            # 设置函数签名
            self._setup_cubism_functions()
            return True
            
        except Exception as e:
            self.logger.error(f"加载 CubismSDK 失败: {e}")
            return False
    
    def _setup_cubism_functions(self):
        """设置 CubismSDK 函数签名"""
        # 这里需要根据实际的 CubismSDK C API 设置函数签名
        # 由于没有实际的 SDK，这里只是示例结构
        pass
    
    async def _load_model_config(self) -> bool:
        """加载模型配置"""
        try:
            config_file = self.model_path / f"{self.model_name}.model3.json"
            
            if not config_file.exists():
                self.logger.error(f"模型配置文件不存在: {config_file}")
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self.model_config = json.load(f)
            
            self.logger.info(f"成功加载模型配置: {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载模型配置失败: {e}")
            return False
    
    def _initialize_opengl(self) -> bool:
        """初始化 OpenGL 资源"""
        try:
            # 创建帧缓冲对象
            self.frame_buffer = gl.glGenFramebuffers(1)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.frame_buffer)
            
            # 创建颜色纹理
            self.color_texture = gl.glGenTextures(1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.color_texture)
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8, self.width, self.height, 
                           0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            
            # 绑定颜色纹理到帧缓冲
            gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, 
                                     gl.GL_TEXTURE_2D, self.color_texture, 0)
            
            # 检查帧缓冲完整性
            if gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER) != gl.GL_FRAMEBUFFER_COMPLETE:
                self.logger.error("帧缓冲不完整")
                return False
            
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
            
            # 加载着色器
            self.shader_program = self._load_shaders()
            if not self.shader_program:
                return False
            
            self.logger.info("OpenGL 资源初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"OpenGL 初始化失败: {e}")
            return False
    
    def _load_shaders(self) -> Optional[int]:
        """加载着色器程序"""
        vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec2 aPos;
        layout (location = 1) in vec2 aTexCoord;
        
        out vec2 TexCoord;
        
        uniform mat4 mvp;
        
        void main() {
            gl_Position = mvp * vec4(aPos, 0.0, 1.0);
            TexCoord = aTexCoord;
        }
        """
        
        fragment_shader_source = """
        #version 330 core
        out vec4 FragColor;
        
        in vec2 TexCoord;
        uniform sampler2D ourTexture;
        uniform vec4 baseColor;
        uniform vec4 multiplyColor;
        uniform vec4 screenColor;
        
        void main() {
            vec4 texColor = texture(ourTexture, TexCoord);
            texColor = texColor * multiplyColor * baseColor;
            FragColor = texColor;
        }
        """
        
        try:
            # 编译顶点着色器
            vertex_shader = gl.glCreateShader(gl.GL_VERTEX_SHADER)
            gl.glShaderSource(vertex_shader, vertex_shader_source)
            gl.glCompileShader(vertex_shader)
            
            # 编译片段着色器
            fragment_shader = gl.glCreateShader(gl.GL_FRAGMENT_SHADER)
            gl.glShaderSource(fragment_shader, fragment_shader_source)
            gl.glCompileShader(fragment_shader)
            
            # 创建着色器程序
            shader_program = gl.glCreateProgram()
            gl.glAttachShader(shader_program, vertex_shader)
            gl.glAttachShader(shader_program, fragment_shader)
            gl.glLinkProgram(shader_program)
            
            # 清理
            gl.glDeleteShader(vertex_shader)
            gl.glDeleteShader(fragment_shader)
            
            return shader_program
            
        except Exception as e:
            self.logger.error(f"着色器加载失败: {e}")
            return None
    
    async def _load_model(self) -> bool:
        """加载 Live2D 模型"""
        try:
            # 这里需要调用 CubismSDK 加载 .moc3 文件
            # 由于没有实际的 SDK 绑定，这里只是示例结构
            
            moc_file = self.model_path / self.model_config["FileReferences"]["Moc"]
            if not moc_file.exists():
                self.logger.error(f"Moc 文件不存在: {moc_file}")
                return False
            
            # 模拟加载模型
            # self._model_handle = self._cubism_lib.LoadModel(str(moc_file))
            
            self.logger.info(f"成功加载模型: {moc_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"加载模型失败: {e}")
            return False
    
    async def _load_textures(self) -> bool:
        """加载模型纹理"""
        try:
            textures = self.model_config["FileReferences"]["Textures"]
            
            for texture_file in textures:
                texture_path = self.model_path / texture_file
                
                if not texture_path.exists():
                    self.logger.warning(f"纹理文件不存在: {texture_path}")
                    continue
                
                # 加载纹理
                image = Image.open(texture_path)
                image = image.convert("RGBA")
                
                texture_id = gl.glGenTextures(1)
                gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
                gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image.width, image.height,
                               0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image.tobytes())
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
                gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
                
                self.texture_handles.append(texture_id)
                self.logger.debug(f"加载纹理: {texture_path}")
            
            self.logger.info(f"成功加载 {len(self.texture_handles)} 个纹理")
            return True
            
        except Exception as e:
            self.logger.error(f"加载纹理失败: {e}")
            return False
    
    def _initialize_parameter_mapping(self):
        """初始化参数映射"""
        try:
            # 从配置中获取所有参数
            param_names = self.hiyori_config.get_all_parameter_names()
            
            # 模拟参数索引（在真实实现中，这些应该从 Cubism SDK 获取）
            for i, param_name in enumerate(param_names):
                self.parameters[param_name] = i
                
                # 初始化参数值
                default_value = self.hiyori_config.get_parameter_default(param_name) or 0.0
                self.parameter_values[param_name] = default_value
                self.parameter_targets[param_name] = default_value
                
                # 更新 VBridger 映射
                if param_name in self.vbridger_params:
                    self.vbridger_params[param_name] = i
            
            # 使用配置中的 VBridger 映射
            lipsync_mapping = self.hiyori_config.lipsync.vbridger_mapping
            for vb_param, live2d_param in lipsync_mapping.items():
                if live2d_param in self.parameters:
                    self.vbridger_params[live2d_param] = self.parameters[live2d_param]
            
            self.logger.info(f"初始化 {len(self.parameters)} 个参数映射")
            
        except Exception as e:
            self.logger.error(f"初始化参数映射失败: {e}")
    
    async def _load_expressions(self):
        """加载表情"""
        try:
            if "Expressions" not in self.model_config.get("FileReferences", {}):
                self.logger.warning("模型配置中未找到表情信息")
                return
            
            expressions = self.model_config["FileReferences"]["Expressions"]
            
            for expr in expressions:
                name = expr["Name"]
                file_path = self.model_path / expr["File"]
                
                if file_path.exists():
                    self.expressions[name] = ExpressionEntry(
                        name=name,
                        file_path=str(file_path)
                    )
                    self.logger.debug(f"加载表情: {name}")
            
            self.logger.info(f"成功加载 {len(self.expressions)} 个表情")
            
        except Exception as e:
            self.logger.error(f"加载表情失败: {e}")
    
    async def _load_motions(self):
        """加载动作"""
        try:
            if "Motions" not in self.model_config.get("FileReferences", {}):
                self.logger.warning("模型配置中未找到动作信息")
                return
            
            motions = self.model_config["FileReferences"]["Motions"]
            
            for group_name, motion_list in motions.items():
                self.motion_groups[group_name] = []
                
                for motion in motion_list:
                    file_path = self.model_path / motion["File"]
                    
                    if file_path.exists():
                        entry = MotionEntry(
                            file_path=str(file_path),
                            fade_in_time=motion.get("FadeInTime", 0.5),
                            fade_out_time=motion.get("FadeOutTime", 0.5),
                            sound_file=motion.get("Sound")
                        )
                        self.motion_groups[group_name].append(entry)
                        self.logger.debug(f"加载动作: {group_name}/{motion['File']}")
            
            self.logger.info(f"成功加载 {len(self.motion_groups)} 个动作组")
            
        except Exception as e:
            self.logger.error(f"加载动作失败: {e}")
    
    def update(self, delta_time: float):
        """更新模型状态"""
        try:
            current_time = time.time()
            self.user_time_seconds += delta_time
            self.breathing_time += delta_time
            
            # 更新眼部闪烁
            self._update_blinking(delta_time)
            
            # 更新唇形同步
            self._update_lipsync(delta_time)
            
            # 更新呼吸效果
            self._update_breathing(delta_time)
            
            # 更新参数平滑过渡
            self._update_parameter_smoothing(delta_time)
            
            # 更新动作
            self._update_motions(delta_time)
            
            # 更新模型（如果有 SDK）
            # if self._model_handle:
            #     self._cubism_lib.UpdateModel(self._model_handle, delta_time)
            
            self.last_update_time = current_time
            
        except Exception as e:
            self.logger.error(f"更新模型失败: {e}")
    
    def _update_blinking(self, delta_time: float):
        """更新眼部闪烁"""
        if not self.blink_enabled:
            return
        
        try:
            current_time = time.time()
            
            if self.blink_state == 0:  # 睁眼状态
                if current_time - self.last_blink_time >= self.next_blink_interval:
                    # 开始闭眼
                    self.blink_state = 1
                    self.blink_timer = 0.0
                    self.last_blink_time = current_time
                    self.next_blink_interval = np.random.uniform(1.5, 6.0)
            
            elif self.blink_state == 1:  # 闭眼中
                self.blink_timer += delta_time
                
                if self.blink_timer >= self.blink_close_duration:
                    self.blink_state = 2
                    self.blink_timer = 0.0
                else:
                    # 渐变闭眼
                    progress = self.blink_timer / self.blink_close_duration
                    eye_open = 1.0 - progress
                    self._set_parameter("ParamEyeLOpen", eye_open)
                    self._set_parameter("ParamEyeROpen", eye_open)
            
            elif self.blink_state == 2:  # 睁眼中
                self.blink_timer += delta_time
                
                if self.blink_timer >= self.blink_open_duration:
                    self.blink_state = 0
                    self._set_parameter("ParamEyeLOpen", 1.0)
                    self._set_parameter("ParamEyeROpen", 1.0)
                else:
                    # 渐变睁眼
                    progress = self.blink_timer / self.blink_open_duration
                    eye_open = progress
                    self._set_parameter("ParamEyeLOpen", eye_open)
                    self._set_parameter("ParamEyeROpen", eye_open)
        
        except Exception as e:
            self.logger.error(f"更新眼部闪烁失败: {e}")
    
    def _update_lipsync(self, delta_time: float):
        """更新唇形同步"""
        if not self.lipsync_enabled or not self.phoneme_queue:
            return
        
        try:
            self.current_phoneme_time += delta_time
            
            # 找到当前时间对应的音素帧
            current_frame = None
            for frame in self.phoneme_queue:
                if frame.time <= self.current_phoneme_time:
                    current_frame = frame
                else:
                    break
            
            if current_frame:
                # 应用 VBridger 参数
                self._set_parameter("ParamMouthOpenY", current_frame.mouth_open_y)
                self._set_parameter("ParamJawOpen", current_frame.jaw_open)
                self._set_parameter("ParamMouthForm", current_frame.mouth_form)
                self._set_parameter("ParamMouthShrug", current_frame.mouth_shrug)
                self._set_parameter("ParamMouthFunnel", current_frame.mouth_funnel)
                self._set_parameter("ParamMouthPuckerWiden", current_frame.mouth_pucker_widen)
                self._set_parameter("ParamMouthPressLipOpen", current_frame.mouth_press_lip)
                self._set_parameter("ParamMouthX", current_frame.mouth_x)
                self._set_parameter("ParamCheekPuffC", current_frame.cheek_puff)
            
            # 清理过期的音素帧
            self.phoneme_queue = [f for f in self.phoneme_queue 
                                if f.time > self.current_phoneme_time - 0.1]
        
        except Exception as e:
            self.logger.error(f"更新唇形同步失败: {e}")
    
    def _update_breathing(self, delta_time: float):
        """更新呼吸效果"""
        if not self.breathing_enabled:
            return
        
        try:
            for breath_param in self.breathing_parameters:
                param_name = breath_param.get("name")
                amplitude = breath_param.get("amplitude", 0.5)
                cycle = breath_param.get("cycle", 3.0)
                
                if param_name:
                    # 计算呼吸值（正弦波）
                    breath_value = amplitude * math.sin(2 * math.pi * self.breathing_time / cycle)
                    
                    # 获取参数的默认值
                    default_value = self.hiyori_config.get_parameter_default(param_name) or 0.0
                    
                    # 应用呼吸效果
                    final_value = default_value + breath_value
                    self._set_parameter(param_name, final_value)
        
        except Exception as e:
            self.logger.error(f"更新呼吸效果失败: {e}")
    
    def _update_parameter_smoothing(self, delta_time: float):
        """更新参数平滑过渡"""
        if not self.hiyori_config.performance.parameter_smoothing:
            return
        
        try:
            smoothing_factor = min(delta_time * 5.0, 1.0)  # 平滑因子
            
            for param_name, target_value in self.parameter_targets.items():
                current_value = self.parameter_values.get(param_name, 0.0)
                
                # 线性插值
                new_value = current_value + (target_value - current_value) * smoothing_factor
                
                self.parameter_values[param_name] = new_value
                
                # 实际设置参数（如果有 SDK）
                # if self._model_handle:
                #     self._cubism_lib.SetParameterValue(self._model_handle, param_index, new_value)
        
        except Exception as e:
            self.logger.error(f"更新参数平滑过渡失败: {e}")
    
    def _update_motions(self, delta_time: float):
        """更新动作播放"""
        # 这里需要实现动作队列的处理
        # 由于没有实际的 SDK，这里只是示例结构
        pass
    
    def render(self) -> Optional[np.ndarray]:
        """渲染模型并返回帧数据"""
        try:
            # 绑定帧缓冲
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.frame_buffer)
            gl.glViewport(0, 0, self.width, self.height)
            
            # 清空缓冲
            gl.glClearColor(0.0, 0.0, 0.0, 0.0)  # 透明背景
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            
            # 启用混合
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            
            # 渲染模型（如果有 SDK）
            # if self._model_handle:
            #     self._cubism_lib.RenderModel(self._model_handle)
            
            # 读取帧缓冲数据
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.frame_buffer)
            frame_data = gl.glReadPixels(0, 0, self.width, self.height, 
                                       gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
            
            # 转换为 numpy 数组
            frame_array = np.frombuffer(frame_data, dtype=np.uint8)
            frame_array = frame_array.reshape(self.height, self.width, 4)
            frame_array = np.flipud(frame_array)  # OpenGL 坐标系翻转
            
            # 恢复默认帧缓冲
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
            
            return frame_array
            
        except Exception as e:
            self.logger.error(f"渲染模型失败: {e}")
            return None
    
    def _set_parameter(self, param_name: str, value: float):
        """设置模型参数"""
        try:
            # 检查参数范围
            param_range = self.hiyori_config.get_parameter_range(param_name)
            if param_range:
                value = max(param_range[0], min(param_range[1], value))
            
            if self.hiyori_config.performance.parameter_smoothing:
                # 使用平滑过渡
                self.parameter_targets[param_name] = value
            else:
                # 直接设置
                self.parameter_values[param_name] = value
            
            # 调用 SDK 设置参数（如果有）
            if param_name in self.parameters:
                param_index = self.parameters[param_name]
                # if self._model_handle:
                #     self._cubism_lib.SetParameterValue(self._model_handle, param_index, value)
                
        except Exception as e:
            self.logger.error(f"设置参数失败 {param_name}: {e}")
    
    # 公共接口
    async def set_expression(self, expression_name: str):
        """设置表情"""
        try:
            # 获取表情参数
            expression_params = self.hiyori_config.get_expression_parameters(expression_name)
            
            if expression_params:
                self.current_expression = expression_name
                
                # 应用表情参数
                for param_name, param_value in expression_params.items():
                    self._set_parameter(param_name, param_value)
                
                # 根据表情选择合适的动作
                motion_config = self.hiyori_config.get_motion_for_emotion(expression_name)
                if motion_config and motion_config.preferred_motions:
                    import random
                    selected_motion = random.choice(motion_config.preferred_motions)
                    await self.play_motion(motion_config.group, AnimationPriority.NORMAL)
                
                if self.hiyori_config.debug.log_expression_changes:
                    self.logger.debug(f"设置表情: {expression_name}")
            else:
                self.logger.warning(f"未找到表情配置: {expression_name}")
                
        except Exception as e:
            self.logger.error(f"设置表情失败: {e}")
    
    async def play_motion(self, motion_group: str, priority: AnimationPriority = AnimationPriority.NORMAL):
        """播放动作"""
        try:
            # 映射动作组名称
            mapped_group = self.motion_group_mapping.get(motion_group, motion_group)
            
            if mapped_group in self.motion_groups:
                motions = self.motion_groups[mapped_group]
                if motions:
                    # 随机选择一个动作
                    import random
                    motion = random.choice(motions)
                    
                    # 添加到队列或立即播放
                    if priority == AnimationPriority.FORCE:
                        # 强制播放，清空队列
                        self.motion_queue.clear()
                    
                    self.motion_queue.append((motion.file_path, priority))
                    self.logger.debug(f"播放动作: {motion_group} -> {mapped_group}")
            else:
                self.logger.warning(f"未找到动作组: {motion_group}")
                
        except Exception as e:
            self.logger.error(f"播放动作失败: {e}")
    
    async def set_idle_animation(self):
        """设置空闲动画"""
        try:
            await self.set_expression("neutral")
            await self.play_motion("Idle", AnimationPriority.IDLE)
            self.logger.debug("设置空闲动画")
        except Exception as e:
            self.logger.error(f"设置空闲动画失败: {e}")
    
    async def sync_lipsync(self, phoneme_timing: List[PhonemeFrame]):
        """同步唇形动画"""
        try:
            self.phoneme_queue.extend(phoneme_timing)
            self.current_phoneme_time = 0.0
            self.logger.debug(f"同步唇形动画，{len(phoneme_timing)} 个音素帧")
        except Exception as e:
            self.logger.error(f"同步唇形动画失败: {e}")
    
    def set_emotion(self, emotion: str):
        """设置情感（同步接口）"""
        try:
            # 运行异步方法
            asyncio.create_task(self.set_expression(emotion))
        except Exception as e:
            self.logger.error(f"设置情感失败: {e}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return self.hiyori_config.get_config_summary()
    
    def get_available_expressions(self) -> List[str]:
        """获取可用的表情列表"""
        return self.hiyori_config.get_expression_names()
    
    def get_available_motions(self) -> List[str]:
        """获取可用的动作列表"""
        return self.hiyori_config.get_motion_names()
    
    def get_parameter_value(self, param_name: str) -> Optional[float]:
        """获取参数当前值"""
        return self.parameter_values.get(param_name)
    
    def get_all_parameter_values(self) -> Dict[str, float]:
        """获取所有参数的当前值"""
        return self.parameter_values.copy()
    
    def validate_config(self) -> List[str]:
        """验证配置有效性"""
        return self.hiyori_config.validate_config()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            "current_fps": self.hiyori_config.performance.max_fps,
            "parameter_count": len(self.parameters),
            "expression_count": len(self.hiyori_config.expressions),
            "motion_count": len(self.hiyori_config.motions),
            "blinking_enabled": self.blink_enabled,
            "breathing_enabled": self.breathing_enabled,
            "lipsync_enabled": self.lipsync_enabled,
            "current_expression": self.current_expression,
            "blink_state": self.blink_state
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 清理 OpenGL 资源
            if self.texture_handles:
                gl.glDeleteTextures(len(self.texture_handles), self.texture_handles)
            
            if self.shader_program:
                gl.glDeleteProgram(self.shader_program)
            
            if self.frame_buffer:
                gl.glDeleteFramebuffers(1, [self.frame_buffer])
            
            if self.color_texture:
                gl.glDeleteTextures(1, [self.color_texture])
            
            # 清理 Cubism 资源
            # if self._model_handle and self._cubism_lib:
            #     self._cubism_lib.ReleaseModel(self._model_handle)
            
            self.logger.info("Live2D 资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理 Live2D 资源失败: {e}") 