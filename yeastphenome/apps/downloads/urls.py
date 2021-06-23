from django.urls import path

from . import views

urlpatterns = [
    path("bundles/", views.download_bundles, name="download_bundles"),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/add/<int:datasets_to_add>/", views.add_to_cart, name="add_to_cart"),
    path(
        "cart/remove/<int:datasets_to_remove>/",
        views.remove_from_cart,
        name="remove_from_cart",
    ),
    path("cart/download/", views.download_cart, name="download_cart"),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
]

app_name = "downloads"
