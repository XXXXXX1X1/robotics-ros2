from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    namespace = LaunchConfiguration('namespace')
    turtle_pose = ('pose', '/turtle1/pose')
    turtle_cmd_vel = ('cmd_vel', '/turtle1/cmd_vel')
    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace', default_value='robot_a',
            description='Пространство имён patrol, pose_relay и pose_listener'),
        DeclareLaunchArgument(
            'record', default_value='false', choices=['true', 'false'],
            description='Записывать /<namespace>/sensor_pose в MCAP'),
        DeclareLaunchArgument(
            'bag_dir', default_value='bag',
            description='Каталог новой записи; не должен существовать'),
        DeclareLaunchArgument(
            'subscriber_reliability', default_value='best_effort',
            choices=['reliable', 'best_effort'],
            description='Надёжность подписки pose_listener на sensor_pose'),
        # Один turtlesim в корне графа — тот же launch, что в ПР02.
        IncludeLaunchDescription(PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('turtle_bringup'), 'launch', 'sim.launch.py']))),
        Node(
            package='patrol', executable='patrol', namespace=namespace,
            remappings=[turtle_pose, turtle_cmd_vel], output='screen'),
        Node(
            package='patrol', executable='pose_relay', namespace=namespace,
            remappings=[turtle_pose], output='screen'),
        Node(
            package='patrol', executable='pose_listener', namespace=namespace,
            parameters=[{'reliability': LaunchConfiguration('subscriber_reliability')}],
            output='screen'),
        ExecuteProcess(
            cmd=['ros2', 'bag', 'record', '-s', 'mcap',
                 '-o', LaunchConfiguration('bag_dir'),
                 '--topics', ['/', namespace, '/sensor_pose']],
            condition=IfCondition(LaunchConfiguration('record')),
            output='screen'),
    ])
