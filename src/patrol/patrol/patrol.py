from geometry_msgs.msg import Twist
from patrol.command import choose_command, clamp_command
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim_msgs.msg import Pose


class Patrol(Node):

    def __init__(self) -> None:
        super().__init__('patrol')
        self.latest_pose: Pose | None = None
        self.pose_sub = self.create_subscription(
            Pose, '/turtle1/pose', self.on_pose, 10)
        self.publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.timer = self.create_timer(0.1, self.tick)

    def on_pose(self, message: Pose) -> None:
        self.latest_pose = message

    def tick(self) -> None:
        linear_x, angular_z = clamp_command(*choose_command(self.latest_pose))
        command = Twist()
        command.linear.x = linear_x
        command.angular.z = angular_z
        self.publisher.publish(command)


def main(args: list[str] | None = None) -> None:
    # Ctrl+C под `ros2 run` приходит дважды: от терминала и пересланный ros2run.
    # Второй сигнал может прервать освобождение ресурсов, поэтому ловим его
    # снаружи блока, который сам завершает контекст и уничтожает ноду.
    try:
        with rclpy.init(args=args):
            rclpy.spin(Patrol())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass


if __name__ == '__main__':
    main()
