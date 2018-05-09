#coding=utf-8

from transwarp.web import get, post, view
from models import User, Blog, Comment

# @view("test_users.html")
# @get("/")
# def test_users():
#     users = User.find_all()
#     return dict(users=users)


@view("blogs.html")
@get("/")
def index():
    blogs = Blog.find_all()
    user = User.find_first("where admin=?", True)
    return dict(blogs=blogs, user=user)



