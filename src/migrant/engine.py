###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
import logging

log = logging.getLogger(__name__)

from migrant import exceptions


class MigrantEngine(object):
    def __init__(self, backend, repository, config, dry_run=False):
        self.backend = backend
        self.repository = repository
        self.script_ids = ["INITIAL"] + repository.list_script_ids()
        self.dry_run = dry_run
        self.config = config

    def update(self, target_id=None):
        target_id = self.pick_rev_id(target_id)
        for db in self.backend.generate_connections():
            log.info("Starting migration for %s" % db)
            migrations = self.backend.list_migrations(db)

            if not migrations:
                latest_revid = self.pick_rev_id(None)
                self.initialize_db(db, latest_revid)
                continue

            actions = self.calc_actions(db, target_id)
            self.execute_actions(db, actions)
            log.info("Migration completed for %s" % db)

    def initialize_db(self, db, initial_revid):
        log.info("Initializing migrations for %s. Assuming database is at %s" %
                 (db, initial_revid))
        self.backend.push_migration(db, initial_revid)

    def pick_rev_id(self, rev_id=None):
        if rev_id is None:
            # Pick latest one
            rev_id = self.script_ids[-1]

        if rev_id not in self.script_ids:
            raise exceptions.ScriptNotFoundError(rev_id)

        return rev_id

    def calc_actions(self, db, target_revid):
        """Caclulate actions, required to update to revision `target_revid`
        """
        assert target_revid in self.script_ids
        migrations = self.backend.list_migrations(db)
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

    def execute_actions(self, db, actions):
        for action, revid in actions:
            script = self.repository.load_script(revid)
            if action == "+":
                if not self.dry_run:
                    log.info("Upgrading to %s" % revid)
                    script.up(db)
                    self.backend.push_migration(db, revid)
            else:
                assert action == "-"
                log.info("Reverting %s" % revid)
                if not self.dry_run:
                    script.down(db)
                    self.backend.pop_migration(db, revid)
