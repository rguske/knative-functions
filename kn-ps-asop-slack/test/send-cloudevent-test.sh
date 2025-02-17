#!/bin/bash

echo "Testing Function ..."
curl -d@test-payload.json \
    -H "Content-Type: application/json" \
    -H 'ce-specversion: 1.0' \
    -H 'ce-id: 0866ff41-0d90-4003-a0a6-06b4c0d16cfa' \
    -H 'ce-source: /kn-asop-webhook-fn' \
    -H 'ce-type: asop.openc2.event.disc-from-switch.v0' \
    -H 'ce-time: 2023-06-08T19:37:42Z' \
    -X POST localhost:8080

echo "See docker container console for output"
