###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################


class MigrantException(RuntimeError):
    pass


class ConfigurationError(MigrantException):
    pass


class ScriptNotFoundError(MigrantException):
    def __str__(self):
        return "Script not found: %s" % self.args


class ScriptAlreadyExists(MigrantException):
    def __str__(self):
        return "Script already exists: %s" % self.args


class RepositoryNotFound(MigrantException):
    def __str__(self):
        return "Repository not found: %s" % self.args


class BackendNotRegistered(MigrantException):
    def __str__(self):
        return "Backend not registered: %s" % self.args


class BackendNameConflict(MigrantException):
    def __str__(self):
        return "Backend name conflict in these pacakges: %s" % self.args


class DatabaseUnavailable(MigrantException):
    """Raised by backend when database is not available for processing"""
