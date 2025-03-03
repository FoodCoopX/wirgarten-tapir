#!/bin/sh

# Run this from inside the "web" container, where poetry and django are running

poetry run python ./manage.py spectacular --file schema.yml