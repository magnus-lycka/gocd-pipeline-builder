import copy
import json
from collections import OrderedDict
import yaml
from jinja2 import Template
from xml.etree import ElementTree


def get_settings(settings_file):
    """
    Factory function returning a settings object from a Yaml och Json file.

    A Json file passed to the factory should have the following structure:
    {
        "environment": "green",
        "pipelines": [ <pipeline> ... ]
    }

    Each <pipeline> should conform to the spec here:
    https://api.go.cd/current/#create-a-pipeline

    If a Yaml file is passed to the factory, it will return a settings
    object created from a Jinja template and parameters in the Yaml file.
    The end result should be as for Json files as described above.

    :param settings_file: a Yaml or Json file.
    :return: A JsonSettings instance (or instance of subclass)
    """
    if settings_file.name.endswith('.json'):
        return JsonSettings(settings_file)
    else:
        return YamlSettings(settings_file)


class JsonSettings(object):
    """
    See get_settings() factory function.
    """
    def __init__(self, settings_file):
        self.pipelines = None
        self.environment = None
        self.load_structure(settings_file)

    def load_structure(self, settings_file=None, settings_string=None):
        if settings_file:
            settings_string = settings_file.read()
        try:
            structure = json.loads(settings_string, object_pairs_hook=OrderedDict)
        except ValueError:
            print settings_string
            raise
        self.pipelines = structure.get('pipelines')
        self.environment = structure.get('environment')

    def update_environment(self, configuration):
        """
        If the setting names an environment, the pipelines in the
        setting, should be assigned to that environment in the cruise-config.
        """
        conf_environments = configuration.find('environments')
        if conf_environments is None:
            print "No environments section in configuration."
            return
        for conf_environment in conf_environments.findall('environment'):
            if conf_environment.get('name') == self.environment:
                for pipeline_dict in self.pipelines:
                    pipeline = pipeline_dict.get('pipeline')
                    name = pipeline.get('name')
                    self._set_pipeline_in_environment(name, conf_environment)
                break
        else:  # No break
            print "Environment %s not found in config" % self.environment

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
    See get_settings() factory function.
    """
    def load_structure(self, settings_file):
        """
        Find the Json template and parameter in the Yaml file,
        render the template, and pass it to the super class.
        """
        structure = yaml.load(settings_file)
        template = Template(open(structure['path']).read())
        settings = template.render(structure['parameters'])
        super(YamlSettings, self).load_structure(settings_string=settings)


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
