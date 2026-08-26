from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from suppliers.management.commands.import_carfree_locations import make_code
from suppliers.models import Supplier, SupplierLocation


SERVICE_CITY_NAMES = {
    "Bydgoszcz": "Bydgoszcz",
    "Katowice Pyrzowice": "Katowice",
    "Kraków Balice": "Kraków",
    "Olsztyn Szymany": "Olsztyn",
    "Pardubice Airport": "Pardubice",
    "Prague Airport": "Prague",
    "Szczecin Goleniów": "Szczecin",
    "Warszawa-Chopin": "Warszawa",
}


def service_city_name(location):
    return SERVICE_CITY_NAMES.get(location.location_name, location.city)


class Command(BaseCommand):
    help = "Create one virtual address-delivery location per supplier and service city."

    def add_arguments(self, parser):
        parser.add_argument("--supplier-code")
        parser.add_argument("--preview", action="store_true")

    def handle(self, *args, **options):
        suppliers = Supplier.objects.filter(status=Supplier.Status.ACTIVE)
        if options["supplier_code"]:
            suppliers = suppliers.filter(supplier_code=options["supplier_code"])
            if not suppliers.exists():
                raise CommandError(
                    f'Supplier with code {options["supplier_code"]!r} was not found.'
                )

        planned = []
        for supplier in suppliers:
            physical_locations = supplier.locations.exclude(
                location_type=SupplierLocation.LocationType.ADDRESS_DELIVERY
            )
            cities = {}
            for location in physical_locations:
                city = service_city_name(location)
                cities.setdefault(city, location.country)

            for city, country in sorted(cities.items()):
                planned.append(
                    {
                        "supplier": supplier,
                        "location_code": f"{make_code(city)}-DELIVERY",
                        "location_name": f"{city} — delivery to customer address",
                        "city": city,
                        "country": country,
                    }
                )

        for item in planned:
            self.stdout.write(
                f'{item["supplier"].supplier_name} | {item["location_code"]} | '
                f'{item["location_name"]} | {item["country"]}'
            )

        if options["preview"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Preview only: {len(planned)} virtual locations, nothing saved."
                )
            )
            return

        created_count = 0
        updated_count = 0
        with transaction.atomic():
            for item in planned:
                _, created = SupplierLocation.objects.update_or_create(
                    supplier=item["supplier"],
                    location_code=item["location_code"],
                    defaults={
                        "location_name": item["location_name"],
                        "city": item["city"],
                        "country": item["country"],
                        "address": "",
                        "location_type": SupplierLocation.LocationType.ADDRESS_DELIVERY,
                        "airport_code": "",
                        "supports_pickup": True,
                        "supports_return": True,
                        "has_rental_desk": False,
                        "supports_terminal_delivery": False,
                        "supports_address_delivery": True,
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Virtual locations complete: {created_count} created, "
                f"{updated_count} updated."
            )
        )
