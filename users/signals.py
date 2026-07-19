from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Profile


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=CustomUser)
def send_welcome_email(sender, instance, created, **kwargs):
    if created and instance.email:
        send_mail(
            subject='Welcome to ConnectHub',
            message=(
                f'Hello {instance.first_name},\n\n'
                'Your ConnectHub account was created successfully.\n\n'
                'Welcome to our social network!'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.email],
            fail_silently=True,
        )