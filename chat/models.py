from django.conf import settings
from django.db import models


class Conversation(models.Model):
    CONVERSATION_TYPES = [
        ('private', 'Private'),
        ('group', 'Group'),
    ]

    conversation_type = models.CharField(max_length=10, choices=CONVERSATION_TYPES)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    name = models.CharField(max_length=150, blank=True)
    image = models.ImageField(upload_to='chat/groups/', blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.conversation_type == 'group':
            return self.name

        return f'Private conversation {self.id}'

    def get_private_chat_user(self, user):
        if self.conversation_type != 'private':
            return None

        return self.participants.exclude(id=user.id).first()


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to='chat/images/', blank=True, null=True)
    video = models.FileField(upload_to='chat/videos/', blank=True, null=True)
    file = models.FileField(upload_to='chat/files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(blank=True, null=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender.email} - {self.created_at}'