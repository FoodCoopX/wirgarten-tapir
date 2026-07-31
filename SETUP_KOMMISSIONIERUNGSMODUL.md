This branch contains a prototype for the integration of [Jasmin](https://github.com/birgit-seyr/jasmin) in Tapir. Those
changes are not meant to be final, instead they serve as a proof-of-concept that Jasmin can be integrated.

The commit a052ba3c62679c0247b9efe4df0945668836092c from Jasmin was used, I haven't tested the latest changes.

Here is an explanation of the process:

## On the Jasmin-Repo

#### Replace user model imports

- Replaced all usages of `JasminUser` with `get_user_model()`.
    - Typically this looks like removing a
      `from ..models import JasminUser` line and adding

```python 
from django.contrib.auth import authenticate, get_user_model

JasminUser = get_user_model()
```

- For model fields (ForeignKey, OneToOneField...), AUTH_USER_MODEL should be used instead of JasminUser. It looks like
  this:

```python
from django.conf import settings

example_field = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    ...
)
```

- This doesn't seem to require migrations on the Jasmin repo

#### Label the accounts app

in jasmin-core/django-core/apps/accounts/apps.py, add `label = "picking_module_accounts"`, otherwise this account app
will conflict with Tapir's accounts app.

#### Update pyproject.toml

- I set the set project's name to "picking-module" so that it is recognizable in the tapir configuration, but now that
  the project has been renamed to Jasmin I think that is not necessary anymore.
- set `package-mode = true`
- Add the following lines to `[tool.poetry]`:

```
  packages = [{include = "apps"}, {include = "core"}]
  include = [
      {path = "apps/static", format = ["sdist", "wheel"]},
  ]
```

- update packages django to version 6+ and redis to 8+

#### Update the frontend config

##### Configure the API clients:

In jasmin-core/react-core/src/shared/services/api.ts, apply the following changes so that the base URL is set. This is
because the base url is different on the standalone version (BASE_URL/...) from the integrated version
(BASE_URL/pickin_module/...)

```
 function isSuperAdminHost(): boolean {
-  return isSuperAdminHostname(window.location.hostname);
+  return isSuperAdminHostname(globalThis.location.hostname);
 }
 
+let baseUrl;
+if (window.parent && window.parent._env_ && window.parent._env_["COMMISSIONING_API_BASE_URL"]) {
+  baseUrl = window.parent._env_["COMMISSIONING_API_BASE_URL"]
+} else if (window._env_ && window._env_["COMMISSIONING_API_BASE_URL"]) {
+  baseUrl = window._env_["COMMISSIONING_API_BASE_URL"]
+} else {
+  baseUrl = API_URL
+}
+
+function getCookie(name: string) {
+  let cookieValue = null;
+  if (document.cookie && document.cookie !== '') {
+    const cookies = document.cookie.split(';');
+    for (let i = 0; i < cookies.length; i++) {
+      const cookie = cookies[i].trim();
+      // Does this cookie string begin with the name we want?
+      if (cookie.substring(0, name.length + 1) === (name + '=')) {
+        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
+        break;
+      }
+    }
+  }
+  return cookieValue;
+}
+const csrftoken = getCookie('csrftoken');
+
 const axiosInstance = axios.create({
-  baseURL: API_URL,
+  baseURL: baseUrl,
   // CRITICAL: send the HttpOnly refresh cookie on every API call. Without
   // this the cookie is dropped and silent refresh fails.
   withCredentials: true,
-  headers: { "Content-Type": "application/json" },
+  headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
 });
```

In jasmin-core/react-core/orval.config.ts under `output`, add:
`baseUrl: {runtime: "window._env_.COMMISSIONING_API_BASE_URL"},`

##### Update the fronted build config so that the files can be found by Tapir

In `vite.config.js` and `vite.config.production.js`, under build/rollupOptions/output, add or update the following
entries:

```
        chunkFileNames: 'static/assets/js/[name]-[hash].js',
        entryFileNames: 'static/assets/js/[name]-[hash].js',
        assetFileNames: 'static/assets/[ext]/[name]-[hash].[ext]'
```

#### Build the python package

Once all those changes are applied, Jasmin is ready to be built as a python package. I used the following script, ran
from the root of the Jasmin repo:

```sh
#!/bin/sh
set -e
make generate-frontend-api
rm -rf /home/theo/PycharmProjects/jasmin/jasmin-core/react-core/dist
cd jasmin-core/react-core
npm run build:dev
cd ../..
make poetry-build
```

The `poetry-build` target must be added to the Makefile.

```Makefile
poetry-build:
	mkdir -p $(DJANGO_DIR)/apps/static/picking-dist
	cp -r $(REACT_DIR)/dist $(DJANGO_DIR)/apps/static/picking-dist
	cd $(DJANGO_DIR) && poetry build
```

If everything works, a wheel file will be created: jasmin-core/django-core/dist/picking_module-[VERSION_NUMBER]
-py3-none-any.whl

## On the Tapir repo

Changes applied to the Tapir repo can be seen in the pull request
(https://github.com/FoodCoopX/wirgarten-tapir/pull/1204/changes).

#### Install the Jasmin package

The file built above can be added as a dependency, add the following to pyproject.toml:
`picking-module = { file = "/home/theo/PycharmProjects/jasmin/jasmin-core/django-core/dist/picking_module-0.1.3-py3-none-any.whl" }`
then run `poetry lock && poetry install`

#### Handle user roles

See changes to KeycloakUser in tapir/accounts/models.py. Tapir adds an "admin" role, it is one of the roles expected by
Jasmin. We would need to do a proper mapping from Tapir's groups, coming from keycloak, to Jasmin's roles.

#### Bypass Jasmin's login

See changes in tapir/accounts/views.py When Tapir's users access Jasmin, they are already logged in, but Jasmin doesn't
know it yet. The new views will ignore the login request coming from Jasmin and use the session from Tapir. Better would
be to skip Jasmin's login page entirely, but this is enough for testing.

#### Setup the iframe

The js code in tapir/core/templates/core/picking_iframe.html tries to have the browser page follow the URL of the
iframe. It doesn't work yet (you can't use previous/next)

#### Update the django settings

A few apps must be added to INSTALLED_APPS, more parameters must be defined. The current version mimics the parameters
from Jasmin as much as possible. We should audit those changes to make sure we're not creating vulnerabilities.

The URLs from Jasmin must be included, see tapir/urls.py . This is where we apply prefixes to all URLs from Jasmin and
the reason why we need the frontend config on the Jasmin repo.

#### Bypass django-tenants

Jasmin uses django-tenants to handle several tenants in one django instance. Tapir has one instance per tenant. We can
bypass django-tenant creating a single tenant and domain, see the changes in
tapir/utils/services/test_data_generation/data_generator.py
