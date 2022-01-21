from django.contrib.auth.models import AbstractUser

from django.db import models


class User(AbstractUser):
    avatar = models.ImageField(default='default.jpeg')
