from django.test import SimpleTestCase
from commcarehq.apps.locations.models import Location
from commcarehq.apps.locations.fixtures import LocationSet


class LocationSetTest(SimpleTestCase):
    def test_duplicate_locations(self):
        location1 = Location(
            _id="1",
            name="Some Parent Location",
            location_type="parent"
        )
        location2 = Location(
            _id="2",
            name="Some Child Location",
            location_type="child",
            parent=location1
        )
        set_locations = LocationSet([location1, location2])
        self.assertEqual(len(set_locations.by_parent['1']), 1)
        self.assertEqual(len(set_locations.by_parent['2']), 0)

        self.assertEqual(len(set_locations.by_id), 2)

        set_locations.add_location(location1)
        set_locations.add_location(location2)

        self.assertEqual(len(set_locations.by_id), 2)
        self.assertEqual(len(set_locations.by_parent['1']), 1)
        self.assertEqual(len(set_locations.by_parent['2']), 0)