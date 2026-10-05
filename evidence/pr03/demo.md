# ПР03. Нода patrol: поза, таймер, remap

Среда: Ubuntu 26.04.1, ROS 2 Lyrical, Python 3.14.4 в контейнере
`tiryoh/ros2-desktop-vnc:lyrical-20260906T0836`, `ROS_DOMAIN_ID=16`.
turtlesim запускался через `ros2 launch turtle_bringup sim.launch.py` из ПР02.
Все выводы лежат рядом с этим файлом.

## Как устроена нода

```text
             /turtle1/pose (Pose)                     cmd_vel (Twist)
turtlesim ─────────────────────► on_pose()            tick() ─────────────► ?
                                   │ только сохраняет   ▲ таймер 0.1 с
                                   ▼                    │
                             self.latest_pose ──► choose_command() ─► clamp_command()
                                                  None → (0, 0)        [-1, 1]
                                                  поза → (0.5, 0.3)
```

- `src/patrol/patrol/patrol.py` — класс `Patrol(Node)`: поле `latest_pose`,
  подписка `pose_sub` на `/turtle1/pose`, издатель в **относительный**
  `cmd_vel`, таймер 0.1 с.
- `src/patrol/patrol/command.py` — чистые функции без ROS:
  `choose_command(pose)` и дополнительное ограничение `clamp_command`.
- `src/patrol/test/test_command.py` — нет позы, обычная поза, поза с
  другими значениями, ограничение обоих знаков и своих пределов
  (`tests.txt`: 10 passed, 1 skipped — copyright, пропуск задан шаблоном).

## Роли `init`, `spin`, callback и Ctrl+C

- **`rclpy.init(args=args)`** создаёт контекст ROS: подключение к
  middleware и разбор аргументов после `--ros-args`. Именно здесь
  запоминается remap `-r cmd_vel:=/turtle1/cmd_vel`; нода, созданная в этом
  контексте, применяет его к своим именам. До `init` нельзя создать ноду.
- **`rclpy.spin(node)`** отдаёт управление исполнителю (executor). Он ждёт
  событий — пришло сообщение, истёк таймер — и вызывает соответствующие
  callback. Пока идёт `spin`, `main` дальше не выполняется; без `spin` ни
  подписка, ни таймер не сработают, хотя нода будет видна в графе.
- **Callback** — функция, которую мы только регистрируем, а вызывает
  исполнитель: `on_pose` при каждом сообщении позы, `tick` каждые 0.1 с.
  Исполнитель однопоточный, callback выполняются по очереди, поэтому
  `latest_pose` читается и пишется без блокировок. Callback должен быть
  коротким: пока он работает, остальные ждут.
- **Ctrl+C** посылает SIGINT, и `spin` прерывается исключением: обычно
  `KeyboardInterrupt`, а если контекст ROS завершили раньше —
  `ExternalShutdownException`. Официальный пример rclpy ловит оба, так же
  сделано и здесь. Выход из `with rclpy.init(...)` завершает
  контекст и уничтожает ноду: издатель и подписка исчезают из графа
  (`stop-info-turtle1-cmd_vel.txt`: `Publisher count: 0`).

### Ctrl+C приходит дважды

При Ctrl+C терминал шлёт SIGINT всей группе процессов, а `ros2 run` ещё и
пересылает его ноде (`[ros2run]: Received signal: Interrupt` в логах). То же
у launch: в `turtlesim.log` два `signal_handler(signum=2)`.

Каркас из лекции (`try: spin … except KeyboardInterrupt … finally:
destroy_node(); try_shutdown()`) у полной ноды дал трейсбек: второй SIGINT
пришёл внутри `finally`, во время `destroy_node()`, где его уже никто не
ловит (`ctrl-c-lecture-main.log`). Нода всё равно остановилась, но с
ошибкой в выводе.

`main` переписан по официальному примеру rclpy в Lyrical
(`examples_rclpy_minimal_publisher`): `with rclpy.init(...)` внутри
`try`, снаружи `except (KeyboardInterrupt, ExternalShutdownException)`.
Второй сигнал во время освобождения ресурсов тоже попадает в этот
`except`. Проверка — 5 остановок подряд без трейсбека
(`ctrl-c-fixed-main.txt`). Однажды второй сигнал пришёл уже после выхода из
`main`, во время завершения интерпретатора: Python напечатал
`Exception ignored in atexit callback … KeyboardInterrupt`
(`patrol-no-pose.log`). Процесс при этом завершился; из кода ноды такой
сигнал не поймать, потому что `main` уже закончился.

## 1. Минимальная нода

Первым шагом собрана нода из лекции (`rclpy.init`, `Node('patrol')`,
`spin`): `ros2 node list` показал `/patrol`, у неё только служебные
`/parameter_events` и `/rosout` (`minimal-node-list.txt`,
`minimal-node-info.txt`).

## 2. До первой позы — нулевая команда

turtlesim не запущен, позы нет:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
ros2 topic echo /turtle1/cmd_vel --once
```

Результат: `linear.x = 0.0`, `angular.z = 0.0` (`no-pose-cmd.txt`).

## 3. Сбой: относительный `cmd_vel`

```bash
ros2 launch turtle_bringup sim.launch.py      # терминал A
ros2 run patrol patrol                        # терминал B, без remap
ros2 node info /patrol                        # терминал C
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose
ros2 topic echo /cmd_vel --once
ros2 topic echo /turtle1/pose --once          # до и после этих проверок
```

Нода в корневом пространстве имён, поэтому относительное имя `cmd_vel`
разрешается в `/cmd_vel`, а turtlesim слушает `/turtle1/cmd_vel`.

## 4. Исправление: remap при запуске

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

Код не менялся: remap подменяет имя `cmd_vel` до разрешения.

## Сравнение

| | Сбой: без remap | После: `-r cmd_vel:=/turtle1/cmd_vel` |
|---|---|---|
| Издатель `/patrol` (`node info`) | `/cmd_vel` | `/turtle1/cmd_vel` |
| Подписка `/patrol` | `/turtle1/pose` | `/turtle1/pose` |
| `/cmd_vel`: издатели / подписчики | 1 (`patrol`) / **0** | топика нет: `Unknown topic '/cmd_vel'` |
| `/turtle1/cmd_vel`: издатели / подписчики | **0** / 1 (`turtlesim`) | 1 (`patrol`) / 1 (`turtlesim`) |
| Команда в топике издателя | `linear.x 0.5, angular.z 0.3` в `/cmd_vel` | `0.5, 0.3` в `/turtle1/cmd_vel` |
| Поза | стоит: (5.544, 5.544, 0.0) до и после | едет: (5.544, 5.544, 0.0) → (6.534, 8.550, 2.501), v = 0.5, ω = 0.3 |

Файлы: `broken-*.txt`, `fixed-*.txt`.

Важная деталь сбоя: в `/cmd_vel` шла **ненулевая** команда. Значит, поза
до ноды доходила и `choose_command` выбрал движение — сломана была только
доставка команды из-за имени, а не подписка и не логика.

## Частота команды за 10 секунд

```bash
timeout --signal=INT 10s ros2 topic hz /turtle1/cmd_vel
timeout --signal=INT 10s ros2 topic echo /turtle1/cmd_vel --csv
```

- `ros2 topic hz`: `average rate: 9.999`, период от 0.096 до 0.103 с,
  `std dev: 0.00160s`, в окне 89 сообщений (`cmd-hz.txt`,
  `cmd-hz-duration.txt`).
- Подсчёт через `echo`: 92 сообщения за 10.229 с (`cmd-echo-10s.csv`,
  `cmd-echo-count.txt`).

Реальная частота — 10 Гц, как задано таймером 0.1 с. Сообщений меньше 100,
потому что каждая CLI-команда тратит около секунды на запуск и обнаружение
издателя и начинает считать не с нулевой секунды.

## Остановка ноды — не команда торможения

После Ctrl+C нода перестаёт публиковать, но turtlesim продолжает
выполнять последнюю полученную команду. Поза записывалась каждые 0.1 с
(`pose_sampler.py`), время прихода команд — `cmd_recorder.py`; сырые данные
в `stop-runs/`, сводка в `stop-timing.txt`:

| Прогон | Последняя команда − SIGINT, с | Остановка − SIGINT, с | Остановка − последняя команда, с |
|---|---|---|---|
| 1 | −0.077 | +1.042 | 1.119 |
| 2 | −0.060 | +1.033 | 1.093 |
| 3 | −0.703 | +0.384 | 1.087 |

Первый пробный прогон без записи команд — `stop-pose-samples.csv` и
`stop-sigint-time.txt`: черепаха встала примерно через 0.6 с после SIGINT;
это расхождение с ожидаемой секундой и стало поводом записать время команд.

«Остановка» — первая выборка позы с `linear_velocity = 0`; последняя
выборка с движением во всех прогонах была через 0.985–1.020 с после
последней команды. Вывод: черепаха останавливается примерно через **1 с
после последней полученной команды** — это таймаут команды в turtlesim, тот
же, что в ПР02 (одна команда повернула θ на 0.504 при ω = 0.5). Время от
Ctrl+C до остановки поэтому зависит от момента последней публикации. В
прогоне 3 последняя команда пришла за 0.70 с до отметки SIGINT; причину
такого зазора я не установил.

Исчезновение процесса — не мгновенное торможение: робот без такого
таймаута ехал бы дальше. Для немедленной остановки нужно перед выходом
опубликовать нулевой Twist; в этой ПР это не требуется.
