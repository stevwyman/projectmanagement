#!/bin/sh

python my-budget/manage.py makemigrations vmb
python my-budget/manage.py migrate

exec "$@"