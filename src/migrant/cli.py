###############################################################################
#
# Copyright 2014 by Shoobx, Inc.
#
###############################################################################
import os
import sys
import click
import logging
from configparser import ConfigParser

from migrant import exceptions
from migrant.engine import MigrantEngine
from migrant.backend import create_backend
from migrant.repository import create_repo

#FORMAT = "%(asctime)s %(levelname)s %(module)s - %(message)s"
#logging.basicConfig(level=logging.INFO, format=FORMAT)
log = logging.getLogger(__name__)


@click.group()
@click.option(
    "-c",
    "--config",
    default="migrant.ini",
    help="Config file to be used",
    required=True,
    type=click.Path(exists=True),
)
@click.argument("database")
@click.pass_context
def cli(ctx, **kwargs):
    ctx.obj = kwargs
    ctx.obj["cfg"] = load_config(ctx.obj["config"])


@cli.command("init")
@click.pass_obj
def cmd_init(obj):
    """Initialize migration script repository"""
    cfg = get_db_config(obj["cfg"], obj["database"])
    repo = create_repo(cfg)
    repo.init()
    backend = create_backend(cfg)
    backend.on_repo_init()


@cli.command("new")
@click.option("--title", help="Migration script title")
@click.pass_obj
def cmd_new(obj, title):
    """Create new migration script, add a script title argument!"""
    obj["title"] = title
    cfg = get_db_config(obj["cfg"], obj["database"])
    repo = create_repo(cfg)
    revname = repo.new_script(obj["title"])
    backend = create_backend(cfg)
    backend.on_new_script(revname)


@cli.command("upgrade")
@click.option(
    "-n",
    "--dry-run",
    help="do not execute scripts, only show what is going to be executed.",
    is_flag=True,
)
@click.option(
    "-r",
    "--revision",
    help="Revision to upgrade to. If not specified, latest revision will be used",
)
@click.pass_obj
def cmd_upgrade(obj, dry_run, revision):
    """Perform upgrade"""
    obj["dry_run"] = dry_run
    obj["revision"] = revision
    cfg = get_db_config(obj["cfg"], obj["database"])
    repo = create_repo(cfg)
    backend = create_backend(cfg)
    engine = MigrantEngine(backend, repo, cfg, dry_run=obj["dry_run"])
    engine.update(obj["revision"])


@cli.command("test")
@click.option(
    "-r",
    "--revision",
    help="Revision to upgrade to. If not specified, latest revision will be used",
)
@click.pass_obj
def cmd_test(obj):
    """Test pending migrations by going through update and downgrade"""
    cfg = get_db_config(obj["cfg"], obj["database"])
    repo = create_repo(cfg)
    backend = create_backend(cfg)
    engine = MigrantEngine(backend, repo, cfg)
    engine.test(obj["revision"])


@cli.command("status")
@click.pass_obj
def cmd_status(obj):
    """Show the migration status"""
    cfg = get_db_config(obj["cfg"], obj["database"])
    repo = create_repo(cfg)
    backend = create_backend(cfg)
    engine = MigrantEngine(backend, repo, cfg)
    actions = engine.status()
    if actions:
        log.info("Pending actions: %s", actions)
    else:
        log.info("Up-to-date")


def load_config(fname):
    if not os.path.exists(fname):
        raise exceptions.ConfigurationError("%s is missing" % fname)
    cfg = ConfigParser()
    with open(fname) as cfgfp:
        cfg.read_file(cfgfp)
    return cfg


def get_db_config(cfg, name):
    if not cfg.has_section(name):
        ava = ", ".join(cfg.sections())
        raise exceptions.ConfigurationError(
            f"No database {name} in migrant.ini, available names: {ava}"
        )
    return dict(cfg.items(name))


if __name__ == "__main__":
    cli()
