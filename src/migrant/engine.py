###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
from typing import TypeVar, Dict, List, Tuple, Generic
import logging
import multiprocessing
import functools

from migrant import exceptions
from migrant.backend import MigrantBackend
from migrant.repository import Repository


log = logging.getLogger(__name__)

Actions = List[Tuple[str, str]]

DBN = TypeVar("DBN")
DBC = TypeVar("DBC")


class MigrantEngine(Generic[DBN, DBC]):
    def __init__(
        self,
        backend: MigrantBackend[DBN, DBC],
        repository: Repository,
        config: Dict[str, str],
        dry_run: bool = False,
        processes: int = None,
    ) -> None:
        self.backend = backend
        self.repository = repository
        self.script_ids = ["INITIAL"] + repository.list_script_ids()
        self.dry_run = dry_run
        self.config = config
        self.processes = processes or multiprocessing.cpu_count()

    def status(self, target_id: str = None) -> int:
        """Return number of migration actions to be performed to
        upgrade to target_id"""
        target_id = self.pick_rev_id(target_id)
        conns = self.backend.generate_connections()

        total_actions = 0
        for db in conns:
            try:
                cdb = self.initialized_db(db)
            except exceptions.DatabaseUnavailable:
                continue
            actions = self.calc_actions(cdb, target_id)
            total_actions += len(actions)

        return total_actions

    def _update(self, db: DBN, target_id: str) -> None:
        try:
            cdb = self.initialized_db(db)
        except exceptions.DatabaseUnavailable:
            return
        log.info(f"{_pname()}: Starting migration for {cdb}")
        actions = self.calc_actions(cdb, target_id)
        try:
            self.execute_actions(cdb, actions)
            self.backend.commit(cdb)
        except:
            self.backend.abort(cdb)
            raise
        finally:
            self.backend.cleanup(cdb)
        log.info(f"{_pname()}: Migration completed for {cdb}")

    def update(self, target_id: str = None) -> None:
        target_id = self.pick_rev_id(target_id)
        conns = self.backend.generate_connections()

        f = functools.partial(self._update, target_id=target_id)

        if self.processes == 1:
            for conn in conns:
                f(conn)
        else:
            with multiprocessing.Pool(self.processes) as pool:
                for _ in pool.imap_unordered(f, conns):
                    pass

    def test(self, target_id: str = None) -> None:
        target_id = self.pick_rev_id(target_id)
        conns = self.backend.generate_test_connections()

        for db in conns:
            try:
                cdb = self.initialized_db(db)
            except exceptions.DatabaseUnavailable:
                continue
            actions = self.calc_actions(cdb, target_id)

            # Perform 2 passes of up/down to make sure database is still
            # upgradeable after being downgraded.
            for testpass in range(1, 3):
                log.info(f"PASS {testpass}. Testing upgrade for {cdb}")
                self.execute_actions(cdb, actions, strict=True)

                log.info(f"PASS {testpass}. Testing downgrade for {cdb}")
                reverted_actions = self.revert_actions(actions)
                self.execute_actions(cdb, reverted_actions, strict=True)

            log.info("Testing completed for %s" % cdb)

    def initialized_db(self, db: DBN) -> DBC:
        log.info(f"{_pname()}: Preparing migrations for {db}")
        try:
            cdb = self.backend.begin(db)
        except exceptions.DatabaseUnavailable:
            log.warning(f"{_pname()}: Starting migration for {db}")
            raise

        migrations = self.backend.list_migrations(cdb)
        if not migrations:
            latest_revid = self.pick_rev_id(None)
            self.initialize_db(cdb, latest_revid)

        return cdb

    def initialize_db(self, db: DBC, initial_revid: str):
        """Iniitialize database that was never migrated before

        Assume it is fully up-to-date.
        """
        # We can assuming the current database state is fully up-to-date. This
        # is the same thing as if all past migrations were executed.
        for sid in self.script_ids:
            if sid != "INITIAL":
                # Try to resolve into proper script name
                script = self.repository.load_script(sid)
                sid = script.name
            self.backend.push_migration(db, sid)

        log.info(
            f"{_pname()}: Initialized migrations for {db}. Assuming database is at {sid}"
        )

    def pick_rev_id(self, rev_id: str = None) -> str:
        if rev_id is None:
            # Pick latest one
            rev_id = self.script_ids[-1]

        if canonical_rev_id(rev_id) not in self.script_ids:
            raise exceptions.ScriptNotFoundError(rev_id)

        return rev_id

    def calc_actions(self, db: DBC, target_revid: str) -> Actions:
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
            log.warning(
                "No common revision between repository and "
                "database %s. Running all migrations up to %s",
                db,
                target_revid,
            )
            base_revid = "INITIAL"
        else:
            base_revid = migrations[0]

        base_idx = script_idx[base_revid]
        target_idx = script_idx[target_revid]

        toremove = [m for m in reversed(migrations) if script_idx[m] > target_idx]
        toadd = [
            s
            for s in self.script_ids
            if base_idx < script_idx[s] <= target_idx and s not in migrations
        ]
        return [("-", rid) for rid in toremove] + [("+", rid) for rid in toadd]

    def revert_actions(self, actions: Actions) -> Actions:
        reverts = [("+" if a == "-" else "-", script) for a, script in actions]
        return list(reversed(reverts))

    def list_backend_migrations(self, db: DBC) -> List[str]:
        return [canonical_rev_id(revid) for revid in self.backend.list_migrations(db)]

    def execute_actions(self, db: DBC, actions: Actions, strict: bool = False) -> None:
        for action, revid in actions:
            script = self.repository.load_script(revid)
            assert action in ("+", "-")
            if action == "+":
                after = script.test_after_up
                before = script.test_before_up
                during = script.up
                end = self.backend.push_migration
                infinitive = "Upgrading"
            elif action == "-":
                after = script.test_after_down
                before = script.test_before_down
                during = script.down
                end = self.backend.pop_migration
                infinitive = "Reverting"
            log.info(
                "%s to %s%s",
                infinitive,
                script.name,
                " (not really)" if self.dry_run else "",
            )
            if not self.dry_run:
                if strict:
                    before(db)
                during(db)
                if strict:
                    after(db)
                end(db, script.name)


def _pname() -> str:
    return multiprocessing.current_process().name


def canonical_rev_id(migration_name: str) -> str:
    if "_" in migration_name:
        return migration_name.split("_", 1)[0]
    else:
        return migration_name
