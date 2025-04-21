import datetime
import random

from environ import ImproperlyConfigured

from tapir.pickup_locations.models import PickupLocationBasketCapacity
from tapir.utils.config import Organization
from tapir.wirgarten.models import ProductType, PickupLocationOpeningTime
from tapir.wirgarten.tests.factories import (
    PickupLocationFactory,
    PickupLocationCapabilityFactory,
)


class PickupLocationGenerator:
    @classmethod
    def generate_pickup_locations(cls, organization: Organization):
        match organization:
            case Organization.WIRGARTEN:
                cls.generate_pickup_locations_for_wirgarten()
            case Organization.BIOTOP:
                cls.generate_pickup_locations_for_biotop()
            case _:
                raise ImproperlyConfigured(f"Unknown organization: {organization}")

    @classmethod
    def generate_pickup_locations_for_wirgarten(cls):
        ernteanteile = ProductType.objects.get(name="Ernteanteile")
        huehneranteile = ProductType.objects.get(name="Hühneranteile")

        wirgarten = PickupLocationFactory.create(
            name="WirGarten Lüneburg",
            coords_lon=53.2731785,
            coords_lat=10.3741809,
            street="Vögelser Straße 25",
            postcode="21339",
            city="Lüneburg-Ochtmissen",
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=wirgarten, max_capacity=30, product_type=ernteanteile
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=wirgarten, max_capacity=None, product_type=huehneranteile
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=wirgarten,
            day_of_week=3,
            open_time=datetime.time(hour=8),
            close_time=datetime.time(hour=17),
        )

        edeka = PickupLocationFactory.create(
            name="Edeka Bergmann",
            coords_lon=53.2443079,
            coords_lat=10.3996325,
            street="Sülfmeisterstraße 3",
            postcode="21335",
            city="Lüneburg",
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=edeka, max_capacity=60, product_type=ernteanteile
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=edeka, max_capacity=None, product_type=huehneranteile
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=edeka,
            day_of_week=3,
            open_time=datetime.time(hour=8),
            close_time=datetime.time(hour=20),
        )

        fluse = PickupLocationFactory.create(
            name="Wohnprojekt Fluse",
            coords_lon=53.2541747,
            coords_lat=10.4238272,
            street="Meisterweg 100",
            postcode="21337",
            city="Lüneburg",
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=fluse, max_capacity=60, product_type=ernteanteile
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=fluse, max_capacity=0, product_type=huehneranteile
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=fluse,
            day_of_week=3,
            open_time=datetime.time(hour=1),
            close_time=datetime.time(hour=18, minute=30),
        )

        frohnatur = PickupLocationFactory.create(
            name="FrohNatur",
            coords_lon=53.2476476,
            coords_lat=10.3533381,
            street="An der Eulenburg 28",
            postcode="21391",
            city="Reppenstedt",
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=frohnatur, max_capacity=30, product_type=ernteanteile
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=frohnatur, max_capacity=0, product_type=huehneranteile
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=frohnatur,
            day_of_week=2,
            open_time=datetime.time(hour=13),
            close_time=datetime.time(hour=18),
        )

        garage = PickupLocationFactory.create(
            name="Garage am Finkenberg",
            coords_lon=53.2421706,
            coords_lat=10.3937467,
            street="Finkenberg 1",
            postcode="21339",
            city="Lüneburg",
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=garage, max_capacity=None, product_type=ernteanteile
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=garage, max_capacity=None, product_type=huehneranteile
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=garage,
            day_of_week=2,
            open_time=datetime.time(hour=15, minute=30),
            close_time=datetime.time(hour=23, minute=59),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=garage,
            day_of_week=3,
            open_time=datetime.time(hour=13),
            close_time=datetime.time(hour=18),
        )

        gemeinde = PickupLocationFactory.create(
            name="Paul-Gerhardt-Gemeinde",
            coords_lon=53.2477177,
            coords_lat=10.4385238,
            street="Bunsenstr. 82",
            postcode="21337",
            city="Lüneburg",
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=gemeinde, max_capacity=30, product_type=ernteanteile
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=gemeinde, max_capacity=None, product_type=huehneranteile
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=gemeinde,
            day_of_week=3,
            open_time=datetime.time(hour=10, minute=0),
            close_time=datetime.time(hour=19, minute=00),
        )

        uni = PickupLocationFactory.create(
            name="Uni-Campus",
            coords_lon=53.2477453,
            coords_lat=10.4231546,
            street="Scharnhorststr. 1",
            postcode="21335",
            city="Lüneburg",
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=uni, max_capacity=60, product_type=ernteanteile
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=uni, max_capacity=None, product_type=huehneranteile
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=uni,
            day_of_week=2,
            open_time=datetime.time(hour=16, minute=0),
            close_time=datetime.time(hour=23, minute=59),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=uni,
            day_of_week=3,
            open_time=datetime.time(hour=0, minute=0),
            close_time=datetime.time(hour=12, minute=0),
        )

        feldstrasse = PickupLocationFactory.create(
            name="Feldstraße (Rotes Feld)",
            coords_lon=53.2424043,
            coords_lat=10.4074418,
            street="Feldstr. 14",
            postcode="21335",
            city="Lüneburg",
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=feldstrasse, max_capacity=33, product_type=ernteanteile
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=feldstrasse, max_capacity=None, product_type=huehneranteile
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=feldstrasse,
            day_of_week=2,
            open_time=datetime.time(hour=13, minute=30),
            close_time=datetime.time(hour=20, minute=0),
        )

        lena = PickupLocationFactory.create(
            name="LeNa",
            coords_lon=53.2574314,
            coords_lat=10.3790822,
            street="Brockwinkler Weg 72b",
            postcode="21339",
            city="Lüneburg",
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=lena, max_capacity=15, product_type=ernteanteile
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=lena, max_capacity=15, product_type=huehneranteile
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=lena,
            day_of_week=2,
            open_time=datetime.time(hour=17, minute=0),
            close_time=datetime.time(hour=21, minute=0),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=lena,
            day_of_week=3,
            open_time=datetime.time(hour=8, minute=0),
            close_time=datetime.time(hour=21, minute=0),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=lena,
            day_of_week=4,
            open_time=datetime.time(hour=8, minute=0),
            close_time=datetime.time(hour=21, minute=0),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=lena,
            day_of_week=5,
            open_time=datetime.time(hour=8, minute=0),
            close_time=datetime.time(hour=12, minute=0),
        )

    @classmethod
    def generate_pickup_locations_for_biotop(cls):
        biodelikat = PickupLocationFactory.create(
            name="Biodelikat",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=biodelikat,
            day_of_week=5,
            open_time=datetime.time(hour=7),
            close_time=datetime.time(hour=18),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=biodelikat,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=biodelikat,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=biodelikat,
            day_of_week=4,
            open_time=datetime.time(hour=15),
            close_time=datetime.time(hour=19),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=biodelikat,
            day_of_week=5,
            open_time=datetime.time(hour=8),
            close_time=datetime.time(hour=15),
        )

        zentrum = PickupLocationFactory.create(
            name="Tölzer Zentrum",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=zentrum,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=zentrum,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=zentrum,
            day_of_week=4,
            open_time=datetime.time(hour=15),
            close_time=datetime.time(hour=21),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=zentrum,
            day_of_week=5,
            open_time=datetime.time(hour=7),
            close_time=datetime.time(hour=18),
        )

        badeteil = PickupLocationFactory.create(
            name="Badeteil",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=badeteil,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=badeteil,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=badeteil,
            day_of_week=4,
            open_time=datetime.time(hour=15),
            close_time=datetime.time(hour=21),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=badeteil,
            day_of_week=5,
            open_time=datetime.time(hour=6),
            close_time=datetime.time(hour=18),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=badeteil,
            day_of_week=6,
            open_time=datetime.time(hour=6),
            close_time=datetime.time(hour=18),
        )

        norden = PickupLocationFactory.create(
            name="Tölzer Norden",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=norden,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=norden,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=norden,
            day_of_week=4,
            open_time=datetime.time(hour=15),
            close_time=datetime.time(hour=21),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=norden,
            day_of_week=5,
            open_time=datetime.time(hour=7),
            close_time=datetime.time(hour=18),
        )

        hofpunkt = PickupLocationFactory.create(
            name="Biotop-Hofpunkt",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=hofpunkt,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=hofpunkt,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=hofpunkt,
            day_of_week=4,
            open_time=datetime.time(hour=10),
            close_time=datetime.time(hour=23, minute=59),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=hofpunkt,
            day_of_week=5,
            open_time=datetime.time(hour=0),
            close_time=datetime.time(hour=23, minute=59),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=hofpunkt,
            day_of_week=6,
            open_time=datetime.time(hour=0),
            close_time=datetime.time(hour=23, minute=59),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=hofpunkt,
            day_of_week=1,
            open_time=datetime.time(hour=0),
            close_time=datetime.time(hour=8, minute=0),
        )

        warenhaus = PickupLocationFactory.create(
            name="Grünes Warenhaus",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=warenhaus,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=warenhaus,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=warenhaus,
            day_of_week=4,
            open_time=datetime.time(hour=10),
            close_time=datetime.time(hour=13, minute=0),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=warenhaus,
            day_of_week=4,
            open_time=datetime.time(hour=14, minute=30),
            close_time=datetime.time(hour=18, minute=30),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=warenhaus,
            day_of_week=5,
            open_time=datetime.time(hour=8, minute=0),
            close_time=datetime.time(hour=13, minute=0),
        )

        hochalmstrasse = PickupLocationFactory.create(
            name="Hochalmstraße Lenggries",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=hochalmstrasse,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=hochalmstrasse,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=hochalmstrasse,
            day_of_week=4,
            open_time=datetime.time(hour=12),
            close_time=datetime.time(hour=21, minute=0),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=hochalmstrasse,
            day_of_week=5,
            open_time=datetime.time(hour=7),
            close_time=datetime.time(hour=18, minute=0),
        )

        schlossweg = PickupLocationFactory.create(
            name="Schloßweg",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=schlossweg,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=schlossweg,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=schlossweg,
            day_of_week=4,
            open_time=datetime.time(hour=15),
            close_time=datetime.time(hour=23, minute=59),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=schlossweg,
            day_of_week=5,
            open_time=datetime.time(hour=0),
            close_time=datetime.time(hour=23, minute=59),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=schlossweg,
            day_of_week=6,
            open_time=datetime.time(hour=15),
            close_time=datetime.time(hour=20, minute=0),
        )

        hotel = PickupLocationFactory.create(
            name="Zauberkabinett",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=hotel,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=hotel,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=hotel,
            day_of_week=4,
            open_time=datetime.time(hour=16),
            close_time=datetime.time(hour=20, minute=0),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=hotel,
            day_of_week=5,
            open_time=datetime.time(hour=7),
            close_time=datetime.time(hour=16, minute=0),
        )

        penzberg = PickupLocationFactory.create(
            name="Penzberg",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=penzberg,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=penzberg,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=penzberg,
            day_of_week=4,
            open_time=datetime.time(hour=16),
            close_time=datetime.time(hour=18, minute=30),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=penzberg,
            day_of_week=5,
            open_time=datetime.time(hour=8, minute=30),
            close_time=datetime.time(hour=14, minute=0),
        )

        tutzing = PickupLocationFactory.create(
            name="Tutzing",
            coords_lon=47 + random.random(),
            coords_lat=11 + random.random(),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="kleine Kiste",
            pickup_location=tutzing,
            capacity=random.randint(10, 100),
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="normale Kiste",
            pickup_location=tutzing,
            capacity=random.randint(10, 100),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=tutzing,
            day_of_week=4,
            open_time=datetime.time(hour=16, minute=30),
            close_time=datetime.time(hour=19, minute=0),
        )
        PickupLocationOpeningTime.objects.create(
            pickup_location=tutzing,
            day_of_week=5,
            open_time=datetime.time(hour=7, minute=0),
            close_time=datetime.time(hour=17, minute=30),
        )
