#!/usr/bin/python -tt
# coding:utf-8
import sys
import argparse
from go_proxy import GoProxy
from model import JsonSettings, YamlSettings


def main(args=sys.argv):
    argparser = argparse.ArgumentParser(
        description="Add pipeline to Go CD server."
    )
    main_action_group = argparser.add_mutually_exclusive_group()
    main_action_group.add_argument(
        "-j", "--json-settings",
        type=argparse.FileType('r'),
        help="Read raw json file with settings for GoCD pipeline."
    )
    main_action_group.add_argument(
        "-y", "--yaml-settings",
        type=argparse.FileType('r'),
        help="Read yaml files with parameters for GoCD pipeline."
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
    argparser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Write status of created pipeline."
    )

    pargs = argparser.parse_args(args[1:])

    go = GoProxy(pargs.config, pargs.verbose)

    if pargs.set_test_config is not None:
        go.tree.set_test_settings_xml(pargs.set_test_config)
        go.upload_config()

    if pargs.json_settings is not None:
        JsonSettings(pargs.json_settings).server_operations(go)

    if pargs.yaml_settings is not None:
        YamlSettings(pargs.yaml_settings).server_operations(go)

    if pargs.dump is not None:
        go.init()
        envelope = '<?xml version="1.0" encoding="utf-8"?>\n%s'
        pargs.dump.write(envelope % go.cruise_xml)

    if pargs.dump_test_config is not None:
        go.init()
        envelope = '<?xml version="1.0" encoding="utf-8"?>\n%s'
        pargs.dump_test_config.write(envelope % go.cruise_xml_subset)


if __name__ == '__main__':
    main()
