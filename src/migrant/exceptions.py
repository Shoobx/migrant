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
        return "Script not found: %s" % self.message


class ScriptAlreadyExists(MigrantException):
    def __str__(self):
        return "Script already exists: %s" % self.message


class RepositoryNotFound(MigrantException):
    def __str__(self):
        return "Repository not found: %s" % self.message


class BackendNotRegistered(MigrantException):
    def __str__(self):
        return "Backend not registered: %s" % self.message


class BackendNameConflict(MigrantException):
    def __str__(self):
        return "Backend name conflict in these pacakges: %s" % self.message
