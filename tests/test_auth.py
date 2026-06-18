import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group


class AuthTest(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Super Admin')
        Group.objects.get_or_create(name='Treasurer')
        self.client = Client()

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/login/?next=/')

    def test_login_succeeds(self):
        User.objects.create_user('u1', password='pass123')
        response = self.client.post('/login/', {'username': 'u1', 'password': 'pass123'})
        self.assertRedirects(response, '/')

    def test_bad_login_stays_on_login(self):
        response = self.client.post('/login/', {'username': 'nobody', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
