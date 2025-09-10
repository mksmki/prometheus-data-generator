#!/bin/bash

docker run \
    --rm \
    -ti \
    -v `pwd`/config.yml:/config.yml \
    -p 127.0.0.1:9000:9000 \
    mksmki/prometheus-data-generator:latest
