#!usr/bin/python

import argparse
import base
import constants
import errno
import events
import logging
import pollable
import select
import signal
import socket


class Disconnect(RuntimeError):
    """Exception for handling disconnects."""

    def __init__(self):
        super(Disconnect, self).__init__('Disconnect')


class Server(base.Base):
    """HTTP server object."""

    _pollable = []  # list of pollable objects
    _close_server = False

    def __init__(
        self,
        timeout,
        poll_type=events.SelectEvents,
    ):
        super(Server, self).__init__()
        self._timeout = timeout
        self._poll_type = poll_type

    @property
    def timeout(self):
        return self._timeout

    @property
    def poll_type(self):
        return self._poll_type

    def add_passive(
        self,
        bind_address,
        bind_port,
    ):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((bind_address, bind_port))
        s.listen(10)
        s.setblocking(False)
        self._pollable.append()
        self.logger.debug(
            'Created new listener socket %s:%s',
            bind_address,
            bind_port,
        )

    def register(self, object):
        self._pollable.append(object)

    def unregister(self, object):
        self._pollable.remove(object)

    def _create_poller(self):
        poller = self.poll_type()
        for s in self._pollable:
            poller.register(s.getfd(), s.getevents())
            self.logger.debug(
                'socket %s was registered with events: %s',
                s.getfd(),
                s.getevents(),
            )
        return poller

    def _get_socket(self, fd):
        for s in self._pollable:
            if s.getfd() == fd:
                return s

    def _close_socket(self, s):
        self.logger.debug('POLLABLE: %s', self._pollable)
        self.logger.debug('closed socket: %s', s.getfd())
        self._pollable.remove(s)
        s.socket.close()
        self.logger.debug('POLLABLE: %s', self._pollable)

    def run(self):
        while self._pollable:
            self.logger.debug('pollable list: %s', self._pollable)
            try:
                # if self._close_server:
                    # self._terminate()
                # for s in self._sockets:
                    # if s.state == Http_socket.CLOSING:
                        # self._remove_socket(s)
                try:
                    self.logger.debug('start polling')
                    for fd, e in self._create_poller().poll(self.timeout):
                        self.logger.debug(
                            'socket fd: %s, event: %s',
                            fd,
                            e,
                        )
                        socket = self._get_socket(fd)
                        self.logger.debug('%s is %s', fd, socket)
                        try:
                            if (
                                e &
                                (events.CommonEvents.POLLHUP | events.CommonEvents.POLLERR)
                            ):
                                raise RuntimeError('Connection Broken')
                            if e & events.CommonEvents.POLLIN:
                                socket.onread()
                            if e & events.CommonEvents.POLLOUT:
                                socket.onwrite()
                        except Disconnect:
                            self.logger.debug('Socket fd: %d has disconnected', fd)
                            socket.onerror()
                        except Exception as ex:
                            self.logger.debug(
                                'Socket fd: %s had unexpected exception:',
                                fd,
                                exc_info=True,
                            )
                            socket.onerror()
                except select.error as ex:
                    if ex[0] != errno.EINTR:
                        raise
            except Exception as ex:
                self.logger.debug(
                    'Unexpected error: %s',
                    exc_info=True,
                )
                # self._terminate()


def parse_args():
    """Parse program arguments."""

    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }

    EVENT_TYPES = {
        event.NAME: event for event in events.CommonEvents.__subclasses__()
    }

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--log-level',
        dest='log_level_str',
        default='INFO',
        choices=LOG_LEVELS.keys(),
        help='set log level. default: %(default)s',
    )
    parser.add_argument(
        '--log-file',
        default=None,
        help='log file to write to. default: standard output',
    )
    parser.add_argument(
        '--new',
        action='append',
        required=True,
        help='''server to create. format is:
             [bind_address]:bind_port
             ''',
    )
    parser.add_argument(
        '--timeout',
        default=constants.TIMEOUT_DEFAULT,
        type=int,
        help='amount for poll to timeout. default: %(default)s',
    )
    parser.add_argument(
        '--block-size',
        default=constants.BLOCK_SIZE,
        type=int,
        help='maximum block size for buffers. default: %(default)s',
    )
    parser.add_argument(
        '--poll-type',
        choices=EVENT_TYPES.keys(),
        default=sorted(EVENT_TYPES.keys())[0],
        help='''event type for async.
            default: %(default)s, choices: %(choices)s
            ''',
    )
    args = parser.parse_args()
    args.log_level = LOG_LEVELS[args.log_level_str]
    return args


def main():
    """Main implementation."""

    args = parse_args()

    if args.log_file is not None:
        log = open(args.log_file, 'a')
    else:
        log = None
    logger = base.setup_logging(
        stream=log,
        level=args.log_level,
    )

    try:
        logger.info('Startup')
        logger.debug('Args: %s', args)
        server = Server(args.timeout)

        def exit_handler(signal, frame):
            server.close_server()

        signal.signal(signal.SIGINT, exit_handler)
        signal.signal(signal.SIGTERM, exit_handler)

        response_context = {}
        request_context = {
            'users':{
                
            },
            'rooms':{
                'room':[],
            },
        }

        for a in args.new:
            bind_addr, bind_port = a.split(':')
            bind_port = int(bind_port)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((bind_addr, bind_port))
            s.listen(10)
            s.setblocking(False)
            server.register(pollable.SocketListen(s, pollable.HttpSocket, server, request_context))
            server.logger.debug(
                'Created new listener socket %s:%s',
                bind_addr,
                bind_port,
            )

        server.run()

    except Exception as e:
        logger.debug('Exception', exc_info=True)

    finally:
        for h in logger.handlers:
            h.close()
            logger.removeHandler(h)


if __name__ == '__main__':
    main()
