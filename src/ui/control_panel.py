"""
控制面板UI
使用CustomTkinter创建现代化的控制界面
"""

import asyncio
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from typing import Optional, Callable, Dict, Any
from loguru import logger
import threading
import time

from ..core.avatar_engine import AvatarEngine, EngineState
from ..utils.config import Config


class ControlPanel:
    """控制面板主类"""
    
    def __init__(self, engine: AvatarEngine, config: Config):
        self.engine = engine
        self.config = config
        
        # UI组件
        self.root: Optional[ctk.CTk] = None
        self.status_frame: Optional[ctk.CTkFrame] = None
        self.metrics_frame: Optional[ctk.CTkFrame] = None
        self.controls_frame: Optional[ctk.CTkFrame] = None
        self.chat_frame: Optional[ctk.CTkFrame] = None
        
        # 状态显示
        self.status_label: Optional[ctk.CTkLabel] = None
        self.state_label: Optional[ctk.CTkLabel] = None
        
        # 性能指标
        self.asr_latency_label: Optional[ctk.CTkLabel] = None
        self.llm_latency_label: Optional[ctk.CTkLabel] = None
        self.tts_latency_label: Optional[ctk.CTkLabel] = None
        self.total_latency_label: Optional[ctk.CTkLabel] = None
        
        # 控制按钮
        self.start_button: Optional[ctk.CTkButton] = None
        self.stop_button: Optional[ctk.CTkButton] = None
        self.test_button: Optional[ctk.CTkButton] = None
        
        # 聊天界面
        self.chat_display: Optional[ctk.CTkTextbox] = None
        self.message_entry: Optional[ctk.CTkEntry] = None
        self.send_button: Optional[ctk.CTkButton] = None
        
        # 配置控件
        self.volume_slider: Optional[ctk.CTkSlider] = None
        self.speed_slider: Optional[ctk.CTkSlider] = None
        
        # 更新控制
        self._update_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info("控制面板初始化")

    def initialize(self):
        """初始化UI"""
        try:
            # 设置主题
            ctk.set_appearance_mode(self.config.ui.theme)
            ctk.set_default_color_theme("blue")
            
            # 创建主窗口
            self.root = ctk.CTk()
            self.root.title(self.config.window.title)
            self.root.geometry("800x600")
            
            # 设置窗口属性
            if self.config.ui.always_on_top:
                self.root.wm_attributes("-topmost", True)
                
            # 创建UI布局
            self._create_layout()
            
            # 绑定事件
            self._bind_events()
            
            # 注册引擎回调
            self._register_engine_callbacks()
            
            logger.info("控制面板UI初始化完成")
            
        except Exception as e:
            logger.error(f"控制面板初始化失败: {e}")
            raise

    def _create_layout(self):
        """创建UI布局"""
        # 配置网格权重
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # 状态栏
        self._create_status_frame()
        
        # 性能指标
        self._create_metrics_frame()
        
        # 控制面板
        self._create_controls_frame()
        
        # 聊天界面
        self._create_chat_frame()

    def _create_status_frame(self):
        """创建状态栏"""
        self.status_frame = ctk.CTkFrame(self.root)
        self.status_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            self.status_frame, 
            text="引擎状态: 未启动",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5)
        
        # 当前状态
        self.state_label = ctk.CTkLabel(
            self.status_frame,
            text="STOPPED",
            font=ctk.CTkFont(size=12),
            text_color="red"
        )
        self.state_label.grid(row=0, column=1, padx=10, pady=5)
        
        # 时间显示
        self.time_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            font=ctk.CTkFont(size=10)
        )
        self.time_label.grid(row=0, column=2, padx=10, pady=5)

    def _create_metrics_frame(self):
        """创建性能指标框架"""
        self.metrics_frame = ctk.CTkFrame(self.root)
        self.metrics_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        # 标题
        title_label = ctk.CTkLabel(
            self.metrics_frame,
            text="性能指标",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        # ASR延迟
        ctk.CTkLabel(self.metrics_frame, text="ASR延迟:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.asr_latency_label = ctk.CTkLabel(self.metrics_frame, text="0.00ms")
        self.asr_latency_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # LLM延迟
        ctk.CTkLabel(self.metrics_frame, text="LLM延迟:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.llm_latency_label = ctk.CTkLabel(self.metrics_frame, text="0.00ms")
        self.llm_latency_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # TTS延迟
        ctk.CTkLabel(self.metrics_frame, text="TTS延迟:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.tts_latency_label = ctk.CTkLabel(self.metrics_frame, text="0.00ms")
        self.tts_latency_label.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        
        # 总延迟
        ctk.CTkLabel(self.metrics_frame, text="总延迟:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.total_latency_label = ctk.CTkLabel(self.metrics_frame, text="0.00ms")
        self.total_latency_label.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        
        # 交互次数
        ctk.CTkLabel(self.metrics_frame, text="交互次数:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.interactions_label = ctk.CTkLabel(self.metrics_frame, text="0")
        self.interactions_label.grid(row=5, column=1, padx=10, pady=5, sticky="w")

    def _create_controls_frame(self):
        """创建控制面板"""
        self.controls_frame = ctk.CTkFrame(self.root)
        self.controls_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        # 标题
        title_label = ctk.CTkLabel(
            self.controls_frame,
            text="引擎控制",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, padx=10, pady=10)
        
        # 控制按钮
        self.start_button = ctk.CTkButton(
            self.controls_frame,
            text="启动引擎",
            command=self._on_start_clicked
        )
        self.start_button.grid(row=1, column=0, padx=10, pady=5)
        
        self.stop_button = ctk.CTkButton(
            self.controls_frame,
            text="停止引擎",
            command=self._on_stop_clicked,
            state="disabled"
        )
        self.stop_button.grid(row=1, column=1, padx=10, pady=5)
        
        self.test_button = ctk.CTkButton(
            self.controls_frame,
            text="测试功能",
            command=self._on_test_clicked
        )
        self.test_button.grid(row=1, column=2, padx=10, pady=5)
        
        # 音量控制
        ctk.CTkLabel(self.controls_frame, text="音量:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.volume_slider = ctk.CTkSlider(
            self.controls_frame,
            from_=0.0,
            to=1.0,
            number_of_steps=100,
            command=self._on_volume_changed
        )
        self.volume_slider.set(self.config.audio.volume)
        self.volume_slider.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        
        # 语速控制
        ctk.CTkLabel(self.controls_frame, text="语速:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.speed_slider = ctk.CTkSlider(
            self.controls_frame,
            from_=0.5,
            to=2.0,
            number_of_steps=30,
            command=self._on_speed_changed
        )
        self.speed_slider.set(self.config.tts.speed)
        self.speed_slider.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

    def _create_chat_frame(self):
        """创建聊天界面"""
        self.chat_frame = ctk.CTkFrame(self.root)
        self.chat_frame.grid(row=1, column=1, rowspan=2, padx=10, pady=5, sticky="nsew")
        
        # 标题
        title_label = ctk.CTkLabel(
            self.chat_frame,
            text="聊天记录",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=10, pady=10)
        
        # 聊天显示区域
        self.chat_display = ctk.CTkTextbox(
            self.chat_frame,
            wrap="word",
            state="disabled"
        )
        self.chat_display.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        # 输入框架
        input_frame = ctk.CTkFrame(self.chat_frame)
        input_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        # 消息输入框
        self.message_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="输入消息..."
        )
        self.message_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # 发送按钮
        self.send_button = ctk.CTkButton(
            input_frame,
            text="发送",
            width=60,
            command=self._on_send_clicked
        )
        self.send_button.grid(row=0, column=1, padx=5, pady=5)
        
        # 配置聊天框架的网格权重
        self.chat_frame.grid_rowconfigure(1, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

    def _bind_events(self):
        """绑定事件"""
        # 回车发送消息
        self.message_entry.bind("<Return>", lambda e: self._on_send_clicked())
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_closing)

    def _register_engine_callbacks(self):
        """注册引擎回调"""
        self.engine.on_state_changed = self._on_engine_state_changed
        self.engine.on_text_recognized = self._on_text_recognized
        self.engine.on_response_generated = self._on_response_generated

    def _on_start_clicked(self):
        """启动按钮点击事件"""
        try:
            # 在后台启动引擎
            threading.Thread(target=self._start_engine_sync, daemon=True).start()
            
            # 更新按钮状态
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            
        except Exception as e:
            logger.error(f"启动引擎失败: {e}")
            messagebox.showerror("错误", f"启动引擎失败: {e}")

    def _start_engine_sync(self):
        """同步启动引擎"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.engine.start())
        except Exception as e:
            logger.error(f"引擎启动失败: {e}")

    def _on_stop_clicked(self):
        """停止按钮点击事件"""
        try:
            # 在后台停止引擎
            threading.Thread(target=self._stop_engine_sync, daemon=True).start()
            
            # 更新按钮状态
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            
        except Exception as e:
            logger.error(f"停止引擎失败: {e}")
            messagebox.showerror("错误", f"停止引擎失败: {e}")

    def _stop_engine_sync(self):
        """同步停止引擎"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.engine.stop())
        except Exception as e:
            logger.error(f"引擎停止失败: {e}")

    def _on_test_clicked(self):
        """测试按钮点击事件"""
        try:
            # 显示测试消息
            self._add_chat_message("系统", "正在进行功能测试...")
            
            # 在后台执行测试
            threading.Thread(target=self._run_tests_sync, daemon=True).start()
            
        except Exception as e:
            logger.error(f"测试失败: {e}")
            messagebox.showerror("错误", f"测试失败: {e}")

    def _run_tests_sync(self):
        """同步运行测试"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 测试各个模块
            test_results = {}
            
            if self.engine.asr:
                test_results["ASR"] = loop.run_until_complete(self._test_asr())
            if self.engine.tts:
                test_results["TTS"] = loop.run_until_complete(self._test_tts())
            if self.engine.llm:
                test_results["LLM"] = loop.run_until_complete(self._test_llm())
            if self.engine.audio:
                test_results["Audio"] = loop.run_until_complete(self._test_audio())
            
            # 显示测试结果
            self.root.after(0, lambda: self._show_test_results(test_results))
            
        except Exception as e:
            logger.error(f"测试执行失败: {e}")

    async def _test_asr(self) -> bool:
        """测试ASR模块"""
        try:
            model_info = self.engine.asr.get_model_info()
            return model_info["status"] == "initialized"
        except:
            return False

    async def _test_tts(self) -> bool:
        """测试TTS模块"""
        try:
            return await self.engine.tts.test_synthesis()
        except:
            return False

    async def _test_llm(self) -> bool:
        """测试LLM模块"""
        try:
            return await self.engine.llm.test_model()
        except:
            return False

    async def _test_audio(self) -> bool:
        """测试音频模块"""
        try:
            return await self.engine.audio.test_audio_io()
        except:
            return False

    def _show_test_results(self, results: Dict[str, bool]):
        """显示测试结果"""
        message = "测试结果:\n"
        for module, success in results.items():
            status = "✓ 通过" if success else "✗ 失败"
            message += f"  {module}: {status}\n"
        
        self._add_chat_message("系统", message)

    def _on_send_clicked(self):
        """发送按钮点击事件"""
        try:
            message = self.message_entry.get().strip()
            if not message:
                return
                
            # 清空输入框
            self.message_entry.delete(0, tk.END)
            
            # 显示用户消息
            self._add_chat_message("用户", message)
            
            # 在后台发送消息
            threading.Thread(target=self._send_message_sync, args=(message,), daemon=True).start()
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    def _send_message_sync(self, message: str):
        """同步发送消息"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(self.engine.send_text_message(message))
            
            if response:
                # 在主线程中显示回复
                self.root.after(0, lambda: self._add_chat_message("Aria", response))
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    def _on_volume_changed(self, value: float):
        """音量滑块变化事件"""
        try:
            if self.engine.audio:
                self.engine.audio.update_volume(value)
        except Exception as e:
            logger.error(f"更新音量失败: {e}")

    def _on_speed_changed(self, value: float):
        """语速滑块变化事件"""
        try:
            if self.engine.tts:
                self.engine.tts.update_config(speed=value)
        except Exception as e:
            logger.error(f"更新语速失败: {e}")

    def _on_engine_state_changed(self, state: EngineState):
        """引擎状态变化回调"""
        try:
            # 在主线程中更新UI
            self.root.after(0, lambda: self._update_state_display(state))
        except Exception as e:
            logger.error(f"更新状态显示失败: {e}")

    def _update_state_display(self, state: EngineState):
        """更新状态显示"""
        state_colors = {
            EngineState.STOPPED: "red",
            EngineState.STARTING: "orange",
            EngineState.LISTENING: "green",
            EngineState.PROCESSING: "blue",
            EngineState.SPEAKING: "purple",
            EngineState.ERROR: "red"
        }
        
        state_texts = {
            EngineState.STOPPED: "已停止",
            EngineState.STARTING: "启动中",
            EngineState.LISTENING: "监听中",
            EngineState.PROCESSING: "处理中",
            EngineState.SPEAKING: "说话中",
            EngineState.ERROR: "错误"
        }
        
        self.state_label.configure(
            text=state_texts.get(state, "未知"),
            text_color=state_colors.get(state, "gray")
        )
        
        # 更新状态标签
        self.status_label.configure(text=f"引擎状态: {state_texts.get(state, '未知')}")

    def _on_text_recognized(self, text: str):
        """文本识别回调"""
        try:
            self.root.after(0, lambda: self._add_chat_message("识别", text))
        except Exception as e:
            logger.error(f"显示识别文本失败: {e}")

    def _on_response_generated(self, text: str):
        """响应生成回调"""
        try:
            self.root.after(0, lambda: self._add_chat_message("Aria", text))
        except Exception as e:
            logger.error(f"显示响应文本失败: {e}")

    def _add_chat_message(self, sender: str, message: str):
        """添加聊天消息"""
        try:
            self.chat_display.configure(state="normal")
            
            # 添加时间戳
            timestamp = time.strftime("%H:%M:%S")
            
            # 格式化消息
            formatted_message = f"[{timestamp}] {sender}: {message}\n"
            
            self.chat_display.insert(tk.END, formatted_message)
            self.chat_display.configure(state="disabled")
            
            # 自动滚动到底部
            self.chat_display.see(tk.END)
            
        except Exception as e:
            logger.error(f"添加聊天消息失败: {e}")

    def _on_window_closing(self):
        """窗口关闭事件"""
        try:
            self._running = False
            
            # 停止引擎
            if self.engine.get_state() != EngineState.STOPPED:
                threading.Thread(target=self._stop_engine_sync, daemon=True).start()
            
            # 关闭窗口
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"窗口关闭失败: {e}")

    def start_update_loop(self):
        """启动UI更新循环"""
        self._running = True
        self._update_loop()

    def _update_loop(self):
        """UI更新循环"""
        try:
            if not self._running:
                return
                
            # 更新时间显示
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.configure(text=current_time)
            
            # 更新性能指标
            if self.config.ui.show_metrics:
                self._update_metrics_display()
            
            # 安排下次更新
            self.root.after(1000, self._update_loop)  # 每秒更新一次
            
        except Exception as e:
            logger.error(f"UI更新循环失败: {e}")

    def _update_metrics_display(self):
        """更新性能指标显示"""
        try:
            metrics = self.engine.get_metrics()
            
            self.asr_latency_label.configure(text=f"{metrics['asr_latency']:.2f}ms")
            self.llm_latency_label.configure(text=f"{metrics['llm_latency']:.2f}ms")
            self.tts_latency_label.configure(text=f"{metrics['tts_latency']:.2f}ms")
            self.total_latency_label.configure(text=f"{metrics['total_latency']:.2f}ms")
            self.interactions_label.configure(text=str(metrics['interactions_count']))
            
        except Exception as e:
            logger.error(f"更新性能指标失败: {e}")

    def run(self):
        """运行UI"""
        try:
            # 启动更新循环
            self.start_update_loop()
            
            # 运行主循环
            self.root.mainloop()
            
        except Exception as e:
            logger.error(f"UI运行失败: {e}")
            raise 