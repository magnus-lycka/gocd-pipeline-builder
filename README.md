GO CD Pipeline Builder
=====================

The gocd-pipeline-builder builds a GoCD pipeline automagically when you push a new git repository to your git server.


How to run the self-tests
-------------------------

Install texttest: [http://texttest.org]

In your $TEXTTEST_HOME folder create a softlink like this:

    cd $TEXTTEST_HOME
    ln -s /whereever/your/clones/live/gocd-pipeline-builder/src/texttest gocdpb

In your texttest personal config file (defaults to ~/.texttest/config, create it if it doesn't exist), add the following to your checkout locations:

	[checkout_location]
	gocd-pipeline-builder:/whereever/your/clones/live/gocd-pipeline-builder
	[end]

start texttest:

    texttest -a gocdpb


Plan for now...
---------------

* Create test case to build rudimentary pipeline.
* Use the Springer gomatic API.
* Use YAML for template configuration.
* Use jinja2 or Mako to fill template with values?
  - Mako uses the familiar ${name} syntax!
* Use Emily's hooks code to talk to Git.


Observations on Gomatic
-----------------------

 * No support for environments in configuration.
   - Issue filed.
   - Pull requests issues (mine and another within 18 minutes of each other!)
 * Missing functionality concerning git material:
   - Assumption of only one git material instance for a pipeline.
   - No support for destination directory.
 * Reorders materials section in pipelines. (Probably doesn't matter.)


GoCD Pipeline Templates and parameters
--------------------------------------

See http://www.go.cd/documentation/user/current/configuration/pipeline_templates.html
and http://www.go.cd/documentation/user/current/configuration/admin_use_parameters_in_configuration.html

GoCD has the concepts of pipeline templates and parameters.
If we use this, there is not so much that we need to define
in outside the normal GoCD configuration.


What we need to pass to the tool
--------------------------------

 * Name of pipeline to add/update (probably derived from repo name).
 * Environment to place the pipeline in.
 * All materials for the pipeline:
   - The git repo which was the cause of all this.
   - Any other material the pipeline might depend on.
 * Which pipeline template to use. (only one to start with?)
 * Parameter(s) used by the template.
   - REPODIR, which would be the destination directory for the source git repo and the working dir for most tasks.
 * Information which is needed for downstream pipelines which will use the output of this pipeline.
   - material, <pipeline name="my_downstream"> <materials> <pipeline pipelineName="xxx" stageName="yyy" />
   - fetch artifact, <pipeline name="my_downstream"> <stage name="x"> <jobs> <job name="x"> <tasks> <fetchartifact pipeline="xxx" stage="yyy" job="x" srcdir="d" dest="upstream_xxx"> <runif status="passed" />

Wishlist
--------

 * Support for virtualenv in GoCD!
