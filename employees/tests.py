from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Employee


class EmployeeTests(TestCase):
    def test_new_employee_is_active_by_default(self):
        employee = Employee.objects.create(
            first_name="Idan",
            last_name="Caliber",
            role=Employee.Role.OWNER_ADMIN,
        )

        self.assertEqual(employee.status, Employee.Status.ACTIVE)

    def test_employee_is_displayed_by_full_name(self):
        employee = Employee(
            first_name="Anna",
            last_name="Nowak",
            role=Employee.Role.SALES,
        )

        self.assertEqual(employee.full_name, "Anna Nowak")
        self.assertEqual(str(employee), "Anna Nowak")

    def test_employee_can_be_linked_to_login_user(self):
        user = get_user_model().objects.create_user(username="anna")

        employee = Employee.objects.create(
            first_name="Anna",
            last_name="Nowak",
            role=Employee.Role.SALES,
            login_user=user,
        )

        self.assertEqual(user.employee_profile, employee)

    def test_employee_is_available_in_admin(self):
        self.assertIn(Employee, admin.site._registry)
