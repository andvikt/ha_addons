from logger import root_logger


async def with_logger(coro, lg=root_logger):
    try:
        return await coro
    except Exception as exc:
        lg.exception(f'in coro: {coro}')
        raise
