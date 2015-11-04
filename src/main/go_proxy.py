import yaml
import sys
import json
from xml.etree import ElementTree
import requests

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

        if not pipeline_groups.has_key(group_name):
            raise KeyError('Pipeline group %s not found among %s'
                       % (group_name, pipeline_groups))
        else:
            pipeline.append_self(pipeline_groups[group_name])


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
