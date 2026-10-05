"""Выбор команды скорости по последней позе без зависимостей от ROS."""

from typing import Any

LINEAR_X = 0.5
ANGULAR_Z = 0.3
MAX_LINEAR_X = 1.0
MAX_ANGULAR_Z = 1.0


def choose_command(pose: Any | None) -> tuple[float, float]:
    """Вернуть (linear.x, angular.z): ноль до первой позы, иначе движение по дуге."""
    if pose is None:
        return 0.0, 0.0
    return LINEAR_X, ANGULAR_Z


def clamp_command(
    linear_x: float,
    angular_z: float,
    max_linear_x: float = MAX_LINEAR_X,
    max_angular_z: float = MAX_ANGULAR_Z,
) -> tuple[float, float]:
    """Ограничить обе скорости симметричным диапазоном [-max, max]."""
    return (
        max(-max_linear_x, min(max_linear_x, linear_x)),
        max(-max_angular_z, min(max_angular_z, angular_z)),
    )
