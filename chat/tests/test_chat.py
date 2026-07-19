import pytest
from django.urls import reverse
from chat.models import Conversation, Message
from users.models import CustomUser, Friendship


@pytest.mark.django_db
def test_create_private_conversation(client):
    user1 = CustomUser.objects.create_user(
        email='user1@test.com',
        password='StrongPassword123',
        first_name='John',
        last_name='Smith'
    )

    user2 = CustomUser.objects.create_user(
        email='user2@test.com',
        password='StrongPassword123',
        first_name='Mike',
        last_name='Brown'
    )

    friendship_user1, friendship_user2 = sorted(
        [user1, user2],
        key=lambda user: user.id
    )

    Friendship.objects.create(
        user1=friendship_user1,
        user2=friendship_user2
    )

    client.force_login(user1)

    response = client.get(
        reverse(
            'chat:start_private_conversation',
            args=[user2.id]
        )
    )

    conversation = Conversation.objects.first()

    assert response.status_code == 302
    assert Conversation.objects.count() == 1
    assert conversation is not None
    assert conversation.conversation_type == 'private'
    assert conversation.created_by == user1
    assert conversation.participants.filter(id=user1.id).exists()
    assert conversation.participants.filter(id=user2.id).exists()


@pytest.mark.django_db
def test_create_group(client):
    user = CustomUser.objects.create_user(
        email='admin@test.com',
        password='StrongPassword123',
        first_name='Admin',
        last_name='User'
    )

    friend = CustomUser.objects.create_user(
        email='friend@test.com',
        password='StrongPassword123',
        first_name='Friend',
        last_name='User'
    )

    friendship_user1, friendship_user2 = sorted(
        [user, friend],
        key=lambda current_user: current_user.id
    )

    Friendship.objects.create(
        user1=friendship_user1,
        user2=friendship_user2
    )

    client.force_login(user)

    response = client.post(
        reverse('chat:create_group'),
        {
            'name': 'Pytest Group',
            'participants': [friend.id],
        }
    )

    conversation = Conversation.objects.filter(
        name='Pytest Group'
    ).first()

    assert response.status_code == 302
    assert conversation is not None
    assert conversation.conversation_type == 'group'
    assert conversation.created_by == user
    assert conversation.participants.filter(id=user.id).exists()
    assert conversation.participants.filter(id=friend.id).exists()


@pytest.mark.django_db
def test_send_message(client):
    user1 = CustomUser.objects.create_user(
        email='user1@test.com',
        password='StrongPassword123',
        first_name='John',
        last_name='Smith'
    )

    user2 = CustomUser.objects.create_user(
        email='user2@test.com',
        password='StrongPassword123',
        first_name='Mike',
        last_name='Brown'
    )

    conversation = Conversation.objects.create(
        conversation_type='private',
        created_by=user1
    )

    conversation.participants.add(user1, user2)

    client.force_login(user1)

    response = client.post(
        reverse(
            'chat:conversation_detail',
            args=[conversation.id]
        ),
        {
            'text': 'Hello from pytest!'
        }
    )

    message = Message.objects.filter(
        text='Hello from pytest!'
    ).first()

    assert response.status_code == 302
    assert message is not None
    assert message.sender == user1
    assert message.conversation == conversation