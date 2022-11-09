from django.urls import path

from tapir.log import views

app_name = "log"
urlpatterns = [
    path(
        "<str:pk>/email_content",
        views.email_log_entry_content,
        name="email_log_entry_content",
    ),
    path(
        "text/create/user/<str:user_pk>",
        views.create_text_log_entry,
        name="create_user_text_log_entry",
    ),
    path(
        "text/create/shareowner/<str:shareowner_pk>",
        views.create_text_log_entry,
        name="create_share_owner_text_log_entry",
    ),
]
