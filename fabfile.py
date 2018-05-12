#coding=utf-8

import os, re
from datetime import datetime

from fabric.api import *

db_user = "root"
db_password = "jiangfeng"

current_user = "root"
app_name = "awesome"

env.user = "root"
env.sudo_user = "root"
env.host = "139.196.136.157"

_TAR_FILE = "dist-awesome.tar.gz"

_REMOTE_TMP_TAR = '/tmp/%s' % _TAR_FILE
_REMOTE_BASE_DIR = "/srv/awesome"

REG_FILES = re.compile('\r?\n')

def _current_path():
    return os.path.abspath(".")

def _now():
    return datetime.now().strftime('%y-%m-%d_%H.%M.%S')


#---------------------------------------------------------------
# 重启服务器.
def _restart_server():
    with settings(warn_only=True):
        sudo("supervisorctl stop %s" % app_name)
        sudo("supervisorctl start %s" % app_name)
        sudo("/etc/init.d/nginx reload")

# 打包.
def pack():
    '''
    Build dist package.
    '''
    # remove old tar file
    local("rm -f dist/%s" % _TAR_FILE)

    # cd to www folder
    with lcd( os.path.join(_current_path(), "www") ):
        includes = ["static", "templates", "transwarp", "*.ico", "*.py"]
        excludes = ["test", ".*", "*.pyc", "*.pyo"]

        cmd = ["tar", "--dereference", "-czvf", "../dist/%s" % _TAR_FILE]
        cmd.extend( ["--exclude=\'%s\'" % ex for ex in excludes] )
        cmd.extend(includes)
        cmdStr = " ".join(cmd)
        print cmdStr

        local(cmdStr)

# 发布.
def deploy():
    '''
    upload local tar file to server, and restart server
    '''
    # remove old tar file
    run("rm -f %s" % _REMOTE_TMP_TAR)
    # upload local tar file to remove tmp folder
    put("dist/%s" % _TAR_FILE, _REMOTE_TMP_TAR)
    # create new folder
    newDir = "www-%s" % _now()
    with cd(_REMOTE_BASE_DIR):
        sudo("mkdir %s" % newDir)
    # uncompress tar file to new folder
    with cd("%s/%s" % (_REMOTE_BASE_DIR, newDir)):
        sudo("tar -xzvf %s" % _REMOTE_TMP_TAR)
    # reset link
    with cd(_REMOTE_BASE_DIR):
        sudo("rm -f www")
        sudo("ln -s %s www" % newDir)
        sudo("chown %s:%s www" % (current_user, current_user))
        sudo("chown -R %s:%s %s" % (current_user, current_user, newDir))
    # restart python and nginx server
    _restart_server()

# 回滚.
def rollback():
    '''
    rollback to previous version
    '''
    with cd(_REMOTE_BASE_DIR):
        r = run("ls -l -p")

        files = []
        for s in REG_FILES.split(r):
            if s.startswith("www-") and s.endswith("/"):
                files.append( s[:-1] )
        files.sort(cmp=lambda s1,s2: 1 if s1 < s2 else -1)

        r = run("ls -l www")
        ss = r.split(" -> ")
        if len(ss) != 2:
            print ('ERROR: \'www\' is not a symbol link.')
            return

        currentV = ss[1]
        print ('Found current symbol link points to: %s\n' % currentV)

        try:
            index = files.index(currentV)
        except ValueError:
            print('ERROR: symbol link is invalid.')
            return

        if len(files) == index + 1:
            print('ERROR: already the oldest version.')
        preV = files[index + 1]

        print ('==================================================')
        for f in files:
            if f == currentV:
                print ('      Current ---> %s' % currentV)
            elif f == preV:
                print ('  Rollback to ---> %s' % preV)
            else:
                print ('                   %s' % f)
        print ('==================================================')

        print ('')
        boo = raw_input("continue? Y/N")
        if boo != "y" and boo != "Y":
            print("Rollback canceled")
            return

        print("Start rollback...")
        sudo('rm -f www')
        sudo("ln -s %s www" % preV)
        sudo("chown %s:%s www" % (current_user, current_user))

        # restart python and nginx server
        _restart_server()

        print ('Rollback ok')

# 备份.
def backup():
    '''
    Dump entire database on server and backup to local as the tar file.
    '''
    # backup sql file
    fi = "backup-%s-%s.sql" % (app_name, _now())

    with cd("/tmp"):
        # dump sql
        run('mysqldump --user=%s --password=%s --skip-opt --add-drop-table --default-character-set=utf8 --quick awesome > %s' % (
            db_user, db_password, fi))
        # zip sql file
        run("tar -czvf %s.tar.gz %s" % (fi, fi))
        # download to local folder
        get("%s.tar.gz" % fi, "%s/backup/" % _current_path())
        # remove sql file
        run("rm -f %s" % fi)
        # remove sql tar file
        run("rm -f %s.tar.gz" % fi)

# 解析备份文件.
def restore2local():
    '''
    restore backup tar sql file to local
    '''
    backup_dir = os.path.join(_current_path(), "backup")
    # list backup files
    fs = os.listdir(backup_dir)
    files = []
    for s in fs:
        if s.startswith("backup-") and s.endswith(".sql.tar.gz"):
            files.append(s)
    files.sort(cmp=lambda s1, s2: 1 if s1 < s2 else -1)

    if len(files)==0:
        print('No backup files found.')
        return

    print ('==================================================')
    n = 0
    for f in files:
        print ('%s: %s' % (n, f))
        n = n + 1
    print ('==================================================')

    print ('')
    # Select an index of file to restore
    try:
        index = int(raw_input('Select an index of file to restore: '))
    except ValueError:
        print ('Invalid file index.')
        return

    restore_file = files[index]

    boo = raw_input("Restore the file: %s? Y/N" % restore_file)
    if boo != "y" and boo != "Y":
        print("Restore canceled")
        return

    print('Start to restore to local database...')
    pswd = raw_input("Input mysql root's password: ")
    sqls = [
        'drop database if exists awesome;',
        'create database awesome;',
        'grant select, insert, update, delete on awesome.* to \'%s\'@\'localhost\' identified by \'%s\';' % (
        db_user, db_password)
    ]
    for sql in sqls:
        local(r'mysql -u root -p %s -e "%s"' % (pswd, sql))

    # uncompress tar sql file
    with lcd(backup_dir):
        local('tar zxvf %s' % restore_file)
    # load sql file
    local(r'mysql -u root -p %s awesome < backup/%s' % (pswd, restore_file[:-7]))
    # remove sql file
    with lcd(backup_dir):
        local('rm -f %s' % restore_file[:-7])