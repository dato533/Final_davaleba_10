from django.contrib import admin
from .models import Post, PostMedia, Comment, Like


class PostMediaInline(admin.TabularInline):
    model = PostMedia
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'created_at', 'updated_at']
    search_fields = ['author__email', 'author__first_name', 'author__last_name', 'text']
    list_filter = ['created_at']
    inlines = [PostMediaInline]


@admin.register(PostMedia)
class PostMediaAdmin(admin.ModelAdmin):
    list_display = ['post', 'media_type', 'created_at']
    list_filter = ['media_type', 'created_at']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    search_fields = ['user__email']
    list_filter = ['created_at']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'created_at']
    search_fields = ['author__email', 'text']
    list_filter = ['created_at']



