###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################


class ConfigurationError(RuntimeError):
    pass


class ScriptNotFoundError(RuntimeError):
    pass


class ScriptAlreadyExists(RuntimeError):
    pass


class RepositoryNotFound(RuntimeError):
    pass


class BackendNotRegistered(RuntimeError):
    pass


class BackendNameConflict(RuntimeError):
    pass
