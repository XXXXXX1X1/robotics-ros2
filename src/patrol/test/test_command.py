import math

from patrol.command import choose_command, validate_values
import pytest
from turtlesim_msgs.msg import Pose


def test_no_pose_gives_zero_command() -> None:
    assert choose_command(None, 0.5, 0.3) == (0.0, 0.0)


def test_pose_gives_parameter_command() -> None:
    pose = Pose(x=5.5, y=5.5, theta=0.0)
    assert choose_command(pose, 0.5, 0.3) == (0.5, 0.3)
    assert choose_command(pose, 1.0, -0.7) == (1.0, -0.7)


def test_command_does_not_depend_on_pose_values() -> None:
    pose = Pose(x=1.0, y=10.0, theta=-3.0, linear_velocity=2.0)
    assert choose_command(pose, 0.5, 0.3) == (0.5, 0.3)


def test_defaults_and_change_to_5_hz_are_valid() -> None:
    assert validate_values(10.0, 0.5, 0.3) == (True, '')
    assert validate_values(5.0, 0.5, 0.3) == (True, '')


@pytest.mark.parametrize('publish_hz', [0.0, -5.0, math.nan, math.inf, 0.5, 30.5])
def test_invalid_publish_hz_is_rejected(publish_hz: float) -> None:
    ok, reason = validate_values(publish_hz, 0.5, 0.3)
    assert not ok
    assert 'publish_hz' in reason


@pytest.mark.parametrize('publish_hz', [1.0, 30.0])
def test_publish_hz_bounds_are_valid(publish_hz: float) -> None:
    assert validate_values(publish_hz, 0.5, 0.3)[0]


@pytest.mark.parametrize('linear_speed', [-0.1, 1.1, math.nan])
def test_invalid_linear_speed_is_rejected(linear_speed: float) -> None:
    ok, reason = validate_values(10.0, linear_speed, 0.3)
    assert not ok
    assert 'linear_speed' in reason


@pytest.mark.parametrize('turn_rate', [-1.1, 1.1, -math.inf])
def test_invalid_turn_rate_is_rejected(turn_rate: float) -> None:
    ok, reason = validate_values(10.0, 0.5, turn_rate)
    assert not ok
    assert 'turn_rate' in reason


def test_speed_and_turn_bounds_are_valid() -> None:
    assert validate_values(10.0, 0.0, -1.0)[0]
    assert validate_values(10.0, 1.0, 1.0)[0]
