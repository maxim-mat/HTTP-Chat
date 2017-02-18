import base
import os
import select


class CommonEvents(base.Base):
    """Common object to unify poll and select."""

    POLLIN, POLLOUT, POLLERR, POLLHUP = (
        1, 4, 8, 16) if os.name == "nt" else (
        select.POLLIN, select.POLLOUT, select.POLLERR, select.POLLHUP
    )

    NAME = 'Common'

    def __init__(self):
        pass

    def register(self, fd, event):
        pass

    def poll(self, timeout):
        pass


if os.name != 'nt':
    class PollEvents(CommonEvents):
        """Object for poll (does nothing special)."""

        NAME = 'Poll'

        def __init__(self):
            super(PollEvents, self).__init__()
            self._poller = select.poll()

        def register(self, fd, event):
            self._poller.register(fd, event)

        def poll(self, timeout):
            return self._poller.poll(timeout)


class SelectEvents(CommonEvents):
    """Object makes select behave like poll."""

    NAME = 'Select'

    def __init__(self):
        super(SelectEvents, self).__init__()
        self._file_descriptors = {}

    def register(self, fd, event):
        self._file_descriptors[fd] = event

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
