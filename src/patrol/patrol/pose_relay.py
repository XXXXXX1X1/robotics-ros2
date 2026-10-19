from patrol.qos import sensor_qos
from patrol.runner import run_node
from rclpy.node import Node
from turtlesim_msgs.msg import Pose


class PoseRelay(Node):
    """Пересылает позу в sensor_pose как поток сенсора: best_effort, keep_last 10."""

    def __init__(self) -> None:
        super().__init__('pose_relay')
        self.publisher = self.create_publisher(
            Pose, 'sensor_pose', sensor_qos('best_effort'))
        self.subscription = self.create_subscription(
            Pose, 'pose', self.publisher.publish, 10)


def main(args: list[str] | None = None) -> None:
    run_node(PoseRelay, args)


if __name__ == '__main__':
    main()
