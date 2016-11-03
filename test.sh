#!/usr/bin/env bash

set -evo pipefail

PYTHONPATH=src python -m unittest discover src/test
