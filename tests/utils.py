import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from srcf.database import MailHandler, Member, Session, Society, queries


def create_test_session() -> Session:
    """
    Populate a test replica of the sysadmins' membership databases, and connect the default session
    for `srcf.database.queries`.
    
    Reserves the CRSid `spqr2` and the society short name `srcf`.
    """
    url = os.getenv("TEST_DB_URL")
    if not url:
        raise unittest.SkipTest("Requires test database, must set TEST_DB_URL")
    engine = create_engine(url)
    Session = sessionmaker(bind=engine)
    sess = Session()
    queries.disable_automatic_session(sess)
    if list(queries.list_members(sess)) or list(queries.list_societies(sess)):
        raise unittest.SkipTest("Test member database is not empty")
    mem = Member(crsid="spqr2", preferred_name="Preferred Names", surname="Surname",
                 email="sysadmins-python-unittest@srcf.net", mail_handler=MailHandler.forward.name,
                 member=True, user=True)
    sess.add(mem)
    soc = Society(society="srcf", description="Student-Run Computing Facility",
                  role_email="sysadmins-python-unittest@srcf.net")
    soc.admins.add(mem)
    sess.add(soc)
    sess.commit()
    return sess


def destroy_test_session(sess: Session) -> None:
    """
    Removes the member and society records auto-generated in `create_test_session`, and reverts the
    global session to the default state.
    """
    soc = queries.get_society("srcf", sess)
    mem = queries.get_member("spqr2", sess)
    soc.admins.remove(mem)
    sess.delete(soc)
    sess.delete(mem)
    sess.commit()
    queries._global_session = None
    queries._auto_create_global_session = True
