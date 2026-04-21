# Translation Agent

一个基于 LLM 的智能翻译系统，支持长文翻译、帖子翻译、术语库管理等功能。

## 功能特性

- 🌐 **多模型支持**: 支持 Google Gemini、OpenAI、Anthropic Claude 等多种 LLM
- 📝 **长文翻译**: 支持 Markdown 文档的分段翻译，保持格式完整
- 💬 **帖子翻译**: 针对社交媒体帖子的快速翻译
- 📚 **术语库管理**: 自定义术语库，确保专业术语翻译一致性
- 📖 **规则库系统**: 支持自定义翻译规则和风格指南
- 🔄 **批量处理**: 支持批量翻译和并行处理
- 🎨 **Web 界面**: 提供友好的 Web 操作界面
- 🔌 **Slack/微信集成**: 支持 Slack 和微信的翻译工作流

## 快速开始

### 环境要求

- **Python**: 3.10 或更高版本
- **Node.js**: 18.x 或更高版本
- **操作系统**: Windows 10/11, Ubuntu 20.04+, Debian 11+, CentOS 8+

### 本地开发（Windows）

1. **克隆仓库**
```bash
git clone https://github.com/your-org/translation-agent.git
cd translation-agent
```

2. **安装 Python 依赖**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. **安装前端依赖**
```bash
cd web\frontend
npm install
npm run build
cd ..\..
```

4. **配置环境变量**
```bash
copy .env.example .env
notepad .env  # 填入你的 API 密钥
```

必填配置：
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BACKUP_API_KEY=your_backup_key_here
```

5. **启动服务**
```bash
start.bat
```

6. **访问应用**
- Web 界面: http://localhost:54321
- API 文档: http://localhost:54321/docs

### 云服务器部署（Linux）

详细的生产环境部署指南（包括 systemd、Nginx、SSL 配置）请参考：[部署指南](docs/DEPLOYMENT.md)

快速部署：
```bash
# 安装依赖
sudo apt update
sudo apt install -y python3.10 python3.10-venv nodejs npm nginx

# 克隆项目
cd /opt
sudo git clone https://github.com/your-org/translation-agent.git
cd translation-agent

# 配置环境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# 前端构建
cd web/frontend && npm install && npm run build && cd ../..

# 配置环境变量
cp .env.example .env
nano .env  # 填入 API 密钥

# 启动服务
./start.sh
```

## 项目结构

```
translation_agent/
├── src/                    # 后端源码
│   ├── api/               # FastAPI 路由和 API 端点
│   │   ├── routers/       # 路由模块（翻译、项目、术语库等）
│   │   └── app.py         # FastAPI 应用入口
│   ├── core/              # 核心业务逻辑
│   │   ├── project.py     # 项目管理
│   │   ├── glossary.py    # 术语库管理
│   │   ├── rules.py       # 规则库管理
│   │   └── file_utils.py  # 文件操作工具
│   ├── llm/               # LLM 集成层
│   │   ├── base.py        # LLM 基类
│   │   ├── gemini.py      # Gemini 实现
│   │   ├── openai.py      # OpenAI 实现
│   │   └── factory.py     # LLM 工厂
│   └── services/          # 服务层
│       ├── batch_translation.py  # 批量翻译服务
│       └── post_translation.py   # 帖子翻译服务
├── web/                   # 前端代码
│   └── frontend/          # React 应用
│       ├── src/           # React 源码
│       └── public/        # 静态资源
├── config/                # 配置文件
│   └── llm_providers.yaml # LLM 提供商配置
├── projects/              # 翻译项目数据（运行时生成）
├── docs/                  # 技术文档
└── scripts/               # 工具脚本
```

## 核心功能

### 1. 长文翻译

支持 Markdown 文档的智能分段翻译，保持格式和结构完整：
- 自动识别段落、标题、列表、代码块
- 支持术语库和规则库
- 多维度翻译（直译、意译、自由译）
- 实时预览和编辑

详见：[长文翻译技术手册](docs/长文翻译技术手册.md)

### 2. 帖子翻译

针对社交媒体帖子的快速翻译：
- 支持多语言互译
- 保持语气和风格
- 支持 Slack 和微信集成

详见：[帖子翻译技术手册](docs/帖子翻译技术手册.md)

### 3. 术语库管理

自定义术语库，确保专业术语翻译一致性：
- 支持多语言术语对照
- 术语优先级管理
- 批量导入导出

详见：[术语库系统手册](docs/术语库系统手册.md)

### 4. 规则库系统

自定义翻译规则和风格指南：
- 支持正则表达式规则
- 规则优先级和作用域
- 规则测试和验证

详见：[规则库系统手册](docs/规则库系统手册.md)

## 技术文档

### 系统架构
- [系统架构](docs/系统架构.md) - 整体架构设计和技术栈
- [LLM 模块系统手册](docs/LLM模块系统手册.md) - LLM 集成和配置

### 功能手册
- [长文翻译技术手册](docs/长文翻译技术手册.md) - 长文翻译流程和技术细节
- [长文翻译链路](docs/长文翻译链路.md) - 翻译链路和数据流
- [帖子翻译技术手册](docs/帖子翻译技术手册.md) - 帖子翻译功能说明
- [帖子翻译链路](docs/帖子翻译链路.md) - 帖子翻译数据流
- [术语库系统手册](docs/术语库系统手册.md) - 术语库管理和使用
- [规则库系统手册](docs/规则库系统手册.md) - 规则库配置和应用

### 部署和配置
- [部署指南](docs/DEPLOYMENT.md) - Windows 和 Linux 完整部署指南
- [代理配置说明](docs/PROXY_CONFIG.md) - 网络代理配置
- [模型配置说明](docs/模型配置说明.md) - LLM 模型参数配置

### API 文档
启动服务后访问 http://localhost:54321/docs 查看完整的 API 文档（Swagger UI）。

## 开发指南

### 运行测试

```bash
# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_project.py

# 查看覆盖率
pytest --cov=src tests/
```

### 代码风格

项目使用以下工具保证代码质量：
- **Black**: 代码格式化
- **Flake8**: 代码检查
- **MyPy**: 类型检查

```bash
# 格式化代码
black src/

# 检查代码
flake8 src/

# 类型检查
mypy src/
```

## 常见问题

### 1. Gemini API 连接失败

确保 `.env` 文件中配置了正确的 API 密钥：
```env
GEMINI_API_KEY=your_real_api_key_here
```

如果在国内网络环境，可能需要配置代理，详见 [代理配置说明](docs/PROXY_CONFIG.md)。

### 2. 前端构建失败

确保 Node.js 版本 >= 18：
```bash
node --version
```

清理缓存后重新安装：
```bash
cd web/frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### 3. 端口被占用

修改 `.env` 文件中的端口配置：
```env
API_PORT=8080  # 改为其他端口
```

更多问题请查看 [部署指南](docs/DEPLOYMENT.md) 的故障排查章节。

## 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

MIT License

## 技术支持

- 📖 查看 [技术文档](docs/)
- 🐛 提交 [Issue](https://github.com/your-org/translation-agent/issues)
- 💬 加入讨论组

---

**开始使用 Translation Agent，让翻译更智能！** 🚀
