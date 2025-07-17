#!/usr/bin/env python3
"""
Python Persona Engine - 主应用程序入口
基于原版 handcrafted-persona-engine 的Python复刻版本

使用方法:
    python main.py [--config config.yaml] [--no-ui] [--debug]
"""

import asyncio
import argparse
import sys
import os
import signal
from pathlib import Path
from typing import Optional
from loguru import logger

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.avatar_engine import AvatarEngine
from src.utils.config import Config
from src.ui.control_panel import ControlPanel


class PersonaEngineApp:
    """主应用程序类"""
    
    def __init__(self, config_path: str = "config/config.yaml", enable_ui: bool = True):
        self.config_path = config_path
        self.enable_ui = enable_ui
        
        # 核心组件
        self.config: Optional[Config] = None
        self.engine: Optional[AvatarEngine] = None
        self.ui: Optional[ControlPanel] = None
        
        # 运行控制
        self._shutdown_event = asyncio.Event()
        
        logger.info("Python Persona Engine 应用程序初始化")

    async def initialize(self):
        """初始化应用程序"""
        try:
            # 加载配置
            self.config = Config.from_file(self.config_path)
            if not self.config.validate():
                logger.error("配置验证失败")
                return False
            
            # 设置日志
            self._setup_logging()
            
            # 创建必要的目录
            self._create_directories()
            
            # 初始化核心引擎
            self.engine = AvatarEngine(self.config)
            
            # 如果启用UI，初始化控制面板
            if self.enable_ui:
                self.ui = ControlPanel(self.engine, self.config)
                self.ui.initialize()
            
            logger.info("应用程序初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"应用程序初始化失败: {e}")
            return False

    def _setup_logging(self):
        """设置日志系统"""
        try:
            # 移除默认处理器
            logger.remove()
            
            # 控制台输出
            logger.add(
                sys.stdout,
                level=self.config.logging.level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                       "<level>{level: <8}</level> | "
                       "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                       "<level>{message}</level>",
                colorize=True
            )
            
            # 文件输出
            log_file = Path(self.config.logging.log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.add(
                log_file,
                level=self.config.logging.level,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                rotation=self.config.logging.max_file_size,
                retention=self.config.logging.backup_count,
                compression="zip"
            )
            
            logger.info(f"日志系统已配置，级别: {self.config.logging.level}")
            
        except Exception as e:
            print(f"日志系统配置失败: {e}")

    def _create_directories(self):
        """创建必要的目录"""
        directories = [
            "logs",
            "resources/live2d",
            "resources/models",
            "resources/sounds",
            "config"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    async def run(self):
        """运行应用程序"""
        try:
            logger.info("Python Persona Engine 启动中...")
            
            # 初始化
            if not await self.initialize():
                logger.error("初始化失败，程序退出")
                return 1
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            if self.enable_ui:
                # UI模式
                await self._run_with_ui()
            else:
                # 命令行模式
                await self._run_headless()
            
            logger.info("应用程序正常退出")
            return 0
            
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在退出...")
            return 0
        except Exception as e:
            logger.error(f"应用程序运行失败: {e}")
            return 1
        finally:
            await self._cleanup()

    async def _run_with_ui(self):
        """运行UI模式"""
        try:
            logger.info("启动UI模式")
            
            # 在单独线程中运行UI
            import threading
            ui_thread = threading.Thread(target=self.ui.run, daemon=True)
            ui_thread.start()
            
            # 等待关闭信号
            await self._shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"UI模式运行失败: {e}")

    async def _run_headless(self):
        """运行无界面模式"""
        try:
            logger.info("启动无界面模式")
            
            # 启动引擎
            await self.engine.start()
            
            logger.info("引擎已启动，按 Ctrl+C 退出")
            
            # 等待关闭信号
            await self._shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"无界面模式运行失败: {e}")

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，开始关闭程序")
            asyncio.create_task(self._shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def _shutdown(self):
        """关闭应用程序"""
        logger.info("开始关闭应用程序...")
        self._shutdown_event.set()

    async def _cleanup(self):
        """清理资源"""
        try:
            logger.info("清理应用程序资源...")
            
            if self.engine:
                await self.engine.stop()
            
            logger.info("资源清理完成")
            
        except Exception as e:
            logger.error(f"资源清理失败: {e}")

    def get_status(self) -> dict:
        """获取应用程序状态"""
        status = {
            "config_loaded": self.config is not None,
            "engine_initialized": self.engine is not None,
            "ui_enabled": self.enable_ui,
        }
        
        if self.engine:
            status["engine_state"] = self.engine.get_state().value
            status["metrics"] = self.engine.get_metrics()
        
        return status


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║  🎭 Python Persona Engine                                    ║
║                                                              ║
║  AI驱动的交互式虚拟角色引擎                                  ║
║  基于原版 handcrafted-persona-engine 的Python复刻版本       ║
║                                                              ║
║  功能特性:                                                   ║
║  • 🎤 语音识别 (OpenAI Whisper)                             ║
║  • 🧠 大语言模型集成 (OpenAI/Anthropic/本地)                ║
║  • 🗣️ 文本转语音 (Coqui TTS/ElevenLabs/Azure)              ║
║  • 🎭 Live2D动画支持                                        ║
║  • 🎮 实时交互与打断检测                                     ║
║  • 🖥️ 现代化控制界面                                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """主函数"""
    # 打印启动横幅
    print_banner()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="Python Persona Engine - AI驱动的交互式虚拟角色引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                          # 使用默认配置启动UI模式
  python main.py --config my_config.yaml  # 使用自定义配置
  python main.py --no-ui                  # 无界面模式运行
  python main.py --debug                  # 启用调试模式
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        default="config/config.yaml",
        help="配置文件路径 (默认: config/config.yaml)"
    )
    
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="禁用UI，以命令行模式运行"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Python Persona Engine v1.0.0"
    )
    
    args = parser.parse_args()
    
    # 检查配置文件
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ 错误: 配置文件不存在: {config_path}")
        print(f"💡 提示: 请复制 config/config.example.yaml 为 {config_path} 并修改相应设置")
        return 1
    
    # 创建应用程序实例
    app = PersonaEngineApp(
        config_path=str(config_path),
        enable_ui=not args.no_ui
    )
    
    try:
        # 运行应用程序
        if sys.platform == "win32":
            # Windows 需要特殊的事件循环策略
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        return asyncio.run(app.run())
        
    except Exception as e:
        print(f"❌ 应用程序启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 