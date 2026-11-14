from django.urls import path
from . import views

app_name = "customers"
urlpatterns = [
    path('contacts/', views.contact_list, name='contacts'),
    path('contacts/<int:contact_id>/', views.contact_detail, name='contact_detail'),
    path("", views.customer_list, name="list"),
    path("<int:customer_id>/", views.customer_detail, name="detail"),
]
