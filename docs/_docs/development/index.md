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


### SendGrid Secrets

We will use SendGrid to possibly send updates or notifications (not developed yet). 
This is not currently required to add.

#### SendGrid Sender Email

You'll need a `SENDGRID_SENDER_EMAIL` exported in your .env file in order to use
SendGrid:

```
export SENDGRID_SENDER_EMAIL=myemail@domain.com
```

If this is the same as your `HELP_CONTACT_EMAIL` you can leave it blank, and the help
contact email will be used. **Important** before using the API this email needs to be added as a known [Sender](https://app.sendgrid.com/settings/sender_auth/senders). If it is not, you will get a permission denied error. You
also likely want to go to Settings -> Tracking and disable link tracking in email.

#### SendGrid Setup

To send emails from the server, we will use SendGrid. This means
that you need to [sign up](https://app.sendgrid.com/) for an account (the basic account with 100 emails
per day is free) and then add the `SENDGRID_API_KEY` to your .env file:

```python
export SENDGRID_API_KEY=xxxxxxxxxxxxxxx
```

Then to create your key:

 1. Go to [SendGrid](https://app.sendgrid.com/) and click on Settings -> Api keys in the left bar
 2. Click the blue button to "Create API key"
 3. Give your key a meaningful name (e.g., freegenes_dev_test)
 4. Choose "Restricted Access" and give "Full Access" to mail send by clicking the bar on the far right circle.
 5. Copy it to a safe place, likely your settings/config.py (it is only shown once!)

If the value is found to be None, emails will not be sent.


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

You might also want to import dummy data for the models, although this is not required.


```bash
# not yet developed
$ python manage.py import_models
```

We would typically use the `manage.py` to run the server.

```bash
python manage.py runserver
```

But there is also a make command that is easier to type:

```bash
make run
```

And then you can open up your browser to [http://localhost:8000](http://localhost:8000).

### Deployment

We will be testing [this](https://cloud.google.com/python/django/appengine#deploying_the_app_to_the_standard_environment_)
and we'll need to figure out how to adopt the current need to download files to be supported by app engine.

<hr>
