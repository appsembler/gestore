from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import ImageFieldFile

from django_countries.fields import Country


class GestoreEncoder(DjangoJSONEncoder):
    def default(self, o, *args, **kwargs):
        if isinstance(o, ImageFieldFile):
            return str(o)
        if isinstance(o, Country):
            return o.code

        return super(GestoreEncoder, self).default(o, *args, **kwargs)
