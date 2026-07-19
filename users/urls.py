from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from .forms import CustomPasswordResetForm, CustomSetPasswordForm


app_name = 'users'

urlpatterns = [
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('change-password/', views.change_password, name='change_password'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
            template_name='users/password_reset.html',
            form_class=CustomPasswordResetForm,
            email_template_name='users/password_reset_email.txt',
            subject_template_name='users/password_reset_subject.txt',
            success_url='/users/password-reset/done/'
        ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
            template_name='users/password_reset_done.html'
        ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
            template_name='users/password_reset_confirm.html',
            form_class=CustomSetPasswordForm,
            success_url='/users/password-reset-complete/'
        ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
            template_name='users/password_reset_complete.html'
        ), name='password_reset_complete'),
    path('profile/<int:user_id>/', views.profile_detail, name='profile_detail'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('account/delete/', views.delete_account, name='delete_account'),
    path('search/', views.user_search, name='user_search'),
    path('friends/', views.friends_list, name='friends_list'),
    path('friends/<int:user_id>/', views.friends_list, name='user_friends'),
    path('friend-requests/', views.friend_requests, name='friend_requests'),
    path('friend-request/send/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('friend-request/<int:request_id>/accept/', views.accept_friend_request, name='accept_friend_request'),
    path('friend-request/<int:request_id>/decline/', views.decline_friend_request, name='decline_friend_request'),
    path('friend/remove/<int:user_id>/', views.remove_friend, name='remove_friend'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/open/', views.open_notification, name='open_notification'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/delete-all/', views.delete_all_notifications, name='delete_all_notifications'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
]