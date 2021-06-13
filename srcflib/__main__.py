import code
import logging
import warnings

from srcf.database import Member, Society, MailHandler
from srcf.database.queries import get_member, get_society  # noqa: F401

from srcflib import email, plumbing as p  # noqa: F401
from srcflib.plumbing.common import *  # noqa: F401, F403
from srcflib.tasks import mailman, membership, mysql, pgsql  # noqa: F401


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    code.interact(local=globals())
