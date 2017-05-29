## @package HTTP--Chat.events Events module.
## @file events.py Implementation of @ref HTTP--Chat.events
#

import base
import os
import select


## Wrapper to implement equal behaviour on *NIX and Windows
#
class CommonEvents(base.Base):

    ## Event constants as defined by *NIX poll
    (POLLIN, POLLOUT, POLLERR, POLLHUP) = (
        1, 4, 8, 16) if os.name == "nt" else (
        select.POLLIN, select.POLLOUT, select.POLLERR, select.POLLHUP
    )

    ## Readable class name.
    NAME = 'Common'

    ## Constructor
    def __init__(self):
        pass

    ## Add I/O object to poller.
    # @param fd (int) I/O object
    # @param event (int) events to look for
    #
    def register(self, fd, event):
        pass

    ## Begin pollong process.
    # @param timeout (float) max time window for single poll
    # @returns (list) pairs of fd and events
    #
    def poll(self, timeout):
        pass


if os.name != 'nt':
    ## Poll logic for *NIX platforms.
    #
    class PollEvents(CommonEvents):

        ## Readable class name.
        NAME = 'Poll'

        ## Constructor.
        def __init__(self):
            super(PollEvents, self).__init__()
            self._poller = select.poll()

        ## @copydoc CommonEvents#register
        def register(self, fd, event):
            self._poller.register(fd, event)

        ## @copydoc CommonEvents#poll
        def poll(self, timeout):
            return self._poller.poll(timeout)


## Mimicing poll behaviour using select on Windows platforms.
#
class SelectEvents(CommonEvents):

    ## Readable class name.
    NAME = 'Select'

    ## Constructor.
    def __init__(self):
        super(SelectEvents, self).__init__()
        self._file_descriptors = {}

    ## @copydoc CommonEvents#register
    def register(self, fd, event):
        self._file_descriptors[fd] = event

    ## @copydoc CommonEvents#poll
    def poll(self, timeout):
        rlist, wlist, xlist = [], [], []

        for fd in self._file_descriptors:
            event = self._file_descriptors[fd]
            if event & SelectEvents.POLLIN:
                rlist.append(fd)
            if event & SelectEvents.POLLOUT:
                wlist.append(fd)
            if event & SelectEvents.POLLERR:
                xlist.append(fd)

        r, w, x = select.select(rlist, wlist, xlist, timeout)

        polled = {}
        for fd in r + w + x:
            if fd in r:
                polled[fd] = SelectEvents.POLLIN
            if fd in w:
                polled[fd] = SelectEvents.POLLOUT
            if fd in x:
                polled[fd] = SelectEvents.POLLERR
        return polled.items()
