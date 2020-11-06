.PHONY: collect migrate migrations

# target: collect - calls the "collectstatic" django command
collect:
	python manage.py collectstatic --noinput

migrations: 
	python manage.py makemigrations
	python manage.py makemigrations common
	python manage.py makemigrations conditions
	python manage.py makemigrations datasets
	python manage.py makemigrations papers
	python manage.py makemigrations phenotypes

migrate: 
	python manage.py migrate

run: 
	python manage.py runserver

deploy_dev:
	gcloud app deploy app-dev.yaml
