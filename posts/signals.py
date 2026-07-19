import os
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import PostMedia


@receiver(post_delete, sender=PostMedia)
def delete_post_media_file(sender, instance, **kwargs):
    if instance.file and os.path.isfile(instance.file.path):
        os.remove(instance.file.path)


