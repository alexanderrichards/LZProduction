"""Logging utilities."""
import logging


def all_loggers(root=True, placeholders=False):
    """"""
    logger_manager = logging.Logger.manager
    if root:
        yield 'root', logger_manager.root
    for name, logger in logger_manager.loggerDict.iteritems():
        if placeholders or isinstance(logger, logging.Logger):
            yield name, logger


def loggers_at_level(level, root=False):
    """
    Yield all logger at a particular level.

    Generator yielding each logger (excluding the root logger)
    that has a level set to level.

    Args:
        level (int): The logging level to search for

    Returns:
        tuple: Yields a tuple containing (name, logger)
    """
    for name, logger in all_loggers(root):
        if logger.level == level:
            yield name, logger


def loggers_not_at_level(level, root=False):
    """"""
    for name, logger in all_loggers(root):
        if logger.level != level:
            yield name, logger

def loggers_with_handlers(root=False):
    """"""
    for name, logger in all_loggers(root):
        if logger.handlers:
            yield name, logger

def loggers_without_handlers(root=False):
    """"""
    for name, logger in all_loggers(root):
        if not logger.handlers:
            yield name, logger
