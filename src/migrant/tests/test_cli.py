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
import logging
import pytest
from configparser import ConfigParser
import multiprocessing

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
""" % os.path.join(
    HERE, "scripts"
)

INTEGRATION_CONFIG += """
[virgin]
backend = test
repository = %s
""" % os.path.join(
    HERE, "noscripts"
)


class MockedDb:
    def __init__(self, name, manager):
        self.name = name
        self.migrations = manager.list()
        self.data = manager.dict()


class MockedBackend(backend.MigrantBackend):
    def __init__(self, dbs, manager=None):
        self.dbs = dbs
        self.new_scripts = manager.list() if manager else []
        self.inits = 0

    def begin(self, db):
        return db

    def list_migrations(self, db):
        return list(db.migrations)

    def push_migration(self, db, migration):
        db.migrations.append(migration)

    def pop_migration(self, db, migration):
        db.migrations.remove(migration)

    def generate_connections(self):
        """Generate connections to process
        """
        yield from self.dbs

    def generate_test_connections(self):
        return self.generate_connections()

    def on_new_script(self, rev_name):
        """Called when new script is created
        """
        self.new_scripts.append(rev_name)

    def on_repo_init(self):
        """Called when new script repository is initialized
        """
        self.inits += 1


class ConfigTest(unittest.TestCase):
    def test_get_db_config(self):
        cp = ConfigParser()
        cp.read_file(io.StringIO(SAMPLE_CONFIG), "SAMPLE_CONFIG")
        config = cli.get_db_config(cp, "db1")
        self.assertEqual(
            config,
            {
                "backend": "mongo",
                "backend_uri": "localhost:27017/acme",
                "repository": "repo/",
            },
        )


class UpgradeTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def backend_fixture(self, tmpdir, migrant_backend):
        m = multiprocessing.Manager()
        self.db0 = MockedDb("db0", m)
        self.backend = MockedBackend([self.db0], m)
        migrant_backend.set(self.backend)

        migrant_ini = tmpdir.join("migrant.ini")
        migrant_ini.write(INTEGRATION_CONFIG)
        self.migrant_ini = str(migrant_ini)

        self.cfg = cli.load_config(self.migrant_ini)

        self.logstream = io.StringIO()
        hdl = logging.StreamHandler(self.logstream)
        hdl.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        logging.root.addHandler(hdl)
        logging.root.setLevel(logging.INFO)

    def test_status_dirty(self):
        self.db0.migrations.extend(["aaaa_first"])

        args = cli.parser.parse_args(["test", "status"])
        cli.dispatch(args, self.cfg)

        log = self.logstream.getvalue()
        self.assertIn("Pending actions: 2", log)

    def test_status_clean(self):
        self.db0.migrations.extend(["aaaa_first", "bbbb_second", "cccc_third"])

        args = cli.parser.parse_args(["test", "status"])
        cli.dispatch(args, self.cfg)

        log = self.logstream.getvalue()
        self.assertIn("Up-to-date", log)

    def test_no_scripts(self):
        args = cli.parser.parse_args(["virgin", "upgrade"])
        cli.dispatch(args, self.cfg)
        self.assertEqual(list(self.db0.migrations), ["INITIAL"])

    def test_initial_upgrade(self):
        args = cli.parser.parse_args(["test", "upgrade"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(
            list(self.db0.migrations),
            ["INITIAL", "aaaa_first", "bbbb_second", "cccc_third"],
        )

    def test_subsequent_emtpy_upgrade(self):
        args = cli.parser.parse_args(["test", "upgrade"])
        cli.dispatch(args, self.cfg)
        # this should be a noop
        cli.dispatch(args, self.cfg)

        self.assertEqual(
            list(self.db0.migrations),
            ["INITIAL", "aaaa_first", "bbbb_second", "cccc_third"],
        )

    def test_upgrade_latest(self):
        self.db0.migrations.extend(["aaaa_first"])

        args = cli.parser.parse_args(["test", "upgrade"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(
            list(self.db0.migrations), ["aaaa_first", "bbbb_second", "cccc_third"]
        )
        self.assertEqual(dict(self.db0.data), {"hello": "world", "value": "c"})

    def test_upgrade_particular(self):
        self.db0.migrations.extend(["aaaa_first"])
        args = cli.parser.parse_args(["test", "upgrade", "--revision", "bbbb_second"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(list(self.db0.migrations), ["aaaa_first", "bbbb_second"])
        self.assertEqual(dict(self.db0.data), {"value": "b"})

    def test_downgrade(self):
        self.db0.migrations.extend(
            ["INITIAL", "aaaa_first", "bbbb_second", "cccc_third"]
        )
        self.db0.data.update({"hello": "world", "value": "c"})

        args = cli.parser.parse_args(["test", "upgrade", "--revision", "aaaa_first"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(list(self.db0.migrations), ["INITIAL", "aaaa_first"])
        self.assertEqual(dict(self.db0.data), {"value": "a"})

    def test_downgrade_to_initial(self):
        self.db0.migrations.extend(
            ["INITIAL", "aaaa_first", "bbbb_second", "cccc_third"]
        )
        self.db0.data.update({"hello": "world", "value": "c"})

        args = cli.parser.parse_args(["test", "upgrade", "--revision", "INITIAL"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(list(self.db0.migrations), ["INITIAL"])
        self.assertEqual(dict(self.db0.data), {})

    def test_dry_run_upgrade(self):
        self.db0.migrations.extend(["aaaa_first"])
        self.db0.data.update({"value": "a"})

        args = cli.parser.parse_args(["test", "upgrade", "--dry-run"])
        cli.dispatch(args, self.cfg)

        self.assertEqual(list(self.db0.migrations), ["aaaa_first"])
        self.assertEqual(dict(self.db0.data), {"value": "a"})

    def test_test(self):
        self.db0.migrations = ["INITIAL", "aaaa_first", "bbbb_second", "cccc_third"]
        self.db0.data = {"hello": "world", "value": "c"}

        cli.main(["-c", self.migrant_ini, "test", "test"])

        log = self.logstream.getvalue()
        assert "Testing upgrade" in log
        assert "Testing downgrade" in log
        assert "Testing completed" in log


class InitTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp("migrant")

    def tearDown(self):
        shutil.rmtree(self.dir)


@pytest.fixture
def sample_config(tmpdir):
    SAMPLE_CONFIG = textwrap.dedent(
        """
    [newdb]
    backend = noop
    repository = %s/repo
    """
        % tmpdir
    )

    cfg = ConfigParser()
    cfg.read_file(io.StringIO(SAMPLE_CONFIG), "SAMPLE_CONFIG")
    return cfg


def initialize(cfg):
    # Initialize repository
    args = cli.parser.parse_args(["newdb", "init"])
    cli.dispatch(args, cfg)


def get_scripts_filename(cfg):
    repodir = cfg.get("newdb", "repository")
    return os.path.join(repodir, "scripts.lst")


def test_missing_cmd():
    with pytest.raises(SystemExit):
        cli.parser.parse_args(["newdb"])


def test_init(sample_config):
    args = cli.parser.parse_args(["newdb", "init"])
    cli.dispatch(args, sample_config)

    repodir = sample_config.get("newdb", "repository")
    assert os.path.exists(repodir)


def test_init_subsequent(sample_config):
    os.mkdir(sample_config.get("newdb", "repository"))

    slistfname = get_scripts_filename(sample_config)
    with open(slistfname, "w") as f:
        f.write("aaaa_test.py")

    args = cli.parser.parse_args(["newdb", "init"])
    cli.dispatch(args, sample_config)

    with open(slistfname) as slist:
        assert slist.read() == "aaaa_test.py"


def test_new_uninitialized(sample_config):
    args = cli.parser.parse_args(["newdb", "new", "First script"])
    with pytest.raises(exceptions.RepositoryNotFound):
        cli.dispatch(args, sample_config)


def test_new_initialized(sample_config):
    initialize(sample_config)
    args = cli.parser.parse_args(["newdb", "new", "First script"])
    cli.dispatch(args, sample_config)

    with open(get_scripts_filename(sample_config)) as slist:
        lines = slist.readlines()
        assert len(lines) == 3
        assert lines[-1].strip().endswith("_first_script.py")


def test_new_subsequent(sample_config):
    initialize(sample_config)
    args = cli.parser.parse_args(["newdb", "new", "First script"])
    cli.dispatch(args, sample_config)

    args = cli.parser.parse_args(["newdb", "new", "Second script"])
    cli.dispatch(args, sample_config)

    with open(get_scripts_filename(sample_config)) as slist:
        lines = slist.readlines()
        assert len(lines) == 4
        assert lines[-2].strip().endswith("_first_script.py")
        assert lines[-1].strip().endswith("_second_script.py")


def test_new_duplicate(sample_config):
    initialize(sample_config)
    args = cli.parser.parse_args(["newdb", "new", "First script"])
    cli.dispatch(args, sample_config)

    with pytest.raises(exceptions.ScriptAlreadyExists):
        cli.dispatch(args, sample_config)


def test_new_on_repo_init(sample_config, migrant_backend):
    backend = MockedBackend([])
    migrant_backend.set(backend)

    args = cli.parser.parse_args(["newdb", "init"])
    cli.dispatch(args, sample_config)

    assert backend.inits == 1


def test_new_on_new_script(sample_config, migrant_backend):
    backend = MockedBackend([])
    migrant_backend.set(backend)
    initialize(sample_config)

    args = cli.parser.parse_args(["newdb", "new", "First script"])
    cli.dispatch(args, sample_config)

    assert len(backend.new_scripts) == 1
    assert backend.new_scripts[0].endswith("_first_script")
