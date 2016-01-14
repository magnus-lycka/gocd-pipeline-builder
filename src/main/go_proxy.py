import sys
import json
import yaml
import requests

from model import CruiseTree


class GoProxy(object):
    """
    Manages HTTP communication with the Go server.
    """
    config_xml_rest_path = "/go/admin/restful/configuration/file/{}/xml"

    def __init__(self, config):
        self._config = yaml.load(config)
        self._cruise_config_md5 = None
        self.tree = None
        self._initial_xml = None
        self.init()

    def init(self):
        """
        Fetch configuration from Go server
        """
        self.tree = CruiseTree.fromstring(self.xml_from_url())
        self._initial_xml = self.cruise_xml

    def changed(self):
        return self.cruise_xml != self._initial_xml

    @property
    def cruise_xml(self):
        return self.tree.tostring()

    @property
    def cruise_xml_subset(self):
        return self.tree.config_subset_tostring()

    def xml_from_url(self):
        url = self._config['url'] + self.config_xml_rest_path.format('GET')
        response = requests.get(url)
        self._cruise_config_md5 = response.headers['x-cruise-config-md5']
        return response.text

    def add_settings(self, json_settings):
        for pipeline in json_settings.pipelines:
            self.add_pipeline(pipeline)
        self.init()  # Update config with new changes
        json_settings.update_environment(self.tree)
        if self.changed():
            self.upload_config()

    def add_pipeline(self, pipeline):
        """
        Add a pipeline to the Go server configuration using the REST API:
        https://api.go.cd/current/#create-a-pipeline

        :param pipeline: Json object as describe in API above.
        """
        url = self._config['url'] + "/go/api/admin/pipelines"
        data = json.dumps(pipeline)
        headers = {
            'Accept': 'application/vnd.go.cd.v1+json',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, data=data, headers=headers)
        if response.status_code != 200:
            sys.stderr.write("status-code: %s\n" % response.status_code)
            sys.stderr.write("text: %s\n" % response.text)
            raise RuntimeError(str(response.status_code))

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
        root = self.tree.getroot()

        for tag in ('pipelines', 'templates', 'environments'):
            for element_to_drop in self.tree.findall(tag):
                root.remove(element_to_drop)

        test_settings = CruiseTree().parse(test_settings_xml)

        ix = 0  # Silence lint about using ix after the loop. root != []
        for ix, element in enumerate(list(root)):
            if element.tag == 'agents':
                break

        for element_type in ('environments', 'templates', 'pipelines'):
            for elem in reversed(test_settings.findall(element_type)):
                root.insert(ix, elem)

    def upload_config(self):
        """
        This method pushes a new cruise-config.xml to the go server.
        It's used when there is no REST API for the changes we want to do.

        Make sure to refresh the cruise-config by using the .init() method
        if the Go server config was just changed through the REST API.
        """
        if self.cruise_xml == self._initial_xml:
            print "No changes done. Not uploading config."
        else:
            url = self._config['url'] + self.config_xml_rest_path.format('POST')
            data = {'xmlFile': self.cruise_xml, 'md5': self._cruise_config_md5}
            response = requests.post(url, data=data)
            if response.status_code != 200:
                sys.stderr.write("status-code: %s\n" % response.status_code)
                # GoCD produces broken JSON???, see
                # https://github.com/gocd/gocd/issues/1472
                json_data = json.loads(response.text.replace("\\'", "'"))
                sys.stderr.write("result: %s\n" % json_data["result"])
                sys.stderr.write(
                    "originalContent:\n%s\n" % json_data["originalContent"])
                raise RuntimeError(response.status_code)
