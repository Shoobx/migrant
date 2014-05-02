###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
import os
import imp
import logging

log = logging.getLogger(__name__)

from migrant import exceptions


INITIAL_SCRIPTLIST = """
# Order of migration scripts. This file is maintained by migrant
#
""".strip()


class Script(object):
    rev_id = None
    name = None

    def __init__(self, filename):
        assert filename.endswith(".py")
        self.name = os.path.basename(filename)[:-3]
        self.module = imp.load_source(self.name, filename)

    def up(self, db):
        self.module.up(db)

    def down(self, db):
        self.module.down(db)


class Repository(object):

    def __init__(self, directory):
        self.directory = directory
        self.scriptlist_fname = os.path.join(self.directory, "scripts.lst")

    def init(self):
        if not os.path.exists(self.directory):
            log.info("Creating migrations directory %s" % self.directory)
            os.makedirs(self.directory)

        if not os.path.exists(self.scriptlist_fname):
            log.info("Creating initial scripts.lst")
            with open(self.scriptlist_fname, "w") as f:
                f.write(INITIAL_SCRIPTLIST)
                f.write("\n")

    def list_script_ids(self):
        """List scripts in right order
        """
        if not os.path.exists(self.scriptlist_fname):
            return []

        with open(self.scriptlist_fname, 'r') as f:
            contents = f.readlines()

        scripts = []
        for scriptname in contents:
            if not self.is_valid_scriptname(scriptname):
                log.warning("Ignoring unrecognized script name: %s" %
                            scriptname)

            scripts.append(self.fname_to_revid(scriptname))

        return scripts

    def load_script(self, scriptid):
        # Find script with given id
        fname = None
        for fname in os.listdir(self.directory):
            if not fname.endswith(".py"):
                continue

            if fname.startswith("%s_" % scriptid):
                break
        else:
            raise exceptions.ScriptNotFoundError(scriptid)

        return Script(os.path.join(self.directory, fname))

    def is_valid_scriptname(self, fname):
        return "_" in fname and fname.endswith(".py")

    def fname_to_revid(self, fname):
        return fname.split("_")[0]


def create_repo(cfg):
    return Repository(cfg['repository'])
