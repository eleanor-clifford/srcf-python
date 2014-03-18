import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


__all__ = ["Member", "Society", "RESTRICTED", "assert_readwrite", "Session"]

from .schema import RESTRICTED, Member, Society

class RestrictedAccess(RuntimeError):
    def __init__(self):
        super(RestrictedAccess, self).__init__(
                "Don't have write access to the membership database")

def assert_readwrite():
    if RESTRICTED:
        raise RestrictedAccess

if not RESTRICTED:
    engine = create_engine("postgresql://root@/sysadmins")
else:
    engine = create_engine("postgresql://nobody@/sysadmins")

Session = sessionmaker(bind=engine)
