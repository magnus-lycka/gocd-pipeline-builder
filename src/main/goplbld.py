#!/usr/bin/python -tt
# coding:utf-8

import sys
import yaml
import json
import argparse
import requests
from xml.etree import ElementTree
from jinja2 import Template


class CruiseTree(ElementTree.ElementTree):
    @classmethod
    def fromstring(cls, text):
        return cls(ElementTree.fromstring(text))

    def tostring(self):
        self.indent(self.getroot())
        return ElementTree.tostring(self.getroot())

    @classmethod
    def indent(cls, elem, level=0):
        """
        Fredrik Lundh's standard recipe.
        (Why isn't this in xml.etree???)
        """
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                cls.indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i


class GoProxy(object):
    def __init__(self, config, dry_run):
        self._config = yaml.load(config)
        self.dry_run = dry_run
        self._cruise_config_md5 = None
        self.init()

    def init(self):
        self.tree = CruiseTree.fromstring(self.xml_from_source())
        self._initial_xml = self.cruise_xml

    @property
    def cruise_xml(self):
        return self.tree.tostring()

    def xml_from_source(self):
        if 'url' in self._config:
            return self.xml_from_url()
        elif 'xml_file' in self._config:
            return self.xml_from_local_file()

    def xml_from_local_file(self):
        with open(self._config['xml_file']) as xml_file:
            return xml_file.read()

    def xml_from_url(self):
        url = self._config['url'] + "/go/admin/restful/configuration/file/GET/xml"
        response = requests.get(url)
        self._cruise_config_md5 = response.headers['x-cruise-config-md5']
        return response.text

    def add_pipeline(self, pipeline):
        group_name = pipeline.pipeline_group
        pipeline_groups = {pipelines.get('group'): pipelines
                           for pipelines in self.tree.findall('pipelines')}
        pipeline_group = pipeline_groups[group_name]
        environment_list = self.tree.findall('environments/environment')
        try:
            pipeline.append_self(pipeline_group, environment_list)
        except KeyError:
            raise KeyError('Pipeline group %s not found among %s'
                           % (group_name, pipeline_groups))

    def upload_config(self):
        if self.dry_run:
            print "Dry run. Not uploading config."
        elif self.cruise_xml == self._initial_xml:
            print "No changes done. Not uploading config."
        elif 'url' not in self._config:
            print "No Go server configured. Not uploading config."
        else:
            url = self._config['url'] + '/go/admin/restful/configuration/file/POST/xml'
            data = {'xmlFile': self.cruise_xml, 'md5': self._cruise_config_md5}
            response = requests.post(url, data)
            if response.status_code != 200:
                sys.stderr.write("status-code: %s\n" % response.status_code)
                # GoCD produces broken JSON???, see
                # https://github.com/gocd/gocd/issues/1472
                # (Or is something strange going on with requests?)
                json_data = json.loads(response.text.replace("\\'", "'"))
                sys.stderr.write("result: %s\n" % json_data["result"])
                sys.stderr.write("originalContent:\n%s\n" % json_data["originalContent"])
                return 1


class Pipeline(object):
    def __init__(self, settings_file):
        self.pipeline_group = None
        self.structure = None
        self.element = None
        self.materials = None
        self.stage = None
        self.job = None
        self.tasks = None
        self.environment = None
        self.load_structure(settings_file)

    def load_structure(self, settings_file):
        structure = yaml.load(settings_file)
        if 'pattern' in structure:
            template = Template(open(structure['pattern']['path']).read())
            structure = yaml.load(template.render(structure['pattern']['parameters']))
        self.pipeline_group = structure['pipelines']['group']
        self.structure = structure['pipeline']
        self.environment = structure.get('environment')

    def append_self(self, parent, environment_list):
        self.element = ElementTree.SubElement(parent, 'pipeline')
        self.set_name()
        self.set_params()
        self.set_environmentvariables()
        self.set_materials()
        if 'template' in self.structure:
            self.element.set('template', self.structure['template'])
        else:
            self.set_stages()
        self.place_in_environment(environment_list)

    def set_name(self):
        self.element.set('name', self.structure['name'])

    def set_params(self):
        if 'params' in self.structure:
            params = ElementTree.SubElement(self.element, 'params')
            for param in self.structure['params']:
                for key, value in param.items():
                    param_elm = ElementTree.SubElement(params, 'param')
                    param_elm.set('name', key)
                    param_elm.text = value

    def set_environmentvariables(self):
        if 'environmentvariables' in self.structure:
            env_elm = ElementTree.SubElement(self.element, 'environmentvariables')
            for env in self.structure['environmentvariables']:
                for key, value in env.items():
                    variable_elm = ElementTree.SubElement(env_elm, 'variable')
                    variable_elm.set('name', key)
                    value_elm = ElementTree.SubElement(variable_elm, 'value')
                    value_elm.text = value

    def set_materials(self):
        assert self.structure['materials']
        self.materials = ElementTree.SubElement(self.element, 'materials')
        for material in self.structure['materials']:
            for kind, content in material.items():
                if kind == 'git':
                    self.set_git_material(content)
                else:
                    raise ValueError('Unknown material: %s' % kind)

    def set_git_material(self, material):
        git = ElementTree.SubElement(self.materials, 'git')
        for key, value in material.items():
            git.set(key, value)

    def set_stages(self):
        for stage in self.structure['stages']:
            self.stage = ElementTree.SubElement(self.element, 'stage')
            self.stage.set('name', stage['stage']['name'])
            self.set_jobs(stage['stage']['jobs'])

    def set_jobs(self, jobs):
        jobs_elm = ElementTree.SubElement(self.stage, 'jobs')
        for job in jobs:
            self.job = ElementTree.SubElement(jobs_elm, 'job')
            self.job.set('name', job['job']['name'])
            self.set_tasks(job['job']['tasks'])

    def set_tasks(self, tasks):
        self.tasks = ElementTree.SubElement(self.job, 'tasks')
        for task in tasks:
            for kind, content in task.items():
                if kind == 'exec':
                    self.set_exec(content)
                else:
                    raise ValueError('Unknown task type: %s' % kind)

    def set_exec(self, task):
        task_elm = ElementTree.SubElement(self.tasks, 'exec')
        for key, value in task.items():
            if key == 'arg':
                for argument in value:
                    arg = ElementTree.SubElement(task_elm, 'arg')
                    arg.text = argument
            else:
                task_elm.set(key, value)

    def place_in_environment(self, environment_list):
        if self.environment:
            for environment in environment_list:
                if environment.get('name') == self.environment:
                    pipelines = environment.find('pipelines')
                    if pipelines is None:
                        pipelines = ElementTree.SubElement(environment, 'pipelines')
                    pipeline = ElementTree.SubElement(pipelines, 'pipeline')
                    pipeline.set('name', self.structure['name'])
                    break
            else:  # No break
                print "Environment %s not found in config" % self.environment


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
