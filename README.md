# Translation Agent

内部协作翻译工作台（长文翻译、段落确认、Slack 辅助工具）。

## 最新功能

### 沉浸式编辑器增强
- **批量重译**：支持选择多个段落（最多50个）一次性重译，提供可读性/专业化/更地道等快捷模板
- **视觉优化**：已确认段落使用浅绿色背景，一眼识别完成状态
- **确认功能**：添加"确认"按钮，快速确认当前段落
- **智能交互**：点击段落任意位置即可选择，重译下拉框智能展开方向

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
2. 至少配置：`GEMINI_API_KEY`
3. 可选配置备用模型：`GEMINI_BACKUP_MODEL=gemini-flash-latest`

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
