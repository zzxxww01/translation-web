from src.services.wechat_formatter import WechatFormatter


class DummyExecutor:
    def __init__(self):
        self.calls = []

    def shutdown(self, wait=False):
        self.calls.append(wait)


def test_shutdown_executor_ignores_none():
    WechatFormatter._shutdown_executor(None)


def test_shutdown_executor_closes_executor_without_waiting():
    executor = DummyExecutor()

    WechatFormatter._shutdown_executor(executor)

    assert executor.calls == [False]
