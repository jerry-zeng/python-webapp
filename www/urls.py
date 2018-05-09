#coding=utf-8

from transwarp.web import get, post, view
from models import User, Blog, Comment

@view("test_users.html")
@get("/")
def test_users():
    users = User.find_all()
    return dict(users=users)