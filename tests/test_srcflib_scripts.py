from inspect import cleandoc
import unittest
from unittest.mock import Mock

from srcf.database import Member, Society, queries

_member = Member(crsid="spqr2")
_society = Society(society="test")

def _get_member(crsid):
    if crsid != _member.crsid:
        raise KeyError
    return _member

def _get_society(society):
    if society != _society.society:
        raise KeyError
    return _society

def _get_member_or_society(username):
    try:
        return _get_member(username)
    except KeyError:
        return _get_society(username)

queries.get_member = _get_member
queries.get_society = _get_society
queries.get_member_or_society = _get_member_or_society

from srcflib.scripts.utils import ENTRYPOINTS

from .scripts import no_args, with_member_society, with_owner


class TestScripts(unittest.TestCase):
    
    def test_entrypoints(self):
        self.assertIn("srcflib-scripts-no-args=tests.scripts:no_args", ENTRYPOINTS)
        
    def test_doc(self):
        self.assertEqual(cleandoc(no_args.__doc__), "Usage: srcflib-scripts-no-args")
        
    def test_args_member_society(self):
        member, society = with_member_society({"MEMBER": "spqr2", "SOCIETY": "test"})
        self.assertEqual(member, _member)
        self.assertEqual(society, _society)
        
    def test_args_owner_member(self):
        member = with_owner({"OWNER": "spqr2"})
        self.assertEqual(member, _member)
        
    def test_args_owner_society(self):
        society = with_owner({"OWNER": "test"})
        self.assertEqual(society, _society)
        

if __name__ == "__main__":
    unittest.main()
