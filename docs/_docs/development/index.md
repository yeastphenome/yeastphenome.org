---
title: Development
tags: 
 - jekyll
 - github
description: Getting started with YeastGenome.org Development
---

# Development

The documentation here will get you started to develop YeastGenome.org.
This documentation is intended for developers. If you are looking to use the interface,
please see the [user getting started]({{ site.baseurl }}/docs/getting-started/).
If you want to see migration notes from the previous deployment, read [migration](migration)

### Setup

You will want to follow the instructions [here](https://cloud.google.com/appengine/docs/standard/python3/building-app/writing-web-service)
and:

 - create a Google Cloud Project.
 - install the gcloud command line client and Python3+
 - authenticate on the command line with `gcloud auth application-default login`

For example, after I've created my project and I've installed gcloud, I might login and
then set the default project to be my new project:

```bash
$ gcloud auth application-default login
$ gcloud config set project <myproject>
```

Then to work locally (if you are developing) you'll want to clone the project:

```bash
git clone https://github.com/yeastgenome/yeastgenome.org
cd yeastgenome.org
```

On the [Google Project Console](https://console.developers.google.com/apis) you'll want to enable
APIs for:

 - Identity and Access Management (IAM) API
 - Google Storage

While you won't need these for a while, it's good to get it out of the way!

#### Storage

Since app engine doesn't allow writing to the filesystem, we will use Google Cloud Storage
for file uploads, and use the [django-storages](https://django-storages.readthedocs.io/en/latest/backends/gcloud.html) library to do this (not yet developed).

### Billing

Under billing, it's good practice to also set up billing alerts - unintended charges to a project that you don't know about can have dire consequences. A small server of this size shouldn't cost more than $55 a month (this would be a LOT) so I generally would start with a lower monthly limit (possibly $55) with alerts at 25, 50, 75, and 100 percents, and adjust as needed.

### Caching

By default, we will use a filesystem cache that expires every 24 hours. This should work on Google
App Engine as it has a /tmp directory stored via RAM. If you want to disable the cache for development:

```bash
export DISABLE_CACHE=True
```

or to permanently disable for a particular view:

```python
from django.views.decorators.cache import never_cache

@never_cache
def my_view(request):
   ...
```

By default it uses /tmp/yeastphenome-cache. You can delete the files in this folder
to clear it.

### Generating Similarities

We are still developing a Google Cloud equivalent to generate similarity values - ideally
we will have a scaled/parallel approach to write rows of similiarities to file, each looking
like this:

```
10311   10394   cosine  -0.014297323440217254   0.8156175716212475
10394   10311   cosine  -0.014297323440217254   0.8156175716212475
10311   2178    cosine  0.029105986454456237    0.033279284801702835
```
Where the values correspond to tab separated values `gene1_id gene2_id metric score pvalue`
and the score itself should be transformed to a Z score. Since you will likely need a lookup
to find a systematic name associated to a gene in the database, you can generate this via:

```bash
python manage.py create_gene_lookup
```
It will generate `genes-lookup.json` in the root directory.

```bash
cat genes-lookup.json |less
{
    "YBR094W": 41,
    "YFL058W": 85,
    "YBR089W": 87,
...
```

Where each systematic name (key) is matched to the gene id in the database.

### Configuration

The application has a set of configuration variables that are discovered in the environment
via an .env file that you can source before running the application, and these
environment variables are also given to the app engine app.yaml file so they are discovered
on App Engine. When you first start out, you can copy the dummy template provided in
the repository:

```bash
cp .dummy-env .env
```

and then populate the following configuration variables into that file.

#### Secret Key

A secret key is used to secure your server. You can use the [secret key generator](https://djecrety.ir/) to make a new secret key, and also export it as the `DJANGO_SECRET_KEY` in your `.env` file:

```bash
export DJANGO_SECRET_KEY=123455
```

#### Disable Cache

We have the ability to use a filesystem cache, meaning a folder in /tmp (`/tmp/yeast-phenome-cache`) that can save pages when we are developing, or on app engine. Since we've better
optimized most pages, we don't need this cache, and so it's recommended to export
this disable cache variable:

```bash
export DISABLE_CACHE=true
```

If you find that you are developing and pages aren't changing, likely you forgot
to export this before starting the server, and you can stop the server, delete
the temporary folder, export the variable, and start it again.


#### Google Analytics

If you want to use [Google Analytics](https://analytics.google.com/analytics/web/) with your application, generate a key and add it to your application, again in the `.env` file.

```bash
export GOOGLE_ANALYTICS_ID=1111111111111111
export GOOGLE_ANALYTICS_SITE=yeastgenome.org
```

#### Social Networks

If you want a twitter card / alias embedded in site metadata, export the `TWITTER_USERNAME` in your .env file.
The default is already set for MHTTC.

```bash
export TWITTER_USERNAME=calico
```

You can also easily link to an instagram or facebook.

```
export FACEBOOK_USERNAME=calico
export INSTAGRAM_USERNAME=calico
```

These last two are undefined by default and won't show on the site.

#### Authentication 

Authentication is only available to site admins, so we don't have a user login flow.
An administrator is responsible for adding new users. 

#### Emails

You should export your `HELP_CONTACT_EMAIL` in the .env file as follows:

```
export HELP_CONTACT_EMAIL=myemail@domain.com
```

And an email to provide for Entrez queries (interacting with Pubmed).

```bash
export ENTREZ_EMAIL=me@email.com
```

### Rate Limits

It's hard to believe that anyone would want to maliciously issue requests to your server,
but it's unfortunately a way of life. For this reason, some views will have a rate limit, along
with blocking ip addresses that exceed it (for the duration of the limit, one day). You
can customize this:

```python
VIEW_RATE_LIMIT="50/1d"  # The rate limit for each view, django-ratelimit, "50 per day per ipaddress)
VIEW_RATE_LIMIT_BLOCK=True # Given that someone goes over, are they blocked for the period?
```

And see the [django-ratelimit](https://django-ratelimit.readthedocs.io/en/v1.0.0/usage.html) documentation
for other options. 

### Database

For our database, we will use [cloud managed SQL](https://cloud.google.com/sql).
We won't need this for local development, for which we will use sqlite (a local file database). If you ever need to delete and refresh this local testing database, you can do:

```bash
rm db.sqlite3
```

For deployment, you'll need to first create your database in cloud managed sql,
and export these environment variables in your local .env file:

```
export MYSQL_HOST=<the.hostname>
export MYSQL_USER=<dbusername>
export MYSQL_PASSWORD=<dbpassword>
export MYSQL_DATABASE=<databasename>
```

And then at the onset of development, you'll need to both make and run migrations,
and collect static files.

```bash
make migrate
make migrations
make collect
```

### Development

To develop locally, you'll want to create a local environment and then install
dependencies to it.

```bash
python -m venv env
source env/bin/activate
pip install  -r requirements.txt
```

And always source this environment before you start working.
Then you will want to source your environment file:

```bash
source .env
```

To make migrations we usually might do this:

```bash
python manage.py makemigrations
python manage.py makemigrations main
python manage.py migrate
```

But to make it easier, there is an included Makefile that can be used to make
migrations, and then migrate.

```bash
make migrations
make migrate
```

Then we would typically use the `manage.py` to run the server.

```bash
python manage.py runserver
```

But there is also a make command that is easier to type:

```bash
make run
```
And then you can open up your browser to [http://localhost:8000](http://localhost:8000).


### Database Import

#### Legacy Import

The original application used a postgres database, and if you have access to this
dump you might want to import it into a postgres container and then connect to your
application. Here is how to do this. First, make sure that you have the dump,
which should be an .sql file.

```bash
yeastphenome_db.P.sql 
```

Note that you might need to decompress this if there is an additional extension like bz2 or .gz.
The repository has a docker folder where you can use Docker compose to start a postgres container.
Note that you'll need to create an .env file alongside the docker-compose.yml to have the correct credentials for the import. For example:

```bash
POSTGRES_USER=pancakes
POSTGRES_PASSWORD=topsecretstuff
```

Then bring up the container:

```bash
$ docker-compose up -d
Creating docker_postgres_1 ... done
```

and then shell into the container:

```bash
$ docker exec -it docker_postgres_1 bash
```

You can navigate to where you placed the file:

```bash
cd /docker-entrypoint-initdb.d/
```

And first create any additional roles that your database has (if you try the import
and get an error because a role doesn't exist, you'll need to start over and create the roles first).

```bash
psql -U ${POSTGRES_USER} 
psql (12.3 (Debian 12.3-1.pgdg100+1))
Type "help" for help.

pancakes=# CREATE ROLE username1;
CREATE ROLE
pancakes=# CREATE ROLE username2;
CREATE ROLE
```
And then issue this command to import:

```bash
psql -U ${POSTGRES_USER} -f yeastphenome_db.P.sql
```

Make sure to scroll up to the beginning to ensure that there are no error messages!
You can then interact with the database to make sure the tables exist.

```bash
psql -U ${POSTGRES_USER} 
/dt

                     List of relations
 Schema |                Name                | Type  | Owner 
--------+------------------------------------+-------+-------
 public | auth_group                         | table | pancakes
 public | auth_group_permissions             | table | pancakes
 public | auth_permission                    | table | pancakes
 public | auth_user                          | table | pancakes
 public | auth_user_groups                   | table | pancakes
 public | auth_user_user_permissions         | table | pancakes
 public | conditions_condition               | table | pancakes
 public | conditions_conditionset            | table | pancakes
 public | conditions_conditionset_conditions | table | pancakes
 public | conditions_conditiontype           | table | pancakes
 public | conditions_conditiontype_tags      | table | pancakes
 public | conditions_conditiontypegroup      | table | pancakes
...
```

Great! Now you can add the database credentials to your settings.py file, which
is done by way of the environment. Note that for this development database,
since we are exporting postgres, we need to also change the default engine to that.

```bash
export DATABASE_HOST=localhost
export DATABASE_USER=pancakes
export DATABASE_PASSWORD=topsecretstuff
export DATABASE_NAME=nameofthedatabase
export DATABASE_ENGINE=django.db.backends.postgresql
```

Make sure this is sourced before starting the server. You'll likely get a message about 
migrations not done yet, in the case that you are importing an older database:

```bash
$ make run
python manage.py runserver
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).

You have 15 unapplied migration(s). Your project may not work properly until you apply the migrations for app(s): admin, auth, conditions, datasets, papers, phenotypes.
Run 'python manage.py migrate' to apply them.

July 21, 2020 - 18:05:29
Django version 3.0.8, using settings 'yeastphenome.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```
If you get an error that the connection is refused, make sure that the container is running
and exposing port 5432, and that the same credentials that you used for your
postgres container are exported via the main .env file.

Note that you might need to use `--fake` for an original set of migrations
if they haven't been made before after the import:

```bash
python manage.py makemigrations
python manage.py migrate --fake
```

For example, migrations might look like the following. We try to migrate
between each command to figure out the next migration to fake, and run any migrations
that will work.

```bash
python manage.py migrate conditions 0001 --fake
python manage.py migrate
python manage.py migrate conditions 0002_auto_20201024_1938 --fake
python manage.py migrate
python manage.py migrate phenotypes 0001 --fake
python manage.py migrate
python manage.py migrate papers 0001 --fake
python manage.py migrate
python manage.py migrate datasets 0001 --fake
```
```bash
$ python manage.py migrate
Operations to perform:
  Apply all migrations: admin, auth, conditions, contenttypes, datasets, papers, phenotypes, sessions
Running migrations:
  Applying datasets.0002_gene... OK
  Applying datasets.0003_data_gene... OK
  Applying datasets.0004_datasetsimilarity_genesimilarity... OK
  Applying datasets.0005_auto_20200903_2004... OK
  Applying datasets.0006_auto_20200904_2323... OK
  Applying datasets.0007_auto_20200912_1726... OK
  Applying datasets.0008_auto_20200912_1854... OK
  Applying datasets.0009_auto_20200913_0310... OK
  Applying datasets.0010_auto_20200913_0312... OK
  Applying datasets.0011_auto_20200921_2027... OK
  Applying phenotypes.0002_remove_phenotype_observable2... OK
  Applying phenotypes.0003_delete_observable2... OK
```

#### Legacy Export

If we want to export just tables, we can do that with django `dumpdata.` This is useful to preserve the models
for different versions of the database that can more easily be imported into different
database types (e.g., postgres to mysql). From the root of the application run:

```bash
mkdir -p backup/legacy/postgres/original
python manage.py dumpdata conditions --output backup/legacy/postgres/original/conditions.json
python manage.py dumpdata phenotypes --output backup/legacy/postgres/original/phenotypes.json
python manage.py dumpdata datasets --output backup/legacy/postgres/original/datasets.json
python manage.py dumpdata papers --output backup/legacy/postgres/original/papers.json
```

For example, you might do the above, put somewhere for safekeeping, and then make changes to the
original database with makemigrations.  You can also dump sql from the database directly:


```bash
$ docker exec -it docker_postgres_1 bash
pg_dump -U ${POSTGRES_USER} ${POSTGRES_DATABASE} > exportname.pgsql
```

### Deployment

Make sure that you have followed the instructions for [migration](migration) of models (to add Genes, etc.)
before exporting and creating the database in Google Cloud. After we added genes 
(took about a day to populate, note that this might be tried
with some kind of multiprocessing approach to be faster, but I read a few un-successful
reports and decided to be conservative instead) we want to re-create the database
with cloud sql! Note that first we've set up and tested [Identity Aware Proxy](https://cloud.google.com/iap) 
(IAP) and are confident that we can deploy a Python 3 app to Google App Egine and have it
protected based on email addresses. Next we want to export the database dump. I wanted
to try both a standard dump, and the command  [recommended by Google](https://cloud.google.com/sql/docs/postgres/import-export/exporting#external-server).

```bash
$ docker exec -it docker_postgres_1 bash
pg_dump -U ${POSTGRES_USER} ${POSTGRES_DATABASE} > yeastphenome.pgsql

pg_dump -U ${POSTGRES_USER} --format=plain --no-owner --no-acl ${POSTGRES_DATABASE} | sed -E 's/(DROP|CREATE|COMMENT ON) EXTENSION/-- \1 EXTENSION/g' > yeastphenome-gcloud.sql
exit
```
```bash
docker cp docker_postgres_1:/yeastphenome.pgsql backup/legacy/postgres/removed-observable2/yeastphenome.pgsql
```

And then [import into cloud SQL](https://cloud.google.com/sql/docs/postgres/import-export/importing)
via storage. Note that you can do this upload to storage manually. This comes down to:

 1. Creating the postgres instance in managed SQL
 2. Uploading the dumps to storage
 3. Giving the instance IAM permission to access storage
 4. Importing in the console from storage
 5. Testing login credentials on the Google Cloud Shell

We then want to [connect from App Engine](https://cloud.google.com/sql/docs/postgres/connect-app-engine-standard).
This means that we need to add the Cloud SQL client to the app engine default service account,
and optionally download the [local sql proxy](https://cloud.google.com/python/django/appengine#installingthecloudsqlproxy) (for local development). It also means that you (finally) need to create and populate the `app.yaml` file with credentials and
other environment settings:

```bash
cp app-example.yaml app.yaml
```

Any files that you don't want uploaded to storage you should add to the `.gcloudignore` file.
Also make sure you've recently collected static, so all files you need are in the static folder:

```bash
make collect
```

Since we are deploying to the [app engine standard environment](https://cloud.google.com/python/django/appengine#deploying_the_app_to_the_standard_environment_) if you've never done this before (and need to set up
and test the IAP) I would recommend deploying a dummy "hello world" project first. When you are ready, you can
deploy and then browse! Note that this deployment was adding a file, hence why there is only
one file to add. At the first go you'll see a few hundreds files.

```bash
$ gcloud app deploy
Services to deploy:

descriptor:      [/home/vanessa/Desktop/Code/yeastphenome.org/app.yaml]
source:          [/home/vanessa/Desktop/Code/yeastphenome.org]
target project:  [your-app-name-01]
target service:  [default]
target version:  [20200830t115100]
target url:      [https://your-app-name-01.uc.r.appspot.com]


Do you want to continue (Y/n)?  y

Beginning deployment of service [default]...
╔════════════════════════════════════════════════════════════╗
╠═ Uploading 1 file to Google Cloud Storage                 ═╣
╚════════════════════════════════════════════════════════════╝
File upload done.
Updating service [default]...done.                                                                                               
Setting traffic split for service [default]...done.                                                                              
Deployed service [default] to [https://your-app-name-01.uc.r.appspot.com]

You can stream logs from the command line by running:
  $ gcloud app logs tail -s default

To view your application in the web browser run:
  $ gcloud app browse
```

That's it! If you see a 500 (or other error) you can usually go to the
Google Cloud Logs console and see the debug output.

#### Migrations after deployment

If you want to make migrations *after* deployment, this is possible to do with
the [cloud sql proxy](https://cloud.google.com/sql/docs/mysql/quickstart-proxy-test).
For Linux this comes down to ensuring your Google Cloud user had admin access to the
Cloud sql, installing psql:

```bash
sudo apt-get install mysql-server
$ which mysql
/usr/bin/mysql
```

I also needed to stop the service after it was started:

```bash
$ sudo /etc/init.d/mysql stop
[ ok ] Stopping mysql (via systemctl): mysql.service.
```

Enabling the MySQL Admin API, ensuring you are logged in to your project,
stopping your local database:

```bash
cd docker
docker-compose stop
```

I also exported `GOOGLE_APPLICATION_CREDENTIALS` from my project, but I'm not sure
that's necessary. Then you can start the proxy with your instance name. Note that instructions for
postgres are [here](https://cloud.google.com/sql/docs/postgres/connect-admin-proxy).

```bash
cloud_sql_proxy -instances=<INSTANCE_CONNECTION_NAME>=tcp:5432
```

This should show that a new connection is started in the terminal running the proxy:

```bash
2020/09/12 11:42:31 New connection for "<INSTANCE_CONNECTION_NAME>"
```

You can then test connecting (with the credentials you created for the cloud database)

```bsah
psql "host=127.0.0.1 sslmode=disable dbname=<DB_NAME> user=<USER_NAME> password=<PASSWORD> port=5432"
```

In practice I found that if I don't include the port, it doesn't work. Once that
works, export the following environment variables (of course defined)

```bash
export APP_ENGINE_USERNAME=
export APP_ENGINE_PASSWORD=
export APP_ENGINE_DATABASE=
export APP_ENGINE_HOST=127.0.0.1
```

And then in settings.py, navigating to the Database section and changing the False
to True. Change this:

```python
# Case 1: we are running locally but want to do migration, etc. (set False to True)
if False and os.getenv("APP_ENGINE_HOST") != None: 
    print("Warning: connecting to production database.")

...
```

to this

```python
# Case 1: we are running locally but want to do migration, etc. (set False to True)
if True and os.getenv("APP_ENGINE_HOST") != None: 
    print("Warning: connecting to production database.")

```
<hr>

You then likely want to make /run migrations.

```bash
make migrations
make migrate
```

#### Resident Instances

App Engine by default will start an instance on demand. This is good for small or
not-regularly-visited apps, but if you want your server to load more quickly, it's
recommended to use resident instances. The way to do this is to set the 
[min_idle_instances](https://cloud.google.com/appengine/docs/standard/python/config/appref#min_idle_instances)
variable to be 1, ensuring that there is something always running.
