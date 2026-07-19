from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Profile, FriendRequest, Friendship


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    ordering = [
        'email'
    ]

    list_display = [
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
    ]

    search_fields = [
        'email',
        'first_name',
        'last_name',
    ]

    fieldsets = (
        (
            None,
            {
                'fields': ('email', 'password',)
            }
        ),
        (
            'Personal information',
            {
                'fields': ('first_name', 'last_name',)
            }
        ),
        (
            'Permissions',
            {
                'fields': ('is_active',
                           'is_staff',
                           'is_superuser',
                           'groups',
                           'user_permissions',
                           )
            }
        ),
        (
            'Important dates',
            {
                'fields': ('last_login', 'date_joined',)
            }
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'password1',
                    'password2',
                    'is_staff',
                    'is_active',
                ),
            }
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'city',
        'created_at',
    ]

    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
    ]


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['sender__email', 'receiver__email']


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ['user1', 'user2', 'created_at']
    search_fields = ['user1__email', 'user2__email']