from django.urls import path

from tapir.products.views import (
    ExtendedProductTypeApiView,
    ProductTypesWithoutCapacityAndConfigApiView,
)

app_name = "products"
urlpatterns = [
    path(
        "api/extended_product_type",
        ExtendedProductTypeApiView.as_view(),
        name="extended_product_type",
    ),
    path(
        "api/product_types_without_capacity",
        ProductTypesWithoutCapacityAndConfigApiView.as_view(),
        name="product_types_without_capacity",
    ),
]
