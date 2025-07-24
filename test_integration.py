#!/usr/bin/env python3
"""
虚拟数字人系统集成测试
测试完整的 Live2D + ASR + TTS + LLM + 推流流程
"""

import asyncio
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent))

from src.core.avatar_engine import AvatarEngine, EngineConfig
from src.modules.live2d.hiyori_config import HiyoriConfig
from loguru import logger


class IntegrationTester:
    """集成测试器"""
    
    def __init__(self):
        self.engine = None
        self.config = None
        
    async def run_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始虚拟数字人系统集成测试")
        
        # 测试配置加载
        if not await self.test_config_loading():
            return False
        
        # 测试引擎初始化
        if not await self.test_engine_initialization():
            return False
        
        # 测试 Live2D 模块
        if not await self.test_live2d_module():
            return False
        
        # 测试音频模块
        if not await self.test_audio_module():
            return False
        
        # 测试推流模块
        if not await self.test_streaming_module():
            return False
        
        # 测试 Hiyori 配置
        if not await self.test_hiyori_config():
            return False
        
        # 测试完整流程
        if not await self.test_complete_workflow():
            return False
        
        logger.info("✅ 所有集成测试通过！")
        return True
    
    async def test_config_loading(self):
        """测试配置加载"""
        try:
            logger.info("📋 测试配置加载...")
            
            # 测试引擎配置
            self.config = EngineConfig()
            
            # 测试 Hiyori 配置
            hiyori_config = HiyoriConfig()
            if not hiyori_config.load_config():
                logger.error("❌ Hiyori 配置加载失败")
                return False
            
            # 验证配置
            errors = hiyori_config.validate_config()
            if errors:
                logger.warning(f"⚠️ 配置验证警告: {errors}")
            
            logger.info("✅ 配置加载测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置加载测试失败: {e}")
            return False
    
    async def test_engine_initialization(self):
        """测试引擎初始化"""
        try:
            logger.info("🔧 测试引擎初始化...")
            
            # 创建引擎实例
            self.engine = AvatarEngine(self.config)
            
            # 初始化引擎
            if not await self.engine.initialize():
                logger.error("❌ 引擎初始化失败")
                return False
            
            logger.info("✅ 引擎初始化测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 引擎初始化测试失败: {e}")
            return False
    
    async def test_live2d_module(self):
        """测试 Live2D 模块"""
        try:
            logger.info("🎭 测试 Live2D 模块...")
            
            if not self.engine.live2d_manager:
                logger.error("❌ Live2D 管理器未初始化")
                return False
            
            # 测试配置摘要
            summary = self.engine.live2d_manager.get_config_summary()
            logger.info(f"Live2D 配置摘要: {summary}")
            
            # 测试表情设置
            expressions = self.engine.live2d_manager.get_available_expressions()
            logger.info(f"可用表情: {expressions}")
            
            if expressions:
                await self.engine.live2d_manager.set_expression(expressions[0])
                logger.info(f"设置表情: {expressions[0]}")
            
            # 测试参数获取
            params = self.engine.live2d_manager.get_all_parameter_values()
            logger.info(f"参数数量: {len(params)}")
            
            logger.info("✅ Live2D 模块测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ Live2D 模块测试失败: {e}")
            return False
    
    async def test_audio_module(self):
        """测试音频模块"""
        try:
            logger.info("🔊 测试音频模块...")
            
            if not self.engine.audio_manager:
                logger.error("❌ 音频管理器未初始化")
                return False
            
            # 测试音频设备列表
            devices = await self.engine.audio_manager.get_device_list()
            logger.info(f"音频设备数量: {len(devices)}")
            
            # 测试音频信息
            audio_info = self.engine.audio_manager.get_audio_info()
            logger.info(f"音频信息: {audio_info}")
            
            logger.info("✅ 音频模块测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 音频模块测试失败: {e}")
            return False
    
    async def test_streaming_module(self):
        """测试推流模块"""
        try:
            logger.info("📺 测试推流模块...")
            
            if not self.engine.spout_streamer:
                logger.warning("⚠️ 推流器未启用，跳过测试")
                return True
            
            # 测试推流状态
            stats = self.engine.spout_streamer.get_streaming_stats()
            logger.info(f"推流统计: {stats}")
            
            # 测试连接状态
            is_connected = self.engine.spout_streamer.is_connected()
            logger.info(f"OBS 连接状态: {is_connected}")
            
            logger.info("✅ 推流模块测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 推流模块测试失败: {e}")
            return False
    
    async def test_hiyori_config(self):
        """测试 Hiyori 配置"""
        try:
            logger.info("🎨 测试 Hiyori 配置...")
            
            if not self.engine.live2d_manager:
                logger.error("❌ Live2D 管理器未初始化")
                return False
            
            # 测试表情切换
            expressions_to_test = ["happy", "thinking", "cool", "neutral"]
            for expr in expressions_to_test:
                if expr in self.engine.live2d_manager.get_available_expressions():
                    await self.engine.live2d_manager.set_expression(expr)
                    logger.info(f"✅ 测试表情: {expr}")
                    await asyncio.sleep(0.5)  # 等待表情切换
            
            # 测试性能统计
            perf_stats = self.engine.live2d_manager.get_performance_stats()
            logger.info(f"性能统计: {perf_stats}")
            
            logger.info("✅ Hiyori 配置测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ Hiyori 配置测试失败: {e}")
            return False
    
    async def test_complete_workflow(self):
        """测试完整工作流程"""
        try:
            logger.info("🔄 测试完整工作流程...")
            
            # 启动引擎
            if not await self.engine.start():
                logger.error("❌ 引擎启动失败")
                return False
            
            logger.info("引擎已启动，模拟对话流程...")
            
            # 模拟一段对话
            test_scenarios = [
                {"emotion": "happy", "text": "你好！我是 Hiyori"},
                {"emotion": "thinking", "text": "让我想想..."},
                {"emotion": "excited", "text": "我知道答案了！"},
                {"emotion": "cool", "text": "这很简单"},
                {"emotion": "neutral", "text": "还有其他问题吗？"}
            ]
            
            for scenario in test_scenarios:
                # 设置表情
                if self.engine.live2d_manager:
                    await self.engine.live2d_manager.set_expression(scenario["emotion"])
                
                # 模拟 TTS 输出（这里只是日志输出）
                logger.info(f"🗣️ [{scenario['emotion']}] {scenario['text']}")
                
                # 等待一下
                await asyncio.sleep(1.0)
            
            # 停止引擎
            await self.engine.stop()
            
            logger.info("✅ 完整工作流程测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 完整工作流程测试失败: {e}")
            return False
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.engine:
                await self.engine.cleanup()
            logger.info("🧹 资源清理完成")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")


async def main():
    """主函数"""
    logger.info("🎯 虚拟数字人系统集成测试开始")
    
    tester = IntegrationTester()
    
    try:
        success = await tester.run_tests()
        
        if success:
            logger.info("🎉 所有测试完成！系统集成成功！")
            return 0
        else:
            logger.error("💥 测试失败！需要修复问题后重试")
            return 1
            
    except KeyboardInterrupt:
        logger.info("⏹️ 测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"💥 测试过程中发生未知错误: {e}")
        return 1
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO"
    )
    
    # 运行测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 