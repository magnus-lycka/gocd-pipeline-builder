GO CD Pipeline Builder
=====================

The gocd-pipeline-builder makes a GoCD pipeline automagically when you push a new git repository to your server.


How to run the self-tests
-------------------------

Install texttest: [http://texttest.org]

In your $TEXTTEST_HOME folder create a softlink like this:

    ln -s /whereever/your/clones/live/gocd-pipeline-builder/src/texttest

In your texttest personal config file (defaults to ~/.texttest/config, create it if it doesn't exist), add the following to your checkout locations:

	[checkout_location]
	gocd-pipeline-builder:/whereever/your/clones/live/gocd-pipeline-builder
	[end]

start texttest:

    texttest -a gocdpb


## Plan for now...

* Create test case to build rudimentary pipeline.
* Use the Springer gomatic API.
* Use YAML for template configuration.
