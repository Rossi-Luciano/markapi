# MarkAPI — SciELO Research Communication Tools (RCT)

[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

Repositório: [scieloorg/markapi](https://github.com/scieloorg/markapi) · Licença: GPLv3

Documentação completa em texto: **[README.txt](README.txt)**

---

## Objetivo do projeto

Plataforma para produção, avaliação e rastreio de objetos de comunicação de pesquisa (manuscritos, preprints, artigos, dados, livros, capítulos), com **XML SPS** como registro único e rastreável.

| Área | Descrição |
|------|-----------|
| Marcação | Pipeline DOCX/LaTeX/ODT → XML SPS com LLM; revisão humana sempre possível |
| Validação | Schemas, regras de negócio e packtools |
| Avaliação | Checklists (CONSORT, PRISMA, STROBE, ARRIVE) e critérios FAIR no XML |
| Saídas | Pacote SPS, PDF, HTML, XML Crossref/PubMed/PMC, JSON DOAJ |
| Integração | API REST (JWT); Wagtail embutido; SciELO Core e publicação via Upload/OPAC |

**Stack:** Python 3.12, Django 6, Wagtail 7.4, DRF, Celery, Redis, PostgreSQL, packtools.

**Princípios:** IA auxilia, humano revisa; integração aditiva a sistemas editoriais existentes; LLM preferencialmente on-premise.

---

## Desenvolvimento

**Pré-requisitos:** Docker, Docker Compose, Make.

| Serviço | URL local |
|---------|-----------|
| Wagtail/Django | http://127.0.0.1:8009 |
| MailHog | http://127.0.0.1:8029 |
| PostgreSQL | `localhost:5439` |
| Redis | `localhost:6399` |

```bash
make build
make up
make django_migrate
make django_createsuperuser
```

```bash
make help    # todos os alvos Make
```

Compose: `local.yml` (dev). Ambiente em `.envs/.local/`. Volume Postgres: `../scms_data/markapi/data_dev`.

**Modelo LLM:** [wiki — baixar e configurar modelo](https://github.com/scieloorg/markapi/wiki/Guia-r%C3%A1pido:-baixar-e-configurar-o-modelo-do-MarkAPI-para-marca%C3%A7%C3%A3o-de-refer%C3%AAncias-em-PDF)

---

## Testes

Settings: `config.settings.test` · Guia: **[docs/testing.md](docs/testing.md)**

```bash
make build
make up
make django_migrate
make django_test      # manage.py test
make django_fast
make pytest
make pytest_fast
make pytest_cov
```

```bash
docker compose -f local.yml run --rm django python manage.py test --settings=config.settings.test
docker compose -f local.yml run --rm django pytest
```

CI: job `tests` em `.github/workflows/ci.yml` (`manage.py test` + `pytest`, sem ignorar falhas).

---

## Configuração

### Módulos Django

| `DJANGO_SETTINGS_MODULE` | Uso |
|--------------------------|-----|
| `config.settings.local` | Desenvolvimento (defeito do `manage.py`) |
| `config.settings.production` | Produção |
| `config.settings.test` | Testes (`make django_test`, `pytest`) |

### Ficheiros de ambiente

- `.envs/.local/.django` — `USE_DOCKER`, `REDIS_URL`, `HF_TOKEN`, `FETCH_DATA_TIMEOUT`, Flower
- `.envs/.local/.postgres` — `POSTGRES_*`
- `.envs/.production/.django` — `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `SENTRY_DSN`, …

No container, o entrypoint define `DATABASE_URL` e `CELERY_BROKER_URL` a partir de `POSTGRES_*` e `REDIS_URL`.

### Variáveis principais

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | PostgreSQL (montada no entrypoint) |
| `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` | Credenciais e base |
| `REDIS_URL` | Redis (ex.: `redis://redis:6379/0`) |
| `CELERY_BROKER_URL` | Broker Celery (= `REDIS_URL` no entrypoint) |
| `DJANGO_SECRET_KEY` | Chave secreta (produção) |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origens CSRF |
| `LLAMA_ENABLED` | Ativar LLM local (`false` em testes) |
| `HF_TOKEN` | Token Hugging Face (download do modelo) |
| `CORE_API_DOMAIN` | API SciELO Core (defeito `https://core.scielo.org`) |
| `DRF_PAGE_SIZE` | Paginação da API REST |
| `SENTRY_DSN` | Monitorização (produção) |
| `COMPRESS_ENABLED` | Compressor de estáticos (produção) |

Lista completa e notas: **[README.txt](README.txt)** (secção 4).

### Requisitos Python

- `requirements/base.txt` — runtime
- `requirements/local.txt` — dev + pytest
- `requirements/production.txt` — produção

Após alterar dependências: `make build`.

---

## Outros

```bash
mypy core    # verificação de tipos (não é suite de testes)
```

**Celery:** serviços `celeryworker` e `celerybeat` no `local.yml`.

**Deploy:** ver `production.yml` e documentação Docker do projeto.

**Docs:** `docs/testing.md`, `docs/pr/`
