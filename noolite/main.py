import asyncio
from asyncio import FIRST_EXCEPTION
from asyncio_mqtt import client as ac
from asyncio_mqtt import Client, Will
from logger import root_logger
import noolite as noo
import ujson
import yaml
from yaml.loader import FullLoader
from logging import DEBUG
import os


loop = asyncio.get_event_loop()
with open(os.environ['CONFIG_PATH']) as f:
    cfg = ujson.load(f)
    print(str(cfg))

lg = root_logger.getChild('noolite_mqtt')
lg.setLevel(cfg['log_level'])

DEFAULT_LIGHT_TIMEOUT = 12 * 60 * 60  # все команды на включение света должны выполняются в форме TEMPORARY_ON с
# дефолтным временем 12 часов на случай если кто-то забыл выключить свет он гарантировано выключится через 12 часов
PREFIX = cfg['mqtt_prefix']
HA_PREFIX = f'homeassistant/{PREFIX}'
ERR_PREFIX = f'{PREFIX}/err'
ONLINE_TOPIC = f'{HA_PREFIX}/online'
OFFLINE = dict(
    topic=ONLINE_TOPIC,
    payload='offline',
)
MQTT_CONF = {
    'hostname': cfg['mqtt_host'],
    'username': cfg['mqtt_user'],
    'password': cfg['mqtt_password'],
    'will': Will(**OFFLINE)
}
RECONNECT_TIME = 10
SWITCH_RESPONSE = f'{PREFIX}/s/{{ch}}'
SWITCH_SUBSCRIPTION = f'{PREFIX}/s/+/set'
RAW_RESPONSE = f'{PREFIX}/r/{{ch}}'
RAW_SUBSCRIPTION = f'{PREFIX}/r/+/cmd'

noolite = noo.Noolite(
    tty_name=cfg['serial_port'],
    loop=loop
)
motions = {}


def parse_msg(msg):
    payload = msg.payload
    ch = int(msg.topic.split('/')[-2])
    data = ujson.loads(payload)
    lg.debug(data)
    if 'brightness' in data:
        yield noo.NooliteCommand.make_command(
            ch=ch,
            br=int(data['brightness']),
            cmd=noo.const.SET_BRIGHTNESS,
        )
        if data['state'] == 'ON':
            yield noo.NooliteCommand.make_command(
                ch=ch,
                duration=DEFAULT_LIGHT_TIMEOUT if data['state'] == 'ON' else None,
                cmd=noo.const.TEMPORARY_ON,
            )
    else:
        yield noo.NooliteCommand.make_command(
            ch=ch,
            duration=DEFAULT_LIGHT_TIMEOUT if data['state'] == 'ON' else None,
            cmd=noo.const.TEMPORARY_ON if data['state'] == 'ON' else noo.const.OFF,
        )


def parse_raw(msg):
    payload = msg.payload
    ch = int(msg.topic.split('/')[-2])
    data = ujson.loads(payload)
    data['ch'] = ch
    cmd = noo.MqttCommand(**data)
    yield noo.NooliteCommand.make_command(**cmd.dict())


def get_lights():
    devices = cfg['lights']
    for value in devices:
        ch = value.pop('ch')
        if value.get('brightness'):
            value['brightness_scale'] = 100
        state_topic = f'{PREFIX}/s/{ch}'
        command_topic = f'{state_topic}/set'
        id = f'{PREFIX}_s_{ch}'
        yield id, dict(
            **value,
            unique_id=id,
            availability_topic=ONLINE_TOPIC,
            command_topic=command_topic,
            state_topic=state_topic,
            schema='json',
        )


def get_motions():
    devices = cfg['motion']
    for value in devices:
        ch = value.pop('ch')
        state_topic = f'{PREFIX}/m/{ch}'
        id = f'{PREFIX}_m_{ch}'
        if 'off_delay' not in value:
            value['off_delay'] = 1
        if 'long' in value:
            value.pop('long')
            lid = f'{id}_l'
            _val = value.copy()
            if 'name' in _val:
                _val['name'] = _val['name'] + ' L'
            yield lid, dict(
                **_val,
                unique_id=lid,
                availability_topic=ONLINE_TOPIC,
                state_topic=f'{state_topic}_l',
            )
        yield id, dict(
            **value,
            unique_id=id,
            availability_topic=ONLINE_TOPIC,
            state_topic=state_topic,
        )


async def announce(client: ac.Client):
    for id, cfg in get_lights():
        lg.debug('announce: %s', cfg)
        await client.publish(
            topic=f'homeassistant/light/{id}/config',
            payload=ujson.dumps(cfg),
        )
    for id, cfg in get_motions():
        lg.debug('announce: %s', cfg)
        await client.publish(
            topic=f'homeassistant/binary_sensor/{id}/config',
            payload=ujson.dumps(cfg),
        )


async def process_noolite(client: ac.Client):
    async for cmd in noolite.in_commands:
        if cmd.cmd in (noo.const.ON, noo.const.SWITCH, noo.const.TEMPORARY_ON):
            await client.publish(
                topic=f'{PREFIX}/m/{cmd.ch}',
                payload='ON',
            )

        elif cmd.cmd == noo.const.OFF:
            await client.publish(
                topic=f'{PREFIX}/m/{cmd.ch}',
                payload='OFF',
            )
        elif cmd.cmd == noo.const.BRIGHT_BACK:
            # долгие нажатия
            await client.publish(
                topic=f'{PREFIX}/m/{cmd.ch}_l',
                payload='ON',
            )

async def process_msgs(
        client: ac.Client,
        parser,
        topic_patt,
        response_template: str
    ):
    """
    :return:
    """
    await client.subscribe(topic_patt)
    async with client.filtered_messages(topic_patt) as messages:
        lg.debug(f'subscribe to {topic_patt}')
        async for msg in messages:
            lg.debug(f'process {msg.topic}: {msg.payload}')
            try:
                for cmd in parser(msg):
                    await noolite.send_command(cmd)
                # сообщаем что все ок
                await client.publish(
                    topic=response_template.format(ch=cmd.ch),
                    payload=msg.payload,
                    retain=True,
                )
            except Exception as exc:
                await client.publish(
                    topic=f'{ERR_PREFIX}/{cmd.ch}',
                    payload=str(exc)
                )
                lg.exception()


async def main():
    while True:
        async with Client(**MQTT_CONF) as client:
            try:
                await announce(client)
                await client.publish(
                    topic=ONLINE_TOPIC,
                    payload='online',
                )
                done, pending = await asyncio.wait([
                    process_msgs(
                        client,
                        topic_patt=SWITCH_SUBSCRIPTION,
                        response_template=SWITCH_RESPONSE,
                        parser=parse_msg
                    ),
                    process_msgs(
                        client,
                        topic_patt=RAW_SUBSCRIPTION,
                        response_template=RAW_RESPONSE,
                        parser=parse_raw
                    ),
                    process_noolite(client),
                ], return_when=FIRST_EXCEPTION)
                for x in done:
                    await x
            except Exception as exc:
                lg.exception('in main loop')
            finally:
                await client.publish(**OFFLINE)
        lg.warning('reconnecting')
        await asyncio.sleep(RECONNECT_TIME)


if __name__ == '__main__':
    loop.run_until_complete(main())
