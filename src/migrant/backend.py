###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################

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


BACKENDS = {
}


def create_backend(cfg):
    name = cfg['backend']

    if name not in BACKENDS:
        raise exceptions.ConfigurationError("Unknown backend: %s" % name)

    factory = BACKENDS[name]
    return factory(cfg)
