#!/usr/bin/python -tt
# coding:utf-8

import sys
import yaml
import argparse
import requests
from xml.etree import ElementTree


def indent(elem, level=0):
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
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i



class CruiseTree(ElementTree.ElementTree):
    @classmethod
    def fromstring(cls, text):
        return cls(ElementTree.fromstring(text))

    def tostring(self):
        return ElementTree.tostring(self.getroot())


class GoProxy(object):
    def __init__(self, config):
        self._config = yaml.load(config)
        self.tree = CruiseTree.fromstring(self.xml_from_source())

    @property
    def cruise_xml(self):
        indent(self.tree.getroot())
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
        return response.text

    def add_pipeline(self, pipeline):
        found_groups = []
        for pipelines in self.tree.findall('pipelines'):
            group_name = pipelines.get('group')
            found_groups.append(group_name)
            if group_name == pipeline.pipeline_group:
                pipeline.append_self(pipelines)
                break
        else:
            raise ValueError('Pipeline group %s not found among %s' %
                             (pipeline.pipeline_group, ", ".join(found_groups)))


class Pipeline(object):
    def __init__(self, settings_file):
        structure = yaml.load(settings_file)
        self.pipeline_group = structure['pipelines']['group']
        self.structure = structure['pipeline']
        self.element = None
        self.materials = None
        self.stage = None

    def append_self(self, parent):
        self.element = ElementTree.SubElement(parent, 'pipeline')
        self.set_name()
        self.set_materials()
        self.set_stages()

    def set_name(self):
        self.element.set('name', self.structure['name'])

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


def main(args=sys.argv):
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
    pargs = argparser.parse_args(args[1:])

    go = GoProxy(pargs.config)

    if pargs.settings is not None:
        go.add_pipeline(Pipeline(pargs.settings))

    if pargs.dump is not None:
        envelope = '<?xml version="1.0" encoding="utf-8"?>\n%s'
        pargs.dump.write(envelope % go.cruise_xml)


if __name__ == '__main__':
    main()
