###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################


class MigrantBackend(object):
    """Base interface for backend implementations"""

    def list_migrations(self):
        raise NotImplementedError

    def push_migration(self, migration):
        raise NotImplementedError

    def pop_migration(self, migration):
        raise NotImplementedError
