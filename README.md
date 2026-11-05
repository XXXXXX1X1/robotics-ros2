# ПР06. Модель робота, tf2 и QoS преобразований

Практика: [условие ПР06](https://ros.lms.ci.nsu.ru/practices/pr06).
Пакет `src/course_description` — Xacro-модель Ackermann-робота
`urdf/vehicle.urdf.xacro`. Размеры взяты из `model.sdf` course kit, плагины
Gazebo не копируются. База, колея и радиус колеса — аргументы Xacro
`wheel_base`, `track_width`, `wheel_radius`. Корень дерева — `base_link`, к нему
фиксированно привязаны `camera_link`, `lidar_link`, `imu_link`. Передние колёса
висят на кулаках с рулевым `revolute`, все колёса — `continuous`.
`launch/description.launch.py` запускает `robot_state_publisher` и по `rviz:=true`
открывает RViz. Владельцы связей — в `evidence/pr06/frames.md`, опыт с durability —
в `evidence/pr06/tf-qos.txt`.

## Сборка и тесты

```bash
colcon build --symlink-install --packages-select course_description
source install/setup.bash
xacro src/course_description/urdf/vehicle.urdf.xacro > /tmp/vehicle.urdf
check_urdf /tmp/vehicle.urdf
python3 -m pytest src/course_description/test
colcon test --packages-select course_description
```

`test_model.py` разворачивает Xacro и проверяет связность дерева, parent, тип и
смещение каждого сочленения, положение сенсоров в `base_link`, радиус и ось
колёс, допустимость инерции и то, что аргументы Xacro действительно меняют
геометрию.

## Запуск

```bash
ros2 launch course_description description.launch.py rviz:=true
ros2 run tf2_ros tf2_echo base_link lidar_link
ros2 run tf2_tools view_frames
```

Fixed Frame в RViz — `base_link`. Колёса и кулаки подвижные, поэтому без
`joint_states` их нет в `/tf`, и у RobotModel статус ошибки по этим звеньям. Это
ожидаемо, фиксированные связи сенсоров публикуются сразу. Увидеть всю модель:

```bash
ros2 topic pub -r 10 /joint_states sensor_msgs/msg/JointState \
  "{header: auto, name: [front_left_steering_joint, front_right_steering_joint, \
  front_left_wheel_joint, front_right_wheel_joint, rear_left_wheel_joint, \
  rear_right_wheel_joint], position: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}"
```

## Дефект

Ветка `pr06-defect` (в `main` не вливается) делает `camera_link` родителем
`lidar_link` с прежним смещением. `check_urdf` такое дерево принимает, а лидар
уезжает в `0.56 0 0.76`. Тесты parent и положения лидара падают.

## Проверка и сдача

Course kit тот же — `v1-w07` (в нём есть манифест PR06). CI собирает все пакеты,
разворачивает Xacro и выполняет `check_urdf`, запускает pytest и `colcon test`,
затем `check_practice.py PR06`. Проверка PR05 из CI убрана: ПР05 сдана коммитом
`0042f9b` и его прогоном CI.

---

# ПР05. Launch, QoS и повтор записи

Практика: [условие ПР05](https://ros.lms.ci.nsu.ru/practices/pr05).
Пакет `src/course_bringup` — launch-файл `patrol.launch.py`: глобальный
turtlesim (через `sim.launch.py` из ПР02) и в пространстве имён
`namespace` три ноды пакета `patrol`:

- `patrol` — команда из ПР04, remap `pose`→`/turtle1/pose`,
  `cmd_vel`→`/turtle1/cmd_vel`;
- `pose_relay` — пересылает `/turtle1/pose` в относительный `sensor_pose`
  с QoS best_effort, keep_last 10;
- `pose_listener` — подписчик `sensor_pose`, надёжность из параметра
  `reliability`, раз в секунду пишет в лог число полученных сообщений.

Аргументы: `namespace` (`robot_a`), `record` (`false`; через `IfCondition`
запускает `ros2 bag record -s mcap`), `bag_dir` (`bag`),
`subscriber_reliability` (`best_effort` | `reliable`). Имена топиков внутри
нод относительные, поэтому `patrol` теперь подписан на `pose`: для
`ros2 run` из ПР03/ПР04 добавьте `-r pose:=/turtle1/pose`.
`config/qos-overrides.yaml` — профиль издателя для `ros2 bag play`.
Опыт и выводы — в `evidence/pr05/`.

## Сборка и тесты

```bash
colcon build --symlink-install --packages-select turtle_bringup patrol course_bringup
source install/setup.bash
python3 -m pytest src/patrol/test
python3 -m pytest src/course_bringup/test
```

У пакетов одинаковые имена lint-тестов, поэтому pytest запускается по
одному пакету. `test_pose_relay.py` в одном процессе проверяет, что relay
публикует best_effort, best_effort-подписчик получает поток, а reliable
видит издателя и не получает ничего.

## Запуск

```bash
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=reliable record:=false
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=best_effort \
  record:=true bag_dir:=evidence/pr05/bag
ros2 bag play evidence/pr05/bag \
  --qos-profile-overrides-path config/qos-overrides.yaml
```

## Ctrl+C и `RCLError`

Все три ноды запускаются через общий `patrol/runner.py`. Он закрывает два
сбоя остановки, которые проявились под `ros2 launch`:

- Ctrl+C в терминале доставляет SIGINT дважды: всей группе процессов и
  повторно от launch. Второй сигнал приходил, когда rclpy уже вернул
  питоновский обработчик, и нода умирала с `exit code -2` (`patrol` — 20 из
  20 остановок). `run_node` ставит SIG_IGN до `rclpy.init`, поэтому после
  выхода rclpy восстанавливает именно его.
- rclpy иногда бросает из `spin` `RCLError: failed to initialize wait set`
  вместо `ExternalShutdownException`, если поток сигналов завершил контекст
  между итерациями — открытый
  [ros2/rclpy#1731](https://github.com/ros2/rclpy/issues/1731).
  `run_node` глотает `RCLError`, только если контекст уже завершён.

После правки — 20 из 20 чистых остановок всех четырёх процессов launch
(SIGINT на группу, как Ctrl+C в терминале).

## Проверка и сдача

Course kit обновлён до `v1-w07`
(SHA-256 `001f7ec79674d09a0f7eff2ad0935f58c95101b0cf200425c368f41579d6a31c`).
CI ставит зависимости всех пакетов через `rosdep`, собирает три пакета,
запускает pytest и `colcon test`, затем `check_practice.py PR05`.
Проверка PR04 из CI убрана: ПР04 сдана коммитом `b9641a9` и его прогоном CI.

---

# ПР04. Параметры patrol: скорость, поворот, частота

Практика: [условие ПР04](https://ros.lms.ci.nsu.ru/practices/pr04).
Нода `/patrol` из ПР03 получила параметры `linear_speed` (0.5 м/с),
`turn_rate` (0.3 рад/с) и `publish_hz` (10.0 Гц). Проверка набора —
чистая функция `validate_values` в `patrol/command.py`: конечные числа,
скорость 0–1 м/с, поворот −1–1 рад/с, частота 1–30 Гц. Она вызывается в
on-set колбэке до изменения состояния; post-set колбэк обновляет поля и при
смене частоты уничтожает старый таймер и создаёт новый с периодом
`1/publish_hz`. Команды, вывод, дефект и сервис/действие turtlesim — в
`evidence/pr04/parameters.md`, тесты — в `evidence/pr04/tests.txt`.

## Сборка и тесты

Среда та же (контейнер `ros2-pr02`, `ROS_DOMAIN_ID=16`):

```bash
colcon build --symlink-install --packages-select patrol
source install/setup.bash
python3 -m pytest src/patrol/test
```

`test_command.py` проверяет `validate_values` (10→5 Гц, 0, отрицательное,
NaN, бесконечность, границы), `test_patrol_node.py` — живую ноду: смена
частоты заменяет таймер, отказ оставляет прежние значение и таймер.

## Запуск

Терминал A — `ros2 launch turtle_bringup sim.launch.py`. Терминал B:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

Терминал C:

```bash
ros2 param get /patrol publish_hz
ros2 param set /patrol publish_hz 5.0
ros2 param set /patrol publish_hz 0.0
timeout --signal=INT 10s ros2 topic hz /turtle1/cmd_vel
```

## Дефект

Ветка `pr04-defect` (в `main` не вливается) отключает проверку частоты:
`publish_hz 0.0` принимается и нода падает с `ZeroDivisionError` при
создании таймера. Тот же `test_patrol_node.py` на этой ветке падает.

## Проверка и сдача

Course kit — `v1-w04` (в нём есть манифест PR04). CI собирает пакеты,
запускает pytest и `colcon test`, затем `check_practice.py PR04`. Проверка
PR03 из CI убрана: ПР03 сдана коммитом `0df4f5e` и его прогоном CI.

---

# ПР03. Нода patrol: поза и команда

Практика: [условие ПР03](https://ros.lms.ci.nsu.ru/practices/pr03).
Пакет — `src/patrol`: нода `/patrol` хранит последнюю позу из
`/turtle1/pose` и каждые 0.1 с публикует Twist в относительный `cmd_vel`.
Выбор команды вынесен в чистую функцию `patrol/command.py`. Опыт, роли
`init`/`spin`/callback/Ctrl+C и замеры — в `evidence/pr03/demo.md`, тесты —
в `evidence/pr03/tests.txt`.

## Сборка и тесты

Среда та же, что в ПР02 (контейнер `ros2-pr02`, `ROS_DOMAIN_ID=16`):

```bash
colcon build --symlink-install --packages-select patrol
source install/setup.bash
python3 -m pytest src/patrol/test
```

Lint-тесты из шаблона `ros2 pkg create` получают путь к пакету явно,
поэтому проверяют только `patrol` и одинаково работают из корня workspace и
из `colcon test`.

## Запуск

Терминал A — turtlesim из ПР02:

```bash
ros2 launch turtle_bringup sim.launch.py
```

Терминал B — сбой (команды уходят в `/cmd_vel`), затем исправление:

```bash
ros2 run patrol patrol
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

Терминал C:

```bash
ros2 node info /patrol
ros2 topic info /turtle1/cmd_vel --verbose
timeout --signal=INT 10s ros2 topic hz /turtle1/cmd_vel
```

## Проверка и сдача

Course kit обновлён до `v1-w04`
(SHA-256 `fec6b4e886c19146078bf69fbf90a19279a4cd33f656642395350b299efeb226`).
CI ставит зависимости `patrol` через `rosdep`, собирает `turtle_bringup` и
`patrol`, запускает pytest и `colcon test`, затем
`check_practice.py PR03`. Проверка PR02 из CI убрана по той же причине, что
и PR01: ПР02 сдана коммитом `5de59f8` и его прогоном CI.

---

# ПР02. Пакет, launch и доставка команды turtlesim

Практика: [условие ПР02](https://ros.lms.ci.nsu.ru/practices/pr02).
Пакет — `src/turtle_bringup`; команды, выводы и сравнение «до / сбой /
после» — в `evidence/pr02/commands.md`; топики и поля Twist — в
`evidence/pr02/types.md`.

## Среда

Тот же образ, что в ПР01, контейнер `ros2-pr02`. Из корня репозитория на Mac:

```bash
docker run -d --name ros2-pr02 -p 6081:80 \
  -v "$PWD:/home/ubuntu/ros2_ws" \
  tiryoh/ros2-desktop-vnc:lyrical-20260906T0836
```

В каждом терминале (`docker exec -it -u ubuntu ros2-pr02 bash`):

```bash
source /opt/ros/lyrical/setup.bash
export DISPLAY=:1 XAUTHORITY=/home/ubuntu/.Xauthority ROS_DOMAIN_ID=16
cd /home/ubuntu/ros2_ws
```

## Сборка

Пакет создан командой:

```bash
cd src
ros2 pkg create --build-type ament_python --license Apache-2.0 \
  turtle_bringup --dependencies launch launch_ros turtlesim
cd ..
```

`build-empty.txt` снят до добавления `launch/`, `build.txt` — после:

```bash
set -o pipefail
colcon build --symlink-install --packages-select turtle_bringup \
  2>&1 | tee evidence/pr02/build.txt
source install/setup.bash
ros2 pkg prefix turtle_bringup
```

`setup.py` устанавливает `launch/*.launch.py` в
`share/turtle_bringup/launch`, поэтому launch находится по имени пакета.

## Запуск и доставка команды

Терминал A (после `source install/setup.bash`):

```bash
ros2 launch turtle_bringup sim.launch.py
```

Терминал B:

```bash
ros2 topic echo /turtle1/pose --once
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
ros2 topic echo /turtle1/pose --once
```

## Сбой и исправление

Тот же Twist публикуется в `/cmd_vel`, затем только имя меняется на
`/turtle1/cmd_vel`. В обоих случаях в терминале C:

```bash
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose
ros2 topic echo /turtle1/pose --once
```

При `/cmd_vel` у издателя 0 подписчиков и поза не меняется, при
`/turtle1/cmd_vel` подписчик `turtlesim` есть и черепаха едет. Подробности —
в `evidence/pr02/commands.md`.

## Проверка и сдача

Course kit тот же — `v1-w03` (в нём есть манифест PR02). CI собирает
`turtle_bringup` в `ros:lyrical-ros-base` (образ закреплён по digest),
проверяет установленный `sim.launch.py`, выполняет `py_compile` launch-файла и
`check_practice.py PR02`. GUI в CI не запускается. Локально:

```bash
python3 -m py_compile src/turtle_bringup/launch/sim.launch.py
python3 .course-kit/v1/tools/check_practice.py PR02 --submission .
```

Первый коммит содержит пакет, README и CI, второй — `evidence/pr02/` и
`AI_USAGE.md`; `report.json.commit` указывает на первый коммит.

Проверка PR01 из CI убрана: после коммита ПР01 kit разрешает менять только
`evidence/pr01/`. ПР01 сдана коммитом `3186c75` и его прогоном CI.

---

# ПР01. Окружение и граф ROS 2

Практика: [условие ПР01](https://ros.lms.ci.nsu.ru/practices/pr01).
Результат опыта — в `evidence/pr01/graph.md`; версии среды — в
`evidence/pr01/environment.json`.

## Среда

Ubuntu 26.04.1 и ROS 2 Lyrical в Docker-образе
`tiryoh/ros2-desktop-vnc:lyrical-20260906T0836`.
Digest образа записан в `environment.json`. Открыть рабочий стол контейнера
можно по адресу <http://localhost:6081>.

Из корня репозитория на Mac:

```bash
docker run -d --name ros2-pr01 -p 6081:80 \
  -v "$PWD:/home/ubuntu/ros2_ws" \
  tiryoh/ros2-desktop-vnc:lyrical-20260906T0836
```

Откройте три терминала A, B и C через рабочий стол или командой
`docker exec -it ros2-pr01 bash`. В каждом:

```bash
source /opt/ros/lyrical/setup.bash
export DISPLAY=:1
export XAUTHORITY=/home/ubuntu/.Xauthority
export ROS_DOMAIN_ID=16
cd /home/ubuntu/ros2_ws
```

Используйте выделенную преподавателем пару доменов вместо 16/17, если она
отличается. Перед опытом остановите ранее запущенные ноды turtlesim и teleop.

## Исправный граф

Терминал A:

```bash
ros2 run turtlesim turtlesim_node
```

Терминал B:

```bash
ros2 run turtlesim turtle_teleop_key
```

При фокусе в B стрелки двигают черепаху. В терминале C:

```bash
mkdir -p evidence/pr01
ros2 doctor --report > evidence/pr01/doctor.txt 2>&1
ros2 node list --no-daemon --spin-time 5 > evidence/pr01/nodes-before.txt
ros2 topic list -t --no-daemon --spin-time 5 > evidence/pr01/topics.txt
ros2 node info /turtlesim > evidence/pr01/turtlesim-info.txt
ros2 node info /teleop_turtle > evidence/pr01/teleop-info.txt
ros2 topic type /turtle1/pose > evidence/pr01/pose-type.txt
POSE_TYPE=$(cat evidence/pr01/pose-type.txt)
ros2 topic echo /turtle1/pose --once > evidence/pr01/pose-before.txt
```

Тип позы в Lyrical — `turtlesim_msgs/msg/Pose`. Замерьте частоту более 10 секунд:

```bash
TIMEFORMAT='elapsed_seconds=%R'
{ time timeout --signal=INT 12s ros2 topic hz /turtle1/pose \
  > evidence/pr01/pose-hz.txt 2>&1; } 2> evidence/pr01/pose-hz-duration.txt
printf 'exit=%s\n' "$?" > evidence/pr01/pose-hz-exit.txt
```

Код 124 здесь означает запланированное окончание замера. После нажатия ↑ в B
сохраните новую позу в C:

```bash
ros2 topic echo /turtle1/pose --once > evidence/pr01/pose-after-key-working.txt
```

## Разрыв связи

Симулятор A остаётся в домене 16. В B остановите teleop через Ctrl+C:

```bash
export ROS_DOMAIN_ID=17
ros2 run turtlesim turtle_teleop_key
```

В C:

```bash
export ROS_DOMAIN_ID=17
ros2 node list --no-daemon --spin-time 5 > evidence/pr01/nodes-broken.txt
timeout --signal=INT --kill-after=2s 5s \
  ros2 topic echo /turtle1/pose "$POSE_TYPE" --once \
  > evidence/pr01/pose-broken.txt 2>&1
printf 'exit=%s\n' "$?" > evidence/pr01/pose-broken-exit.txt
```

Ожидаются только `/teleop_turtle`, отсутствие позы и `exit=124`.
`--kill-after=2s` защищает от зависания CLI при завершении в этой сборке.
Если код 137, опыт нужно повторить: это принудительное завершение, не ожидаемый таймаут.
Нажмите ↑ в B и проверьте позу из домена симулятора:

```bash
ROS_DOMAIN_ID=16 ros2 topic echo /turtle1/pose --once \
  > evidence/pr01/pose-after-key-broken-control.txt
```

## Восстановление

В B остановите teleop и запустите его снова:

```bash
export ROS_DOMAIN_ID=16
ros2 run turtlesim turtle_teleop_key
```

В C повторите ту же проверку, изменив только домен и выходные файлы:

```bash
export ROS_DOMAIN_ID=16
ros2 node list --no-daemon --spin-time 5 > evidence/pr01/nodes-fixed.txt
timeout --signal=INT --kill-after=2s 5s \
  ros2 topic echo /turtle1/pose "$POSE_TYPE" --once \
  > evidence/pr01/pose-fixed.txt 2>&1
printf 'exit=%s\n' "$?" > evidence/pr01/pose-fixed-exit.txt
```

Ожидаются обе ноды, поза и `exit=0`. После ↑ в B:

```bash
ros2 topic echo /turtle1/pose --once > evidence/pr01/pose-after-key-fixed.txt
```

Сравнение «до / сбой / после» и причина разрыва описаны в `graph.md`.
`ROS_DOMAIN_ID` применяется при запуске ноды, поэтому teleop перезапускается.

## Проверка и сдача

Course kit `v1-w03` закреплён по SHA-256
`7fbfd3e8161ab6c6ebefc7663efdaf77d9a7d490399743507f33dcefbd5ac522`.
На хосте из корня репозитория:

```bash
curl -fsSLo course-kit.tar.gz \
  https://ros.lms.ci.nsu.ru/downloads/robotics-course-kit-v1-w03-7fbfd3e8161a.tar.gz
printf '%s  %s\n' \
  7fbfd3e8161ab6c6ebefc7663efdaf77d9a7d490399743507f33dcefbd5ac522 \
  course-kit.tar.gz | shasum -a 256 -c -
mkdir -p .course-kit
tar -xzf course-kit.tar.gz -C .course-kit
python3 -m json.tool evidence/pr01/environment.json > /dev/null
python3 .course-kit/v1/tools/check_practice.py PR01 --submission .
```

CI проверяет JSON и комплектность evidence. Живой опыт ROS выполняется
локально. Первый коммит содержит README и CI, второй — `evidence/pr01/` и
`AI_USAGE.md`; `report.json.commit` указывает на первый коммит.
