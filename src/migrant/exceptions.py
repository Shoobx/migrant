###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################


class ConfigurationError(RuntimeError):
    pass


class ScriptNotFoundError(RuntimeError):
    pass


class BackendNotRegistered(RuntimeError):
    pass


class BackendNameConflict(RuntimeError):
    pass
