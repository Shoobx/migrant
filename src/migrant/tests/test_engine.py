###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
import unittest

import mock

from migrant.engine import MigrantEngine


class MigrantEngineTest(unittest.TestCase):
    def test_calc_actions_simple(self):
        engine = self._make_engine(['a', 'b'], ['a', 'b', 'c', 'd'])
        actions = engine.calc_actions(None, "d")
        self.assertEqual(actions, [('+', 'c'), ('+', 'd')])

    def test_calc_actions_downgrade(self):
        engine = self._make_engine(['a', 'b', 'c'], ['a', 'b', 'c', 'd'])
        actions = engine.calc_actions(None, "a")
        self.assertEqual(actions, [('-', 'c'), ('-', 'b')])

    def test_calc_actions_outoforder_upgrade(self):
        engine = self._make_engine(['a', 'b', 'd'], ['a', 'b', 'c', 'd'])
        actions = engine.calc_actions(None, "d")
        self.assertEqual(actions, [('+', 'c')])

    def test_calc_actions_outoforder_downgrade(self):
        engine = self._make_engine(['a', 'b', 'd'], ['a', 'b', 'c', 'd'])
        actions = engine.calc_actions(None, "c")
        self.assertEqual(actions, [('-', 'd'), ('+', 'c')])

    def test_calc_actions_nobeginning(self):
        engine = self._make_engine(['b', 'd'], ['a', 'b', 'c', 'd', 'e'])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [('+', 'c'), ('+', 'e')])

    def test_calc_actions_removedscripts(self):
        engine = self._make_engine(['a', 'b', 'c', 'd'], ['c', 'd', 'e'])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [('+', 'e')])

    def test_calc_actions_wrongorder(self):
        engine = self._make_engine(['d', 'b', 'a'], ['b', 'c', 'd', 'e'])
        actions = engine.calc_actions(None, "e")
        self.assertEqual(actions, [('+', 'c'), ('+', 'e')])

    def test_calc_actions_wrongorder_downgrade(self):
        engine = self._make_engine(['e', 'd', 'b', 'a'], ['b', 'c', 'd', 'e'])
        actions = engine.calc_actions(None, "b")
        self.assertEqual(actions, [('-', 'e'), ('-', 'd')])

    def _make_engine(self, migrations, scripts):
        backend = mock.Mock()
        backend.list_migrations.return_value = migrations

        repository = mock.Mock()
        repository.list_script_ids.return_value = scripts

        engine = MigrantEngine(backend, repository, {})
        return engine
