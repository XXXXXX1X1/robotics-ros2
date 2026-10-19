from collections.abc import Callable, Iterator
import time

from patrol.pose_listener import PoseListener
from patrol.pose_relay import PoseRelay
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import ReliabilityPolicy
from turtlesim_msgs.msg import Pose


class Graph:
    """Источник позы → pose_relay → pose_listener в одном процессе."""

    def __init__(self) -> None:
        self.executor = SingleThreadedExecutor()
        self.relay = PoseRelay()
        self.listener = PoseListener()
        self.source = rclpy.create_node('pose_source')
        publisher = self.source.create_publisher(Pose, 'pose', 10)
        self.source.create_timer(0.02, lambda: publisher.publish(Pose(x=1.0)))
        for node in (self.relay, self.listener, self.source):
            self.executor.add_node(node)

    def spin_until(self, done: Callable[[], bool], seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline and not done():
            self.executor.spin_once(timeout_sec=0.05)


@pytest.fixture
def graph(request: pytest.FixtureRequest) -> Iterator[Graph]:
    with rclpy.init(args=['--ros-args', '-p', f'reliability:={request.param}']):
        graph = Graph()
        yield graph
        for node in graph.executor.get_nodes():
            node.destroy_node()


@pytest.mark.parametrize('graph', ['best_effort'], indirect=True)
def test_relay_publishes_best_effort(graph: Graph) -> None:
    graph.spin_until(lambda: graph.relay.count_subscribers('sensor_pose') > 0, 5.0)
    [info] = graph.relay.get_publishers_info_by_topic('/sensor_pose')
    assert info.qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT


@pytest.mark.parametrize('graph', ['best_effort'], indirect=True)
def test_best_effort_listener_receives(graph: Graph) -> None:
    graph.spin_until(lambda: graph.listener.received >= 5, 5.0)
    assert graph.listener.received >= 5


@pytest.mark.parametrize('graph', ['reliable'], indirect=True)
def test_reliable_listener_sees_topic_but_gets_nothing(graph: Graph) -> None:
    graph.spin_until(lambda: graph.listener.count_publishers('sensor_pose') > 0, 5.0)
    graph.spin_until(lambda: False, 2.0)
    assert graph.listener.count_publishers('sensor_pose') == 1
    assert graph.listener.received == 0
