# ПР04. Параметры patrol: скорость, поворот, частота

Среда та же, что в ПР03: Ubuntu 26.04.1, ROS 2 Lyrical, Python 3.14.4 в
контейнере `tiryoh/ros2-desktop-vnc:lyrical-20260906T0836`, `ROS_DOMAIN_ID=16`.
turtlesim — `ros2 launch turtle_bringup sim.launch.py`, нода —
`ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel`.
Полные выводы лежат рядом с этим файлом.

## Как устроено

```text
ros2 param set ──► validate()  on-set ──── отказ ──► ответ с причиной;
                    │  validate_values(hz, v, ω)     параметр, поля и таймер прежние
                    │  только проверка, состояние не трогает
                    ▼ принято
                   rclpy записывает параметр
                    ▼
                   apply()  post-set ── поля linear_speed / turn_rate / publish_hz
                                        hz изменилась → timer.cancel(), destroy_timer(),
                                                        create_timer(1 / publish_hz)
tick() ──► choose_command(pose, linear_speed, turn_rate) ──► Twist
```

- `command.py`: `validate_values` — конечные числа, частота 1–30 Гц,
  скорость 0–1 м/с, поворот −1–1 рад/с; `choose_command` берёт скорости из
  параметров. `clamp_command` из ПР03 удалён: с проверкой на входе он
  ничего не ограничивал.
- `patrol.py`: `declare_parameter` со значениями 0.5 / 0.3 / 10.0; стартовые
  значения (в том числе из `--ros-args`) проверяются тем же
  `validate_values`, потому что колбэки регистрируются после объявления.
- Смена скорости или поворота таймер не трогает: `tick` читает поля.

## Исходное состояние: 10 Гц

`fixed-params.txt`, `hz-10.txt`:

```text
$ ros2 param list /patrol
  linear_speed
  publish_hz
  start_type_description_service
  turn_rate
  use_sim_time
$ ros2 param get /patrol publish_hz
Double value is: 10.0
$ timeout --signal=INT 10s ros2 topic hz /turtle1/cmd_vel
average rate: 9.998
	min: 0.096s max: 0.103s std dev: 0.00183s window: 89
```

`linear_speed` и `turn_rate` — 0.5 и 0.3.

## Допустимая смена 10 → 5 Гц

`set-5.txt`, `hz-5.txt`:

```text
$ ros2 param set /patrol publish_hz 5.0
Set parameter successful
$ ros2 param get /patrol publish_hz
Double value is: 5.0
$ timeout --signal=INT 10s ros2 topic hz /turtle1/cmd_vel
average rate: 5.000
	min: 0.181s max: 0.222s std dev: 0.00465s window: 44
```

`get` показывает принятое значение, `hz` — что поток действительно стал
вдвое реже. То, что старый таймер уничтожен и таймер у ноды один,
проверяет `test_valid_rate_replaces_timer`.

## Недопустимые значения отклоняются

`set-invalid.txt`, `hz-after-reject.txt` (нода уже на 5 Гц):

```text
$ ros2 param set /patrol publish_hz 0.0
Setting parameter failed: publish_hz must be in [1.0, 30.0] Hz, got 0.0
$ ros2 param get /patrol publish_hz
Double value is: 5.0
$ ros2 param set /patrol publish_hz -1.0
Setting parameter failed: publish_hz must be in [1.0, 30.0] Hz, got -1.0
$ ros2 param set /patrol publish_hz .nan
Setting parameter failed: publish_hz must be a finite number, got nan
$ ros2 param set /patrol linear_speed 2.0
Setting parameter failed: linear_speed must be in [0, 1.0] m/s, got 2.0
$ ros2 param get /patrol publish_hz
Double value is: 5.0
$ ros2 node list --no-daemon --spin-time 3
/patrol
/turtlesim
$ timeout --signal=INT 10s ros2 topic hz /turtle1/cmd_vel
average rate: 5.000
	min: 0.195s max: 0.205s std dev: 0.00222s window: 40
```

Отказ пришёл с причиной, значение осталось 5.0, нода жива, поток идёт с
прежней частотой. Что сохранился тот же объект таймера, проверяет
`test_invalid_rate_keeps_value_and_timer` (0.0, −1.0, NaN).

Скорость и поворот меняют саму команду (`set-speed.txt`):

```text
$ ros2 param set /patrol linear_speed 1.0
Set parameter successful
$ ros2 param set /patrol turn_rate -0.6
Set parameter successful
$ ros2 topic echo /turtle1/cmd_vel --once
linear:  x: 1.0 …
angular: … z: -0.6
```

## Дефект: проверка частоты отключена

Ветка `pr04-defect`, коммит `38f3a0e` — из `validate_values` убрана только
проверка диапазона `publish_hz` (дифф — в начале `defect.txt`). Сборка —
`defect-build.txt`. Тот же запуск, затем 5.0 и 0.0 (`defect.txt`,
`patrol-defect.log`):

```text
$ ros2 param set /patrol publish_hz 5.0
Set parameter successful
$ timeout --signal=INT --kill-after=2s 5s ros2 param set /patrol publish_hz 0.0
exit=124
$ ros2 node list --no-daemon --spin-time 3
/turtlesim
$ ros2 topic info /turtle1/cmd_vel
Publisher count: 0
Subscription count: 1
$ timeout --signal=INT 5s ros2 topic hz /turtle1/cmd_vel
exit=124
patrol exit=1
```

```text
  File ".../rclpy/parameter_service.py", line 142, in _set_parameters_callback
  File ".../rclpy/node.py", line 1038, in _call_post_set_parameters_callback
  File ".../patrol/patrol.py", line 49, in apply
    self.timer = self.create_timer(1.0 / self.publish_hz, self.tick)
ZeroDivisionError: division by zero
[ros2run]: Process exited with failure 1
```

- **Симптом:** `ros2 param set … 0.0` не получил ответа (оборван по
  таймауту, код 124), поток команд прекратился — `hz` не увидел ни одного
  сообщения.
- **Подтверждения:** `ZeroDivisionError` в `apply`, процесс завершился с
  кодом 1, `/patrol` нет в графе, у `/turtle1/cmd_vel` 0 издателей.
- **Первопричина:** без проверки on-set пропустил 0, rclpy записал параметр
  и вызвал post-set `apply`. Тот отменил и уничтожил старый таймер, а затем
  делил на ноль при расчёте периода. Исключение из колбэка сервиса
  параметров вышло из `spin`, `main` ловит только Ctrl+C — процесс упал.
  Даже если бы исключение поймали, нода осталась бы с `publish_hz = 0` и без
  таймера: проверять нужно **до** изменения состояния.
- **Исправление:** проверка возвращена (`main`, коммит `3c87c03`), тот же
  запрос даёт отказ с причиной, значение 5.0 и поток 5 Гц сохраняются (см.
  раздел выше).

Те же тесты на ветке дефекта (`tests-defect.txt`): 7 failed, 19 passed.
`test_invalid_rate_keeps_value_and_timer[0.0]` и
`test_invalid_set_rejects_whole_batch` падают с тем же `ZeroDivisionError`,
`[-1.0]` — с `RCLError: timer period must be non-negative`,
`test_invalid_publish_hz_is_rejected` — на 0, −5, 0.5 и 30.5 Гц. NaN-случаи
проходят: проверка конечности осталась. На `main` (`tests.txt`) — 30 passed,
1 skipped (copyright, пропуск задан шаблоном); `colcon test-result`
считает 36 тестов, потому что добавляет 5 тестов `turtle_bringup` из
прошлой сборки.

## Готовый сервис `/clear` и действие `rotate_absolute`

`clear.txt`: `ros2 service list -t` показывает `/clear [std_srvs/srv/Empty]`.

```text
$ ros2 topic echo /turtle1/pose --once
x: 1.9306063652038574  y: 6.471914291381836  theta: 2.971229314804077
$ ros2 service call /clear std_srvs/srv/Empty '{}'
requester: making request: std_srvs.srv.Empty_Request()
response:
std_srvs.srv.Empty_Response()
$ ros2 topic echo /turtle1/pose --once
x: 1.9306063652038574  y: 6.471914291381836  theta: 2.971229314804077
```

След стёрт (`turtlesim.log`: `Clearing turtlesim.`), поза та же.

`action.txt`:

```text
$ ros2 action list -t
/turtle1/rotate_absolute [turtlesim_msgs/action/RotateAbsolute]
$ ros2 action info /turtle1/rotate_absolute
Action clients: 0
Action servers: 1
    /turtlesim
$ ros2 action send_goal /turtle1/rotate_absolute \
    turtlesim_msgs/action/RotateAbsolute '{theta: 1.57}' --feedback
Goal accepted with ID: aa4e1e3ffffd46ea89a634261c873965
Feedback:
    remaining: -1.4012292623519897
…  (88 сообщений feedback)
Feedback:
    remaining: -0.009229302406311035
Result:
    delta: 1.3919999599456787
Goal finished with status: SUCCEEDED
```

Цель отправлена после остановки `patrol`, чтобы команды скорости не мешали
повороту; черепаха смотрела на θ ≈ 2.97, поэтому `remaining` отрицательный.

**Запрос и цель.** Запрос сервиса `/clear` — одна короткая операция: клиент
отправляет `Empty.Request` и получает `Empty.Response`, когда след уже стёрт,
без промежуточных сообщений и без возможности отменить. Цель
`/turtle1/rotate_absolute` живёт дольше вызова: сервер сначала принимает её,
во время поворота шлёт feedback `remaining`, в конце возвращает result
`delta` и итоговый статус (`SUCCEEDED`, `CANCELED` или `ABORTED`), а клиент
может отдельно запросить отмену.

## Проверка

```bash
python3 -m pytest src/patrol/test
python3 .course-kit/v1/tools/check_practice.py PR04 --submission .
```
