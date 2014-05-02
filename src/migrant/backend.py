###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################

import logging
import pkg_resources

from migrant import exceptions

log = logging.getLogger(__name__)


class MigrantBackend(object):
    """Base interface for backend implementations"""

    def list_migrations(self, db):
        raise NotImplementedError

    def push_migration(self, db, migration):
        raise NotImplementedError

    def pop_migration(self, db, migration):
        raise NotImplementedError

    def generate_connections(self):
        """Generate connections to process
        """
        raise NotImplementedError


class NoopBackend(MigrantBackend):
    def __init__(self, cfg):
        self.cfg = cfg

    def list_migrations(self, db):
        return ["INITIAL"]

    def push_migration(self, db, migration):
        log.info("NOOP: pushing migration %s" % migration)

    def pop_migration(self, db, migration):
        log.info("NOOP: popping migration %s" % migration)

    def generate_connections(self):
        yield "NOOP"


def create_backend(cfg):
    name = cfg['backend']

    factory = get_backend(name)
    return factory(cfg)


def get_backend(name):
    backends = list(pkg_resources.iter_entry_points('migrant', name))
    if not backends:
        raise exceptions.BackendNotRegistered(name)
    if len(backends) > 1:
        raise exceptions.BackendNameConflict(backends)
    pcls = backends[0].load()
    return pcls
