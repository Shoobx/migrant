###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################

import argparse
import logging
from ConfigParser import SafeConfigParser

from migrant.engine import MigrantEngine, create_repo
from migrant.backend import create_backend

log = logging.getLogger(__name__)


def cmd_new(args, cfg):
    print "NEW", args


def cmd_upgrade(args, cfg):
    cfg = get_db_config(cfg, args.database)
    repo = create_repo(cfg)
    backend = create_backend(cfg)
    engine = MigrantEngine(backend, repo, cfg)
    engine.update(args.revision)


parser = argparse.ArgumentParser(
    description='Database Migration Engine')

commands = parser.add_subparsers()

new_parser = commands.add_parser(
    "new",
    help="Create new migration script")
new_parser.set_defaults(cmd=cmd_new)

upgrade_parser = commands.add_parser(
    "upgrade",
    help="Perform upgrade")
upgrade_parser.set_defaults(cmd=cmd_upgrade)
upgrade_parser.add_argument("-n", "--dry-run", action="store_true",
                            help=("dry run: do not execute scripts, only "
                                  "show what is going to be executed."))
upgrade_parser.add_argument("database", help="Database name to upgrade")
upgrade_parser.add_argument("-r", "--revision",
                            help=("Revision to upgrade to. If not specified, "
                                  "latest revision will be used"))

def load_config():
    cfg = SafeConfigParser()
    with open('migrant.ini') as cfgfp:
        cfg.readfp(cfgfp)
    return cfg


def get_db_config(cfg, name):
    return dict(cfg.items(name))


def main():
    cfg = load_config()
    args = parser.parse_args()
    args.cmd(args, cfg)
