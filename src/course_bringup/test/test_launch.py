import importlib.util
from pathlib import Path

from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch_ros.actions import Node

LAUNCH_FILE = Path(__file__).resolve().parents[1] / 'launch' / 'patrol.launch.py'


def load_entities() -> list[object]:
    spec = importlib.util.spec_from_file_location('patrol_launch', LAUNCH_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.generate_launch_description().entities)


def test_declares_required_arguments() -> None:
    arguments = {
        entity.name: entity.default_value
        for entity in load_entities() if isinstance(entity, DeclareLaunchArgument)}
    assert set(arguments) == {'namespace', 'record', 'bag_dir', 'subscriber_reliability'}


def test_recorder_is_conditional() -> None:
    [recorder] = [e for e in load_entities() if isinstance(e, ExecuteProcess)
                  and not isinstance(e, Node)]
    assert isinstance(recorder.condition, IfCondition)


def test_starts_patrol_relay_and_listener() -> None:
    executables = [e.node_executable for e in load_entities() if isinstance(e, Node)]
    assert executables == ['patrol', 'pose_relay', 'pose_listener']
