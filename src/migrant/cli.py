###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################

import argparse
import logging

log = logging.getLogger(__name__)


def cmd_new(args):
    print "NEW", args


def cmd_upgrade(args):
    print "UPGRADE", args


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


def main():
    args = parser.parse_args()
    args.cmd(args)
    print args.cmd
