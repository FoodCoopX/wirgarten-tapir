# Tapir Member & Shift Management System

Tapir is a member and shift management system to be used by [SuperCoop Berlin](https://supercoop.de).

Tapir [has a trunk](https://www.youtube.com/watch?v=JgwBecM_E6Q), but not quite such a beautiful one as
[Mme. l'élephan](https://github.com/elefan-grenoble/gestion-compte). Tapir is badass,
[but not quite as badass as the other
animals](https://www.youtube.com/watch?v=zJm6nDnR2SE). Let's teach Tapir some tricks!

## Getting started

    docker-compose up

This starts a container with an LDAP server and automatically loads the test data into the LDAP.

Next, set up the test database and load test data

    # Create tables
    docker-compose exec web poetry run python manage.py migrate
    
    # Import configuration parameter definitions
    docker-compose exec web poetry run python manage.py parameter_definitions

    # Load admin (password: admin) account
    docker-compose exec web poetry run python manage.py loaddata admin_account
    
    # Load lots of test users & shifts
    docker-compose exec web poetry run python manage.py populate --reset_all

## Developing

Leon uses [PyCharm](https://www.jetbrains.com/pycharm/) for development.
It has a Poetry plugin that easily allows setting up a local (not in the container) Python env and run the tests in
there. Make sure to enable Django support in the project settings so that things like the template language and the
test runner are automagically selected (note that right now this doesn't really work anymore as the tests must be run
inside docker to have an LDAP server. But PyCharm is still pretty cool)

### Pre-commit hooks

First thing after checkout, run the following to install auto-formatting using [black](https://github.com/psf/black/)
before every commit:

    poetry install && pre-commit install

### Django Shell

    docker-compose exec web poetry run python manage.py shell_plus

### LDAP

For reading or modifying the LDAP, Apache Directory Studio is pretty handy.

### Running tests

For running the test should have a clean openldap container with the test data.

    docker-compose up -d openldap

Then, run the tests.

    docker-compose run web poetry run pytest

To regenerate the test data fixtures:

    docker-compose up --force-recreate
    docker compose exec web poetry run python manage.py migrate
    docker compose exec web poetry run python manage.py populate --reset_all
    docker-compose exec web poetry run python manage.py dumpdata accounts.TapirUser shifts.ShiftTemplateGroup shifts.ShiftTemplate shifts.ShiftSlotTemplate shifts.ShiftAttendanceTemplate coop.ShareOwner coop.ShareOwnership > tapir/utils/fixtures/test_data.json

#### Selenium Tests

You can connect to the selenium container via VNC for debugging purpose. The address is localhost:5900, password :
secret

### Vocabulary

A few definitions to help newcomers understand the model classes.

| Class | Definition |
| ----- | ---------- |
| DraftUser | Also called Applicant. Represents a person that expressed interest in joining but that hasn't completed the subscription process yet. |
| ShareOwner | Represents a person or a company that is either currently owning at least a share, or has owned shares in the past. Therefore they are or have been a member of the cooperative. They may not be active, for example investing members or someone who sold their shares. |
| TapirUser | Represents a person with a user account. Accounts are linked between Tapir and the Wiki for example. Gets created when the member becomes active (part of the shift system etc.), but can become inactive. |  
| Shift | Represents a shift with a specific date and time (for example, 18/06/21 10:00 to 13:00). Can be a one-time activity or an instance of a ShiftTemplate |
| ShiftTemplate | Represents the recurring aspect of a shift in the ABCD system. For example helping at the shop on Tuesday, 10:00 to 13:00, on Week C. It has a weekday (Tuesday) and a time, but no date (18/06/21) | 

### Translations

To generate the translation files, first use "makemessages" and specify the language you want to generate:

    docker-compose exec -w /app/tapir web poetry run python ../manage.py makemessages -l de

Update tapir/translations/locale/de/LC_MESSAGES/django.po with your translations.

For the changes to take effect, restart the Docker container. This will run `manage.py compilemessages` automatically.

### Configuration Parameters

We have introduced a generic way to configure the application with key-value pairs.

Currently the datatypes `string`, `float`, `integer` and `boolean` are supported.

You can retrieve parameter values in Python in the following way:

``` python
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameters import Parameter

get_parameter_value(Parameter.SITE_NAME) # --> WirGarten Lüneburg eG
```

There is also a template tag available for reading parameter values:

``` html
{% load configuration %}

{{ 'wirgarten.coop.site_name' | parameter }}
```

#### How to define parameters

Best practice for those parameters is to create a `<app>/parameters.py` file per app.

It contains constants for parameter names and categories (so it is easy to find usages in the IDE), and the actual
parameter definitions (with a description, initial value, datatype).

When running the `manage.py parameter_definitions` command, all instances of `TapirParameterDefinitionImporter` will be
found and imported through the `import_definitions()` function.

The key should have the following format: `<app>.<category>.<name>`

Example (see [wirgarten/parameters.py](tapir/wirgarten/parameters.py) for the full example):

``` python
# Constants for parameter categories
class ParameterCategory:
    SITE = "Standort"
    # [...]

# Constants for parameter names
class Parameter:
    SITE_NAME = "wirgarten.site.name"
    SITE_EMAIL = "wirgarten.site.email"
    # [...]

# Parameter definitions (for automatic import)
class ParameterDefinitions(TapirParameterDefinitionImporter):
    def import_definitions(self):
        
        parameter_definition(
            key=Parameter.SITE_NAME,
            datatype=TapirParameterDatatype.STRING,
            initial_value="WirGarten Lüneburg eG",
            description="Der Name des WirGarten Standorts. Beispiel: 'WirGarten Lüneburg eG'",
            category=ParameterCategory.SITE,
        )

        parameter_definition(
            key=Parameter.SITE_EMAIL,
            datatype=TapirParameterDatatype.STRING,
            initial_value="lueneburg@wirgarten.com",
            description="Die Kontakt Email-Adresse des WirGarten Standorts. Beispiel: 'lueneburg@wirgarten.com'",
            category=ParameterCategory.SITE,
        )
        
        # [...]
```

#### UI

A simple UI for editing parameter values can be found under "Administration -> Configuration" (permission: `coop.admin`)
.
The parameters are grouped by the category.

![image](https://user-images.githubusercontent.com/12133154/190416712-4f3b3a8f-3d49-4a51-bd87-50cff131985d.png)

### Welcome Desk Authentication

All users logging in at the welcome desk are granted more permissions. This magic uses SSL client certificates. The web
server requests and checks the client certificate and subsequently sets a header that is then checked
by `tapir.accounts.middleware.ClientPermsMiddleware`.

Here are some quick one-liners for key management:

```
# Create a new CA - only the first time. The public key in the cer file is distributed to the webserver, the private key is to be kept secret!
openssl req -newkey rsa:4096 -keyform PEM -keyout members.supercoop.de.key -x509 -days 3650 -outform PEM -nodes -out members.supercoop.de.cer -subj="/C=DE/O=SuperCoop Berlin eG/CN=members.supercoop.de"


# Create a new key
export CERT_HOSTNAME=welcome-desk-1
openssl genrsa -out $CERT_HOSTNAME.members.supercoop.de.key 4096
openssl req -new -key $CERT_HOSTNAME.members.supercoop.de.key -out $CERT_HOSTNAME.members.supercoop.de.req -sha256 -subj "/C=DE/O=SuperCoop Berlin eG/CN=welcome-desk.members.supercoop.de"
openssl x509 -req -in $CERT_HOSTNAME.members.supercoop.de.req -CA members.supercoop.de.cer -CAkey members.supercoop.de.key -CAcreateserial -extensions client -days 3650 -outform PEM -out $CERT_HOSTNAME.members.supercoop.de.cer -sha256

# Create a PKCS12 bundle consumable by the browser
openssl pkcs12 -export -inkey $CERT_HOSTNAME.members.supercoop.de.key -in $CERT_HOSTNAME.members.supercoop.de.cer -out $CERT_HOSTNAME.members.supercoop.de.p12

# Remove CSR and bundled private/public key files
rm $CERT_HOSTNAME.members.supercoop.de.key $CERT_HOSTNAME.members.supercoop.de.cer $CERT_HOSTNAME.members.supercoop.de.req
```

