import os
import re
import pwd
from ldap3 import Server, Connection, ALL, ALL_ATTRIBUTES
import stat
import shutil
import configparser
import pymysql
import posix1e


__all__ = ["email_re", "ldapsearch", "is_admin", "mysql_conn"]


# yeah whatever.
email_re = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z][A-Za-z]+$")


# LDAP helper
def ldapsearch(crsid):
    server = Server('ldap.lookup.cam.ac.uk', get_info=ALL)
    conn = Connection(server, auto_bind=True)
    conn.search('ou=people, o=University of Cambridge,dc=cam,dc=ac,dc=uk', '(uid={0})'.format(crsid), attributes=ALL_ATTRIBUTES)
    r = conn.entries

    if len(r) != 1:
        raise KeyError(crsid)
    return r[0]


def is_admin(member):
    for soc in member.societies:
        if soc.society == "srcf-admin":
            return True
    return False


mysql_passwd = None

def mysql_conn():
    global mysql_passwd
    if not mysql_passwd:
        my_cnf = configparser.ConfigParser()
        my_cnf.read("/societies/srcf-admin/.my.cnf")
        mysql_passwd = my_cnf.get('client', 'password')
    conn = pymysql.connect(user="srcf_admin", db="srcf_admin", passwd=mysql_passwd)
    conn.autocommit = True
    return conn


def is_valid_socname(s):
    return re.match(r'^[a-z0-9_-]+$', s)


# Copy a tree, overriding the owner, group and permissions
# (for installing /etc/skel into homedirs)
# "Inspired by" (an antique version of) shutil.copytree but:
#  -  Errors are immediately fatal
#  -  The destination directory must already exist
# /!\ User permissions are copied to group permissions
def copytree_chown_chmod(src, dst, uid, gid):
    for name in os.listdir(src):
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        linkto = None
        if os.path.islink(srcname):
            linkto = os.readlink(srcname)
            os.symlink(linkto, dstname)
        elif os.path.isdir(srcname):
            os.mkdir(dstname)
            copytree(srcname, dstname, symlinks)
        else:
            shutil.copy(srcname, dstname)
        # The rest is "inspired by" shutil.copystat...
        # (but doesn't handle xattrs or flags because we don't need that)
        os.chown(dstname, uid, gid, follow_symlinks=False)
        st = os.stat(srcname, follow_symlinks=False)
        os.utime(dstname, ns=(st.st_atime_ns, st.st_mtime_ns), follow_symlinks=False)
        if linkto is None:
            mode = stat.S_IMODE(st.st_mode)
            # Copy user mode bits to group mode
            mode = (mode & 0o7707) | ((mode & 0o0700) >> 3)
            os.chmod(dstname, mode)

