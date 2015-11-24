from xml.etree import ElementTree
import yaml
from jinja2 import Template


class Pipeline(object):
    def __init__(self, settings_file):
        self.pipeline_group = None
        self.structure = None
        self.element = None
        self.materials = None
        self.stage = None
        self.job = None
        self.tasks = None
        self.load_structure(settings_file)

    def load_structure(self, settings_file):
        structure = yaml.load(settings_file)
        if 'pattern' in structure:
            template = Template(open(structure['pattern']['path']).read())
            structure = yaml.load(
                template.render(structure['pattern']['parameters']))
        self.pipeline_group = structure['pipelines']['group']
        self.structure = structure['pipeline']

    def append_self(self, parent):
        self.element = ElementTree.SubElement(parent, 'pipeline')
        self.set_name()
        self.set_params()
        self.set_environmentvariables()
        self.set_materials()
        if 'template' in self.structure:
            self.element.set('template', self.structure['template'])
        else:
            self.set_stages()

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
            env_elm = ElementTree.SubElement(self.element,
                                             'environmentvariables')
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
