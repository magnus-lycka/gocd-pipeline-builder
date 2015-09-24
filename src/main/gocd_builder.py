#!/usr/bin/env python

import argparse
from gomatic import *  # TODO Usch!
import os 

GOSERVER = os.environ['GOSERVER']


def main(template_file, settings_file):
    print("Hello World!")
    update_pipeline()


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
    parser.add_argument("--template-file", '-t', help="Use this template file as the basis for a new go cd pipeline")
    parser.add_argument("--settings-file", '-s', help="use this settings file to insert values into the template file given")

    parsed_args = parser.parse_args()
    args_as_dict = vars(parsed_args) # convert Namespace object to python dictionary

    print "will create pipeline using template {template_file} and settings {settings_file}".format(**args_as_dict)
    main(**args_as_dict)
