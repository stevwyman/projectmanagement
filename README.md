
# budget

![Python](https://img.shields.io/badge/Python-3.13-green.svg)
![Django](https://img.shields.io/badge/Django-5.1.7-green.svg)

a tool to track the budget in my projects

In a first step every project is defined with a budget.

In a second step all the "Expenditure Items" are being imported from Oracle and imported to a local database.

Then a consolidated view can be generated, that shows all expenditures that occurred by project. and in addition how much is left from the budget.

## backlog

- [ ] add a timestamp for the latest successful import

## manual

1. upload an oracle export and import it
2. update project and milestones
3. review your data :-)

### running local/locally

´´´sh
source ../budget-env/bin/activate
python projectmanagement/manage.py runserver
´´´´

### using podamn

```sh
podman build -f Dockerfile -t projectmanagement:latest --ignorefile .dockerignore
podman compose --file docker-compose.yaml up --detach
````

## setting up the development environment

```python
python3 manage.py makemigrations vmb
python3 manage.py migrate
python3 manage.py runserver
````

The below is for creating a project from scratch

```python
# setting up env
python3 -m venv budget-env

mkdir projectmanagement
django-admin startproject budget projectmanagement
cd projectmanagement
python3 manage.py startapp vmb

source ../../virtualenv/budget-env/bin/activate
pip3 install -r ../requirements.txt
````
