@echo off
REM Python Persona Engine 安装脚本 (Windows)

echo 🎭 Python Persona Engine 安装脚本
echo ==================================

REM 检查Python版本
echo 📋 检查Python版本...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.9或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ❌ Python版本过低，需要Python 3.9或更高版本
    echo 请升级Python后重新运行此脚本
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set python_version=%%i
echo ✅ Python版本: %python_version% (满足要求)

REM 检查GPU支持
echo 🔍 检查GPU支持...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo ⚠️  未检测到NVIDIA GPU，将使用CPU模式
    set GPU_SUPPORT=false
) else (
    echo ✅ 检测到NVIDIA GPU
    set GPU_SUPPORT=true
)

REM 创建虚拟环境
echo 📦 创建Python虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo ✅ 虚拟环境已创建
) else (
    echo ℹ️  虚拟环境已存在
)

REM 激活虚拟环境
echo 🔌 激活虚拟环境...
call venv\Scripts\activate.bat

REM 升级pip
echo ⬆️  升级pip...
python -m pip install --upgrade pip

REM 安装基础依赖
echo 📥 安装基础依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)

REM 安装GPU支持（如果可用）
if "%GPU_SUPPORT%"=="true" (
    echo 🚀 安装GPU支持...
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
)

REM 检查espeak-ng
echo 🔧 检查系统依赖...
where espeak-ng >nul 2>&1
if errorlevel 1 (
    echo ⚠️  未找到espeak-ng
    echo 请从以下地址下载并安装espeak-ng:
    echo https://github.com/espeak-ng/espeak-ng/releases
    echo 安装后请确保espeak-ng在系统PATH中
) else (
    echo ✅ espeak-ng 已安装
)

REM 创建配置文件
echo ⚙️  设置配置文件...
if not exist "config\config.yaml" (
    copy "config\config.example.yaml" "config\config.yaml" >nul
    echo ✅ 已创建配置文件: config\config.yaml
    echo 🔑 请编辑配置文件并设置您的API密钥
) else (
    echo ℹ️  配置文件已存在: config\config.yaml
)

REM 创建启动脚本
echo 📝 创建启动脚本...
(
echo @echo off
echo REM Python Persona Engine 启动脚本
echo.
echo REM 激活虚拟环境
echo call venv\Scripts\activate.bat
echo.
echo REM 运行程序
echo python main.py %%*
) > run.bat

echo ✅ 启动脚本已创建: run.bat

REM 安装完成
echo.
echo 🎉 安装完成！
echo.
echo 下一步:
echo 1. 编辑配置文件: config\config.yaml
echo 2. 设置您的API密钥 (OpenAI, Anthropic等)
echo 3. 运行程序: run.bat 或 python main.py
echo.
echo 更多信息请查看 README.md
echo.

REM 提示配置API密钥
echo 🔑 重要提醒:
echo 请确保在config\config.yaml中设置正确的API密钥：
echo   - OpenAI API密钥 (用于LLM)
echo   - 其他服务的API密钥 (如需要)
echo.
echo 没有正确的API密钥，引擎将无法正常工作。
echo.

pause 