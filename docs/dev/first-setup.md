# Local instance without test data

This guide prepares a new, empty Tapir instance for local evaluation or for entering real
membership data. The Docker Compose setup is a development setup (debug mode, Django's
runserver, and Mailpit); it is not suitable for production.

## Start the instance

Start the services and initialise the database:

```sh
make up
TAPIR_ADMIN_EMAIL=me@example.org TAPIR_ADMIN_PASSWORD=secret make init
```

`make init` runs the migrations, creates the parameter definitions, and creates the admin
account. The optional variables are `TAPIR_ADMIN_FIRST_NAME` (default `Admin`),
`TAPIR_ADMIN_LAST_NAME` (default `Tapir`), `TAPIR_ADMIN_EMAIL` (default
`admin@example.com`), and `TAPIR_ADMIN_PASSWORD` (default `admin`). They can also be
passed as arguments to `make init`, for example `make init TAPIR_ADMIN_EMAIL=me@example.org`.
`make init` can be run again safely: if an account with that email already exists, the
admin creation is skipped and its password is not changed.

Open <http://localhost:8000> and log in with the email and password you configured.

!!! warning
    Do not create `.env.local` in the Docker setup. The repository is mounted in the
    container, and Django reads that file there too; it would override the Docker hostnames.
    For a non-Docker local setup, put the variables in `.env.local` as described in the
    README's [Django outside of Docker](https://github.com/FoodCoopX/wirgarten-tapir#django-outside-of-docker)
    section.

## Persisting and resetting data

PostgreSQL and Keycloak data are stored in the `tapir-db` and `keycloak-data` Docker
volumes. Data therefore survives `make down` and `make up`. Keep the Tapir admin and
Keycloak accounts together: to wipe an instance completely, remove both volumes at once:

```sh
docker compose down -v
```

Do not remove only one of these volumes. `make populate` and `make reset` replace the
instance with test data; never run them on an instance containing real data.

The local development setup sends mail to Mailpit. View captured mail at
<http://localhost:8025>; the Keycloak development console is at
<http://localhost:8080> (admin/admin).

## Configure the instance

After logging in, use the administration links in this order. The German labels below are
the labels shown in Tapir, followed by an English explanation.

1. **Konfiguration** (`/config/parameters`) — set the organisation, site, email,
   payment, and other parameters required by your organisation.
2. **Vertragsperiode & Produkte** (`/tapir/product`) — add a **Vertragsperiode**
   (growing/contract period), then configure its **Produkttypen**, **Produkte**, prices,
   and capacities. The add-period action uses `/tapir/product/periodadd`.
3. **Abholorte** (`/tapir/admin/pickuplocations`) — create the pickup locations and
   configure their delivery days and capacities.
4. **Datenübernahme** (`/utils/data_import`) — import members and their related data,
   as described below.

These pages are also available from the **Administration** group in the sidebar. Product
and pickup-location management use the legacy `/tapir/` pages; the `/products/` and
`/pickup_locations/` routes are API endpoints rather than setup pages.

## Import existing data

Open **Datenübernahme** (`/utils/data_import`). Upload an Excel (`.xlsx`) or CSV file.
You can download a template from the page (the repository also contains a
[sample workbook](../admins/member_lists/tapir_import_sample_01.xlsx)). The web workflow is:

1. Upload the file and select the import types.
2. Map source columns to Tapir fields.
3. Review the dry run and select the rows to import.
4. Apply the selected valid rows.
5. After all data is present, send the activation mails.

Import in this order: **Mitglieder** (members), **Genossenschaftsanteile** (cooperative
shares), then **Verträge** (subscriptions). Subscriptions require the growing period,
products, and pickup locations to exist first. For a detailed member-list guide, see
[Adding new members](../admins/member_lists/adding_new_members.md).

The page validates rows before applying them and rolls back an unexpected failure while
applying selected rows. Activation mails are sent only when you choose **Aktivierungsmails
verschicken**; locally they arrive in Mailpit. If an imported member has the admin's email,
the existing admin account is reused rather than creating a second account.

### Command-line import

For automation, run the management command through the web container. The file must be
inside the repository (mounted at `/app`):

```sh
make manage ARGS="import-data --type members --file <path> --dry-run"
```

The command also supports `--type shares` and `--type subscriptions`. Use `--update yes`
to update existing records; see `python manage.py import-data --help` for all options.
