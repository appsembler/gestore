
from django.test import TestCase

from demoapp.factories.demoapp import BookFactory, GenreFactory
from demoapp.factories.django import UserFactory
from demoapp.models import Author, Book, Genre, Profile
from gestore import processors


class TestProcessors(TestCase):
    def test_process_foreign_key(self):
        book = BookFactory.create()
        value, item = processors.process_foreign_key(book, Book.author.field)

        # Value returned must equal the ID of the object in the instance
        self.assertEqual(value, book.author.id)

        # Item returned must equal the field itself
        self.assertEqual(item, book.author)

    def test_process_one_to_many_relation(self):
        book = BookFactory.create()

        # Creating a book will create 1 author
        self.assertEqual(Author.objects.count(), 1)

        author = Author.objects.first()
        to_process = processors.process_one_to_many_relation(
            author, author._meta.get_field('book')
        )

        # to_process should be a list of instances to process
        self.assertEqual(type(to_process), list)

        # Must have a single instance of Book
        self.assertEqual(len(to_process), 1)
        self.assertEqual(to_process[0], book)

    def test_process_one_to_one_relation_exists(self):
        user = UserFactory.create()
        profile = user.profile

        items = processors.process_one_to_one_relation(
            profile,
            Profile.user.field
        )

        # Return type is a list that contains one item only
        self.assertEqual(type(items), list)
        self.assertEqual(len(items), 1)

        # The object must equal the one it's connected to
        self.assertEqual(items[0], user)

    def test_process_many_to_many_relation(self):
        book1 = BookFactory.create()

        self.assertEqual(Book.objects.count(), 1)
        self.assertEqual(Genre.objects.count(), 1)

        genre = Genre.objects.first()
        data, to_process = processors.process_many_to_many_relation(
            book1, Book.genre.field
        )

        # data and to_process are list
        self.assertEqual(type(data), list)
        self.assertEqual(type(to_process), list)

        # Must have one item with book id
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], book1.id)

        # Must get one item to process, and it's Genre on the other end
        self.assertEqual(len(to_process), 1)
        self.assertEqual(to_process[0], genre)

    def test_process_many_to_many_relation_other_end(self):
        genre = GenreFactory.create()
        books = {
            BookFactory.create(genre=[genre]),
            BookFactory.create(genre=[genre])
        }

        self.assertEqual(Book.objects.count(), len(books))
        self.assertEqual(Genre.objects.count(), 1)

        data, to_process = processors.process_many_to_many_relation(
            genre, Genre._meta.get_field('book')
        )

        # No data shall be returned on the other end
        self.assertIsNone(data)

        # Must return all books using this genre to be processed
        self.assertEqual(len(to_process), len(books))
        for obj in to_process:
            if obj not in books:
                raise AssertionError('obj with %s not in list' % obj.id)
