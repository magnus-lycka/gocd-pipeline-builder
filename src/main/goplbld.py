#!/usr/bin/python -tt
# coding:utf-8
import sys
import argparse
from go_proxy import GoProxy
from model import get_settings


def main(args=sys.argv):
    argparser = argparse.ArgumentParser(
        description="Add pipeline to Go CD server."
    )
    argparser.add_argument(
        "-s", "--settings",
        type=argparse.FileType('r'),
        help="Yaml or Json file with settings for GoCD pipeline."
    )
    argparser.add_argument(
        "-c", "--config",
        type=argparse.FileType('r'),
        help="Yaml file with configuration."
    )
    argparser.add_argument(
        "--set-test-config",
        type=argparse.FileType('r'),
        help="Set some sections in config first. (For test setup.)"
    )
    argparser.add_argument(
        "--dump-test-config",
        type=argparse.FileType('w'),
        help="Copy of some sections of new GoCD configuration XML file."
    )
    argparser.add_argument(
        "-d", "--dump",
        type=argparse.FileType('w'),
        help="Copy of new GoCD configuration XML file."
    )

    pargs = argparser.parse_args(args[1:])

    go = GoProxy(pargs.config)

    if pargs.set_test_config is not None:
        go.set_test_settings_xml(pargs.set_test_config)
        go.upload_config()

    if pargs.settings is not None:
        go.add_settings(get_settings(pargs.settings))

    go.init()

    if pargs.dump is not None:
        envelope = '<?xml version="1.0" encoding="utf-8"?>\n%s'
        pargs.dump.write(envelope % go.cruise_xml)

    if pargs.dump_test_config is not None:
        envelope = '<?xml version="1.0" encoding="utf-8"?>\n%s'
        pargs.dump_test_config.write(envelope % go.cruise_xml_subset)


if __name__ == '__main__':
    main()
