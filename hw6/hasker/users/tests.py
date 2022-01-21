from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from .models import User


class ProfileViewTests(TestCase):
    def test_user_access(self):
        """
        User can access his own profile
        """
        user = User.objects.create(username='test')
        self.client.force_login(user)

        response = self.client.get(reverse('profile', kwargs={'pk': user.pk}))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_redirect_to_login(self):
        """
        If user makes request to see another user's profile,
        redirect to login
        """
        owner = User.objects.create(username='owner')
        another_user = User.objects.create(username='another_user')
        self.client.force_login(another_user)

        response = self.client.get(reverse('profile', kwargs={'pk': owner.pk}))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
