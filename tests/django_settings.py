"""
Minimal Django settings for running chowkidar tests standalone.
"""
import os

SECRET_KEY = "test-secret-key-for-chowkidar-unit-tests"
DEBUG = True
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
AUTH_USER_MODEL = "auth.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Chowkidar settings
JWT_SECRET_KEY = "test-jwt-secret"
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "chowkidar-tests"
JWT_LEEWAY = 10
