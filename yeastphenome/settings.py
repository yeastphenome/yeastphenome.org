import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuration environment
GOOGLE_ANALYTICS_SITE = os.environ.get("GOOGLE_ANALYTICS_SITE")
GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID")
TWITTER_USERNAME = os.environ.get("TWITTER_USERNAME")
INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME")
FACEBOOK_USERNAME = os.environ.get("FACEBOOK_USERNAME")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
GITHUB_DOCUMENTATION = os.environ.get("GITHUB_DOCUMENTATION")

# SendGrid and Help Contact Email
HELP_CONTACT_EMAIL = os.environ.get("HELP_CONTACT_EMAIL")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDGRID_SENDER_EMAIL = os.environ.get("SENDGRID_SENDER_EMAIL", HELP_CONTACT_EMAIL)
ENTREZ_EMAIL = os.environ.get("ENTREZ_EMAIL", HELP_CONTACT_EMAIL)

# You likely will need to set the domain name after it's been allocated
# E.g., https://<app-name>-01.uc.r.appspot.com/
DOMAIN_NAME = os.environ.get("DOMAIN_NAME", "http://127.0.0.1:8000")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Update the secret key to a value of your own before deploying the app.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True if os.getenv("DEBUG") != "false" else False

# SECURITY WARNING: App Engine's security features ensure that it is safe to
# have ALLOWED_HOSTS = ['*'] when the app is deployed. If you deploy a Django
# app not on App Engine, make sure to set an appropriate host here.
# See https://docs.djangoproject.com/en/2.1/ref/settings/
ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    "yeastphenome.apps.common",
    "yeastphenome.apps.conditions",
    "yeastphenome.apps.datasets",
    "yeastphenome.apps.papers",
    "yeastphenome.apps.phenotypes",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "rest_framework",
    "drf_yasg",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "yeastphenome.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "yeastphenome.context_processors.globals",
            ],
        },
    },
]

TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG
WSGI_APPLICATION = "yeastphenome.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

# Case 1: we are running locally but want to do migration, etc. (set False to True)
if False and os.getenv("APP_ENGINE_HOST") != None:
    print("Warning: connecting to production database.")

    # Running in development, but want to access the Google Cloud SQL instance in production.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "USER": os.getenv("APP_ENGINE_USERNAME"),
            "PASSWORD": os.getenv("APP_ENGINE_PASSWORD"),
            "NAME": os.getenv("APP_ENGINE_DATABASE"),
            "HOST": os.getenv("APP_ENGINE_HOST"),  # Set to IP address
            "PORT": "",  # empty string for default.
        }
    }

# Case 2: we are running on app engine
elif os.getenv("APP_ENGINE_CONNECTION_NAME") != None:

    # Running on production App Engine, so connect to Google Cloud SQL using
    # the unix socket at /cloudsql/<your-cloudsql-connection string>
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": "/cloudsql/%s" % os.getenv("APP_ENGINE_CONNECTION_NAME"),
            "USER": os.getenv("APP_ENGINE_USERNAME"),
            "PASSWORD": os.getenv("APP_ENGINE_PASSWORD"),
            "NAME": os.getenv("APP_ENGINE_DATABASE"),
        }
    }

# Case 3: Database local development uses DATABASE_* variables
elif os.getenv("DATABASE_HOST") is not None:
    # Make sure to export all of these in your .env file
    DATABASES = {
        "default": {
            "ENGINE": os.environ.get("DATABASE_ENGINE", "django.db.backends.mysql"),
            "HOST": os.environ.get("DATABASE_HOST"),
            "USER": os.environ.get("DATABASE_USER"),
            "PASSWORD": os.environ.get("DATABASE_PASSWORD"),
            "NAME": os.environ.get("DATABASE_NAME"),
        }
    }
else:
    # Use sqlite when testing locally
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        }
    }

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa: 501
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",  # noqa: 501
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",  # noqa: 501
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",  # noqa: 501
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_ROOT = "static"
STATIC_URL = "/static/"
MEDIA_ROOT = "data"
MEDIA_URL = "/data/"

# Download prefix for libChEBIpy
DOWNLOAD_PREFIX = os.environ.get("YEASTPHENOME_DOWNLOAD_PREFIX", MEDIA_ROOT)

# Rate Limiting

VIEW_RATE_LIMIT = "5000/1d"  # The rate limit for each view, django-ratelimit, "50 per day per ipaddress)
VIEW_RATE_LIMIT_BLOCK = (
    True  # Given that someone goes over, are they blocked for the period?
)

# On any admin or plugin login redirect to standard social-auth entry point for agreement to terms
LOGIN_REDIRECT_URL = "/login"
