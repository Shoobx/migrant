###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################

import unittest
import tempfile
import os
import shutil
import textwrap

from migrant import repository


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp("migrant")
        self.slistfname = os.path.join(self.dir, "scripts.lst")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_create_list(self):
        repo = repository.Repository(self.dir)
        repo.init()
        newrev = repo.new_script("Hello, World")

        revids = repo.list_script_ids()
        self.assertEqual(revids, [newrev.split('_')[0]])

    def test_is_valid_scriptname(self):
        repo = repository.Repository(self.dir)
        self.assertTrue(repo.is_valid_scriptname("xxxx_hello.py"))
        self.assertFalse(repo.is_valid_scriptname("hello.py"))
        self.assertFalse(repo.is_valid_scriptname("# Some Comment"))
        self.assertFalse(repo.is_valid_scriptname("# Some_Comment"))

    def test_weird_list(self):
        repo = repository.Repository(self.dir)
        repo.init()

        SCRIPTSLST = textwrap.dedent("""
        # This is some Comment

        a24bc_first.py
        weird line
        <<<< HEAD
        d724a_second.py
        ====
        1babe_third.py
        >>>> CONFLICT MARKER
        """).lstrip()
        with open(self.slistfname, "w") as lf:
            lf.write(SCRIPTSLST)

        revids = repo.list_script_ids()
        self.assertEqual(revids, ['a24bc', 'd724a', '1babe'])
