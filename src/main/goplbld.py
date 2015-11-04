#!/usr/bin/python -tt
# coding:utf-8

import sys
import argparse

from go_proxy import GoProxy
from model import Pipeline

def main(args=sys.argv):
    fail = 0
    argparser = argparse.ArgumentParser(
        description="Add pipeline to Go CD server.")
    argparser.add_argument(
        "-s", "--settings",
        type=argparse.FileType('r'),
        help="Yaml file with settings for GoCD pipeline."
    )
    argparser.add_argument(
        "-c", "--config",
        type=argparse.FileType('r'),
        help="Yaml file with configuration."
    )
    argparser.add_argument(
        "-d", "--dump",
        type=argparse.FileType('w'),
        help="Copy of new GoCD configuration XML file."
    )
    argparser.add_argument(
        "-n", "--dry-run",
        type=bool,
        help="Don't actually update the Go server."
    )

    pargs = argparser.parse_args(args[1:])

    go = GoProxy(pargs.config, pargs.dry_run)

    if pargs.settings is not None:
        go.add_pipeline(Pipeline(pargs.settings))
        fail = go.upload_config()

    if fail:
        # Reload config
        go.init()

    if pargs.dump is not None:
        envelope = '<?xml version="1.0" encoding="utf-8"?>\n%s'
        pargs.dump.write(envelope % go.cruise_xml)

    sys.exit(fail)


if __name__ == '__main__':
    main()
