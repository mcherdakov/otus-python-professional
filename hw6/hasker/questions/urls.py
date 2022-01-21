from django.urls import path

from . import views


urlpatterns = [
    path('', views.index_view, name='index'),
    path('create/', views.create_question_view, name='create'),
    path('<int:pk>/', views.question_detail_view, name='question'),
    path('vote/', views.vote_view, name='vote'),
    path('vote_best/', views.vote_best_view, name='vote_best'),
    path('search/', views.search_view, name='search'),
]
