from glob import glob

from setuptools import find_packages, setup

package_name = 'course_description'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/urdf', glob('urdf/*.urdf.xacro')),
        ('share/' + package_name + '/rviz', glob('rviz/*.rviz')),
    ],
    package_data={'': ['py.typed']},
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='A. Salapanov',
    maintainer_email='a.salapanov@g.nsu.ru',
    description='URDF/Xacro model of the Ackermann robot and its tf tree (practice PR06)',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
        ],
    },
)
