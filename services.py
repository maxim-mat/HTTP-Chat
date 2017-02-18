import base
import constants
import os
import time


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
