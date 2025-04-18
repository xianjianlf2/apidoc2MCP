from loguru import logger
import sys


def init_logger():
    logger.remove()
    logger.add(sys.stdout, level="INFO")


def get_logger():
    return logger
