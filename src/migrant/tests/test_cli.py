###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
import os
import io
import unittest
from ConfigParser import SafeConfigParser

import mock

from migrant import cli
from migrant import backend


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
dbs = main
""" % os.path.join(HERE, 'scripts')


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

        mock.patch.dict(backend.BACKENDS, test=lambda cfg: self.backend).start()

        self.cfg = SafeConfigParser()
        self.cfg.readfp(io.BytesIO(INTEGRATION_CONFIG), "INTEGRATION_CONFIG")

    def tearDown(self):
        mock.patch.stopall()

    def test_initial_upgrade(self):
        args = cli.parser.parse_args(["upgrade", "test"])
        cli.cmd_upgrade(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['cccc'])

    def test_subsequent_emtpy_upgrade(self):
        args = cli.parser.parse_args(["upgrade", "test"])
        cli.cmd_upgrade(args, self.cfg)
        # this should be a noop
        cli.cmd_upgrade(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['cccc'])

    def test_upgrade_latest(self):
        self.db0.migrations = ["aaaa"]

        args = cli.parser.parse_args(["upgrade", "test"])
        cli.cmd_upgrade(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['aaaa', 'bbbb', 'cccc'])
        self.assertEqual(self.db0.data, {'hello': 'world', 'value': 'c'})

    def test_upgrade_particular(self):
        self.db0.migrations = ["aaaa"]

        args = cli.parser.parse_args(["upgrade", "--revision", "bbbb", "test"])
        cli.cmd_upgrade(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['aaaa', 'bbbb'])
        self.assertEqual(self.db0.data, {'value': 'b'})

    def test_downgrade(self):
        self.db0.migrations = ["aaaa", "bbbb", "cccc"]
        self.db0.data = {'hello': 'world', 'value': 'c'}

        args = cli.parser.parse_args(["upgrade", "--revision", "aaaa", "test"])
        cli.cmd_upgrade(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['aaaa'])
        self.assertEqual(self.db0.data, {'value': 'a'})

    def test_dry_run_upgrade(self):
        self.db0.migrations = ["aaaa"]
        self.db0.data = {"value": "a"}

        args = cli.parser.parse_args(["upgrade", "--dry-run", "test"])
        cli.cmd_upgrade(args, self.cfg)

        self.assertEqual(self.db0.migrations, ['aaaa'])
        self.assertEqual(self.db0.data, {'value': 'a'})
