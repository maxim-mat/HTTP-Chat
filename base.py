# -*- coding: utf-8 -*-

import logging
import sys


class Base(object):
    """Base of all objects"""

    LOG_PREFIX = 'my'

    @property
    def logger(self):
        """Logger."""
        return self._logger

    def __init__(self):
        """Contructor."""
        self._logger = logging.getLogger(
            '%s.%s' % (
                self.LOG_PREFIX,
                self.__module__,
            ),
        )

    def __eq__(self, other):
        """Equality operator.

        Python-2/python-3 bridge, python-2 has no __eq__ in object.

        Args:
            other (object): oter object.

        Returns:
            bool: True if equals.
        """
        if type(self) is not type(other):
            return NotImplemented

        sup = super(Base, self)
        if hasattr(sup, '__eq__'):  # python-3
            return sup.__eq__(other)
        else:
            return True


def setup_logging(stream=None, level=logging.INFO):
    logger = logging.getLogger(Base.LOG_PREFIX)
    logger.propagate = False
    logger.setLevel(level)

    try:
        if stream is not None:
            h = logging.StreamHandler(stream)
        else:
            h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.DEBUG)
        h.setFormatter(
            logging.Formatter(
                fmt=(
                    '%(asctime)-15s '
                    '[%(levelname)-7s] '
                    '%(name)s::%(funcName)s:%(lineno)d '
                    '%(message)s'
                ),
            ),
        )
        logger.addHandler(h)
    except IOError:
        logging.warning('Cannot initialize logging', exc_info=True)

    return logger
