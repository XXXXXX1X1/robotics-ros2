# ПР02. Команды, выводы и сравнение

Среда: Ubuntu 26.04.1, ROS 2 Lyrical, Python 3.14.4 в контейнере
`tiryoh/ros2-desktop-vnc:lyrical-20260906T0836` (как в ПР01),
`ROS_DOMAIN_ID=16`. Все выводы ниже сохранены в файлы этой папки.

## Три команды Linux

### 1. `mkdir -p src evidence/pr02`

- **Назначение:** создать каталог исходников workspace и каталог evidence.
  `-p` создаёт недостающие родительские каталоги и не считает ошибкой уже
  существующий каталог, поэтому команду можно повторять.
- **Результат:** появились `src/` и `evidence/pr02/`; вывода нет, код 0.

### 2. `set -o pipefail; colcon build ... 2>&1 | tee evidence/pr02/build.txt`

Точная команда:

```bash
set -o pipefail
colcon build --symlink-install --packages-select turtle_bringup \
  2>&1 | tee evidence/pr02/build.txt
```

- **Назначение:** собрать только `turtle_bringup`, показать лог в терминале
  и одновременно сохранить его в файл. `2>&1` направляет stderr туда же, куда
  stdout, чтобы ошибки сборки тоже попали в лог. `|` передаёт этот поток
  программе `tee`. `set -o pipefail` делает код возврата конвейера ненулевым,
  если упал `colcon`; без него код был бы кодом `tee`, то есть 0 даже при
  ошибке сборки.
- **Результат:** `Summary: 1 package finished [0.73s]`, код 0 (`build.txt`).
  Для пустого пакета та же команда дала `build-empty.txt`.

### 3. `source install/setup.bash`

- **Назначение:** добавить в окружение текущей оболочки пути overlay
  (`AMENT_PREFIX_PATH` и другие), чтобы ROS 2 нашёл собранный пакет.
- **Результат:** `ros2 pkg prefix turtle_bringup` вывел
  `/home/ubuntu/ros2_ws/install/turtle_bringup` (`pkg-prefix.txt`).

## `>` и `|`

- `>` перенаправляет stdout команды **в файл** и перезаписывает его. Пример:
  `ros2 topic echo /turtle1/pose --once > pose-before.txt`. В терминале при
  этом ничего не видно, данные только в файле.
- `|` передаёт stdout одной команды **на stdin другой программы**. Пример:
  `colcon build ... 2>&1 | tee build.txt`. Здесь вторая программа, `tee`,
  печатает поток на экран и пишет его в файл.

Итог: `>` — «куда сохранить», `|` — «кому передать дальше».

## `source` и запуск новой программы

`source файл` выполняет скрипт **в текущей оболочке**, поэтому сделанные им
`export` остаются после завершения. `bash файл` запускает **дочерний процесс**:
он меняет только своё окружение, а после выхода изменения пропадают.
Проверка (`source-vs-bash.txt`):

```text
$ bash install/setup.bash && ros2 pkg prefix turtle_bringup
Package not found
exit=1
$ source install/setup.bash && ros2 pkg prefix turtle_bringup
/home/ubuntu/ros2_ws/install/turtle_bringup
exit=0
```

По той же причине `source` нужен в каждом новом терминале.

## Сборка и запуск

| Шаг | Команда | Результат | Файл |
|-----|---------|-----------|------|
| Пустой пакет | `colcon build --symlink-install --packages-select turtle_bringup` | 1 package finished, exit 0 | `build-empty.txt` |
| Обнаружение | `ros2 pkg prefix turtle_bringup` | `/home/ubuntu/ros2_ws/install/turtle_bringup` | `pkg-prefix.txt` |
| С launch | та же сборка после добавления `launch/sim.launch.py` | 1 package finished, exit 0; файл установлен в `install/turtle_bringup/share/turtle_bringup/launch/` | `build.txt` |
| Запуск | `ros2 launch turtle_bringup sim.launch.py` | `Starting turtlesim with node name /turtlesim`, черепаха в (5.544445, 5.544445, 0) | `launch.txt` |
| Граф | `ros2 node list`, `ros2 topic list -t` | нода `/turtlesim`, топики `/turtle1/cmd_vel`, `/turtle1/pose` и др. | `launch-nodes.txt`, `launch-topics.txt` |
| Остановка | SIGINT (Ctrl+C) процессу `ros2 launch` | `process has finished cleanly`; после этого `ros2 node list` пуст | `launch.txt`, `nodes-after-stop.txt` |

## Доставка команды (этап 4)

```bash
ros2 interface show geometry_msgs/msg/Twist   # twist-interface.txt
ros2 topic type /turtle1/pose                 # turtlesim_msgs/msg/Pose
ros2 topic echo /turtle1/pose --once          # pose-before.txt
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'     # pub-once.txt
ros2 topic echo /turtle1/pose --once          # pose-after.txt
```

- **Начальная поза:** x = 5.544445, y = 5.544445, θ = 0.0.
- **Ожидание:** черепаха смотрит вдоль +x; `linear.x = 1.0` двигает её
  вперёд, `angular.z = 0.5` поворачивает против часовой стрелки. Значит,
  x растёт, y немного растёт, θ растёт — дуга влево.
- **Факт:** x = 6.509309, y = 5.796991, θ = 0.504; скорости снова 0.
  Приращение θ = 0.504 ≈ 0.5 рад/с × 1 с: одна команда подействовала около
  секунды, и черепаха остановилась.

## Сбой и исправление (этап 5)

Сбой — тот же Twist в топик без пространства имён черепахи:

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose
```

Исправление — та же команда, изменено только имя: `/cmd_vel` →
`/turtle1/cmd_vel`. Издатель в обоих случаях работал 12 с
(`timeout --signal=INT 12s`, отсюда `exit=124` в `pub-*.txt`), `info` и `echo`
выполнялись на 5-й секунде публикации.

| | До (этап 4) | Сбой: `/cmd_vel` | После: `/turtle1/cmd_vel` |
|---|---|---|---|
| Тип | `geometry_msgs/msg/Twist` | `geometry_msgs/msg/Twist` | `geometry_msgs/msg/Twist` |
| Издатели `/cmd_vel` | — | 1 (`_ros2cli_2425`) | топика нет: `Unknown topic '/cmd_vel'` |
| Подписчики `/cmd_vel` | — | **0** | — |
| Издатели `/turtle1/cmd_vel` | не замерялось (`--once`) | **0** | 1 (`_ros2cli_2588`) |
| Подписчики `/turtle1/cmd_vel` | не замерялось | 1 (`turtlesim`) | 1 (`turtlesim`) |
| Поза до публикации | (5.544, 5.544, 0.000) | (6.509, 5.797, 0.504) | (6.509, 5.797, 0.504) |
| Поза во время публикации | — | (6.509, 5.797, 0.504), v = 0 | (5.237, 9.522, −2.995), v = 1.0, ω = 0.5 |
| Итог | поехала | **не поехала** за 12 сообщений | поехала; после остановки (5.998, 5.598, 0.229) |

Файлы: `pose-broken-*.txt`, `pub-broken.txt`, `info-broken-*.txt`,
`pose-fixed-*.txt`, `pub-fixed.txt`, `info-fixed-*.txt`.

Во время сбоя издатель печатал `publishing #1 … #12`, то есть CLI честно
отправлял сообщения, но их никто не получал.

## Почему правильного типа недостаточно

В сбое тип и даже хеш типа совпадают у обоих топиков:
`RIHS01_9c45bf16fe0983d80e3cfe750d6835843d265a9a6c46bd2e609fcddde6fb8d2a`.
DDS соединяет издателя и подписчика только при совпадении **полного имени
топика** (и совместимом QoS). `/cmd_vel` и `/turtle1/cmd_vel` — разные
топики, поэтому у издателя 0 подписчиков, а у turtlesim 0 издателей.

## Обнаружение и доставка

- **Обнаружение** — ноды видят друг друга в графе: `ros2 topic info` в сбое
  показывает и издателя CLI, и подписчика turtlesim. Оба в одном домене 16.
- **Доставка** — сообщение пришло к нужному подписчику и изменило его
  состояние. Её доказывают `Subscription count: 1` у **того же** топика, что
  у издателя, и изменение позы, а не строка `publishing #N` в выводе
  издателя.

Сбой ПР01 (разные домены) ломал обнаружение. Сбой ПР02 обнаружение не ломает:
граф виден полностью, но из-за имени топика доставки нет.
