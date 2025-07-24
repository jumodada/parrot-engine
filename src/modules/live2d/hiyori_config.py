"""
Hiyori Live2D 模型配置管理器
负责加载和管理 Hiyori 模型的专门配置
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from loguru import logger


@dataclass
class ParameterConfig:
    """参数配置"""
    range: List[float]
    default: float


@dataclass
class ExpressionConfig:
    """表情配置"""
    name: str
    parameters: Dict[str, float]


@dataclass
class MotionConfig:
    """动作配置"""
    group: str
    motions: List[str]
    weight: float = 1.0
    fade_in: float = 0.5
    fade_out: float = 0.5
    emotion_triggers: Optional[List[str]] = None
    preferred_motions: Optional[List[str]] = None


@dataclass
class BlinkingConfig:
    """眼部闪烁配置"""
    enabled: bool = True
    interval_min: float = 1.5
    interval_max: float = 6.0
    close_duration: float = 0.06
    open_duration: float = 0.10


@dataclass
class LipsyncConfig:
    """唇形同步配置"""
    enabled: bool = True
    vbridger_mapping: Dict[str, str]
    intensity: float = 0.8
    smoothing: float = 0.3


@dataclass
class BreathingConfig:
    """呼吸效果配置"""
    enabled: bool = True
    parameters: List[Dict[str, Any]]


@dataclass
class PerformanceConfig:
    """性能配置"""
    max_fps: int = 60
    update_interval: float = 0.016
    parameter_smoothing: bool = True
    motion_blending: bool = True


@dataclass
class DebugConfig:
    """调试配置"""
    show_parameters: bool = False
    log_motion_changes: bool = True
    log_expression_changes: bool = True
    performance_monitoring: bool = True


class HiyoriConfig:
    """
    Hiyori 模型配置管理器
    
    负责：
    1. 加载 YAML 配置文件
    2. 解析模型参数映射
    3. 管理表情和动作配置
    4. 提供配置查询接口
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self.config_path = Path(config_path) if config_path else Path("config/hiyori_config.yaml")
        
        # 配置数据
        self.raw_config: Dict[str, Any] = {}
        
        # 解析后的配置
        self.model_config: Dict[str, Any] = {}
        self.parameters: Dict[str, Dict[str, ParameterConfig]] = {}
        self.expressions: Dict[str, ExpressionConfig] = {}
        self.motions: Dict[str, MotionConfig] = {}
        self.blinking: BlinkingConfig = BlinkingConfig()
        self.lipsync: LipsyncConfig = LipsyncConfig(
            enabled=True,
            vbridger_mapping={}
        )
        self.breathing: BreathingConfig = BreathingConfig(
            enabled=True,
            parameters=[]
        )
        self.performance: PerformanceConfig = PerformanceConfig()
        self.debug: DebugConfig = DebugConfig()
        
        logger.info(f"Hiyori 配置管理器初始化，配置文件: {self.config_path}")
    
    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                logger.error(f"配置文件不存在: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.raw_config = yaml.safe_load(f)
            
            # 解析各个配置项
            self._parse_model_config()
            self._parse_parameters()
            self._parse_expressions()
            self._parse_motions()
            self._parse_blinking()
            self._parse_lipsync()
            self._parse_breathing()
            self._parse_performance()
            self._parse_debug()
            
            logger.info("Hiyori 配置加载完成")
            return True
            
        except Exception as e:
            logger.error(f"加载 Hiyori 配置失败: {e}")
            return False
    
    def _parse_model_config(self):
        """解析模型基本配置"""
        self.model_config = self.raw_config.get('model', {})
    
    def _parse_parameters(self):
        """解析参数配置"""
        params_config = self.raw_config.get('parameters', {})
        
        for category, params in params_config.items():
            self.parameters[category] = {}
            for param_name, param_data in params.items():
                self.parameters[category][param_name] = ParameterConfig(
                    range=param_data.get('range', [0.0, 1.0]),
                    default=param_data.get('default', 0.0)
                )
    
    def _parse_expressions(self):
        """解析表情配置"""
        expressions_config = self.raw_config.get('expressions', {})
        
        for expr_name, expr_data in expressions_config.items():
            self.expressions[expr_name] = ExpressionConfig(
                name=expr_data.get('name', expr_name),
                parameters=expr_data.get('parameters', {})
            )
    
    def _parse_motions(self):
        """解析动作配置"""
        motions_config = self.raw_config.get('motions', {})
        
        for motion_name, motion_data in motions_config.items():
            self.motions[motion_name] = MotionConfig(
                group=motion_data.get('group', 'Idle'),
                motions=motion_data.get('motions', []),
                weight=motion_data.get('weight', 1.0),
                fade_in=motion_data.get('fade_in', 0.5),
                fade_out=motion_data.get('fade_out', 0.5),
                emotion_triggers=motion_data.get('emotion_triggers'),
                preferred_motions=motion_data.get('preferred_motions')
            )
    
    def _parse_blinking(self):
        """解析眼部闪烁配置"""
        blinking_config = self.raw_config.get('blinking', {})
        
        self.blinking = BlinkingConfig(
            enabled=blinking_config.get('enabled', True),
            interval_min=blinking_config.get('interval_min', 1.5),
            interval_max=blinking_config.get('interval_max', 6.0),
            close_duration=blinking_config.get('close_duration', 0.06),
            open_duration=blinking_config.get('open_duration', 0.10)
        )
    
    def _parse_lipsync(self):
        """解析唇形同步配置"""
        lipsync_config = self.raw_config.get('lipsync', {})
        
        self.lipsync = LipsyncConfig(
            enabled=lipsync_config.get('enabled', True),
            vbridger_mapping=lipsync_config.get('vbridger_mapping', {}),
            intensity=lipsync_config.get('intensity', 0.8),
            smoothing=lipsync_config.get('smoothing', 0.3)
        )
    
    def _parse_breathing(self):
        """解析呼吸效果配置"""
        breathing_config = self.raw_config.get('breathing', {})
        
        self.breathing = BreathingConfig(
            enabled=breathing_config.get('enabled', True),
            parameters=breathing_config.get('parameters', [])
        )
    
    def _parse_performance(self):
        """解析性能配置"""
        performance_config = self.raw_config.get('performance', {})
        
        self.performance = PerformanceConfig(
            max_fps=performance_config.get('max_fps', 60),
            update_interval=performance_config.get('update_interval', 0.016),
            parameter_smoothing=performance_config.get('parameter_smoothing', True),
            motion_blending=performance_config.get('motion_blending', True)
        )
    
    def _parse_debug(self):
        """解析调试配置"""
        debug_config = self.raw_config.get('debug', {})
        
        self.debug = DebugConfig(
            show_parameters=debug_config.get('show_parameters', False),
            log_motion_changes=debug_config.get('log_motion_changes', True),
            log_expression_changes=debug_config.get('log_expression_changes', True),
            performance_monitoring=debug_config.get('performance_monitoring', True)
        )
    
    # 配置查询接口
    def get_model_path(self) -> str:
        """获取模型路径"""
        return self.model_config.get('path', 'src/modules/live2d/Models/Hiyori')
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.model_config.get('name', 'Hiyori')
    
    def get_render_size(self) -> tuple[int, int]:
        """获取渲染尺寸"""
        render_config = self.model_config.get('render', {})
        return (
            render_config.get('width', 1080),
            render_config.get('height', 1920)
        )
    
    def get_expression_parameters(self, expression_name: str) -> Optional[Dict[str, float]]:
        """获取表情参数"""
        if expression_name in self.expressions:
            return self.expressions[expression_name].parameters
        return None
    
    def get_motion_for_emotion(self, emotion: str) -> Optional[MotionConfig]:
        """根据情感获取动作配置"""
        for motion_config in self.motions.values():
            if (motion_config.emotion_triggers and 
                emotion in motion_config.emotion_triggers):
                return motion_config
        
        # 返回默认空闲动作
        return self.motions.get('idle')
    
    def get_parameter_range(self, param_name: str) -> Optional[List[float]]:
        """获取参数范围"""
        for category in self.parameters.values():
            if param_name in category:
                return category[param_name].range
        return None
    
    def get_parameter_default(self, param_name: str) -> Optional[float]:
        """获取参数默认值"""
        for category in self.parameters.values():
            if param_name in category:
                return category[param_name].default
        return None
    
    def get_all_parameter_names(self) -> List[str]:
        """获取所有参数名称"""
        param_names = []
        for category in self.parameters.values():
            param_names.extend(category.keys())
        return param_names
    
    def get_expression_names(self) -> List[str]:
        """获取所有表情名称"""
        return list(self.expressions.keys())
    
    def get_motion_names(self) -> List[str]:
        """获取所有动作名称"""
        return list(self.motions.keys())
    
    def validate_config(self) -> List[str]:
        """验证配置有效性"""
        errors = []
        
        # 检查模型路径
        model_path = Path(self.get_model_path())
        if not model_path.exists():
            errors.append(f"模型路径不存在: {model_path}")
        
        # 检查模型文件
        model_json = model_path / f"{self.get_model_name()}.model3.json"
        if not model_json.exists():
            errors.append(f"模型配置文件不存在: {model_json}")
        
        # 检查动作文件
        for motion_config in self.motions.values():
            for motion_file in motion_config.motions:
                motion_path = model_path / "motions" / motion_file
                if not motion_path.exists():
                    errors.append(f"动作文件不存在: {motion_path}")
        
        # 检查参数范围
        for category_name, category in self.parameters.items():
            for param_name, param_config in category.items():
                if len(param_config.range) != 2:
                    errors.append(f"参数范围格式错误: {category_name}.{param_name}")
                elif param_config.range[0] > param_config.range[1]:
                    errors.append(f"参数范围无效: {category_name}.{param_name}")
        
        return errors
    
    def save_config(self, output_path: Optional[Path] = None) -> bool:
        """保存配置到文件"""
        try:
            output_file = output_path or self.config_path
            
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.raw_config, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            logger.info(f"配置已保存到: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def update_expression(self, expression_name: str, parameters: Dict[str, float]):
        """更新表情配置"""
        if expression_name in self.expressions:
            self.expressions[expression_name].parameters.update(parameters)
            # 同时更新原始配置
            if 'expressions' not in self.raw_config:
                self.raw_config['expressions'] = {}
            if expression_name not in self.raw_config['expressions']:
                self.raw_config['expressions'][expression_name] = {}
            if 'parameters' not in self.raw_config['expressions'][expression_name]:
                self.raw_config['expressions'][expression_name]['parameters'] = {}
            
            self.raw_config['expressions'][expression_name]['parameters'].update(parameters)
            
            if self.debug.log_expression_changes:
                logger.info(f"表情配置已更新: {expression_name}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "model_name": self.get_model_name(),
            "model_path": self.get_model_path(),
            "render_size": self.get_render_size(),
            "expressions_count": len(self.expressions),
            "motions_count": len(self.motions),
            "parameters_count": sum(len(category) for category in self.parameters.values()),
            "blinking_enabled": self.blinking.enabled,
            "lipsync_enabled": self.lipsync.enabled,
            "breathing_enabled": self.breathing.enabled,
            "max_fps": self.performance.max_fps
        } 