GO CD Pipeline Builder
=====================

The gocd-pipeline-builder builds a GoCD pipeline automagically when you push
a new git repository to your git server.

This is still in alpha state. Don't expect it to be useful.
Don't let it near your production Go-server if you try it out!


What works?
-----------
 * Fetch XML config from go-server.
 * Updating XML config with a simple pipeline with just one git repo
 * Creating a new pipeline in an existing pipeline group, limited to
   - git material (url & destination directory)
   - stages with name
   - jobs with name
   - exec tasks with command, workingdir and arg-list.
   - use go-templates
   - environment and parameters
 * Producing XML with the new pipeline
 * Upload configuration change to Go server
 * Add pipeline in environment


Obviously missing
-----------------
 * Other material than git
 * Define git branch
 * filter/ignore in git material
 * Update existing pipeline
 * Git hooks
 * Fetchartifact tasks
 * Define artifacts
 * Request resource in job
 * Hook in new pipeline in downstream pipeline?


Plan for now...
---------------
 * Git branch
 * Filters in git material
 * Pipeline material.
 * Handle go-server authentication.
 * Hook in new pipeline in downstream pipeline?


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
you use a YAML file which closely resembles the XML
format you see in the GoCD XML config. Besides the
`pipeline` section, you also need to supply some other
information, such as which pipeline group and which
environment to place the pipeline in.

Example below:

    pipelines:
      group: defaultGroup

    pipeline:
      name: gocd
      materials:
        - git:
            url: https://github.com/magnus-lycka/gocd.git
            dest: gocd
      template: my_template
      params:
        - PARAM_NAME: 17
      environmentvariables:
        - ENV_NAME: 42

    environment: windows

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

    pattern:
      path: ./simple_pipeline_pattern.yaml
      parameters:
        name: gocd
        url: https://github.com/magnus-lycka/gocd.git

The pattern file `./simple_pipeline_pattern.yaml` can
look like this:

    pipelines:
      group: defaultGroup

    pipeline:
      name: {{ name }}
      materials:
        - git:
            url: {{ url }}
            dest: {{ name }}
      template: my_template
      params:
        - PARAM_NAME: 17
      environmentvariables:
        - ENV_NAME: 42

    environment: windows

If you want, the patterns can be a lot more complex, with
loops and conditionals etc, as described in the jinja2
docs at http://jinja.pocoo.org/

How to run the self-tests
-------------------------

Install texttest: [http://texttest.org]

In your $TEXTTEST_HOME folder create a softlink like this:

    cd $TEXTTEST_HOME
    ln -s /whereever/your/clones/live/gocd-pipeline-builder/src/texttest gocdpb

In your texttest personal config file (defaults to ~/.texttest/config, create
it if it doesn't exist), add the following to your checkout locations:

    [checkout_location]
    gocd-pipeline-builder:/whereever/your/clones/live/gocd-pipeline-builder
    [end]

start texttest:

    texttest -a gocdpb

