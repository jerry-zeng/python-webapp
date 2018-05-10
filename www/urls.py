#coding=utf-8

import os, re, time, base64, hashlib, logging

from transwarp.web import get, post, view, interceptor, ctx, seeOther, notFound
from models import User, Blog, Comment
from apis import api, ApiError, ApiValueError
from config import configs

_COOKIE_NAME = configs.session.name
_COOKIE_KEY = configs.session.secret

#--------------------------------------------------------

def make_signed_cookie(id, password, max_age):
    # build cookie string by: id-expires-md5
    max_age = max_age or 0
    expires = str( int(time.time() + max_age) )
    L = [id,
         expires,
         hashlib.md5('%s-%s-%s-%s' % (id, password, expires, _COOKIE_KEY)).hexdigest()
         ]
    return "-".join(L)

def parse_signed_cookie(cookie_str):
    try:
        L = cookie_str.split("-")
        if len(L) != 3:
            return None
        id, expires, md5 = L

        if int(expires) < time.time():
            return None

        user = User.get(id)
        if user is None:
            return None

        if md5 != hashlib.md5('%s-%s-%s-%s' % (id, user.password, expires, _COOKIE_KEY)).hexdigest():
            return None

        return user

    except:
        return None

#------------------------------Logic------------------------------
@view("blogs.html")
@get("/")
def index():
    blogs = Blog.find_all()
    user = ctx.request.user
    return dict(blogs=blogs, user=user)

@view("signin.html")
@get("/signin")
def signin():
    return dict()

@view("register.html")
@get("/register")
def register():
    return dict()

@get("/signout")
def signout():
    ctx.response.delete_cookie(_COOKIE_NAME)
    raise seeOther("/")

@interceptor("/")
def user_interceptor(next):
    #logging.info("try to bind user from session cookies...")
    user = None
    cookie = ctx.request.cookies.get(_COOKIE_NAME)
    if cookie:
        user = parse_signed_cookie(cookie)
    ctx.request.user = user
    return next()

@interceptor("/manage/")
def manage_interceptor(next):
    user = ctx.request.user
    if user and user.admin:
        return next()
    raise seeOther("/signin")

#------------------------------Api------------------------------

@api
@post("/api/authenticate")
def authenticate():
    input = ctx.request.input(remember="")
    email = input.email.strip().lower()
    password = input.password
    remember = input.remember

    user = User.find_first("where email=?", email)
    if user is None:
        raise ApiError("auth failed", "email", "Invalid email.")
    elif user.password != password:
        raise ApiError("auth failed", "password", "Invalid password.")

    # make session cookie:
    max_age = None
    if remember == "true" or remember == "True":
        max_age = 7 * 86400

    cookie = make_signed_cookie(user.id, user.password, max_age)
    ctx.response.set_cookie(_COOKIE_NAME, cookie, max_age=max_age)

    user.password = "******"
    return user

_REG_EMAIL = re.compile(r"^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$")
_REG_MD5 = re.compile(r"^[0-9a-f]{32}$")

@api
@post("/api/users")
def api_register_user():
    input = ctx.request.input(name="", email="", password="")
    name = input.name.strip()
    email = input.email.strip().lower()
    password = input.password
    logging.info("api_register_user(): " + email)
    if not name:
        raise ApiValueError("name", "Invalid name")
    if not email or not _REG_EMAIL.match(email):
        raise ApiValueError("email", "Invalid email")
    if not password or not _REG_MD5.match(password):
        raise ApiValueError("password", "Invalid password")

    user = User.find_first("where email=?", email)
    if user:
        raise ApiError("register failed", "email", "Email is already in use.")
    else:
        user = User(name=name, email=email, password=password, image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email).hexdigest())
        user.insert()
    return user

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