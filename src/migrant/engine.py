###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
import logging

log = logging.getLogger(__name__)


class ScriptNotFoundError(RuntimeError):
    pass


class Script(object):
    rev_id = None
    title = None

    def __init__(self, filename):
        pass

    def up(self, engine):
        pass

    def down(self, engine):
        pass


class Repository(object):

    def __init__(self, directory):
        self.directory = directory

    def list_script_ids(self):
        """List scripts in right order
        """
        return []

    def load_script(scriptid):
        pass


class MigrantEngine(object):
    def __init__(self, backend, repository, config):
        self.backend = backend
        self.repository = repository
        self.script_ids = repository.list_script_ids()
        self.config = config

    def update(self, target_id=None):
        target_id = self.pick_rev_id(target_id)
        actions = self.calc_actions(target_id)
        self.execute_actions(actions)

    def pick_rev_id(self, rev_id=None):
        if rev_id is None:
            # Pick latest one
            rev_id = self.script_ids[-1]

        if rev_id not in self.script_ids:
            raise ScriptNotFoundError(rev_id)

        return rev_id

    def calc_actions(self, target_revid):
        """Caclulate actions, required to update to revision `target_revid`
        """
        assert target_revid in self.script_ids
        migrations = self.backend.list_migrations()
        assert len(migrations) > 0, "Migrations are initialized"

        script_idx = {v: idx for idx, v in enumerate(self.script_ids)}

        migrations = [m for m in migrations if m in script_idx]
        migrations = sorted(migrations, key=lambda m: script_idx[m])

        if not migrations:
            log.error("Cannot upgrade: no common revision between "
                      "repository and database")
            return []

        base_revid = migrations[0]
        base_idx = script_idx[base_revid]
        target_idx = script_idx[target_revid]

        toremove = [m for m in reversed(migrations)
                    if script_idx[m] > target_idx]
        toadd = [s for s in self.script_ids
                 if base_idx < script_idx[s] <= target_idx
                 and s not in migrations]
        return [('-', rid) for rid in toremove] + [('+', rid) for rid in toadd]

    def execute_actions(self, actions):
        for a in actions:
            a.do()
