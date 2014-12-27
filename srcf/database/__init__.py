import os
import getpass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


__all__ = ["Member", "Society", "PendingAdmin",
           "RESTRICTED", "assert_readwrite", "Session"]

from .schema import RESTRICTED, Member, Society, PendingAdmin
from .schema import LogLevel, LogRecord, JobState, Job

class RestrictedAccess(RuntimeError):
    def __init__(self):
        super(RestrictedAccess, self).__init__(
                "Don't have write access to the membership database")

def assert_readwrite():
    if RESTRICTED:
        raise RestrictedAccess

if os.uname()[1] == "pip":
    _host = ""
else:
    _host = "pip.internal"

# try and use a privileged user if we can, otherwise read only
_user = getpass.getuser()
if _user not in ("root", "srcf-admin"):
    _user = "nobody"

engine = create_engine("postgresql://{user}@{host}/sysadmins".format(host=_host, user=_user))
Session = sessionmaker(bind=engine)