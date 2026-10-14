from collections.abc import Iterator

from patrol.patrol import Patrol
import pytest
import rclpy
from rclpy.parameter import Parameter


@pytest.fixture
def node() -> Iterator[Patrol]:
    with rclpy.init():
        patrol = Patrol()
        yield patrol
        patrol.destroy_node()


def period_s(node: Patrol) -> float:
    return node.timer.timer_period_ns / 1e9


def test_defaults_give_10_hz_timer(node: Patrol) -> None:
    assert node.get_parameter('publish_hz').value == 10.0
    assert node.get_parameter('linear_speed').value == 0.5
    assert node.get_parameter('turn_rate').value == 0.3
    assert period_s(node) == pytest.approx(0.1)


def test_valid_rate_replaces_timer(node: Patrol) -> None:
    old_timer = node.timer
    result = node.set_parameters_atomically([Parameter('publish_hz', value=5.0)])
    assert result.successful
    assert node.timer is not old_timer
    # Старый таймер уничтожен, а не только отменён: у ноды ровно один таймер.
    assert list(node.timers) == [node.timer]
    assert period_s(node) == pytest.approx(0.2)


@pytest.mark.parametrize('publish_hz', [0.0, -1.0, float('nan')])
def test_invalid_rate_keeps_value_and_timer(node: Patrol, publish_hz: float) -> None:
    node.set_parameters_atomically([Parameter('publish_hz', value=5.0)])
    old_timer = node.timer
    result = node.set_parameters_atomically([Parameter('publish_hz', value=publish_hz)])
    assert not result.successful
    assert 'publish_hz' in result.reason
    assert node.get_parameter('publish_hz').value == 5.0
    assert node.timer is old_timer
    assert not old_timer.is_canceled()
    assert period_s(node) == pytest.approx(0.2)


def test_speed_change_keeps_timer(node: Patrol) -> None:
    old_timer = node.timer
    result = node.set_parameters_atomically([
        Parameter('linear_speed', value=0.8), Parameter('turn_rate', value=-0.5)])
    assert result.successful
    assert (node.linear_speed, node.turn_rate) == (0.8, -0.5)
    assert node.timer is old_timer


def test_invalid_set_rejects_whole_batch(node: Patrol) -> None:
    result = node.set_parameters_atomically([
        Parameter('linear_speed', value=0.8), Parameter('publish_hz', value=0.0)])
    assert not result.successful
    assert node.linear_speed == 0.5
    assert node.get_parameter('linear_speed').value == 0.5
