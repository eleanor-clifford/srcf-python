from inspect import cleandoc
import platform
import unittest
from unittest.mock import Mock

from srcf.database import Member, Society

from srcflib.plumbing.common import (command, owner_desc, owner_name, owner_website, Password,
                                     Result, State)

from .plumbing import (collect_all, collect_pair, created, default, require_here, success,
                       success_value, unchanged)


from .plumbing import require_here


class TestOwnerInfo(unittest.TestCase):

    def test_name_member(self):
        member = Member(crsid="spqr2")
        self.assertEqual(owner_name(member), "spqr2")

    def test_name_society(self):
        society = Society(society="test")
        self.assertEqual(owner_name(society), "test")

    def test_desc_member(self):
        member = Member(preferred_name="first", surname="last")
        self.assertEqual(owner_desc(member), "first last")

    def test_desc_society(self):
        society = Society(description="Test Society")
        self.assertEqual(owner_desc(society), "Test Society")

    def test_desc_society_admins(self):
        society = Society(description="Test Society")
        self.assertEqual(owner_desc(society, True), "Test Society admins")

    def test_website_member(self):
        member = Member(crsid="spqr2")
        self.assertEqual(owner_website(member), "https://spqr2.user.srcf.net")

    def test_website_society(self):
        society = Society(society="test")
        self.assertEqual(owner_website(society), "https://test.soc.srcf.net")


class TestResult(unittest.TestCase):

    maxDiff = None

    def test_state_default(self):
        self.assertEqual(default().state, State.unchanged)

    def test_state_unchanged(self):
        self.assertEqual(unchanged().state, State.unchanged)

    def test_state_success(self):
        self.assertEqual(success().state, State.success)

    def test_state_parts_success(self):
        self.assertEqual(collect_pair().state, State.success)

    def test_state_parts_created(self):
        self.assertEqual(collect_all().state, State.created)

    def test_value_unset(self):
        with self.assertRaises(ValueError):
            success().value

    def test_value_set(self):
        self.assertEqual(success_value("test").value, "test")

    def test_caller_inspect(self):
        self.assertEqual(default().caller, "tests.plumbing:default")

    def test_caller_custom(self):
        self.assertEqual(Result(caller=default).caller, "tests.plumbing:default")

    def test_truthy_unchanged(self):
        self.assertFalse(unchanged())

    def test_truthy_success(self):
        self.assertTrue(success())

    def test_truthy_created(self):
        self.assertTrue(created())
        
    def test_collect(self):
        result = collect_pair()
        self.assertEqual(result.parts[0].caller, "tests.plumbing:unchanged")
        self.assertEqual(result.parts[1].caller, "tests.plumbing:success")

    def test_str(self):
        self.assertEqual(str(collect_all()), cleandoc("""
        tests.plumbing:collect_all: created 'test'
            tests.plumbing:unchanged: unchanged
            tests.plumbing:success: success
            tests.plumbing:success_value: success 'test'
            tests.plumbing:created: created
        """))


class TestPassword(unittest.TestCase):
    
    def test_str(self):
        self.assertEqual(str(Password("test")), "test")
    
    def test_repr(self):
        self.assertEqual(repr(Password("test")), "<Password: '***'>")
        
    def test_template_str(self):
        self.assertEqual(str(Password("test", "prefix:{}")), "prefix:test")
    
    def test_template_repr(self):
        self.assertEqual(repr(Password("test", "prefix:{}")), "<Password: 'prefix:***'>")
    
    def test_template_wrap(self):
        self.assertEqual(str(Password("test").wrap("prefix:{}")), "prefix:test")


class TestHost(unittest.TestCase):
    
    def test_match(self):
        platform.node = Mock(return_value="here")
        self.assertEqual(require_here().state, State.success)
    
    def test_mismatch(self):
        platform.node = Mock(return_value="not-here")
        with self.assertRaises(RuntimeError):
            require_here()


class TestCommand(unittest.TestCase):
    
    def test_args(self):
        self.assertEqual(command(["echo", "left", "right"], output=True).stdout, b"left right\n")
    
    def test_input(self):
        self.assertEqual(command(["cat"], input_="input", output=True).stdout, b"input")
    
    def test_input_password(self):
        self.assertEqual(command(["cat"], input_=Password("secret"), output=True).stdout, b"secret")
        

if __name__ == "__main__":
    unittest.main()
