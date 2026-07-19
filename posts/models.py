from django.conf import settings
from django.db import models


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    text = models.TextField(blank=True)
    shared_post = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='reposts', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def reaction_counts(self):
        counts = {
            'like': 0,
            'love': 0,
            'haha': 0,
            'wow': 0,
            'sad': 0,
            'angry': 0,
        }

        for reaction in self.likes.all():
            counts[reaction.reaction_type] += 1

        return counts

    @property
    def reaction_emojis(self):
        emojis = {
            'like': '👍',
            'love': '❤️',
            'haha': '😂',
            'wow': '😮',
            'sad': '😢',
            'angry': '😡',
        }

        existing_reactions = []

        for reaction in self.likes.all():
            emoji = emojis.get(reaction.reaction_type)

            if emoji and emoji not in existing_reactions:
                existing_reactions.append(emoji)

        return existing_reactions

    @property
    def total_reactions(self):
        return self.likes.count()

    @property
    def total_reposts(self):
        return self.reposts.count()

    def __str__(self):
        return f'{self.author.email} - {self.created_at}'

    @property
    def reaction_emojis(self):
        emojis = {
            'like': '👍',
            'love': '❤️',
            'haha': '😂',
            'wow': '😮',
            'sad': '😢',
            'angry': '😡',
        }

        existing_reactions = []

        for reaction in self.likes.all():
            emoji = emojis.get(reaction.reaction_type)

            if emoji and emoji not in existing_reactions:
                existing_reactions.append(emoji)

        return existing_reactions

    @property
    def total_reactions(self):
        return self.likes.count()

    def __str__(self):
        return f'{self.author.email} - {self.created_at}'


class PostMedia(models.Model):
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='posts/media/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.post.id} - {self.media_type}'
    

class Like(models.Model):
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('love', 'Love'),
        ('haha', 'Haha'),
        ('wow', 'Wow'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes'
    )

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes'
    )

    reaction_type = models.CharField(
        max_length=10,
        choices=REACTION_CHOICES,
        default='like'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'post']
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.reaction_type} - {self.post.id}'

    @property
    def emoji(self):
        reaction_emojis = {
            'like': '👍',
            'love': '❤️',
            'haha': '😂',
            'wow': '😮',
            'sad': '😢',
            'angry': '😡',
        }

        return reaction_emojis.get(self.reaction_type, '👍')


class Comment(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author.email} - post {self.post.id}'
    



    