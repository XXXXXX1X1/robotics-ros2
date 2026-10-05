"""Печатать время Unix прихода каждого Twist из /turtle1/cmd_vel; только чтение."""

import sys
import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node


def main() -> None:
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    rclpy.init()
    node = Node('cmd_recorder')
    print('unix_time,linear_x,angular_z', flush=True)

    def on_command(message: Twist) -> None:
        print(f'{time.time():.3f},{message.linear.x:.2f},{message.angular.z:.2f}', flush=True)

    node.create_subscription(Twist, '/turtle1/cmd_vel', on_command, 10)
    end = time.monotonic() + duration
    while rclpy.ok() and time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
