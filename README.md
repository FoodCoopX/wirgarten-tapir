# Tapir

[![Python code test coverage](https://sonarcloud.io/api/project_badges/measure?project=FoodCoopX_wirgarten-tapir&metric=coverage)](https://sonarcloud.io/summary/overall?id=FoodCoopX_wirgarten-tapir&branch=master)

Tapir is a management system for community supported agriculture. It is currently used productively by several
organizations,
including [WirGarten Lüneburg eG](https://lueneburg.wirgarten.com/), [Möllers Morgen](https://www.moellersmorgen.de), [Gemüsekollektiv Hebenshausen e.V.](https://gemuesekollektiv.org),
and more.

Its features include:

- Member & membership management including cooperative shares
- Contract management: yearly commitment, weekly deliveries, solidarity contributions, renewal...
- Communication with the members with customizable automated mails
- Delivery locations and capacity management
- And more

The development is lead mainly by [Théo](https://seriousdino.org/) for [FoodCoopX](https://foodcoopx.de/).

The backend code is written with Python and Django, the frontend code is a mix of Django templates and React.

Don't hesitate to contact us if you are interested in using or contributing to Tapir.

## User documentation

The user documentation is maintained as Markdown files in [`docs/`](docs/) and published as a searchable website with
MkDocs and GitHub Pages. See [Contributing to the documentation](CONTRIBUTING.md#contributing-to-the-documentation) to
preview documentation changes locally.

## Getting started

Use docker to quickly get a development server running on your machine. Run the following commands:

```sh
make up
# Create tables, define the configuration parameters, generate test data
make migrate parameters populate
```

Alternatively, run the reset script: `./scripts/reset_all_containers.sh` (or `make reset`).

Every repetitive task has a `make` target — run `make help` to see them. They wrap the commands in
`docker compose exec web …` for you, which is where Django, `manage.py` and the tests have to run.
If you prefer typing the commands yourself, look at the [Makefile](Makefile): it is short and
deliberately readable.

You should now have a local instance accessible at http://localhost:8000/. You can log in as admin with username
`roberto.cortes@example.com` and password `roberto.cortes`.

You can log in as any user using the same pattern: `[name]@example.come` as username and `[name]` as password

### Django outside of Docker

You may want to run the Django server outside of Docker, for example if you want to run a debugger or to make it easier
to run tests from your IDE. To do that:

- Define a few environment variables: copy the .env.local.disabled file to .env.local, it's content
  will be read automatically.
- Start the non-django containers, the minimum you need is `docker compose up -d keycloak db redis` for a local Tapir
  instance, or just `db redis` if you just want to run automated tests.
- Start the django server with `poetry run python manage.py runserver`
- Start the vite server with `pnpm run dev`

If you want a fresh setup, for example after switching branches, the equivalent of `./scripts/reset_all_containers.sh`
is `./scripts/reset_and_start_local_server.sh`

## Contributing & GitHub issues

You are very welcome to try Tapir locally with the "Getting started" instructions above and do your own thing. The
current documentation being basically just this README, you may need extra guidance to get started. Don't hesitate to
contact us so that we can give you an introduction.

If you're looking for something to work on, filter the issues using
the [Ready to be worked on](https://github.com/FoodCoopX/wirgarten-tapir/issues?q=state%3Aopen%20label%3A%22Ready%20to%20be%20worked%20on%22)
label. Those issues should have a good enough description to get you started. Don't hesitate to ask more questions on
the issue directly if needed. If you do, also assign either Theo (for technical questions) or Marcus (for requirements
questions) to the issue, so that they know they have to react. They'll assign the issue back to you when the answer is
there.

You're of course free to check the other issues and ask questions about them, but be aware that they may not make sense
if you're not involved in the daily Tapir-development life. We don't have an internal tool to track tasks yet, so we use
the GitHub issues as our todo-list. Hopefully the labels will be enough to let you sort through the mess.

### Bäckerei (bakery)

The bakery is off by default and is switched on by setting the environment variable `BAKERY_ENABLED` to True. For a
local instance filled with test data — a bakery with one `Brotanteil` share, four pickup stations, breads and members —
set it and run:

```sh
make populate-bakery
```

The baking-plan solver needs `ortools`, the optional `bakery` extra in
`pyproject.toml`. The Docker image installs it (`poetry install --extras bakery`); without it the solver endpoints
answer 503.

## Tests

Tests are run with `pytest`, inside the `web` container:

```shell
make test-fast                      # the whole suite
make test-app APP=subscriptions     # just one app
make test                           # what CI runs: format check + coverage
```

If you run into troubles, run pytest without `--reuse-db -n auto`:
`docker compose exec web poetry run pytest`.

Unit and integration tests are not separated by path, so **running `pytest` on your host collects
the integration tests too and they fail**. Run them through the targets above, or — if you work
with the [Django outside of Docker](#django-outside-of-docker) setup — against a local server with
`db` and `redis` running.

### Keycloak during tests

User authentication is handled by keycloak through `django-allauth`. During integration tests, this connection is mocked
via `tapir.wirgarten.tests.test_utils.mock_keycloak`, called in `TapirIntegrationTest`. The mocking happen during
`setUp` and `setUpTestData` happens before `setUp`, that means we can't create users inside `setUpTestData`.

## Formatting

Python files are formatted with [Black](https://github.com/psf/black).

JavaScript and React files are formatted with [Prettier](https://prettier.io/).

Django template files are formatted with [DjHTML](https://github.com/rtts/djhtml)

Install the pre-commit hooks to make sure that the files you commit are properly formatted:
`poetry run pre-commit install`. It should be possible to configure your IDE of choice to run the formatting
automatically on save, at least for Black and Prettier. Look in their respective documentation.

## Frontend API clients

API Requests made from the React frontend use API clients. Here are the steps to get updated API clients:

- Annotate your API view with [Spectacular](https://github.com/tfranzel/drf-spectacular) (search for `@extend_schema(`
  for examples)
- Run `make schema`

That regenerates the schema file with `manage.py spectacular --file schema.yml` and then the
TypeScript clients with [OpenAPI Generator](https://openapi-generator.tech/). The underlying help
scripts live in the `/scripts` folder; the client step is a no-op when `schema.yml` did not change.
Commit `schema.yml`, `.schema.hash` and the regenerated client together with your backend change.

## Style and conventions

### Models

Models should inherit from `tapir.core.models.TapirModel`:

- It uses nanoid instead of integer IDs, that makes sure we never use an ID from a model when getting another model, for
  example in tests.
- It has `created_at` and `updated_at` fields that help unterstand the state of production databases.

As much as possible, model classes should contain only their own fields. Helper methods are OK if they only reference
the fields of the given object.

### Cache

Many functions, especially service functions, take a `cache` parameter which is a normal python dictionary. The goal of
this cache is to avoid redundant database requests within one http request: in most of our views, DB requests are the
most time-consuming part. The cache dictionary should be created at the origin point: for example in the view's
`__init__` function or the first lines or the command. Since this cache only lives for the duration of the request, in
most cases it is not necessary to invalidate it. If you do need to invalidate, look at
`tapir.utils.services.tapir_cache_manager.TapirCacheManager`
Some functions have the cache parameter optional. This is only because they are called in legacy code, all new functions
should have the cache parameter required if possible. For examples, see usages of
`tapir.utils.services.tapir_cache.TapirCache`.

### Service classes

Most of the business logic code should be in service classes. You can find examples in tapir/*/services/.

### Commits

Use [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) for your commit messages. When applicable,
add the ID of the related GitHub issue in the commit message.

### Legacy code

Everything that is under tapir/wirgarten should be considered legacy code. It doesn't respect the conventions above. If
you need to change anything in there, consider rewriting the part that you are changing and moving it to one of the
other apps.

## Testing mail integration

To make testing mail integration convenient, all mail is forwarded to a [Mailpit](https://mailpit.axllent.org/) instance.
This prevents leaking test emails to any real inboxes. The Mailpit instance is available at http://localhost:8025.

## Mailing lists

An optional integration with Mailman can be activated by setting MAILING_LISTS_ENABLED to True. The URL, username and
password parameters must be set (see `MAILMAN_*` in `settings/base.py`).

You can use this separate docker compose file to set this up:

```sh
docker compose -f docker-compose.mailman.yml up -d
```

In addition to the base services, this starts:

- Mailman API at http://localhost:8001/3.1/
- Mailman web UI at http://localhost:8002 (the user's email is admin@example.com, use the password reset
  function to set it. The reset mail will be accessible in Mailpit)

## Class diagram

[![models.png](models.png)](https://raw.githubusercontent.com/FoodCoopX/wirgarten-tapir/master/models.png)

If this graph is outdated, you can re-generate it with:

```shell
docker compose exec web sh -c "apt update && apt install -y graphviz graphviz-dev && poetry run pip install pygraphviz && poetry run python manage.py graph_models -a -g -o models.png"
```

## The other Tapir

This Tapir started as a fork of another
project: [Tapir for cooperative supermarkets](https://github.com/SuperCoopBerlin/tapir). They are now completely
separate but have kept the same name. Sorry for the confusion!
