from django.urls import include, path, re_path
from rest_framework import routers

from tapir.mail import views
from tapir.mail.views import (
    RegisterToMailCategoryView,
    ConfirmationMailSentView,
    ConfirmRegistrationToMailCategoryView,
    ExternalRecipientManagementView,
    MailUiView,
)

router = routers.SimpleRouter()
router.register("email_template", views.EmailTemplateViewSet, basename="email_template")
router.register(
    "email_template_paginated",
    views.PaginatedEmailTemplateViewSet,
    basename="email_template_paginated",
)
router.register("email_configuration", views.EmailConfigurationViewSet)
router.register("email_configuration_version", views.EmailConfigurationVersionViewSet)
router.register("email_configuration_dispatch", views.EmailConfigurationDispatchViewSet)
router.register("email_dispatch", views.EmailDispatchViewSet)
router.register("triggers", views.TriggerListView, basename="Triggers")
router.register(
    "trigger_tokens", views.TransactionalTriggerTokenView, basename="Trigger Tokens"
)
router.register("segment", views.SegmentAndFilterViewSet, basename="segment")
router.register("tokens", views.TokensView, basename="tokens")
router.register("tracking", views.TrackingView, basename="tracking")
router.register("static_segment", views.StaticSegmentViewSet)
router.register("static_segment_recipient", views.StaticSegmentRecipientViewSet)
router.register("mail_category", views.MailCategoryViewSet)


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
    path(
        "external/manage/<uuid:recipient_secret>",
        ExternalRecipientManagementView.as_view(),
        name="external_recipient_manager",
    ),
    path("", MailUiView.as_view(), name="mail_ui"),
    re_path(
        r"^(?!api/).*$",
        MailUiView.as_view(),
    ),
    path(
        "api/missing_triggers",
        views.MissingTriggersView.as_view(),
        name="missing_triggers",
    ),
    path(
        "api/create_missing_trigger",
        views.CreateMissingTriggerMailView.as_view(),
        name="create_missing_trigger",
    ),
]
