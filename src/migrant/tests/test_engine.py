###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
from typing import List, Dict, Generator
import os
import unittest
import time

import mock

from migrant import exceptions
from migrant.engine import MigrantEngine
from migrant.backend import MigrantBackend
from migrant.repository import Script, Repository


class MigrantEngineTest(unittest.TestCase):
    def test_calc_actions_simple(self):
        engine = _make_engine(["a", "b"], ["a", "b", "c", "d"])
        actions = engine.calc_actions(None, "d")
        self.assertEqual(actions, [("+", "c"), ("+", "d")])

    def test_calc_actions_downgrade(self):
        engine = _make_engine(["a", "b", "c"], ["a", "b", "c", "d"])
        actions = engine.calc_actions(None, "a")
        self.assertEqual(actions, [("-", "c"), ("-", "b")])

    def test_calc_actions_outoforder_upgrade(self):
        engine = _make_engine(["a", "b", "d"], ["a", "b", "c", "d"])
        actions = engine.calc_actions(None, "d")
        self.assertEqual(actions, [("+", "c")])

    def test_calc_actions_outoforder_downgrade(self):
        engine = _make_engine(["a", "b", "d"], ["a", "b", "c", "d"])
        actions = engine.calc_actions(None, "c")
        self.assertEqual(actions, [("-", "d"), ("+", "c")])

    def test_calc_actions_nobeginning(self):
        engine = _make_engine(["b", "d"], ["a", "b", "c", "d", "e"])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [("+", "c"), ("+", "e")])

    def test_calc_actions_removedscripts(self):
        engine = _make_engine(["a", "b", "c", "d"], ["c", "d", "e"])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [("+", "e")])

    def test_calc_actions_wrongorder(self):
        engine = _make_engine(["d", "b", "a"], ["b", "c", "d", "e"])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [("+", "c"), ("+", "e")])

    def test_calc_actions_nocommon(self):
        engine = _make_engine(["a", "b", "c"], ["d", "e"])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [("+", "d"), ("+", "e")])

    def test_calc_actions_wrongorder_downgrade(self):
        engine = _make_engine(["e", "d", "b", "a"], ["b", "c", "d", "e"])
        actions = engine.calc_actions(None, "b")
        self.assertEqual(actions, [("-", "e"), ("-", "d")])

    def test_revert_actions(self):
        engine = _make_engine([], [])
        reverted = engine.revert_actions([("-", "a"), ("+", "b")])
        self.assertEqual(reverted, [("-", "b"), ("+", "a")])

    def test_test(self):
        log = []
        engine = _make_engine(["a", "b"], ["a", "b", "c", "d"], log)
        engine.test()
        assert log == [
            # DB 1 PASS 1
            "db1 c before up",
            "db1 c up",
            "db1 c after up",
            "db1 d before up",
            "db1 d up",
            "db1 d after up",
            "db1 d before down",
            "db1 d down",
            "db1 d after down",
            "db1 c before down",
            "db1 c down",
            "db1 c after down",
            # DB 1 PASS 2
            "db1 c before up",
            "db1 c up",
            "db1 c after up",
            "db1 d before up",
            "db1 d up",
            "db1 d after up",
            "db1 d before down",
            "db1 d down",
            "db1 d after down",
            "db1 c before down",
            "db1 c down",
            "db1 c after down",
            # DB 2 PASS 1
            "db2 c before up",
            "db2 c up",
            "db2 c after up",
            "db2 d before up",
            "db2 d up",
            "db2 d after up",
            "db2 d before down",
            "db2 d down",
            "db2 d after down",
            "db2 c before down",
            "db2 c down",
            "db2 c after down",
            # DB 2 PASS 2
            "db2 c before up",
            "db2 c up",
            "db2 c after up",
            "db2 d before up",
            "db2 d up",
            "db2 d after up",
            "db2 d before down",
            "db2 d down",
            "db2 d after down",
            "db2 c before down",
            "db2 c down",
            "db2 c after down",
        ]


class ScriptMock:
    def __init__(self, name, log):
        self.name = name
        self.log = log

    def up(self, db):
        self.log.append(f"{db} {self.name} up")

    def down(self, db):
        self.log.append(f"{db} {self.name} down")

    def test_before_up(self, db):
        self.log.append(f"{db} {self.name} before up")

    def test_after_up(self, db):
        self.log.append(f"{db} {self.name} after up")

    def test_before_down(self, db):
        self.log.append(f"{db} {self.name} before down")

    def test_after_down(self, db):
        self.log.append(f"{db} {self.name} after down")


def _make_engine(migrations, scripts, log=None):
    """Make a mock engine that upgrades backend, having `migrations` installed,
    using `scripts` in repository
    """
    log = log if log is not None else []
    backend = mock.Mock()
    backend.list_migrations.return_value = migrations
    backend.begin = lambda db: db

    backend.generate_test_connections.return_value = ["db1", "db2"]

    scriptmodules = {sid: ScriptMock(sid, log) for sid in scripts}
    repository = mock.Mock()
    repository.list_script_ids.return_value = scripts
    repository.load_script = scriptmodules.__getitem__

    engine = MigrantEngine(backend, repository, {})
    return engine


class MultiDbBackend(MigrantBackend[str, str]):
    def __init__(self, dbs: List[str], logfname: str) -> None:
        self._applied = {}
        self.dbs = dbs
        self.logfname = logfname
        self.unavailable_dbs: List[str] = []
        for db in dbs:
            self._applied[db] = ["INITIAL"]

    def begin(self, db: str) -> str:
        if db in self.unavailable_dbs:
            raise exceptions.DatabaseUnavailable(db)
        return db

    def list_migrations(self, db: str) -> List[str]:
        return self._applied.get(db, [])

    def push_migration(self, db, migration):
        migrations = self._applied.setdefault(db, [])
        migrations.append(migration)

    def pop_migration(self, db, migration):
        migrations = self._applied.setdefault(db, [])
        migrations.remove(migration)

    def generate_connections(self) -> Generator[str, None, None]:
        """Generate connections to process
        """
        for db in self.dbs:
            yield db


class TimedScript(Script):
    def __init__(self, name: str, timemap: Dict[str, float], logfname: str) -> None:
        self.name = name
        self._timemap = timemap
        self._logfname = logfname

    def up(self, db):
        tosleep = self._timemap.get(db, 0)
        time.sleep(tosleep)
        with open(self._logfname, "a") as f:
            f.write(f"{db}: Upgraded to {self.name} ({tosleep}s)\n")


class MultiDbRepo(Repository):
    def __init__(self, timemap: Dict[str, float], logfname: str) -> None:
        self.timemap = timemap
        self.logfname = logfname

    def list_script_ids(self) -> List[str]:
        return ["script1"]

    def load_script(self, scriptid: str) -> Script:
        return TimedScript(scriptid, self.timemap, self.logfname)


def test_concurrent_upgrade_multiprocess(tmp_path) -> None:
    # GIVEN

    # Prepare the log file. Since we are running scripts in
    # multiprocessing environment, we cannot share memory data structure, like
    # list, and let scripts write log to it. Instead, write to a share file.
    logfname = os.path.join(tmp_path, "migration.log")
    # backend = MultiDbBackend(["db1"] + ["db2", "db3"]*10, logfname)
    backend = MultiDbBackend(["db1", "db2", "db3"], logfname)
    repository = MultiDbRepo({"db1": 0.1, "db2": 0.01, "db3": 0.05}, logfname)
    engine = MigrantEngine(backend, repository, {}, processes=2)

    # WHEN
    engine.update()

    # THEN
    with open(logfname, "r") as f:
        log = f.read().strip().split("\n")

    # Longest task executed last
    assert log == [
        "db2: Upgraded to script1 (0.01s)",
        "db3: Upgraded to script1 (0.05s)",
        "db1: Upgraded to script1 (0.1s)",
    ]


def test_concurrent_upgrade_singleprocess(tmp_path) -> None:
    # GIVEN

    # Prepare the log file. Since we are running scripts in
    # multiprocessing environment, we cannot share memory data structure, like
    # list, and let scripts write log to it. Instead, write to a share file.
    logfname = os.path.join(tmp_path, "migration.log")
    backend = MultiDbBackend(["db1", "db2", "db3"], logfname)
    repository = MultiDbRepo({"db1": 0.1, "db2": 0.01, "db3": 0.05}, logfname)
    engine = MigrantEngine(backend, repository, {}, processes=1)

    # WHEN
    engine.update()

    # THEN
    with open(logfname, "r") as f:
        log = f.read().strip().split("\n")

    # First task executed first despite being the longest
    assert log == [
        "db1: Upgraded to script1 (0.1s)",
        "db2: Upgraded to script1 (0.01s)",
        "db3: Upgraded to script1 (0.05s)",
    ]


def test_skip_unavailable(tmp_path) -> None:
    # GIVEN
    logfname = os.path.join(tmp_path, "migration.log")

    backend = MultiDbBackend(["db1", "db2", "db3"], logfname)
    backend.unavailable_dbs = ["db1", "db3"]
    repository = MultiDbRepo({"db1": 0.1, "db2": 0.01, "db3": 0.05}, logfname)
    engine = MigrantEngine(backend, repository, {}, processes=1)

    # WHEN
    engine.update()

    # THEN
    with open(logfname, "r") as f:
        log = f.read().strip().split("\n")

    # First task executed first despite being the longest
    assert log == [
        "db2: Upgraded to script1 (0.01s)",
    ]
