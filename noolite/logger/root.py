from logging import getLogger, StreamHandler, Formatter, INFO
import os
root_logger = getLogger('smarthome')
root_logger.setLevel(INFO)

if os.environ.get('DEVELOP', 'Y') == 'Y':
    h = StreamHandler()
    h.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(h)
