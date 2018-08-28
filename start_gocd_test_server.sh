#!/bin/bash -ex

docker run -i -t --rm \
    --name gocd-test-server \
    -p 8153:8153 \
    -v ${PWD}/gocd-test-server/godata/config:/godata/config \
    gocd/gocd-server:v18.6.0
