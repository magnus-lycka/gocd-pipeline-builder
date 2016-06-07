from __future__ import print_function
import sys
import json
import os.path
from collections import OrderedDict, defaultdict
from xml.etree import ElementTree

import yaml
from jinja2 import Template


class GoProxy(object):
    """
    Intercept calls to go.create_a_pipeline_wrapper
    to figure out which pipelines should potentially
    be added to environment, unpaused etc.
    """
    def __init__(self, go_server, settings):
        self.go = go_server
        self.settings = settings

    def __getattr__(self, item):
        if item == 'create_a_pipeline':
            return self.create_a_pipeline_wrapper
        else:
            return getattr(self.go, item)

    def create_a_pipeline_wrapper(self, pipeline):
        self.go.create_a_pipeline(pipeline)
        self.settings.pipeline_names.append(pipeline["pipeline"]["name"])
        self.settings.pipeline_stage_names.append([
            stage["name"] for stage
            in pipeline["pipeline"].get("stages") or []
        ])


class JsonSettings(object):
    """
    A json file passed to the this class should have the following structure:
    [
        {
            "<key>": <value>,
        },
    ]

    See README.md for details.
    """
    def __init__(self, settings_file, extra_settings, verbose=False):
        self.list = None
        self.verbose = verbose
        self.load_file(settings_file, extra_settings)
        self.pipeline_names = []
        self.pipeline_stage_names = []
        self.pipeline_group_map = {}
        self.action_plugins = OrderedDict()

    def load_file(self, settings_file, extra_settings):
        self.load_template(settings_file, extra_settings)

    def load_template(self, template_data, parameters):
        template = Template(template_data)
        data = self.get_default_parameters()
        data.update(parameters)
        json_text = template.render(data)
        if self.verbose:
            print("Rendered json settings:\n\n{}\n".format(json_text))
        self.list = json.loads(json_text,
                               object_pairs_hook=OrderedDict)

    def register_plugin(self, module):
        self.action_plugins.update(module.action_plugins)

    @staticmethod
    def get_default_parameters(git_config_path='.git/config'):
        data = {}
        if os.path.exists(git_config_path):
            for row in open(git_config_path):
                if row.strip().startswith('url = '):
                    data['repo_url'] = row.split('=')[1].strip()
        data['repo_name'] = os.path.basename(os.getcwd())
        return data

    def server_operations(self, go):
        go = GoProxy(go, self)
        for operation in self.list:
            for action, plugin in self.action_plugins.items():
                if action in operation:
                    plugin(go=go, operation=operation[action])
            if "create-a-pipeline" in operation:
                go.create_a_pipeline(operation["create-a-pipeline"])
            if self.pipeline_names and "environment" in operation:
                go.init()
                self.update_environment(go.tree, operation)
                if go.need_to_upload_config:
                    go.upload_config()
            if "add-downstream-dependencies" in operation:
                dependency_updates = operation["add-downstream-dependencies"]
                for dependency_update in dependency_updates:
                    downstream_name = dependency_update["name"]
                    etag, pipeline = go.get_pipeline_config(downstream_name)
                    # If this pipeline uses a template, we need to use that!!!
                    self.add_downstream_dependencies(pipeline, dependency_update)
                    go.edit_pipeline_config(downstream_name, etag, pipeline)
            for pipeline_name in self.pipeline_names:
                if "unpause" in operation and operation["unpause"]:
                    go.unpause(pipeline_name)
                if go.verbose:
                    status = go.get_pipeline_status(pipeline_name)
                    print(json.dumps(status, indent=4, sort_keys=True))

    def add_downstream_dependencies(self, pipeline, update):
        if "material" in update:
            pipeline["materials"].append(update["material"])
        if "task" in update:
            self.ensure_dependency_material(pipeline)
            if "stages" in pipeline:
                job = self.get_job(pipeline, update)
                job["tasks"].insert(0, update["task"])
            else:
                sys.stderr.write("Adding tasks to template not supported!\n")

    def ensure_dependency_material(self, pipeline):
        for material in pipeline['materials']:
            if material['type'] == 'dependency' and material['attributes']['pipeline']:
                return
        # Expected dependency material not found. Add default.
        if self.pipeline_stage_names and (len(self.pipeline_stage_names[-1]) == 1):
            pipeline['materials'].append(
                {
                    "type": "dependency",
                    "attributes": {
                        "pipeline": self.pipeline_names[-1],
                        "stage": self.pipeline_stage_names[-1][0],
                        "auto_update": True
                    }
                }
            )
        else:
            raise ValueError('Explicit dependency material is needed unless'
                             ' there is exactly one stage in new pipeline')

    # We only call get_job if we actually have stages
    # noinspection PyUnboundLocalVariable
    @staticmethod
    def get_job(pipeline, update):
        if "stage" in update:
            for stage in pipeline["stages"]:
                if stage["name"] == update["stage"]:
                    break
        else:
            stage = pipeline["stages"][0]
        if "job" in update:
            for job in stage["jobs"]:
                if job["name"] == update["job"]:
                    break
        else:
            job = stage["jobs"][0]
        return job

    def update_environment(self, configuration, operation):
        """
        If the setting names an environment, the pipelines in the
        setting, should be assigned to that environment in the cruise-config.
        :param configuration: Go configuration as xml.etree.ElementTree
        :param operation: Operation to perform in the Json settings
        """
        conf_environments = configuration.find('environments')
        if conf_environments is None:
            print("No environments section in configuration.")
            return
        op_env_name = operation.get('environment')
        if not op_env_name:
            return
        for conf_environment in conf_environments.findall('environment'):
            if conf_environment.get('name') == op_env_name:
                for name in self.pipeline_names:
                    self._set_pipeline_in_environment(name, conf_environment)
                break

    @staticmethod
    def _set_pipeline_in_environment(name, conf_environment):
        conf_pipelines = conf_environment.find('pipelines')
        if conf_pipelines is None:
            conf_pipelines = ElementTree.SubElement(
                conf_environment, 'pipelines')
        # TODO: Check if already there?
        conf_pipeline = ElementTree.SubElement(conf_pipelines, 'pipeline')
        conf_pipeline.set('name', name)


class YamlSettings(JsonSettings):
    """
    A YamlSettings object is initiated with a yaml
    file, which has a 'path', indicating a json template
    file, and 'parameters', where we find a dictionary
    that we can pass to the template. This dictionary
    might contains parameters that override default
    parameters in the base class.
    """
    def load_file(self, settings_file, extra_settings):
        """
        Find the json template and parameter in the yaml file,
        render the template, and pass it to the super class.
        :param settings_file: Yaml file
        :param extra_settings: settings from e.g. command line
        """
        settings = yaml.load(settings_file)
        template_path = settings['path']
        parameters = settings['parameters']
        parameters.update(extra_settings)
        self.load_template(open(template_path).read(), parameters)


def last_modification(modifications):
        return sorted(modifications, key=lambda rev: rev['modified_time'])[-1]


class SourceMaterial(object):
    def __init__(self, material_revision):
        self.__type = material_revision['material']['type']
        self.__description = material_revision['material']['description']
        last_mod = last_modification(material_revision['modifications'])
        self.__revision = last_mod['revision']

    def as_dict(self, **kwargs):
        data = dict(type=self.__type,
                    description=self.__description,
                    revision=self.__revision)
        data.update(kwargs)
        return data

    def __str__(self):
        return "; ".join((self.__type, self.__description, self.__revision))

    def __hash__(self):
        return hash(self.__revision)

    def __eq__(self, other):
        return self.__revision == other.__revision


class Pipeline(object):
    def __init__(self, pipeline_instance, go, output_format):
        self.pipeline, self.instance = pipeline_instance.split('/')[:2]
        self.go = go
        self.format = output_format
        self.upstreams = []
        self.source_repos = []
        self.recursive_repos = defaultdict(set)

    def print_recursive_repos(self):
        self.prepare_recursive_repos()
        self.collect_recursive_repos()
        if self.format == 'json':
            repos = [repo.as_dict(pipelines=[dict(zip(('name', 'counter'), pl)) for pl in pipelines])
                     for repo, pipelines in self.recursive_repos.items()]
            print(json.dumps(repos, indent=4, sort_keys=True))
        elif self.format == 'semicolon':
            for repo, pipelines in self.recursive_repos.items():
                print("%s; %s" % (repo, ", ".join(["%s/%s" % (p, i) for p, i in pipelines])))
        else:
            raise TypeError("Don't know how to print in format: {}".format(self.format))

    def prepare_recursive_repos(self):
        pipeline_instance = self.go.get_pipeline_instance(self.pipeline, self.instance)
        for material_revision in pipeline_instance['build_cause']['material_revisions']:
            if material_revision['material']['type'] == 'Pipeline':
                last_mod = last_modification(material_revision['modifications'])
                upstream_pipeline = Pipeline(last_mod['revision'], self.go, self.format)
                self.upstreams.append(upstream_pipeline)
                upstream_pipeline.prepare_recursive_repos()
            else:
                self.source_repos.append(SourceMaterial(material_revision))

    def collect_recursive_repos(self):
        for upstream in self.upstreams:
            upstream.collect_recursive_repos()
            for repo in upstream.recursive_repos:
                self.recursive_repos[repo].update(upstream.recursive_repos[repo])
        for repo in self.source_repos:
            self.recursive_repos[repo].add((self.pipeline, self.instance))
