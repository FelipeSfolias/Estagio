from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def _simple_dotenv_values(dotenv_path: Path) -> dict[str, str]:
    if not dotenv_path.exists():
        return {}
    data: dict[str, str] = {}
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        if k:
            data[k] = v
    return data


try:
    from dotenv import dotenv_values  # type: ignore

    _env = {k: v for k, v in dotenv_values(BASE_DIR / ".env").items() if v is not None}
except ModuleNotFoundError:
    _env = _simple_dotenv_values(BASE_DIR / ".env")


def _env_str(key: str, default: str = "") -> str:
    v = _env.get(key)
    if v is None:
        v = os.environ.get(key, default)
    return str(v)


def _env_bool(key: str, default: bool = False) -> bool:
    v = _env.get(key)
    if v is None:
        v = os.environ.get(key)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _env_csv(key: str, default: list[str] | None = None) -> list[str]:
    raw = _env.get(key)
    if raw is None:
        raw = os.environ.get(key)
    if raw is None:
        return default or []
    return [p.strip() for p in str(raw).split(",") if p.strip()]


SECRET_KEY = _env_str("SECRET_KEY", "dev-only-change-me")
DEBUG = _env_bool("DEBUG", default=True)
ALLOWED_HOSTS = _env_csv("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
if DEBUG and "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.core",
    "apps.accounts",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "frontend" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "frontend",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/pos-login/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
