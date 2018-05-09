#coding=utf-8

import logging, os

logging.basicConfig(level=logging.INFO)

from transwarp import db
from transwarp.web import WSGIApplication, Jinja2TemplateEngine

from config import configs

document_root = os.path.dirname(os.path.abspath(__file__))

# 初始化数据库.
db.create_engine(**configs.db)

# 创建 WSGIApplication
wsgi = WSGIApplication(document_root)

# 初始化 Jinja2TemplateEngine
wsgi.template_engine = Jinja2TemplateEngine( os.path.join(document_root, "templates") )

# 加载带有@get/@post的URL处理函数
import urls
wsgi.add_module(urls)

# 在9000端口上启动测试服务.
if __name__ == "__main__":
    wsgi.run(port=9000)