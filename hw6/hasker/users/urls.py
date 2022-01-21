from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


urlpatterns = [
    path('auth/login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('auth/signup/', views.SignUpView.as_view(), name='signup'),
    path('profile/<int:pk>', views.ProfileView.as_view(), name='profile'),
]
