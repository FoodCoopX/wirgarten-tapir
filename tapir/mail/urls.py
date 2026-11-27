from django.urls import include, path, re_path, reverse_lazy
from django.views.generic import RedirectView
from rest_framework import routers

from tapir.mail.views.email_templates import (
    EmailTemplateViewSet,
    PaginatedEmailTemplateViewSet,
)
from tapir.mail.views.email_configurations import (
    EmailConfigurationVersionViewSet,
    EmailConfigurationViewSet,
)
from tapir.mail.views.dispatches import (
    EmailConfigurationDispatchViewSet,
    EmailDispatchViewSet,
    TrackingView,
)
from tapir.mail.views.segments import (
    SegmentAndFilterViewSet,
    StaticSegmentRecipientViewSet,
    StaticSegmentViewSet,
)
from tapir.mail.views.triggers import (
    CreateMissingTriggerMailView,
    MissingTriggersView,
    TokensView,
    TransactionalTriggerTokenView,
    TriggerListView,
)
from tapir.mail.views.mail_categories import MailCategoryViewSet
from tapir.mail.views.external import (
    ConfirmRegistrationToMailCategoryView,
    ConfirmationMailSentView,
    RegisterToMailCategoryView,
)
from tapir.mail.views.ui import MailUiView

router = routers.SimpleRouter()
router.register("email_template", EmailTemplateViewSet, basename="email_template")
router.register(
    "email_template_paginated",
    PaginatedEmailTemplateViewSet,
    basename="email_template_paginated",
)
router.register("email_configuration", EmailConfigurationViewSet)
router.register("email_configuration_version", EmailConfigurationVersionViewSet)
router.register("email_configuration_dispatch", EmailConfigurationDispatchViewSet)
router.register("email_dispatch", EmailDispatchViewSet)
router.register("triggers", TriggerListView, basename="Triggers")
router.register(
    "trigger_tokens", TransactionalTriggerTokenView, basename="Trigger Tokens"
)
router.register("segment", SegmentAndFilterViewSet, basename="segment")
router.register("tokens", TokensView, basename="tokens")
router.register("tracking", TrackingView, basename="tracking")
router.register("static_segment", StaticSegmentViewSet)
router.register("static_segment_recipient", StaticSegmentRecipientViewSet)
router.register("mail_category", MailCategoryViewSet)


urlpatterns = [
    path("api/media_library/", include("tapir.mail.media_library.urls")),
    path("api/", include(router.urls)),  # REST API
    path(
        "external/registration/<str:category_id>",
        RegisterToMailCategoryView.as_view(),
        name="category_registration_external_form",
    ),
    path(
        "external/confirmation_mail_sent/<str:category_id>",
        ConfirmationMailSentView.as_view(),
        name="confirmation_mail_sent",
    ),
    path(
        "external/confirm/<uuid:secret>",
        ConfirmRegistrationToMailCategoryView.as_view(),
        name="user_confirms_registration",
    ),
    # Used to be a permanent management page reached through ExternalRecipient.secret_key.
    # Management now only goes through temporary signed links, so links in old mails
    # lead to the page where a new link can be requested.
    path(
        "external/manage/<uuid:recipient_secret>",
        RedirectView.as_view(
            url=reverse_lazy("core:subscription_management_link_request")
        ),
        name="external_recipient_manager",
    ),
    path("", MailUiView.as_view(), name="mail_ui"),
    re_path(
        r"^(?!api/).*$",
        MailUiView.as_view(),
    ),
    path(
        "api/missing_triggers",
        MissingTriggersView.as_view(),
        name="missing_triggers",
    ),
    path(
        "api/create_missing_trigger",
        CreateMissingTriggerMailView.as_view(),
        name="create_missing_trigger",
    ),
]
