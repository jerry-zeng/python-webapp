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


class Page(object):
    '''
    item_count: total item count
    '''
    def __init__(self, total_item_count, page_index=1, page_size=10):
        self.total_item_count = total_item_count
        self.page_size = page_size

        extra = 0
        if total_item_count%page_size > 0:
            extra = 1
        self.page_count = total_item_count // page_size + extra

        if total_item_count == 0 or page_index < 1 or page_index > self.page_count:
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size

        self.has_next = self.page_index < self.page_count
        self.has_previous = self.page_index > 1

    def __str__(self):
        return "{total_item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s}" % (self.total_item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)

    __repr__ = __str__

def _dump(obj):
    if isinstance(obj, Page):
        return dict(page_index=obj.page_index,
                    page_count=obj.page_count,
                    item_count=obj.total_item_count,
                    has_next=obj.has_next,
                    has_previous=obj.has_previous)
    else:
        raise TypeError('%s is not JSON serializable' % obj)

def api(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        try:
            r = func(*args, **kw)
            r = json.dumps( r, default=_dump )
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