import sys

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from faker import Faker

from demoapp.models import Author, Book, BookInstance, Genre, Language


class Command(BaseCommand):
    help = 'Generates objects in the database'

    def __init__(self, *args, **kwargs):
        self.fake = Faker()
        self.genres = list({
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
        self.genres_len = len(self.genres)

        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        self.stdout.write('Generating instances in progress...')
        self.generate_books_instances()
        self.create_superuser()
        self.stdout.write(self.style.SUCCESS(
            'Objects generated successfully!'
        ))

    def create_author(self):
        died = self.fake.date_time()
        author = Author.objects.create(
            first_name=self.fake.first_name(),
            last_name=self.fake.last_name(),
            date_of_birth=self.fake.date_time(end_datetime=died),
            date_of_death=self.fake.date_time(),
        )

        return author

    def create_language(self):
        language = self.fake.language_name()
        language, _ = Language.objects.get_or_create(name=language)

        return language

    def create_title(self, count=200):
        return self.fake.sentence()[:-1][:count]

    def create_summary(self):
        return ' '.join(self.fake.sentences())[:1000]

    def create_isbn(self):
        return self.fake.isbn13()

    def create_genre(self):
        index = self.fake.random_int(min=0, max=self.genres_len-1)
        genre, _ = Genre.objects.get_or_create(
            name=self.genres[index]
        )

        return genre

    def generate_book(self):
        book = Book.objects.create(
            title=self.create_title(),
            author=self.create_author(),
            summary=self.create_summary(),
            isbn=self.create_isbn(),
            language=self.create_language(),
        )
        book.genre.add(self.create_genre())
        book.save()
        return book

    def create_user(self):
        username = self.fake.user_name()
        email = self.fake.email()

        user_qs = User.objects.filter(username=username)
        if user_qs.exists():
            return user_qs.first()

        user_qs = User.objects.filter(email=email)
        if user_qs.exists():
            return user_qs.first()

        user = User.objects.create_user(
            username=username,
            email=email,
            password=self.fake.password(),
        )
        return user

    def get_loan_status(self):
        statuses = BookInstance.LOAN_STATUS
        index = self.fake.random_int(min=0, max=len(statuses)-1)
        return statuses[index][0]

    def generate_books_instances(self):
        for _ in range(1000):
            self.stdout.write('.', ending='')
            sys.stdout.flush()

            BookInstance.objects.create(
                book=self.generate_book(),
                imprint=self.create_title(),
                due_back=self.fake.future_datetime(),
                borrower=self.create_user(),
                status=self.get_loan_status(),
            )
        self.stdout.write()

    def create_superuser(self):
        User.objects.create_superuser(
            username='admin',
            email='admin@appsembler.com',
            password='admin'
        )
