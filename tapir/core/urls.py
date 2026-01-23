from django.urls import path

from tapir.core import views
from tapir.core.views import MemberMailCategoryDataApiView

app_name = "core"
urlpatterns = [
    path(
        "api/get_theme",
        views.GetThemeView.as_view(),
        name="get_theme",
    ),
    path(
        "api/member_mail_category_data",
        MemberMailCategoryDataApiView.as_view(),
        name="member_mail_category_data",
    ),
]
