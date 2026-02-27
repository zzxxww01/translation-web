"""
Compatibility entrypoint.

`src.api.app:app` is the single canonical FastAPI application.
This module keeps backward compatibility for imports like
`from src.api.main import app`.
"""

from src.api.app import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000)
