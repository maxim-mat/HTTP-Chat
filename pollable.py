## @package HTTP--Chat.pollable I/O objects.
## @file pollable.py Implementation of @ref HTTP--Chat.pollable
#

import base
import constants
import errno
import services
import socket
import urlparse

from events import CommonEvents
from server import Disconnect


## Interface for generic I/O object
#
class Pollable(base.Base):

    ## Constructor.
    def __init__(self):
        super(Pollable, self).__init__()

    ## Logic to run in case of output event.
    def onwrite(self):
        pass

    ## Logic to run in case of input event.
    def onread(self):
        pass

    ## Logic to run in case of error event.
    def onerror(self):
        pass

    ## Retrieve fd for this object.
    # @returns (int) object fd
    #
    def getfd(self):
        pass

    ## Retrieve events poller should care about for this object.
    # @returns (int) relevant events
    #
    def getevents(self):
        pass


class SocketListen(Pollable):

    ## Constructor.
    # @param socket (object) communication socket
    # @param ret_class (type) type to create when accepting new connections
    # @param poller (object) related poller
    # @param context (dict) application context
    #
    def __init__(
        self,
        socket,
        ret_class,
        poller,
        context,
    ):
        super(SocketListen, self).__init__()
        self._socket = socket
        self._ret_class = ret_class
        self._poller = poller
        self._context = context

    ## Retrieve socket.
    @property
    def socket(self):
        return self._socket

    ## Retrieve class this object creates upon accepting connections.
    @property
    def ret_class(self):
        return self._ret_class

    ## Retrieve poller handling this object.
    @property
    def poller(self):
        return self._poller

    ## Retrieve application context.
    @property
    def context(self):
        return self._context

    ## @copydoc Pollable#getfd
    def getfd(self):
        return self.socket.fileno()

    ## @copydoc Pollable#getevents
    def getevents(self):
        return CommonEvents.POLLERR | CommonEvents.POLLIN

    ## @copydoc Pollable#onread
    def onread(self):
        self.logger.debug('Listening')
        try:
            client, addr = self.socket.accept()
            client.setblocking(False)
            self.logger.debug('Connected new client %s', client.fileno())
        except Exception as e:
            self.logger.error('Unexpected error: %s', exc_info=True)
            client.close()
        self.poller.register(self.ret_class(client, self.poller, self.context))

    ## @copydoc Pollable#onerror
    def onerror(self):
        self.poller.unregister(self)
        self.logger.debug('removed and closed passive socket %s', self.getfd())
        self.socket.close()


class HttpSocket(Pollable):

    ## State machine states.
    (FIRST, HEADERS, CONTENT, R_FIRST, R_HEADERS, R_CONTENT, END) = range(7)
    _services = {
        service.NAME: service for service in services.Service.__subclasses__()
    }

    ## Constructor.
    # @param socket (object) communication socket
    # @param poller (object) related poller
    # @param context (dict) application context
    # @param block_size (int) maximum amount to read
    #
    def __init__(
        self,
        socket,
        poller,
        context,
        block_size=constants.BLOCK_SIZE,
    ):
        super(HttpSocket, self).__init__()
        self._socket = socket
        self._poller = poller
        self._block_size = block_size
        self._context = context
        self._buf = ''
        self._state = HttpSocket.FIRST
        self._outgoing = ''
        self._dialogue = {
            'request': {
                'headers': {
                    'Content-Length': 0,
                },
                'name': '',
                'content': '',
                'context': self._context,
            },
            'response': {
                'headers': {

                },
                'content': '',
            },
        }
        self._service = None

    ## Retrieve socket.
    @property
    def socket(self):
        return self._socket

    ## Retrieve block size.
    @property
    def block_size(self):
        return self._block_size

    ## Set block size.
    @block_size.setter
    def block_size(self, val):
        self._block_size = val

    ## Retrieve context.
    @property
    def context(self):
        return self._context

    ## Retrieve reading buffer.
    @property
    def buf(self):
        return self._buf

    ## Set value of reading buffer.
    @buf.setter
    def buf(self, val):
        self._buf = val

    ## Retrieve state.
    @property
    def state(self):
        return self._state

    ## Set state.
    @state.setter
    def state(self, val):
        self._state = val

    ## Retrieve service.
    @property
    def service(self):
        return self._service

    ## Set service.
    @service.setter
    def service(self, val):
        self._service = val

    ## Retrieve dialogue data structure. Wider application context.
    @property
    def dialogue(self):
        return self._dialogue

    ## Retrieve sending buffer.
    @property
    def outgoing(self):
        return self._outgoing

    ## Set sending buffer.
    @outgoing.setter
    def outgoing(self, val):
        self._outgoing = val

    ## Retrieve related poller.
    @property
    def poller(self):
        return self._poller

    ## Equality operator.
    # @arg other (object) other object.
    # @returns (bool) True if equal.
    #
    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self.getfd() == other.getfd()

    ## @copydoc Pollable#getfd
    def getfd(self):
        return self.socket.fileno()

    ## @copydoc Pollable#getevents
    def getevents(self):
        e = CommonEvents.POLLERR
        if len(self.buf) < self.block_size:
            e |= CommonEvents.POLLIN
        if self.outgoing:
            e |= CommonEvents.POLLOUT
        return e

    ## @copydoc Pollable#onwrite
    def onwrite(self):
        try:
            while self._outgoing:
                self.logger.debug('SENDING: %s', self.outgoing)
                self.outgoing = self.outgoing[self.socket.send(self.outgoing):]
            self._parse()
        except socket.error as e:
            if e.errno != errno.EWOULDBLOCK:
                raise

    ## @copydoc Pollable#onread
    def onread(self):
        try:
            temp = self.socket.recv(self.block_size)
            self.logger.debug('received %s', temp)
            if not temp:
                raise Disconnect()
            self.buf += temp
            self._parse()
        except socket.error as e:
            if e.errno != errno.EWOULDBLOCK:
                raise

    ## @copydoc Pollable#onerror
    def onerror(self):
        self._terminate()

    ## Parse header
    # @param line (str) header line to parse
    # @returns (tuple) first is header title second is header data
    # @throws RuntimeError If header violates HTTP protocol
    #
    def _parse_header(self, line):
        SEP = ':'
        n = line.find(SEP)
        if n == -1:
            raise RuntimeError('Invalid Header')
        return line[:n].rstrip(), line[n + len(SEP):].lstrip()

    ## Parse and carefully examine first line of HTTP request.
    # @param req (str) HTTP request first line
    # @throws RuntimeError If HTTP protocol is incomplete
    # @throws RuntimeError If protocol is not HTTP
    # @throws RuntimeError If URI is invalid
    #
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
        self.dialogue['request']['uri'] = parsed.path
        self.dialogue['request']['params'] = urlparse.parse_qs(parsed.query)
        self.service = self._services[parsed.path]()
        self.logger.debug('validated protocol')

    ## State machine logic handling and responding to HTTP requests.
    # @throws RuntimeError If a header is too long
    # @throws RuntimeError If request has too many headers
    #
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
                if len(line) > constants.MAX_HEADER_LEN:
                    raise RuntimeError("Header too long")
                title, data = self._parse_header(line)
                if len(
                    self.dialogue['request']['headers'].keys()
                ) > constants.MAX_HEADER_AMOUNT:
                    raise RuntimeError("Too many headers")
                if title in self.dialogue['request']['headers']:
                    if title == 'Content-Length':
                        data = int(data)
                    self.dialogue['request']['headers'][title] = data
                self.buf = self.buf[n + len(constants.CRLF_BIN):]
        if self.state == HttpSocket.CONTENT:
            if self.dialogue['request']['headers']['Content-Length'] > 0:
                self.dialogue['request']['content'] += self.buf
                self.logger.debug(
                    'put content in context: %s',
                    self.buf,
                )
                self.logger.debug(
                    'actual content is: %s',
                    self.dialogue['request']['content'],
                )
                self.logger.debug(
                    'length before: %s',
                    self.dialogue['request']['headers']['Content-Length'],
                )
                self.dialogue[
                    'request']['headers']['Content-Length'] -= len(self.buf)
                self.logger.debug(
                    'length after: %s',
                    self.dialogue['request']['headers']['Content-Length'],
                )
                self.buf = ''
                self.service.on_content(self.dialogue)
            if self.dialogue['request']['headers']['Content-Length'] <= 0:
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
            if len(
                self.dialogue['response']['content']
            ) == 0 and not self.outgoing:
                self.state = HttpSocket.END
                self.logger.debug('CHANGED STATE TO: %s', self.state)
        if self.state == HttpSocket.END:
                self.service.on_end(self.dialogue)
                self._terminate()

    ## String formatting for response first line.
    #
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

    ## String formatting for response headers.
    #
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

    ## Formatting for response content.
    #
    def _format_content(self):
        self.outgoing += self.dialogue['response']['content']

    ## End of communication. Close and remove communication socket.
    def _terminate(self):
        self.poller.unregister(self)
        self.logger.debug(
            'ended communication and closed socket %s',
            self.getfd(),
        )
        self.socket.close()
