from django.urls import path

from tapir.products.views import ExtendedProductTypeApiView

app_name = "products"
urlpatterns = [
    path(
        "api/extended_product_type",
        ExtendedProductTypeApiView.as_view(),
        name="extended_product_type",
    ),
]
