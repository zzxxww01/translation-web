# 协作说明

## 分支与提交流程
1. 从 `main` 拉最新代码后创建功能分支。
2. 每个改动保持单一目标，提交信息使用 `feat/fix/refactor/chore` 前缀。
3. 合并前至少通过前端 `lint + build` 与后端基础导入检查。

## 最小自检清单
- 前端：`cd web/frontend && npm run lint && npm run build`
- 后端：`python -m compileall src`
- API 启动自检：`python -c "from src.api.app import app; print(len(app.routes))"`

## 约定
- `start.bat` / `stop.bat` 保持原样，不在协作中直接修改。
- 运行期数据放在 `projects/`，不要将个人测试数据提交到仓库。
- 需要新增文档时优先更新 `README` 或 `ARCHITECTURE`，避免文档数量膨胀。
