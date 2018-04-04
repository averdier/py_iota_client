# -*- coding: utf-8 -*-

import logging
from logging.handlers import RotatingFileHandler


levels = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'critical': logging.CRITICAL
}


class FileLogger:
    """
    Custom file logger
    """

    def __init__(self, name, path, level='debug'):
        self._logger = logging.getLogger(name)
        handler_debug = logging.handlers.RotatingFileHandler(path, mode="a", maxBytes=50000, backupCount=1,
                                                             encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s -- %(name)s -- %(levelname)s -- %(message)s")
        handler_debug.setFormatter(formatter)

        self._logger.setLevel(levels.get(level, 'debug'))
        self._logger.addHandler(handler_debug)

    def info(self, message):
        self._logger.info(message)

    def debug(self, message):
        self._logger.debug(message)

    def critical(self, message):
        self._logger.critical(message)

    def error(self, message):
        self._logger.error(message)