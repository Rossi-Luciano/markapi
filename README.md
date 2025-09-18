# MarkAPI

MarkAPI is a project designed to tag, validate, and convert XML documents in the SciELO publishing context. It offers tools for:

- Tagging XML structure and content
- Validating XML against defined schemas, business rules and content
- Converting XML to HTML, DOCX, and PDF

[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

License: GPLv3

---

## Development Environment

You can use Docker directly or via `make`. To see available commands:

```bash
make help
```

Example output:

```bash
Usage: make [target] [argument] ...

Argument:
    compose = {compose_file_name}

Targets:
    help                                Show this help
    app_version                         Show app version
    vcs_ref                             Show last commit ref
    build_date                          Show build date
    build                               Build app using $(COMPOSE_FILE_DEV)
    up                                  Start app using $(COMPOSE_FILE_DEV)
    logs                                Show logs using $(COMPOSE_FILE_DEV)
    stop                                Stop app using $(COMPOSE_FILE_DEV)
    ps                                  Show containers using $(COMPOSE_FILE_DEV)
    rm                                  Remove containers using $(COMPOSE_FILE_DEV)
    django_shell                        Open Django shell
    wagtail_sync                        Sync Wagtail page fields
    wagtail_update_translation_field    Update Wagtail translation fields
    django_createsuperuser              Create Django superuser
    django_bash                         Bash into Django container
    django_test                         Run Django tests
    django_fast                         Run fast Django tests
    django_makemigrations               Make migrations
    django_migrate                      Apply migrations
    django_makemessages                 Run makemessages
    django_compilemessages              Run compilemessages
    django_dump_auth                    Dump Django auth data
    django_load_auth                    Load Django auth data
    dump_data                           Dump database to .sql
    restore_data                        Restore database from .sql
```

### Common Commands

Build the development environment:

```bash
make build compose=local.yml
# or simply
make
```

Start the project:

```bash
make up
```

Stop the project:

```bash
make stop
```

To use a custom `.yml` or environment, copy `.envs` and `compose` folders, then run:

```bash
make <target> compose=your_config.yml
```

The stack uses two Docker Compose files:

* `local.yml` (development)
* `production.yml` (production)

---

## Settings

Refer to the [settings documentation](http://cookiecutter-django.readthedocs.io/en/latest/settings.html).

---

## Usage Guide

### User Setup

* **Normal user:** Sign up via UI. Confirm email using the console output.
* **Superuser:** Run:

```bash
python manage.py createsuperuser
```

Use different browsers to test both user types simultaneously.

---

### Type Checks

```bash
mypy core
```

---

### Testing

Run tests and generate coverage report:

```bash
coverage run -m pytest
coverage html
open htmlcov/index.html
```

Or just:

```bash
pytest
```

---

### Live Reload & Sass

See: [Live reloading & SASS](https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html#sass-compilation-live-reloading)

---

### Celery

To start a worker:

```bash
cd core
celery -A config.celery_app worker -l info
```

Ensure you're in the correct directory (`core`) for Celery to work properly.

---

### Email (MailHog)

A local SMTP server with web UI is included.

Access at: `http://127.0.0.1:8025`

See [Docker deployment docs](http://cookiecutter-django.readthedocs.io/en/latest/deployment-with-docker.html) for details.

---

### Sentry

Sentry is pre-configured for logging. Set the DSN URL in production.

Signup at: [https://sentry.io/signup/?code=cookiecutter](https://sentry.io/signup/?code=cookiecutter)

---

## Deployment

See full [Docker deployment guide](http://cookiecutter-django.readthedocs.io/en/latest/deployment-with-docker.html).

## Download Model

https://github.com/scieloorg/markapi/wiki/Guia-r%C3%A1pido:-baixar-e-configurar-o-modelo-do-MarkAPI-para-marca%C3%A7%C3%A3o-de-refer%C3%AAncias-em-PDF
