#coding=utf-8

import threading
from utils import Dict, UTC
import os, sys,  functools, types, mimetypes, traceback, logging
import re, urllib, cgi, datetime

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

ctx = threading.local()

#-----------------------------------Status & Headers & HttpError----------------------------------

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

#----------------------------------Tool-----------------------------------
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


_REG_ROUTE = re.compile(r"(\:[a-zA-Z_]\w*)")

def _build_regex(path):
    '''
    _build_regex('/path/to/:file')
    _build_regex('/:user/:comments/list')
    _build_regex(':id-:pid/:w')
    '''
    re_list = []
    var_list = []
    is_var = False

    re_list.append("^")

    for v in _REG_ROUTE.split(path):
        if is_var:
            var_name = v[1:]
            var_list.append(var_name)
            re_list.append(r"(?P<%s>[^\/]+)" % var_name)
        else:
            s = ""
            for ch in v:
                if ch >= '0' and ch <= '9':
                    s = s + ch
                elif ch >= 'A' and ch <= 'Z':
                    s = s + ch
                elif ch >= 'a' and ch <= 'z':
                    s = s + ch
                else:
                    s = s + "\\" + ch
            re_list.append(s)

        is_var = not is_var

    re_list.append("$")
    return ''.join(re_list)

class Route(object):
    def __init__(self, func):
        self.path = func.__web_route__
        self.method = func.__web_method__
        self.is_static = _REG_ROUTE.search(self.path) is None
        if not self.is_static:
            self.route = re.compile(_build_regex(self.path))
        self.func = func

    def match(self, url):
        if self.route:
            mt = self.route.match(url)
            if mt:
                return mt.groups()

        return None

    def __call__(self, *args, **kwargs):
        return self.func(*args)

    def __str__(self):
        if self.is_static:
            return "Route(static, %s, path=%s)" % (self.method, self.path)
        else:
            return "Route(dynamic, %s, path=%s)" % (self.method, self.path)

    __repr__ = __str__


def _static_file_generator(fpath):
    block_size = 8192
    with open(fpath, "rb") as f:
        block = f.read(block_size)
        while block:
            yield block
            block = f.read(block_size)

class StaticFileRoute(object):
    def __init__(self):
        self.method = "GET"
        self.is_static = False
        self.route = re.compile("^/static/(.+)$")

    def match(self, url):
        if url.startswith('/static/'):
            return (url[1:],)
        return None

    def __call__(self, *args, **kwargs):
        fpath = os.path.join(ctx.application.document_root, args[0])
        if not os.path.isfile(fpath):
            raise notFound()

        fext = os.path.splitext(fpath)[1]
        tm = mimetypes.types_map  # global
        ctx.response.content_type = tm.get(fext.lower(), 'application/octet-stream')
        return _static_file_generator(fpath)


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
    # 解析environ.
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

_UTC_0 = UTC('+00:00')

class Response(object):
    def __init__(self):
        self._status = "200 OK"
        self._headers = {'CONTENT-TYPE': 'text/html; charset=utf-8'}

    @property
    def status_code(self):
        return int(self._status[:3])

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if isinstance(value, (int, long)):
            if value >= 100 and value <= 999:
                sc = _RESPONSE_STATUSES[value]
                if sc:
                    self._status = "%d %s" % (value, sc)
                else:
                    self._status = str(value)
            else:
                raise ValueError('Bad response code: %s' % value)

        elif isinstance(value, basestring):
            if isinstance(value, unicode):
                value = value.encode(DEFAULT_ENCODING)

            if _REG_RESPONSE_STATUSES.match(value):
                self._status = value
            else:
                raise ValueError('Bad response code: %s' % value)

        else:
            raise ValueError('Bad type of response code: %s' % value)


    @property
    def headers(self):
        l = [ ( _RESPONSE_HEADERS_DICT.get(k, k), v) for k,v in self._headers.iteritems()]
        if hasattr(self, "_cookies"):
            for v in self._cookies.itervalues():
                l.append( ("Set-Cookie", v) )

        l.append(_HEADER_X_POWERED_BY)
        return l

    def header(self, key):
        name = key.upper()
        if not name in _RESPONSE_HEADERS_DICT:
            name = key
        return self._headers.get(name)

    def unset_header(self, key):
        name = key.upper()
        if not name in _RESPONSE_HEADERS_DICT:
            name = key
        if name in self._headers:
            del self._headers[name]

    def set_header(self, key, value):
        name = key.upper()
        if not name in _RESPONSE_HEADERS_DICT:
            name = key
        self._headers[name] = value

    @property
    def content_type(self):
        return self.header("CONTENT-TYPE")

    @content_type.setter
    def content_type(self, value):
        if value:
            self.set_header("CONTENT-TYPE", value)
        else:
            self.unset_header("CONTENT-TYPE")

    @property
    def content_length(self):
        return self.header("CONTENT-LENGTH")

    @content_length.setter
    def content_length(self, value):
        self.set_header("CONTENT-LENGTH", str(value))

    def delete_cookie(self, key):
        self.set_cookie(key, "__deleted__", expires=0)

    def set_cookie(self, key, value, max_age=None, expires=None, path="/", domain=None, secure=False, http_only=True):
        if not hasattr(self, "_cookies"):
            self._cookies = {}

        l = [ "%s=%s" % (_quote(key), _quote(value)) ]

        if expires is not None:
            # TODO: format expires to date time string.
            if isinstance(expires, (float, int, long)):
                expStr = datetime.datetime.fromtimestamp(expires, _UTC_0).strftime('%a, %d-%b-%Y %H:%M:%S GMT')
                l.append("Expires=%s" % expStr)
            elif isinstance(expires, (datetime.date, datetime.datetime)):
                expStr = expires.astimezone(_UTC_0).strftime('%a, %d-%b-%Y %H:%M:%S GMT')
                l.append("Expires=%s" % expStr)

        elif isinstance(max_age, (int, long)):
            l.append("Max-Age=%d" % max_age)

        l.append('Path=%s' % path)

        if domain:
            l.append("Domain=%s" % domain)
        if secure:
            l.append("Secure")
        if http_only:
            l.append("HttpOnly")

        self._cookies[key] = "; ".join(l)

    def unset_cookie(self, key):
        if hasattr(self, "_cookies"):
            if key in self._cookies:
                del self._cookies[key]

#----------------------------------View-----------------------------------
class Template(object):
    def __init__(self, template_name, **kw):
        self.template_name = template_name
        self.model = Dict(**kw)

class TemplateEngine(object):
    def __call__(self, path, model):
        return "<!-- override this method to render template -->"

class Jinja2TemplateEngine(TemplateEngine):
    def __init__(self, temp_dir, **kw):
        from jinja2 import Environment, FileSystemLoader
        if not "autoescape" in kw:
            kw["autoescape"] = True

        self._env = Environment(loader=FileSystemLoader(temp_dir), **kw)

    def add_filter(self, key, fn_filter):
        self._env.filters[key] = fn_filter

    def __call__(self, path, model):
        return self._env.get_template(path).render(**model).encode(DEFAULT_ENCODING)


def view(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            r = func(*args, **kw)
            if isinstance(r, dict):
                return Template(path, **r)
            else:
                raise ValueError('Expect return a dict when using @view() decorator.')
        return wrapper
    return decorator

#-------------------------------Interceptor---------------------------------

_REG_INTERCEPTOR_STARTS_WITH = re.compile(r"^([^\*\?]+)\*?$")
_REG_INTERCEPTOR_ENDS_WITH = re.compile(r"^\*([^\*\?]+)$")

def _build_pattern_fn(pattern):
    mt = _REG_INTERCEPTOR_STARTS_WITH.match(pattern)
    if mt:
        return lambda s: s.startswith(mt.group(1))

    mt = _REG_INTERCEPTOR_ENDS_WITH.match(pattern)
    if mt:
        return lambda s: s.endswith(mt.group(1))

    raise ValueError('Invalid pattern definition in interceptor: %s' % pattern)

def interceptor(pattern="/"):
    def decorator(func):
        func.__interceptor__ = _build_pattern_fn(pattern)
        return func
    return decorator


def _build_interceptor_fn(func, next):
    def decorator():
        if func.__interceptor__(ctx.request.path_info):
            return func(next)
        else:
            return next()
    return decorator

def _build_interceptor_chain(last_fn, *interceptors):
    l = list(interceptors)
    l.reverse()

    fn = last_fn
    for f in l:
        fn = _build_interceptor_fn(f, fn)

    return fn

#--------------------------------WSGI Application-------------------------------------

def _load_module(module_name):
    last_dot = module_name.rfind(".")
    if last_dot == -1:
        return __import__(module_name, globals(), locals())

    fromModule = module_name[:last_dot]
    importModule = module_name[last_dot+1:]
    md = __import__(fromModule, globals(), locals(), [importModule])
    return hasattr(importModule, md)

class WSGIApplication(object):
    def __init__(self, document_root=None, **kw):
        self._running = False
        self._document_root = document_root

        self._interceptors = []
        self._template_engine = None

        self._get_static_route = {}
        self._post_static_route = {}

        self._get_dynamic_route = []
        self._post_dynamic_route = []

    def _check_is_running(self):
        if self._running:
            raise RuntimeError("Cannot modify WSGIApplication when running.")

    def add_module(self, mod):
        self._check_is_running()

        m = None
        if type(mod) == types.ModuleType:
            m = mod
        else:
            m = _load_module(mod)

        for name in dir(m):
            fn = getattr(m, name)
            if callable(fn) and hasattr(fn, "__web_route__") and hasattr(fn, "__web_method__"):
                self.add_url(fn)

    def add_url(self, func):
        self._check_is_running()
        route = Route(func)
        if route.is_static:
            if route.method == "POST":
                self._post_static_route[route.path] = route
            elif route.method == "GET":
                self._get_static_route[route.path] = route
        else:
            if route.method == "POST":
                self._post_dynamic_route.append(route)
            elif route.method == "GET":
                self._get_dynamic_route.append(route)

    def add_interceptor(self, interceptor):
        self._check_is_running()
        self._interceptors.append(interceptor)

    @property
    def template_engine(self):
        return self._template_engine

    @template_engine.setter
    def template_engine(self, value):
        self._check_is_running()
        self._template_engine = value

    def get_wsgi_application(self, debug=False):
        self._check_is_running()

        if debug:
            self._get_dynamic_route.append( StaticFileRoute() )

        self._running = True

        _application = Dict(document_root=self._document_root)


        def fn_route():
            request_method = ctx.request.request_method
            path_info = ctx.request.path_info

            if request_method == "GET":
                fn = self._get_static_route.get(path_info, None)
                if fn:
                    return fn()

                for route in self._get_dynamic_route:
                    args = route.match(path_info)
                    if args:
                        return route(*args)

                raise notFound()

            elif request_method == "POST":
                fn = self._post_static_route.get(path_info, None)
                if fn:
                    return fn()

                for route in self._post_dynamic_route:
                    args = route.match(path_info)
                    if args:
                        return route(*args)

                raise notFound()

            else:
                raise badRequest()

        fn_exe = _build_interceptor_chain(fn_route, *self._interceptors)


        def wsgi(env, start_response):
            ctx.application = _application
            ctx.request = Request(env)
            ctx.response = Response()

            response = ctx.response

            try:
                r = fn_exe()

                if isinstance(r, Template):
                    r = self._template_engine(r.template_name, r.model)
                if isinstance(r, unicode):
                    r = r.encode(DEFAULT_ENCODING)
                if r is None:
                    r = []

                start_response(response.status, response.headers)

                return r

            except RedirectError, e:
                response.set_header("Location", e.location)
                start_response(e.status, e.location)
                return []
            except HttpError, e:
                start_response(e.status, response.headers)
                return [ '<html><body><h1>', e.status, '</h1></body></html>' ]
            except Exception, e:
                logging.exception(e)

                # 500
                err = internalError()
                if not debug:
                    start_response(err.status, err.headers)
                    return [ '<html><body><h1>', err.status, '</h1></body></html>' ]

                exc_type, exc_value, exc_traceback = sys.exc_info()
                fp = StringIO()
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=fp)
                stacks = fp.getvalue()
                fp.close()

                start_response(err.status, err.headers)

                return [
                    '<html><body><h1>',
                    err.status,
                    r'''</h1><div style="font-family:Monaco, Menlo, Consolas, 'Courier New', monospace;"><pre>''',
                    stacks.replace('<', '&lt;').replace('>', '&gt;'),
                    '</pre></div></body></html>']

            finally:
                del ctx.application
                del ctx.request
                del ctx.response

        return wsgi

    def run(self, host="127.0.0.1", port=9000):
        from wsgiref.simple_server import make_server
        logging.info('application (%s) will start at %s:%s...' % (self._document_root, host, port))
        server = make_server(host, port, self.get_wsgi_application(debug=True))
        server.serve_forever()

        self.server = server

    def shutdown(self):
        if self.server:
            self.server.shutdown()

if __name__ == "__main__":
    sys.path.append(".")
    import doctest
    doctest.testmod()