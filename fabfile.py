#coding=utf-8

import os, re
from datetime import datetime

from fabric import Connection

db_user = "root"
db_password = "jiangfeng"

conn = Connection(host="139.196.136.157", user="root" )


_TAR_FILE = "dist-awesome.tar.gz"

_REMOTE_TAR_FILE = '/tmp/%s' % _TAR_FILE

_REMOTE_BASE_DIR = "/srv/awesome"

REG_FILES = re.compile('\r?\n')

def _current_path():
    return os.path.abspath(".")

def _now():
    return datetime.now().strftime('%y-%m-%d_%H.%M.%S')


#---------------------------------------------------------------

# 打包.
def pack():
    '''
    Build dist package.
    '''

    # remove old tar file
    conn.local("rm -f dist/%s" % _TAR_FILE)

    # cd to www folder
    conn.cd( os.path.join(_current_path(), "www") )
    # {
    includes = ["static", "templates", "transwarp", "favico.ico", "*.py"]
    excludes = ["test", ".*", "*.pyc", "*.pyo"]
    cmd = ["tar", "--dereference", "-czvf", "../dist/%s" % _TAR_FILE]
    cmd.extend( ["--exclude=\'%s\'" % ex for ex in excludes] )
    cmd.extend(includes)
    cmdStr = " ".join(cmd)
    print cmdStr

    conn.local(cmdStr)
    # }

# 发布.
def deploy():
    pass

# 备份.
def backup():
    pass

# 回滚.
def rollback():
    pass


def restore2local():
    pass