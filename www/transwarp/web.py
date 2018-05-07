#coding=utf-8

import threading
from utils import Dict
import os, sys, time, datetime, functools
import re

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

ctx = threading.local()


# 状态码.
_RESPONSE_STATUSES = {
    # Informational
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',

    # Successful
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi Status',
    226: 'IM Used',

    # Redirection
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',

    # Client Error
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',

    # Server Error
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    507: 'Insufficient Storage',
    510: 'Not Extended',
}

_REG_RESPONSE_STATUSES = re.compile(r"\d\d\d(\ [\w ]+)?$")

_RESPONSE_HEADERS = (
    'Accept-Ranges',
    'Age',
    'Allow',
    'Cache-Control',
    'Connection',
    'Content-Encoding',
    'Content-Language',
    'Content-Length',
    'Content-Location',
    'Content-MD5',
    'Content-Disposition',
    'Content-Range',
    'Content-Type',
    'Date',
    'ETag',
    'Expires',
    'Last-Modified',
    'Link',
    'Location',
    'P3P',
    'Pragma',
    'Proxy-Authenticate',
    'Refresh',
    'Retry-After',
    'Server',
    'Set-Cookie',
    'Strict-Transport-Security',
    'Trailer',
    'Transfer-Encoding',
    'Vary',
    'Via',
    'Warning',
    'WWW-Authenticate',
    'X-Frame-Options',
    'X-XSS-Protection',
    'X-Content-Type-Options',
    'X-Forwarded-Proto',
    'X-Powered-By',
    'X-UA-Compatible',
)

_RESPONSE_HEADERS_DICT = dict( zip(map(lambda x:x.upper(), _RESPONSE_HEADERS), _RESPONSE_HEADERS) )

_HEADER_X_POWERED_BY = ('X-Powered-By', 'transwarp/1.0')

class HttpError(Exception):
    def __init__(self, code):
        super(Exception, self).__init__()
        self.status = "%d %s" % (code, _RESPONSE_STATUSES[code])

    def header(self, key, value):
        if not hasattr(self, "_headers"):
            self._headers = [_HEADER_X_POWERED_BY]
        self._headers.append( (key, value) )

    @property
    def headers(self):
        if hasattr(self, "_headers"):
            return self._headers
        return []

    def __str__(self):
        return self.status

    __repr__ = __str__

class RedirectError(HttpError):
    def __init__(self, code, location):
        super(RedirectError, self).__init__(code)
        self.location = location

    def __str__(self):
        return "%s, %s" % (self.status, self.location)

    __repr__ = __str__


class Request(object):
    def input(self):
        pass

    def get(self, key, default=None):
        pass

    @property
    def path_info(self):
        pass

    @property
    def header(self):
        pass

    def cookie(self, key, default=None):
        pass


class Response(object):
    def set_header(self, key, value):
        pass

    def set_cookie(self, key, value, max_age=None, expires=None, path="/"):
        pass

    @property
    def status(self):
        pass

    @status.setter
    def status(self, value):
        pass


class TemplateEngine(object):
    pass


def get(path):
    pass

def post(path):
    pass

def view(path):
    pass

def interceptor(pattern):
    pass

class Jinja2TemplateEngine(TemplateEngine):
    pass

class WSGIApplication(object):
    def __init__(self, document_root=None, **kw):
        pass

    def add_url(self, func):
        pass

    def add_interceptor(self, func):
        pass

    @property
    def template_engine(self):
        pass

    @template_engine.setter
    def template_engine(self):
        pass

    def get_wsgi_application(self):
        def wsgi(env, start_response):
            pass

        return wsgi

    def run(self, host="127.0.0.1", port=9000):
        from wsgiref.simple_server import make_server
        server = make_server(host, port, self.get_wsgi_application())
        server.serve_forever()

