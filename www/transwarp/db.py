#coding=utf-8

import threading, functools
import time, uuid, logging
import mysql.connector

def next_id(t=None):
    '''
    Return next id as 50-char string.
    Args:
        t: unix timestamp, default to None and using time.time().
    '''
    if t is None:
        t = time.time()
    return '%015d%s000' % (int(t * 1000), uuid.uuid4().hex)

class DBError(Exception):
    pass

class MultiColumnsError(DBError):
    pass

class Dict(dict):
    def __init__(self, names, values, **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except:
            return None

    def __setattr__(self, key, value):
        self[key] = value

class _Engine():
    def __init__(self, connect):
        self._connect = connect

    def connect(self):
        return self._connect()

_engine = None

def create_engine(user, password, host, port, database, **kw):
    global _engine
    if _engine is None:
        params = dict(user=user, password=password, host=host, port=port, database=database)
        defualts = dict(use_unicode=True, charset='utf8', collation='utf8_general_ci', autocommit=False)
        for k,v in defualts.iteritems():
            params[k] = kw.pop(k, v)
        params.update(kw)
        params["buffered"] = True  #important
        _engine = _Engine(lambda: mysql.connector.connect(**params))
    else:
        raise DBError("engine is already initialized.")


class _DbCtx(threading.local):
    def __init__(self):
        self.connection = None
        self.transactions = 0

    def is_init(self):
        return not self.connection is None

    def init(self):
        if self.connection is None:
            global _engine
            self.connection = _engine.connect()

    def cursor(self):
        self.init()
        return self.connection.cursor()

    def commit(self):
        self.init()
        try:
            self.connection.commit()
        except:
            self.connection.rollback()
            raise

    def rollback(self):
        self.init()
        self.connection.rollback()

    def close(self):
        if not self.connection is None:
            self.connection.close()
        self.connection = None

_db_ctx = _DbCtx()


class _ConnectionCtx():
    def __enter__(self):
        global _db_ctx
        self.should_cleanup = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_cleanup = True

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _db_ctx
        if self.should_cleanup == True:
            _db_ctx.close()

def _connection():
    return _ConnectionCtx()

def _with_connection(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        with _connection():
            return func(*args, **kw)
    return wrapper


class _TransactionCtx():
    def __enter__(self):
        global _db_ctx
        self.should_close_conn = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_close_conn = True
        _db_ctx.transactions = _db_ctx.transactions + 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _db_ctx
        _db_ctx.transactions = _db_ctx.transactions - 1
        try:
            if _db_ctx.transactions == 0:
                if exc_type is None:
                    _db_ctx.commit()
                else:
                    _db_ctx.rollback()

        finally:
            if self.should_close_conn == True:
                _db_ctx.close()

def _transaction():
    return _TransactionCtx()

def _with_transaction(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        with _transaction():
            return func(*args, **kw)
    return wrapper


def __handle_sql(sql):
    if sql is None:
        return sql
    return sql.replace("?", "%s")

def _select(sql, first, *args):
    global _db_ctx
    cursor = None
    sql = __handle_sql(sql)
    try:
        cursor = _db_ctx.cursor()
        cursor.execute(sql, args)

        if cursor.description:
            keys = [k[0] for k in cursor.description]

            if first:
                values = cursor.fetchone()
                cursor.close()
                if not values:
                    return None
                return Dict(keys, values)
            else:
                values = cursor.fetchall()
                return [Dict(keys, value) for value in values]

        return None
    finally:
        if cursor:
            cursor.close()

@_with_connection
def select_int(sql, *args):
    d = _select(sql, True, *args)
    if len(d) > 1:
        raise MultiColumnsError("Expect only one column.")
    return d.values()[0]

@_with_connection
def select_one(sql, *args):
    return _select(sql, True, *args)

@_with_connection
def select(sql, *args):
    r'''
    select * from %s where %s [order by %s ASC|DESC]
    '''
    return _select(sql, False, *args)


def _update(sql, *args):
    global _db_ctx
    cursor = None
    sql = __handle_sql(sql)
    try:
        cursor = _db_ctx.cursor()
        cursor.execute(sql, args)
        r = cursor.rowcount

        if _db_ctx.transactions == 0:
            _db_ctx.commit()

        return r
    finally:
        if cursor:
            cursor.close()

@_with_connection
def update(sql, *args):
    r'''
    update('update user set password=? where id=?', '***', '123\' or id=\'456')
    '''
    return _update(sql, *args)

@_with_connection
def insert(table, **kw):
    r'''
    insert into `%s` (%s) values (%s)
    '''
    cols, args = zip(*kw.iteritems())
    keys = ','.join( ['`%s`' % col for col in cols] )
    values = ','.join( ['?' for i in range(len(cols))] )
    sql = 'insert into `%s` (%s) values (%s)' % (table, keys, values)
    return _update(sql, *args)

@_with_connection
def delete(table, **kw):
    r'''
    delete from `%s` where %s
    '''
    cols, args = zip(*kw.iteritems())
    conditions = " and ".join(["%s=?" % col for col in cols])
    sql = 'delete from `%s` where %s' % (table, conditions)
    return _update(sql, *args)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    create_engine('root', 'root', '127.0.0.1', '3306', 'mytest')
    update('drop table if exists user')
    update('create table user (ID int primary key, Name text, Email text, Password text, Last_Modified real)')
    import doctest
    doctest.testmod()