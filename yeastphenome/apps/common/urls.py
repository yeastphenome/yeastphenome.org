from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/add/<str:dataset_id>/<str:next>", views.add_to_cart, name="add_to_cart"),
    path(
        "cart/remove/<str:dataset_id>/<str:next>",
        views.remove_from_cart,
        name="remove_from_cart",
    ),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
    # Development templates
    path("dev/depmap/", views.depmap_inspired, name="depmap_inspired"),
]

app_name = "common"
