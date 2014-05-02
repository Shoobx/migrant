###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
import os
import io
import unittest
import tempfile
import shutil
import textwrap
from ConfigParser import SafeConfigParser

import mock

from migrant import cli, backend, exceptions


HERE = os.path.dirname(__file__)

SAMPLE_CONFIG = """
[db1]
backend = mongo
repository = repo/
backend_uri = localhost:27017/acme

[db2]
backend = test
repository = /repo
"""

INTEGRATION_CONFIG = """
[test]
backend = test
repository = %s
""" % os.path.join(HERE, 'scripts')

INTEGRATION_CONFIG += """
[virgin]
backend = test
repository = %s
""" % os.path.join(HERE, 'noscripts')


class TestDb(object):
    def __init__(self, name):
        self.name = name
        self.migrations = []
        self.data = {}


class TestBackend(backend.MigrantBackend):
    def __init__(self, dbs):
        self.dbs = dbs

    def list_migrations(self, db):
        return db.migrations

    def push_migration(self, db, migration):
        db.migrations.append(migration)

    def pop_migration(self, db, migration):
        db.migrations.remove(migration)

    def generate_connections(self):
        """Generate connections to process
        """
        for db in self.dbs:
            yield db


class ConfigTest(unittest.TestCase):
    def test_get_db_config(self):
        cp = SafeConfigParser()
        cp.readfp(io.BytesIO(SAMPLE_CONFIG), "SAMPLE_CONFIG")
        config = cli.get_db_config(cp, "db1")
        self.assertEqual(config,
                         {'backend': 'mongo',
                          'backend_uri': 'localhost:27017/acme',
                          'repository': 'repo/'})


class UpgradeTest(unittest.TestCase):
    def setUp(self):
        self.db0 = TestDb("db0")
        self.backend = TestBackend([self.db0])

        mock.patch.object(backend, "get_backend",
                          return_value=lambda cfg: self.backend).start()

        self.cfg = SafeConfigParser()
        self.cfg.readfp(io.BytesIO(INTEGRATION_CONFIG), "INTEGRATION_CONFIG")

    def tearDown(self):
        mock.patch.stopall()

    def test_no_scripts(self):
        args = cli.parser.parse_args(["virgin", "upgrade"])
        cli.dispatch(args, self.cfg)
        self.assertEqual(self.db0.migrations, ['INITIAL'])

    def test_initial_upgrade(self):
        args = cli.parser.parse_args(["test", "upgrade"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['cccc'])

    def test_subsequent_emtpy_upgrade(self):
        args = cli.parser.parse_args(["test", "upgrade"])
        cli.dispatch(args, self.cfg)
        # this should be a noop
        cli.dispatch(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['cccc'])

    def test_upgrade_latest(self):
        self.db0.migrations = ["aaaa"]

        args = cli.parser.parse_args(["test", "upgrade"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['aaaa', 'bbbb', 'cccc'])
        self.assertEqual(self.db0.data, {'hello': 'world', 'value': 'c'})

    def test_upgrade_particular(self):
        self.db0.migrations = ["aaaa"]

        args = cli.parser.parse_args(["test", "upgrade", "--revision", "bbbb"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['aaaa', 'bbbb'])
        self.assertEqual(self.db0.data, {'value': 'b'})

    def test_downgrade(self):
        self.db0.migrations = ["INITIAL", "aaaa", "bbbb", "cccc"]
        self.db0.data = {'hello': 'world', 'value': 'c'}

        args = cli.parser.parse_args(["test", "upgrade", "--revision", "aaaa"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['INITIAL', 'aaaa'])
        self.assertEqual(self.db0.data, {'value': 'a'})

    def test_downgrade_to_initial(self):
        self.db0.migrations = ["INITIAL", "aaaa", "bbbb", "cccc"]
        self.db0.data = {'hello': 'world', 'value': 'c'}

        args = cli.parser.parse_args(["test", "upgrade",
                                     "--revision", "INITIAL"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['INITIAL'])
        self.assertEqual(self.db0.data, {})

    def test_dry_run_upgrade(self):
        self.db0.migrations = ["aaaa"]
        self.db0.data = {"value": "a"}

        args = cli.parser.parse_args(["test", "upgrade", "--dry-run"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['aaaa'])
        self.assertEqual(self.db0.data, {'value': 'a'})


class InitTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp("migrant")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_init(self):
        SAMPLE_CONFIG = textwrap.dedent("""
        [newdb]
        backend = noop
        repository = %s/repo
        """ % self.dir)

        cfg = SafeConfigParser()
        cfg.readfp(io.BytesIO(SAMPLE_CONFIG), "SAMPLE_CONFIG")
        args = cli.parser.parse_args(["newdb", "init"])
        cli.dispatch(args, cfg)

        self.assertTrue(os.path.exists(os.path.join(self.dir, "repo")))

    def test_init_subsequent(self):
        SAMPLE_CONFIG = textwrap.dedent("""
        [newdb]
        backend = noop
        repository = %s/repo
        """ % self.dir)

        os.mkdir(os.path.join(self.dir, "repo"))
        slistfname = os.path.join(self.dir, "repo", "scripts.lst")
        with open(slistfname, "w") as f:
            f.write("aaaa_test.py")

        cfg = SafeConfigParser()
        cfg.readfp(io.BytesIO(SAMPLE_CONFIG), "SAMPLE_CONFIG")
        args = cli.parser.parse_args(["newdb", "init"])
        cli.dispatch(args, cfg)

        self.assertTrue(os.path.exists(os.path.join(self.dir, "repo")))
        with open(slistfname) as slist:
            self.assertEqual(slist.read(), "aaaa_test.py")


class NewTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp("migrant")
        self.slistfname = os.path.join(self.dir, "repo", "scripts.lst")

        # Create initialized repo
        SAMPLE_CONFIG = textwrap.dedent("""
        [newdb]
        backend = noop
        repository = %s/repo
        """ % self.dir)

        self.cfg = SafeConfigParser()
        self.cfg.readfp(io.BytesIO(SAMPLE_CONFIG), "SAMPLE_CONFIG")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def initialize(self):
        # Initialize repository
        args = cli.parser.parse_args(["newdb", "init"])
        cli.dispatch(args, self.cfg)

    def test_new_uninitialized(self):
        args = cli.parser.parse_args(["newdb", "new", "First script"])
        with self.assertRaises(exceptions.RepositoryNotFound):
            cli.dispatch(args, self.cfg)

    def test_new_initialized(self):
        self.initialize()
        args = cli.parser.parse_args(["newdb", "new", "First script"])
        cli.dispatch(args, self.cfg)

        with open(self.slistfname) as slist:
            lines = slist.readlines()
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[-1].strip(), "e0f428_first_script.py")

    def test_new_subsequent(self):
        self.initialize()
        args = cli.parser.parse_args(["newdb", "new", "First script"])
        cli.dispatch(args, self.cfg)

        args = cli.parser.parse_args(["newdb", "new", "Second script"])
        cli.dispatch(args, self.cfg)

        with open(self.slistfname) as slist:
            lines = slist.readlines()
            self.assertEqual(len(lines), 4)
            self.assertEqual(lines[-2].strip(), "e0f428_first_script.py")
            self.assertEqual(lines[-1].strip(), "ad1b5b_second_script.py")

    def test_new_duplicate(self):
        self.initialize()
        args = cli.parser.parse_args(["newdb", "new", "First script"])
        cli.dispatch(args, self.cfg)

        with self.assertRaises(exceptions.ScriptAlreadyExists):
            cli.dispatch(args, self.cfg)
