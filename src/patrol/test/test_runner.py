import signal

from patrol import runner
import pytest
import rclpy
from rclpy.impl.implementation_singleton import rclpy_implementation as _rclpy
from rclpy.node import Node


def make_node() -> Node:
    return rclpy.create_node('runner_test')


@pytest.fixture
def installed(monkeypatch: pytest.MonkeyPatch) -> dict[int, object]:
    """Перехватить signal.signal, чтобы не менять обработчики процесса pytest."""
    handlers: dict[int, object] = {}
    monkeypatch.setattr(runner.signal, 'signal',
                        lambda signum, handler: handlers.__setitem__(signum, handler))
    return handlers


def test_sigint_ignored_before_rclpy_init(
        monkeypatch: pytest.MonkeyPatch, installed: dict[int, object]) -> None:
    seen: list[dict[int, object]] = []
    monkeypatch.setattr(runner.rclpy, 'spin', lambda node: seen.append(dict(installed)))
    runner.run_node(make_node)
    assert seen == [{signal.SIGINT: signal.SIG_IGN}]


def test_rcl_error_after_shutdown_is_quiet(
        monkeypatch: pytest.MonkeyPatch, installed: dict[int, object]) -> None:
    def spin_after_signal(node: Node) -> None:
        rclpy.shutdown()
        raise _rclpy.RCLError('failed to initialize wait set: the given context is not valid')

    monkeypatch.setattr(runner.rclpy, 'spin', spin_after_signal)
    runner.run_node(make_node)


def test_rcl_error_with_live_context_propagates(
        monkeypatch: pytest.MonkeyPatch, installed: dict[int, object]) -> None:
    def broken_spin(node: Node) -> None:
        raise _rclpy.RCLError('real failure')

    monkeypatch.setattr(runner.rclpy, 'spin', broken_spin)
    with pytest.raises(_rclpy.RCLError, match='real failure'):
        runner.run_node(make_node)
