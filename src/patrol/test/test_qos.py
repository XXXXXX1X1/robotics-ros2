from patrol.qos import sensor_qos
import pytest
from rclpy.qos import HistoryPolicy, ReliabilityPolicy


@pytest.mark.parametrize('name, policy', [
    ('reliable', ReliabilityPolicy.RELIABLE),
    ('best_effort', ReliabilityPolicy.BEST_EFFORT),
])
def test_sensor_qos_sets_reliability(name: str, policy: ReliabilityPolicy) -> None:
    profile = sensor_qos(name)
    assert profile.reliability == policy
    assert profile.history == HistoryPolicy.KEEP_LAST
    assert profile.depth == 10


@pytest.mark.parametrize('name', ['', 'Reliable', 'best-effort', 'system_default'])
def test_unknown_reliability_is_rejected(name: str) -> None:
    with pytest.raises(ValueError, match='reliability'):
        sensor_qos(name)
