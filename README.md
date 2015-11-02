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


Obviously missing
-----------------
 * Other material than git
 * filter/ignore in git material
 * Update existing pipeline
 * Git hooks
 * Fetchartifact tasks
 * Define artifacts
 * Add pipeline in environment
 * Request resource in job
 * Hook in new pipeline in downstream pipeline?
 * Replace existing pipeline?


Plan for now...
---------------
 * Add pipeline in environment
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

