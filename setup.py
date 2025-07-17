#!/usr/bin/env python3
"""
Python Persona Engine 安装脚本
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# 读取requirements文件
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="python-persona-engine",
    version="1.0.0",
    description="AI驱动的交互式虚拟角色引擎",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Python Persona Engine Team",
    author_email="team@persona-engine.com",
    url="https://github.com/your-username/python-persona-engine",
    
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.txt", "*.md"],
        "config": ["*.yaml", "*.txt"],
        "resources": ["**/*"],
    },
    
    install_requires=requirements,
    
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "gpu": [
            "torch>=2.1.0+cu118",
            "torchaudio>=2.1.0+cu118",
        ],
        "elevenlabs": [
            "elevenlabs>=0.2.0",
        ],
        "azure": [
            "azure-cognitiveservices-speech>=1.30.0",
        ],
    },
    
    python_requires=">=3.9",
    
    entry_points={
        "console_scripts": [
            "persona-engine=main:main",
        ],
    },
    
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    
    keywords=[
        "ai", "chatbot", "voice", "speech", "tts", "asr", 
        "live2d", "virtual-character", "persona", "assistant"
    ],
    
    project_urls={
        "Bug Reports": "https://github.com/your-username/python-persona-engine/issues",
        "Source": "https://github.com/your-username/python-persona-engine",
        "Documentation": "https://github.com/your-username/python-persona-engine/wiki",
        "Original Project": "https://github.com/fagenorn/handcrafted-persona-engine",
    },
) 