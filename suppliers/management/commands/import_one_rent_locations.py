from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from suppliers.models import Supplier, SupplierLocation


ONE_RENT_LOCATIONS = [
    {
        "location_code": "WAW",
        "location_name": "Warsaw Chopin Airport",
        "city": "Warsaw",
        "address": "Żwirki i Wigury 1, 00-001 Warszawa",
        "airport_code": "WAW",
        "pickup": "Meet the One Rent steward in the middle of the arrivals hall.",
        "return": "Leave the car in parking P1 (rent a car) and meet the steward near the information desk in the departures terminal.",
    },
    {
        "location_code": "WMI",
        "location_name": "Warsaw Modlin Airport",
        "city": "Nowy Dwór Mazowiecki",
        "address": "Generała Wiktora Thommée 1a, 05-102 Nowy Dwór Mazowiecki",
        "airport_code": "WMI",
        "pickup": "Meet the One Rent steward in the middle of the arrivals hall.",
        "return": "Leave the car in the departures parking and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "WRO",
        "location_name": "Wrocław Airport",
        "city": "Wrocław",
        "address": "Graniczna 190, 54-530 Wrocław",
        "airport_code": "WRO",
        "pickup": "Meet the One Rent steward in the middle of the arrivals hall.",
        "return": "Leave the car in the departures parking and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "KRK-DELIVERY",
        "location_name": "Kraków Airport terminal delivery",
        "city": "Kraków",
        "address": "Medweckiego 1, 32-083 Balice",
        "airport_code": "KRK",
        "pickup": "Meet the agent after baggage claim in the arrivals hall. The agent will escort the customer to the shuttle bus or directly to the car.",
        "return": "Return is handled at the separate TINA Balice Parking location.",
        "supports_return": False,
    },
    {
        "location_code": "KRK-TINA",
        "location_name": "TINA Balice Parking",
        "city": "Kraków",
        "address": "",
        "airport_code": "",
        "pickup": "The car can be collected at the One Rent office at TINA Balice Parking.",
        "return": "Enter TINA Balice Parking, use lane C and leave the car in a marked One Rent bay. Outside office hours, put the keys in the key box by the office.",
        "location_type": SupplierLocation.LocationType.BRANCH,
        "has_rental_desk": True,
        "supports_terminal_delivery": False,
        "supports_self_return_via_key_box": True,
    },
    {
        "location_code": "POZ",
        "location_name": "Poznań Ławica Airport",
        "city": "Poznań",
        "address": "Bukowska 285, 60-189 Poznań",
        "airport_code": "POZ",
        "pickup": "Meet the One Rent steward in the middle of the arrivals hall.",
        "return": "Leave the car in parking P1 or P3 and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "RZE",
        "location_name": "Rzeszów Jasionka Airport",
        "city": "Rzeszów",
        "address": "Jasionka 942, 36-002 Jasionka",
        "airport_code": "RZE",
        "pickup": "Meet the One Rent steward in the middle of the arrivals hall.",
        "return": "Leave the car in the departures parking and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "LUZ",
        "location_name": "Lublin Airport",
        "city": "Lublin",
        "address": "Króla Jana III Sobieskiego 1, 21-040 Świdnik",
        "airport_code": "LUZ",
        "pickup": "Meet the One Rent steward in the middle of the arrivals hall.",
        "return": "Leave the car in the departures parking and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "GDN",
        "location_name": "Gdańsk Airport",
        "city": "Gdańsk",
        "address": "Juliusza Słowackiego 210, 80-298 Gdańsk",
        "airport_code": "GDN",
        "pickup": "Meet the One Rent steward in the middle of the arrivals hall.",
        "return": "Leave the car in the departures parking and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "KTW",
        "location_name": "Katowice Pyrzowice Airport",
        "city": "Katowice",
        "address": "Wolności 90, 42-625 Ożarowice",
        "airport_code": "KTW",
        "pickup": "Meet the One Rent steward in the middle of the arrivals hall.",
        "return": "Leave the car in the departures parking and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "SZZ",
        "location_name": "Szczecin Goleniów Airport",
        "city": "Szczecin",
        "address": "Glewice 1a, 72-100 Goleniów",
        "airport_code": "SZZ",
        "pickup": "Meet the One Rent steward in the middle of the arrivals hall.",
        "return": "Leave the car in parking P1 and meet the driver at the main entrance to the departures hall.",
    },
]


class Command(BaseCommand):
    help = "Preview or import verified One Rent locations from its rental guide."

    def add_arguments(self, parser):
        parser.add_argument("--supplier-code", default="02")
        parser.add_argument("--preview", action="store_true")

    def handle(self, *args, **options):
        for source in ONE_RENT_LOCATIONS:
            pickup = "yes" if source.get("supports_pickup", True) else "no"
            returns = "yes" if source.get("supports_return", True) else "no"
            key_box = "yes" if source.get("supports_self_return_via_key_box", False) else "no"
            self.stdout.write(
                f'{source["location_code"]}: {source["location_name"]} | '
                f'pickup={pickup} | return={returns} | key_box={key_box}'
            )

        if options["preview"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Preview only: {len(ONE_RENT_LOCATIONS)} locations, nothing saved."
                )
            )
            return

        try:
            supplier = Supplier.objects.get(supplier_code=options["supplier_code"])
        except Supplier.DoesNotExist as error:
            raise CommandError(
                f'Supplier with code {options["supplier_code"]!r} was not found.'
            ) from error

        created_count = 0
        updated_count = 0
        with transaction.atomic():
            for source in ONE_RENT_LOCATIONS:
                defaults = {
                    "location_name": source["location_name"],
                    "city": source["city"],
                    "country": "Poland",
                    "address": source["address"],
                    "location_type": source.get(
                        "location_type", SupplierLocation.LocationType.AIRPORT
                    ),
                    "airport_code": source["airport_code"],
                    "supports_pickup": source.get("supports_pickup", True),
                    "supports_return": source.get("supports_return", True),
                    "has_rental_desk": source.get("has_rental_desk", False),
                    "supports_terminal_delivery": source.get(
                        "supports_terminal_delivery", True
                    ),
                    "supports_address_delivery": False,
                    "supports_self_return_via_key_box": source.get(
                        "supports_self_return_via_key_box", False
                    ),
                    "default_pickup_instructions": source["pickup"],
                    "default_return_instructions": source["return"],
                    "is_active": True,
                }
                _, created = SupplierLocation.objects.update_or_create(
                    supplier=supplier,
                    location_code=source["location_code"],
                    defaults=defaults,
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete: {created_count} created, {updated_count} updated."
            )
        )
