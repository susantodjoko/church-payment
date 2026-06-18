import pytest
from django.contrib.auth.models import User, Group


@pytest.fixture
def admin_group(db):
    return Group.objects.get_or_create(name='Super Admin')[0]


@pytest.fixture
def treasurer_group(db):
    return Group.objects.get_or_create(name='Treasurer')[0]


@pytest.fixture
def admin_user(db, admin_group):
    user = User.objects.create_user('admin', password='testpass123')
    user.groups.add(admin_group)
    return user


@pytest.fixture
def treasurer_user(db, treasurer_group):
    user = User.objects.create_user('treasurer', password='testpass123')
    user.groups.add(treasurer_group)
    return user
