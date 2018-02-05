###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
from builtins import object
import unittest

import mock

from migrant.engine import MigrantEngine


class MigrantEngineTest(unittest.TestCase):
    def test_calc_actions_simple(self):
        engine = _make_engine(['a', 'b'], ['a', 'b', 'c', 'd'])
        actions = engine.calc_actions(None, "d")
        self.assertEqual(actions, [('+', 'c'), ('+', 'd')])

    def test_calc_actions_downgrade(self):
        engine = _make_engine(['a', 'b', 'c'], ['a', 'b', 'c', 'd'])
        actions = engine.calc_actions(None, "a")
        self.assertEqual(actions, [('-', 'c'), ('-', 'b')])

    def test_calc_actions_outoforder_upgrade(self):
        engine = _make_engine(['a', 'b', 'd'], ['a', 'b', 'c', 'd'])
        actions = engine.calc_actions(None, "d")
        self.assertEqual(actions, [('+', 'c')])

    def test_calc_actions_outoforder_downgrade(self):
        engine = _make_engine(['a', 'b', 'd'], ['a', 'b', 'c', 'd'])
        actions = engine.calc_actions(None, "c")
        self.assertEqual(actions, [('-', 'd'), ('+', 'c')])

    def test_calc_actions_nobeginning(self):
        engine = _make_engine(['b', 'd'], ['a', 'b', 'c', 'd', 'e'])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [('+', 'c'), ('+', 'e')])

    def test_calc_actions_removedscripts(self):
        engine = _make_engine(['a', 'b', 'c', 'd'], ['c', 'd', 'e'])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [('+', 'e')])

    def test_calc_actions_wrongorder(self):
        engine = _make_engine(['d', 'b', 'a'], ['b', 'c', 'd', 'e'])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [('+', 'c'), ('+', 'e')])

    def test_calc_actions_nocommon(self):
        engine = _make_engine(['a', 'b', 'c'], ['d', 'e'])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [('+', 'd'), ('+', 'e')])

    def test_calc_actions_wrongorder_downgrade(self):
        engine = _make_engine(['e', 'd', 'b', 'a'], ['b', 'c', 'd', 'e'])
        actions = engine.calc_actions(None, "b")
        self.assertEqual(actions, [('-', 'e'), ('-', 'd')])

    def test_revert_actions(self):
        engine = _make_engine([], [])
        reverted = engine.revert_actions([('-', 'a'), ('+', 'b')])
        self.assertEqual(reverted, [('-', 'b'), ('+', 'a')])

    def test_test(self):
        log = []
        engine = _make_engine(['a', 'b'], ['a', 'b', 'c', 'd'], log)
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


class ScriptMock(object):
    def __init__(self, name, log):
        self.name = name
        self.log = log

    def up(self, db):
        self.log.append("%s %s up" % (db, self.name))

    def down(self, db):
        self.log.append("%s %s down" % (db, self.name))

    def test_before_up(self, db):
        self.log.append("%s %s before up" % (db, self.name))

    def test_after_up(self, db):
        self.log.append("%s %s after up" % (db, self.name))

    def test_before_down(self, db):
        self.log.append("%s %s before down" % (db, self.name))

    def test_after_down(self, db):
        self.log.append("%s %s after down" % (db, self.name))


def _make_engine(migrations, scripts, log=None):
    """Make a mock engine that upgrades backend, having `migrations` installed,
    using `scripts` in repository
    """
    log = log if log is not None else []
    backend = mock.Mock()
    backend.list_migrations.return_value = migrations

    backend.generate_test_connections.return_value = ["db1", "db2"]

    scriptmodules = {sid: ScriptMock(sid, log) for sid in scripts}
    repository = mock.Mock()
    repository.list_script_ids.return_value = scripts
    repository.load_script = scriptmodules.__getitem__

    engine = MigrantEngine(backend, repository, {})
    return engine
