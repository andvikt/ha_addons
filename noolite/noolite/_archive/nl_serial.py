import typing

from logger import root_logger
from logger import with_logger
from noolite.typing import NooliteCommand
from noolite.noolite import NooliteBase
from typing import Optional
import asyncio

lg = root_logger.getChild('noolite')


class NotApprovedError(Exception):
    pass


class NooliteSerial(NooliteBase):
    """
    Взаимодействие с noolite через serial-порт
    """
    def __init__(
            self,
            tty_name: str,
            loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        :param tty_name: имя порта
        :param loop: eventloop, по умолчанию текущий евентлуп
        """
        super(NooliteSerial, self).__init__()
        self.tty = self._get_tty(tty_name)
        self.responses = []
        self._loop = loop
        #работа с очередью исходящих сообщений
        self.send_lck = asyncio.Lock()
        self._clients_lock = asyncio.Lock()
        self._clients: typing.List[asyncio.StreamWriter] = []
        self.wait_ftr: Optional[asyncio.Future] = None
        self.wait_cmd: Optional[NooliteCommand] = None
        self._started = False

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop or asyncio.get_event_loop()

    def start(self):
        """
        Начать прослушивание порта, можно запускать только при наличии работающего eventloop
        :return:
        """
        assert not self._started
        self._started = True
        self.loop.add_reader(self.tty.fd, self.handle_tty)
        lg.debug('start listening')

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

    def handle_tty(self):
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

    async def _on_new_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        lg.debug('adding new client %s', writer)
        async with self._clients_lock:
            self._clients.append(writer)
        try:
            while True:
                try:
                    _packet = await reader.readexactly(17)
                    # _packet = await reader.readuntil(bytes(const.F_OUT_BEG))
                    # _packet = await reader.readuntil(bytes(const.F_OUT_END))
                    await asyncio.sleep(0.05)
                except asyncio.IncompleteReadError:
                    lg.info('client disconnected')
                    return
                try:
                    cmd = NooliteCommand(*list(_packet))
                    await self.send_command(cmd)
                    lg.debug(f'write {_packet}')
                    writer.write(_packet)
                    await writer.drain()
                except NotApprovedError:
                    continue
        except Exception:
            lg.exception('while handling tcp client')
        finally:
            async with self._clients_lock:
                lg.debug('closing %s', writer)
                writer.close()
                self._clients.remove(writer)


async def _slow_down(coro):
    await asyncio.sleep(0.05)
    await with_logger(coro, lg=lg)
