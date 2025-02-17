#!/bin/bash

echo "Testing Function ..."
curl -d@test-payload.json \
    -H "Content-Type: application/json" \
    -H 'ce-specversion: 1.0' \
    -H 'ce-id: 2da43885-5e52-4c7f-80f8-7ccd337bab3f' \
    -H 'ce-source: https://198.48.0.1:443' \
    -H 'ce-type: dev.knative.apiserver.resource.update' \
    -H 'ce-time: 2023-09-07T14:48:09.308148663Z' \
    -X POST localhost:8080

echo "See docker container console for output"
