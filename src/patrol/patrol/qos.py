"""Профиль QoS потока sensor_pose."""

from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

SENSOR_DEPTH = 10
RELIABILITY = {
    'reliable': ReliabilityPolicy.RELIABLE,
    'best_effort': ReliabilityPolicy.BEST_EFFORT,
}


def sensor_qos(reliability: str) -> QoSProfile:
    """Вернуть keep_last 10 с надёжностью 'reliable' или 'best_effort'."""
    if reliability not in RELIABILITY:
        raise ValueError(
            f'reliability must be one of {sorted(RELIABILITY)}, got {reliability!r}')
    return QoSProfile(
        reliability=RELIABILITY[reliability],
        history=HistoryPolicy.KEEP_LAST,
        depth=SENSOR_DEPTH)
