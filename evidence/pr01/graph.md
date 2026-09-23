# ПР01. Граф ROS 2 и разрыв связи между доменами

Опыт выполнен 23 сентября 2026 года в одном Docker-контейнере:
Ubuntu 26.04.1, ROS 2 Lyrical, RMW `rmw_fastrtps_cpp`.
Окно turtlesim работало через VNC; клавиша ↑ передавалась настоящему
`turtle_teleop_key` через терминал PTY. Команды и порядок повторения — в
[README](../../README.md), версии среды — в [environment.json](environment.json).

## Исправный граф: домен 16

Симулятор `/turtlesim` и управление `/teleop_turtle` были запущены в домене 16.
`ros2 node list --no-daemon --spin-time 5` обнаружил обе ноды:

```text
/teleop_turtle
/turtlesim
```

Исходный вывод — [nodes-before.txt](nodes-before.txt). `/teleop_turtle`
публикует команды скорости в `/turtle1/cmd_vel` с типом
`geometry_msgs/msg/Twist`; `/turtlesim` подписан на этот топик и публикует
позу `/turtle1/pose` (`turtlesim_msgs/msg/Pose`) и цвет под черепахой
`/turtle1/color_sensor` (`turtlesim_msgs/msg/Color`). Это проверено через
[node info симулятора](turtlesim-info.txt) и [node info управления](teleop-info.txt).

`ros2 topic list -t --no-daemon --spin-time 5` вернул:

```text
/parameter_events [rcl_interfaces/msg/ParameterEvent]
/rosout [rcl_interfaces/msg/Log]
/turtle1/cmd_vel [geometry_msgs/msg/Twist]
/turtle1/color_sensor [turtlesim_msgs/msg/Color]
/turtle1/pose [turtlesim_msgs/msg/Pose]
```

Исходный [список топиков](topics.txt) и отдельно определённый
[тип позы](pose-type.txt) сохранены. CLI-команды `echo` и `hz` создают
временных подписчиков на позу; teleop на неё не подписывается.

До нажатия клавиши [поза](pose-before.txt) имела `x=5.544444561004639`,
`y=5.544444561004639`. После ↑ в исправном домене `x` стала
`7.560444355010986`, что подтверждает фактическое движение:
[поза после клавиши](pose-after-key-working.txt).

## Частота позы

Команда `timeout --signal=INT 12s ros2 topic hz /turtle1/pose`
проработала **12.893 с**; последняя средняя частота — **62.495 Гц**.
Это соответствует периоду публикации порядка 16 мс. [Вывод hz](pose-hz.txt),
[длительность](pose-hz-duration.txt) и [код завершения](pose-hz-exit.txt)
сохранены отдельно. `exit=124` здесь означает намеренное завершение замера
по таймеру: сообщения поступали и участвовали в расчёте частоты.

## Разрыв связи: teleop и CLI в домене 17

Симулятор остался в 16. Teleop был остановлен и заново запущен в 17; CLI
также переключён в 17. `node list --no-daemon --spin-time 5` обнаружил только
`/teleop_turtle`: [nodes-broken.txt](nodes-broken.txt).

Для проверки позы использован тип, полученный в исправном домене:

```bash
timeout --signal=INT --kill-after=2s 5s ros2 topic echo \
  /turtle1/pose turtlesim_msgs/msg/Pose --once
```

За 5 секунд сообщение не пришло: [pose-broken.txt](pose-broken.txt) пуст,
[pose-broken-exit.txt](pose-broken-exit.txt) содержит `exit=124`.
После ↑ в teleop, работающем в 17, контрольное чтение из домена симулятора
показало прежние `x=7.560444355010986`, `y=5.544444561004639`:
[контрольная поза](pose-after-key-broken-control.txt). Симулятор продолжал
публиковать в 16, но команда из 17 до него не дошла.

## Восстановление: возврат в домен 16

Teleop остановлен и заново запущен в 16. CLI возвращён в 16. Повторена та же
команда `timeout … ros2 topic echo` с тем же типом и таймаутом 5 секунд.
Теперь [видны обе ноды](nodes-fixed.txt), [поза получена](pose-fixed.txt),
[код завершения](pose-fixed-exit.txt) — `exit=0`.
После нового ↑ координата `x` выросла до `9.576444625854492`:
[поза после восстановления](pose-after-key-fixed.txt).

| Состояние | Домены sim / teleop / CLI | Ноды в CLI | Поза в CLI | exit | x после ↑ |
|---|---|---|---|---:|---:|
| До | 16 / 16 / 16 | sim и teleop | получена | 0 | 7.560444 |
| Разрыв | 16 / 17 / 17 | только teleop | нет за 5 с | 124 | 7.560444 |
| После | 16 / 16 / 16 | sim и teleop | получена | 0 | 9.576445 |

**Причина.** `ROS_DOMAIN_ID` определяет область обнаружения ноды при её
запуске. Ноды из разных доменов друг друга не обнаруживают, даже если имена
топиков и типы совпадают. `export` меняет окружение для новых процессов и
не перенастраивает уже работающую ноду, поэтому teleop пришлось перезапускать.
Симулятор всё время оставался в 16; его и установку ROS менять не требовалось.
