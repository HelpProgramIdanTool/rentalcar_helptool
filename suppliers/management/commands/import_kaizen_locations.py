from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from suppliers.models import Supplier, SupplierLocation


CUSTOMER_SERVICE_PHONE = "+48 76 727 99 99"

KAIZEN_LOCATIONS = [
    {
        "location_code": "WAW",
        "location_name": "Warsaw Chopin Airport",
        "city": "Warsaw",
        "address": "Żwirki i Wigury 1, 00-001 Warsaw",
        "airport_code": "WAW",
        "phone": "+48 881 717 924",
        "has_rental_desk": True,
        "pickup": "Visit the airport office on level 0 in arrivals, next to McDonald's. Collect the car from car park P34, about five minutes from the terminal.",
        "return": "Return the car to car park P34, then return the keys and parking ticket to the airport office.",
    },
    {
        "location_code": "WMI",
        "location_name": "Warsaw Modlin Airport",
        "city": "Nowy Dwór Mazowiecki",
        "address": "Generała Wiktora Thommée 1a, 05-102 Nowy Dwór Mazowiecki",
        "airport_code": "WMI",
        "phone": "+48 881 212 955",
        "supports_terminal_delivery": True,
        "pickup": "Staff will contact the customer and meet them at the main exit from the arrivals hall.",
        "return": "Leave the car in the departures parking and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "WARSAW-CITY",
        "location_name": "Warsaw City Office",
        "city": "Warsaw",
        "address": "Łączyny 2/52, entrance from Pieskowa Skała street, 02-699 Warsaw",
        "phone": "+48 881 212 063",
        "location_type": SupplierLocation.LocationType.BRANCH,
        "has_rental_desk": True,
        "pickup": "The personnel will be waiting in the office.",
        "return": "Leave the car in the car park near the office and meet the driver in the Kaizen Rent office.",
    },
    {
        "location_code": "WRO",
        "location_name": "Wrocław Airport",
        "city": "Wrocław",
        "address": "Graniczna 190, 54-530 Wrocław",
        "airport_code": "WRO",
        "phone": "+48 881 212 687",
        "has_rental_desk": True,
        "supports_self_return_via_key_box": True,
        "pickup": "Use the Kaizen desk in the terminal's car rental area in arrivals.",
        "return": "Use the reserved airport spaces or car park PC, then meet the driver at the Kaizen office or leave the keys in the key box.",
    },
    {
        "location_code": "KRK-AIRPORT",
        "location_name": "Kraków Balice Airport",
        "city": "Kraków",
        "address": "Medweckiego 1, 32-083 Balice",
        "airport_code": "KRK",
        "phone": "+48 881 212 968",
        "has_rental_desk": True,
        "supports_self_return_via_key_box": True,
        "pickup": "Use the last rental car office on the first floor of the terminal.",
        "return": "Leave the car in sector E on level 5.5, then meet the driver at the first-floor Kaizen office or leave the keys in the key box.",
    },
    {
        "location_code": "KRAKOW-CITY",
        "location_name": "Kraków City Office",
        "city": "Kraków",
        "address": "Radzikowskiego 5a, 31-305 Kraków",
        "phone": "+48 881 212 074",
        "location_type": SupplierLocation.LocationType.BRANCH,
        "has_rental_desk": True,
        "pickup": "The personnel will be waiting in the office.",
        "return": "Leave the car in the car park next to the office and meet the driver at the Kaizen Rent office.",
    },
    {
        "location_code": "POZ",
        "location_name": "Poznań Ławica Airport",
        "city": "Poznań",
        "address": "Bukowska 285, 60-189 Poznań",
        "airport_code": "POZ",
        "phone": "+48 881 212 076",
        "supports_terminal_delivery": True,
        "pickup": "Meet the personnel inside the arrivals hall at the main exit.",
        "return": "Leave the car in parking P1 or P3 and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "RZE",
        "location_name": "Rzeszów Jasionka Airport",
        "city": "Rzeszów",
        "address": "Jasionka 942, 36-002 Jasionka",
        "airport_code": "RZE",
        "phone": "+48 881 212 074",
        "supports_terminal_delivery": True,
        "pickup": "Meet the personnel in the arrivals terminal; they will display the customer's name and the Kaizen Rent logo.",
        "return": "Leave the car in the departures parking and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "LUZ",
        "location_name": "Lublin Airport",
        "city": "Lublin",
        "address": "Króla Jana III Sobieskiego 1, 21-040 Świdnik",
        "airport_code": "LUZ",
        "phone": "+48 881 212 063",
        "supports_terminal_delivery": True,
        "pickup": "Meet the personnel in the arrivals terminal; they will display the customer's name and the Kaizen Rent logo.",
        "return": "Leave the car in the departures parking and meet the driver at the main entrance to the departures hall.",
    },
    {
        "location_code": "GDN",
        "location_name": "Gdańsk Airport",
        "city": "Gdańsk",
        "address": "Juliusza Słowackiego 210, 80-298 Gdańsk",
        "airport_code": "GDN",
        "phone": "+48 881 212 746",
        "has_rental_desk": True,
        "pickup": "Use the Kaizen office at the end of the terminal, next to So! Coffee.",
        "return": "Leave the car in car park P2 in a Kaizen space and meet the driver in the Kaizen office.",
    },
    {
        "location_code": "KTW",
        "location_name": "Katowice Pyrzowice Airport transfer",
        "city": "Katowice",
        "address": "Wolności 90, 42-625 Ożarowice",
        "airport_code": "KTW",
        "phone": "+48 881 212 022",
        "pickup": "Staff will contact the customer and take them from the arrivals terminal to the Kaizen office at Transportowa 2, Pyrzowice.",
        "return": "Return the car to the Kaizen office at Transportowa 2, Pyrzowice. Staff will drive the customer back to the airport.",
    },
    {
        "location_code": "SZZ",
        "location_name": "Szczecin Goleniów Airport",
        "city": "Szczecin",
        "address": "Glewice 1a, 72-100 Szczecin Goleniów",
        "airport_code": "SZZ",
        "phone": "",
        "supports_terminal_delivery": True,
        "pickup": "Meet the Kaizen driver in the arrivals hall and continue to the airport parking area for the handover.",
        "return": "Leave the car in airport car park P1, then meet the driver at the main entrance to the departures hall and hand over the keys and parking ticket.",
    },
]


class Command(BaseCommand):
    help = "Preview or import verified Kaizen locations and meeting instructions."

    def add_arguments(self, parser):
        parser.add_argument("--supplier-code", default="01")
        parser.add_argument("--preview", action="store_true")

    def handle(self, *args, **options):
        for source in KAIZEN_LOCATIONS:
            service = "desk" if source.get("has_rental_desk", False) else "driver/transfer"
            key_box = "yes" if source.get("supports_self_return_via_key_box", False) else "no"
            self.stdout.write(
                f'{source["location_code"]}: {source["location_name"]} | '
                f'{service} | key_box={key_box}'
            )

        if options["preview"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Preview only: {len(KAIZEN_LOCATIONS)} locations, nothing saved."
                )
            )
            return

        try:
            supplier = Supplier.objects.get(supplier_code=options["supplier_code"])
        except Supplier.DoesNotExist as error:
            raise CommandError(
                f'Supplier with code {options["supplier_code"]!r} was not found.'
            ) from error

        supplier.phone = CUSTOMER_SERVICE_PHONE
        supplier.save(update_fields=["phone", "updated_at"])

        created_count = 0
        updated_count = 0
        with transaction.atomic():
            for source in KAIZEN_LOCATIONS:
                defaults = {
                    "location_name": source["location_name"],
                    "city": source["city"],
                    "country": "Poland",
                    "address": source["address"],
                    "location_type": source.get(
                        "location_type", SupplierLocation.LocationType.AIRPORT
                    ),
                    "airport_code": source.get("airport_code", ""),
                    "phone": source["phone"],
                    "supports_pickup": True,
                    "supports_return": True,
                    "has_rental_desk": source.get("has_rental_desk", False),
                    "supports_terminal_delivery": source.get(
                        "supports_terminal_delivery", False
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
