#!/bin/sh

# Run this from inside the "vite" docker container, where NPM and Vite are running
# Only regenerate if schema.yml has changed (using content hash)

SCHEMA_HASH_FILE=".schema.hash"
CURRENT_HASH=$(md5sum schema.yml | cut -d' ' -f1)

if [ -f "$SCHEMA_HASH_FILE" ]; then
  PREV_HASH=$(cat "$SCHEMA_HASH_FILE")
else
  PREV_HASH=""
fi

if [ "$CURRENT_HASH" != "$PREV_HASH" ]; then
  npx openapi-generator-cli generate \
    -i schema.yml \
    -g typescript-fetch \
    -o ./src_frontend/api-client \
    --additional-properties=sortParamsByRequiredFlag=false,sortModelPropertiesByRequiredFlag=false

  npx prettier --write --log-level error 'src_frontend/api-client/**/*.ts'
  echo "$CURRENT_HASH" > "$SCHEMA_HASH_FILE"
  echo "API client regenerated"
else
  echo "API client up to date (schema.yml unchanged)"
fi