#!/usr/bin/env python

import srcf
import unittest

class TestAdmins(unittest.TestCase):
    def setUp(self):
        self.soc = srcf.get_society('executive')

    def test_contains(self):
        for admin in self.soc.admins:
            self.assertTrue(admin in self.soc)
            self.assertTrue(admin.crsid in self.soc)

if __name__ == '__main__':
    unittest.main()
