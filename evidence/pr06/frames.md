# Дерево систем координат

Корень `base_link`. Оси REP-103: x вперёд, y влево, z вверх, единицы СИ.
Размеры взяты из `models/course_ackermann/model.sdf` (course kit `v1-w07`).

| Родитель | Потомок | Сочленение, тип | Ожидаемое преобразование, м | Канал | Владелец |
|---|---|---|---|---|---|
| `base_link` | `camera_link` | `camera_joint`, fixed | `0.28 0 0.38` | `/tf_static` | `robot_state_publisher` |
| `base_link` | `lidar_link` | `lidar_joint`, fixed | `0.28 0 0.38` | `/tf_static` | `robot_state_publisher` |
| `base_link` | `imu_link` | `imu_joint`, fixed | `0.28 0 0.38` | `/tf_static` | `robot_state_publisher` |
| `base_link` | `front_left_knuckle` | `front_left_steering_joint`, revolute | `0.40 0.31 0` + поворот по z | `/tf` | `robot_state_publisher` по `joint_states` |
| `base_link` | `front_right_knuckle` | `front_right_steering_joint`, revolute | `0.40 -0.31 0` + поворот по z | `/tf` | `robot_state_publisher` по `joint_states` |
| `front_left_knuckle` | `front_left_wheel` | `front_left_wheel_joint`, continuous | `0 0 0` + вращение по y | `/tf` | `robot_state_publisher` по `joint_states` |
| `front_right_knuckle` | `front_right_wheel` | `front_right_wheel_joint`, continuous | `0 0 0` + вращение по y | `/tf` | `robot_state_publisher` по `joint_states` |
| `base_link` | `rear_left_wheel` | `rear_left_wheel_joint`, continuous | `-0.40 0.31 0` + вращение по y | `/tf` | `robot_state_publisher` по `joint_states` |
| `base_link` | `rear_right_wheel` | `rear_right_wheel_joint`, continuous | `-0.40 -0.31 0` + вращение по y | `/tf` | `robot_state_publisher` по `joint_states` |

У каждой связи один издатель: в графе одна нода `/robot_state_publisher`
(`nodes.txt`), у `/tf_static` `Publisher count: 1` (`tf-qos.txt`). `map` и `odom`
ещё не публикуются, поэтому Fixed Frame в RViz — `base_link`.

Подвижные звенья попадают в `/tf`, только когда кто-то публикует `joint_states`.
Поэтому в `frames.gv` видны три фиксированные связи, а на `rviz.png` колёса видны
благодаря ручной публикации нулевых положений.

При старте `robot_state_publisher` пишет предупреждение KDL, что у корневого звена
`base_link` есть инерция (`launch.log`). Оно не влияет на дерево: контракт курса
требует корень `base_link`, а инерция нужна модели, не tf.

## Проверка связи и дефект

| Проверка | `main` | `pr06-defect` (`camera_link` родитель `lidar_link`) |
|---|---|---|
| `check_urdf` | exit 0, `lidar_link` под `base_link` | exit 0, `lidar_link` под `camera_link` |
| `tf2_echo base_link lidar_link` | `0.280 0.000 0.380` | `0.560 0.000 0.760` |
| `view_frames` | `frames.gv`: `base_link -> lidar_link` | `frames-defect.gv`: `camera_link -> lidar_link` |
| `test_model.py` | 29 passed (`fixed.txt`) | 2 failed, 27 passed (`defect.txt`) |
| RViz | `rviz.png` | `rviz-defect.png`: лидар выше и впереди камеры |

`check_urdf` принимает оба дерева: он проверяет структуру, но не смысл связи.
Ошибку ловят тесты ожидаемого родителя и положения лидара в `base_link`.

Первый снимок `tf-qos.txt` показал `Publisher count: 3`: это были незавершённые
`robot_state_publisher` от прошлых запусков, поэтому они были остановлены и снимок
повторён. Один раз `ros2 topic echo` с volatile не завершился по `timeout`, запуск
тоже повторён; в сохранённом выводе `exit=124`.
