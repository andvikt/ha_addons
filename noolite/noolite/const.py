from logger import root_logger
from .typing import TempHumSensor, MotionSensor

lg = logger = root_logger.getChild('noolite')


F_OUT_BEG = 171
F_OUT_END = 172
F_IN_BEG = 173
F_IN_END = 174
MOTION_JITTER = 3  # минимальное кол-во секунд между командами от датчика движения, команды, пришедшие раньше этого
# когда приходит новая команда, она передается в конструктор обработчика команд
# тут указываем все возможные конструкторы для конкретных команд
# этот справочник так же используется для отправки команд через api

dispatching_constructors = (
    (0	, None, 'off 	', 'Выключить нагрузку.'),
    (1	, None, 'bright_down 	', 'Запускает плавное понижение яркости.'),
    (2	, None, 'on', 'Включить нагрузку.'),
    (3	, None, 'bright_up 	', 'Запускает плавное повышение яркости вниз.'),
    (4	, None, 'switch 	', 'Включает или выключает нагрузку.'),
    (5	, None, 'bright_back 	', 'Запускает плавное изменение яркости в обратном направлении.'),
    (6	, None, 'set_brightness 	', 'Установить заданную в расширении команды яркость (количество данных зависит от устройства).'),
    (7	, None, 'load_preset', 'Вызвать записанный сценарий.'),
    (8	, None, 'save_preset 	', 'Записать сценарий в память.'),
    (9	, None, 'unbind 	', 'Запускает процедуру стирания адреса управляющего устройства из памяти исполнительного'),
    (10	, None, 'stop_reg 	', 'Прекращает действие команд Bright_Down,'),
    (11	, None, 'bright_step_down 	', 'Понизить яркость на шаг. При отсутствии поля данных увеличивает отсечку на 64 мкс, при наличии поля данных на величину в микросекундах (0 соответствует 256 мкс).'),
    (12	, None, 'bright_step_up ', 'яркость на шаг. При отсутствии поля данных уменьшает отсечку на 64 мкс, при наличии поля данных на величину в микросекундах (0 соответствует 256 мкс).'),
    (13	, None, 'bright_reg', 'Запускает плавное изменение яркости с направлением и скоростью, заданными в расширении.'),
    (15	, None, 'bind 	', 'Сообщает исполнительному устройству, что управляющее хочет активировать режим привязки. При привязке также передаѐтся тип устройства в данных.'),
    (16	, None, 'roll_colour 	', 'Запускает плавное изменение цвета в RGB- контроллере по радуге'),
    (17	, None, 'switch_colour 	', 'Переключение между стандартными цветами в RGB-контроллере.'),
    (18	, None, 'switch_mode 	', 'Переключение между режимами RGB- контроллера.'),
    (19	, None, 'speed_Mode_Back', 	'Запускает изменение скорости работы режимов RGB контроллера в обратном направлении.'),
    (20	, None, 'battery_low 	', 'У устройства, которое передало данную команду, разрядился элемент питания.'),
    (21	, TempHumSensor, 'sens_temp_humi 	', 'Передает данные о температуре, влажности и состоянии элементов.'),
    (25	, MotionSensor, 'temporary_on 	', 'Включить свет на заданное время. Время в 5- секундных тактах передается в расширении (см. описание A).'),
    (26	, None, 'modes 	', 'Установка режимов работы исполнительного устройства (см. описание B).'),
    (128	, None, 'read_state 	', 'Получение состояния исполнительного устройства (см. описание C).'),
    (129	, None, 'write_state 	', 'Установка состояния исполнительного устройства.'),
    (130	, None, 'send_state 	', 'Ответ от исполнительного устройства (см. описание C).'),
    (131	, None, 'service 	', 'Включение сервисного режима на заранее привязанном устройстве (см. описание D).'),
    (132	, None, 'clear_memory 	', 'Очистка памяти устройства nooLite. Для выполнения команды используется ключ 170- 85-170-85 (записывается в поле данных D0...D3).'),
)
api_commands = {x[2].strip().lower(): x[0] for x in dispatching_constructors}
dispatchers = {x[0]: (x[1], x[2]) for x in dispatching_constructors}
SENS_TEMP = '001'
SENS_HUM_TEMP = '010'


OFF = 0
BRIGHT_DOWN = 1
ON = 2
BRIGHT_UP = 3
SWITCH = 4
BRIGHT_BACK = 5
SET_BRIGHTNESS = 6
LOAD_PRESET = 7
SAVE_PRESET = 8
UNBIND = 9
STOP_REG = 10
BRIGHT_STEP_DOWN = 11
BRIGHT_STEP_UP = 12
BRIGHT_REG = 13
BIND = 15
ROLL_COLOUR = 16
SWITCH_COLOUR = 17
SWITCH_MODE = 18
SPEED_MODE_BACK = 19
BATTERY_LOW = 20
SENS_TEMP_HUMI = 21
TEMPORARY_ON = 25
MODES = 26
READ_STATE = 128
WRITE_STATE = 129
SEND_STATE = 130
SERVICE = 131
CLEAR_MEMORY = 132

services = {
    'BIND_TX': {'cmd': BIND, 'commit': None}
    , 'BIND_RX': {'mode': 1, 'ctr': 3, 'commit': 40}
    , 'UNBIND_TX': {'cmd': UNBIND, 'commit': None}
    , 'UNBIND_RX': {'mode': 1, 'ctr': 5, 'commit': None}
    , 'RESET_ALL': {'mode': 1, 'ctr': 6, 'd0': 170, 'd1': 85, 'd2': 170, 'd3': 85, 'commit': None}
}


