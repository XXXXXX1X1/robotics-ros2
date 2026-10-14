"""Выбор и проверка команды скорости без зависимостей от ROS."""

import math
from typing import Any

MIN_PUBLISH_HZ = 1.0
MAX_PUBLISH_HZ = 30.0
MAX_LINEAR_SPEED = 1.0
MAX_TURN_RATE = 1.0


def choose_command(
    pose: Any | None, linear_speed: float, turn_rate: float
) -> tuple[float, float]:
    """Вернуть (linear.x, angular.z): ноль до первой позы, иначе движение по дуге."""
    if pose is None:
        return 0.0, 0.0
    return linear_speed, turn_rate


def validate_values(
    publish_hz: float, linear_speed: float, turn_rate: float
) -> tuple[bool, str]:
    """Проверить весь набор параметров; вернуть (допустим ли, причина отказа)."""
    values = {
        'publish_hz': publish_hz,
        'linear_speed': linear_speed,
        'turn_rate': turn_rate,
    }
    for name, value in values.items():
        if not math.isfinite(value):
            return False, f'{name} must be a finite number, got {value}'
    # ДЕФЕКТ ПР04: проверка диапазона publish_hz временно отключена.
    if not 0.0 <= linear_speed <= MAX_LINEAR_SPEED:
        return False, f'linear_speed must be in [0, {MAX_LINEAR_SPEED}] m/s, got {linear_speed}'
    if not -MAX_TURN_RATE <= turn_rate <= MAX_TURN_RATE:
        return False, (f'turn_rate must be in [{-MAX_TURN_RATE}, {MAX_TURN_RATE}] rad/s, '
                       f'got {turn_rate}')
    return True, ''
