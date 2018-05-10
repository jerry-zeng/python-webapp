#coding=utf-8

import functools, json, logging
from transwarp.web import ctx


class ApiError(StandardError):
    def __init__(self, err, data="", message=""):
        super(ApiError, self).__init__(message)
        self.error = err
        self.data = data
        self.message = message

class ApiValueError(ApiError):
    def __init__(self, field, msg=""):
        super(ApiValueError, self).__init__("value invalid", field, msg)

class ApiResourceNotFoundError(ApiError):
    def __init__(self, field, msg=""):
        super(ApiValueError, self).__init__("resource not found", field, msg)

class ApiPermissionError(ApiError):
    def __init__(self, msg=""):
        super(ApiValueError, self).__init__("permission denied", "permission", msg)


def api(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        try:
            r = func(*args, **kw)
            r = json.dumps( r )
        except ApiError, e:
            r = json.dumps(dict(error=e.error, data=e.data, message=e.message))
        except Exception, e:
            logging.exception(e)
            r = json.dumps(dict(error="internalError", data=e.__class__.__name__, message=e.message))

        ctx.response.content_type = "application/json"
        return r
    return wrapper

if __name__ == "__main__":
    import doctest
    doctest.testmod()