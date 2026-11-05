from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest

MODEL = Path(__file__).resolve().parents[1] / 'urdf' / 'vehicle.urdf.xacro'
XYZ = tuple[float, float, float]

# Размеры из models/course_ackermann/model.sdf: база 0.8, колея 0.62, сенсоры в 0.28 0 0.38.
EXPECTED_JOINTS: dict[str, tuple[str, str, XYZ]] = {
    'camera_link': ('base_link', 'fixed', (0.28, 0.0, 0.38)),
    'lidar_link': ('base_link', 'fixed', (0.28, 0.0, 0.38)),
    'imu_link': ('base_link', 'fixed', (0.28, 0.0, 0.38)),
    'front_left_knuckle': ('base_link', 'revolute', (0.40, 0.31, 0.0)),
    'front_right_knuckle': ('base_link', 'revolute', (0.40, -0.31, 0.0)),
    'front_left_wheel': ('front_left_knuckle', 'continuous', (0.0, 0.0, 0.0)),
    'front_right_wheel': ('front_right_knuckle', 'continuous', (0.0, 0.0, 0.0)),
    'rear_left_wheel': ('base_link', 'continuous', (-0.40, 0.31, 0.0)),
    'rear_right_wheel': ('base_link', 'continuous', (-0.40, -0.31, 0.0)),
}
LINKS_WITHOUT_GEOMETRY = {'front_left_knuckle', 'front_right_knuckle'}


def expand(*mappings: str) -> ET.Element:
    result = subprocess.run(
        ['xacro', str(MODEL), *mappings], check=True, capture_output=True, text=True)
    return ET.fromstring(result.stdout)


@pytest.fixture(scope='module')
def model() -> ET.Element:
    return expand()


def joints_by_child(robot: ET.Element) -> dict[str, ET.Element]:
    return {required(j, 'child').attrib['link']: j for j in robot.findall('joint')}


def required(parent: ET.Element, tag: str) -> ET.Element:
    element = parent.find(tag)
    assert element is not None, f'нет <{tag}>'
    return element


def origin_xyz(joint: ET.Element) -> XYZ:
    x, y, z = (float(v) for v in required(joint, 'origin').attrib['xyz'].split())
    return x, y, z


def position_in_base_link(robot: ET.Element, link: str) -> XYZ:
    """Сложить смещения по цепочке до корня: поворотов в origin сочленений нет."""
    joints = joints_by_child(robot)
    x, y, z = 0.0, 0.0, 0.0
    for _ in range(len(joints) + 1):
        if link == 'base_link':
            return x, y, z
        dx, dy, dz = origin_xyz(joints[link])
        x, y, z = x + dx, y + dy, z + dz
        link = required(joints[link], 'parent').attrib['link']
    pytest.fail('цикл в цепочке родителей')


def test_tree_is_connected_and_acyclic(model: ET.Element) -> None:
    links = {link.attrib['name'] for link in model.findall('link')}
    joints = model.findall('joint')
    children = [required(j, 'child').attrib['link'] for j in joints]
    assert len(children) == len(set(children)), 'у звена больше одного родителя'
    assert 'base_link' not in children, 'у корня есть родитель'
    # У каждого звена один родитель, а у корня нет: звено на цикле недостижимо из корня.
    reached = {'base_link'}
    frontier = ['base_link']
    while frontier:
        parent = frontier.pop()
        for joint in joints:
            child = required(joint, 'child').attrib['link']
            if required(joint, 'parent').attrib['link'] == parent and child not in reached:
                reached.add(child)
                frontier.append(child)
    assert reached == links


@pytest.mark.parametrize('child', EXPECTED_JOINTS)
def test_joint_parent_and_type(model: ET.Element, child: str) -> None:
    parent, joint_type, _ = EXPECTED_JOINTS[child]
    joint = joints_by_child(model)[child]
    assert required(joint, 'parent').attrib['link'] == parent
    assert joint.attrib['type'] == joint_type


@pytest.mark.parametrize('child', EXPECTED_JOINTS)
def test_joint_offset(model: ET.Element, child: str) -> None:
    *_, xyz = EXPECTED_JOINTS[child]
    assert origin_xyz(joints_by_child(model)[child]) == pytest.approx(xyz)


@pytest.mark.parametrize('sensor', ['camera_link', 'lidar_link', 'imu_link'])
def test_sensor_position_in_base_link(model: ET.Element, sensor: str) -> None:
    assert position_in_base_link(model, sensor) == pytest.approx((0.28, 0.0, 0.38))


def test_wheel_radius_and_axis(model: ET.Element) -> None:
    joints = joints_by_child(model)
    for wheel in ('front_left', 'front_right', 'rear_left', 'rear_right'):
        link = model.find(f"link[@name='{wheel}_wheel']")
        assert link is not None
        for section in ('visual', 'collision'):
            geometry = required(required(link, section), 'geometry')
            assert float(required(geometry, 'cylinder').attrib['radius']) == 0.12
        axis = required(joints[f'{wheel}_wheel'], 'axis').attrib['xyz']
        assert axis == '0 1 0'


def test_dimensions_are_parameters() -> None:
    robot = expand('wheel_base:=1.0', 'track_width:=0.8', 'wheel_radius:=0.2')
    joints = joints_by_child(robot)
    assert origin_xyz(joints['front_left_knuckle']) == pytest.approx((0.5, 0.4, 0.0))
    assert origin_xyz(joints['rear_right_wheel']) == pytest.approx((-0.5, -0.4, 0.0))
    cylinder = robot.find("link[@name='rear_left_wheel']/visual/geometry/cylinder")
    assert cylinder is not None and float(cylinder.attrib['radius']) == 0.2


def test_steering_limits_body_size_and_masses(model: ET.Element) -> None:
    joints = joints_by_child(model)
    for knuckle in ('front_left_knuckle', 'front_right_knuckle'):
        limit = required(joints[knuckle], 'limit').attrib
        assert float(limit['lower']) == -0.55 and float(limit['upper']) == 0.55
    body = model.find("link[@name='base_link']/visual/geometry/box")
    assert body is not None and body.attrib['size'] == '1.05 0.52 0.22'
    for link, mass in (('base_link', 12.0), ('rear_left_wheel', 0.8), ('front_left_knuckle', 0.2)):
        value = model.find(f"link[@name='{link}']/inertial/mass")
        assert value is not None and float(value.attrib['value']) == mass


def test_visual_and_collision_are_declared_separately(model: ET.Element) -> None:
    for link in model.findall('link'):
        if link.attrib['name'] not in LINKS_WITHOUT_GEOMETRY:
            assert link.find('visual') is not None, link.attrib['name']
            assert link.find('collision') is not None, link.attrib['name']


def test_inertia_is_physically_possible(model: ET.Element) -> None:
    for link in model.findall('link'):
        inertial = required(link, 'inertial')
        assert float(required(inertial, 'mass').attrib['value']) > 0
        inertia = required(inertial, 'inertia').attrib
        ixx, iyy, izz = (float(inertia[k]) for k in ('ixx', 'iyy', 'izz'))
        assert min(ixx, iyy, izz) > 0, link.attrib['name']
        assert ixx + iyy >= izz and ixx + izz >= iyy and iyy + izz >= ixx, link.attrib['name']


def test_no_gazebo_plugins(model: ET.Element) -> None:
    assert model.find('.//gazebo') is None
    assert model.find('.//plugin') is None


def test_check_urdf_accepts_expanded_model(model: ET.Element, tmp_path: Path) -> None:
    urdf = tmp_path / 'vehicle.urdf'
    ET.ElementTree(model).write(urdf, encoding='unicode')
    result = subprocess.run(['check_urdf', str(urdf)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'root Link: base_link' in result.stdout
