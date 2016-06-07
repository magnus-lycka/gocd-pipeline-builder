#!/usr/bin/python -tt
# coding:utf-8
from __future__ import print_function
import sys
import getpass
import argparse
import importlib
import requests
from goserver_adapter import Goserver
from gocd_settings import JsonSettings, YamlSettings, Pipeline


def list2dict(list_of_pairs):
    return dict(tuple(pair.split('=', 1) for pair in list_of_pairs or []))


def add_secrets_to_config(config, password_parameters):
    for password_parameter in password_parameters or []:
        config[password_parameter] = getpass.getpass(password_parameter + ': ')


def get_json_settings(path):
    if path.startswith('http'):
        response = requests.get(path)
        assert response.status_code == 200
        return response.text
    else:
        return open(path).read()


def repos(args=sys.argv):
    argparser = argparse.ArgumentParser(
        description="Recursively fetch all source code revisions used in a pipeline build."
    )
    argparser.add_argument(
        "pipeline_instance",
        help="pipeline/instance to start at."
    )
    argparser.add_argument(
        "-f", "--format",
        choices=['semicolon', 'json'],
        default='json',
        help="Format for output."
    )

    go, pargs = init_run(argparser, args)

    Pipeline(pargs.pipeline_instance, go, pargs.format).print_recursive_repos()


def main(args=sys.argv):
    argparser = argparse.ArgumentParser(
        description="Add pipeline to Go CD server."
    )
    main_action_group = argparser.add_mutually_exclusive_group()
    main_action_group.add_argument(
        "-j", "--json-settings",
        help="Read json file / url with settings for GoCD pipeline."
    )
    main_action_group.add_argument(
        "-y", "--yaml-settings",
        type=argparse.FileType('r'),
        help="Read yaml files with parameters for GoCD pipeline."
    )
    argparser.add_argument(
        "-p", "--plugin",
        action="append",
        help="Plugin module for custom functions."
    )
    argparser.add_argument(
        "-D", "--define",
        action="append",
        help="Define setting parameter on command line."
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

    go, pargs = init_run(argparser, args)

    settings = None
    if pargs.json_settings:
        json_settings = get_json_settings(pargs.json_settings)
        settings = JsonSettings(json_settings, list2dict(pargs.define), verbose=pargs.verbose)

    if pargs.yaml_settings is not None:
        settings = YamlSettings(pargs.yaml_settings, list2dict(pargs.define), verbose=pargs.verbose)

    if settings:
        if pargs.plugin:
            for plugin in pargs.plugin:
                settings.register_plugin(importlib.import_module(plugin))
        settings.server_operations(go)

    if pargs.dump is not None:
        go.init()
        envelope = '<?xml version="1.0" encoding="utf-8"?>\n%s'
        pargs.dump.write(envelope % go.cruise_xml)

    if pargs.dump_test_config is not None:
        go.init()
        envelope = '<?xml version="1.0" encoding="utf-8"?>\n%s'
        pargs.dump_test_config.write(envelope % go.cruise_xml_subset)


def init_run(argparser, args):
    argparser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Write status of created pipeline."
    )
    argparser.add_argument(
        "-c", "--config",
        type=argparse.FileType('r'),
        help="Yaml file with configuration."
    )
    argparser.add_argument(
        "-C", "--config-param",
        action="append",
        help="Define config parameter on command line."
    )
    argparser.add_argument(
        "-P", "--password-prompt",
        action="append",
        help="Prompt for config parameter without echo."
    )
    argparser.add_argument(
        "--set-test-config",
        type=argparse.FileType('r'),
        help="Set some sections in config first. (For test setup.)"
    )
    pargs = argparser.parse_args(args[1:])
    extra_config = list2dict(pargs.config_param)
    add_secrets_to_config(extra_config, pargs.password_prompt)
    go = Goserver(pargs.config, pargs.verbose, extra_config)
    try:
        go.check_config()
    except AssertionError as error:
        print("Missing '{}' in configuration.".format(error))
        sys.exit(1)
    go.init()
    if pargs.set_test_config is not None:
        go.tree.set_test_settings_xml(pargs.set_test_config)
        go.upload_config()
    return go, pargs


if __name__ == '__main__':
    main()
