#!/bin/sh

# Run this from inside the "vite" docker container, where NPM and Vite are running

npx openapi-generator-cli generate -i schema.yml -g typescript-fetch -o ./src_frontend/api-client

# The generator emits imports for functions it does not write on union models.
# Without this the freshly generated client does not compile.
node scripts/patch_api_client_unions.mjs
