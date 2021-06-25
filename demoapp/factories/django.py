import factory


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Faker('user_name')
    email = factory.lazy_attribute(lambda o: '%s@appsembler.com' % o.username)
    is_superuser = False

    class Meta:
        model = 'auth.User'
        django_get_or_create = ('username',)
