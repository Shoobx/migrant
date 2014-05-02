###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
import os
import imp
import logging
import string
import sha

log = logging.getLogger(__name__)

from migrant import exceptions


INITIAL_SCRIPTLIST = """
# Order of migration scripts. This file is maintained by migrant
#
""".lstrip()


SCRIPT_TEMPLATE = """'''
%(title)s
'''


def up(db):
    # Upgrade database
    pass


def down(db):
    # Downgrade database
    pass
""".lstrip()


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

    def new_script(self, title):
        self.check_repo()

        # Make name out of title
        title = title.strip()
        toreplace = string.punctuation + " "
        trmap = string.maketrans(toreplace, '_' * len(toreplace))
        name = title.lower().translate(trmap)
        revid = sha.new(title).hexdigest()[:6]
        fname = "%s_%s.py" % (revid, name)
        fullfname = os.path.join(self.directory, fname)

        if os.path.exists(fullfname):
            log.error("Script %s is already registered" % fname)
            raise exceptions.ScriptAlreadyExists()

        # Create script in repo
        with open(fullfname, "w") as sf:
            ns = {
                "title": title
            }
            sf.write(SCRIPT_TEMPLATE % ns)

        # Register script in list
        with open(self.scriptlist_fname, "a") as lf:
            lf.write(fname)
            lf.write("\n")

        log.info("Script %s created" % fullfname)

    def list_script_ids(self):
        """List scripts in right order
        """
        self.check_repo()

        if not os.path.exists(self.scriptlist_fname):
            return []

        with open(self.scriptlist_fname, 'r') as f:
            contents = f.readlines()

        scripts = []
        for scriptname in contents:
            scriptname = scriptname.strip()
            if scriptname.startswith("#"):
                continue

            if not scriptname:
                continue

            if not self.is_valid_scriptname(scriptname):
                log.warning("Ignoring unrecognized script name: %s" %
                            scriptname)
                continue

            scripts.append(self.fname_to_revid(scriptname))

        return scripts

    def load_script(self, scriptid):
        self.check_repo()

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

    def check_repo(self):
        if not os.path.exists(self.directory):
            raise exceptions.RepositoryNotFound(self.directory)


def create_repo(cfg):
    return Repository(cfg['repository'])