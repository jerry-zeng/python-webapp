#coding=utf-8

import os, re, time, base64, hashlib, logging

from transwarp.web import get, post, view
from models import User, Blog, Comment
from apis import api, ApiError, ApiValueError

#------------------------------test------------------------------
# @view("test_users.html")
# @get("/")
# def test_users():
#     users = User.find_all()
#     return dict(users=users)

#------------------------------Logic------------------------------
@view("blogs.html")
@get("/")
def index():
    blogs = Blog.find_all()
    user = User.find_first("where admin=?", True)
    return dict(blogs=blogs, user=user)


#------------------------------Api------------------------------
@api
@get("/api/users")
def api_get_users():
    users = User.find_by("order by created_at desc")
    for u in users:
        u.password = "******"
    return dict(users=users)

@api
@get("/api/blogs")
def api_get_blogs():
    blogs = Blog.find_by("order by created_at desc")
    return dict(blogs=blogs)