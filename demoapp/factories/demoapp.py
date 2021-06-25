import factory.fuzzy

from demoapp.factories.django import UserFactory
from demoapp.models import BookInstance


class AuthorFactory(factory.django.DjangoModelFactory):
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

    date_of_birth = factory.Faker('date_object')
    date_of_death = factory.Faker('date_object')

    class Meta:
        model = 'demoapp.Author'


class GenreFactory(factory.django.DjangoModelFactory):
    name = factory.fuzzy.FuzzyChoice({
        'Action and adventure',
        'Art/architecture',
        'Alternate history',
        'Autobiography',
        'Anthology',
        'Biography',
        'Chick lit',
        'Business/economics',
        'Children\'s',
        'Crafts/hobbies',
        'Classic',
        'Cookbook',
        'Comic book',
        'Diary',
        'Coming-of-age',
        'Dictionary',
        'Crime',
        'Encyclopedia',
        'Drama',
        'Guide',
        'Fairytale',
        'Health/fitness',
        'Fantasy',
        'History',
        'Graphic novel',
        'Home and garden',
        'Historical fiction',
        'Humor',
        'Horror',
        'Journal',
        'Mystery',
        'Math',
        'Paranormal romance',
        'Memoir',
        'Picture book',
        'Philosophy',
        'Poetry',
        'Prayer',
        'Political thriller',
        'Religion, spirituality, and new age',
        'Romance',
        'Textbook',
        'Satire',
        'True crime',
        'Science fiction',
        'Review',
        'Short story',
        'Science',
        'Suspense',
        'Self help',
        'Thriller',
        'Sports and leisure',
        'Western',
        'Travel',
        'Young adult',
        'True crime',
    })

    class Meta:
        model = 'demoapp.Genre'


class LanguageFactory(factory.django.DjangoModelFactory):
    name = factory.Faker('language_name')

    class Meta:
        model = 'demoapp.Language'


class BookFactory(factory.django.DjangoModelFactory):
    title = factory.Faker('sentence')
    author = factory.SubFactory(AuthorFactory)
    summary = factory.Faker('paragraph')
    isbn = factory.Faker('isbn10')
    language = factory.SubFactory(LanguageFactory)

    @factory.post_generation
    def genre(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for g in extracted:
                self.genre.add(g)
        else:
            self.genre.add(GenreFactory.create())

    class Meta:
        model = 'demoapp.Book'


class BookInstanceFactory(factory.django.DjangoModelFactory):
    book = factory.SubFactory(BookFactory)
    borrower = factory.SubFactory(UserFactory)
    due_back = factory.Faker('future_date')
    imprint = factory.Faker('sentence')
    status = factory.fuzzy.FuzzyChoice(
        BookInstance.LOAN_STATUS,
        getter=lambda c: c[0]
    )

    class Meta:
        model = 'demoapp.BookInstance'
