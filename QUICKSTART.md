# 🚀 Parrot Engine 快速启动指南

## 📋 项目已清理完成

### ✅ 已清理的文件
- 🗑️ **Python缓存**: 清理了所有 `__pycache__` 目录
- 🗑️ **重复依赖文件**: 删除了多余的 requirements 文件
- ✅ **保留重要文件**: 保留了所有必要的源码和配置

### 📁 项目结构
```
parrot-engine/
├── main.py                 # 🎯 主程序入口 (推荐)
├── run_example.py          # 📖 简单演示程序
├── test_integration.py     # 🧪 集成测试
├── requirements.txt        # 📦 唯一需要的依赖文件
├── config/
│   ├── config.yaml         # ⚙️ 主配置文件 (需要编辑)
│   ├── hiyori_config.yaml  # 🎭 Live2D模型配置
│   └── personality.txt     # 👤 角色性格设置
└── src/                    # 💻 源代码目录
```

## 🎮 启动选项

### 1. 完整系统 (推荐)
```bash
python main.py
```
**功能**: 完整的虚拟数字人系统，包含所有功能模块

### 2. 简单演示
```bash
python run_example.py
```
**功能**: 基础聊天演示，无需配置API即可体验

### 3. 系统测试
```bash
python test_integration.py
```
**功能**: 测试所有模块是否正常工作

## ⚙️ 首次启动前配置

### 1. 编辑 `config/config.yaml`
```yaml
# 配置LLM API密钥
llm:
  text_api_key: "sk-your-openai-api-key-here"  # 必须配置
  text_model: "gpt-4"                          # 可选择模型
```

### 2. 可选配置
- **个性化**: 编辑 `config/personality.txt` 自定义角色
- **Live2D**: 调整 `config/hiyori_config.yaml` 模型设置

## 🆘 故障排除

### 如果遇到导入错误
```bash
# 确保在项目根目录
cd /path/to/parrot-engine

# 确保虚拟环境激活
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows
```

### 如果API调用失败
1. 检查 `config/config.yaml` 中的API密钥
2. 确保网络连接正常
3. 验证API额度是否充足

### 如果音频功能异常
```bash
# macOS 确保 portaudio 已安装
brew install portaudio

# 检查麦克风权限
```

## 📚 下一步

1. **配置API密钥** → 获得完整功能
2. **运行 main.py** → 体验完整系统
3. **阅读 README.md** → 了解详细功能
4. **查看 docs/** → 深入了解架构

## 🎉 开始使用

```bash
# 快速启动 (简单演示)
python run_example.py

# 完整启动 (需要配置API)
python main.py
```

系统已准备就绪，开始探索吧！🚀 