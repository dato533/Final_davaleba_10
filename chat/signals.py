import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Conversation, Message


@receiver(post_delete, sender=Message)
def delete_message_files(sender, instance, **kwargs):
    if instance.image and os.path.isfile(instance.image.path):
        os.remove(instance.image.path)

    if instance.video and os.path.isfile(instance.video.path):
        os.remove(instance.video.path)

    if instance.file and os.path.isfile(instance.file.path):
        os.remove(instance.file.path)


@receiver(post_delete, sender=Conversation)
def delete_group_image(sender, instance, **kwargs):
    if instance.image and os.path.isfile(instance.image.path):
        os.remove(instance.image.path)