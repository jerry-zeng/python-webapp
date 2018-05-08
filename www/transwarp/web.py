#coding=utf-8

import threading
from utils import Dict
import os, sys, time, datetime, functools
import re, urllib, cgi

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

ctx = threading.local()

#---------------------------------------------------------------------

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

def badRequest():
    return HttpError(400)
def unauthorized():
    return HttpError(401)
def forbidden():
    return HttpError(403)
def notFound():
    return HttpError(404)
def conflict():
    return HttpError(409)
def internalError():
    return HttpError(500)
def redirect(location):
    return RedirectError(301, location)
def found(location):
    return RedirectError(302, location)
def seeOther(location):
    return RedirectError(303, location)

#---------------------------------------------------------------------
DEFAULT_ENCODING = "utf-8"

def _to_str(s):
    if isinstance(s, str):
        return s
    if isinstance(s, unicode):
        return s.encode(DEFAULT_ENCODING)
    return str(s)

def _to_unicode(s, encoding=DEFAULT_ENCODING):
    return s.encode(encoding)

def _quote(s, encoding=DEFAULT_ENCODING):
    if isinstance(s, unicode):
        s = s.encode(encoding)
    return urllib.quote(s)

def _unquote(s, encoding=DEFAULT_ENCODING):
    s = urllib.unquote(s)
    return s.decode(encoding)



def get(path):
    def decorator(func):
        func.__web_route__ = path
        func.__web_method__ = "GET"
        return func
    return decorator

def post(path):
    def decorator(func):
        func.__web_route__ = path
        func.__web_method__ = "POST"
        return func
    return decorator

#----------------------------------Request & Response-----------------------------------

class MultipartFile(object):
    def __init__(self, storage):
        self.filename = _to_unicode(storage.filename)
        self.file = storage.file


class Request(object):
    def __init__(self, environ):
        self._environ = environ

    def _parse_input(self):
        def _convert(item):
            if isinstance(item, list):
                return [_to_unicode(i.value) for i in item]
            if item.filename:
                return MultipartFile(item)
            return _to_unicode(item)

        fs = cgi.FieldStorage(fp=self._environ.get("wsgi.input"), environ=self._environ, keep_blank_values=True)
        inputs = dict()
        for key in fs:
            inputs[key] = _convert(fs[key])
        return inputs

    def _get_raw_input(self):
        if not hasattr(self, "_raw_input"):
            self._raw_input = self._parse_input()
        return self._raw_input

    def __getitem__(self, key):
        r = self._get_raw_input()[key]
        if isinstance(r, list):
            return r[0]
        return r

    @property
    def environ(self):
        return self._environ

    @property
    def path_info(self):
        return urllib.unquote(self._environ.get("PATH_INFO", ""))

    @property
    def host(self):
        return self._environ.get("HTTP_HOST", "")

    @property
    def remote_addr(self):
        return self._environ.get("REMOTE_ADDR", "0.0.0.0")

    @property
    def document_root(self):
        return self._environ.get("DOCUMENT_ROOT", "")

    @property
    def query_string(self):
        return self._environ.get("QUERY_STRING", "")

    @property
    def request_method(self):
        return self._environ.get("REQUEST_METHOD", "")

    @property
    def headers(self):
        return Dict(**self._get_header())

    @property
    def cookies(self):
        return Dict(**self._get_cookie())

    def input(self, **kw):
        copy = Dict(**kw)
        r = self._get_raw_input()
        for k,v in r.iteritems():
            copy[k] = v[0] if isinstance(v, list) else v
        return copy

    def get(self, key, default=None):
        r = self._get_raw_input().get(key, default)
        if isinstance(r, list):
            return r[0]
        return r

    def gets(self, key):
        r = self._get_raw_input()[key]
        if isinstance(r, list):
            return r[:]
        return [r]

    def get_body(self):
        fp = self._environ.get("wsgi.input")
        return fp.read()


    def _get_header(self):
        if not hasattr(self, "_headers"):
            kvs = {}
            self._headers = kvs

            for k,v in self._environ.iteritems():
                if k.startsWith("HTTP_"):
                    kvs[ k[5:].replace("_", "-").upper() ] = v.decode(DEFAULT_ENCODING)

        return self._headers

    def header(self, key, default=None):
        d = self._get_header()
        return d.get(key.upper(), default)

    def _get_cookie(self):
        if not hasattr(self, "_cookies"):
            kvs = {}
            self._cookies = kvs

            cookieStr = self._environ.get("HTTP_COOKIE")
            if cookieStr:
                for v in cookieStr.splite(";"):
                    pos = v.find("=")
                    if pos > 0:
                        kvs[ v[:pos].strip() ] = _unquote( v[pos+1:] )

        return self._cookies

    def cookie(self, key, default=None):
        d = self._get_cookie()
        return d.get(key.upper(), default)


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

#----------------------------------View-----------------------------------
class TemplateEngine(object):
    pass


class Jinja2TemplateEngine(TemplateEngine):
    pass


def view(path):
    pass

#-------------------------------Interceptor---------------------------------
def interceptor(pattern):
    pass


#---------------------------------------------------------------------

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

