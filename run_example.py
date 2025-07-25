#!/usr/bin/env python3
"""
Python Persona Engine 示例脚本
用于展示基本功能和测试安装
"""

import asyncio
import os
import sys
import random
from typing import List, Dict
import threading

# 检查tkinter可用性
TKINTER_AVAILABLE = False
try:
    import tkinter as tk
    from tkinter import scrolledtext
    TKINTER_AVAILABLE = True
except ImportError:
    print("⚠️  tkinter 不可用，将使用命令行模式")
    tk = None
    scrolledtext = None

# 检查customtkinter可用性
try:
    import customtkinter as ctk
except ImportError:
    if TKINTER_AVAILABLE:
        print("未安装customtkinter，使用标准tkinter")
    ctk = None


def simple_text_chat():
    """简单的文本聊天演示"""
    
    if not TKINTER_AVAILABLE:
        # 使用命令行模式
        return simple_console_chat()
    
    # 预设回复
    responses = [
        "很高兴能和你聊天！",
        "我是Python Persona Engine的示例角色。我还没有连接到真正的AI引擎。",
        "如果你想使用完整功能，请配置config.yaml中的API密钥。",
        "我可以模拟对话、语音识别和文本转语音等功能。",
        "这只是个简单演示，完整引擎支持Live2D角色动画！",
        "有关如何设置和使用的详细信息，请查看README.md。",
        "你可以使用OpenAI、Anthropic或本地的LLM模型作为我的大脑。"
    ]
    
    # 创建简单UI
    root = ctk.CTk() if ctk else tk.Tk()
    root.title("Python Persona Engine 演示")
    root.geometry("600x800")
    
    frame = ctk.CTkFrame(root) if ctk else tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # 对话区域
    chat_label = ctk.CTkLabel(frame, text="聊天记录") if ctk else tk.Label(frame, text="聊天记录")
    chat_label.pack(pady=(0, 5), anchor="w")
    
    chat_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=20)
    chat_area.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
    chat_area.insert(tk.END, "助手: 你好！我是Python Persona Engine的示例角色。请输入消息与我聊天。\n\n")
    chat_area.config(state=tk.DISABLED)
    
    # 输入区域
    input_label = ctk.CTkLabel(frame, text="输入消息") if ctk else tk.Label(frame, text="输入消息")
    input_label.pack(pady=(0, 5), anchor="w")
    
    input_area = ctk.CTkTextbox(frame, height=80) if ctk else tk.Text(frame, height=4)
    input_area.pack(fill=tk.X, pady=(0, 10))
    
    # 状态区域
    status_var = tk.StringVar()
    status_var.set("准备就绪")
    status_label = ctk.CTkLabel(frame, textvariable=status_var) if ctk else tk.Label(frame, textvariable=status_var)
    status_label.pack(pady=5)
    
    # 发送函数
    def send_message():
        msg = input_area.get("1.0", tk.END).strip()
        if not msg:
            return
            
        # 禁用输入
        input_area.config(state=tk.DISABLED)
        status_var.set("思考中...")
        
        # 更新聊天记录
        chat_area.config(state=tk.NORMAL)
        chat_area.insert(tk.END, f"用户: {msg}\n\n")
        chat_area.see(tk.END)
        chat_area.config(state=tk.DISABLED)
        
        # 清空输入
        input_area.delete("1.0", tk.END)
        
        # 模拟处理延迟
        def delayed_response():
            response = random.choice(responses)
            
            chat_area.config(state=tk.NORMAL)
            chat_area.insert(tk.END, f"助手: {response}\n\n")
            chat_area.see(tk.END)
            chat_area.config(state=tk.DISABLED)
            
            status_var.set("准备就绪")
            input_area.config(state=tk.NORMAL)
            input_area.focus()
            
        # 模拟延迟
        threading.Timer(1.0, delayed_response).start()
    
    # 按钮
    button_frame = ctk.CTkFrame(frame) if ctk else tk.Frame(frame)
    button_frame.pack(fill=tk.X, pady=10)
    
    send_button = ctk.CTkButton(button_frame, text="发送", command=send_message) if ctk else tk.Button(button_frame, text="发送", command=send_message)
    send_button.pack(side=tk.RIGHT)
    
    quit_button = ctk.CTkButton(button_frame, text="退出", command=root.destroy) if ctk else tk.Button(button_frame, text="退出", command=root.destroy)
    quit_button.pack(side=tk.LEFT)
    
    # 绑定回车键
    input_area.bind("<Return>", lambda event: send_message())
    
    root.mainloop()


def simple_console_chat():
    """命令行聊天演示"""
    
    # 预设回复
    responses = [
        "很高兴能和你聊天！",
        "我是Python Persona Engine的示例角色。我还没有连接到真正的AI引擎。",
        "如果你想使用完整功能，请配置config.yaml中的API密钥。",
        "我可以模拟对话、语音识别和文本转语音等功能。",
        "这只是个简单演示，完整引擎支持Live2D角色动画！",
        "有关如何设置和使用的详细信息，请查看README.md。",
        "你可以使用OpenAI、Anthropic或本地的LLM模型作为我的大脑。"
    ]
    
    print("\n" + "="*60)
    print("🎭 Python Persona Engine 命令行聊天演示")
    print("="*60)
    print("助手: 你好！我是Python Persona Engine的示例角色。")
    print("助手: 请输入消息与我聊天，输入 'quit' 或 'exit' 退出。")
    print("="*60)
    
    while True:
        try:
            # 获取用户输入
            user_input = input("\n用户: ").strip()
            
            # 检查退出命令
            if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                print("\n助手: 再见！感谢使用 Python Persona Engine！")
                break
            
            if not user_input:
                continue
            
            # 模拟思考延迟
            print("助手: [思考中...]", end="", flush=True)
            import time
            time.sleep(1)
            print("\r", end="")  # 清除思考提示
            
            # 随机选择回复
            response = random.choice(responses)
            print(f"助手: {response}")
            
        except KeyboardInterrupt:
            print("\n\n助手: 再见！感谢使用 Python Persona Engine！")
            break
        except EOFError:
            print("\n\n助手: 再见！感谢使用 Python Persona Engine！")
            break


def show_features():
    """展示功能列表"""
    print("\n🎭 Python Persona Engine 功能列表")
    print("=" * 40)
    
    features = [
        ("🗣️ 语音交互", "使用Whisper语音识别和TTS语音合成"),
        ("🧠 大语言模型", "支持OpenAI, Anthropic, Ollama等"),
        ("👁️ 视觉感知", "可以看到并理解屏幕内容"),
        ("😀 Live2D动画", "生动的角色表情和口型同步"),
        ("🎛️ 控制面板", "直观的图形用户界面"),
        ("⚙️ 灵活配置", "通过YAML文件轻松配置所有功能"),
    ]
    
    for title, desc in features:
        print(f"{title}: {desc}")
    
    print("\n要启用完整功能，请配置config.yaml文件中的API密钥。")


def print_requirements():
    """打印系统要求"""
    print("\n🖥️ 系统要求")
    print("=" * 40)
    print("- Python 3.9+")
    print("- 推荐NVIDIA GPU (用于语音识别、Live2D渲染)")
    print("- 以下系统依赖:")
    print("  • espeak-ng: 用于基本TTS")
    print("  • ffmpeg: 用于音频处理")
    print("\n要安装系统依赖:")
    print("- macOS: brew install espeak-ng ffmpeg")
    print("- Ubuntu/Debian: sudo apt-get install espeak-ng ffmpeg")
    print("- Windows: 请参考QUICKSTART.md中的安装说明")


def main():
    """主函数"""
    print("🎭 Python Persona Engine 示例脚本")
    
    # 显示功能列表
    show_features()
    
    # 显示系统要求
    print_requirements()
    
    # 检查tkinter状态
    if not TKINTER_AVAILABLE:
        print("\n⚠️  GUI 环境检测")
        print("=" * 40)
        print("tkinter 不可用，这通常发生在以下情况:")
        print("1. 使用 pyenv 安装的 Python 没有 tkinter 支持")
        print("2. 在服务器环境或 Docker 容器中运行")
        print("3. macOS 上缺少 Tk 框架")
        print("\n解决方案:")
        print("- macOS: brew install python-tk 或重新安装 Python")
        print("- 或者使用命令行模式: python run_example.py --console")
        print("\n将自动使用命令行模式...")
    
    # 检查是否有命令行参数
    console_mode = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "--no-ui":
            return
        elif sys.argv[1] in ["--console", "--cli"]:
            console_mode = True
    
    # 如果没有tkinter或指定了命令行模式，使用命令行聊天
    if not TKINTER_AVAILABLE or console_mode:
        print("\n启动命令行聊天演示...")
        simple_console_chat()
    else:
        # 运行GUI演示
        print("\n启动GUI聊天演示界面...")
        simple_text_chat()


if __name__ == "__main__":
    main()