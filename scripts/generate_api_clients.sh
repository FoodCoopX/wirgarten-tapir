#!/bin/sh

# Run this from inside the "vite" docker container, where NPM and Vite are running

npx openapi-generator-cli generate -i schema.yml -g typescript-fetch -o ./src_frontend/api-client