#!/usr/bin/env python

from __future__ import unicode_literals

import six
import unittest

import srcf

class TestStrings(unittest.TestCase):

    def test_memberlist(self):
        self.assertTrue(isinstance(srcf.MEMBERLIST, six.string_types))
        self.assertEqual(srcf.MEMBERLIST, "/societies/sysadmins/admin/memberlist")

    def test_soclist(self):
        self.assertTrue(isinstance(srcf.SOCLIST, six.string_types))
        self.assertEqual(srcf.SOCLIST, "/societies/sysadmins/admin/soclist")


if __name__ == '__main__':
    unittest.main()

# Local Variables:
# mode: python
# coding: utf-8
# tab-width: 4
# indent-tabs-mode: nil
# End:
