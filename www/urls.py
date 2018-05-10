#coding=utf-8

import os, re, time, base64, hashlib, logging
import markdown2

from transwarp.web import get, post, view, interceptor, ctx, seeOther, notFound
from models import User, Blog, Comment
from apis import api, ApiError, ApiValueError, ApiPermissionError, ApiResourceNotFoundError, Page
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

def check_admin():
    user = ctx.request.user
    if user and user.admin:
        return
    raise ApiPermissionError("Only admin can do the action.")

def _get_page_index():
    page_index = 1
    try:
        page_index = int( ctx.request.get("page", "1") )
    except ValueError:
        pass
    return page_index

def _get_page_size():
    page_size = 10
    try:
        page_size = int(ctx.request.get("size", "10"))
    except ValueError:
        pass
    return page_size

def _get_blogs_by_page():
    total = Blog.count_all()
    page = Page(total, _get_page_index(), _get_page_size())
    blogs = Blog.find_by("order by created_at desc limit ?,?", page.offset, page.limit)
    return blogs, page

def _get_users_by_page():
    total = User.count_all()
    page = Page(total, _get_page_index(), _get_page_size())
    users = User.find_by("order by created_at desc limit ?,?", page.offset, page.limit)
    return users, page

def _get_comments_by_page(blog_id=None):
    total = Comment.count_all()
    page = Page(total, _get_page_index(), _get_page_size())
    comments = None
    if blog_id:
        comments = Comment.find_by("where blog_id=? order by created_at desc limit ?,?", blog_id, page.offset, page.limit)
    else:
        comments = Comment.find_by("order by created_at desc limit ?,?", page.offset, page.limit)

    for c in comments:
        blog = Blog.get(c.blog_id)
        if blog:
            c.blog_title = blog.title

    return comments, page

#------------------------------Logic------------------------------
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
    if user:
        return next()
    raise seeOther("/signin")


@view("blogs.html")
@get("/")
def index():
    blogs, page = _get_blogs_by_page()
    user = ctx.request.user
    return dict(blogs=blogs, page=page, user=user)

@view("blog_detail.html")
@get("/blogs/:blog_id")
def get_blog(blog_id):
    blog = Blog.get(blog_id)
    if blog is None:
        raise notFound()

    blog.html_content = markdown2.markdown(blog.content)
    comments = Comment.find_by("where blog_id=? order by created_at desc limit 100", blog_id)
    return dict(blog=blog, comments=comments, user=ctx.request.user)

@view("manage_blog_edit.html")
@get("/manage/blogs/create")
def manage_blog_create():
    return dict(id=None, action="/api/blogs", redirect="/manage/blogs", user=ctx.request.user)

@view("manage_blog_edit.html")
@get("/manage/blogs/edit/:blog_id")
def manage_blog_edit(blog_id):
    blog = Blog.get(blog_id)
    if blog is None:
        raise notFound()
    return dict(id=blog.id, title=blog.title, summary=blog.summary, content=blog.content,
                action="/api/blogs/%s"%blog_id, redirect="/manage/blogs",
                user=ctx.request.user)

@view("manage_blog_list.html")
@get("/manage/blogs")
def manage_blogs():
    return dict(page_index=_get_page_index(), user=ctx.request.user)


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


@get('/manage/')
def manage_index():
    raise seeOther('/manage/blogs')


@view("manage_comment_list.html")
@get("/manage/comments")
def manage_comments():
    return dict(page_index=_get_page_index(), user=ctx.request.user)


@view("manage_user_list.html")
@get("/manage/users")
def manage_users():
    return dict(page_index=_get_page_index(), user=ctx.request.user)

#------------------------------Api------------------------------

_REG_EMAIL = re.compile(r"^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$")
_REG_MD5 = re.compile(r"^[0-9a-f]{32}$")


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

    user.last_login = time.time()
    user.update()

    # make session cookie:
    max_age = 3600
    if remember == "true" or remember == "True":
        max_age = 7 * 86400

    cookie = make_signed_cookie(user.id, user.password, max_age)
    ctx.response.set_cookie(_COOKIE_NAME, cookie, max_age=max_age)

    user.password = "******"
    return user

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
        user.last_login = time.time()
        user.insert()
    return user

@api
@get("/api/users")
def api_get_users():
    users, page = _get_users_by_page()
    for u in users:
        u.password = "******"
    return dict(users=users, page=page)


@api
@post("/api/blogs")
def api_create_blog():
    input = ctx.request.input(title="", summary="", content="")
    title = input.title.strip()
    summary = input.summary.strip()
    content = input.content.strip()

    if not title:
        raise ApiValueError("title", "title can't be empty.")
    if not summary:
        raise ApiValueError("summary", "summary can't be empty.")
    if not content:
        raise ApiValueError("content", "content can't be empty.")

    user = ctx.request.user
    blog = Blog(title=title, summary=summary, content=content, user_id=user.id, user_name=user.name, user_image=user.image)
    blog.insert()
    return blog

@api
@get("/api/blogs")
def api_get_blogs():
    blogs, page = _get_blogs_by_page()
    format = ctx.request.get("format", "")
    if format == "html":
        for blog in blogs:
            blog.content = markdown2.markdown(blog.content)
    return dict(blogs=blogs, page=page)

@api
@get("/api/blogs/:blog_id")
def api_get_blog(blog_id):
    blog = Blog.get(blog_id)
    if blog:
        return blog
    raise ApiResourceNotFoundError("Blog")

@api
@post("/api/blogs/:blog_id")
def api_update_blog(blog_id):
    input = ctx.request.input(title="", summary="", content="")
    title = input.title.strip()
    summary = input.summary.strip()
    content = input.content.strip()

    if not title:
        raise ApiValueError("title", "title can't be empty.")
    if not summary:
        raise ApiValueError("summary", "summary can't be empty.")
    if not content:
        raise ApiValueError("content", "content can't be empty.")

    blog = Blog.get(blog_id)
    if blog is None:
        raise ApiResourceNotFoundError("Blog")

    blog.title = title
    blog.summary = summary
    blog.content = content
    blog.update()

    return blog

@api
@post("/api/blogs/:blog_id/delete")
def api_delete_blog(blog_id):
    blog = Blog.get(blog_id)
    if blog is None:
        raise ApiResourceNotFoundError("Blog")
    blog.delete()
    return dict(id=blog_id)


@api
@post("/api/blogs/:blog_id/comments")
def api_create_blog_comment(blog_id):
    user = ctx.request.user
    if user is None:
        raise ApiPermissionError("Need signin.")
    blog = Blog.get(blog_id)
    if blog is None:
        raise ApiResourceNotFoundError("Blog")

    input = ctx.request.input(content="")
    content = input.content.strip()
    if not content:
        raise ApiValueError("content")

    c = Comment(blog_id=blog_id, user_id=user.id, user_name=user.name, user_image=user.image, content=content)
    c.insert()

    blog.latest_reply = time.time()

    return dict(comment=c)

@api
@get("/api/blogs/:blog_id/comments")
def api_get_blog_comments(blog_id):
    comments, page = _get_comments_by_page(blog_id)
    return dict(comments=comments, page=page)

@api
@get("/api/comments")
def api_get_comments():
    comments, page = _get_comments_by_page()
    return dict(comments=comments, page=page)

@api
@post("/api/comments/:comment_id/delete")
def api_delete_comments(comment_id):
    comment = Comment.get(comment_id)
    if comment is None:
        raise ApiResourceNotFoundError("Comment")
    comment.delete()
    return dict(id=comment_id)