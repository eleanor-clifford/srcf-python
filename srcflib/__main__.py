import code
import logging

from srcf.database import Session, Member, Society, MailHandler
from srcf.database import queries as q

from srcflib import email, plumbing as p
from srcflib.plumbing.common import *
from srcflib.tasks import mailman, membership, mysql, pgsql


sess = Session()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    code.interact(local=globals())
