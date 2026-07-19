from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_type', 'name', 'created_by', 'created_at']
    list_filter = ['conversation_type', 'created_at']
    search_fields = ['name', 'created_by__email']
    filter_horizontal = ['participants']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'conversation', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__email', 'text']