import pytest
from django.urls import reverse
from users.models import CustomUser
from posts.models import Post


@pytest.mark.django_db
def test_create_post(client):

    user = CustomUser.objects.create_user(
        email='john@test.com',
        password='StrongPassword123',
        first_name='John',
        last_name='Smith'
    )

    client.force_login(user)

    response = client.post(
        reverse('posts:create_post'),
        {
            'text': 'My first pytest post'
        }
    )

    assert response.status_code == 302
    assert Post.objects.filter(text='My first pytest post').exists()


@pytest.mark.django_db
def test_edit_post(client):

    user = CustomUser.objects.create_user(
        email='john@test.com',
        password='StrongPassword123',
        first_name='John',
        last_name='Smith'
    )

    post = Post.objects.create(
        author=user,
        text='Old text'
    )

    client.force_login(user)

    response = client.post(
        reverse('posts:edit_post', args=[post.id]),
        {
            'text': 'New text'
        }
    )

    post.refresh_from_db()

    assert response.status_code == 302
    assert post.text == 'New text'


@pytest.mark.django_db
def test_delete_post(client):

    user = CustomUser.objects.create_user(
        email='john@test.com',
        password='StrongPassword123',
        first_name='John',
        last_name='Smith'
    )

    post = Post.objects.create(
        author=user,
        text='Delete me'
    )

    client.force_login(user)

    response = client.post(
        reverse('posts:delete_post', args=[post.id])
    )

    assert response.status_code == 302
    assert not Post.objects.filter(id=post.id).exists()