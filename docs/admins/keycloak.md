# Keycloak setup

Tapir delegates login to Keycloak through `django-allauth`. The management command

```sh
python manage.py keycloak check
python manage.py keycloak sync
```

reconciles the Keycloak realm with the state Tapir expects. This page describes what the command
manages, which environment variables configure it, and how to connect Tapir to a new or existing
Keycloak server.

## What Tapir manages

`keycloak sync` creates missing settings and repairs drift. It never deletes roles, groups or clients.
Extra roles in the `superuser` group and extra role scope mappings are reported as warnings only.

### Realm settings

| Setting                        | Value   |
| ------------------------------ | ------- |
| `enabled`                      | `true`  |
| `registrationAllowed`          | `false` |
| `registrationEmailAsUsername`  | `true` (`KEYCLOAK_REGISTRATION_EMAIL_AS_USERNAME`) |
| `loginWithEmailAllowed`        | `true`  |
| `duplicateEmailsAllowed`       | `false` |
| `editUsernameAllowed`          | `false` (`KEYCLOAK_EDIT_USERNAME_ALLOWED`) |
| `resetPasswordAllowed`         | `true`  |
| `verifyEmail`                  | `true`  |

With `KEYCLOAK_USERNAME_SOURCE=customernumber`, set both username flags to `false`; `check` warns
otherwise. E-mail login keeps working because `loginWithEmailAllowed` stays `true`.

### Realm roles and the superuser group

Tapir creates the nine realm roles defined by `Permission.all()` in
`tapir/wirgarten/constants.py`:

```text
coop.view
coop.manage
accounts.view
accounts.manage
payments.view
payments.manage
products.view
products.manage
email.manage
```

It also creates the `superuser` group and assigns all nine roles to it. Tapir puts superusers into
that group when it creates their Keycloak user.

### Keycloak usernames

`KEYCLOAK_USERNAME_SOURCE` controls the username of **newly created** Keycloak users:

| Value            | Keycloak username |
| ---------------- | ----------------- |
| `email` (default) | The Tapir user's e-mail address; this is the previous behaviour. |
| `customernumber`  | `Member.member_no`; the Tapir member number. |

`KEYCLOAK_USERNAME_FORMAT` selects the representation of the customernumber:

| Value        | Example | Meaning |
| ------------ | ------- | ------- |
| `raw` (default) | `17` | The integer value without prefix or padding. |
| `formatted`  | `BT0017` | `MemberNumberService.format_member_number()` with the Tapir prefix and zero-padding. |

Django's `TapirUser.username` remains the e-mail address in both modes. Only the Keycloak username
changes. The adapter and duplicate-e-mail checks find Keycloak users by e-mail, so e-mail login and
e-mail changes keep working.

Members without a customernumber are not created in Keycloak when the source is `customernumber`.
The waiting-list confirmation, the bestell wizard and the member create modal assign a member number
before creating the Keycloak user. Resend-verification, e-mail change and `send_verify_emails`
return or log a clear error until a number exists. Non-Member accounts created by `create_admin`
keep the e-mail as Keycloak username because they have no `member_no`.

Existing Keycloak users are not migrated. Only users created after the setting is enabled use the
new username. To use customernumber usernames, configure:

```dotenv
KEYCLOAK_USERNAME_SOURCE=customernumber
KEYCLOAK_USERNAME_FORMAT=raw
KEYCLOAK_REGISTRATION_EMAIL_AS_USERNAME=0
KEYCLOAK_EDIT_USERNAME_ALLOWED=0
```

The sample declarative user profile in this repository has a `username` minimum length of 3 and a
required `customernumber` attribute. A short raw number such as `17` fails the minimum length; use
`formatted` or lower the minimum. The username change does not populate the profile's
`customernumber` attribute; populate it separately or remove that requirement from the profile.

### Clients and role mappings

| Client            | Type         | Service account | Standard flow | Direct grants | Secret variable                     |
| ----------------- | ------------ | --------------- | ------------- | ------------- | ----------------------------------- |
| `tapir-backend`   | confidential | yes             | yes           | no            | `KEYCLOAK_ADMIN_CLIENT_SECRET_KEY`   |
| `tapir-frontend`  | public       | no              | yes           | no            | none                                |
| `tapir-provisioner` | confidential | yes           | no            | no            | `KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY` |

All three clients have `fullScopeAllowed=false`. Redirect URIs and web origins are derived from
`SITE_URL` for the backend and frontend clients; the provisioner has none.

The service accounts and client scope mappings are managed as well:

| Client            | Role                                         |
| ----------------- | -------------------------------------------- |
| `tapir-backend`   | `realm-management/manage-users`              |
| `tapir-provisioner` | `realm-management/realm-admin`             |
| `tapir-frontend`  | none                                          |

Both the service-account role and the client's role scope mapping are required. With
`fullScopeAllowed=false`, a token only contains roles that are included in the client's role scope
mappings. The service-account role is what lets the client call the admin API; the scope mapping makes
the role available to the token.

### Admin API audience

Current Keycloak releases enforce an audience check on the Admin REST API (RFC 9700). A client's
access token only reaches the admin endpoints when it carries the `kc-admin-api` scope and the
realm's admin API URL in its `aud` claim. The built-in `kc-admin-api` client scope supplies both;
Keycloak's own `admin-cli` and `security-admin-console` clients get it automatically on upgrade,
custom clients do not.

`tapir-backend` and `tapir-provisioner` call the Admin API, so `check`/`sync` assign the
`kc-admin-api` default client scope to both. Without it Keycloak answers every admin call with
`401 {"error":"HTTP 401 Unauthorized"}` and Tapir fails on the first permission check. The service
account roles stay unchanged; the audience check is independent of them.

### What the command does not manage

Users, SMTP settings, themes, client scope definitions, optional protocol mappers, authentication
flows, identity providers and the user profile are not managed. Client scopes are only assigned, and
only the built-in `kc-admin-api` scope is assigned. Configure the rest in the Keycloak admin console.
A missing `smtpServer` is reported as a warning, not as an error.

Export the realm from the Keycloak admin console, or with `kc.sh export`, before the first `sync` if
you want a backup.

## Configuration

All settings are read through `django-environ` from the process environment or the `.env.local` file
in the repository root.

| Variable                             | Default                  | Purpose |
| ------------------------------------ | ------------------------ | ------- |
| `KEYCLOAK_ADMIN_SERVER_URL`          | `http://keycloak:8080`   | Base URL of the Keycloak server as reachable from Tapir. Used by `check`/`sync` and for OIDC discovery. |
| `KEYCLOAK_PUBLIC_URL`                | `http://localhost:8080`  | Browser-facing base URL. Used for the password-change redirect and the CSP `frame-src`. |
| `KEYCLOAK_REALM_NAME`                | `tapir`                  | Realm to manage. The realm must already exist. |
| `KEYCLOAK_CLIENT_ID`                 | `tapir-backend`          | Confidential backend client used for login and user management. |
| `KEYCLOAK_ADMIN_CLIENT_SECRET_KEY`   | `**********`             | Secret for the backend client. `sync` creates the client or repairs its secret. |
| `KEYCLOAK_FRONTEND_CLIENT_ID`        | `tapir-frontend`         | Public client used by the frontend. |
| `KEYCLOAK_PROVISIONER_CLIENT_ID`     | `tapir-provisioner`      | Client used by `manage.py keycloak`. Must exist before the first `sync`. |
| `KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY` | `**********`         | Secret for the provisioner client. Must match Keycloak before `sync`. |
| `KEYCLOAK_SKIP_VERIFICATION_EMAIL`   | `false`                  | Skip the verification email Tapir sends through Keycloak. |
| `KEYCLOAK_REGISTRATION_EMAIL_AS_USERNAME` | `true`              | Realm setting. Set to `0` when usernames are customernumbers. |
| `KEYCLOAK_EDIT_USERNAME_ALLOWED`     | `false`                  | Realm setting. Keep `0` when usernames are managed by Tapir. |
| `KEYCLOAK_VERIFY_EMAIL`              | `true`                   | Managed realm setting. Override when the realm uses a different e-mail verification policy. |
| `KEYCLOAK_SUPERUSER_GROUP_NAME`      | `superuser`              | Group that receives all Tapir realm roles and is assigned to superusers. |
| `KEYCLOAK_USERNAME_SOURCE`           | `email`                  | Keycloak username for new users: `email` or `customernumber`. |
| `KEYCLOAK_USERNAME_FORMAT`           | `raw`                    | Customernumber format: `raw` (`17`) or `formatted` (`BT0017`). |
| `SITE_URL`                           | `http://localhost:8000`  | Public URL of Tapir. Redirect URIs and web origins are derived from it. |
| `DEBUG`                              | `false`                  | Adds localhost redirect URIs and disables the local-default warnings. |

The four `KEYCLOAK_*` realm/group overrides are optional. For example:

```dotenv
KEYCLOAK_REGISTRATION_EMAIL_AS_USERNAME=0
KEYCLOAK_EDIT_USERNAME_ALLOWED=1
KEYCLOAK_VERIFY_EMAIL=0
KEYCLOAK_SUPERUSER_GROUP_NAME=tapir-admins
```

`KEYCLOAK_ADMIN_SERVER_URL` is the base URL only. It may include a path prefix such as
`https://auth.example.org/auth`, but it must not include `/realms/<realm>`. A trailing slash is
ignored.

`KEYCLOAK_ADMIN_SERVER_URL` must be reachable from the Tapir backend, because the OpenID Connect
discovery document and the admin API are fetched server-side. `KEYCLOAK_PUBLIC_URL` is what browsers
see. In a simple deployment both are the same; behind split DNS or a reverse proxy they can differ.
Set both explicitly, and make sure `SITE_URL` is the canonical browser URL.

### TLS and private CAs

Certificate verification is always on. If Keycloak uses a certificate from a private CA, add that CA
to the container trust store or point `REQUESTS_CA_BUNDLE` at the CA bundle. There is deliberately no
insecure verification toggle.

## Bootstrapping a new Keycloak server

Keycloak 26.8.2 or newer is required. The only things Tapir needs before the first `sync` are a
realm and a provisioner client with `realm-management/realm-admin` and the `kc-admin-api` default
client scope. Everything else is created by the command.

### 1. Create the realm

Create a dedicated realm (for example `tapir`) or choose an existing one and set
`KEYCLOAK_REALM_NAME` accordingly. `sync` cannot create a realm.

### 2. Create the provisioner client

In the Keycloak admin console, create a client in that realm:

- Client ID: `tapir-provisioner` (or the value of `KEYCLOAK_PROVISIONER_CLIENT_ID`)
- Client authentication: on (confidential)
- Service accounts roles: on
- Standard flow: off
- Direct access grants: off
- Implicit flow: off
- Valid redirect URIs and web origins: empty
- Full scope allowed: off
- Client scopes: add the built-in `kc-admin-api` scope as a **Default** client scope
- Client secret: generate one and copy it

`sync` cannot add the scope to its own provisioner client, because it is not authenticated yet; add
it by hand here. The local bootstrap file `docker/keycloak/import/tapir-realm.json` is a minimal
reference for these settings and already contains the scope.

### 3. Give the provisioner client realm-admin

The provisioner needs `realm-management/realm-admin` in two places:

1. **Service account role:** open the client, go to *Service accounts roles*, select
   `realm-management`, and assign `realm-admin`.
2. **Client scope mapping:** open the client, go to *Client scopes*, open the `realm-management`
   scope, and assign `realm-admin` there as well.

With `fullScopeAllowed=false`, missing either mapping leaves the command unable to read or change the
realm. `sync` verifies both and reports what is missing.

### 4. Configure Tapir

Create `.env.local` from `.env.local.disabled` for the local Docker stack, or set the variables
directly in the environment of the `web` and Celery containers in production. A production example:

```dotenv
DEBUG=0
SITE_URL=https://tapir.example.org
KEYCLOAK_ADMIN_SERVER_URL=https://auth.example.org
KEYCLOAK_PUBLIC_URL=https://auth.example.org
KEYCLOAK_REALM_NAME=tapir
KEYCLOAK_CLIENT_ID=tapir-backend
KEYCLOAK_ADMIN_CLIENT_SECRET_KEY=<generated-secret>
KEYCLOAK_FRONTEND_CLIENT_ID=tapir-frontend
KEYCLOAK_PROVISIONER_CLIENT_ID=tapir-provisioner
KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY=<secret-from-keycloak>
```

For a one-off run against a different server, pass the values to `docker compose exec`:

```sh
docker compose exec \
  -e KEYCLOAK_ADMIN_SERVER_URL=https://auth.example.org \
  -e KEYCLOAK_PUBLIC_URL=https://auth.example.org \
  -e KEYCLOAK_REALM_NAME=tapir \
  -e KEYCLOAK_PROVISIONER_CLIENT_ID=tapir-provisioner \
  -e KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY='<secret-from-keycloak>' \
  -e KEYCLOAK_CLIENT_ID=tapir-backend \
  -e KEYCLOAK_ADMIN_CLIENT_SECRET_KEY='<generated-secret>' \
  -e SITE_URL=https://tapir.example.org \
  web poetry run python manage.py keycloak check
```

The same command can run on a host installation with `poetry run python manage.py keycloak check`.

### 5. Check, then sync

```sh
docker compose exec web poetry run python manage.py keycloak check
docker compose exec web poetry run python manage.py keycloak sync
```

`check` is read-only and exits `1` when the realm drifts. It prints a `Checks:` block that lists
every realm setting, role, group, client, scope mapping, service account, runtime secret and SMTP
check with its status. `sync` creates missing settings and then verifies the result; it exits `0`
when the realm is converged and `2` on a configuration or setup error. Both commands accept
`--json` for automation. The JSON contains a `config` block with the effective server URL, public
URL, realm, site URL and client IDs, plus a `checks` array, but never secrets.

`sync` is idempotent. Running it twice reports no changes the second time.

### Rotating secrets

- **Backend secret:** change `KEYCLOAK_ADMIN_CLIENT_SECRET_KEY` and run `sync`. The command updates
  the `tapir-backend` client to the configured secret.
- **Provisioner secret:** change the secret in Keycloak and in
  `KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY` together. `sync` cannot repair this secret because it needs
  a working secret to authenticate in the first place.

## Local development stack

The `docker-compose.yml` stack imports `docker/keycloak/import/tapir-realm.json` into a fresh
Keycloak database. That import intentionally contains only the realm, the `tapir-provisioner` client
with its `realm-management/realm-admin` mappings and the `kc-admin-api` default client scope.
`tapir-backend`, `tapir-frontend`, the Tapir roles, the `superuser` group and the `kc-admin-api` scope
on the backend client are created by `make keycloak-sync`.

Keycloak reads the import only when its database is empty. After changing the import, recreate the
container and its volume:

```sh
docker compose down -v
docker compose up -d --wait
```

The local stack uses different URLs on purpose: Tapir reaches Keycloak at `http://keycloak:8080`
inside the Docker network, while browsers use `http://localhost:8080`. If the host ports are remapped
in `docker-compose.override.yml`, set `KEYCLOAK_PUBLIC_URL` (and Keycloak's `KC_HOSTNAME`) to the
remapped public URL.

## Troubleshooting

| Message | Fix |
| ------- | --- |
| `Keycloak is not reachable at KEYCLOAK_ADMIN_SERVER_URL=...` | Check the URL, DNS and network access from the Tapir container, and the TLS trust chain. |
| `The Keycloak provisioning client could not authenticate ...` | Check `KEYCLOAK_PROVISIONER_CLIENT_ID`, its secret and `KEYCLOAK_REALM_NAME`. Also check that the provisioner client has the `kc-admin-api` default client scope. |
| `The Keycloak realm does not exist.` | Create the realm or correct `KEYCLOAK_REALM_NAME`. |
| `The Keycloak provisioning client lacks realm-management/realm-admin.` | Assign `realm-admin` to the service account and add the client scope mapping. |
| `client tapir-backend cannot authenticate with the configured secret` | `sync` repairs it. Also check `KEYCLOAK_ADMIN_CLIENT_SECRET_KEY` and `KEYCLOAK_CLIENT_ID`. |
| `client tapir-backend cannot call the Admin API: ... kc-admin-api ...` | The server does not offer the built-in scope or the assignment failed. Upgrade Keycloak if the scope is missing, otherwise assign `kc-admin-api` as a default client scope. |
| `The Keycloak server does not provide the built-in client scope 'kc-admin-api'` | Upgrade Keycloak; older releases do not ship the scope. |
| `KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY is still the placeholder value` | Set a real secret in Keycloak and in the environment. |
| `Invalid redirect URI` in the browser | Make `SITE_URL` match the canonical browser URL, and proxy other hostnames to that URL. |
| `SSL: CERTIFICATE_VERIFY_FAILED` | Add the private CA to the trust store or set `REQUESTS_CA_BUNDLE`. |
| `Keycloak username is still the e-mail` | Existing users are not migrated; only new users use `KEYCLOAK_USERNAME_SOURCE`. |
| `Keycloak user is not created: no member number` | Assign a member number first; `manage.py backfill_member_numbers` can help. |
| `Invalid username` / Keycloak username policy | Use `KEYCLOAK_USERNAME_FORMAT=formatted` or lower the profile's username minimum length. |
| `Admin cannot log in` | `create_admin` creates a non-Member account and keeps the e-mail username; check `loginWithEmailAllowed`. |
| `User profile requires customernumber` | The username change does not write that profile attribute; populate it separately or adjust the profile. |
