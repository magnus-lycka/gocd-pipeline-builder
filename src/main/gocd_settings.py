import re
import sys
import json
import os.path
from collections import OrderedDict, defaultdict
from xml.etree import ElementTree

import yaml
from jinja2 import Template


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
        self.pipeline_names = []
        self.pipeline_stage_names = []
        self.pipeline_group_map = {}

    def load_file(self, settings_file, extra_settings):
        self.load_template(settings_file, extra_settings)

    def load_template(self, template_data, parameters):
        template = Template(template_data)
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

    def server_operations(self, go):
        for operation in self.list:
            if "create-a-pipeline" in operation:
                go.create_a_pipeline(operation["create-a-pipeline"])
                self.pipeline_names.append(operation["create-a-pipeline"]["pipeline"]["name"])
                self.pipeline_stage_names.append([
                    stage["name"] for stage
                    in operation["create-a-pipeline"]["pipeline"].get("stages") or []
                ])
            if "clone-pipelines" in operation:
                self.clone_pipelines(go, operation["clone-pipelines"])
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
                    print json.dumps(status, indent=4, sort_keys=True)

    def clone_pipelines(self, go, operation):
        """
        For now, this is fairly limited.
        Given a "FIND-group" and a "CREATE-group" in the operation,
        we use re.sub with FIND-name and REPLACE-name in the pipeline
        to make a new pipeline in the group "REPLACE-name" with a
        new name for each pipeline in group "FIND-name".
        The new pipelines will use the git branch indicated by
        "REPLACE-branch" for their Git material.
        """
        find_group = operation["FIND-group"]
        all_groups = go.get_pipeline_groups()

        for pipeline_group in all_groups:
            for pipeline in pipeline_group["pipelines"]:
                self.pipeline_group_map[pipeline['name']] = pipeline_group['name']
        for pipeline, group in self.pipeline_group_map.items():
            if group == find_group:
                name = self.clone_pipeline(go, operation, pipeline)
                if name:
                    self.pipeline_names.append(name)
        for pipeline_name in self.pipeline_names:
            self.fix_pipeline(go, operation, pipeline_name)

    def clone_pipeline(self, go, operation, old_name):
        create_group = operation["CREATE-group"]
        find_name = operation['pipeline']["FIND-name"]
        replace_name = operation['pipeline']["REPLACE-name"]
        etag, pipeline = go.get_pipeline_config(old_name)
        new_name = re.sub(find_name, replace_name, old_name)
        if new_name is None:
            return
        pipeline['name'] = new_name
        new_pipeline = dict(group=create_group, pipeline=pipeline)
        old_material = pipeline["materials"][:]
        pipeline["materials"] = []
        for actual_material in old_material:
            for op_material in operation['pipeline']['materials']:
                if actual_material["type"] == op_material["type"]:
                    ok = self._update_material(actual_material, op_material)
                    if ok:
                        pipeline["materials"].append(actual_material)
        go.create_a_pipeline(new_pipeline)
        return new_name

    def fix_pipeline(self, go, operation, name):
        etag, pipeline = go.get_pipeline_config(name)
        for actual_material in pipeline["materials"]:
            for op_material in operation['pipeline']['materials']:
                if actual_material["type"] == op_material["type"] == 'dependency':
                    self._fix_dependencies(actual_material, op_material)
        go.edit_pipeline_config(name, etag, pipeline)

    def _update_material(self, actual_material, op_material):
        """
        This method is called on the material in pipelines we clone.
        It should copy source code repositories and update their branch.
        It should copy the matching dependency material, but we should
        postpone updates of the names, until all pipelines have been
        cloned to avoid references to not yet created pipelines.
        """
        if actual_material["type"] == 'git':
            actual_material["attributes"]["branch"] = op_material["attributes"]["REPLACE-branch"]
            return True
        elif actual_material["type"] == 'dependency':
            find_pipeline = op_material['attributes']["FIND-pipeline"]
            pipeline_name = actual_material["attributes"]["pipeline"]
            if not re.search(find_pipeline, pipeline_name):
                return False
            find_group = op_material['attributes']["FIND-group"]
            if self.pipeline_group_map[pipeline_name] == find_group:
                return True
            return False

    @staticmethod
    def _fix_dependencies(actual_material, op_material):
        find_pipeline = op_material['attributes']["FIND-pipeline"]
        replace_pipeline = op_material['attributes']["REPLACE-pipeline"]
        new_name = re.sub(find_pipeline, replace_pipeline, actual_material["attributes"]["pipeline"])
        if new_name:
            actual_material["attributes"]["pipeline"] = new_name

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
        """
        conf_environments = configuration.find('environments')
        if conf_environments is None:
            print "No environments section in configuration."
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
            print json.dumps(repos, indent=4, sort_keys=True)
        elif self.format == 'semicolon':
            for repo, pipelines in self.recursive_repos.items():
                print "%s; %s" % (repo, ", ".join(["%s/%s" % (p, i) for p, i in pipelines]))
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
