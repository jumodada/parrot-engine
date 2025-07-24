#!/usr/bin/env python3
"""
虚拟数字人系统性能优化工具
用于分析和优化系统性能
"""

import asyncio
import sys
import time
import psutil
import gc
from pathlib import Path
from typing import Dict, List, Tuple, Any

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent))

from src.core.avatar_engine import AvatarEngine, EngineConfig
from src.modules.live2d.hiyori_config import HiyoriConfig
from loguru import logger


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.engine = None
        self.config = None
        self.metrics = {}
        
    async def run_optimization(self):
        """运行性能优化"""
        logger.info("🚀 开始性能优化分析")
        
        # 系统性能基准测试
        await self.system_benchmark()
        
        # 内存使用分析
        await self.memory_analysis()
        
        # Live2D 性能优化
        await self.optimize_live2d()
        
        # 音频性能优化
        await self.optimize_audio()
        
        # 推流性能优化
        await self.optimize_streaming()
        
        # 生成优化报告
        self.generate_optimization_report()
        
        logger.info("✅ 性能优化完成！")
    
    async def system_benchmark(self):
        """系统性能基准测试"""
        logger.info("📊 执行系统性能基准测试...")
        
        # CPU 信息
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存信息
        memory = psutil.virtual_memory()
        
        # GPU 信息（如果可用）
        gpu_info = self._get_gpu_info()
        
        self.metrics['system'] = {
            'cpu_count': cpu_count,
            'cpu_frequency': cpu_freq.current if cpu_freq else 0,
            'cpu_usage': cpu_percent,
            'memory_total': memory.total / (1024**3),  # GB
            'memory_available': memory.available / (1024**3),  # GB
            'memory_usage_percent': memory.percent,
            'gpu_info': gpu_info
        }
        
        logger.info(f"CPU: {cpu_count} 核心, {cpu_freq.current if cpu_freq else 'N/A'} MHz")
        logger.info(f"内存: {memory.total / (1024**3):.1f} GB, 使用率: {memory.percent}%")
        logger.info(f"GPU: {gpu_info}")
    
    def _get_gpu_info(self) -> str:
        """获取 GPU 信息"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return f"{gpu.name} ({gpu.memoryTotal}MB)"
            else:
                return "未检测到 GPU"
        except ImportError:
            return "GPU 信息不可用（需要 GPUtil）"
        except Exception as e:
            return f"GPU 信息获取失败: {e}"
    
    async def memory_analysis(self):
        """内存使用分析"""
        logger.info("🧠 执行内存使用分析...")
        
        # 创建引擎实例进行内存分析
        config = EngineConfig()
        engine = AvatarEngine(config)
        
        # 测量初始化前的内存
        process = psutil.Process()
        memory_before = process.memory_info().rss / (1024**2)  # MB
        
        # 初始化引擎
        await engine.initialize()
        
        # 测量初始化后的内存
        memory_after = process.memory_info().rss / (1024**2)  # MB
        memory_used = memory_after - memory_before
        
        # 强制垃圾回收
        gc.collect()
        memory_after_gc = process.memory_info().rss / (1024**2)  # MB
        
        self.metrics['memory'] = {
            'before_init': memory_before,
            'after_init': memory_after,
            'initialization_cost': memory_used,
            'after_gc': memory_after_gc,
            'gc_freed': memory_after - memory_after_gc
        }
        
        logger.info(f"初始化前内存: {memory_before:.1f} MB")
        logger.info(f"初始化后内存: {memory_after:.1f} MB")
        logger.info(f"初始化内存成本: {memory_used:.1f} MB")
        logger.info(f"垃圾回收释放: {memory_after - memory_after_gc:.1f} MB")
        
        # 清理引擎
        await engine.cleanup()
        self.engine = engine
    
    async def optimize_live2d(self):
        """Live2D 性能优化"""
        logger.info("🎭 执行 Live2D 性能优化...")
        
        if not self.engine or not self.engine.live2d_manager:
            logger.warning("Live2D 管理器未初始化，跳过优化")
            return
        
        # 获取当前性能统计
        perf_stats = self.engine.live2d_manager.get_performance_stats()
        
        # 优化建议
        optimizations = []
        
        # 检查参数数量
        param_count = perf_stats.get('parameter_count', 0)
        if param_count > 50:
            optimizations.append("建议减少不必要的参数以提升性能")
        
        # 检查表情数量
        expr_count = perf_stats.get('expression_count', 0)
        if expr_count > 20:
            optimizations.append("建议减少表情数量或使用预缓存")
        
        # 检查 FPS 设置
        current_fps = perf_stats.get('current_fps', 60)
        if current_fps > 30:
            optimizations.append("对于流畅体验，可以考虑降低到 30 FPS")
        
        self.metrics['live2d'] = {
            'performance_stats': perf_stats,
            'optimizations': optimizations
        }
        
        logger.info(f"参数数量: {param_count}")
        logger.info(f"表情数量: {expr_count}")
        logger.info(f"目标 FPS: {current_fps}")
        
        for opt in optimizations:
            logger.info(f"💡 优化建议: {opt}")
    
    async def optimize_audio(self):
        """音频性能优化"""
        logger.info("🔊 执行音频性能优化...")
        
        if not self.engine or not self.engine.audio_manager:
            logger.warning("音频管理器未初始化，跳过优化")
            return
        
        # 获取音频信息
        audio_info = self.engine.audio_manager.get_audio_info()
        
        # 优化建议
        optimizations = []
        
        # 检查采样率
        sample_rate = audio_info.get('input_sample_rate', 16000)
        if sample_rate > 16000:
            optimizations.append("对于语音识别，16kHz 采样率通常足够")
        
        # 检查缓冲区大小
        buffer_size = audio_info.get('buffer_size', 1024)
        if buffer_size < 512:
            optimizations.append("缓冲区过小可能导致音频断裂")
        elif buffer_size > 2048:
            optimizations.append("缓冲区过大会增加延迟")
        
        self.metrics['audio'] = {
            'audio_info': audio_info,
            'optimizations': optimizations
        }
        
        logger.info(f"采样率: {sample_rate} Hz")
        logger.info(f"缓冲区大小: {buffer_size}")
        
        for opt in optimizations:
            logger.info(f"💡 优化建议: {opt}")
    
    async def optimize_streaming(self):
        """推流性能优化"""
        logger.info("📺 执行推流性能优化...")
        
        if not self.engine or not self.engine.spout_streamer:
            logger.warning("推流器未初始化，跳过优化")
            return
        
        # 获取推流统计
        streaming_stats = self.engine.spout_streamer.get_streaming_stats()
        
        # 优化建议
        optimizations = []
        
        # 检查分辨率
        resolution = streaming_stats.get('resolution', '1080x1920')
        width, height = map(int, resolution.split('x'))
        if width > 1920 or height > 1080:
            optimizations.append("高分辨率会显著影响性能，考虑降低到 1080p")
        
        # 检查 FPS
        target_fps = streaming_stats.get('target_fps', 60)
        if target_fps > 30:
            optimizations.append("对于推流，30 FPS 通常已足够")
        
        # 检查队列大小
        queue_size = streaming_stats.get('queue_size', 0)
        if queue_size > 5:
            optimizations.append("队列积压可能表示处理跟不上生成速度")
        
        self.metrics['streaming'] = {
            'streaming_stats': streaming_stats,
            'optimizations': optimizations
        }
        
        logger.info(f"推流分辨率: {resolution}")
        logger.info(f"目标 FPS: {target_fps}")
        logger.info(f"队列大小: {queue_size}")
        
        for opt in optimizations:
            logger.info(f"💡 优化建议: {opt}")
    
    def generate_optimization_report(self):
        """生成优化报告"""
        logger.info("📋 生成优化报告...")
        
        report_path = Path("performance_report.txt")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("虚拟数字人系统性能优化报告\n")
            f.write("=" * 50 + "\n\n")
            
            # 系统信息
            f.write("系统信息:\n")
            f.write("-" * 20 + "\n")
            system_info = self.metrics.get('system', {})
            for key, value in system_info.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # 内存分析
            if 'memory' in self.metrics:
                f.write("内存分析:\n")
                f.write("-" * 20 + "\n")
                memory_info = self.metrics['memory']
                for key, value in memory_info.items():
                    f.write(f"{key}: {value:.1f} MB\n")
                f.write("\n")
            
            # 各模块优化建议
            modules = ['live2d', 'audio', 'streaming']
            for module in modules:
                if module in self.metrics:
                    f.write(f"{module.upper()} 模块优化:\n")
                    f.write("-" * 20 + "\n")
                    optimizations = self.metrics[module].get('optimizations', [])
                    if optimizations:
                        for opt in optimizations:
                            f.write(f"• {opt}\n")
                    else:
                        f.write("无优化建议\n")
                    f.write("\n")
            
            # 总结
            f.write("总结:\n")
            f.write("-" * 20 + "\n")
            f.write("1. 监控内存使用，定期进行垃圾回收\n")
            f.write("2. 根据实际需求调整 FPS 和分辨率\n")
            f.write("3. 优化参数数量和表情缓存\n")
            f.write("4. 确保音频缓冲区设置合理\n")
            f.write("5. 定期检查推流队列状态\n")
        
        logger.info(f"📄 优化报告已保存到: {report_path}")
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.engine:
                await self.engine.cleanup()
            logger.info("🧹 性能优化器清理完成")
        except Exception as e:
            logger.error(f"清理失败: {e}")


async def main():
    """主函数"""
    logger.info("🎯 虚拟数字人系统性能优化开始")
    
    optimizer = PerformanceOptimizer()
    
    try:
        await optimizer.run_optimization()
        logger.info("🎉 性能优化完成！")
        return 0
        
    except KeyboardInterrupt:
        logger.info("⏹️ 优化被用户中断")
        return 1
    except Exception as e:
        logger.error(f"💥 优化过程中发生错误: {e}")
        return 1
    finally:
        await optimizer.cleanup()


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO"
    )
    
    # 运行优化
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 