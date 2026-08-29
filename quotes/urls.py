from django.urls import path

from . import views

app_name = "quotes"

urlpatterns = [
    path("customer-lookup/", views.customer_lookup, name="customer_lookup"),
    path("", views.new_inquiry, name="new_inquiry"),
    path("offers/new/", views.new_inquiry, name="new_inquiry_alias"),
    path("offers/<str:quote_number>/", views.inquiry_saved, name="inquiry_saved"),
    path("offers/<str:quote_number>/edit/", views.edit_quote, name="edit_quote"),
    path("offers/<str:quote_number>/duplicate/", views.duplicate_quote, name="duplicate_quote"),
    path("offers/<str:quote_number>/calculate/", views.calculate_quote, name="calculate_quote"),
    path("offers/<str:quote_number>/preview/", views.quote_preview, name="quote_preview"),
    path("offers/<str:quote_number>/preview-v2/", views.quote_preview, name="quote_preview_v2"),
]
