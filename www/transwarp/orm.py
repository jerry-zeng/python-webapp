#coding=utf-8

import logging, time
import db

class Field(object):
    _count = 0

    def __init__(self, **kw):
        self.name = kw.get("name", None)
        self._default = kw.get("default", None)
        self.primary_key = kw.get("primary_key", False)
        self.nullable = kw.get("nullable", False)
        self.updatable = kw.get("updatable", True)
        self.insertable = kw.get("insertable", True)
        self.ddl = kw.get("ddl", "")
        self._order = Field._count

        Field._count = Field._count + 1

    @property
    def default(self):
        d = self._default
        return d() if callable(d) else d

    def __str__(self):
        s = ["<%s:%s, %s,default(%s)," % (self.__class__.__name__, self.name, self.ddl, self._default)]
        self.nullable and s.append("N")
        self.updatable and s.append("U")
        self.insertable and s.append("I")
        s.append(">")
        return "".join(s)

class StringField(Field):
    def __init__(self, **kw):
        if not "default" in kw:
            kw["default"] = ""
        if not "ddl" in kw:
            kw["ddl"] = "varchar(255)"
        super(StringField, self).__init__(**kw)

class IntegerField(Field):
    def __init__(self, **kw):
        if not "default" in kw:
            kw["default"] = 0
        if not "ddl" in kw:
            kw["ddl"] = "bigint"
        super(IntegerField, self).__init__(**kw)

class FloatField(Field):
    def __init__(self, **kw):
        if not "default" in kw:
            kw["default"] = 0.0
        if not "ddl" in kw:
            kw["ddl"] = "real"
        super(FloatField, self).__init__(**kw)

class BooleanField(Field):
    def __init__(self, **kw):
        if not "default" in kw:
            kw["default"] = False
        if not "ddl" in kw:
            kw["ddl"] = "bool"
        super(BooleanField, self).__init__(**kw)

class TextField(Field):
    def __init__(self, **kw):
        if not "default" in kw:
            kw["default"] = ""
        if not "ddl" in kw:
            kw["ddl"] = "text"
        super(TextField, self).__init__(**kw)

class BlobField(Field):
    def __init__(self, **kw):
        if not "default" in kw:
            kw["default"] = ""
        if not "ddl" in kw:
            kw["ddl"] = "blob"
        super(BlobField, self).__init__(**kw)

class VersionField(Field):
    def __init__(self, **kw):
        if not "default" in kw:
            kw["default"] = 0
        if not "ddl" in kw:
            kw["ddl"] = "bigint"
        if not "name" in kw:
            kw["name"] = None
        super(VersionField, self).__init__(**kw)


_triggers = frozenset(['pre_insert', 'pre_update', 'pre_delete'])

def _gen_table_sql(table_name, fieldMap):
    primary_key = None
    sql = [ '-- generating SQL for %s:' % table_name ]
    sql.append( 'create table `%s` (' % table_name )

    for f in sorted(fieldMap.values(), lambda x,y: cmp(x._order, y._order)):
        if not hasattr(f, "ddl"):
            raise StandardError('no ddl in field "%s".' % f.name)
        ddl = f.ddl
        nullable = f.nullable
        if f.primary_key:
            primary_key = f.name
        prop = nullable and '  `%s` %s,' % (f.name, ddl) or '  `%s` %s not null,' % (f.name, ddl)
        sql.append(prop)

    sql.append("  primary key(`%s`)" % primary_key)
    sql.append(");")

    return "\n".join(sql)


class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        if name == "Model":
            return type.__new__(cls, name, bases, attrs)

        if not hasattr(cls, 'subclasses'):
            cls.subclasses = {}

        if not name in cls.subclasses:
            cls.subclasses[name] = name
        else:
            logging.warning("Re-define class %s" % name)

        # 遍历所有类的属性.
        mappings = dict()
        primary_key = None

        for k,v in attrs.iteritems():
            if isinstance(v, Field):
                if not v.name:
                    v.name = k

                if v.primary_key:
                    if primary_key:
                        raise TypeError('Cannot define more than 1 primary key in class: %s' % name)
                    if v.updatable:
                        v.updatable = False
                    if v.nullable:
                        v.nullable = False
                    primary_key = v

                mappings[k] = v

        if not primary_key:
            raise TypeError('Primary key not defined in class: %s' % name)

        for k in mappings.iterkeys():
            attrs.pop(k)

        # attrs["__table__"] = cls.__table__
        if not '__table__' in attrs:
            attrs['__table__'] = name.lower()

        attrs["__mappings__"] = mappings
        attrs["__primary_key__"] = primary_key

        attrs["__sql__"] = lambda self: _gen_table_sql(attrs['__table__'], mappings)

        for t in _triggers:
            if not t in attrs:
                attrs[t] = None

        return type.__new__(cls, name, bases, attrs)


class Model(dict):
    __metaclass__ = ModelMetaclass

    def __init__(self, **kw):
        super(Model,self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no key '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def insert(self):
        self.pre_insert and self.pre_insert()

        params = {}
        for k,v in self.__mappings__.iteritems():
            if v.insertable:
                if not hasattr(self, k):
                    setattr(self, k, v.default)
                params[v.name] = getattr(self, k)

        db.insert("%s" % self.__table__, **params)

        return self

    def delete(self):
        self.pre_delete and self.pre_delete()

        pk = self.__primary_key__.name
        params = {}
        params[pk] = getattr(self, pk)
        db.delete("%s" % self.__table__, **params)

        return self

    def update(self):
        self.pre_update and self.pre_update()

        keys = []
        args = []

        for k, v in self.__mappings__.iteritems():
            if v.updatable:
                if not hasattr(self, k):
                    setattr(self, k, v.default)

                arg = getattr(self, k)
                keys.append("`%s`=?" % k)
                args.append(arg)

        changes = ",".join(keys)
        pk = self.__primary_key__.name
        args.append( getattr(self, pk) )
        db.update("update %s set %s where %s=?" % (self.__table__, changes, pk), *args)

        return self


    @classmethod
    def get(cls, pk):
        d = db.select_one("select * from %s where %s=?" % (cls.__table__, cls.__primary_key__.name), pk)
        return cls(**d) if d else None

    @classmethod
    def find_first(cls, where, *args):
        d = db.select_one("select * from %s %s" % (cls.__table__, where), *args)
        return cls(**d) if d else None

    @classmethod
    def find_all(cls):
        l = db.select("select * from %s" % cls.__table__)
        return [cls(**d) for d in l]

    @classmethod
    def find_by(cls, where, *args):
        l = db.select("select * from %s %s" % (cls.__table__, where), *args)
        return [cls(**d) for d in l]

    @classmethod
    def count_all(cls):
        pk = cls.__primary_key__.name
        return db.select_int("select count(`%s`) from %s" %(pk, cls.__table__))

    @classmethod
    def count_by(cls, where, *args):
        pk = cls.__primary_key__.name
        return db.select_int("select count(`%s`) from %s %s" % (pk, cls.__table__, where), *args)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    db.create_engine('root', 'root', '127.0.0.1', '3306', 'mytest')
    db.update('drop table if exists user')
    db.update('create table user (ID int primary key, Name text, Email text, Password text, Last_Modified real)')
    import doctest
    doctest.testmod()
