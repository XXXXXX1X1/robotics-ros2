import importlib.util
from pathlib import Path

from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch_ros.actions import Node

LAUNCH_FILE = Path(__file__).resolve().parents[1] / 'launch' / 'description.launch.py'


def load_entities() -> list[object]:
    spec = importlib.util.spec_from_file_location('description_launch', LAUNCH_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.generate_launch_description().entities)


def test_declares_rviz_argument() -> None:
    names = [e.name for e in load_entities() if isinstance(e, DeclareLaunchArgument)]
    assert names == ['rviz']


def test_starts_state_publisher_and_optional_rviz() -> None:
    nodes = [e for e in load_entities() if isinstance(e, Node)]
    assert [n.node_executable for n in nodes] == ['robot_state_publisher', 'rviz2']
    assert isinstance(nodes[1].condition, IfCondition)
