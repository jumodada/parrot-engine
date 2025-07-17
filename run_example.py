#!/usr/bin/env python3
"""
Python Persona Engine 简单运行示例
用于演示基本功能，无需复杂配置
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.avatar_engine import AvatarEngine, EngineState
from src.utils.config import Config
from loguru import logger


async def simple_text_chat():
    """简单的文本聊天示例"""
    print("🎭 Python Persona Engine - 文本聊天示例")
    print("=" * 50)
    
    # 创建最小配置
    config = Config()
    
    # 设置基本参数（使用默认值，无需外部服务）
    config.llm.text_provider = "local"  # 模拟本地模式
    config.live2d.enabled = False  # 禁用Live2D以简化示例
    config.asr.device = "cpu"  # 使用CPU模式
    
    # 创建引擎
    engine = AvatarEngine(config)
    
    print("🚀 正在初始化引擎...")
    
    try:
        # 初始化引擎（跳过需要外部服务的部分）
        # 这里只是演示架构，实际运行需要配置API密钥
        print("ℹ️  注意：这是一个架构演示，实际运行需要配置API密钥")
        print("📝 请参考 config/config.example.yaml 进行完整配置")
        
        # 模拟对话
        conversation = [
            "你好！",
            "你能做什么？",
            "今天天气怎么样？",
            "再见！"
        ]
        
        print("\n💬 模拟对话演示:")
        print("-" * 30)
        
        for message in conversation:
            print(f"👤 用户: {message}")
            
            # 模拟处理延迟
            await asyncio.sleep(0.5)
            
            # 模拟回复（在实际使用中这会调用LLM）
            responses = {
                "你好！": "[EMOTION:happy] 你好！我是Aria，很高兴见到你！",
                "你能做什么？": "[EMOTION:thinking] 我可以和你聊天，回答问题，还能通过表情和动作表达情感哦！",
                "今天天气怎么样？": "[EMOTION:shy] 抱歉，我无法查看实时天气信息，但我可以陪你聊其他话题！",
                "再见！": "[EMOTION:sad] 再见！希望很快能再次见到你！"
            }
            
            response = responses.get(message, "[EMOTION:neutral] 有趣的问题，让我想想...")
            print(f"🤖 Aria: {response}")
            print()
            
            await asyncio.sleep(1)
        
        print("✨ 演示完成！")
        print("\n📖 完整功能体验:")
        print("1. 配置 config/config.yaml 中的API密钥")
        print("2. 运行 python main.py 启动完整版本")
        print("3. 查看 README.md 了解更多功能")
        
    except Exception as e:
        logger.error(f"演示运行失败: {e}")
        print(f"❌ 演示失败: {e}")


async def show_features():
    """展示主要功能特性"""
    print("\n🌟 Python Persona Engine 主要功能:")
    print("=" * 50)
    
    features = [
        "🎤 实时语音识别 - 基于OpenAI Whisper",
        "🧠 智能对话系统 - 支持多种LLM后端",
        "🗣️ 自然语音合成 - 多种TTS引擎选择",
        "🎭 Live2D角色动画 - 表情和动作同步",
        "🎮 打断检测 - 自然的对话体验",
        "🖥️ 现代化界面 - 直观的控制面板",
        "⚙️ 灵活配置 - 完全可定制",
        "🔌 插件系统 - 可扩展架构"
    ]
    
    for i, feature in enumerate(features, 1):
        print(f"{i:2d}. {feature}")
        await asyncio.sleep(0.2)
    
    print("\n🏗️ 系统架构:")
    print("┌─────────────┐    ┌─────────────┐    ┌─────────────┐")
    print("│   语音输入   │───▶│   ASR模块   │───▶│  文本处理   │")
    print("└─────────────┘    └─────────────┘    └─────────────┘")
    print("                                             │")
    print("┌─────────────┐    ┌─────────────┐    ┌─────────────┐")
    print("│  Live2D动画  │◀───│   TTS模块   │◀───│   LLM引擎   │")
    print("└─────────────┘    └─────────────┘    └─────────────┘")
    print("       │                   │")
    print("┌─────────────┐    ┌─────────────┐")
    print("│   视觉输出   │    │   音频输出   │")
    print("└─────────────┘    └─────────────┘")


def print_requirements():
    """打印系统要求"""
    print("\n📋 系统要求:")
    print("=" * 30)
    print("• Python 3.9+")
    print("• NVIDIA GPU (推荐，用于AI加速)")
    print("• 4GB+ RAM")
    print("• 麦克风和扬声器")
    print("• API密钥 (OpenAI/Anthropic等)")
    
    print("\n🔧 依赖组件:")
    print("• OpenAI Whisper - 语音识别")
    print("• Coqui TTS - 语音合成")
    print("• PyAudio - 音频处理")
    print("• CustomTkinter - 现代UI")
    print("• NumPy/SciPy - 数值计算")


async def main():
    """主函数"""
    try:
        # 展示功能特性
        await show_features()
        
        # 运行文本聊天演示
        await simple_text_chat()
        
        # 显示系统要求
        print_requirements()
        
        print("\n🎉 感谢体验 Python Persona Engine!")
        print("🔗 原版项目: https://github.com/fagenorn/handcrafted-persona-engine")
        
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 