# ПР02. Топики и типы

Выводы: `launch-topics.txt`, `pose-type.txt`, `cmd-vel-type.txt`,
`twist-interface.txt`, `pose-before.txt`.

## Два основных топика turtlesim

| Топик | Тип | Кто публикует | Кто подписан | Назначение |
|-------|-----|---------------|--------------|------------|
| `/turtle1/cmd_vel` | `geometry_msgs/msg/Twist` | CLI `ros2 topic pub` (в ПР01 — teleop) | `/turtlesim` | команда скорости черепахе |
| `/turtle1/pose` | `turtlesim_msgs/msg/Pose` | `/turtlesim` | CLI `ros2 topic echo` | текущее положение и скорость черепахи |

В ROS 2 Lyrical тип позы — `turtlesim_msgs/msg/Pose`, а не
`turtlesim/msg/Pose`, как в старых дистрибутивах.

## Поля `geometry_msgs/msg/Twist`

```text
Vector3  linear
	float64 x
	float64 y
	float64 z
Vector3  angular
	float64 x
	float64 y
	float64 z
```

Twist — скорость в свободном пространстве, разбитая на линейную и угловую
части. Сам тип систему координат не задаёт; turtlesim трактует скорости
относительно курса черепахи: `linear.x` — вперёд по направлению `theta`.

| Поле | Смысл | В опыте |
|------|-------|---------|
| `linear.x` | линейная скорость вперёд, ед./с | 1.0 — черепаха едет вперёд |
| `linear.y` | линейная скорость вбок, ед./с | 0.0 |
| `linear.z` | линейная скорость вверх; в плоском симуляторе смысла не имеет | 0.0 |
| `angular.x` | угловая скорость вокруг оси x (крен); в 2D смысла не имеет | 0.0 |
| `angular.y` | угловая скорость вокруг оси y (тангаж); в 2D смысла не имеет | 0.0 |
| `angular.z` | угловая скорость вокруг вертикальной оси (рыскание), рад/с; > 0 — поворот против часовой стрелки | 0.5 — θ выросла с 0 до 0.504 |

Поля, не указанные в YAML-строке `ros2 topic pub`, заполняются нулями: это
видно в `pub-once.txt` (`y=0.0, z=0.0` у `linear`, `x=0.0, y=0.0` у
`angular`).

## Поля `turtlesim_msgs/msg/Pose` (для сравнения)

`x`, `y` — координаты черепахи; `theta` — курс, рад; `linear_velocity`,
`angular_velocity` — текущие скорости. После одиночной команды скорости
вернулись к 0 (`pose-after.txt`), а во время непрерывной публикации были
1.0 и 0.5 (`pose-fixed-after.txt`).
