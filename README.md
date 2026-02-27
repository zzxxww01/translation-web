# Translation Agent

内部协作翻译工作台（长文翻译、段落确认、Slack 辅助工具）。

## 适用范围
- 仅供你和协作者共同开发与使用。
- 不维护社区贡献流程与配套治理文档。

## 快速启动（Windows）
1. 安装后端依赖
```bash
pip install -r requirements.txt
```

2. 安装前端依赖
```bash
cd web/frontend
npm install
```

3. 启动服务
```bash
start.bat
```

4. 访问地址
- Web：`http://localhost:54321`
- API 文档：`http://localhost:54321/docs`

## 基础配置
1. 复制 `.env.example` 为 `.env`
2. 至少配置：`GEMINI_BACKUP_API_KEY`

## 运行脚本说明
- `start.bat` / `stop.bat` 保持原样，不在本次重构中改动。
- 两个脚本包含较强的端口清理动作，可能结束占用进程，建议仅在本机受控环境使用。

## 目录结构
- `src/`：后端 API 与核心业务逻辑
- `web/frontend/`：前端应用
- `projects/`：运行期项目数据
- `glossary/`：术语表

## 文档
- 架构文档：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 协作说明：[docs/COLLAB_GUIDE.md](docs/COLLAB_GUIDE.md)
