from django.urls import include, path
from rest_framework import routers

from tapir.mail.media_library import views

urlpatterns = [
    path("filepond/", include("django_drf_filepond.urls")),
    path("confirm_upload/", views.ConfirmUploadView.as_view(), name="confirm_upload"),
    path("get_file/<str:upload_id>", views.get_file_view, name="get_file"),
]

router = routers.DefaultRouter()
router.register("temporary_upload", views.TemporaryUploadViewSet)
router.register("stored_upload", views.StoredUploadViewSet)

urlpatterns += router.urls
