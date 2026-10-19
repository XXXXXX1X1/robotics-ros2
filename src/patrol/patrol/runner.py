"""Общий запуск ноды до Ctrl+C."""

from collections.abc import Callable
import signal

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.impl.implementation_singleton import rclpy_implementation as _rclpy
from rclpy.node import Node


def run_node(make_node: Callable[[], Node], args: list[str] | None = None) -> None:
    """Создать ноду в новом контексте ROS и крутить её до Ctrl+C."""
    # Ctrl+C под ros2 run и ros2 launch приходит дважды: от терминала и
    # пересланный ros2. Первый ловит обработчик rclpy, а при выходе из with
    # rclpy возвращает прежний обработчик. Если прежний — питоновский, второй
    # сигнал прерывает освобождение ресурсов или финализацию, и процесс
    # умирает с -2. Поэтому прежним делаем SIG_IGN.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        with rclpy.init(args=args):
            try:
                rclpy.spin(make_node())
            except _rclpy.RCLError:
                # rclpy#1731: поток сигналов может завершить контекст между
                # итерациями spin, и тогда вместо ExternalShutdownException
                # летит RCLError. Глотаем только её; проверка ok() — внутри
                # with, пока контекст не завершён нами самими. Убрать после
                # выхода rclpy#1732 в Lyrical.
                if rclpy.ok():
                    raise
    except ExternalShutdownException:
        pass
