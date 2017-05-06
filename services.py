import base
import constants
import Cookie
import os
import time
import urlparse
import util
import xml.etree.ElementTree as et


class Service(object):

    NAME = 'Base'

    def __init__(self):
        pass

    def on_first_line(self, dialogue):
        pass

    def on_headers(self, dialogue):
        pass

    def on_content(self, dialogue):
        pass

    def response_first_line(self, dialogue):
        pass

    def response_headers(self, dialogue):
        pass

    def response_content(self, dialogue):
        pass

    def on_end(self, dialogue):
        pass

class Clock(base.Base, Service):

    NAME = '/clock'

    def __init__(
        self,
    ):
        super(Clock, self).__init__()
        Service.__init__(self)
        self._content = ''

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, val):
        self._content = val

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'

    def response_headers(self, dialogue):
        self.content = '<html><body>%s</body></html>' % (time.strftime('%H:%M:%S'))
        dialogue['response']['headers']['Content-Length'] = len(self.content)
        dialogue['response']['headers']['Content-Type'] = 'text/html'

    def response_content(self, dialogue):
        dialogue['response']['content'] = self.content
        self.content = ''

class Favicon(base.Base, Service):

    NAME = '/favicon.ico'

    def __init__(
        self,
    ):
        super(Favicon, self).__init__()
        Service.__init__(self)
        self._resource = None
        self._content = ''

    @property
    def resource(self):
        return self._resource

    @resource.setter
    def resource(self, val):
        self._resource = val

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        self.resource = open('chat.ico', 'rb')

    def response_headers(self, dialogue):
        dialogue['response']['headers']['Content-Length'] = os.fstat(self.resource.fileno()).st_size
        dialogue['response']['headers']['Content-Type'] = 'image/jpeg'

    def response_content(self, dialogue):
        dialogue['response']['content'] = self.resource.read(constants.BUFFER_LIMIT)

    def on_end(self, dialogue):
        self.resource.close()

class Chat(base.Base, Service):

    NAME = '/chat'

    def __init__(
        self,
    ):
        super(Chat, self).__init__()
        Service.__init__(self)
        self._resource = None
        self._content = ''

    @property
    def resource(self):
        return self._resource

    @resource.setter
    def resource(self, val):
        self._resource = val

    def on_headers(self, dialogue):
        dialogue['request']['headers']['Cookie'] = ''

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        self.resource = open('chat.html', 'rb')
        c = Cookie.SimpleCookie()
        c.load(str(dialogue['request']['headers']['Cookie']))
        room = dialogue['request']['params']['room'][0]
        username = dialogue['request']['context']['users'][c['uid'].value]
        dialogue['request']['context']['rooms'][room]['users'][username] = time.time()
        self.logger.debug("USERS %s", dialogue['request']['context']['rooms'][room]['users'])

    def response_headers(self, dialogue):
        dialogue['response']['headers']['Content-Length'] = os.fstat(self.resource.fileno()).st_size
        dialogue['response']['headers']['Content-Type'] = 'text/html'

    def response_content(self, dialogue):
        dialogue['response']['content'] = self.resource.read(constants.BUFFER_LIMIT)

    def on_end(self, dialogue):
        self.resource.close()

class Update(base.Base, Service):

    NAME = '/update'

    def __init__(
        self,
    ):
        super(Update, self).__init__()
        Service.__init__(self)
        self._content = ''

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, val):
        self._content = val

    def on_headers(self, dialogue):
        dialogue['request']['headers']['Cookie'] = ''

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        c = Cookie.SimpleCookie()
        c.load(str(dialogue['request']['headers']['Cookie']))
        root = et.fromstring(dialogue['request']['content'])
        messages = root.findall('messages')
        room = root.findall('room')[0].attrib['name']
        for message in messages[0].findall('message'):
            dialogue['request']['context']['rooms'][room]['users'][dialogue['request']['context']['users'][c['uid'].value]] = time.time()
            dialogue['request']['context']['rooms'][room]['messages'].append('%s: %s' % (dialogue['request']['context']['users'][c['uid'].value], message.attrib['text']))

    def response_headers(self, dialogue):
        c = Cookie.SimpleCookie()
        c.load(str(dialogue['request']['headers']['Cookie']))
        root = et.fromstring(dialogue['request']['content'])
        room = root.findall('room')[0].attrib['name']
        messages = util.get_revision(dialogue['request']['context']['rooms'][room]['messages'], int(root.findall('fetch')[0].attrib['id']))
        root = et.Element('root')
        et.SubElement(root, 'messages')
        for entry in messages:
            et.SubElement(root[0], 'message').text = entry
        if messages:
            et.SubElement(root, 'id').text = '%s' % (len(dialogue['request']['context']['rooms'][room]['messages']))
        et.SubElement(root, 'users')
        util.clear_outdated_users(dialogue['request']['context']['rooms'][room]['users'])
        for name in dialogue['request']['context']['rooms'][room]['users'].keys():
            et.SubElement(root[1], 'user').text = name
        self.logger.debug('HERE BE THE MESSAGES: %s', et.tostring(root))
        self.content = et.tostring(root)
        dialogue['response']['headers']['Content-Length'] = len(self.content)
        dialogue['response']['headers']['Content-Type'] = 'text/xml'

    def response_content(self, dialogue):
        dialogue['response']['content'] = self.content
        self.content = ''

class Home(base.Base, Service):

    NAME = '/'

    def __init__(
        self,
    ):
        super(Home, self).__init__()
        Service.__init__(self)
        self._resource = None

    @property
    def resource(self):
        return self._resource

    @resource.setter
    def resource(self, val):
        self._resource = val

    def on_headers(self, dialogue):
        dialogue['request']['headers']['Cookie'] = ''

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        if not dialogue['request']['headers']['Cookie']:
            self.resource = open('home.html', 'rb')

    def response_headers(self, dialogue):
        if not dialogue['request']['headers']['Cookie']:
            dialogue['response']['headers']['Content-Length'] = os.fstat(self.resource.fileno()).st_size
            dialogue['response']['headers']['Content-Type'] = 'text/html'
        else:
            dialogue['response']['headers']['Refresh'] = '0; url=/rooms'

    def response_content(self, dialogue):
        if not dialogue['request']['headers']['Cookie']:
            dialogue['response']['content'] = self.resource.read(constants.BUFFER_LIMIT)

    def on_end(self, dialogue):
        if not dialogue['request']['headers']['Cookie']:
            self.resource.close()

class Login(base.Base, Service):

    NAME = '/login'

    def __init__(
        self,
    ):
        super(Login, self).__init__()
        Service.__init__(self)
        self._resource = None
        self._content = ''

    @property
    def resource(self):
        return self._resource

    @resource.setter
    def resource(self, val):
        self._resource = val

    def response_first_line(self, dialogue):
        self.logger.debug("NEW USER CONNECTED: %s", dialogue['request']['params']['name'][0])
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'

    def response_headers(self, dialogue):
        c = Cookie.SimpleCookie()
        c['uid'] = util.generate_unique(dialogue['request']['context']['users'].keys())
        dialogue['request']['context']['users'][c['uid'].value] = dialogue['request']['params']['name'][0]
        dialogue['response']['headers']['Set-Cookie'] = '%s=%s' % (c['uid'].key, c['uid'].value)
        dialogue['response']['headers']['Refresh'] = '0; url=/rooms'

class Rooms(base.Base, Service):

    NAME = '/rooms'

    def __init__(
        self,
    ):
        super(Rooms, self).__init__()
        Service.__init__(self)
        self._resource = None
        self._content = ''

    @property
    def resource(self):
        return self._resource

    @resource.setter
    def resource(self, val):
        self._resource = val

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        self.resource = open('rooms.html', 'rb')

    def response_headers(self, dialogue):
        dialogue['response']['headers']['Content-Length'] = os.fstat(self.resource.fileno()).st_size
        dialogue['response']['headers']['Content-Type'] = 'text/html'

    def response_content(self, dialogue):
        dialogue['response']['content'] = self.resource.read(constants.BUFFER_LIMIT)

    def on_end(self, dialogue):
        self.resource.close()

class Append(base.Base, Service):

    NAME = '/append'

    def __init__(
        self,
    ):
        super(Append, self).__init__()
        Service.__init__(self)

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        root = et.fromstring(dialogue['request']['content'])
        dialogue['request']['context']['rooms'][root[0].attrib['name']] = {'users':{}, 'messages': []}

class Refresh(base.Base, Service):

    NAME = '/refresh'

    def __init__(
        self,
    ):
        super(Refresh, self).__init__()
        Service.__init__(self)
        self._content = ''

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, val):
        self._content = val

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'

    def response_headers(self, dialogue):
        root = et.Element('root')
        for room in dialogue['request']['context']['rooms'].keys():
            et.SubElement(root, 'room').text = room
        self.content = et.tostring(root)
        dialogue['response']['headers']['Content-Length'] = len(self.content)
        dialogue['response']['headers']['Content-Type'] = 'text/xml'

    def response_content(self, dialogue):
        dialogue['response']['content'] = self.content
        self.content = ''

class Users(base.Base, Service):

    NAME = '/users'

    def __init__(
        self,
    ):
        super(Users, self).__init__()
        Service.__init__(self)
        self._content = ''

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, val):
        self._content = val

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'

    def response_headers(self, dialogue):
        root = et.Element('root')
        input = et.fromstring(dialogue['request']['content'])
        room = input.findall('room')[0].attrib['name']
        for name in dialogue['request']['context']['rooms'][room]['users'].keys():
            et.SubElement(root, 'user').text = name
        self.content = et.tostring(root)
        dialogue['response']['headers']['Content-Length'] = len(self.content)
        dialogue['response']['headers']['Content-Type'] = 'text/xml'

    def response_content(self, dialogue):
        dialogue['response']['content'] = self.content
        self.content = ''
