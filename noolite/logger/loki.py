import asyncio
import time
from asyncio import AbstractEventLoop
from collections import defaultdict
from logging import Handler, LogRecord
import ujson
import aiohttp
import typing

from .const import TAG_NAME, TAG_LEVEL, HEADERS

format_label_lru_size: int = 256


class AsyncLokiHandler(Handler):

    def __init__(
            self,
            host: str = 'http://localhost:3100',
            endpoint='/loki/api/v1/push',
            flush_interval=5,
            loop: AbstractEventLoop = None,
            labels: dict = None,
            autostart=True,
            **kwargs
    ):
        """

        :param host: full url of push method
        """
        self._labels = labels or {}
        self._labels = {**self._labels, **kwargs}
        self._host = host
        self._endpoint = endpoint
        self._loop = loop or asyncio.get_event_loop()
        self._lck = asyncio.Lock()
        self._que = asyncio.Queue()
        self._main: asyncio.Task = None
        self._streams: typing.DefaultDict[tuple, typing.List[typing.Tuple[str, str]]] = defaultdict(list)
        self.flush_interval = flush_interval
        self.url = f'{self._host}{self._endpoint}'
        super().__init__()
        if autostart:
            self.start()

    # def flush(self) -> None:
    #

    def start(self):
        assert self._main is None
        self._main = self._loop.create_task(self._run())
        self._processor = self._loop.create_task(self._que_process())

    async def stop(self):
        if self._main is not None:
            self._main.cancel()
            self._processor.cancel()
            await self._main
            self._main = None

    def emit(self, record: LogRecord) -> None:
        self._que.put_nowait(record)

    async def _que_process(self):
        while True:
            try:
                record: LogRecord = await self._que.get()
                async with self._lck:
                    try:
                        stream = self._build_stream_key({
                            TAG_NAME: record.name,
                            TAG_LEVEL: record.levelname.lower(),
                        })
                        self._streams[stream].append((str(time.time_ns()), self.format(record)))
                    except Exception as exc:
                        print(exc)
            except asyncio.CancelledError:
                return

    async def _run(self):
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
            except asyncio.CancelledError:
                print('loki emitter stopped')
                return
            finally:
                try:
                    await self._emit()
                except Exception as exc:
                    print(exc)

    def _build_stream_key(self, labels):
        return tuple((*self._labels.items(), *labels.items()))

    async def _emit(self):
        async with self._lck:
            # print(self._streams)
            if len(self._streams) == 0:
                return
            streams = [
                {
                    'stream': dict(key),
                    'values': values
                }
                for key, values in self._streams.items()
            ]
            payload = ujson.dumps(dict(streams=streams))
            async with aiohttp.request(
                    'post', self.url, headers=HEADERS, data=payload,
            ) as req:
                if req.status > 299:
                    # super().emit(record)
                    raise RuntimeError(f'error while emitting loki (status {req.status}):\n{await req.text()}\n{payload}')
            self._streams = defaultdict(list)

