from django.test import TestCase
from django.urls import reverse
from . import tests as inquiry_data


class DriverLayoutTests(TestCase):
    setUp = inquiry_data.FirstInquiryTests.setUp

    def test_one_driver_editor_replaces_legacy_fee_widgets(self):
        response = self.client.get(reverse('quotes:new_inquiry'))
        self.assertContains(response, 'data-driver-editor', count=1)
        self.assertContains(response, 'driver_details.css')
        self.assertContains(response, 'class="driver-toggle"')
        self.assertNotContains(response, 'name="young_driver_quantity"')
        self.assertNotContains(response, 'value="YOUNG_DRIVER"')
