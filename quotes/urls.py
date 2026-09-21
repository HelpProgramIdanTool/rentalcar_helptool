from django.urls import path

from . import views
from bookings import quote_conversion
from bookings import workspace
from bookings import manual
from .inquiry_import import import_inquiry
from bookings.paste_entry import paste_booking

app_name = "quotes"

urlpatterns = [
    path("bookings/paste/", paste_booking, name="paste_booking"),
    path("inquiry-import/", import_inquiry, name="import_inquiry"),
    path("offers/<str:quote_number>/copy/", views.copy_quote, name="copy_quote"),
    path("offers/<str:quote_number>/book/<int:option_id>/", quote_conversion.from_offer, name="booking_from_offer"),
    path("bookings/", workspace.booking_list, name="booking_list"),
    path("bookings/new/", manual.new_booking, name="new_booking"),
    path("bookings/<int:pk>/supplier-message/", workspace.supplier_message, name="supplier_message"),
    path("bookings/<int:pk>/vouchers/", workspace.upload_voucher, name="upload_voucher"),
    path("bookings/<int:pk>/vouchers/<int:voucher_id>/download/", workspace.download_voucher, name="download_voucher"),
    path("bookings/<int:pk>/", workspace.booking_detail, name="booking_detail"),
    path("offers/<str:quote_number>/email/", views.email_editor, name="email_editor"),
    path("offers/<str:quote_number>/guides/<str:code>/", views.quote_guide, name="quote_guide"),
    path("offers/<str:quote_number>/deliveries/<int:delivery_id>/", views.email_delivery, name="email_delivery"),
    path("customers/<int:customer_id>/offer/", views.new_inquiry, name="customer_offer"),
    path("customer-lookup/", views.customer_lookup, name="customer_lookup"),
    path("", views.quote_list, name="home"),
    path("offers/", views.quote_list, name="quote_list"),
    path("offers/new/", views.new_inquiry, name="new_inquiry"),
    path("offers/new/", views.new_inquiry, name="new_inquiry_alias"),
    path("offers/<str:quote_number>/", views.inquiry_saved, name="inquiry_saved"),
    path("offers/<str:quote_number>/edit/", views.edit_quote, name="edit_quote"),
    path("offers/<str:quote_number>/duplicate/", views.duplicate_quote, name="duplicate_quote"),
    path("offers/<str:quote_number>/calculate/", views.calculate_quote, name="calculate_quote"),
    path("offers/<str:quote_number>/preview/", views.quote_preview, name="quote_preview"),
    path("offers/<str:quote_number>/send/", views.send_quote, name="send_quote"),
    path("offers/<str:quote_number>/preview-v2/", views.quote_preview, name="quote_preview_v2"),
]
