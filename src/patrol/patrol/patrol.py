from geometry_msgs.msg import Twist
from patrol.command import choose_command, validate_values
from patrol.runner import run_node
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.parameter import Parameter
from turtlesim_msgs.msg import Pose


class Patrol(Node):

    def __init__(self) -> None:
        super().__init__('patrol')
        self.linear_speed: float = self.declare_parameter('linear_speed', 0.5).value
        self.turn_rate: float = self.declare_parameter('turn_rate', 0.3).value
        self.publish_hz: float = self.declare_parameter('publish_hz', 10.0).value
        # Колбэки регистрируются после объявления и стартовые значения
        # (в том числе из --ros-args) не видят, поэтому проверяем их здесь.
        ok, reason = validate_values(self.publish_hz, self.linear_speed, self.turn_rate)
        if not ok:
            raise ValueError(reason)
        self.add_on_set_parameters_callback(self.validate)
        self.add_post_set_parameters_callback(self.apply)
        self.latest_pose: Pose | None = None
        self.pose_sub = self.create_subscription(
            Pose, 'pose', self.on_pose, 10)
        self.publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.timer = self.create_timer(1.0 / self.publish_hz, self.tick)

    def validate(self, updates: list[Parameter]) -> SetParametersResult:
        # Только проверка: при отказе rclpy не меняет параметр, а мы — поля и таймер.
        proposed = {p.name: p.value for p in updates}
        ok, reason = validate_values(
            proposed.get('publish_hz', self.publish_hz),
            proposed.get('linear_speed', self.linear_speed),
            proposed.get('turn_rate', self.turn_rate))
        return SetParametersResult(successful=ok, reason=reason)

    def apply(self, updates: list[Parameter]) -> None:
        accepted = {p.name: p.value for p in updates}
        old_hz = self.publish_hz
        self.linear_speed = accepted.get('linear_speed', self.linear_speed)
        self.turn_rate = accepted.get('turn_rate', self.turn_rate)
        self.publish_hz = accepted.get('publish_hz', self.publish_hz)
        if self.publish_hz != old_hz:
            self.timer.cancel()
            self.destroy_timer(self.timer)
            self.timer = self.create_timer(1.0 / self.publish_hz, self.tick)

    def on_pose(self, message: Pose) -> None:
        self.latest_pose = message

    def tick(self) -> None:
        linear_x, angular_z = choose_command(
            self.latest_pose, self.linear_speed, self.turn_rate)
        command = Twist()
        command.linear.x = linear_x
        command.angular.z = angular_z
        self.publisher.publish(command)


def main(args: list[str] | None = None) -> None:
    run_node(Patrol, args)


if __name__ == '__main__':
    main()
