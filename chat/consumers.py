import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from users.models import Notification
from .models import Conversation, Message


ACTIVE_CHAT_USERS = {}


class InboxConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.inbox_group_name = f'chat_inbox_{self.user.id}'

        await self.channel_layer.group_add(
            self.inbox_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'inbox_group_name'):
            await self.channel_layer.group_discard(
                self.inbox_group_name,
                self.channel_name
            )

    async def conversation_updated(self, event):
        await self.send(text_data=json.dumps({
            'type': 'conversation_updated',
            'conversation_id': event['conversation_id'],
            'action': event.get('action', 'updated'),
        }))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        if not self.user.is_authenticated:
            await self.close()
            return

        if not await self.user_is_participant():
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        self.add_active_user()

    async def disconnect(self, close_code):
        if not hasattr(self, 'room_group_name'):
            return

        if getattr(self, 'user', None) and self.user.is_authenticated:
            self.remove_active_user()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_typing',
                    'sender_id': self.user.id,
                    'sender_name': self.get_sender_name(),
                    'is_typing': False,
                }
            )

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error('Invalid message data.')
            return

        event_type = data.get('type', 'chat_message')

        if event_type == 'typing':
            await self.handle_typing(data)
            return

        if event_type == 'mark_read':
            await self.handle_mark_read()
            return

        if event_type == 'delete_message':
            await self.handle_delete_message(data)
            return

        if event_type == 'edit_message':
            await self.handle_edit_message(data)
            return

        await self.handle_text_message(data)

    async def handle_text_message(self, data):
        message_text = data.get('message', '').strip()

        if not message_text:
            await self.send_error('Message cannot be empty.')
            return

        if not await self.user_is_participant():
            await self.close()
            return

        active_user_ids = self.get_active_user_ids()
        message = await self.create_message(message_text)

        if not message:
            await self.send_error('Message could not be saved.')
            return

        await self.create_notifications(active_user_ids)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_typing',
                'sender_id': self.user.id,
                'sender_name': self.get_sender_name(),
                'is_typing': False,
            }
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message['id'],
                'message': message['text'],
                'sender_id': message['sender_id'],
                'sender_name': message['sender_name'],
                'sender_avatar': message['sender_avatar'],
                'created_at': message['created_at'],
                'is_read': message['is_read'],
                'is_edited': False,
            }
        )

        await self.notify_inboxes('created')

    async def handle_typing(self, data):
        if not await self.user_is_participant():
            await self.close()
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_typing',
                'sender_id': self.user.id,
                'sender_name': self.get_sender_name(),
                'is_typing': bool(data.get('is_typing')),
            }
        )

    async def handle_mark_read(self):
        if not await self.user_is_participant():
            await self.close()
            return

        read_message_ids = await self.mark_unread_messages_as_read()

        if not read_message_ids:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'messages_read',
                'message_ids': read_message_ids,
                'reader_id': self.user.id,
            }
        )

        await self.notify_inboxes('read')

    async def handle_delete_message(self, data):
        if not await self.user_is_participant():
            await self.close()
            return

        try:
            message_id = int(data.get('message_id'))
        except (TypeError, ValueError):
            await self.send_error('Invalid message ID.')
            return

        deleted_message_id = await self.delete_own_message(message_id)

        if not deleted_message_id:
            await self.send_error('You can delete only your own messages from this chat.')
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_deleted',
                'message_id': deleted_message_id,
                'deleted_by': self.user.id,
            }
        )

        await self.notify_inboxes('deleted')

    async def handle_edit_message(self, data):
        if not await self.user_is_participant():
            await self.close()
            return

        try:
            message_id = int(data.get('message_id'))
        except (TypeError, ValueError):
            await self.send_error('Invalid message ID.')
            return

        new_text = str(data.get('message', '')).strip()
        edited_message = await self.edit_own_message(message_id, new_text)

        if not edited_message:
            await self.send_error(
                'The message could not be edited. You can edit only your own message and it cannot be empty without an attachment.'
            )
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_edited',
                'message_id': edited_message['id'],
                'message': edited_message['text'],
                'edited_at': edited_message['edited_at'],
            }
        )

        await self.notify_inboxes('edited')

    async def notify_inboxes(self, action):
        participant_ids = await self.get_participant_ids()

        for participant_id in participant_ids:
            await self.channel_layer.group_send(
                f'chat_inbox_{participant_id}',
                {
                    'type': 'conversation_updated',
                    'conversation_id': int(self.conversation_id),
                    'action': action,
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event['message_id'],
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'sender_avatar': event['sender_avatar'],
            'created_at': event['created_at'],
            'is_read': event['is_read'],
            'is_edited': event.get('is_edited', False),
            'image_url': event.get('image_url', ''),
            'video_url': event.get('video_url', ''),
            'file_url': event.get('file_url', ''),
            'file_name': event.get('file_name', ''),
        }))

    async def chat_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'is_typing': event['is_typing'],
        }))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'message_ids': event['message_ids'],
            'reader_id': event['reader_id'],
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'deleted_by': event['deleted_by'],
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message_id': event['message_id'],
            'message': event['message'],
            'edited_at': event['edited_at'],
        }))

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
        }))

    def add_active_user(self):
        conversation_users = ACTIVE_CHAT_USERS.setdefault(self.conversation_id, {})
        conversation_users[self.user.id] = conversation_users.get(self.user.id, 0) + 1

    def remove_active_user(self):
        conversation_users = ACTIVE_CHAT_USERS.get(self.conversation_id)

        if not conversation_users:
            return

        connection_count = conversation_users.get(self.user.id, 0)

        if connection_count <= 1:
            conversation_users.pop(self.user.id, None)
        else:
            conversation_users[self.user.id] = connection_count - 1

        if not conversation_users:
            ACTIVE_CHAT_USERS.pop(self.conversation_id, None)

    def get_active_user_ids(self):
        return list(ACTIVE_CHAT_USERS.get(self.conversation_id, {}).keys())

    def get_sender_name(self):
        sender_name = f'{self.user.first_name} {self.user.last_name}'.strip()
        return sender_name or self.user.email

    @database_sync_to_async
    def user_is_participant(self):
        return Conversation.objects.filter(
            id=self.conversation_id,
            participants=self.user
        ).exists()

    @database_sync_to_async
    def get_participant_ids(self):
        return list(
            Conversation.objects.filter(
                id=self.conversation_id,
                participants=self.user
            ).values_list('participants__id', flat=True)
        )

    @database_sync_to_async
    def mark_unread_messages_as_read(self):
        unread_messages = Message.objects.filter(
            conversation_id=self.conversation_id,
            is_read=False
        ).exclude(sender=self.user)

        message_ids = list(unread_messages.values_list('id', flat=True))

        if message_ids:
            unread_messages.update(is_read=True)

        return message_ids

    @database_sync_to_async
    def create_message(self, message_text):
        try:
            conversation = Conversation.objects.get(
                id=self.conversation_id,
                participants=self.user
            )
        except Conversation.DoesNotExist:
            return None

        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            text=message_text,
            is_read=False
        )

        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])

        sender_avatar = ''

        if hasattr(self.user, 'profile') and self.user.profile.avatar:
            sender_avatar = self.user.profile.avatar.url

        return {
            'id': message.id,
            'text': message.text,
            'sender_id': self.user.id,
            'sender_name': self.get_sender_name(),
            'sender_avatar': sender_avatar,
            'created_at': message.created_at.strftime('%H:%M'),
            'is_read': message.is_read,
        }

    @database_sync_to_async
    def edit_own_message(self, message_id, new_text):
        try:
            message = Message.objects.get(
                id=message_id,
                conversation_id=self.conversation_id,
                sender=self.user
            )
        except Message.DoesNotExist:
            return None

        if not new_text and not message.image and not message.video and not message.file:
            return None

        message.text = new_text
        message.edited_at = timezone.now()
        message.save(update_fields=['text', 'edited_at'])

        message.conversation.updated_at = timezone.now()
        message.conversation.save(update_fields=['updated_at'])

        return {
            'id': message.id,
            'text': message.text,
            'edited_at': message.edited_at.strftime('%H:%M'),
        }

    @database_sync_to_async
    def delete_own_message(self, message_id):
        try:
            message = Message.objects.get(
                id=message_id,
                conversation_id=self.conversation_id,
                sender=self.user
            )
        except Message.DoesNotExist:
            return None

        conversation = message.conversation
        deleted_message_id = message.id
        message.delete()
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        return deleted_message_id

    @database_sync_to_async
    def create_notifications(self, active_user_ids):
        try:
            conversation = Conversation.objects.prefetch_related('participants').get(
                id=self.conversation_id,
                participants=self.user
            )
        except Conversation.DoesNotExist:
            return

        sender_name = self.get_sender_name()
        recipients = conversation.participants.exclude(
            id=self.user.id
        ).exclude(id__in=active_user_ids)

        notifications = [
            Notification(
                recipient=participant,
                sender=self.user,
                notification_type='message',
                text=f'{sender_name} sent you a message.',
                url=f'/chat/{conversation.id}/'
            )
            for participant in recipients
        ]

        if notifications:
            Notification.objects.bulk_create(notifications)
