import os
import logging

import bpy

LOG_FILE_IMPORT = 'pd_import.log'
LOG_FILE_EXPORT = 'pd_export.log'
LOG_FMT = '%(asctime)s [%(name)s] %(message)s'
LOG_DATEFMT = '%H:%M:%S'

def log_get(name): return logging.getLogger(name.split('.')[0])

def log_filename(filename):
    log_dir = os.path.dirname(bpy.data.filepath)
    return f'{log_dir}/{filename}'

def log_clear(filename):
    f = open(log_filename(filename), 'r+')
    f.seek(0)
    f.truncate(0)

def log_config(logger, filename):
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_filename(filename))
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    formatter = logging.Formatter(LOG_FMT, datefmt=LOG_DATEFMT)
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
