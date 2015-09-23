#!/usr/bin/env python

import argparse

def main(template_file, settings_file):
	print("Hello World!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="turns a template file into a gocd pipeline")
    parser.add_argument("--template-file", '-t', help="Use this template file as the basis for a new go cd pipeline")
    parser.add_argument("--settings-file", '-s', help="use this settings file to insert values into the template file given")

    parsed_args = parser.parse_args()
    args_as_dict = vars(parsed_args) # convert Namespace object to python dictionary

    print "will create pipeline using template {template_file} and settings {settings_file}".format(**args_as_dict)
    main(**args_as_dict)
