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

# Addition of Gene to Datasets App

This migration includes the following:

 - creating a Gene model under datasets
 - using the Data.orf field to populate it
 - making a foreign key to the gene from the Data model.

Although the last step should be to delete the orf field, for the time being (while
the database isn't completely redone in production) we are going to leave the model.
That way, we can easily add the Gene model:

```
class Gene(models.Model):
    systematic_name = models.CharField(max_length=50, null=True, blank=True, unique=True) # previously data.orf field
    common_name = models.CharField(max_length=50, null=True, blank=True)
#    aliases
```

and then make migrations:

```bash
make migrations
make migrate
```

and then add the foreign key to it alongside the Data.orf model:

```bash
class Data(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.DO_NOTHING)
    value = models.DecimalField(max_digits=10, decimal_places=3)
    orf = models.CharField(max_length=50)
    # this is added, note that we aren't deleting orf because we need the values!
    gene = models.ForeignKey(
        "datasets.Gene", null=True, blank=True, on_delete=models.DO_NOTHING
    )
```

and again migrate.

```bash
make migrations
make migrate
```

And now you should be able to run the script to generate the gene foreign keys
(and genes) to associate with a dataset.

```bash
$ python manage.py create_genes
Creating genes...
Created or found 11287 genes.
Updating data... this may take some time!
```

And this does take some time! When the database is in production and the genes
added, the orf field can be removed with another migrations.

# Import of GeneSimilarity and DatasetSimilarity scores

After adding the `DatasetSimilarity` and `GeneSimilarity` models, instead of calculating
them for pairwise datasets and genes, we can start with an initial data import.
In the project [yeastphenome_data_transfer](https://console.cloud.google.com/storage/browser/yeastphenome_data_transfer)
bucket, there are two HDF (*.h5) files that include:

 - yp_cols_store.h5 contains the correlations between datasets.
 - yp_rows_store.h5 contains the correlations between genes.

Since pandas is required to read the data (but isn't a dependency of the deployed
server) you should install it to your local development environment only (and do not
add to the requirements.txt).

```bash
source env/bin/activate
# installed verison 1.1.1 at time of development
pip install pandas
# installed version 3.6.1 at time of development
pip install tables
```

You can then import each of dataset similarity and gene similarity by doing
the following:

```bash
$ python manage.py import_gene_similarities yp_rows_store.h5 
$ python manage.py import_dataset_similarities yp_cols_store.h5 
```
We only import the diagonal, so we do a check for the existence of gene1|gene2 and gene2|gene1.

Both files contain a dictionary of dataframes, and we care about the cosine similarity score,
and the pvalue, both of which are added to each of the `DatasetSimilarity` and `GeneSimilarity` models.
The index of the gene data file (rows) is the gene systematic name (=ORFs, for  yp_rows_store.h5), and for the datasets file (for yp_cols_store.h5)
is the dataset id.

As an alternative, if you can produce a file of rows (gene or dataset similarities) in the format

```
gene1	gene2	score	pvalue
dataset1	dataset2	score	pvalue
```

You can also give this .tsv file to either script, and it will do a postgres copy
instead. These files were also generated by Anastasia and provided in the same storage bucket:

 - genesim-exports.tsv
 - datasim-exports.tsv

We tested this [here](https://github.com/vsoch/django-create-benchmark) and it is much
faster! For the datasim-exports, if the files are too big so the database proxy connection
cuts and the transaction is broken, we can split into a subset of smaller files comparable to
the genesim exports:

```bash
split -l 20000000 datasim-export.tsv datasim-export-partial
```
