from django.urls import path

from demoapp import views

urlpatterns = [
    path('', views.index, name='index'),
    path('author/<int:pk>',
         views.AuthorDetailView.as_view(), name='author-detail'),
    path('author/create/', views.AuthorCreate.as_view(), name='author-create'),
    path(
        'author/<int:pk>/update/',
        views.AuthorUpdate.as_view(),
        name='author-update'
    ),
    path('author/<int:pk>/delete/', views.AuthorDelete.as_view(),
         name='author-delete'),
    path('authors/', views.AuthorListView.as_view(), name='authors'),
    path('books/', views.BookListView.as_view(), name='books'),
    path('book/<int:pk>', views.BookDetailView.as_view(), name='book-detail'),
    path('book/<uuid:pk>/renew/', views.renew_book_librarian,
         name='renew-book-librarian'),
    path('book/create/', views.BookCreate.as_view(), name='book-create'),
    path('book/<int:pk>/update/', views.BookUpdate.as_view(),
         name='book-update'),
    path('book/<int:pk>/delete/', views.BookDelete.as_view(),
         name='book-delete'),
    path(r'borrowed/', views.LoanedBooksAllListView.as_view(),
         name='all-borrowed'),
    path('genres/', views.GenresListView.as_view(), name='genres'),
    path('genre/create/', views.GenreCreate.as_view(), name='genre-create'),
    path('genre/<int:pk>', views.GenreView.as_view(), name='genre-detail'),
    path('languages/', views.LanguagesListView.as_view(), name='languages'),
    path(
        'language/create/',
        views.LanguageCreate.as_view(),
        name='language-create'
    ),
    path(
        'language/<int:pk>',
        views.LanguageView.as_view(),
        name='language-detail'
    ),
    path('mybooks/', views.LoanedBooksByUserListView.as_view(),
         name='my-borrowed'),
]
