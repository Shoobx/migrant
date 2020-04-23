###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
from typing import List
import os
import logging
import string
import hashlib
from importlib.machinery import SourceFileLoader

log = logging.getLogger(__name__)

from migrant import exceptions


INITIAL_SCRIPTLIST = """
# Order of migration scripts. This file is maintained by migrant
#
""".lstrip()


SCRIPT_TEMPLATE = '''"""%(title)s"""


def up(db):
    # Upgrade database
    pass


def down(db):
    # Downgrade database
    pass


# Tests for migration

def test_before_up(db):
    pass


def test_after_up(db):
    pass


def test_before_down(db):
    pass


def test_after_down(db):
    pass

'''.lstrip()


class Script:
    rev_id: str
    name: str

    def __init__(self, filename):
        assert filename.endswith(".py")
        self.name = os.path.basename(filename)[:-3]
        self.module = SourceFileLoader(self.name, filename).load_module()

    def up(self, db):
        self._exec("up", db)

    def down(self, db):
        self._exec("down", db)

    def test_before_up(self, db):
        self._exec("test_before_up", db)

    def test_after_up(self, db):
        self._exec("test_after_up", db)

    def test_before_down(self, db):
        self._exec("test_before_down", db)

    def test_after_down(self, db):
        self._exec("test_after_down", db)

    def _exec(self, method, *args, **kwargs):
        __traceback_info__ = (args, kwargs)
        if not hasattr(self.module, method):
            return

        return getattr(self.module, method)(*args, **kwargs)


class Repository:
    def new_script(self, title: str) -> str:
        raise NotImplementedError()

    def list_script_ids(self) -> List[str]:
        raise NotImplementedError()

    def load_script(self, scriptid: str) -> Script:
        raise NotImplementedError()


class DirectoryRepository(Repository):
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
        trmap = str.maketrans(toreplace, "_" * len(toreplace))
        name = title.lower().translate(trmap)
        revid = hashlib.sha1((self.directory + title).encode("utf-8")).hexdigest()[:6]
        revname = f"{revid}_{name}"
        fname = "%s.py" % revname
        fullfname = os.path.join(self.directory, fname)

        if os.path.exists(fullfname):
            log.error("Script %s is already registered" % fname)
            raise exceptions.ScriptAlreadyExists()

        # Create script in repo
        with open(fullfname, "w") as sf:
            ns = {"title": title}
            sf.write(SCRIPT_TEMPLATE % ns)

        # Register script in list
        with open(self.scriptlist_fname, "a") as lf:
            lf.write(fname)
            lf.write("\n")

        log.info("Script %s created" % fullfname)
        return revname

    def list_script_ids(self):
        """List scripts in right order
        """
        self.check_repo()

        if not os.path.exists(self.scriptlist_fname):
            return []

        with open(self.scriptlist_fname, "r") as f:
            contents = f.readlines()

        scripts = []
        for scriptname in contents:
            scriptname = scriptname.strip()
            if scriptname.startswith("#"):
                continue

            if not scriptname:
                continue

            if not self.is_valid_scriptname(scriptname):
                log.warning("Ignoring unrecognized script name: %s" % scriptname)
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
    return DirectoryRepository(cfg["repository"])
