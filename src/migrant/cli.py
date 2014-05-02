###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
import os
import sys
import argparse
import logging
from ConfigParser import SafeConfigParser

from migrant import exceptions
from migrant.engine import MigrantEngine
from migrant.backend import create_backend
from migrant.repository import create_repo

log = logging.getLogger(__name__)


def cmd_init(args, cfg):
    cfg = get_db_config(cfg, args.database)
    repo = create_repo(cfg)
    repo.init()


def cmd_new(args, cfg):
    cfg = get_db_config(cfg, args.database)
    repo = create_repo(cfg)
    repo.new_script(args.title)


def cmd_upgrade(args, cfg):
    cfg = get_db_config(cfg, args.database)
    repo = create_repo(cfg)
    backend = create_backend(cfg)
    engine = MigrantEngine(backend, repo, cfg, dry_run=args.dry_run)
    engine.update(args.revision)


parser = argparse.ArgumentParser(
    description='Database Migration Engine')

commands = parser.add_subparsers()

# INIT options
init_parser = commands.add_parser(
    "init", help="Initialize migration script repository")
init_parser.set_defaults(cmd=cmd_init)
init_parser.add_argument("database", help="Database name")

# NEW options
new_parser = commands.add_parser(
    "new",
    help="Create new migration script")
new_parser.set_defaults(cmd=cmd_new)
new_parser.add_argument("database", help="Database name")
new_parser.add_argument("title", help="Migration script title")

# UPGRADE options
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
    if not os.path.exists("migrant.ini"):
        raise exceptions.ConfigurationError("migrant.ini is missing")
    cfg = SafeConfigParser()
    with open('migrant.ini') as cfgfp:
        cfg.readfp(cfgfp)
    return cfg


def get_db_config(cfg, name):
    return dict(cfg.items(name))


def setup_logging(args, cfg):
    logging.basicConfig(level=logging.INFO)


def dispatch(args, cfg):
    args.cmd(args, cfg)


def main():
    args = parser.parse_args()
    try:
        cfg = load_config()
        setup_logging(args, cfg)
        dispatch(args, cfg)
    except exceptions.MigrantException, e:
        sys.exit("fatal: %s" % e)
