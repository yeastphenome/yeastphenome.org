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
git clone https://github.com/vsoch/yeastgenome.org
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

#### Help Contact Email

You should export your `HELP_CONTACT_EMAIL` in the .env file as follows:

```
export HELP_CONTACT_EMAIL=myemail@domain.com
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

We will be testing [this](https://cloud.google.com/python/django/appengine#deploying_the_app_to_the_standard_environment_)
and we'll need to figure out how to adopt the current need to download files to be supported by app engine.

<hr>
