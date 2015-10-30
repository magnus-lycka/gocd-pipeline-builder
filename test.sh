#!/usr/bin/env bash

set -evo pipefail

PYTHONPATH=src/main python -m unittest discover .