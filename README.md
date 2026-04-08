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

It is developed by [Théo](https://seriousdino.org/) for [FoodCoopX](https://foodcoopx.de/).

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

Javascript and React files are formatted with [Prettier](https://prettier.io/).

Django template files are formatted with [djLint](https://djlint.com/)

## Frontend API clients
API Requests made from the React frontend use API clients. Here are the steps to get updated API clients:
- Annotate your API view with [Spectacular](https://github.com/tfranzel/drf-spectacular) (search for `@extend_schema(` for examples)
- Generate the API schema file with `python ./manage.py spectacular --file schema.yml`
- Generate the TypeScript API clients using [OpenAPI Generator](https://openapi-generator.tech/) with `./scripts/generate_api_clients.sh`

There are help scripts in the `/scripts` folder. You can do a full update with the following command:
```bash
docker compose exec web ./scripts/generate_api_schema.sh && docker compose exec vite ./scripts/generate_api_clients.sh
```

## Legacy code
Everything that is under tapir/wirgarten should be considered legacy code. If you need to change anything in there, 
consider rewriting the part that you are changing and moving it to one of the other apps.

## Class diagram

[![models.png](models.png)](https://raw.githubusercontent.com/FoodCoopX/wirgarten-tapir/master/models.png)

If this graph is outdated, you can re-generate it with:

```shell
docker compose exec web sh -c "apt update && apt install -y graphviz graphviz-dev && poetry run pip install pygraphviz && poetry run python manage.py graph_models -a -g -o models.png"
```

## The other Tapir
This Tapir started as a fork of another project: [Tapir for cooperative supermarkets](https://github.com/SuperCoopBerlin/tapir).
They are now completely separate but have kept the same name. Sorry for the confusion!
