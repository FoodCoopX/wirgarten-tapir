#!/bin/sh

awk -F ";" 'NR!=1 {cmd="echo Importing masterdata " $1 "/" $2 " && poetry run ./manage.py loaddata --app " $1 " " $2; system(cmd)}' masterdata.csv