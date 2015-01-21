from django.test import SimpleTestCase
from corehq.apps.userreports.exceptions import BadSpecError
from corehq.apps.userreports.transforms.factory import TransformFactory
from corehq.apps.userreports.transforms.specs import CustomTransform


class TransformFactoryTest(SimpleTestCase):

    def testMissingType(self):
        with self.assertRaises(BadSpecError):
            TransformFactory.get_transform({
                "custom_type": "user_display"
            })

    def testInvalidType(self):
        with self.assertRaises(BadSpecError):
            TransformFactory.get_transform({
                "type": "not_a_transform_type",
                "custom_type": "user_display"
            })


class CustomTransformTest(SimpleTestCase):

    def testInvalidCustomType(self):
        with self.assertRaises(BadSpecError):
            TransformFactory.get_transform({
                "type": "custom",
                "custom_type": "not_valid"
            })

    def testValidCustom(self):
        transform = TransformFactory.get_transform({
            "type": "custom",
            "custom_type": "user_display"
        })
        self.assertTrue(isinstance(transform, CustomTransform))
