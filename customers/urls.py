from django.urls import path
from . import views

app_name = "customers"
urlpatterns = [
    path("", views.customer_list, name="list"),
    path("<int:customer_id>/", views.customer_detail, name="detail"),
]
