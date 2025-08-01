import os
import logging

import bpy

from utils import pd_utils as pdu
from pd_blendtools import pd_addonprefs as pda

LOG_FILE_IMPORT = 'pd_import.log'
LOG_FILE_EXPORT = 'pd_export.log'
LOG_FMT = '%(asctime)s [%(name)s] %(message)s'
LOG_DATEFMT = '%H:%M:%S'

def log_get(name): return logging.getLogger(name.split('.')[0])

def log_filename(filename):
    env = os.environ
    log_dir = env['TEMP'] if 'TEMP' in env else env['TMPDIR']

    if not log_dir:
        print('Error: unable to find temp directory, log files will not be created.')
        return ''

    log_dir += '/pd_blendtools_logs'
    if os.path.isdir(log_dir):
        return f'{log_dir}/{filename}'

    # log dir doesn't exist, try to create
    try:
        os.mkdir(log_dir)
    except Exception as err:
        print(f'Error occurred while creating log dir {log_dir}: {err}')
        return ''

    return f'{log_dir}/{filename}'

def log_clear(filename):
    f = open(log_filename(filename), 'r+')
    f.seek(0)
    f.truncate(0)
    f.close()

def log_get_level():
    lvmap = {
        'info': logging.INFO,
        'debug': logging.DEBUG,
        'error': logging.ERROR,
    }

    lv = pda.log_level()
    return lvmap.get(lv, logging.ERROR)

def log_config(logger, filename):
    level = log_get_level()
    logger.handlers.clear()
    logger.setLevel(level)

    file_h = None
    logfile = log_filename(filename)
    file_h = logging.FileHandler(logfile) if logfile else None
    stream_h = logging.StreamHandler()

    formatter = logging.Formatter(LOG_FMT, datefmt=LOG_DATEFMT)
    stream_h.setFormatter(formatter)
    logger.addHandler(stream_h)

    if file_h:
        file_h.setFormatter(formatter)
        logger.addHandler(file_h)

