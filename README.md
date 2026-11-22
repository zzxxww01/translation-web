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
git clone https://github.com/zzxxww01/translation-web.git
cd translation-web
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

- **momo.beauty 线上环境**：按 [生产发布流程](docs/production-release.md) 操作（用户级 systemd 单元
  `translation-agent-live.service`，不可变发布目录 `/home/zxw/releases/translation-agent-<revision>`，
  `scripts/verify_release.py` 做发布门禁）。不要用下面的通用步骤直接改线上。
- **通用部署模板**（systemd、Nginx、SSL）：[部署指南](docs/DEPLOYMENT.md)。

通用环境的最小步骤：
```bash
git clone https://github.com/zzxxww01/translation-web.git && cd translation-web
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -c requirements-lock.txt
cd web/frontend && npm ci && npm run build && cd ../..
cp .env.example .env   # 填入 API 密钥
./start.sh             # 单 worker；需要 --dev 时自动热重载
```

## 项目结构

```
translation-web/
├── src/                    # 后端源码（FastAPI）
│   ├── api/               # 路由、中间件、流式接口；app.py 是应用入口
│   ├── agents/            # 四步翻译、深度分析、一致性审校、质量报告等 Agent
│   ├── core/              # 项目、术语库、解析、导出、格式保护等核心逻辑
│   ├── llm/               # LLM 适配层：Gemini、OpenAI 兼容中转、官方 OpenAI、故障转移与预算
│   ├── services/          # 服务层：批量翻译、术语确认、Substack、微信排版、检查点等
│   ├── prompts/           # 提示词模板与微信主题 CSS
│   ├── html2md/           # HTML → Markdown 转换
│   ├── cli/               # 命令行入口（automation=translation-agent、cost_report）
│   └── settings.py        # 环境变量配置
├── skill_runner/          # momo「Agent」页后端（独立 systemd 服务，见 skill_runner/README.md）
├── web/frontend/          # React 前端（Vite + TypeScript + Tailwind）
├── config/                # llm_providers.yaml、translation_models.yaml、editing_options.json
├── glossary/              # 全局术语库 global_glossary_semi.json（单一术语源）
├── projects/              # 翻译项目数据（运行时生成，不入库）
├── docs/                  # 技术文档；线上发布流程见 docs/production-release.md
├── scripts/               # 工具脚本
└── tests/                 # pytest 测试（tests/unit/skill_runner 为 skill-runner 测试）
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

命令行（机器人、脚本）用统一入口 `translation-agent translate-post`，和网页同一条链路，输出 JSON：

```bash
./translation-agent-cli translate-post 'NVIDIA says demand for Blackwell remains extremely strong.'
printf '%s\n' 'First line.' 'Second line.' | ./translation-agent-cli translate-post   # 多行走标准输入
```

所有子命令见 [Muse 自动化](docs/Muse自动化.md)。

详见：[帖子翻译技术手册](docs/帖子翻译技术手册.md)

### 3. Slack 回复

网页 Slack 页的回复面板：分析对方的英文消息、给出中文理解和 3 个英文回复，或把中文回复草稿改写成 3 种英文版本。
命令行用 `translation-agent slack-reply`（`--mode auto|incoming|compose`、`--history '<JSON>'`），见 [Muse 自动化](docs/Muse自动化.md)。

### 模型与通道配置

模型入口配置在 `config/llm_providers.yaml`，长文阶段分工在
`config/translation_models.yaml`。常规模型选择优先使用 VectorEngine，
同组候选失败后才尝试 Google 官方兜底；带 `-official` 的显式选择仍表示官方通道。

- 默认任务模型（`task_defaults`）：长文与帖子翻译 `gemini-flash`（中转，实际 `gemini-3.8-flash`）；
  帖子优化与标题 `gemini-official-argon`（官方，实际 `gemini-4-argon`）；分析与元数据 `deepseek-v3`
  （中转，实际 `deepseek-v4.1-flash`）；Slack `gemini-pro`（中转，当前同样指向 `gemini-3.8-flash`）。
- 长文分阶段（`translation_models.yaml` 的 `default`）：Phase 0 预扫描 `grok-4-1-fast-non-reasoning`
  （实际 `grok-4.7`）、Phase 1 初译 `gemini-flash`、Phase 2 精修 `gemini-official-argon`、Phase 3 质量报告
  `gemini-preview`（当前指向 `gemini-3.8-flash`）。
- `deepseek-v3`、`grok-4-1-fast-non-reasoning`、`gemini-pro`、`gemini-preview` 是为兼容历史选择保留的配置别名，
  实际版本以各条目的 `real_model` 为准。
- `gpt-6.1-sol` 走 OpenAI 官方直连，只在显式选择时使用、不参与兜底，见 [docs/openai-official.md](docs/openai-official.md)。

配置只提交环境变量引用，不提交 `.env` 或 API Key。模型目录可见不代表当前通道可用，
更换版本前应实测；短句成功也不代表长文稳定。运行中的服务会缓存配置，修改后应先安全暂停任务，
重启服务加载配置，再从已有检查点续译。

### 4. 术语库管理

自定义术语库，确保专业术语翻译一致性：
- 支持多语言术语对照
- 术语优先级管理
- 批量导入导出

详见：[术语库系统手册](docs/术语库系统手册.md)

### 5. 规则库系统

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
- [Muse 自动化](docs/Muse自动化.md) - 给 Muse 经 SSH 调用的 `translation-agent` CLI（查新文章 / @我、翻译、查状态）

### 部署和配置
- [生产发布流程](docs/production-release.md) - momo.beauty 线上发布、校验与回滚的权威流程
- [部署指南](docs/DEPLOYMENT.md) - Windows 本地与通用 Linux 部署模板
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

# 运行所有测试（需要 requirements-dev.txt）
pytest

# 只跑某一组，例如 skill-runner
pytest tests/unit/skill_runner

# 查看覆盖率
pytest --cov=src tests/
```

### 代码检查

与 `.github/workflows/ci.yml` 一致：

```bash
# 未定义名字（CI 阻断项）
ruff check --select F821 src skill_runner scripts tests

# 前端：lint 零警告、类型检查与单元测试
cd web/frontend && npm run lint -- --max-warnings 0 && npx tsc -b && npm test
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
- 🐛 提交 [Issue](https://github.com/zzxxww01/translation-web/issues)
- 💬 加入讨论组

---

**开始使用 Translation Agent，让翻译更智能！** 🚀
