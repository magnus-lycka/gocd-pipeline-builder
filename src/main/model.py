import copy
import sys
import json
import os.path
from collections import OrderedDict
import yaml
from jinja2 import Template
from xml.etree import ElementTree


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
    def __init__(self, settings_file, extra_settings):
        self.list = None
        self.load_file(settings_file, extra_settings)
        self.pipeline_name = None
        self.pipeline_stage_names = []

    def server_operations(self, go):
        for operation in self.list:
            if "create-a-pipeline" in operation:
                go.create_a_pipeline(operation["create-a-pipeline"])
                self.pipeline_name = operation["create-a-pipeline"]["pipeline"]["name"]
                self.pipeline_stage_names = [
                    stage["name"] for stage
                    in operation["create-a-pipeline"]["pipeline"].get("stages", [])
                ]
            if self.pipeline_name and "environment" in operation:
                go.init()
                self.update_environment(go.tree)
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
            if "unpause" in operation and operation["unpause"]:
                go.unpause(self.pipeline_name)
            if self.pipeline_name and go.verbose:
                status = go.get_pipeline_status(self.pipeline_name)
                print json.dumps(status, indent=4, sort_keys=True)

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
        if len(self.pipeline_stage_names) == 1:
            pipeline['materials'].append(
                {
                    "type": "dependency",
                    "attributes": {
                        "pipeline": self.pipeline_name,
                        "stage": self.pipeline_stage_names[0],
                        "auto_update": True
                    }
                }
            )
        else:
            raise ValueError('Explicit dependency material is needed unless'
                             ' there is exactly one stage in new pipeline')

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

    def load_file(self, settings_file, extra_settings):
        self.load_template(settings_file, extra_settings)

    def load_template(self, template, parameters):
        template = Template(template.read())
        data = self.get_default_parameters()
        data.update(parameters)
        self.list = json.loads(template.render(data),
                               object_pairs_hook=OrderedDict)

    @staticmethod
    def get_default_parameters(git_config_path='.git/config'):
        data = {}
        if os.path.exists(git_config_path):
            for row in open(git_config_path):
                if row.strip().startswith('url = '):
                    data['repo_url'] = row.split('=')[1].strip()
        data['repo_name'] = os.path.basename(os.getcwd())
        return data

    def update_environment(self, configuration):
        """
        If the setting names an environment, the pipelines in the
        setting, should be assigned to that environment in the cruise-config.
        """
        conf_environments = configuration.find('environments')
        if conf_environments is None:
            print "No environments section in configuration."
            return
        for operation in self.list:
            op_env_name = operation.get('environment')
            if not op_env_name:
                continue
            for conf_environment in conf_environments.findall('environment'):
                if conf_environment.get('name') == op_env_name:
                    data = operation.get('create-a-pipeline')
                    if data:
                        pipeline = data.get('pipeline')
                        name = pipeline.get('name')
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
        """
        settings = yaml.load(settings_file)
        template_path = settings['path']
        parameters = settings['parameters']
        parameters.update(extra_settings)
        self.load_template(open(template_path), parameters)


class CruiseTree(ElementTree.ElementTree):
    """
    A thin layer on top of the cruise-config.xml used by the Go server.
    """
    @classmethod
    def fromstring(cls, text):
        return cls(ElementTree.fromstring(text))

    def tostring(self):
        self.indent(self.getroot())
        return ElementTree.tostring(self.getroot())

    def config_subset_tostring(self):
        """
        See GoProxy.set_test_settings_xml()
        """
        root = copy.deepcopy(self).getroot()
        for child in list(root):
            if child.tag not in ('pipelines', 'templates', 'environments'):
                root.remove(child)
        self.indent(root)
        return ElementTree.tostring(root)

    @classmethod
    def indent(cls, elem, level=0):
        """
        Fredrik Lundh's standard recipe.
        (Why isn't this in xml.etree???)
        """
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                cls.indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def set_test_settings_xml(self, test_settings_xml):
        """
        Replace parts of the Go server config for test purposes

        The main sections in the config are:
        - server
        - repositories
        - pipelines * N
        - templates
        - environments
        - agents
        We want to replace the sections pipelines*, templates and environments.
        Let server and agents stay as usual.
        We've never used repositories so far.
        """
        root = self.getroot()

        self.drop_sections_to_be_replaced(root)

        test_settings = CruiseTree().parse(test_settings_xml)

        ix = self.place_for_test_settings(root)

        for element_type in ('environments', 'templates', 'pipelines'):
            for elem in reversed(test_settings.findall(element_type)):
                root.insert(ix, elem)

    def drop_sections_to_be_replaced(self, root):
        for tag in ('pipelines', 'templates', 'environments'):
            for element_to_drop in self.findall(tag):
                root.remove(element_to_drop)

    @staticmethod
    def place_for_test_settings(root):
        ix = 0  # Silence lint about using ix after the loop. root != []
        for ix, element in enumerate(list(root)):
            if element.tag == 'agents':
                break
        return ix
