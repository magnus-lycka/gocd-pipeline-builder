GoCD Pipeline Builder
=====================

The gocd-pipeline-builder lets you create a GoCD pipeline
from a git repository.

[![Build Status](https://travis-ci.org/magnus-lycka/gocd-pipeline-builder.svg?branch=master)](https://travis-ci.org/magnus-lycka/gocd-pipeline-builder)
[![Quality Gate](https://sonarqube.com/api/badges/gate?key=gocdpb)](https://sonarqube.com/dashboard/index/gocdpb)
[![Quality Gate](https://sonarqube.com/api/badges/measure?key=gocdpb&metric=ncloc)](https://sonarqube.com/dashboard/index/gocdpb)
[![Quality Gate](https://sonarqube.com/api/badges/measure?key=gocdpb&metric=sqale_debt_ratio)](https://sonarqube.com/dashboard/index/gocdpb)
[![Quality Gate](https://sonarqube.com/api/badges/measure?key=gocdpb&metric=code_smells)](https://sonarqube.com/dashboard/index/gocdpb)


Supported GoCD versions
-----------------------

The GoCD REST API is continuously developing, and the
*GoCD Pipeline Builder* uses a lot of the newer APIs,
so you have to use a fairly current GoCD version to
use this software. 

If this software doesn't work because your GoCD server
is older than the one we test it with, please upgrade
your GoCD server. If this software doesn't work with
the latest released GoCD from Thoughtworks, please file
an issue.

Unfortunately, the GoCD server isn't very explicit 
in its error messages. If an API changes to use e.g.
`application/vnd.go.cd.v4+json` and we call it with 
`application/vnd.go.cd.v3+json`, we'll simply get an 
HTTP status 404 as response.


Overview
--------

The actions of the gocd-pipeline-builder are driven by
a json file containing a list of operations to perform.
See below and the pattern.json files under src/texttest.

This json file can use Jinja2 templates to pass in
custom values etc, so that the .json-files can be generic
templates.

The values to pass to the Jinja2 template can either be
passed to the tool on the command file, and/or come from
a .yaml file.

As of today, there is no builtin githook support, but
it's no rocket science to call the tool on post-receive.


gocdpb Command Line Interface
------------------------------

The gocdpb script configures new pipelines in a GoCD server.

    usage: gocdpb [-h] [-j JSON_SETTINGS | -y YAML_SETTINGS] [-p PLUGIN]
                  [-D DEFINE] [--dump-test-config DUMP_TEST_CONFIG] [-d DUMP]
                  [-v] [-c CONFIG] [-C CONFIG_PARAM] [-P PASSWORD_PROMPT]
                  [--set-test-config SET_TEST_CONFIG]

    Add pipeline to Go CD server.

    optional arguments:
      -h, --help            show this help message and exit
      -j JSON_SETTINGS, --json-settings JSON_SETTINGS
                            Read json file / url with settings for GoCD pipeline.
      -y YAML_SETTINGS, --yaml-settings YAML_SETTINGS
                            Read yaml files with parameters for GoCD pipeline.
      -p PLUGIN, --plugin PLUGIN
                            Plugin module for custom functions.
      -D DEFINE, --define DEFINE
                            Define setting parameter on command line.
      --dump-test-config DUMP_TEST_CONFIG
                            Copy of some sections of new GoCD configuration XML
                            file.
      -d DUMP, --dump DUMP  Copy of new GoCD configuration XML file.
      -v, --verbose         Write status of created pipeline.
      -c CONFIG, --config CONFIG
                            Yaml file with configuration.
      -C CONFIG_PARAM, --config-param CONFIG_PARAM
                            Define config parameter on command line.
      -P PASSWORD_PROMPT, --password-prompt PASSWORD_PROMPT
                            Prompt for config parameter without echo.
      --set-test-config SET_TEST_CONFIG
                            Set some sections in config first. (For test setup.)


-c and -C/-P are two ways of providing the same information:
From file or on command line. -P allows us to secretly provide passwords.

-j together with -D can provide the same information on the commandline as
-y would provide in a file. See below.

Assuming that you have an appropriate settings file available at http:/server/settings.json
with pattern parameters `{{ repo_url }}`, `{{ group }}` and `{{ repo_name }}`, and you
stand in a git checkout and want a new pipeline named as the checkout directory, in
pipeline group `X` at `http://mygoserver:8153`, where you log in as `charlie`, you
can type this:

    gocdpb -C url=http://mygoserver:8153 -C username=charlie -P password -D group=X -j http:/server/settings.json

You will be prompted for password.

If you want the pipeline to be called `Y` instead of the directory name,
simply add `-D repo_name=Y` to the command line.

The `-p | --plugin` flag is new in version 7. See section on plugins below.


GoCD Pipeline Templates and parameters
--------------------------------------

See http://www.go.cd/documentation/user/current/configuration/pipeline_templates.html
and http://www.go.cd/documentation/user/current/configuration/admin_use_parameters_in_configuration.html

GoCD has the concepts of pipeline templates and parameters.
If we use this, there is not so much that we need to define
outside the normal GoCD configuration.


GoCD Pipeline Builder Setting Files
-----------------------------------

To create a GoCD pipeline with the pipeline builder,
you use a json file which follows this pattern:

    [
        {
            "environment": "name of environment",
            "unpause": "true or false"
            "<action>": <data>
        }
    ]


Use `gocdpb -j` to pass the json settings file to the builder.

See *.json files under src/texttest for more examples of
intended usage.

Both `environment` and `unpause` are optional.

`<action>` can be one of:

  - "create-a-pipeline": This means that we plan
    to call the REST API for creation of a new pipeline.
    See https://api.go.cd/current/#create-a-pipeline .
    `<data>` should be a json pipeline configuration as
    described by this API.
    For this action, the "environment" field will
    indicate that the new pipeline should belong
    to a Go server environment with the given name.
    Newly created pipelines are typically paused, but
    setting "unpause" to "true" will make it an
    immediate candidate for getting built.
  - "add-downstream-dependencies": This action is
    used to add the newly created pipeline as a
    dependency to a downstream pipeline.
    `<data>` is an object with the following members:
    - "name" of the downstream pipeline.
    - "material" (optional) specifies the dependency
      material, so that defaults can be overridden.
      This object should follow the structure of
      dependency material in the REST API.
      If missing, a dependency material object with
      the name of the newly created pipeline with
      default values will be used.
    - "stage" is used for fetchartifact tasks to
      tell where to add it. If missing, the first stage
      will be used.
    - "job" is used for fetchartifact tasks to
      tell where to add it. If missing, the first job
      will be used.
    - "task" should be a fetch task as described in the
      REST API which fetches some build artifact from
      the newly created pipeline.
  - Custom value: See section on Plugins below.

GoCD Pipeline Builder Patterns
------------------------------

The pipeline builder has a concept called `patterns`.
We could have called it `templates`, but since GoCD has
something else which is called `pipeline templates`,
we call these things `patterns`.

A `pattern` is a Jinja2 template, see http://jinja.pocoo.org/

With a pipeline builder `pattern`, we can avoid a lot
of repetition. For instance, if we have several pipelines
like the one above, that only differ on name, we can have
yaml parameter file like this:

    path: ./simple_pipeline_pattern.json
    parameters:
        name: gocd
        url: https://github.com/magnus-lycka/gocd.git

Use `gocdpb -y` to pass the yaml parameter file to the builder.

The pattern file `./simple_pipeline_pattern.json` is a
json file as described in the previous section, with
jinja2 templating. See the test suite for examples.

See also Jinja2 docs at http://jinja.pocoo.org/

See *.yaml files under src/texttest for more examples of
intended usage.


Builtin parameters
------------------

Whether you run  `goplbld -y` or  `goplbld -j`, you can
use builtin parameters to substitute values via the Jinja2
template mechanism. The following builtin parameters exist:

| Parameter | Default value                       |
|-----------|-------------------------------------|
| repo_url  | URL for git repo from ./.git/config |
| repo_name | Name of current working directory   |


Branching/tagging releases
--------------------------

If you need to maintain a released version of your software in parallel with
development of new features, you might want to tag and/or branch all source
code repos involved in creating a release. The `gocdrepos` and `gocdtagrepos`
tools help prepare that, while the `clone-pipelines` action for `gocdpb` will
set up the actual pipelines you need for your release, with release pipelines
in a separate pipeline-group using branched source code repos as material.

(This might not be the ideal way of working with Continuous Deployment, but
its a reality for many teams that strive towards Continuous Deployment.)


Plugins
-------

Features not supported by `gocdpb` can be added through plugins.

You need to provide a Python module with a module level dictionary
called `action_plugins` with the action names as keys, and each
corresponding handler as values. A handler could be any callable
Python object, i.e. a class with an `__init__`, an instance with
a `__call__`, or a function or method.

The callable should only accept keyword arguments, and accept any
keyword argument to be able to deal with future expansions without
breaking. The caller of the callable doesn't expect any return
value. Throw an explanatory exception if the expectations of
calling can't be met.

Something like this:

    # my_plugin_module.py
    def beer_pipeline_handler(go=None, operation=None, **kwargs):
       ...
       if brand not in inventory:
           raise ValueError('Unknown brand')
       ...

    action_plugins = {'beer-pipeline': beer_pipeline_handler}


By calling `gocdpb` with `-p my_plugin_module` and using `beer-pipeline`
as action in the GoCD Pipeline Builder Setting File, as described above,
we'll make `gocdpb` run the `beer_pipeline_handler`.

The parameter `go` is an instance of goserver_adapter.Goserver. The general
idea is that Goserver has methods corresponding to the GoCD REST API calls
which take the needed parameters (url and login is already taken care of)
and returns either `json_data` as the result of json.load (with OrderedDict)
or a tuple of  `etag, json_data`.

The parameter `operation` in the value in the Json settings file corresponding
to the key in the `action_plugins` dictionary. So, for the example above, if
we have the following in our settings file...

    ...
    'beer-pipeline': {'brand': 'Carnegie Porter', 'flow': '600l/h', 'alc': '6.2%'},
    ...

...we'll call `beer_pipeline_handler` with `operation` set to
`{'brand': 'Carnegie Porter', 'amount': '600', 'alc': '6.2%'}`.


gocdrepos Command Line Interface
--------------------------------

The gocdrepos tool lists all the source code repositories used directly or
indirectly to build a certain instance of a pipeline. The `-f` flag is used to
decide whether to use json format or a flat semicolon separated format for the
output. All other flags work just as for `gocdpb`.
The pipeline_instance parameter has to be provided on the form
<pipeline name>/<pipeline counter>, so if you want to have a json listing
of the source code repositories used to create build 12 or the `hello`
pipeline, you might type this and provide the password when prompted:
`gocdrepos -C url=http://go -C username=gouser -P password -f json hello/12`


    usage: gocdrepos [-h] [-f {semicolon,json}] [-v] [-c CONFIG] [-C CONFIG_PARAM]
                     [-P PASSWORD_PROMPT] [--set-test-config SET_TEST_CONFIG]
                     pipeline_instance

    Recursively fetch all source code revisions used in a pipeline build.

    positional arguments:
      pipeline_instance     pipeline/instance to start at.

    optional arguments:
      -h, --help            show this help message and exit
      -f {semicolon,json}, --format {semicolon,json}
                            Format for output.
      -v, --verbose         Write status of created pipeline.
      -c CONFIG, --config CONFIG
                            Yaml file with configuration.
      -C CONFIG_PARAM, --config-param CONFIG_PARAM
                            Define config parameter on command line.
      -P PASSWORD_PROMPT, --password-prompt PASSWORD_PROMPT
                            Prompt for config parameter without echo.
      --set-test-config SET_TEST_CONFIG
                            Set some sections in config first. (For test setup.)


gocdtagrepos Command Line Interface
-----------------------------------

The gocdtagrepos tool uses a json-file of the format created by gocdrepos. For
each repo in the json-file, it will make a clone under DIRECTORY, tag it with
TAG_NAME, and also branch it with the TAG_NAME if the pipeline used to create
it was listed in BRANCH_LIST. The -p flag is used to automatically push the
repository, and the -c flag to remove the clone when it's done.

Currently, this tool only supports git.

    usage: gocdtagrepos [-h] [-d DIRECTORY] -t TAG_NAME [-b BRANCH_LIST] [-p] [-c]
                        [jsonfile]

    Tag and/or branch a set of Git repositories as provided by json data.

    positional arguments:
      jsonfile              Json file as produced by gocdrepos. Read from stdin if
                            no filename given.

    optional arguments:
      -h, --help            show this help message and exit
      -d DIRECTORY, --directory DIRECTORY
                            Parent directory of repository clones clones. Default
                            to /tmp.
      -t TAG_NAME, --tag-name TAG_NAME
                            Name of tag / branch to create.
      -b BRANCH_LIST, --branch-list BRANCH_LIST
                            Comma-separated list of pipeline names. Create
                            branches for these.
      -p, --push            Push changes to remote repo.
      -c, --clean           Remove cloned repo.


TODO
----

- Make git hooks to run gocdpb automatically.


How to run the self-tests
-------------------------

This software is mainly developed through an ATDD approach, with the bulk of tests in
texttest. Unit tests exist are mainly complements to the the functional tests.

Run ./test.sh in the root folder for unit tests, and follow the instructions below
for functional tests:

Install a go-server for functional tests.
See https://www.go.cd/documentation/user/current/installation/installing_go_server.html

The test will wipe most of the configuration before each test, so don't use a go-server
that's used for anything else for these tests.

Create a user in the go-server with credentials corresponding to `src/texttest/goplbld.yaml`.
See https://www.go.cd/documentation/user/current/configuration/dev_authentication.html

hint:

    sudo htpasswd -bcs /etc/go/htpasswd gouser verysecret

If you manage to lock yourself out of the go-server when you do this, you can fix the
/etc/go/cruise-config.xml in an editor and restart the service. It might be good to save
a backup of cruise-config.xml before you start changing stuff.

Install TextTest and CaptureMock: [http://texttest.org].
Also install all the python libraries listed in 'requirements.txt'.

hint:

    sudo pip install TextTest
    sudo pip install CaptureMock
    sudo pip install -r requirements.txt

In your $TEXTTEST_HOME folder create a softlink pointing out where the test code is.
Given an environment variable $CLONE_LOCATION which points to the directory where you have cloned this repo:

    cd $TEXTTEST_HOME
    ln -s $CLONE_LOCATION/gocd-pipeline-builder/src/texttest gocdpb

In your texttest personal config file (defaults to ~/.texttest/config, create
it if it doesn't exist), add the following to your checkout locations:

(You should replace $CLONE_LOCATION with an actual path or environment variable that is set in all shells)

    [checkout_location]
    gocd-pipeline-builder:$CLONE_LOCATION/gocd-pipeline-builder
    [end]

start texttest:

    texttest -a gocdpb

Since the tests change the state of the Go server, it's important to run them
sequentially unless capturemock is in replay mode.

TODO: Document how to set up docker for the repo_checks tests.


Upgrading gocdpb in PyPI
------------------------

Make sure that all tests pass and that the version has been updated in setup.py.
Commit and push changes to the repository before doing the following.

    $ python setup.py sdist
    $ twine upload dist/gocdpb-<new version>.tar.gz
    $ sudo pip install --upgrade gocdpb

Verify that the new version is downloaded, and works as intended.

