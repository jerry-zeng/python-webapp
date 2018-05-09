#coding=utf-8

import logging, os, time

logging.basicConfig(level=logging.INFO)

from transwarp import db
from transwarp.web import WSGIApplication, Jinja2TemplateEngine
from datetime import datetime

from config import configs

document_root = os.path.dirname(os.path.abspath(__file__))
print"document_root:", document_root

# 初始化数据库.
db.create_engine(**configs.db)

# 创建 WSGIApplication
wsgi = WSGIApplication(document_root)

# 初始化 Jinja2TemplateEngine
def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u"1分钟前"
    elif delta < 3600:
        return u'%s分钟前' % (delta // 60)
    elif delta < 86400:
        return u'%s小时前' % (delta // 3600)
    elif delta < 604800:
        return u'%s天前' % (delta // 86400)

    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

template_engine = Jinja2TemplateEngine( os.path.join(document_root, "templates") )
template_engine.add_filter("datetime", datetime_filter)

wsgi.template_engine = template_engine

# 加载带有@get/@post的URL处理函数
import urls
wsgi.add_module(urls)

# 在9000端口上启动测试服务.
if __name__ == "__main__":
    wsgi.run(port=9000)
else:
    application = wsgi.get_wsgi_application()