"""tapir URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView

from tapir.wirgarten.views.default_redirect import wirgarten_redirect_view
from tapir.wirgarten.views.mailing import TapirMailView

tapir_mail_path = (
    settings.TAPIR_MAIL_PATH[1:]
    if settings.TAPIR_MAIL_PATH.startswith("/")
    else settings.TAPIR_MAIL_PATH
) + "/"

urlpatterns = [
    path("", wirgarten_redirect_view, name="index"),
    path("core/", include("tapir.core.urls")),
    path("coop/", include("tapir.coop.urls")),
    path("accounts/", include("tapir.accounts.urls")),
    path(
        "accounts/login/",
        RedirectView.as_view(url="/accounts/oidc/keycloak/login"),
        name="account_login",
    ),
    path("accounts/", include("allauth.urls")),
    path("log/", include("tapir.log.urls")),
    path("config/", include("tapir.configuration.urls")),
    path("tapir/", include("tapir.wirgarten.urls")),
    path(
        "mailing/",
        TapirMailView.as_view(),
        name="tapir_mail",
        kwargs={"TAPIR_MAIL_PATH": settings.TAPIR_MAIL_PATH},
    ),
    path(tapir_mail_path, include("tapir_mail.urls")),
    path("deliveries/", include("tapir.deliveries.urls")),
    path("generic_exports/", include("tapir.generic_exports.urls")),
    path("subscriptions/", include("tapir.subscriptions.urls")),
    path("pickup_locations/", include("tapir.pickup_locations.urls")),
    path("utils/", include("tapir.utils.urls")),
    path("waiting_list/", include("tapir.waiting_list.urls")),
    path("products/", include("tapir.products.urls")),
    path("payments/", include("tapir.payments.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.ENABLE_SILK_PROFILING:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
