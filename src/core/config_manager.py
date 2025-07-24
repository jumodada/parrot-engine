"""
配置管理器模块
负责加载和管理系统配置
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_file: str = "config/config.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
            else:
                print(f"配置文件 {self.config_file} 不存在，使用默认配置")
                self.config = self.get_default_config()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self.config = self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "llm": {
                "provider": "openai",
                "api_key": "",
                "model": "gpt-3.5-turbo",
                "endpoint": "https://api.openai.com/v1"
            },
            "tts": {
                "engine": "default",
                "voice": "zh-CN",
                "speed": 1.0,
                "volume": 0.8
            },
            "asr": {
                "model": "base",
                "language": "zh",
                "vad_threshold": 0.5
            },
            "audio": {
                "sample_rate": 16000,
                "buffer_size": 1024,
                "input_device": None,
                "output_device": None
            },
            "live2d": {
                "model_path": "src/modules/live2d/Models/Hiyori",
                "model_name": "Hiyori",
                "width": 1080,
                "height": 1920
            },
            "streaming": {
                "enable_obs": True,
                "obs_host": "localhost",
                "obs_port": 4444,
                "obs_password": "",
                "target_fps": 60
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键 (如 "llm.api_key")
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save_config(self) -> None:
        """保存配置到文件"""
        try:
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置节
        
        Args:
            section: 节名称
            
        Returns:
            配置节字典
        """
        return self.config.get(section, {})

# 全局配置管理器实例
config_manager = ConfigManager() 