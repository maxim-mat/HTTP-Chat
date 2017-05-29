## @package HTTP--Chat.base Base module.
## @file base.py Implementation of @ref HTTP--Chat.base
#

import logging
import sys


## Base of all objects.
#
class Base(object):

    ## Log prefix to use.
    LOG_PREFIX = 'my'

    ## Logger.
    @property
    def logger(self):
        """Logger."""
        return self._logger

    ## Constructor.
    def __init__(self):
        """Contructor."""
        self._logger = logging.getLogger(
            '%s.%s' % (
                self.LOG_PREFIX,
                self.__module__,
            ),
        )

    ## Equality operator.
    # @arg other (object) other object.
    # @returns (bool) True if equal.
    #
    def __eq__(self, other):

        if type(self) is not type(other):
            return NotImplemented

        sup = super(Base, self)
        # python-3
        if hasattr(sup, '__eq__'):
            return sup.__eq__(other)
        else:
            return True


## Setup logging system.
# @returns (logger) program logger.
#
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
