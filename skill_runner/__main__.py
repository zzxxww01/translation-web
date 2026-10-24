"""python -m skill_runner：按环境变量配置启动服务。"""

import logging

import uvicorn

from .app import create_app
from .config import Config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = Config.from_env()
    # SSE 长连接和 can_use_tool 的挂起都依赖单进程内的共享状态，只能跑一个 worker
    uvicorn.run(create_app(config), host=config.host, port=config.port, workers=1, log_level="info")


if __name__ == "__main__":
    main()
