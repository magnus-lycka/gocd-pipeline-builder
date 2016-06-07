from __future__ import print_function
import sys
import json
import yaml
import requests
from collections import OrderedDict

from goserver_config import CruiseTree


class Goserver(object):
    """
    Manages HTTP communication with the Go server.
    """
    config_xml_rest_path = "/go/admin/restful/configuration/file/{}/xml"

    def __init__(self, config, verbose, config_overrides):
        self.__config = {}
        if config is not None:
            self.__config.update(yaml.load(config))
        self.__config.update(config_overrides)
        self.verbose = verbose
        self._cruise_config_md5 = None
        self.tree = None
        self._initial_xml = None
        self.need_to_download_config = True

    def check_config(self):
        for param in (
            'url',
        ):
            assert param in self.__config, param

    def init(self):
        """
        Fetch configuration from Go server
        """
        if self.need_to_download_config:
            try:
                self.tree = CruiseTree.fromstring(self.xml_from_url())
                self._initial_xml = self.cruise_xml
            except RuntimeError as error:
                print('Could not get XML configuration. That might not be a problem...')
                print(error)
            self.need_to_download_config = False

    @property
    def need_to_upload_config(self):
        return self.cruise_xml != self._initial_xml

    @property
    def __auth(self):
        if 'username' in self.__config:
            return self.__config['username'], self.__config['password']

    @property
    def cruise_xml(self):
        return self.tree.tostring()

    @property
    def cruise_xml_subset(self):
        return self.tree.config_subset_tostring()

    def request(self, action, path, **kwargs):
        action = action.upper()
        if self._changing_call(action):
            # If we change via REST API, we need to fetch the config
            # again if we need to understand the state.
            # If we uploaded the config XML, we need to fetch it
            # again to get a new md5 checksum in case we want to
            # change some more...
            self.need_to_download_config = True
        url = self.__config['url'] + path
        if self.__auth:
            kwargs['auth'] = self.__auth
        response = requests.request(action, url, **kwargs)
        if response.status_code != 200:
            sys.stderr.write("Failed to {} {}\n".format(action, path))
            sys.stderr.write("status-code: {}\n".format(response.status_code))
            sys.stderr.write("text: {}\n".format(response.text))
        return response

    @staticmethod
    def _changing_call(action):
        return action not in ('HEAD', 'GET')

    def xml_from_url(self):
        action = 'GET'
        path = self.config_xml_rest_path.format(action)
        response = self.request(action, path)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))
        self._cruise_config_md5 = response.headers['x-cruise-config-md5']
        return response.text

    def create_a_pipeline(self, pipeline):
        """
        Add a pipeline to the Go server configuration using the REST API:
        https://api.go.cd/current/#create-a-pipeline

        :param pipeline: Json object as describe in API above.
        """
        path = "/go/api/admin/pipelines"
        data = json.dumps(pipeline)
        headers = {
            'Accept': 'application/vnd.go.cd.v1+json',
            'Content-Type': 'application/json'
        }
        response = self.request('post', path, data=data, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))

    def get_pipeline_config(self, pipeline_name):
        path = "/go/api/admin/pipelines/" + pipeline_name
        headers = {
            'Accept': 'application/vnd.go.cd.v1+json'
        }
        response = self.request('get', path, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))
        json_data = json.loads(response.text.replace("\\'", "'"),
                               object_pairs_hook=OrderedDict)
        etag = response.headers['etag']
        return etag, json_data

    def edit_pipeline_config(self, pipeline_name, etag, pipeline):
        path = "/go/api/admin/pipelines/" + pipeline_name
        data = json.dumps(pipeline)
        headers = {
            'Accept': 'application/vnd.go.cd.v1+json',
            'Content-Type': 'application/json',
            'If-Match': etag
        }
        response = self.request('put', path, data=data, headers=headers)
        if response.status_code != 200:
            print(response.text)
            raise RuntimeError(str(response.status_code))

    def unpause(self, pipeline_name):
        path = "/go/api/pipelines/" + pipeline_name + "/unpause"
        self.request('post', path)

    def get_pipeline_status(self, pipeline_name):
        path = "/go/api/pipelines/" + pipeline_name + "/status"
        headers = {
            'Accept': 'application/json'
        }
        response = self.request('get', path, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))
        json_data = json.loads(response.text.replace("\\'", "'"),
                               object_pairs_hook=OrderedDict)
        return json_data

    def get_pipeline_groups(self):
        path = "/go/api/config/pipeline_groups"
        headers = {
            'Accept': 'application/json'
        }
        response = self.request('get', path, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))
        json_data = json.loads(response.text.replace("\\'", "'"),
                               object_pairs_hook=OrderedDict)
        return json_data

    def get_pipeline_instance(self, pipeline, instance):
        path = "/go/api/pipelines/" + pipeline + "/instance/" + instance
        headers = {
            'Accept': 'application/json'
        }
        response = self.request('get', path, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))
        json_data = json.loads(response.text.replace("\\'", "'"),
                               object_pairs_hook=OrderedDict)
        return json_data

    def upload_config(self):
        """
        This method pushes a new cruise-config.xml to the go server.
        It's used when there is no REST API for the changes we want to do.

        Make sure to refresh the cruise-config by using the .init() method
        if the Go server config was just changed through the REST API.
        """
        if self.cruise_xml == self._initial_xml:
            print("No changes done. Not uploading config.")
        else:
            data = {'xmlFile': self.cruise_xml, 'md5': self._cruise_config_md5}
            action = 'POST'
            response = self.request(action,
                                    self.config_xml_rest_path.format(action),
                                    data=data)
            if response.status_code != 200:
                sys.stderr.write("status-code: %s\n" % response.status_code)
                # GoCD produces broken JSON???, see
                # https://github.com/gocd/gocd/issues/1472
                json_data = json.loads(response.text.replace("\\'", "'"),
                                       object_pairs_hook=OrderedDict)
                sys.stderr.write("result: %s\n" % json_data["result"])
                sys.stderr.write(
                    "originalContent:\n%s\n" % json_data["originalContent"])
                raise RuntimeError(response.status_code)

