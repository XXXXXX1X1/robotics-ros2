from patrol.command import choose_command, clamp_command
from turtlesim_msgs.msg import Pose


def test_no_pose_gives_zero_command() -> None:
    assert choose_command(None) == (0.0, 0.0)


def test_pose_gives_arc_command() -> None:
    pose = Pose(x=5.5, y=5.5, theta=0.0)
    assert choose_command(pose) == (0.5, 0.3)


def test_command_does_not_depend_on_pose_values() -> None:
    pose = Pose(x=1.0, y=10.0, theta=-3.0, linear_velocity=2.0)
    assert choose_command(pose) == (0.5, 0.3)


def test_clamp_keeps_command_in_range() -> None:
    assert clamp_command(0.5, 0.3) == (0.5, 0.3)


def test_clamp_limits_both_signs() -> None:
    assert clamp_command(3.0, -2.0) == (1.0, -1.0)
    assert clamp_command(-3.0, 2.0) == (-1.0, 1.0)


def test_clamp_uses_custom_limits() -> None:
    assert clamp_command(0.8, 0.8, max_linear_x=0.5, max_angular_z=0.3) == (0.5, 0.3)
