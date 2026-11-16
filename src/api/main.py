"""
Compatibility entrypoint.

`src.api.app:app` is the single canonical FastAPI application.
This module keeps backward compatibility for imports like
`from src.api.main import app`.
"""

from src.api.app import app

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    # 与 settings 默认值、README 和 vite 开发代理一致：127.0.0.1:54321
    uvicorn.run("src.api.app:app", host="127.0.0.1", port=54321)
