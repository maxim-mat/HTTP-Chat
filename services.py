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

class Cute(base.Base, Service):

    NAME = '/cute'

    def __init__(
        self,
    ):
        super(Cute, self).__init__()
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
        self.resource = open('dog.jpg', 'rb')

    def response_headers(self, dialogue):
        dialogue['response']['headers']['Content-Length'] = os.fstat(self.resource.fileno()).st_size
        dialogue['response']['headers']['Content-Type'] = 'image/jpeg'

    def response_content(self, dialogue):
        dialogue['response']['content'] = self.resource.read(constants.BUFFER_LIMIT)

    def on_end(self, dialogue):
        self.resource.close()

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

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        self.resource = open('chat.html', 'rb')

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
        if dialogue['request']['method'] == 'POST':
            root = et.fromstring(dialogue['request']['content'])
            dialogue['request']['context']['rooms']['room'].append(root[0].attrib['text'])

    def response_headers(self, dialogue):
        c = Cookie.SimpleCookie()
        c.load(str(dialogue['request']['headers']['Cookie']))
        self.content = '<html><body>%s: %s</body></html><br/>' % (dialogue['request']['context']['users'][c['uid'].value] , util.get_last_element(dialogue['request']['context']['rooms']['room']))
        dialogue['response']['headers']['Content-Length'] = len(self.content)
        dialogue['response']['headers']['Content-Type'] = 'text/html'
        dialogue['response']['headers']['Cookie'] = dialogue['request']['headers']['Cookie']

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

    def response_first_line(self, dialogue):
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'
        self.resource = open('home.html', 'rb')

    def response_headers(self, dialogue):
        dialogue['response']['headers']['Content-Length'] = os.fstat(self.resource.fileno()).st_size
        dialogue['response']['headers']['Content-Type'] = 'text/html'

    def response_content(self, dialogue):
        dialogue['response']['content'] = self.resource.read(constants.BUFFER_LIMIT)

    def on_end(self, dialogue):
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
        self.logger.debug("USER NAME IS: %s", dialogue['request']['params']['name'][0])
        dialogue['response']['code'] = '200'
        dialogue['response']['message'] = 'OK'

    def response_headers(self, dialogue):
        c = Cookie.SimpleCookie()
        c['uid'] = util.generate_unique(dialogue['request']['context']['users'].keys())
        dialogue['request']['context']['users'][c['uid'].value] = dialogue['request']['params']['name'][0]
        print dialogue['request']['context']
        dialogue['response']['headers']['Refresh'] = '0; url=http://localhost:8080/chat'
        dialogue['response']['headers']['Set-Cookie'] = '%s=%s' % (c['uid'].key, c['uid'].value)

