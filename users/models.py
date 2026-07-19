from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(
            email=email,
            password=password,
            **extra_fields
        )


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = [
        'first_name',
        'last_name',
    ]

    objects = CustomUserManager()

    def get_friends(self):
        return CustomUser.objects.filter(
            Q(friendships_as_user2__user1=self) |
            Q(friendships_as_user1__user2=self)
        ).distinct()

    def is_friend_with(self, user):
        return Friendship.objects.filter(
            models.Q(user1=self, user2=user) |
            models.Q(user1=user, user2=self)
        ).exists()
    
    @property
    def is_online(self):
        if not self.last_activity:
            return False

        online_limit = timezone.now() - timedelta(minutes=5)

        return self.last_activity >= online_limit

    def __str__(self):
        return self.email
    

class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='profiles/avatars/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='profiles/covers/', blank=True, null=True)
    bio = models.TextField(blank=True)
    birth_date = models.DateField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.email} profile'
    

class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_friend_requests')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['sender', 'receiver']
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.sender.email} -> {self.receiver.email}'


class Friendship(models.Model):
    user1 = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friendships_as_user1')
    user2 = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friendships_as_user2')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user1', 'user2']

    def __str__(self):
        return f'{self.user1.email} - {self.user2.email}'
    


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('friend_request', 'Friend request'),
        ('friend_accepted', 'Friend accepted'),
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('message', 'Message'),
        ('group_added', 'Added to group'),
    ]

    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    text = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient.email} - {self.notification_type}'