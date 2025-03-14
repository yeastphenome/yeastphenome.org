import os
import re
import tempfile

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuration environment
GOOGLE_ANALYTICS_SITE = os.environ.get("GOOGLE_ANALYTICS_SITE", "")
GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID", "")

# Email Addresses
HELP_CONTACT_EMAIL = os.environ.get("HELP_CONTACT_EMAIL")
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
DEBUG = os.environ.get("DEBUG", "False")
DISABLE_CACHE = os.environ.get("DISABLE_CACHE", "False")

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
    "yeastphenome.apps.genes",
    "yeastphenome.apps.papers",
    "yeastphenome.apps.phenotypes",
    "yeastphenome.apps.tags",
    "yeastphenome.apps.search",
    "yeastphenome.apps.downloads",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.sitemaps",
    "django.contrib.sites",
    "django.contrib.staticfiles",
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Do we want to enable the cache?

if not DISABLE_CACHE:
    MIDDLEWARE += [
        "django.middleware.cache.UpdateCacheMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.cache.FetchFromCacheMiddleware",
    ]

    CACHE_MIDDLEWARE_ALIAS = "default"
    CACHE_MIDDLEWARE_SECONDS = 86400  # one day


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

# Cache to tmp
CACHE_LOCATION = os.path.join(tempfile.gettempdir(), "yeastphenome-cache")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": CACHE_LOCATION,
    }
}

if not os.path.exists(CACHE_LOCATION):
    os.mkdir(CACHE_LOCATION)

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases


# Case 1: we are running locally but want to do migration, etc. (set False to True)
if True and os.getenv("APP_ENGINE_HOST") != None:
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

    # Ensure debug is absolutely off
    TEMPLATES[0]["OPTIONS"]["debug"] = False
    DEBUG = False

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

    # If we are on app engine, ensure https only
    SECURE_SSL_REDIRECT = False
    # But on the staging service, allow http (needed for Google Cloud Scheduler to run)
    if os.getenv("APP_ENGINE_SERVICE") != "staging":
        SECURE_SSL_REDIRECT = True


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
SITE_ID = 1


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_ROOT = os.environ.get("STATIC_ROOT", "yeastphenome-static/")
STATIC_URL = os.environ.get("STATIC_URL", "/static/")

MEDIA_ROOT = "data"
MEDIA_URL = "/data/"

# Download prefix for filenames
DOWNLOAD_PREFIX = os.environ.get("YEASTPHENOME_DOWNLOAD_PREFIX", "YeastPhenome")

# Rate Limiting

# The rate limit for each view, django-ratelimit, "50 per day per ipaddress)
VIEW_RATE_LIMIT = "5000/1d" if DEBUG else "50/1d"
VIEW_RATE_LIMIT_BLOCK = (
    True  # Given that someone goes over, are they blocked for the period?
)

# On any admin or plugin login redirect to standard social-auth entry point for agreement to terms
LOGIN_REDIRECT_URL = "/login"

ELASTICSEARCH_HOST = os.environ.get("ELASTICSEARCH_HOST")
ELASTICSEARCH_AUTH = os.environ.get("ELASTICSEARCH_AUTH")

CSRF_USE_SESSIONS = True
CSRF_COOKIE_HTTPONLY = True

DISALLOWED_USER_AGENTS = [
    re.compile(r'^Bytespider'),
]
