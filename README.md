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
