import asyncio
from datetime import datetime

import serial

from logger import root_logger
from . import const
from .typing import NooliteCommand, BaseNooliteRemote, MotionSensor
from typing import Dict, Callable
import typing

lg = root_logger.getChild('noolite')


class NotApprovedError(Exception):
    pass


class Noolite:

    def __init__(
            self,
            tty_name: str,
            loop: typing.Optional[asyncio.AbstractEventLoop],
    ):
        self.callbacks: Dict[int, Callable] = {}
        self.global_cbs = []
        self._cmd_log: typing.Dict[int, datetime] = {}
        self.event_que: asyncio.Queue[BaseNooliteRemote] = asyncio.Queue()
        self.tty = _get_tty(tty_name)
        self.loop = loop
        self.loop.add_reader(self.tty.fd, self._handle_tty)
        self.wait_ftr: typing.Optional[asyncio.Future] = None
        self.wait_cmd: typing.Optional[NooliteCommand] = None
        self.send_lck = asyncio.Lock()

    def _handle_tty(self):
        """
        Хендлер входящих данных от адаптера
        :return:
        """
        while self.tty.in_waiting >= 17:
            in_bytes = self.tty.read(17)
            resp = NooliteCommand(*(x for x in in_bytes))
            lg.debug(f'< %s', list(in_bytes))
            if self._cancel_waiting(resp):
                return
            asyncio.create_task(self.handle_command(resp))

    def _cancel_waiting(self, msg: NooliteCommand):
        """
        Отменяет ожидание подвтерждения, возвращает истину если ожидание было, ложь, если нет
        :return:
        """
        if isinstance(self.wait_ftr, asyncio.Future) \
                and msg.ch == self.wait_cmd.ch \
                and msg.mode == self.wait_cmd.mode:
            self.wait_ftr.set_result(True)
            lg.debug(f'{"Approved:".rjust(20, " ")} {self.wait_cmd}')
            return True
        else:
            return False

    @property
    async def in_commands(self):
        """
        Возвращает пришедшие команды в бесконечном цикле
        :return:
        """
        while True:
            yield await self.event_que.get()

    async def handle_command(self, resp: NooliteCommand):
        """
        При приеме входящего сообщения нужно вызвать этот метод

        :param resp:
        :return:
        """
        try:
            dispatcher, name = const.dispatchers.get(resp.cmd, (None, None))
            if name:
                lg.debug(f'dispatching {name}')
            if dispatcher is None:
                dispatcher = BaseNooliteRemote
            remote = dispatcher(resp)
            if isinstance(remote, MotionSensor):
                l = self._cmd_log.get(remote.channel)
                self._cmd_log[remote.channel] = datetime.now()
                if l is not None:
                    td = (datetime.now() - l).total_seconds()
                    if td < const.MOTION_JITTER:
                        lg.debug(f'anti-jitter: {resp}')
                        return
            await self.event_que.put(remote)
        except Exception:
            lg.exception(f'handling {resp}')
            raise

    async def send_command(self, command: typing.Union[NooliteCommand, bytearray]):
        """
        Отправляет команды, асинхронно, ждет подтверждения уже отправленной команды
        :param command:
        :return:
        """
        # отправляем только одну команду до получения подтверждения
        async with self.send_lck:
            if isinstance(command, NooliteCommand):
                cmd = command.as_tuple()
            else:
                cmd = command
            lg.debug(f'> {cmd}')
            self.tty.write(bytearray(cmd))
            # отправляем команду и ждем секунду, если придет ответ, то ожидание будет отменено с ошибкой CancelledError
            # - значит от модуля пришел ответ о подтверждении команды, в противном случае поднимаем ошибку о том что
            # команда не подтверждена

            if command.commit is None:
                return True
            self.wait_ftr = self.loop.create_future()
            self.wait_cmd = command
            try:
                await asyncio.wait_for(self.wait_ftr, command.commit)
                await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                return True
            except asyncio.TimeoutError:
                raise NotApprovedError(command)
            finally:
                self.wait_ftr = None
                self.wait_cmd = None


def _get_tty(tty_name) -> serial.Serial:
    """
    Подключение к последовательному порту
    :param tty_name: имя порта
    :return:
    """
    serial_port = serial.Serial(tty_name, 9600, timeout=2)
    if not serial_port.is_open:
        serial_port.open()
    serial_port.flushInput()
    serial_port.flushOutput()
    return serial_port
