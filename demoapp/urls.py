from django.conf.urls import url

from demoapp import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^author/(?P<pk>[0-9]+)',
        views.AuthorDetailView.as_view(), name='author-detail'),
    url(r'^author/create/', views.AuthorCreate.as_view(),
        name='author-create'),
    url(r'^author/(?P<pk>[0-9]+)/update/',
        views.AuthorUpdate.as_view(),
        name='author-update'
        ),
    url(r'^author/(?P<pk>[0-9]+)/delete/', views.AuthorDelete.as_view(),
        name='author-delete'),
    url(r'^authors/', views.AuthorListView.as_view(), name='authors'),
    url(r'^books/', views.BookListView.as_view(), name='books'),
    url(r'^book/(?P<pk>[0-9]+)/', views.BookDetailView.as_view(),
        name='book-detail'),
    url(
        r'^book/(?P<pk>[0-9A-Fa-f]{8}'
        r'(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12})/renew/',
        views.renew_book_librarian,
        name='renew-book-librarian'),
    url(r'^book/create/', views.BookCreate.as_view(), name='book-create'),
    url(r'^book/(?P<pk>[0-9]+)/update/', views.BookUpdate.as_view(),
        name='book-update'),
    url(r'^book/(?P<pk>[0-9]+)/delete/', views.BookDelete.as_view(),
        name='book-delete'),
    url(r'^borrowed/', views.LoanedBooksAllListView.as_view(),
        name='all-borrowed'),
    url(r'^genres/', views.GenresListView.as_view(), name='genres'),
    url(r'^genre/create/', views.GenreCreate.as_view(), name='genre-create'),
    url(r'^genre/(?P<pk>[0-9]+)', views.GenreView.as_view(),
        name='genre-detail'),
    url(r'^languages/', views.LanguagesListView.as_view(), name='languages'),
    url(r'^language/create/',
        views.LanguageCreate.as_view(),
        name='language-create'
        ),
    url(r'^language/(?P<pk>[0-9]+)',
        views.LanguageView.as_view(),
        name='language-detail'
        ),
    url(r'^mybooks/', views.LoanedBooksByUserListView.as_view(),
        name='my-borrowed'),
]
