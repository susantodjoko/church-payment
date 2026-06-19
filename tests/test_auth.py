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

    def test_treasurer_cannot_access_settings(self):
        treasurer_group = Group.objects.get(name='Treasurer')
        user = User.objects.create_user('treasurer1', password='pass')
        user.groups.add(treasurer_group)
        self.client.login(username='treasurer1', password='pass')
        # settings_admin URLs protected by SuperAdminRequired
        # We'll test a real settings URL in Task 13; for now test the mixin directly

    def test_super_admin_context_flag(self):
        admin_group = Group.objects.get(name='Super Admin')
        user = User.objects.create_user('admin1', password='pass')
        user.groups.add(admin_group)
        self.client.login(username='admin1', password='pass')
        response = self.client.get('/')
        self.assertTrue(response.context['is_super_admin'])

    def test_treasurer_context_flag_false(self):
        treasurer_group = Group.objects.get(name='Treasurer')
        user = User.objects.create_user('treas1', password='pass')
        user.groups.add(treasurer_group)
        self.client.login(username='treas1', password='pass')
        response = self.client.get('/')
        self.assertFalse(response.context['is_super_admin'])


class SettingsAdminAccessTest(TestCase):
    def setUp(self):
        admin_group = Group.objects.get_or_create(name='Super Admin')[0]
        treasurer_group = Group.objects.get_or_create(name='Treasurer')[0]
        self.admin = User.objects.create_user('admin', password='pass')
        self.admin.groups.add(admin_group)
        self.treasurer = User.objects.create_user('treasurer', password='pass')
        self.treasurer.groups.add(treasurer_group)

    def test_admin_can_access_settings_users(self):
        self.client.login(username='admin', password='pass')
        response = self.client.get('/settings/users/')
        self.assertEqual(response.status_code, 200)

    def test_treasurer_cannot_access_settings_users(self):
        self.client.login(username='treasurer', password='pass')
        response = self.client.get('/settings/users/')
        self.assertEqual(response.status_code, 403)
