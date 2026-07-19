import pytest
from django.urls import reverse
from users.models import CustomUser


@pytest.mark.django_db
def test_register_user(client):

    response = client.post(
        reverse('users:register'),
        {
            'first_name': 'John',
            'last_name': 'Smith',
            'email': 'john@test.com',
            'password1': 'StrongPassword123',
            'password2': 'StrongPassword123',
        }
    )

    assert response.status_code == 302
    assert CustomUser.objects.filter(email='john@test.com').exists()


@pytest.mark.django_db
def test_login_user(client):

    user = CustomUser.objects.create_user(
        email='john@test.com',
        password='StrongPassword123',
        first_name='John',
        last_name='Smith'
    )

    response = client.post(
        reverse('users:login'),
        {
            'username': user.email,
            'password': 'StrongPassword123',
        }
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_profile_created_after_registration():

    user = CustomUser.objects.create_user(
        email='profile@test.com',
        password='StrongPassword123',
        first_name='Profile',
        last_name='Test'
    )

    assert hasattr(user, 'profile')