from inspect import cleandoc
import unittest

from srcf.database import Session, queries

from srcflib.scripts.utils import ENTRYPOINTS

from .scripts import no_args, with_member_society, with_owner
from .utils import create_test_session, destroy_test_session


sess: Session


def setUpModule():
    global sess
    sess = create_test_session()


def tearDownModule():
    destroy_test_session(sess)


class TestScripts(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.mem = queries.get_member("spqr2", sess)
        cls.soc = queries.get_society("unittest", sess)

    def test_entrypoints(self):
        self.assertIn("srcflib-scripts-no-args=tests.scripts:no_args", ENTRYPOINTS)

    def test_doc(self):
        self.assertEqual(cleandoc(no_args.__doc__), "Usage: srcflib-scripts-no-args")

    def test_args_member_society(self):
        member, society = with_member_society({"MEMBER": self.mem.crsid,
                                               "SOCIETY": self.soc.society})
        self.assertEqual(member, self.mem)
        self.assertEqual(society, self.soc)

    def test_args_owner_member(self):
        member = with_owner({"OWNER": self.mem.crsid})
        self.assertEqual(member, self.mem)

    def test_args_owner_society(self):
        society = with_owner({"OWNER": self.soc.society})
        self.assertEqual(society, self.soc)


if __name__ == "__main__":
    unittest.main()
