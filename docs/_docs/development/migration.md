---
title: Migration
tags: 
 - jekyll
 - github
description: Notes for migration from the previous to new deployment
---

# Removal of Observable2 Model

We decided on the following steps to remove the Observable2 model.

#### First check for observable2 and mptt in code

Largely these modules / model classes were defined in the admin.py and models.py
functions for the phenotype app. Before touching these, we will want to remove
the models completely from the database, the next step.

#### Check that it's not cascade

Before deleting anything, we verify that the Observable2 model is set to DONOTHING.

```python
    observable2 = TreeForeignKey(
        Observable2, blank=True, null=True, on_delete=models.DO_NOTHING
    )
```

#### Set all observable2 id to None

Next we want to open a shell and set all observable2 to None.

```bash
python manage.py shell
```

```python
from yeastphenome.apps.phenotypes.models import Phenotype

for p in Phenotype.objects.all(): 
    p.observable2 = None 
    p.save() 
```

#### Remove field observable2 from phenotype

We can now delete the Observable2 field, and make a migration for that change.

```bash
$ make migrations
python manage.py makemigrations
Migrations for 'phenotypes':
  yeastphenome/apps/phenotypes/migrations/0002_remove_phenotype_observable2.py
    - Remove field observable2 from phenotype
python manage.py makemigrations common
No changes detected in app 'common'
python manage.py makemigrations conditions
No changes detected in app 'conditions'
python manage.py makemigrations datasets
No changes detected in app 'datasets'
python manage.py makemigrations papers
No changes detected in app 'papers'
python manage.py makemigrations phenotypes
No changes detected in app 'phenotypes'
(env) (base) vanessa@vanessa-ThinkPad-T490s:~/Desktop/Code/yeastphenome.org$ make migrate
python manage.py migrate
Operations to perform:
  Apply all migrations: admin, auth, conditions, contenttypes, datasets, papers, phenotypes, sessions
Running migrations:
  Applying phenotypes.0002_remove_phenotype_observable2... OK
```

#### Remove model from database

We can now delete all instances of observable2

```bash
python manage.py shell
```
```python
for o in Observable2.objects.all(): 
    o.delete() 
```

And then delete the Model itself from models.py, and any references
in admin.py. There were also references in datasets/views.py, which I believe
can be updated from Observable2 to Observable.

```bash
$ python manage.py makemigrations
Migrations for 'phenotypes':
  yeastphenome/apps/phenotypes/migrations/0003_delete_observable2.py
    - Delete model Observable2
(env) (base) vanessa@vanessa-ThinkPad-T490s:~/Desktop/Code/yeastphenome.org$ python manage.py migrate
Operations to perform:
  Apply all migrations: admin, auth, conditions, contenttypes, datasets, papers, phenotypes, sessions
Running migrations:
  Applying phenotypes.0003_delete_observable2... OK
```

#### delete methods that rely on observable2

We can now delete references to Observable2 fields in models (Phenotype has several)
along with imports of mptt, and remove the module from being required.

#### export database / upload to google drive with removed

After that, we would want to again export the development database, and add the new migrations.

```bash
mkdir -p backup/legacy/postgres/removed-observable2
python manage.py dumpdata conditions --output backup/legacy/postgres/removed-observable2/conditions.json
python manage.py dumpdata phenotypes --output backup/legacy/postgres/removed-observable2/phenotypes.json
python manage.py dumpdata datasets --output backup/legacy/postgres/removed-observable2/datasets.json
python manage.py dumpdata papers --output backup/legacy/postgres/removed-observable2/papers.json
```
And also export full sql

```bash
$ docker exec -it docker_postgres_1 bash
pg_dump -U ${POSTGRES_USER} ${POSTGRES_DATABASE} > yeastphenome.pgsql
exit
```

And copy from the container to host

```bash
docker cp docker_postgres_1:/yeastphenome.pgsql backup/legacy/postgres/removed-observable2/yeastphenome.pgsql
```

And upload these to a shared Google Drive (or other place) for safekeeping. 
