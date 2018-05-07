#coding=utf-8

import threading
from utils import Dict


ctx = threading.local()

class HttpError(Exception):
    pass


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

