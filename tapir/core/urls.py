from django.urls import path

from tapir.core import views

app_name = "core"
urlpatterns = [
    path(
        "api/get_theme",
        views.GetThemeView.as_view(),
        name="get_theme",
    ),
    path(
        "api/member_mail_category_data",
        views.MemberMailCategoryDataApiView.as_view(),
        name="member_mail_category_data",
    ),
    path(
        "api/member_extra_emails",
        views.MemberExtraEmailApiView.as_view(),
        name="member_extra_emails",
    ),
    path(
        "member_extra_email_confirm/<uuid:secret>",
        views.ConfirmMemberExtraEmailApiView.as_view(),
        name="member_extra_email_confirm",
    ),
    path(
        "member_extra_email_confirmed/<uuid:secret>",
        views.MemberExtraEmailConfirmedView.as_view(),
        name="member_extra_email_confirmed",
    ),
]
