GO CD Pipeline Builder
=====================

The gocd-pipeline-builder builds a GoCD pipeline automagically
when you push a new git repository to your git server.

This is still in alpha state. Don't expect it to be useful.
Don't let it near your production Go-server if you try it out!

Plans for Go 15.3
-----------------

From Go version 15.3, there is a REST API for pipeline config,
see https://api.go.cd/current/#pipeline-config

This means that we can remove a lot of current functionality
from the pipeline-builder, and avoid adding a lot of planned
features. We simply use the json format stated in the REST API
and push interpretation and error handling to the Go server.

The new approach is to use this API and not support older versions of Go.

The pipeline-builder will mainly consist of the following parts:
- Wrapping the REST calls and interpretation of results.
- Integrating this with git hooks.
- Provide a templating mechanism (pattern files) using jinja2,
  so that we can avoid duplicating common behaviour in the pipelines.
- Manage dependencies, e.g. state downstream pipelines that
  should add an upstream pipeline as a dependency.

The pattern file should then be a json file of the format described
in https://api.go.cd/current/#create-a-pipeline

When the program is run, we should first get the pipeline groups,
see https://api.go.cd/current/#pipeline-groups
and see if a pipeline with the same name exists.
If the pipeline name is not in the configuration, we should
create a new pipeline, see https://api.go.cd/current/#create-a-pipeline
If the pipeline name is in the configuration, and it's in the
pipeline group stated in the given input, we should edit the
pipeline config, see https://api.go.cd/current/#edit-pipeline-config
If the pipeline exists in a different pipeline group, we should exit
with an error message.


What works?
-----------
 * Fetch XML config from go-server.
 * Updating XML config with a pipeline using the Go Server 15.3 REST API.
 * Creating a new pipeline in an existing pipeline group.
 * Add pipeline in environment


Obviously missing
-----------------
 * Update existing pipeline
 * Git hooks
 * Add new pipeline as material and fetch artifact in downstream pipeline
 * go-server authentication.


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
            "environment": "build",
            "create-a-pipeline": [ <pipeline> ... ]
        }
    ]

Each <pipeline> should conform to the spec here:
https://api.go.cd/current/#create-a-pipeline

Use `goplbld -s` to pass the settings file to the builder.


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
settings file like this:

    path: ./simple_pipeline_pattern.json
    parameters:
        name: gocd
        url: https://github.com/magnus-lycka/gocd.git

The pattern file `./simple_pipeline_pattern.json` is a
json file as described in the previous section, with
jinja2 templating. See the test suite for examples.

See also jinja2 docs at http://jinja.pocoo.org/


How to run the self-tests
-------------------------

Install texttest: [http://texttest.org]. Also install all the python libraries listed in 'requirements.txt'.

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


