from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import FileField, ImageFieldFile
from django.test import TestCase

from django_countries.fields import Country

from gestore.encoders import GestoreEncoder


class TestGestoreEncoder(TestCase):
    def setUp(self):
        self.encoder = GestoreEncoder()

    def test_super_class(self):
        self.assertTrue(issubclass(GestoreEncoder, DjangoJSONEncoder))

    def test_image_file_field(self):
        field = ImageFieldFile(
            instance=None,
            field=FileField(),
            name='pictures/default.jpg'
        )

        value_returned = self.encoder.default(field)
        self.assertEqual(value_returned, field.name)

    def test_country_field(self):
        code = 'PS'
        field = Country(code)

        value_returned = self.encoder.default(field)
        self.assertEqual(value_returned, field.code)

    def test_country_field_does_not_exist(self):
        code = 'PS'
        field = Country(code)

        # Monkey patching import
        try:
            import __builtin__
            realimport = __builtin__.__import__

            def fakeimport(name, *args, **kw):
                if name == 'django_countries':
                    raise ImportError
                realimport(name, *args, **kw)
            __builtin__.__import__ = fakeimport

            with self.assertRaises(TypeError):
                # This means our encoder hit the super method
                self.encoder.default(field)
        finally:
            # Make sure this is set back to default no matter what happens
            __builtin__.__import__ = realimport
