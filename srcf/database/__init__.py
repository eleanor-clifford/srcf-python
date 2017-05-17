import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


__all__ = ["Member", "Society", "PendingAdmin",
           "RESTRICTED", "assert_readwrite", "Session"]

from .schema import RESTRICTED, POSTGRES_USER
from .schema import Member, Society, PendingAdmin
from .schema import LogLevel, LogRecord, Domain, HTTPSCert, JobState, Job

class RestrictedAccess(RuntimeError):
    def __init__(self):
        super(RestrictedAccess, self).__init__(
                "Don't have write access to the membership database")

def assert_readwrite():
    if RESTRICTED:
        raise RestrictedAccess

# try and use a privileged user if we can, otherwise read only
engine = create_engine("postgresql://{user}@postgres.internal/sysadmins".format(user=POSTGRES_USER))
Session = sessionmaker(bind=engine)
