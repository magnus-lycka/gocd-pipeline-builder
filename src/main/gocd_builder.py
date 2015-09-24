#!/usr/bin/env python

import argparse
from gomatic import GoCdConfigurator, HostRestClient
import os 
from mako.template import Template
import yaml

GOSERVER = os.environ['GOSERVER']


def main(template_file, settings_file):
    print("Hello World!")
    update_pipeline()
    read_some_config(template_file, settings_file)


def expand_vars(dictionary):
    for key in dictionary:
        dictionary[key] = os.path.expandvars(dictionary[key])


def read_some_config(template_file, settings_file):
    import pprint
    settings = yaml.load(settings_file.read())
    expand_vars(settings)
    template = Template(template_file.read())
    pprint.pprint(yaml.load(template.render(**settings)))

def update_pipeline():
    configurator = GoCdConfigurator(HostRestClient(GOSERVER))
    #configurator = GoCdConfigurator(FakeHostRestClient(empty_config_xml))

    pipeline = configurator\
        .ensure_pipeline_group("defaultGroup")\
        .ensure_replacement_of_pipeline("test_pipeline")\
        .set_git_url("http://git/git/pageroonline/services/factoring/factoring.git")
    stage = pipeline.ensure_stage("defaultStage")
    job = stage.ensure_job("defaultJob")

    configurator.save_updated_config(save_config_locally=True, dry_run=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="turns a template file into a gocd pipeline")
    parser.add_argument("--template-file", '-t', type=argparse.FileType('r'),
                        help="Use this template file as the basis for a new go cd pipeline")
    parser.add_argument("--settings-file", '-s', type=argparse.FileType('r'),
                        help="use this settings file to insert values into the template file given")

    parsed_args = parser.parse_args()
    print repr(parsed_args)
    args_as_dict = vars(parsed_args)  # convert Namespace object to python dictionary

    print "will create pipeline using template {template_file} and settings {settings_file}".format(**args_as_dict)
    main(**args_as_dict)
