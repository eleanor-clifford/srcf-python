import os
import os.path
import pwd
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from srcflib.plumbing.common import State
from srcflib.plumbing import unix


class TestFilesystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.user = unix.User(pwd.getpwuid(os.getuid()))

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "test")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_mkdir(self):
        result = unix.mkdir(self.path, self.user)
        self.assertEqual(result.state, State.created)
        self.assertTrue(os.path.isdir(self.path))

    def test_mkdir_group_write(self):
        unix.mkdir(self.path, self.user, 0o775)
        stats = os.stat(self.path)
        mode = stat.S_IMODE(stats.st_mode)
        self.assertTrue(mode, 0o775)

    def test_mkdir_set_gid(self):
        unix.mkdir(self.path, self.user, 0o2700)
        stats = os.stat(self.path)
        mode = stat.S_IMODE(stats.st_mode)
        self.assertTrue(mode, 0o2700)

    def test_mkdir_user(self):
        if self.user.pw_uid != 0:
            self.skipTest("Requires chown, must run as root")
        nobody = unix.get_user("nobody")
        unix.mkdir(self.path, nobody)
        stats = os.stat(self.path)
        self.assertTrue(stats.st_uid, nobody.pw_uid)

    def test_mkdir_change_perms(self):
        unix.mkdir(self.path, self.user, 0o700)
        result = unix.mkdir(self.path, self.user, 0o770)
        self.assertEqual(result.state, State.success)

    def test_mkdir_change_user(self):
        if self.user.pw_uid != 0:
            self.skipTest("Requires chown, must run as root")
        unix.mkdir(self.path, self.user)
        nobody = unix.get_user("nobody")
        result = unix.mkdir(self.path, nobody)
        self.assertEqual(result.state, State.success)

    def test_mkdir_unchanged(self):
        unix.mkdir(self.path, self.user)
        result = unix.mkdir(self.path, self.user)
        self.assertEqual(result.state, State.unchanged)

    def test_symlink(self):
        result = unix.symlink(self.path, "target")
        self.assertEqual(result.state, State.created)
        self.assertTrue(os.path.islink(self.path))
        self.assertEqual(os.readlink(self.path), "target")

    def test_symlink_unchanged(self):
        unix.symlink(self.path, "target")
        result = unix.symlink(self.path, "target")
        self.assertEqual(result.state, State.unchanged)

    @patch("{}.LOG".format(unix.__spec__.name))
    def test_symlink_existing_link(self, log: Mock):
        unix.symlink(self.path, "target")
        result = unix.symlink(self.path, "not-target")
        log.warning.assert_called_with("Not overwriting existing file %r", self.path)
        self.assertEqual(result.state, State.unchanged)

    @patch("{}.LOG".format(unix.__spec__.name))
    def test_symlink_existing_file(self, log: Mock):
        with open(self.path, "w"):
            pass
        result = unix.symlink(self.path, "target")
        log.warning.assert_called_with("Not overwriting existing file %r", self.path)
        self.assertEqual(result.state, State.unchanged)


if __name__ == "__main__":
    unittest.main()
