from django.urls import path
from django.views import generic

from tapir.accounts.views import change_email, AdminApplyMailChangeView

app_name = "accounts"
urlpatterns = [
    # Standard login/logout/password views should be un-namespaced because Django refers to them in a few places and
    # it's easier to do it like this than hunt down all the places and fix the references
    path(
        "password_change",
        generic.TemplateView.as_view(template_name="accounts/password_update.html"),
        name="password_change",
    ),
    path("email_change/<str:token>", change_email, name="change_email_confirm"),
    path(
        "admin_apply_mail_change",
        AdminApplyMailChangeView.as_view(),
        name="admin_apply_mail_change",
    ),
    path(
        "link_expired",
        generic.TemplateView.as_view(template_name="accounts/link_expired.html"),
        name="link_expired",
    ),
]
