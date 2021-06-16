from datetime import datetime
import unittest

from srcf.database import MailHandler, Member, Session, Society, queries

from .utils import create_test_session, destroy_test_session


sess: Session


def setUpModule():
    global sess
    sess = create_test_session()


def tearDownModule():
    destroy_test_session(sess)


class TestDatabase(unittest.TestCase):
    
    def setUp(self):
        self.now = datetime.now().strftime("%Y%m%d%H%M%S")
        sess.begin()
        
    def tearDown(self):
        sess.rollback()

    def test_create_member(self):
        crsid = "spqr3"
        preferred_name = "Preferred Names {}".format(self.now)
        surname = "Surname {}".format(self.now)
        email = "sysadmins-python-unittest-{}@srcf.net".format(self.now)
        mem = Member(crsid=crsid, preferred_name=preferred_name, surname=surname, email=email,
                     mail_handler=MailHandler.forward.name, member=True, user=True)
        sess.add(mem)
        sess.flush()
        got = queries.get_member(crsid, sess)
        self.assertIs(mem, got)
        self.assertIsNotNone(mem.uid)
        self.assertIsNotNone(mem.gid)
        self.assertTrue(mem.member)
        self.assertTrue(mem.user)

    def test_create_society(self):
        name = "test"
        description = "Test Society {}".format(self.now)
        role_email = "sysadmins-python-unittest-{}@srcf.net".format(self.now)
        soc = Society(society=name, description=description, role_email=role_email)
        sess.add(soc)
        sess.flush()
        got = queries.get_society(name, sess)
        self.assertIs(soc, got)
        self.assertIsInstance(soc.uid, int)
        self.assertIsInstance(soc.gid, int)


if __name__ == "__main__":
    unittest.main()
