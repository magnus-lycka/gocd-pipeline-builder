# -*- coding: utf-8 -*-
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
    config_xml_rest_path = "/admin/restful/configuration/file/{}/xml"

    def __init__(self, config, verbose, config_overrides):
        self.__config = {}
        if config is not None:
            self.__config.update(yaml.load(config))
        self.__config.update(config_overrides)
        self.verbose = verbose
        self._cruise_config_md5 = None
        self.tree = None

    def check_config(self):
        assert 'url' in self.__config, "'url' missing."
        assert not (('username' in self.__config) ^ ('password' in self.__config)), \
            "Need both or neither of ('username', 'password') in configuration."

    def fetch_config(self):
        """
        Fetch configuration from Go server
        """
        self.tree = CruiseTree.fromstring(self.xml_from_url())

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
        base_url = self.__config['url']
        if not base_url.endswith('/go'):
            print('Adding /go to %s' % base_url)
            base_url += '/go'
        url = base_url + path
        if self.__auth:
            kwargs['auth'] = self.__auth
        response = requests.request(action, url, **kwargs)
        if response.status_code != 200:
            sys.stderr.write("Failed to {} {}\n".format(action, url))
            sys.stderr.write("status-code: {}\n".format(response.status_code))
            sys.stderr.write(u"text: {}\n".format(response.text))
        return response

    def xml_from_url(self):
        action = 'GET'
        path = self.config_xml_rest_path.format(action)
        response = self.request(action, path)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))
        try:
            self._cruise_config_md5 = response.headers['x-cruise-config-md5']
        except KeyError:
            print("Missing 'x-cruise-config-md5' in:", file=sys.stderr)
            print(response.headers, file=sys.stderr)
            raise
        return response.text

    def create_a_pipeline(self, pipeline):
        """
        Add a pipeline to the Go server configuration using the REST API:
        https://api.go.cd/current/#create-a-pipeline

        :param pipeline: Json object as describe in API above.
        """
        path = "/api/admin/pipelines"
        data = json.dumps(pipeline)
        headers = {
            'Accept': 'application/vnd.go.cd.v5+json',
            'Content-Type': 'application/json'
        }
        response = self.request('post', path, data=data, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))

    def get_pipeline_config(self, pipeline_name):
        path = "/api/admin/pipelines/" + pipeline_name
        headers = {
            'Accept': 'application/vnd.go.cd.v5+json'
        }
        response = self.request('get', path, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))
        json_data = json.loads(response.text.replace("\\'", "'"),
                               object_pairs_hook=OrderedDict)
        etag = response.headers['etag']
        return etag, json_data

    def edit_pipeline_config(self, pipeline_name, etag, pipeline):
        path = "/api/admin/pipelines/" + pipeline_name
        data = json.dumps(pipeline)
        headers = {
            'Accept': 'application/vnd.go.cd.v5+json',
            'Content-Type': 'application/json',
            'If-Match': etag
        }
        response = self.request('put', path, data=data, headers=headers)
        if response.status_code != 200:
            print(response.text)
            raise RuntimeError(str(response.status_code))

    def delete_pipeline_config(self, pipeline_name):
        path = "/api/admin/pipelines/" + pipeline_name
        headers = {
            'Accept': 'application/vnd.go.cd.v5+json',
        }
        response = self.request('delete', path, headers=headers)
        if response.status_code != 200:
            print(response.text)
            raise RuntimeError(str(response.status_code))

    def unpause(self, pipeline_name):
        headers = {
            'Accept': 'application/vnd.go.cd.v1+json',
            'X-GoCD-Confirm': 'true'
        }
        path = "/api/pipelines/" + pipeline_name + "/unpause"
        self.request('post', path, headers=headers)

    def get_pipeline_status(self, pipeline_name):
        path = "/api/pipelines/" + pipeline_name + "/status"
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
        path = "/api/config/pipeline_groups"
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
        path = "/api/pipelines/" + pipeline + "/instance/" + instance
        headers = {
            'Accept': 'application/json'
        }
        response = self.request('get', path, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))
        json_data = json.loads(response.text.replace("\\'", "'"),
                               object_pairs_hook=OrderedDict)
        return json_data

    def patch_environment(
            self,
            env_name,
            pipelines_add=None,
            pipelines_remove=None,
            agents_add=None,
            agents_remove=None):
        path = "/api/admin/environments/" + env_name
        pipelines = {}
        if pipelines_add:
            pipelines["add"] = pipelines_add
        if pipelines_remove:
            pipelines["remove"] = pipelines_remove
        agents = {}
        if agents_add:
            agents["add"] = agents_add
        if agents_remove:
            agents["remove"] = agents_remove
        data_structure = {}
        if pipelines:
            data_structure["pipelines"] = pipelines
        if agents:
            data_structure["agents"] = agents
        data = json.dumps(data_structure)
        headers = {
            'Accept': 'application/vnd.go.cd.v2+json',
            'Content-Type': 'application/json'
        }
        response = self.request('patch', path, data=data, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(str(response.status_code))

    def upload_config(self):
        """
        This method pushes a new cruise-config.xml to the go server.
        It's used when there is no REST API for the changes we want to do.
        """
        headers = {
            'Confirm': 'true'
        }
        data = {'xmlFile': self.cruise_xml, 'md5': self._cruise_config_md5}
        action = 'POST'
        response = self.request(action,
                                self.config_xml_rest_path.format(action),
                                headers=headers,
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

    def rename_pipeline_group(self, source_name, target_name):
        target_group = None
        for group in self.get_pipeline_groups():
            if group['name'] == target_name:
                target_group = group
                break
        if target_group and target_group["pipelines"]:
            names = ", ".join(p['name'] for p in target_group['pipelines'])
            raise ValueError('Pipeline group "{}" exists and contains pipelines: {}'.format(target_name, names))
        self.fetch_config()
        if target_group:
            self.tree.drop_pipeline_group(target_name)
        self.tree.rename_pipeline_group(source_name, target_name)
        self.upload_config()

    def move_all_pipelines_in_group(self, source_name, target_name):
        target_group = None
        for group in self.get_pipeline_groups():
            if group['name'] == target_name:
                target_group = group
                break
        if target_group and target_group["pipelines"]:
            names = ", ".join(p['name'] for p in target_group['pipelines'])
            raise ValueError('Pipeline group "{}" exists and contains pipelines: {}'.format(target_name, names))
        self.fetch_config()
        if target_group:
            self.tree.drop_pipeline_group(target_name)
        self.tree.move_all_pipelines_in_group(source_name, target_name)
        self.upload_config()


