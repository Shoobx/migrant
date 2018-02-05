###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
from future import standard_library
standard_library.install_aliases()

import os
import sys
import argparse
import logging

with standard_library.hooks():
    from configparser import SafeConfigParser

from migrant import exceptions
from migrant.engine import MigrantEngine
from migrant.backend import create_backend
from migrant.repository import create_repo

log = logging.getLogger(__name__)


def cmd_init(args, cfg):
    cfg = get_db_config(cfg, args.database)
    repo = create_repo(cfg)
    repo.init()
    backend = create_backend(cfg)
    backend.on_repo_init()


def cmd_new(args, cfg):
    cfg = get_db_config(cfg, args.database)
    repo = create_repo(cfg)
    revname = repo.new_script(args.title)
    backend = create_backend(cfg)
    backend.on_new_script(revname)


def cmd_upgrade(args, cfg):
    cfg = get_db_config(cfg, args.database)
    repo = create_repo(cfg)
    backend = create_backend(cfg)
    engine = MigrantEngine(backend, repo, cfg, dry_run=args.dry_run)
    engine.update(args.revision)


def cmd_test(args, cfg):
    cfg = get_db_config(cfg, args.database)
    repo = create_repo(cfg)
    backend = create_backend(cfg)
    engine = MigrantEngine(backend, repo, cfg)
    engine.test(args.revision)


def cmd_status(args, cfg):
    cfg = get_db_config(cfg, args.database)
    repo = create_repo(cfg)
    backend = create_backend(cfg)
    engine = MigrantEngine(backend, repo, cfg)
    actions = engine.status()
    if actions:
        log.info(u"Pending actions: %s", actions)
    else:
        log.info(u"Up-to-date")


parser = argparse.ArgumentParser(
    description='Database Migration Engine')
parser.add_argument("database", help="Database name")

parser.add_argument("-c", "--config", default="migrant.ini",
                    help=("Config file to be used"))

commands = parser.add_subparsers()

# INIT options
init_parser = commands.add_parser(
    "init", help="Initialize migration script repository")
init_parser.set_defaults(cmd=cmd_init)
# init_parser.add_argument("database", help="Database name")

# NEW options
new_parser = commands.add_parser(
    "new",
    help="Create new migration script, add a script title argument!")
new_parser.set_defaults(cmd=cmd_new)
# new_parser.add_argument("database", help="Database name")
new_parser.add_argument("title", help="Migration script title")

# STATUS options
status_parser = commands.add_parser(
    "status",
    help="Show the migration status")
status_parser.set_defaults(cmd=cmd_status)

# UPGRADE options
upgrade_parser = commands.add_parser(
    "upgrade",
    help="Perform upgrade")
upgrade_parser.set_defaults(cmd=cmd_upgrade)
upgrade_parser.add_argument("-n", "--dry-run", action="store_true",
                            help=("dry run: do not execute scripts, only "
                                  "show what is going to be executed."))
# upgrade_parser.add_argument("database", help="Database name to upgrade")
upgrade_parser.add_argument("-r", "--revision",
                            help=("Revision to upgrade to. If not specified, "
                                  "latest revision will be used"))


# TEST options
test_parser = commands.add_parser(
    "test",
    help="Test pending migrations by going through update and downgrade")
test_parser.set_defaults(cmd=cmd_test)
test_parser.add_argument("-r", "--revision",
                         help=("Revision to upgrade to. If not specified, "
                               "latest revision will be used"))


def load_config(fname):
    if not os.path.exists(fname):
        raise exceptions.ConfigurationError("%s is missing" % fname)
    cfg = SafeConfigParser()
    with open(fname) as cfgfp:
        cfg.readfp(cfgfp)
    return cfg


def get_db_config(cfg, name):
    if not cfg.has_section(name):
        ava = ', '.join(cfg.sections())
        raise exceptions.ConfigurationError(
            "No database %s in migrant.ini, available names: %s" % (name, ava))
    return dict(cfg.items(name))


def setup_logging(args, cfg):
    logging.basicConfig(level=logging.INFO)


def dispatch(args, cfg):
    args.cmd(args, cfg)


def main(args=sys.argv[1:]):
    args = parser.parse_args(args)
    try:
        cfg = load_config(args.config)
        setup_logging(args, cfg)
        dispatch(args, cfg)
    except exceptions.MigrantException as e:
        sys.exit("fatal: %s" % e)
