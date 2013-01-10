#!/usr/bin/env python

import srcf
import unittest

class TestAdmins(unittest.TestCase):
    def setUp(self):
        self.mems, self.socs = srcf.members_and_socs()

    def mem_soc(self, mem, soc):
        self.assertTrue(mem in soc)
        self.assertTrue(mem.crsid in soc)
        self.assertTrue(mem in soc.admins())
        self.assertTrue(mem.crsid in soc.admins())

    def test_mem_socs(self):
        for mem in self.mems.values():
            for soc in mem.socs():
                self.mem_soc(mem, soc)

    def test_soc_admins(self):
        for soc in self.socs.values():
            for mem in soc.admins():
                self.mem_soc(mem, soc)

if __name__ == '__main__':
    unittest.main()
