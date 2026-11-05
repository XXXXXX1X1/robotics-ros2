from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    share = FindPackageShare('course_description')
    xacro_file = PathJoinSubstitution([share, 'urdf', 'vehicle.urdf.xacro'])
    robot_description = ParameterValue(Command(['xacro "', xacro_file, '"']), value_type=str)
    return LaunchDescription([
        DeclareLaunchArgument(
            'rviz', default_value='false', choices=['true', 'false'],
            description='Открыть модель в RViz'),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}],
            output='screen',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', PathJoinSubstitution([share, 'rviz', 'vehicle.rviz'])],
            condition=IfCondition(LaunchConfiguration('rviz')),
            output='screen',
        ),
    ])
