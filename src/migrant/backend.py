###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################

import pkg_resources

from migrant import exceptions


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
