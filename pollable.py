import base
import constants
import errno
from events import CommonEvents
import services
import socket
import urlparse


class Pollable(object):

    def __init__(self):
        pass

    def onread(self):
        pass

    def onwrite(self):
        pass

    def onerror(self):
        pass

    def getfd(self):
        pass

    def getevents(self):
        pass


class SocketListen(base.Base, Pollable):

    def __init__(
        self,
        socket,
        ret_class,
        poller,
    ):
        super(SocketListen, self).__init__()
        self._socket = socket
        self._ret_class = ret_class
        self._poller = poller

    @property
    def socket(self):
        return self._socket

    @property
    def ret_class(self):
        return self._ret_class

    @property
    def poller(self):
        return self._poller

    def getfd(self):
        return self.socket.fileno()

    def getevents(self):
        return CommonEvents.POLLERR | CommonEvents.POLLIN

    def onread(self):
        self.logger.debug('Listening')
        try:
            client, addr = self.socket.accept()
            client.setblocking(False)
            self.logger.debug('Connected new client %s', client.fileno())
        except Exception as e:
            self.logger.error('Unexpected error: %s', exc_info=True)
            client.close()
        self.poller.register(self.ret_class(client, self.poller))

    def onerror(self):
        self.poller.unregister(self)
        self.logger.debug('removed and closed passive socket %s', self.getfd())
        self.socket.close()


class HttpSocket(base.Base, Pollable):

    FIRST, HEADERS, CONTENT, R_FIRST, R_HEADERS, R_CONTENT, END = range(7)
    _services = {
        service.NAME: service for service in services.Service.__subclasses__()
    }
    _lookup = ['Content-Type', ]

    def __init__(
        self,
        socket,
        poller,
        block_size=constants.BLOCK_SIZE,
    ):
        super(HttpSocket, self).__init__()
        self._socket = socket
        self._poller = poller
        self._block_size = block_size
        self._buf = ''
        self._state = HttpSocket.FIRST
        self._outgoing = ''
        self._dialogue = {
            'request': {
                'headers': {
                    'Content-Length':0,
                },
                'content': '',
            },
            'response': {
                'headers': {
                    
                },
                'signature': constants.HTTP_SIGNATURE,
                'state': False,
            },
        }
        self._service = None

    @property
    def socket(self):
        return self._socket

    @property
    def block_size(self):
        return self._block_size

    @block_size.setter
    def block_size(self, val):
        self._block_size = val

    @property
    def buf(self):
        return self._buf

    @buf.setter
    def buf(self, val):
        self._buf = val

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val):
        self._state = val

    @property
    def service(self):
        return self._service

    @service.setter
    def service(self, val):
        self._service = val

    @property
    def dialogue(self):
        return self._dialogue

    @property
    def outgoing(self):
        return self._outgoing

    @outgoing.setter
    def outgoing(self, val):
        self._outgoing = val

    @property
    def poller(self):
        return self._poller

    def getfd(self):
        return self.socket.fileno()

    def getevents(self):
        e = CommonEvents.POLLERR
        if len(self.buf) < self.block_size:
            e |= CommonEvents.POLLIN
        if self.outgoing:
            e |= CommonEvents.POLLOUT
        return e

    def onwrite(self):
        try:
            while self._outgoing:
                self.outgoing = self.outgoing[self.socket.send(self.outgoing):]
            self._parse()
        except socket.error as e:
            if e.errno != errno.EWOULDBLOCK:
                raise

    def onread(self):
        try:
            if len(self.buf) > constants.MAX_HEADER_LEN:
                raise RuntimeError('Exceeded maximum header length %s' % constants.MAX_HEADER_LEN)
            temp = self.socket.recv(self.block_size)
            self.logger.debug('received %s', temp)
            if self.buf and not temp:
                raise Disconnect()
            self.buf += temp
            self._parse()
        except socket.error as e:
            if e.errno != errno.EWOULDBLOCK:
                raise

    def onerror(self):
        self.poller.unregister(self)
        self.logger.debug('removed and closed active socket %s', self.getfd())
        self.socket.close()

    def _parse_header(self, line):
        SEP = ':'
        n = line.find(SEP)
        if n == -1:
            raise RuntimeError('Invalid Header')
        return line[:n].rstrip(), line[n + len(SEP):].lstrip()

    def _validate(self, req):
        req_comps = req.split(' ', 2)
        if len(req_comps) != 3:
            raise RuntimeError('Incomplete HTTP protocol')
        method, uri, signature = req_comps
        if signature != constants.HTTP_SIGNATURE:
            raise RuntimeError('Not HTTP protocol')
        parsed = urlparse.urlparse(uri)
        if parsed.path not in self._services.keys():
            raise RuntimeError(
                "Invalid uri: %s",
                uri,
            )
        self.dialogue['request']['method'] = method
        self.dialogue['request']['uri'] = uri
        self.service = self._services[parsed.path]()
        self.logger.debug('validated protocol')

    def _parse(self):
        if self.state == HttpSocket.FIRST:
            n = self.buf.find(constants.CRLF_BIN)
            if n != -1:
                line = self.buf[:n].decode('utf-8')
                self.buf = self.buf[n + len(constants.CRLF_BIN):]
                self._validate(line)
                self.service.on_first_line(self.dialogue)
                self.state = HttpSocket.HEADERS
                self.logger.debug('CHANGED STATE TO: %s', self.state)
        if self.state == HttpSocket.HEADERS:
            self.service.on_headers(self.dialogue)
            while self.buf:
                n = self.buf.find(constants.CRLF_BIN)
                if n == -1:
                    break
                if n == 0:
                    self.state = HttpSocket.CONTENT
                    self.logger.debug('CHANGED STATE TO: %s', self.state)
                    self.buf = self.buf[n + len(constants.CRLF_BIN):]
                    break
                line = self.buf[:n].decode('utf-8')
                title, data = self._parse_header(line)
                if title in self.dialogue['request']['headers']:
                    self.dialogue['request']['headers'][title] = data
                self.buf = self.buf[n + len(constants.CRLF_BIN):]
        if self.state == HttpSocket.CONTENT:
            if self.dialogue['request']['headers']['Content-Length'] > 0:
                self.dialogue['request']['content'] += self.buf
                self.buf = ''
                self.service.on_content(self.dialogue)
            else:
                self.state = HttpSocket.R_FIRST
                self.logger.debug('CHANGED STATE TO: %s', self.state)
        if self.state == HttpSocket.R_FIRST:
            self.service.response_first_line(self.dialogue)
            self._format_first_line()
            self.state = HttpSocket.R_HEADERS
            self.logger.debug('CHANGED STATE TO: %s', self.state)
        if self.state == HttpSocket.R_HEADERS:
            self.service.response_headers(self.dialogue)
            self._format_headers()
            self.state = HttpSocket.R_CONTENT
            self.logger.debug('CHANGED STATE TO: %s', self.state)
        if self.state == HttpSocket.R_CONTENT:
            self.service.response_content(self.dialogue)
            self._format_content()
            if len(self.dialogue['response']['content']) == 0:
                self.state = HttpSocket.END
                self.logger.debug('CHANGED STATE TO: %s', self.state)
        if self.state == HttpSocket.END:
                self.service.on_end(self.dialogue)
                self.poller.unregister(self)
                self.logger.debug('ended communication and closed socket %s', self.getfd())
                self.socket.close()

    def _format_first_line(self):
        self.outgoing += (
            (
                '%s %s %s\r\n'
            ) % (
                constants.HTTP_SIGNATURE,
                self.dialogue['response']['code'],
                self.dialogue['response']['message'],
            )
        ).encode('utf-8')

    def _format_headers(self):
        for header, info in self.dialogue['response']['headers'].items():
            self.outgoing += (
                (
                    '%s: %s\r\n'
                ) % (
                    header,
                    info,
                )
            ).encode('utf-8')
        self.outgoing += '\r\n'.encode('utf-8')

    def _format_content(self):
        self.outgoing += self.dialogue['response']['content']

    # def _handle_buffer(self):
        # while self.buf:
            # if self.state == HttpSocket.R_FIRST:
                # self.service.response_first_line(self.dialogue)
                # self.state = HttpSocket.R_HEADERS
                # break
            # if self.state == HttpSocket.R_HEADERS:
                # self.service.response_headers(self.dialogue)
                # self.state = HttpSocket.R_CONTENT
                # self.outgoing = (
                    # (
                        # '%s %s %s\r\n'
                        # '%s: %s\r\n'
                        # '%s: %s\r\n'
                        # '\r\n'
                    # ) % (
                        # constants.HTTP_SIGNATURE
                        # self.dialogue['response']['code'],
                        # self.dialogue['response']['message'],
                        # 'Content-Length',
                        # self.dialogue['response']['headers']['Content-Length'],
                        # 'Content-Type',
                        # self.dialogue['response']['headers']['Content-Type']
                    # )
                # ).encode('utf-8')
                # self.state = HttpSocket.R_CONTENT
            # if self.state == HttpSocket.R_CONTENT:
                # self.service.response_content(self.dialogue)
                # self.outgoing = self.dialogue['response']['content']
            # if self.state == HttpSocket.CONTENT:
                # self.dialogue['request']['content'] += self.buf
                # self.buf = ''
                # self.service.on_content(self.dialogue)
                # if self.dialogue['request']['headers']['Content-Length'] == 0:
                    # self.state = HttpSocket.R_FIRST
                    # break
            # n = self.buf.find(constants.CRLF_BIN)
            # if n == -1:
                # break
            # if n == 0:
                # self.logger.debug('now content')
                # self.buf = self.buf[n + len(constants.CRLF_BIN):]
                # self.state = HttpSocket.CONTENT
                # break
            # line = self.buf[:n].decode('utf-8')
            # if self.state == HttpSocket.FIRST:
                # self._validate(line)
            # elif self.state == HttpSocket.HEADERS:
                # title, data = self._parse_header(line)
                # if title in self.dialogue['request']['headers']:
                    # self.dialogue['request']['headers'][title] = data
            # self.buf = self.buf[n + len(constants.CRLF_BIN):]
