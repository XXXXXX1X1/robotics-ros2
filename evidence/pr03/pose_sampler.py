"""Печатать позу turtlesim каждые 0.1 с с временем Unix; только чтение."""

import sys
import time

import rclpy
from rclpy.node import Node
from turtlesim_msgs.msg import Pose


def main() -> None:
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    rclpy.init()
    node = Node('pose_sampler')
    latest: list[Pose] = []
    node.create_subscription(Pose, '/turtle1/pose', lambda m: latest.append(m), 10)
    print('unix_time,x,y,theta,linear_velocity,angular_velocity', flush=True)

    def sample() -> None:
        if latest:
            p = latest[-1]
            print(f'{time.time():.3f},{p.x:.4f},{p.y:.4f},{p.theta:.4f},'
                  f'{p.linear_velocity:.2f},{p.angular_velocity:.2f}', flush=True)

    node.create_timer(0.1, sample)
    end = time.monotonic() + duration
    while rclpy.ok() and time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
