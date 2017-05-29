## @package HTTP--Chat.services Services module.
## @file services.py Implementation of @ref HTTP--Chat.services
#

import Cookie
import base
import constants
import os
import time
import urlparse
import util
import xml.etree.ElementTree as et


## Interface for generic service object.
#
class Service(base.Base):

    ## Service name, request URI.
    NAME = 'Base'

    ## Constructor.
    def __init__(self):
        super(Service, self).__init__()

    ## Method to call on request first line state.
    # @param dialogue (dict) application context
    #
    def on_first_line(self, dialogue):
        pass

    ## Method to call on request headers state.
    # @param dialogue (dict) application context
    #
    def on_headers(self, dialogue):
        pass

    ## Method to call on request content state.
    # @param dialogue (dict) application context
    #
    def on_content(self, dialogue):
        pass

    ## Method to call on response first line state.
    # @param dialogue (dict) application context
    #
    def response_first_line(self, dialogue):
        pass

    ## Method to call on response headers state.
    # @param dialogue (dict) application context
    #
    def response_headers(self, dialogue):
        pass

    ## Method to call on response content state.
    # @param dialogue (dict) application context
    #
    def response_content(self, dialogue):
        pass

    ## Method to call on end of communication state.
    # @param dialogue (dict) application context
    #
    def on_end(self, dialogue):
        pass


## File service sending application icon.
#
class Favicon(Service):

    ## Service name, request URI.
    NAME = '/favicon.ico'

    ## Constructor.
    def __init__(
        self,
    ):
        super(Favicon, self).__init__()
        self._resource = None
        self._content = ''

    ## Retrieve fd of file to send.
    @property
    def resource(self):
        return self._resource

    ## Set the fd of file to send.
    @resource.setter
    def resource(self, val):
        self._resource = val

    ## @copydoc Service#response_first_line
    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        self.resource = open('chat.ico', 'rb')

    ## @copydoc Service#response_headers
    def response_headers(self, dialogue):
        dialogue['response']['headers']['Content-Length'] = os.fstat(
            self.resource.fileno()).st_size
        dialogue['response']['headers']['Content-Type'] = 'image/jpeg'

    ## @copydoc Service#response_content
    def response_content(self, dialogue):
        dialogue['response']['content'] = self.resource.read(
            constants.BLOCK_SIZE)

    ## @copydoc Service#on_end
    def on_end(self, dialogue):
        self.resource.close()


## File service sending chat room html
#
class Chat(Service):

    ## Service name, request URI.
    NAME = '/chat'

    ## Constructor.
    def __init__(
        self,
    ):
        super(Chat, self).__init__()
        self._resource = None
        self._content = ''

    ## Retrieve fd of file to send.
    @property
    def resource(self):
        return self._resource

    ## Set fd of file to send.
    @resource.setter
    def resource(self, val):
        self._resource = val

    ## @copydoc Service#on_headers
    def on_headers(self, dialogue):
        dialogue['request']['headers']['Cookie'] = ''

    ## @copydoc Service#response_first_line
    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        self.resource = open('chat.html', 'rb')
        c = Cookie.SimpleCookie()
        c.load(str(dialogue['request']['headers']['Cookie']))
        room = dialogue['request']['params']['room'][0]
        username = dialogue['request']['context']['users'][c['uid'].value]
        dialogue['request']['context']['rooms'][room]['users'][username] = time.time()
        self.logger.debug(
            "USERS %s", dialogue['request']['context']['rooms'][room]['users'])

    ## @copydoc Service#response_headers
    def response_headers(self, dialogue):
        dialogue['response']['headers']['Content-Length'] = os.fstat(
            self.resource.fileno()).st_size
        dialogue['response']['headers']['Content-Type'] = 'text/html'

    ## @copydoc Service#response_content
    def response_content(self, dialogue):
        dialogue['response']['content'] = self.resource.read(
            constants.BLOCK_SIZE)

    ## @copydoc Service#on_end
    def on_end(self, dialogue):
        self.resource.close()


## Service handling chat messages.
#
class GetMessages(Service):

    ## Service name, request URI.
    NAME = '/get-messages'

    ## Constructor.
    def __init__(
        self,
    ):
        super(GetMessages, self).__init__()
        self._content = ''

    ## Retrieve response content to send.
    @property
    def content(self):
        return self._content

    ## Set response content to send.
    @content.setter
    def content(self, val):
        self._content = val

    ## @copydoc Service#on_headers
    def on_headers(self, dialogue):
        dialogue['request']['headers']['Cookie'] = ''

    ## @copydoc Service#response_first_line
    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        c = Cookie.SimpleCookie()
        c.load(str(dialogue['request']['headers']['Cookie']))
        root = et.fromstring(dialogue['request']['content'])
        messages = root.findall('messages')
        room = root.findall('room')[0].attrib['name']
        appendee = []
        for message in messages[0].findall('message'):
            appendee.append('%s: %s' % (
                dialogue['request']['context']['users'][c['uid'].value], message.attrib['text']))
        if len(appendee) > 0:
            dialogue['request']['context']['rooms'][room]['messages'].append(
                appendee)
        dialogue['request']['context']['rooms'][room]['users'][dialogue['request']
                                                               ['context']['users'][c['uid'].value]] = time.time()
        if len(dialogue['request']['context']['rooms'][room]['messages']) > constants.TOO_BIG:
            dialogue['request']['context']['rooms'][room]['messages'] = dialogue['request']['context']['rooms'][room]['messages'][2:]
            dialogue['request']['context']['rooms'][room]['base_index'] = 2

    ## @copydoc Service#response_headers
    def response_headers(self, dialogue):
        c = Cookie.SimpleCookie()
        c.load(str(dialogue['request']['headers']['Cookie']))
        root = et.fromstring(dialogue['request']['content'])
        room = root.findall('room')[0].attrib['name']
        messages = util.get_revision(dialogue['request']['context']['rooms'][room], int(
            root.findall('fetch')[0].attrib['id']))
        root = et.Element('root')
        messages_node = et.SubElement(root, 'messages')
        for entry in messages:
            et.SubElement(messages_node, 'message').attrib['text'] = entry
        if messages:
            et.SubElement(root, 'id').attrib['revision'] = '%s' % (
                len(dialogue['request']['context']['rooms'][room]['messages']))
        users_node = et.SubElement(root, 'users')
        util.clear_outdated_users(
            dialogue['request']['context']['rooms'][room]['users'])
        for name in dialogue['request']['context']['rooms'][room]['users'].keys():
            et.SubElement(users_node, 'user').attrib['name'] = name
        self.logger.debug('HERE BE THE MESSAGES: %s', et.tostring(root))
        self.content = et.tostring(root)
        dialogue['response']['headers']['Content-Length'] = len(self.content)
        dialogue['response']['headers']['Content-Type'] = 'text/xml'

    ## @copydoc Service#response_content
    def response_content(self, dialogue):
        dialogue['response']['content'] = self.content
        self.content = ''


## File service sending home page.
#
class Home(Service):

    ## Request URI.
    NAME = '/'

    ## Constructor.
    def __init__(
        self,
    ):
        super(Home, self).__init__()
        self._resource = None

    ## Retrieve fd of file to send.
    @property
    def resource(self):
        return self._resource

    ## Set fd of file to send.
    @resource.setter
    def resource(self, val):
        self._resource = val

    ## @copydoc Service#on_headers
    def on_headers(self, dialogue):
        dialogue['request']['headers']['Cookie'] = ''

    ## @copydoc Service#response_first_line
    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        if not dialogue['request']['headers']['Cookie']:
            self.resource = open('home.html', 'rb')

    ## @copydoc Service#response_headers
    def response_headers(self, dialogue):
        if not dialogue['request']['headers']['Cookie']:
            dialogue['response']['headers']['Content-Length'] = os.fstat(
                self.resource.fileno()).st_size
            dialogue['response']['headers']['Content-Type'] = 'text/html'
        else:
            dialogue['response']['headers']['Refresh'] = '0; url=/rooms'

    ## @copydoc Service#response_content
    def response_content(self, dialogue):
        if not dialogue['request']['headers']['Cookie']:
            dialogue['response']['content'] = self.resource.read(
                constants.BLOCK_SIZE)

    ## @copydoc Service#on_end
    def on_end(self, dialogue):
        if not dialogue['request']['headers']['Cookie']:
            self.resource.close()


## Service handling registration process.
#
class Register(Service):

    ## Service name, request URI.
    NAME = '/register'

    ## Constructor.
    def __init__(
        self,
    ):
        super(Register, self).__init__()

    ## @copydoc Service#response_first_line
    def response_first_line(self, dialogue):
        self.logger.debug("NEW USER CONNECTED: %s",
                          dialogue['request']['params']['name'][0])
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'

    ## @copydoc Service#response_headers
    def response_headers(self, dialogue):
        c = Cookie.SimpleCookie()
        c['uid'] = util.generate_unique(
            dialogue['request']['context']['users'].keys())
        dialogue['request']['context']['users'][c['uid']
                                                .value] = dialogue['request']['params']['name'][0]
        self.logger.info(
            "%s has connected",
            dialogue['request']['params']['name'][0],
        )
        dialogue['response']['headers']['Set-Cookie'] = '%s=%s' % (
            c['uid'].key, c['uid'].value)
        dialogue['response']['headers']['Refresh'] = '0; url=/rooms'


## File service sending list of chat rooms html.
#
class Rooms(Service):

    ## Service name, request URI.
    NAME = '/rooms'

    ## Constructor.
    def __init__(
        self,
    ):
        super(Rooms, self).__init__()
        self._resource = None

    ## Retrieve fd of file to send.
    @property
    def resource(self):
        return self._resource

    ## Set fd of file to send.
    @resource.setter
    def resource(self, val):
        self._resource = val

    ## @copydoc Service#response_first_line
    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        self.resource = open('rooms.html', 'rb')

    ## @copydoc Service#response_headers
    def response_headers(self, dialogue):
        dialogue['response']['headers']['Content-Length'] = os.fstat(
            self.resource.fileno()).st_size
        dialogue['response']['headers']['Content-Type'] = 'text/html'

    ## @copydoc Service#response_content
    def response_content(self, dialogue):
        dialogue['response']['content'] = self.resource.read(
            constants.BLOCK_SIZE)

    ## @copydoc Service#on_end
    def on_end(self, dialogue):
        self.resource.close()


## Service handling addition of new rooms.
#
class AddRoom(Service):

    ## Service name, request URI.
    NAME = '/add-room'

    ## Constructor.
    def __init__(
        self,
    ):
        super(AddRoom, self).__init__()

    ## @copydoc Service#response_first_line
    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        root = et.fromstring(dialogue['request']['content'])
        dialogue['request']['context']['rooms'][root[0].attrib['name']] = {
            'users': {}, 'messages': [], 'base_index': 0}
        self.logger.info(
            "Created new room: %s",
            root[0].attrib['name'],
        )


## Service handling request to get current rooms.
#
class GetRooms(Service):

    ## Service name, request URI.
    NAME = '/get-rooms'

    ## Constructor.
    def __init__(
        self,
    ):
        super(GetRooms, self).__init__()
        self._content = ''

    ## Retrieve response content to send.
    @property
    def content(self):
        return self._content

    ## Set response content to send.
    @content.setter
    def content(self, val):
        self._content = val

    ## @copydoc Service#response_first_line
    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'

    ## @copydoc Service#response_headers
    def response_headers(self, dialogue):
        root = et.Element('root')
        for room in dialogue['request']['context']['rooms'].keys():
            et.SubElement(root, 'room').attrib['name'] = room
        self.content = et.tostring(root)
        dialogue['response']['headers']['Content-Length'] = len(self.content)
        dialogue['response']['headers']['Content-Type'] = 'text/xml'

    ## @copydoc Service#response_content
    def response_content(self, dialogue):
        dialogue['response']['content'] = self.content
        self.content = ''
