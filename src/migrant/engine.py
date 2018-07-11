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

    def status(self, target_id=None):
        """Return number of migration actions to be performed to
        upgrade to target_id"""
        target_id = self.pick_rev_id(target_id)
        conns = self.backend.generate_connections()

        total_actions = 0
        for db in self.initialized_dbs(conns):
            actions = self.calc_actions(db, target_id)
            total_actions += len(actions)

        return total_actions

    def update(self, target_id=None):
        target_id = self.pick_rev_id(target_id)
        conns = self.backend.generate_connections()

        for db in self.initialized_dbs(conns):
            log.info(u"Starting migration for %s" % db)
            actions = self.calc_actions(db, target_id)
            self.execute_actions(db, actions)
            log.info(u"Migration completed for %s" % db)

    def test(self, target_id=None):
        target_id = self.pick_rev_id(target_id)
        conns = self.backend.generate_test_connections()

        for db in self.initialized_dbs(conns):
            actions = self.calc_actions(db, target_id)

            # Perform 2 passes of up/down to make sure database is still
            # upgradeable after being downgraded.
            for testpass in range(1, 3):
                log.info(u"PASS %s. Testing upgrade for %s" % (testpass, db))
                self.execute_actions(db, actions, strict=True)

                log.info(u"PASS %s. Testing downgrade for %s" % (testpass, db))
                reverted_actions = self.revert_actions(actions)
                self.execute_actions(db, reverted_actions, strict=True)

            log.info(u"Testing completed for %s" % db)

    def initialized_dbs(self, conns):
        for db in conns:
            log.info(u"Preparing migrations for %s" % db)
            migrations = self.backend.list_migrations(db)
            if not migrations:
                latest_revid = self.pick_rev_id(None)
                self.initialize_db(db, latest_revid)
                continue

            yield db

    def initialize_db(self, db, initial_revid):
        for sid in self.script_ids:
            if sid != "INITIAL":
                # Try to resolve into proper script name
                script = self.repository.load_script(sid)
                sid = script.name
            self.backend.push_migration(db, sid)

        log.info(u"Initializing migrations for %s. Assuming database is at %s" %
                 (db, sid))

    def pick_rev_id(self, rev_id=None):
        if rev_id is None:
            # Pick latest one
            rev_id = self.script_ids[-1]

        if canonical_rev_id(rev_id) not in self.script_ids:
            raise exceptions.ScriptNotFoundError(rev_id)

        return rev_id

    def calc_actions(self, db, target_revid):
        """Caclulate actions, required to update to revision `target_revid`
        """
        target_revid = canonical_rev_id(target_revid)
        assert target_revid in self.script_ids
        migrations = self.list_backend_migrations(db)
        assert len(migrations) > 0, "Migrations are initialized"

        script_idx = {v: idx for idx, v in enumerate(self.script_ids)}

        migrations = [m for m in migrations if m in script_idx]
        migrations = sorted(migrations, key=lambda m: script_idx[m])

        if not migrations:
            log.warning(u"No common revision between repository and "
                        "database %s. Running all migrations up to %s",
                        db, target_revid)
            base_revid = 'INITIAL'
        else:
            base_revid = migrations[0]

        base_idx = script_idx[base_revid]
        target_idx = script_idx[target_revid]

        toremove = [m for m in reversed(migrations)
                    if script_idx[m] > target_idx]
        toadd = [s for s in self.script_ids
                 if base_idx < script_idx[s] <= target_idx
                 and s not in migrations]
        return [('-', rid) for rid in toremove] + [('+', rid) for rid in toadd]

    def revert_actions(self, actions):
        reverts = [("+" if a == "-" else "-", script)
                   for a, script in actions]
        return list(reversed(reverts))

    def list_backend_migrations(self, db):
        return [canonical_rev_id(revid)
                for revid in self.backend.list_migrations(db)]

    def execute_actions(self, db, actions, strict=False):
        for action, revid in actions:
            script = self.repository.load_script(revid)
            assert action in ("+", "-")
            if action == "+":
                after = script.test_after_up
                before = script.test_before_up
                during = script.up
                end = self.backend.push_migration
                infinitive = u"Upgrading"
            elif action == "-":
                after = script.test_after_down
                before = script.test_before_down
                during = script.down
                end = self.backend.pop_migration
                infinitive = u"Reverting"
            log.info(
                u"%s to %s%s", infinitive, script.name, " (not really)" if self.dry_run else ""
            )
            if not self.dry_run:
                if strict:
                    before(db)
                during(db)
                if strict:
                    after(db)
                end(db, script.name)


def canonical_rev_id(migration_name):
    if "_" in migration_name:
        return migration_name.split("_", 1)[0]
    else:
        return migration_name
