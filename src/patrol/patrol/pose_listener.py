from patrol.qos import sensor_qos
from patrol.runner import run_node
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from turtlesim_msgs.msg import Pose


class PoseListener(Node):
    """Подписчик sensor_pose с надёжностью из параметра; раз в секунду пишет счётчик."""

    def __init__(self) -> None:
        super().__init__('pose_listener')
        # QoS задаётся при создании подписки, поэтому смена на лету ничего бы не дала.
        self.reliability: str = self.declare_parameter(
            'reliability', 'best_effort',
            ParameterDescriptor(read_only=True)).value
        self.received = 0
        self.subscription = self.create_subscription(
            Pose, 'sensor_pose', self.on_pose, sensor_qos(self.reliability))
        self.timer = self.create_timer(1.0, self.report)

    def on_pose(self, message: Pose) -> None:
        self.received += 1

    def report(self) -> None:
        self.get_logger().info(
            f'reliability={self.reliability} received={self.received}')


def main(args: list[str] | None = None) -> None:
    run_node(PoseListener, args)


if __name__ == '__main__':
    main()
