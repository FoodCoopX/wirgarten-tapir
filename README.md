# Tapir

[![Python code test coverage](https://sonarcloud.io/api/project_badges/measure?project=FoodCoopX_wirgarten-tapir&metric=coverage)](https://sonarcloud.io/summary/overall?id=FoodCoopX_wirgarten-tapir&branch=master)

Tapir is a management system for community supported agriculture. 
It is currently used productively by several organizations, including [WirGarten Lüneburg eG](https://lueneburg.wirgarten.com/), [Möllers Morgen](https://www.moellersmorgen.de), [Gemüsekollektiv Hebenshausen e.V.](https://gemuesekollektiv.org), and more.

Its features include:
- Member & membership management including cooperative shares
- Contract management: yearly commitment, weekly deliveries, solidarity contributions, renewal...
- Communication with the members with customizable automated mails
- Delivery locations and capacity management
- And more

The development is lead mainly by [Théo](https://seriousdino.org/) for [FoodCoopX](https://foodcoopx.de/).

The backend code is written with Python and Django, the frontend code is a mix of Django templates and React.

Don't hesitate to contact us if you are interested in using or contributing to Tapir.

## Getting started

Use docker to quickly get a development server running on your machine. Run the following commands:
```sh
docker compose up -d
# Create tables
docker compose exec web poetry run python manage.py migrate
# Define the configuration parameters
docker compose exec web poetry run python manage.py parameter_definitions    
# Generate test data
docker compose exec web poetry run python manage.py populate --reset_all
```

You should now have a local instance accessible at http://localhost:8000/. 
You can log in as admin with username `roberto.cortes@example.com` and password `roberto.cortes`.

You can log in as any user using the same pattern: `[name]@example.come` as username and `[name]` as password 


## Contributing & GitHub issues
You are very welcome to try Tapir locally with the "Getting started" instructions above and do your own thing. 
The current documentation being basically just this README, you may need extra guidance to get started. Don't hesitate to contact us so that we can give you an introduction.

If you're looking for something to work on, filter the issues using the [Ready to be worked on](https://github.com/FoodCoopX/wirgarten-tapir/issues?q=state%3Aopen%20label%3A%22Ready%20to%20be%20worked%20on%22) label.
Those issues should have a good enough description to get you started. Don't hesitate to ask more questions on the issue directly if needed. 
If you just, also assign either Theo (for technical questions) or Marcus (for requirements questions) to the issue, so that they know they have to react. They'll assign the issue back to you when the answer is there.

You're of course free to check the other issues and ask questions about them, but we aware that they may not make sense if you're not involved in the daily Tapir life.
We don't have an internal tool to track tasks yet, so we use the GitHub issues as our todo-list. Hopefully the labels will be enough to let you sort through the mess. 

## Tests
Tests are run with `pytest`:
```shell
docker compose exec web poetry run pytest --reuse-db -n auto
```
If you run into troubles while running the tests, try running them without `--reuse-db -n auto`.

You can run unit tests outside the Docker container with just by simple running `pytest`, 
assuming you have the poetry environment installed and activated. That should be a bit faster. 
Integration tests must be run from inside Docker.

### Keycloak during tests
User authentication is handled by keycloak through `django-allauth`. 
During integration tests, this connection is mocked via `tapir.wirgarten.tests.test_utils.mock_keycloak`, called in `TapirIntegrationTest`.
The mocking happen during `setUp` and `setUpTestData` happens before `setUp`, that means we can't create users inside `setUpTestData`. 

## Formatting
Python files are formatted with [Black](https://github.com/psf/black).

JavaScript and React files are formatted with [Prettier](https://prettier.io/).

Django template files are formatted with [DjHTML](https://github.com/rtts/djhtml)

Install the pre-commit hooks to make sure that the files you commit are properly formatted: `poetry run pre-commit install`.
It should be possible to configure your IDE of choice to run the formatting automatically on save, at least for Black and Prettier. Look in their respective documentation.

## Frontend API clients
API Requests made from the React frontend use API clients. Here are the steps to get updated API clients:
- Annotate your API view with [Spectacular](https://github.com/tfranzel/drf-spectacular) (search for `@extend_schema(` for examples)
- Generate the API schema file with `python ./manage.py spectacular --file schema.yml`
- Generate the TypeScript API clients using [OpenAPI Generator](https://openapi-generator.tech/) with `./scripts/generate_api_clients.sh`

There are help scripts in the `/scripts` folder. You can do a full update with the following command:
```bash
docker compose exec web ./scripts/generate_api_schema.sh && docker compose exec vite ./scripts/generate_api_clients.sh
```

## Style and conventions

### Models
Models should inherit from `tapir.core.models.TapirModel`:
 - It uses nanoid instead of integer IDs, that makes sure we never use an ID from a model when getting another model, for example in tests.
 - It has `created_at` and `updated_at` fields that help unterstand the state of production databases.

As much as possible, model classes should contain only their own fields. Helper methods are OK if they only reference the fields of the given object.

### Cache
Many functions, especially service functions, take a `cache` parameter which is a normal python dictionary. 
The goal of this cache is to avoid redundant database requests within one http request: in most of our views, DB requests are the most time-consuming part.
The cache dictionary should be created at the origin point: for example in the view's `__init__` function or the first lines or the command. 
Since this cache only lives for the duration of the request, in most cases it is not necessary to invalidate it. If you do need to invalidate, look at `tapir.utils.services.tapir_cache_manager.TapirCacheManager`
Some functions have the cache parameter optional. This is only because they are called in legacy code, all new functions should have the cache parameter required if possible.
For examples, see usages of `tapir.utils.services.tapir_cache.TapirCache`.

### Service classes
Most of the business logic code should be in service classes. You can find examples in tapir/*/services/.

### Commits
Use [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) for your commit messages. 
When applicable, add the ID of the related GitHub issue in the commit message.

### Legacy code
Everything that is under tapir/wirgarten should be considered legacy code. It doesn't respect the conventions above. 
If you need to change anything in there, consider rewriting the part that you are changing and moving it to one of the other apps.

## Class diagram

[![models.png](models.png)](https://raw.githubusercontent.com/FoodCoopX/wirgarten-tapir/master/models.png)

If this graph is outdated, you can re-generate it with:

```shell
docker compose exec web sh -c "apt update && apt install -y graphviz graphviz-dev && poetry run pip install pygraphviz && poetry run python manage.py graph_models -a -g -o models.png"
```

## The other Tapir
This Tapir started as a fork of another project: [Tapir for cooperative supermarkets](https://github.com/SuperCoopBerlin/tapir).
They are now completely separate but have kept the same name. Sorry for the confusion!
