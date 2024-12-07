import os
import logging

import bpy

import pd_utils as pdu

LOG_FILE_IMPORT = 'pd_import.log'
LOG_FILE_EXPORT = 'pd_export.log'
LOG_FMT = '%(asctime)s [%(name)s] %(message)s'
LOG_DATEFMT = '%H:%M:%S'

def log_get(name): return logging.getLogger(name.split('.')[0])

def log_filename(filename):
    # log_dir = os.path.dirname(bpy.data.filepath)

    # when we save the log in the addon folder, Blender will lock the file and we
    # aren't able to uninstall the addon, so we save in the root of the addons dir
    user_path = bpy.utils.resource_path('USER') # TODO find a proper way to store the log
    log_dir = os.path.join(user_path, 'scripts', 'addons')
    return f'{log_dir}/{filename}'

def log_clear(filename):
    f = open(log_filename(filename), 'r+')
    f.seek(0)
    f.truncate(0)
    f.close()

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
