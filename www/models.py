#coding=utf-8

from transwarp.db import next_id
from transwarp.orm import Model, StringField, IntegerField, TextField, BooleanField, FloatField
import time

class User(Model):
    __table__ = "user"

    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)")
    name = StringField(ddl="varchar(50)")
    password = StringField(ddl="varchar(50)")
    admin = BooleanField()
    email = StringField(updatable=False, ddl="varchar(50)")
    image = StringField(ddl="varchar(500)")
    created_at = FloatField(updatable=False, default=time.time)
    last_login = FloatField()

class Blog(Model):
    __table__ = "blog"

    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)")
    user_id = StringField(updatable=False, ddl="varchar(50)")
    user_name = StringField(ddl="varchar(50)")
    user_image = StringField(ddl="varchar(500)")
    title = StringField(ddl="varchar(50)")
    summary = StringField(ddl="varchar(200)")
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)
    latest_reply = FloatField()

class Comment(Model):
    __table__ = "comment"

    id = StringField(primary_key=True, default=next_id, ddl="varchar(50)")
    blog_id = StringField(updatable=False, ddl="varchar(50)")
    blog_title = StringField(ddl="varchar(50)")
    user_id = StringField(updatable=False, ddl="varchar(50)")
    user_name = StringField(ddl="varchar(50)")
    user_image = StringField(ddl="varchar(500)")
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)
